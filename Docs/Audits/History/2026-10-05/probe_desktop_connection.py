"""Isolated installed Desktop -> transparent relay -> native managed owner.

The relay forwards original bytes. It neither emulates Codex nor injects RPCs.
Only method names and public initialization identity are retained in memory.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import select
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "integration")]
from codex_auto_continuer.codex import find_codex
from codex_auto_continuer.config import Config
from codex_auto_continuer.supervisor import Supervisor
from codex_auto_continuer.uds import connect_socket
from native_support import NativeFixture


class FrameSummary:
    def __init__(self):
        self.buffer = bytearray()
        self.upgraded = False
        self.methods = collections.Counter()
        self.identity = None

    def feed(self, data):
        self.buffer.extend(data)
        if not self.upgraded:
            end = self.buffer.find(b"\r\n\r\n")
            if end < 0:
                if len(self.buffer) > 65536:
                    raise ValueError("Oversized relay handshake")
                return
            del self.buffer[:end + 4]
            self.upgraded = True
        while len(self.buffer) >= 2:
            opcode, size = self.buffer[0], self.buffer[1] & 127
            masked = bool(self.buffer[1] & 128)
            header = 2
            if size == 126:
                if len(self.buffer) < 4:
                    return
                size = struct.unpack("!H", self.buffer[2:4])[0]
                header = 4
            elif size == 127:
                if len(self.buffer) < 10:
                    return
                size = struct.unpack("!Q", self.buffer[2:10])[0]
                header = 10
            if size > 16 * 1024 * 1024:
                raise ValueError("Oversized relay frame")
            total = header + (4 if masked else 0) + size
            if len(self.buffer) < total:
                return
            mask = self.buffer[header:header + 4]
            body = bytes(self.buffer[header + (4 if masked else 0):total])
            del self.buffer[:total]
            if masked:
                body = bytes(value ^ mask[index % 4] for index, value in enumerate(body))
            if opcode == 0x81:
                message = json.loads(body)
                method = message.get("method")
                if isinstance(method, str):
                    self.methods[method] += 1
                if method == "initialize":
                    info = message.get("params", {}).get("clientInfo", {})
                    self.identity = {k: info.get(k) for k in ("name", "title", "version")}


class Relay:
    def __init__(self, path):
        self.path = path
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(4)
        self.listener.settimeout(0.2)
        self.url = f"ws://127.0.0.1:{self.listener.getsockname()[1]}"
        self.stop = threading.Event()
        self.summaries = []
        self.errors = []
        self.workers = []
        self.thread = threading.Thread(target=self.accept, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def accept(self):
        while not self.stop.is_set():
            try:
                client, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            summary = FrameSummary()
            self.summaries.append(summary)
            worker = threading.Thread(target=self.forward, args=(client, summary), daemon=True)
            self.workers.append(worker)
            worker.start()

    def forward(self, client, summary):
        owner = None
        try:
            owner = connect_socket(self.path, 5)
            client.settimeout(5)
            while not self.stop.is_set():
                ready = select.select([client, owner], [], [], 0.2)[0]
                for source in ready:
                    data = source.recv(65536)
                    if not data:
                        return
                    if source is client:
                        summary.feed(data)
                    (owner if source is client else client).sendall(data)
        except Exception as exc:
            if not self.stop.is_set():
                self.errors.append(type(exc).__name__)
        finally:
            client.close()
            if owner is not None:
                owner.close()

    def __exit__(self, *_):
        self.stop.set()
        self.listener.close()
        self.thread.join(3)
        for worker in self.workers:
            worker.join(6)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desktop", type=Path, required=True)
    args = parser.parse_args()
    binary = find_codex()
    with NativeFixture(ROOT, binary, managed=True) as native:
        native.service.allow_rejected_external = True
        with Relay(native.socket) as relay:
            env = native.env | {"CODEX_ELECTRON_USER_DATA_PATH": str(native.home / "desktop-profile"),
                "CODEX_APP_SERVER_WS_URL": relay.url, "APPDATA": str(native.home / "roaming")}
            env.pop("ELECTRON_RUN_AS_NODE", None)
            previous = os.environ.copy()
            os.environ.clear()
            os.environ.update(native.env)
            try:
                supervisor = Supervisor(Config(codex_executable=binary, queue_holding=True), native.data / "state.json")
                native.supervisors.append(supervisor)
                supervisor.connect()
                assert supervisor.client.socket_path == native.socket
            finally:
                os.environ.clear()
                os.environ.update(previous)
            output = native.stack.enter_context((native.home / "desktop.stdout").open("wb"))
            process = subprocess.Popen([str(args.desktop.resolve(strict=True))], env=env, cwd=native.home,
                stdin=subprocess.DEVNULL, stdout=output, stderr=output)
            try:
                deadline = time.monotonic() + 35
                while time.monotonic() < deadline:
                    if any(s.identity and s.methods.get("account/read") for s in relay.summaries):
                        break
                    if process.poll() is not None:
                        break
                    time.sleep(0.1)
                result = {"client": "installed Desktop", "productionCACConnectionUnmodified": True,
                    "relayForwardsUnchangedBytes": True,
                    "connections": [{"identity": s.identity, "methods": dict(s.methods)} for s in relay.summaries],
                    "relayErrors": relay.errors, "modelRequests": native.service.inference_count,
                    "clientExited": process.poll() is not None,
                    "composerAcceptance": "not tested: native GUI input tool unavailable"}
                print(json.dumps(result, indent=2))
                assert any(s.identity and s.methods.get("account/read") for s in relay.summaries), "Desktop did not establish the expected owner connection"
            finally:
                if process.poll() is None:
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
