"""Fixed-identity AF_UNIX read-only broker for image-build post-install progress."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import struct

from .post_install_progress import SCHEMA, snapshot

WIRE = "image-build-post-install-progress-rpc-v1"
MAX_REQUEST = 4096
MAX_RESPONSE = 65536


class ProgressBrokerError(ValueError):
    pass


def _peer_uid(conn):
    raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    _pid, uid, _gid = struct.unpack("3i", raw)
    return uid


def _frame(value, maximum):
    data=json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    if not 0 < len(data) <= maximum:
        raise ProgressBrokerError("progress frame too large")
    return struct.pack("!I", len(data))+data


def _read_exact(conn, count):
    chunks=[]
    remaining=count
    while remaining:
        value=conn.recv(remaining)
        if not value:
            raise ProgressBrokerError("truncated progress request")
        chunks.append(value)
        remaining-=len(value)
    return b"".join(chunks)


def _decode(conn):
    count=struct.unpack("!I", _read_exact(conn,4))[0]
    if not 0 < count <= MAX_REQUEST:
        raise ProgressBrokerError("invalid progress request length")
    try:
        value=json.loads(_read_exact(conn,count))
    except (ValueError,UnicodeError):
        raise ProgressBrokerError("invalid progress request") from None
    if type(value) is not dict:
        raise ProgressBrokerError("invalid progress request")
    return value


@contextmanager
def _activated_socket():
    if os.environ.get("LISTEN_PID") != str(os.getpid()) or os.environ.get("LISTEN_FDS") != "1":
        raise ProgressBrokerError("exactly one systemd-activated progress socket required")
    sock=socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        yield sock
    finally:
        sock.close()


class PostInstallProgressBroker:
    def __init__(self, state_dir, *, applications, authorized_uid):
        state=Path(state_dir)
        if not state.is_absolute() or state == Path("/") or ".." in state.parts:
            raise ProgressBrokerError("fixed canonical image-build state required")
        state=state.resolve()
        if type(authorized_uid) is not int or not 1 <= authorized_uid < 2**31:
            raise ProgressBrokerError("invalid progress observer UID")
        values=tuple(sorted(set(applications)))
        if not values:
            raise ProgressBrokerError("fixed application allowlist required")
        # Validate the fixed allowlist once. Missing producer state is valid.
        try:
            snapshot(state, applications=values, limit=1)
        except Exception as error:
            raise ProgressBrokerError("invalid application allowlist or state root") from error
        self.state=state
        self.applications=values
        self.authorized_uid=authorized_uid

    def handle(self, request):
        if request.get("schema") != WIRE or request.get("operation") != "snapshot":
            raise ProgressBrokerError("progress endpoint is strictly read-only")
        if set(request) != {"schema","operation","after","limit"}:
            raise ProgressBrokerError("invalid progress request shape")
        return snapshot(
            self.state, applications=self.applications,
            after=request["after"], limit=request["limit"],
        )


def respond_one(broker, conn):
    with conn:
        conn.settimeout(20)
        if _peer_uid(conn) != broker.authorized_uid:
            return
        try:
            result=broker.handle(_decode(conn))
            payload={"ok":True,"result":result}
            data=_frame(payload,MAX_RESPONSE)
        except Exception:
            data=_frame({"ok":False,"error":"progress-unavailable"},4096)
        conn.sendall(data)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--authorized-uid", type=int, required=True)
    parser.add_argument("--application", action="append", required=True)
    args=parser.parse_args(argv)
    if os.geteuid() == 0 or os.geteuid() == args.authorized_uid:
        raise ProgressBrokerError("distinct nonroot producer and consumer identities required")
    broker=PostInstallProgressBroker(
        args.state_dir, applications=args.application, authorized_uid=args.authorized_uid
    )
    with _activated_socket() as listener:
        while True:
            conn,_=listener.accept()
            respond_one(broker,conn)


if __name__=="__main__":
    main()
