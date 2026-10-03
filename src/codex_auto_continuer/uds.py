from __future__ import annotations

import os
import select
import socket
import struct
from pathlib import Path


def windows_address(path: Path) -> bytes:
    encoded = os.fsencode(path)
    if b"\0" in encoded or len(encoded) >= 108:
        raise ValueError("Windows Unix socket path must fit in 107 UTF-8 bytes and contain no NUL.")
    return struct.pack("=H108s", 1, encoded)


def windows_socket_call(name: str, sock: socket.socket, path: Path) -> None:
    # CPython on Windows can create AF_UNIX (1), but cannot marshal sockaddr_un.
    # Only address marshalling uses Winsock; Python owns the socket and all I/O.
    import ctypes

    winsock = ctypes.WinDLL("ws2_32")
    call = getattr(winsock, name)
    call.argtypes = [ctypes.c_size_t, ctypes.c_void_p, ctypes.c_int]
    call.restype = ctypes.c_int
    winsock.WSAGetLastError.restype = ctypes.c_int
    address = windows_address(path)
    if call(sock.fileno(), address, len(address)) != 0:
        error = winsock.WSAGetLastError()
        raise OSError(error, ctypes.FormatError(error))


def connect_socket(path: Path, timeout: float) -> socket.socket:
    family = 1 if os.name == "nt" else socket.AF_UNIX
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        if os.name == "nt":
            sock.setblocking(False)
            try:
                windows_socket_call("connect", sock, path)
            except OSError as exc:
                if exc.errno != 10035:  # WSAEWOULDBLOCK
                    raise
                _, writable, errors = select.select([], [sock], [sock], timeout)
                if not writable and not errors:
                    raise TimeoutError("Timed out connecting to the Codex Unix socket.")
                error = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if error:
                    raise OSError(error, "Windows Unix socket connection failed.")
            sock.settimeout(timeout)
        else:
            sock.settimeout(timeout)
            sock.connect(str(path))
        return sock
    except BaseException:
        sock.close()
        raise
