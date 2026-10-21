"""Linux credential-bearing reply and disconnect containment tests."""
import json
import os
import socket
import struct

import pytest

from zog.image_build.post_install_progress_broker import (
    TRANSPORT_AUTH,
    WIRE,
    _frame,
    respond_one,
)


pytestmark = pytest.mark.skipif(
    not hasattr(socket, "SCM_CREDENTIALS")
    or not hasattr(socket, "SO_PASSCRED")
    or not hasattr(socket.socket, "sendmsg"),
    reason="Linux AF_UNIX SCM_CREDENTIALS required",
)


class Broker:
    authorized_uid = os.geteuid()

    def handle(self, request):
        assert request == {
            "schema": WIRE,
            "operation": "snapshot",
            "after": None,
            "limit": 4,
        }
        return {"transport_test": True}


def request_bytes():
    return _frame({
        "schema": WIRE,
        "operation": "snapshot",
        "after": None,
        "limit": 4,
    }, 4096)


def exact(conn, count):
    parts = []
    while count:
        value = conn.recv(count)
        assert value
        parts.append(value)
        count -= len(value)
    return b"".join(parts)


def authenticated_reply(conn):
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    first, ancillary, _flags, _address = conn.recvmsg(
        4, socket.CMSG_SPACE(struct.calcsize("3i"))
    )
    credentials = []
    for level, kind, data in ancillary:
        if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS:
            credentials.append(struct.unpack("3i", data[:struct.calcsize("3i")]))
    assert len(credentials) == 1
    header = first + exact(conn, 4 - len(first))
    count = struct.unpack("!I", header)[0]
    return credentials[0], json.loads(exact(conn, count))


def test_transport_contract_authenticates_actual_reply_sender_not_listener_owner():
    assert TRANSPORT_AUTH == "image-build-post-install-progress-linux-credentials-v1"
    server, client = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.sendall(request_bytes())
        assert respond_one(Broker(), server) is True
        credentials, reply = authenticated_reply(client)
        assert credentials == (os.getpid(), os.geteuid(), os.getegid())
        assert reply == {"ok": True, "result": {"transport_test": True}}
    finally:
        client.close()


def test_authorized_disconnect_before_request_is_contained_and_next_client_served():
    server, client = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    client.close()
    assert respond_one(Broker(), server) is False

    server, client = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.sendall(request_bytes())
        assert respond_one(Broker(), server) is True
        _credentials, reply = authenticated_reply(client)
        assert reply["ok"] is True
    finally:
        client.close()


def test_authorized_disconnect_during_reply_is_contained():
    class Disconnected:
        def __init__(self):
            self.incoming = bytearray(request_bytes())

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def settimeout(self, _timeout):
            pass

        def getsockopt(self, level, option, size):
            assert level == socket.SOL_SOCKET
            assert option == socket.SO_PEERCRED
            return struct.pack("3i", os.getpid(), os.geteuid(), os.getegid())

        def recv(self, count):
            value = bytes(self.incoming[:count])
            del self.incoming[:count]
            return value

        def sendmsg(self, *_args):
            raise BrokenPipeError()

        def sendall(self, _data):
            raise AssertionError("sendall must not follow failed credential send")

    assert respond_one(Broker(), Disconnected()) is False
