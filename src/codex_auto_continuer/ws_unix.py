from __future__ import annotations

import base64
import hashlib
import os
import socket
import select
import struct
import time
from pathlib import Path

from .errors import ProtocolError, TransportError
from .uds import connect_socket

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_MAX_HANDSHAKE = 64 * 1024
_MAX_MESSAGE = 16 * 1024 * 1024


class UnixWebSocket:
    def __init__(self, sock: socket.socket, prefetched: bytes = b""):
        self._sock = sock
        self._prefetched = bytearray(prefetched)
        self._closed = False
        self._timeout = sock.gettimeout()
        self._deadline: float | None = None

    def begin_request(self) -> None:
        self._deadline = None if self._timeout is None else time.monotonic() + self._timeout

    def message_ready(self, timeout: float) -> bool:
        if self._prefetched:
            return True
        try:
            return bool(select.select([self._sock], [], [], timeout)[0])
        except (OSError, ValueError) as exc:
            raise TransportError("Codex notification connection is unavailable.") from exc

    def _apply_timeout(self) -> None:
        if self._deadline is not None:
            remaining = self._deadline - time.monotonic()
            if remaining <= 0:
                raise TransportError("Codex app-server exceeded the total RPC deadline.")
            try:
                self._sock.settimeout(remaining)
            except OSError as exc:
                raise TransportError("Codex app-server socket is unavailable while setting its deadline.") from exc

    @classmethod
    def connect(cls, path: Path, timeout: float) -> "UnixWebSocket":
        sock = None
        try:
            sock = connect_socket(path, timeout)
            key = base64.b64encode(os.urandom(16)).decode("ascii")
            request = (
                "GET / HTTP/1.1\r\n"
                "Host: localhost\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                "Sec-WebSocket-Version: 13\r\n\r\n"
            ).encode("ascii")
            sock.sendall(request)
            header, rest = cls._read_handshake(sock)
            cls._validate_handshake(header, key)
            sock.settimeout(timeout)
            return cls(sock, rest)
        except (OSError, ValueError, ProtocolError, TransportError) as exc:
            if sock is not None:
                sock.close()
            if isinstance(exc, ProtocolError):
                raise
            if isinstance(exc, ValueError):
                raise ProtocolError(f"Unsupported Codex socket path {path}: {exc}. Use a shorter Codex home path.") from exc
            raise TransportError(f"Could not connect to Codex app-server socket {path}: {exc}") from exc

    @staticmethod
    def _read_handshake(sock: socket.socket) -> tuple[bytes, bytes]:
        data = bytearray()
        marker = b"\r\n\r\n"
        timeout = sock.gettimeout()
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            pos = data.find(marker)
            if pos >= 0:
                end = pos + len(marker)
                if end > _MAX_HANDSHAKE:
                    raise ProtocolError("Codex WebSocket handshake exceeded 64 KiB.")
                return bytes(data[:end]), bytes(data[end:])
            if len(data) >= _MAX_HANDSHAKE:
                raise ProtocolError("Codex WebSocket handshake exceeded 64 KiB.")
            try:
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError("Total WebSocket handshake deadline exceeded.")
                    sock.settimeout(remaining)
                chunk = sock.recv(4096)
            except OSError as exc:
                raise TransportError(f"Codex WebSocket handshake read failed: {exc}") from exc
            if not chunk:
                raise TransportError("Codex app-server closed during WebSocket handshake.")
            data.extend(chunk)

    @staticmethod
    def _validate_handshake(header: bytes, key: str) -> None:
        try:
            lines = header.decode("iso-8859-1").split("\r\n")
        except UnicodeDecodeError as exc:
            raise ProtocolError("Invalid WebSocket HTTP handshake encoding.") from exc
        if not lines or " 101 " not in f" {lines[0]} ":
            raise ProtocolError(f"Codex app-server rejected WebSocket upgrade: {lines[0] if lines else '<empty>'}")
        headers: dict[str, str] = {}
        for line in lines[1:]:
            if not line:
                continue
            if ":" not in line:
                raise ProtocolError(f"Malformed WebSocket handshake header: {line!r}")
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()
        expected = base64.b64encode(hashlib.sha1((key + _GUID).encode("ascii")).digest()).decode("ascii")
        if headers.get("sec-websocket-accept") != expected:
            raise ProtocolError("Codex app-server returned an invalid Sec-WebSocket-Accept value.")
        if headers.get("upgrade", "").lower() != "websocket":
            raise ProtocolError("Codex app-server WebSocket handshake omitted Upgrade: websocket.")
        connection_tokens = {x.strip().lower() for x in headers.get("connection", "").split(",")}
        if "upgrade" not in connection_tokens:
            raise ProtocolError("Codex app-server WebSocket handshake omitted Connection: Upgrade.")

    def _read_exact(self, count: int) -> bytes:
        self._apply_timeout()
        out = bytearray()
        if self._prefetched:
            take = min(count, len(self._prefetched))
            out.extend(self._prefetched[:take])
            del self._prefetched[:take]
        while len(out) < count:
            try:
                self._apply_timeout()
                chunk = self._sock.recv(count - len(out))
            except socket.timeout as exc:
                raise TransportError("Timed out waiting for Codex app-server.") from exc
            except OSError as exc:
                raise TransportError(f"Codex app-server socket read failed: {exc}") from exc
            if not chunk:
                raise TransportError("Codex app-server closed the connection.")
            out.extend(chunk)
        return bytes(out)

    def _read_frame(self) -> tuple[bool, int, bytes]:
        first, second = self._read_exact(2)
        fin = bool(first & 0x80)
        rsv = first & 0x70
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F
        if rsv:
            raise ProtocolError("Codex WebSocket used unsupported RSV bits.")
        if masked:
            raise ProtocolError("Codex server sent a masked WebSocket frame.")
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            raw = self._read_exact(8)
            length = struct.unpack("!Q", raw)[0]
            if length & (1 << 63):
                raise ProtocolError("Codex WebSocket frame has an invalid 64-bit length.")
        if opcode >= 0x8:
            if not fin or length > 125:
                raise ProtocolError("Invalid fragmented/oversized WebSocket control frame.")
        if length > _MAX_MESSAGE:
            raise ProtocolError(f"Codex WebSocket frame exceeded {_MAX_MESSAGE} bytes.")
        return fin, opcode, self._read_exact(length)

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        if self._closed:
            raise TransportError("Cannot write to a closed Codex WebSocket.")
        if len(payload) > _MAX_MESSAGE:
            raise ProtocolError(f"Outgoing WebSocket message exceeded {_MAX_MESSAGE} bytes.")
        first = 0x80 | opcode
        mask = os.urandom(4)
        length = len(payload)
        if length < 126:
            header = bytes([first, 0x80 | length])
        elif length <= 0xFFFF:
            header = bytes([first, 0x80 | 126]) + struct.pack("!H", length)
        else:
            header = bytes([first, 0x80 | 127]) + struct.pack("!Q", length)
        masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
        try:
            self._apply_timeout()
            self._sock.sendall(header + mask + masked)
        except OSError as exc:
            raise TransportError(f"Codex app-server socket write failed: {exc}") from exc

    def send_text(self, text: str) -> None:
        self._send_frame(0x1, text.encode("utf-8"))

    def recv_text(self) -> str:
        chunks = bytearray()
        message_opcode: int | None = None
        while True:
            fin, opcode, payload = self._read_frame()
            if opcode == 0x8:
                self._closed = True
                raise TransportError("Codex app-server closed the WebSocket.")
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode in (0x1, 0x2):
                if message_opcode is not None:
                    raise ProtocolError("Codex WebSocket started a new data message before finishing the previous one.")
                message_opcode = opcode
                chunks.extend(payload)
            elif opcode == 0x0:
                if message_opcode is None:
                    raise ProtocolError("Codex WebSocket sent an orphan continuation frame.")
                chunks.extend(payload)
            else:
                raise ProtocolError(f"Unsupported WebSocket opcode 0x{opcode:x}.")
            if len(chunks) > _MAX_MESSAGE:
                raise ProtocolError(f"Codex WebSocket message exceeded {_MAX_MESSAGE} bytes.")
            if fin:
                if message_opcode == 0x2:
                    raise ProtocolError("Codex app-server sent a binary application message; JSON text was expected.")
                try:
                    return chunks.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ProtocolError("Codex app-server sent invalid UTF-8 text.") from exc

    def close(self) -> None:
        if self._closed:
            try:
                self._sock.close()
            finally:
                return
        try:
            self._deadline = time.monotonic() + 1
            self._send_frame(0x8, b"")
        except Exception:
            pass
        finally:
            self._closed = True
            self._sock.close()

    def abort(self) -> None:
        """Wake an exclusive observer's blocking read without racing a close frame."""
        self._closed = True
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            self._sock.close()
