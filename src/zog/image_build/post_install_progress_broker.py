"""Fixed-identity AF_UNIX read-only broker for image-build post-install progress."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import struct

from .post_install_progress import (
    SCHEMA,
    producer_source,
    snapshot,
    validate_snapshot_configuration,
)

WIRE = "image-build-post-install-progress-rpc-v2"
TRANSPORT_AUTH = "image-build-post-install-progress-linux-credentials-v1"
MAX_REQUEST = 4096
MAX_RESPONSE = 65536


class ProgressBrokerError(ValueError):
    pass


def _peer_uid(conn):
    raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    _pid, uid, _gid = struct.unpack("3i", raw)
    return uid


def _sender_credentials():
    if not hasattr(socket, "SCM_CREDENTIALS"):
        raise ProgressBrokerError("kernel credential messages required")
    return struct.pack("3i", os.getpid(), os.geteuid(), os.getegid())


def _send_authenticated_frame(conn, data):
    """Send one reply with kernel-validated broker credentials on its first byte."""
    if not hasattr(conn, "sendmsg") or not hasattr(socket, "SCM_CREDENTIALS"):
        raise ProgressBrokerError("kernel credential messages required")
    credentials = [(
        socket.SOL_SOCKET,
        socket.SCM_CREDENTIALS,
        _sender_credentials(),
    )]
    try:
        sent = conn.sendmsg([data[:1]], credentials)
        if sent != 1:
            raise ProgressBrokerError("short credential-bearing progress reply")
        conn.sendall(data[1:])
        return True
    except OSError:
        # A disconnected authorized consumer is a per-connection outcome. It must
        # never terminate the long-lived socket-activated broker.
        return False


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


def _boot_id():
    try:
        value = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError as error:
        raise ProgressBrokerError("current boot identity is unavailable") from error
    try:
        import uuid
        parsed = str(uuid.UUID(value))
    except (ValueError, AttributeError) as error:
        raise ProgressBrokerError("invalid current boot identity") from error
    if parsed != value:
        raise ProgressBrokerError("noncanonical current boot identity")
    return value


class PostInstallProgressBroker:
    def __init__(self, state_dir, *, applications, authorized_uid,
                 source_repository, source_revision, boot_id=None):
        state=Path(state_dir)
        if not state.is_absolute() or state == Path("/") or ".." in state.parts:
            raise ProgressBrokerError("fixed canonical image-build state required")
        state=state.resolve()
        if type(authorized_uid) is not int or not 1 <= authorized_uid < 2**31:
            raise ProgressBrokerError("invalid progress observer UID")
        values=tuple(sorted(set(applications)))
        if not values:
            raise ProgressBrokerError("fixed application allowlist required")
        source = producer_source(source_repository, source_revision)
        boot = _boot_id() if boot_id is None else boot_id
        # Cold start validates only immutable broker configuration. The first
        # consumer request performs the full durable publication/artifact/view/
        # rootfs verification exactly once, and every later request performs it
        # again. No provenance result is cached across requests.
        try:
            values, source, boot = validate_snapshot_configuration(
                applications=values,
                producer_source=source,
                producer_boot_id=boot,
            )
        except Exception as error:
            raise ProgressBrokerError(
                "invalid application allowlist or producer binding"
            ) from error
        self.source=source
        self.boot_id=boot
        self.state=state
        self.applications=tuple(values)
        self.authorized_uid=authorized_uid

    def handle(self, request):
        if request.get("schema") != WIRE or request.get("operation") != "snapshot":
            raise ProgressBrokerError("progress endpoint is strictly read-only")
        if set(request) != {"schema","operation","after","limit"}:
            raise ProgressBrokerError("invalid progress request shape")
        return snapshot(
            self.state,
            applications=self.applications,
            producer_source=self.source,
            producer_boot_id=self.boot_id,
            after=request["after"],
            limit=request["limit"],
        )


def respond_one(broker, conn):
    with conn:
        conn.settimeout(20)
        if _peer_uid(conn) != broker.authorized_uid:
            return False
        try:
            result=broker.handle(_decode(conn))
            payload={"ok":True,"result":result}
            data=_frame(payload,MAX_RESPONSE)
        except Exception:
            data=_frame({"ok":False,"error":"progress-unavailable"},4096)
        return _send_authenticated_frame(conn, data)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--authorized-uid", type=int, required=True)
    parser.add_argument("--application", action="append", required=True)
    parser.add_argument("--source-repository", required=True)
    parser.add_argument("--source-revision", required=True)
    args=parser.parse_args(argv)
    if not hasattr(socket, "SCM_CREDENTIALS") or not hasattr(socket.socket, "sendmsg"):
        raise ProgressBrokerError("Linux credential-bearing AF_UNIX replies required")
    if os.geteuid() == 0 or os.geteuid() == args.authorized_uid:
        raise ProgressBrokerError("distinct nonroot producer and consumer identities required")
    broker=PostInstallProgressBroker(
        args.state_dir,
        applications=args.application,
        authorized_uid=args.authorized_uid,
        source_repository=args.source_repository,
        source_revision=args.source_revision,
    )
    with _activated_socket() as listener:
        while True:
            conn,_=listener.accept()
            respond_one(broker,conn)


if __name__=="__main__":
    main()
