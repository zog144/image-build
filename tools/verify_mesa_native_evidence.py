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
            "elf_dependencies", "library_provenance", "delivered_notices",
            "implicit_inputs", "link_commands")
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
    values = list(roots.values())
    require(not any(a in b.parents or b in a.parents
                    for i, a in enumerate(values) for b in values[i + 1:]),
            "overlapping native capture roots")
    return roots


def compiler_flags(argv, roots, directory):
    require(isinstance(argv, list) and all(isinstance(x, str) and x for x in argv),
            "invalid compiler argv")
    require(not any(x.startswith("@") for x in argv), "response file needs independent expansion")
    require(argv.count("-c") == 1 and argv.count("-o") == 1,
            "ambiguous compiler source/output switches")
    require(argv.count("-MF") == 1,
            "ambiguous compiler depfile switches")
    # This source verifier cannot inspect compiler driver plugins, alternate
    # sysroots, injected forced headers or opaque option forwarding. Hold them.
    forbidden = ("-include", "-imacros", "-isysroot", "--sysroot",
                 "-sysroot", "-resource-dir", "-fmodule-", "-fplugin",
                 "-specs", "-B", "-Xclang", "-Xlinker", "-Wl,",
                 "-plugin", "-load", "-T", "-wrapper", "-Wp,",
                 "-Wa,", "-Xpreprocessor", "-fprofile-use", "-fprofile-instr-use",
                 "-F", "-iframework", "-include-pch", "-fmodule-file",
                 "-fmodule-map-file", "-save-temps")
    require(not any(x.startswith(forbidden) for x in argv),
            "unsupported implicit or linker/compiler input")
    prefixes = ("-I", "-L", "-isystem", "-iquote", "-idirafter")
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-c", "-o", "-MF", "-MT", "-MQ"):
            i += 1
            require(i < len(argv), "compiler option missing value")
            i += 1
            continue
        require(not arg.startswith(("-MF", "-MT", "-MQ")),
                "unreviewed concatenated dependency option")
        if arg in prefixes:
            i += 1
            require(i < len(argv), "missing compiler path option")
            path = argv[i]
        else:
            prefix = next((p for p in prefixes if arg.startswith(p) and len(arg) > len(p)), None)
            path = arg[len(prefix):] if prefix else None
        if path is not None:
            candidate = Path(path)
            candidate = candidate if candidate.is_absolute() else directory / candidate
            require(any(within_if_exists(candidate, root) for root in roots),
                    "compiler Host include/library directory: " + path)
        require(not arg.startswith(("-Wl,", "-fplugin", "-B/")),
                "opaque linker or compiler plugin argument requires review")
        if path is None and not arg.startswith("-"):
            raise EvidenceError("additional unreviewed compiler input: " + arg)
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
        require("directory" in cmd and "file" in cmd,
                "compile database lacks directory/file")
        require(("arguments" in cmd) != ("command" in cmd),
                "compile database must specify exactly one argument representation")
        argv = cmd.get("arguments")
        if argv is None:
            require(isinstance(cmd["command"], str), "invalid shell command")
            argv = shlex.split(cmd["command"])
            require(not any(c in cmd["command"] for c in (";", "|", "\n", "`", "$(", "&", "<", ">", "$", "\r")),
                    "shell expansion in compile database must be reviewed")
        require(argv and argv[0].startswith("/") and "-c" in argv and "-o" in argv,
                "unstructured compiler invocation")
        directory = Path(cmd["directory"]).resolve(strict=True)
        require(within(directory, roots["build"]) == directory and directory.is_dir(),
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
        # CMake/Meson may omit the optional 'output' member and use relative
        # command paths. Normalize against the declared compilation directory.
        def normalize(value):
            require(isinstance(value, str) and value, "invalid compiler file path")
            p = Path(value)
            return p.resolve(strict=True) if p.is_absolute() else (directory / p).resolve(strict=True)
        require(normalize(arg_source) == normalize(cmd["file"]),
                "compile command source mismatch")
        if "output" in cmd:
            require(normalize(arg_output) == normalize(cmd["output"]),
                    "compile command output mismatch")
        compiler_flags(argv[1:], tuple(roots.values()), directory)
        key = (str(normalize(cmd["file"])), str(normalize(arg_output)))
        require(key in mapped and key not in seen, "missing or duplicated source-object mapping")
        seen.add(key)
    require(seen == set(mapped), "unobserved mapped compiler output")
    # Reported-to-reported agreement alone is insufficient: an omitted .o
    # could contain unreviewed code and later enter a shared library.
    physical = set()
    for file in roots["build"].rglob("*"):
        if file.is_symlink():
            require(within_if_exists(file, roots["build"]),
                    "build object symlink escapes capture")
        if file.is_file() and file.suffix in (".o", ".obj"):
            physical.add(str(within(file, roots["build"])))
    recorded = {pair[1] for pair in mapped}
    require(physical == recorded, "unreported or missing build object")
    return len(seen)


def file_digest_matches(path, compilers):
    if not isinstance(compilers, list) or len(compilers) > 32:
        return False
    for row in compilers:
        if (isinstance(row, dict) and set(row) == {"path", "sha256"}
                and row["path"] == str(path) and sha(row["sha256"])):
            return digest(path.read_bytes()) == row["sha256"]
    return False


def verify_implicit_inputs(sidecars, roots):
    """Compare full -MD compiler depfile bytes with independently inventoried inputs.

    -MMD excludes system headers and is inadequate here. This still checks
    only the submitted capture, not whether a compiler truly produced it.
    """
    commands = sidecars["compile_commands"]
    mapped = sidecars["source_objects"]
    evidence = sidecars["implicit_inputs"]
    require(len(evidence) == len(commands), "implicit dependency coverage incomplete")
    by_obj = {}
    for row in evidence:
        require(set(row) == {"object", "depfile", "depfile_sha256", "inputs"},
                "incomplete implicit-input record")
        object_path = (roots["build"] / relative(row["object"])).resolve(strict=True)
        require(object_path not in by_obj, "duplicated implicit-input record")
        by_obj[object_path] = row
        file_hash(roots["build"], row["depfile"], row["depfile_sha256"])
        text = actual_file(roots["build"], row["depfile"]).read_text()
        require("$" not in text and "\x00" not in text,
                "unsupported dependency expansion")
        text = text.replace("\\\n", " ")
        require(text.count(":") == 1, "unsupported depfile grammar")
        target, deps = text.split(":", 1)
        words = shlex.split(deps)
        require(words and len(words) == len(set(words)),
                "missing/duplicated implicit dependency")
        target_path = Path(target.strip())
        target_path = (roots["build"] / target_path).resolve(strict=True) if not target_path.is_absolute() else target_path.resolve(strict=True)
        require(target_path == object_path, "depfile object mismatch")
        claimed = set()
        for item in row["inputs"]:
            require(set(item) == {"root", "path", "sha256"}
                    and item["root"] in ("source", "build", "software"),
                    "invalid implicit dependency origin")
            file_hash(roots[item["root"]], item["path"], item["sha256"])
            claimed.add(str(actual_file(roots[item["root"]], item["path"])))
        require(len(claimed) == len(row["inputs"]), "duplicated implicit input")
        actual = set()
        for word in words:
            path = Path(word)
            path = path if path.is_absolute() else roots["build"] / path
            path = path.resolve(strict=True)
            require(any(path == r or r in path.parents
                        for r in (roots["source"], roots["build"], roots["software"])),
                    "Host implicit compiler dependency")
            actual.add(str(path))
        require(actual == claimed, "depfile/input digest inventory mismatch")
    for cmd in commands:
        argv = cmd.get("arguments")
        if argv is None:
            argv = shlex.split(cmd["command"])
        require("-MD" in argv and "-MMD" not in argv,
                "full system-inclusive -MD dependency capture required")
        require(argv.count("-MF") == 1 and argv.index("-MF") + 1 < len(argv),
                "unreviewed or absent depfile flag")
        depfile = Path(argv[argv.index("-MF") + 1])
        directory = Path(cmd["directory"]).resolve(strict=True)
        depfile = depfile if depfile.is_absolute() else directory / depfile
        output = Path(argv[argv.index("-o") + 1])
        output = output if output.is_absolute() else directory / output
        key = output.resolve(strict=True)
        require(key in by_obj, "implicit inputs omit compile object")
        expected = roots["build"] / relative(by_obj[key]["depfile"])
        require(depfile.resolve(strict=True) == expected.resolve(strict=True),
                "compiler depfile path differs from captured bytes")
    require({(roots["build"] / relative(r["object"])).resolve(strict=True)
             for r in mapped} == set(by_obj), "unmapped implicit compiler inputs")


def verify_link_commands(sidecars, roots, envelope):
    """Require explicit link input and output bytes; reject opaque link stages."""
    links = sidecars["link_commands"]
    binaries = sidecars["elf_dependencies"]
    objects = sidecars["source_objects"]
    require(len(links) == len(binaries), "ELF/link command coverage incomplete")
    object_hashes = {str((roots["build"] / relative(row["object"])).resolve(strict=True)):
                     row["object_sha256"] for row in objects}
    seen = set()
    for row in links:
        require(set(row) == {"installed_path", "output", "output_sha256",
                             "arguments", "inputs"}, "incomplete link command record")
        installed = relative(row["installed_path"]).as_posix()
        require(installed in {e["path"] for e in binaries} and installed not in seen,
                "missing/duplicate linked output")
        seen.add(installed)
        file_hash(roots["build"], row["output"], row["output_sha256"])
        file_hash(roots["destdir"], installed, row["output_sha256"])
        argv = row["arguments"]
        require(isinstance(argv, list) and len(argv) >= 5
                and all(isinstance(a, str) and a for a in argv),
                "invalid linker command")
        exe = Path(argv[0])
        require(exe.is_file() and within_if_exists(exe, roots["software"])
                and file_digest_matches(exe, envelope["compilers"]),
                "unapproved linker bytes")
        require(argv.count("-o") == 1 and argv.index("-o") + 1 < len(argv),
                "link command missing explicit output")
        named_output = Path(argv[argv.index("-o") + 1])
        if not named_output.is_absolute():
            named_output = roots["build"] / named_output
        require(named_output.resolve(strict=True) ==
                (roots["build"] / relative(row["output"])).resolve(strict=True),
                "linker output differs from recorded object")
        require("-shared" in argv, "unsupported executable link/interpreter mode")
        require(not any(a.startswith(("@", "-Wl,", "-Xlinker", "-T", "--script",
                                     "--sysroot", "-fuse-ld", "-plugin", "-l",
                                     "-L", "-B", "-fplugin", "-specs", "-Wl"))
                        for a in argv[1:]), "unsupported opaque linker input")
        allowed_flags = {"-shared", "-fPIC", "-pthread"}
        actual_inputs = []
        skip_next = False
        for i, item in enumerate(argv[1:], 1):
            if skip_next:
                skip_next = False
                continue
            if item == "-o":
                skip_next = True
                continue
            if item in allowed_flags:
                continue
            require(not item.startswith("-"), "unsupported linker flag")
            path = Path(item)
            path = path if path.is_absolute() else roots["build"] / path
            path = path.resolve(strict=True)
            require(within_if_exists(path, roots["build"]),
                    "Host or unsupported linker input")
            require(path.suffix in (".o", ".obj"),
                    "archive/linker script/opaque library input not admitted")
            actual_inputs.append(str(path))
        claimed = []
        for item in row["inputs"]:
            require(set(item) == {"root", "path", "sha256"} and item["root"] == "build",
                    "unreviewed linker input provenance")
            file_hash(roots["build"], item["path"], item["sha256"])
            path = str((roots["build"] / relative(item["path"])).resolve(strict=True))
            require(object_hashes.get(path) == item["sha256"],
                    "linker object has no compilation source provenance")
            claimed.append(path)
        require(len(actual_inputs) == len(set(actual_inputs))
                and len(claimed) == len(set(claimed))
                and set(actual_inputs) == set(claimed)
                and claimed, "unreported/missing linker inputs")
    require(seen == {e["path"] for e in binaries},
            "unlinked ELF installed output")


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
        if typ == 3:
            raise EvidenceError("PT_INTERP requires independently attested loader provenance")
    require(dynamic is not None and dynamic[1] % 16 == 0, "ELF lacks PT_DYNAMIC")
    entries = []
    for offset in range(dynamic[0], dynamic[0] + dynamic[1], 16):
        tag, val = struct.unpack_from("<qQ", data, offset)
        if tag == 0:
            break
        entries.append((tag, val))
    else:
        raise EvidenceError("unterminated ELF dynamic table")
    # Extra implicit loader inputs are not captured by DT_NEEDED.
    unsupported = {0x7fffffff, 0x7ffffffd, 0x6ffffefb, 0x6ffffefc}
    require(not any(t in unsupported for t, _ in entries),
            "unsupported ELF audit/filter dependency")
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
    require(all(n and n not in (".", "..") and
                "/" not in n and "\\\\" not in n for n in needed),
            "DT_NEEDED contains a path or invalid library name")
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
    # Every ELF physically installed in DESTDIR must be accounted for.
    # Otherwise a malicious evidence producer could simply omit a binary
    # with unresolved DT_NEEDED or a Host RPATH from the report.
    observed_elf = set()
    for name, item in inventory.items():
        if item["type"] != "file":
            continue
        path = actual_file(roots["destdir"], name)
        with path.open("rb") as fd:
            if fd.read(4) == b"\x7fELF":
                observed_elf.add(name)
    require(tracked == observed_elf, "unreported installed ELF object")
    mapped = set()
    for row in links:
        require(set(row) == {"consumer", "needed", "root", "path", "sha256"},
                "incomplete library provenance record")
        key = (row["consumer"], row["needed"])
        require(relative(row["path"]).name == row["needed"],
                "resolved library filename differs from DT_NEEDED")
        require(key in edges and key not in mapped, "unmatched/duplicate library resolution")
        mapped.add(key)
        require(row["root"] in ("destdir", "software"), "Host library origin")
        file_hash(roots[row["root"]], row["path"], row["sha256"])
        target = actual_file(roots[row["root"]], row["path"])
        # This is only a conservative modeled lookup, NOT proof of what the
        # authenticated runtime loader actually chose.
        consumer = row["consumer"]
        report = next(e for e in binaries if e["path"] == consumer)
        root = roots[row["root"]]
        base = roots["destdir"] / relative(consumer)
        directories = [roots[k] / part for k in ("software", "destdir")
                       for part in ("lib", "lib64", "usr/lib", "usr/lib64")]
        if row["root"] == "destdir":
            for token in report["rpath"] + report["runpath"]:
                if token == "$ORIGIN" or token.startswith("$ORIGIN/"):
                    directories.append(base.parent / token.replace("$ORIGIN", ".", 1))
        require(any(within_if_exists(target.parent, root) and
                    target.parent == d.resolve(strict=False) for d in directories),
                "library provider outside modeled loader search")
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
    verify_implicit_inputs(sidecars, roots)
    verify_link_commands(sidecars, roots, envelope)
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
