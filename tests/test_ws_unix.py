from __future__ import annotations

import base64
import hashlib
import socket
import struct
import threading
from pathlib import Path

import pytest

from codex_auto_continuer.errors import ProtocolError
from codex_auto_continuer.ws_unix import UnixWebSocket, _GUID


def server_frame(opcode: int, payload: bytes, *, fin: bool = True) -> bytes:
    first = (0x80 if fin else 0) | opcode
    n = len(payload)
    if n < 126:
        return bytes([first, n]) + payload
    if n <= 0xFFFF:
        return bytes([first, 126]) + struct.pack("!H", n) + payload
    return bytes([first, 127]) + struct.pack("!Q", n) + payload


def test_fragmented_text_and_ping():
    a, b = socket.socketpair()
    ws = UnixWebSocket(a)
    try:
        b.sendall(
            server_frame(0x1, b'{"a', fin=False)
            + server_frame(0x9, b"hi")
            + server_frame(0x0, b'":1', fin=False)
            + server_frame(0x0, b"}", fin=True)
        )
        assert ws.recv_text() == '{"a":1}'
        # Pong is a masked client frame; enough to verify opcode.
        header = b.recv(2)
        assert header[0] & 0x0F == 0xA
        assert header[1] & 0x80
    finally:
        ws.close(); b.close()


def test_server_masked_frame_rejected():
    a, b = socket.socketpair()
    ws = UnixWebSocket(a)
    try:
        b.sendall(bytes([0x81, 0x80]) + b"abcd")
        with pytest.raises(ProtocolError, match="masked"):
            ws.recv_text()
    finally:
        ws.close(); b.close()


def test_binary_application_message_rejected():
    a, b = socket.socketpair()
    ws = UnixWebSocket(a)
    try:
        b.sendall(server_frame(0x2, b"abc"))
        with pytest.raises(ProtocolError, match="binary"):
            ws.recv_text()
    finally:
        ws.close(); b.close()


def test_handshake_preserves_prefetched_frame(unix_path, unix_listener):
    path = unix_path
    listener = unix_listener(path)
    def serve():
        conn, _ = listener.accept()
        request = b""
        while b"\r\n\r\n" not in request:
            request += conn.recv(4096)
        key = None
        for line in request.decode("ascii").split("\r\n"):
            if line.lower().startswith("sec-websocket-key:"):
                key = line.split(":", 1)[1].strip()
        accept = base64.b64encode(hashlib.sha1((key + _GUID).encode()).digest()).decode()
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: keep-alive, Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        ).encode("ascii") + server_frame(0x1, b"hello")
        conn.sendall(response)
        conn.close()
    thread = threading.Thread(target=serve); thread.start()
    try:
        ws = UnixWebSocket.connect(path, 2)
        assert ws.recv_text() == "hello"
        ws.close()
    finally:
        thread.join(timeout=2); listener.close()
