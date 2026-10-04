from __future__ import annotations

import sys
from pathlib import Path

import os
import socket
import tempfile
import select

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def unix_listener():
    from codex_auto_continuer.uds import windows_socket_call

    class WindowsListener:
        def __init__(self, sock):
            self.sock = sock

        def accept(self):
            import ctypes
            if not select.select([self.sock], [], [], 3)[0]:
                raise TimeoutError("Test Unix listener received no connection.")
            api = ctypes.WinDLL("ws2_32")
            api.accept.argtypes = [ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]
            api.accept.restype = ctypes.c_size_t
            handle = api.accept(self.sock.fileno(), None, None)
            if handle == ctypes.c_size_t(-1).value:
                raise OSError(api.WSAGetLastError(), "Test Unix listener accept failed.")
            conn = socket.socket(1, socket.SOCK_STREAM, fileno=handle)
            conn.settimeout(3)
            return conn, None

        def close(self):
            self.sock.close()

    def create(path):
        listener = socket.socket(1 if os.name == "nt" else socket.AF_UNIX, socket.SOCK_STREAM)
        listener.settimeout(3)
        try:
            if os.name == "nt":
                windows_socket_call("bind", listener, path)
            else:
                listener.bind(str(path))
            listener.listen(1)
            return WindowsListener(listener) if os.name == "nt" else listener
        except BaseException:
            listener.close()
            raise
    return create


@pytest.fixture
def unix_path():
    # Keep native socket fixtures short and in the checkout's ignored staging area.
    # This host cannot connect to venv-created sockets in the system temp directory.
    directory = ROOT / ".data" if os.name == "nt" else None
    if directory is not None:
        directory.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="uds-", dir=directory) as temporary:
        yield Path(temporary) / "s.sock"
