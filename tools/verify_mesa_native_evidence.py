#!/usr/bin/env python3
"""Consistency checks for captured Mesa-family native build evidence (NO admission).

All evidence and path roots are untrusted until a separate root-control
native witness authenticates exact collection, installation and execution.
No compiler invocation, network access, native admission, or rights approval.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import struct

COMPONENTS = ("llvm", "mesa", "libdrm", "libxshmfence", "libXxf86vm", "mesa-demos")
SIDECARS = ("compile_commands", "source_objects", "installed_inventory",
            "elf_dependencies", "library_provenance", "delivered_notices")
SCHEMA = "zog-mesa-native-evidence-v1"
MAX_JSON = 8 * 1024 * 1024
MAX_ENTRIES = 200000
MAX_BYTES = 2 ** 35


class EvidenceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha(value):
    return isinstance(value, str) and len(value) == 64 and all(
        c in "0123456789abcdef" for c in value)


def json_file(path):
    require(path.is_file() and not path.is_symlink(), "missing/nonregular evidence: " + str(path))
    require(path.stat().st_size <= MAX_JSON, "oversized evidence JSON")
    return json.loads(path.read_bytes())


def relative(value):
    require(isinstance(value, str) and value and "\x00" not in value and "\\" not in value,
            "invalid evidence path")
    p = Path(value)
    require(not p.is_absolute() and all(x not in (".", "..") for x in value.split("/"))
            and "//" not in value, "traversal or noncanonical path: " + value)
    return p


def within(path, root):
    resolved = path.resolve(strict=True)
    require(resolved == root or root in resolved.parents, "Host path escape: " + str(path))
    return resolved


def actual_file(root, name):
    path = root / relative(name)
    resolved = within(path, root)
    require(resolved.is_file(), "not a regular file: " + name)
    return resolved


def file_hash(root, name, claimed):
    require(sha(claimed), "missing/invalid content SHA256: " + name)
    path = actual_file(root, name)
    require(path.stat().st_size <= MAX_BYTES, "file too large")
    h = hashlib.sha256()
    with path.open("rb") as fd:
        for block in iter(lambda: fd.read(1024 * 1024), b""):
            h.update(block)
    require(h.hexdigest() == claimed, "content digest mismatch: " + name)


def load_sidecars(folder, envelope):
    require(set(envelope["evidence"]) == set(SIDECARS), "incomplete evidence sidecars")
    result = {}
    for key in SIDECARS:
        ref = envelope["evidence"][key]
        require(set(ref) == {"file", "sha256"} and sha(ref["sha256"]),
                "sidecar identity invalid: " + key)
        name = relative(ref["file"])
        require(len(name.parts) == 1 and name.suffix == ".json",
                "sidecars must be flat JSON files")
        file_hash(folder, name.as_posix(), ref["sha256"])
        result[key] = json_file(folder / name)
        require(isinstance(result[key], list) and len(result[key]) <= MAX_ENTRIES,
                "invalid sidecar array: " + key)
    return result


def roots_from(envelope):
    require(set(envelope["roots"]) == {"source", "build", "destdir", "software"},
            "missing native evidence roots")
    roots = {}
    for key, text in envelope["roots"].items():
        path = Path(text)
        require(path.is_absolute() and not path.is_symlink() and path.is_dir(),
                "native root must be an existing absolute directory: " + key)
        roots[key] = path.resolve(strict=True)
        require(roots[key] != Path("/"), "unbounded native root: " + key)
    require(len(set(roots.values())) == len(roots), "overlapping identical roots")
    return roots


def compiler_flags(argv, roots):
    require(isinstance(argv, list) and all(isinstance(x, str) and x for x in argv),
            "invalid compiler argv")
    require(not any(x.startswith("@") for x in argv), "response file needs independent expansion")
    prefixes = ("-I", "-L", "-isystem", "-iquote", "-idirafter")
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in prefixes:
            i += 1
            require(i < len(argv), "missing compiler path option")
            path = argv[i]
        else:
            prefix = next((p for p in prefixes if arg.startswith(p) and len(arg) > len(p)), None)
            path = arg[len(prefix):] if prefix else None
        if path is not None:
            require(Path(path).is_absolute() and any(
                within_if_exists(Path(path), root) for root in roots),
                "compiler Host include/library directory: " + path)
        require(not arg.startswith(("-Wl,", "-fplugin", "-B/")),
                "opaque linker or compiler plugin argument requires review")
        i += 1


def within_if_exists(path, root):
    try:
        return within(path, root) == path.resolve(strict=True)
    except (OSError, EvidenceError):
        return False


def commands_and_objects(sidecars, roots, envelope):
    commands = sidecars["compile_commands"]
    maps = sidecars["source_objects"]
    require(commands and len(commands) == len(maps), "compile/source-object coverage differs")
    require(len({(row["source_root"], row["source"], row["object"]) for row in maps}) ==
            len(maps), "duplicate source-object relation")
    mapped = {}
    for row in maps:
        require(set(row) == {"source_root", "source", "source_sha256",
                             "object", "object_sha256", "generated_inputs"},
                "incomplete source-object map")
        origin = row["source_root"]
        require(origin in ("source", "build"), "source outside accepted source/generated root")
        require(origin == "build" or row["generated_inputs"] == [],
                "original source cannot claim generated inputs")
        require(isinstance(row["generated_inputs"], list), "invalid generator dependency list")
        if origin == "build":
            require(row["generated_inputs"], "generated source missing provenance inputs")
            for item in row["generated_inputs"]:
                require(set(item) == {"root", "path", "sha256"} and item["root"] in ("source", "build"),
                        "invalid generator input")
                file_hash(roots[item["root"]], item["path"], item["sha256"])
        file_hash(roots[origin], row["source"], row["source_sha256"])
        file_hash(roots["build"], row["object"], row["object_sha256"])
        key = (str((roots[origin] / relative(row["source"])).resolve()),
               str((roots["build"] / relative(row["object"])).resolve()))
        require(key not in mapped, "duplicate object mapping")
        mapped[key] = row
    seen = set()
    for cmd in commands:
        require("directory" in cmd and "file" in cmd and "output" in cmd,
                "compile database lacks directory/file/output")
        require(("arguments" in cmd) != ("command" in cmd),
                "compile database must specify exactly one argument representation")
        argv = cmd.get("arguments")
        if argv is None:
            require(isinstance(cmd["command"], str), "invalid shell command")
            argv = shlex.split(cmd["command"])
            require(not any(c in cmd["command"] for c in (";", "|", "\n", "\`", "$(")),
                    "shell expansion in compile database must be reviewed")
        require(argv and argv[0].startswith("/") and "-c" in argv and "-o" in argv,
                "unstructured compiler invocation")
        require(Path(cmd["directory"]).resolve(strict=True) == roots["build"],
                "compiler working directory outside selected build root")
        compiler = Path(argv[0])
        require(compiler.is_file() and within_if_exists(compiler, roots["software"]),
                "compiler outside selected software root")
        require(file_digest_matches(compiler, envelope["compilers"]), "unapproved compiler bytes")
        try:
            arg_source = argv[argv.index("-c") + 1]
            arg_output = argv[argv.index("-o") + 1]
        except IndexError:
            raise EvidenceError("truncated -c/-o option") from None
        require(arg_source == cmd["file"] and arg_output == cmd["output"],
                "compile command source/output mismatch")
        require(Path(arg_source).is_absolute() and Path(arg_output).is_absolute(),
                "unbound compiler source/output")
        compiler_flags(argv[1:], tuple(roots.values()))
        key = (str(Path(cmd["file"]).resolve(strict=True)),
               str(Path(cmd["output"]).resolve(strict=True)))
        require(key in mapped and key not in seen, "missing or duplicated source-object mapping")
        seen.add(key)
    require(seen == set(mapped), "unobserved mapped compiler output")
    return len(seen)


def file_digest_matches(path, compilers):
    if not isinstance(compilers, list) or len(compilers) > 32:
        return False
    for row in compilers:
        if (isinstance(row, dict) and set(row) == {"path", "sha256"}
                and row["path"] == str(path) and sha(row["sha256"])):
            return digest(path.read_bytes()) == row["sha256"]
    return False


def installed_files(rows, root, expected):
    require(isinstance(rows, list) and rows, "missing DESTDIR inventory")
    seen = set()
    for item in rows:
        require(isinstance(item, dict) and item.get("type") in ("file", "symlink"),
                "invalid installed file record")
        name = relative(item["path"]).as_posix()
        require(name not in seen, "duplicate installed path")
        seen.add(name)
        path = root / name
        mode = path.lstat().st_mode
        if item["type"] == "file":
            require(stat.S_ISREG(mode) and set(item) == {"path", "type", "sha256"},
                    "not an installed regular file")
            file_hash(root, name, item["sha256"])
        else:
            require(stat.S_ISLNK(mode) and set(item) == {"path", "type", "target"},
                    "not an installed symbolic link")
            require(os.readlink(path) == item["target"] and not Path(item["target"]).is_absolute(),
                    "changed or absolute symlink target")
            within(path, root)
    observed = set()
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in files:
            observed.add((Path(directory) / name).relative_to(root).as_posix())
        for name in list(dirs):
            if (Path(directory) / name).is_symlink():
                observed.add((Path(directory) / name).relative_to(root).as_posix())
                dirs.remove(name)
    require(seen == observed, "incomplete DESTDIR enumeration")
    require(set(expected).issubset(seen), "expected installed output/notice missing")
    return {row["path"]: row for row in rows}


def elf_dynamic(path):
    """Read actual ELF64 little-endian PT_DYNAMIC, not a claimed readelf report."""
    data = path.read_bytes()
    require(data[:6] == b"\x7fELF\x02\x01" and len(data) >= 64,
            "unsupported or non-ELF dynamic object: " + str(path))
    h = struct.unpack_from("<16sHHIQQQIHHHHHH", data, 0)
    phoff, phsize, phnum = h[5], h[9], h[10]
    require(phnum <= 512 and phsize >= 56 and phoff + phnum * phsize <= len(data),
            "invalid ELF program headers")
    loads, dynamic = [], None
    for i in range(phnum):
        typ, _, off, addr, _, size, _, _ = struct.unpack_from("<IIQQQQQQ", data, phoff + i * phsize)
        require(off + size <= len(data), "ELF segment outside file")
        if typ == 1:
            loads.append((addr, off, size))
        if typ == 2:
            dynamic = (off, size)
    require(dynamic is not None and dynamic[1] % 16 == 0, "ELF lacks PT_DYNAMIC")
    entries = []
    for offset in range(dynamic[0], dynamic[0] + dynamic[1], 16):
        tag, val = struct.unpack_from("<qQ", data, offset)
        if tag == 0:
            break
        entries.append((tag, val))
    else:
        raise EvidenceError("unterminated ELF dynamic table")
    values = {t: v for t, v in entries}
    require(5 in values and 10 in values and values[10] <= len(data),
            "missing ELF dynamic string table")
    strtab = next((off + values[5] - addr for addr, off, size in loads
                   if addr <= values[5] < addr + size), None)
    require(strtab is not None and strtab + values[10] <= len(data),
            "ELF dynamic string table unmapped")
    def string(index):
        require(index < values[10], "ELF dynamic string offset out of range")
        start = strtab + index
        end = data.find(b"\x00", start, strtab + values[10])
        require(end >= start, "ELF dynamic string unterminated")
        return data[start:end].decode("utf-8")
    needed = [string(v) for t, v in entries if t == 1]
    return {"needed": needed,
            "soname": string(values[14]) if 14 in values else None,
            "rpath": string(values[15]).split(":") if 15 in values else [],
            "runpath": string(values[29]).split(":") if 29 in values else []}


def elf_and_libraries(sidecars, roots, inventory):
    binaries = sidecars["elf_dependencies"]
    links = sidecars["library_provenance"]
    require(isinstance(binaries, list) and isinstance(links, list), "missing ELF evidence")
    tracked, edges = set(), set()
    for entry in binaries:
        require(set(entry) == {"path", "needed", "soname", "rpath", "runpath"},
                "incomplete ELF dynamic record")
        name = relative(entry["path"]).as_posix()
        require(name in inventory and name not in tracked, "ELF not in installed inventory")
        tracked.add(name)
        observed = elf_dynamic(actual_file(roots["destdir"], name))
        require(observed == {k: entry[k] for k in observed}, "ELF dynamic bytes/report differ")
        for token in observed["rpath"] + observed["runpath"]:
            require(token and not token.startswith("/") and
                    (token == "$ORIGIN" or token.startswith("$ORIGIN/")) and
                    all(part != ".." for part in token.split("/")),
                    "untrusted ELF RPATH/RUNPATH")
        require(len(set(observed["needed"])) == len(observed["needed"]),
                "duplicate ELF DT_NEEDED name")
        edges.update((name, dep) for dep in observed["needed"])
    mapped = set()
    for row in links:
        require(set(row) == {"consumer", "needed", "root", "path", "sha256"},
                "incomplete library provenance record")
        key = (row["consumer"], row["needed"])
        require(key in edges and key not in mapped, "unmatched/duplicate library resolution")
        mapped.add(key)
        require(row["root"] in ("destdir", "software"), "Host library origin")
        file_hash(roots[row["root"]], row["path"], row["sha256"])
        target = actual_file(roots[row["root"]], row["path"])
        require(elf_dynamic(target)["soname"] == row["needed"],
                "resolved library SONAME mismatch")
    require(mapped == edges, "DT_NEEDED with no library byte provenance")
    return len(tracked), len(edges)


def notices(rows, root, inventory, rights):
    plans = rights["original_member_delivery_plan"]
    expected = {item["installed_path"]: item["original_member"] for item in plans}
    require(len(expected) == len(plans) and expected, "invalid notice contract")
    seen = set()
    evidence = rights["_original_member_hashes"]
    for row in rows:
        require(set(row) == {"path", "original_member", "sha256"},
                "incomplete delivered notice identity")
        path = relative(row["path"]).as_posix()
        require(path in expected and path not in seen and
                row["original_member"] == expected[path], "unknown/duplicate notice")
        seen.add(path)
        require(path in inventory and inventory[path]["type"] == "file",
                "notice must be installed as a regular file")
        require(evidence[row["original_member"]] == row["sha256"],
                "delivered notice not equal to original pinned archive member")
        file_hash(root, path, row["sha256"])
    require(seen == set(expected), "missing original notice delivery")
    return len(seen)


def verify(folder, drafts):
    folder = Path(folder).resolve(strict=True)
    envelope = json_file(folder / "evidence.json")
    require(envelope.get("schema") == SCHEMA and envelope.get("component") in COMPONENTS,
            "wrong native evidence schema/component")
    require(envelope.get("capture_status") == "untrusted-observation",
            "evidence cannot self-assert native acceptance")
    require(not any(k in envelope for k in ("approved", "rights_approved", "native_accepted")),
            "evidence must not assert authorization")
    component = envelope["component"]
    drafts = Path(drafts).resolve(strict=True)
    root = drafts / component
    upstream = ast.literal_eval((root / "upstream.py").read_text())
    source_sha = upstream.get("sha256") or upstream["source"]["sha256"]
    require(envelope.get("source_archive_sha256") == source_sha,
            "selected source archive differs from draft")
    contract = ast.literal_eval((root / "stages/final/produce-manifest.py").read_text())
    ledger = json_file(drafts / "rights-admission-evidence.json")
    require(not ledger["rights_approved"] and not ledger["canonical_admitted"],
            "source evidence cannot approve graphics")
    rights = dict(ledger["components"][component])
    license_record = ast.literal_eval((root / "license.py").read_text())
    require(license_record["status"] == "unresolved",
            "source verifier cannot consume approved rights as authority")
    rights["_original_member_hashes"] = {item["path"]: item["sha256"]
                                        for item in license_record["evidence"]}
    sidecars = load_sidecars(folder, envelope)
    roots = roots_from(envelope)
    number = commands_and_objects(sidecars, roots, envelope)
    inventory = installed_files(sidecars["installed_inventory"], roots["destdir"],
                                contract["required"])
    elfcount, edges = elf_and_libraries(sidecars, roots, inventory)
    noticenum = notices(sidecars["delivered_notices"], roots["destdir"], inventory, rights)
    return {"schema": "zog-mesa-evidence-consistency-result-v1", "component": component,
            "status": "evidence-consistent-not-native-accepted",
            "compile_units": number, "installed_files": len(inventory),
            "elf_objects": elfcount, "linked_dependencies": edges,
            "original_notices": noticenum, "native_accepted": False,
            "source_archives_independently_accepted": False,
            "redistribution_authorized": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", required=True, type=Path)
    p.add_argument("--drafts", type=Path, default=Path(__file__).resolve().parents[1] /
                   "project/graphics-drafts")
    args = p.parse_args()
    print(json.dumps(verify(args.bundle, args.drafts), sort_keys=True))


if __name__ == "__main__":
    main()
