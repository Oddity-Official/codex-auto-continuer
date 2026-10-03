"""Verify native quota failure persistence against a local HTTP 429 fixture.

Uses an isolated temporary CODEX_HOME and a non-secret fixture key. No real
account request, account exhaustion, or user conversation is involved.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))

from codex_auto_continuer.appserver import AppServerClient
from codex_auto_continuer.codex import find_codex
from codex_auto_continuer.errors import TransportError


class QuotaFixture(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        body = json.dumps({"error": {"type": "usage_limit_reached", "plan_type": "pro",
                                    "resets_at": int(time.time()) + 3600}}).encode()
        self.send_response(429)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuotaFixture)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix="q") as directory:
            home = Path(directory)
            path = home / "app-server-control" / "app-server-control.sock"
            (home / "config.toml").write_text(
                'model_provider = "quota_probe"\nmodel = "fixture-model"\n'
                '[model_providers.quota_probe]\nname = "Quota fixture"\n'
                f'base_url = "http://127.0.0.1:{server.server_port}/v1"\n'
                'env_key = "CAC_QUOTA_FIXTURE_KEY"\nwire_api = "responses"\n'
                'request_max_retries = 0\nstream_max_retries = 0\n', encoding="utf-8",
            )
            env = os.environ.copy()
            env["CODEX_HOME"] = str(home)
            env["CAC_QUOTA_FIXTURE_KEY"] = "local-non-secret-fixture"
            process = subprocess.Popen(
                [find_codex(), "app-server", "--listen", "unix://"], env=env,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            client = None
            try:
                deadline = time.monotonic() + 10
                while client is None:
                    try:
                        client = AppServerClient.connect(path, 2)
                    except TransportError:
                        if process.poll() is not None:
                            raise RuntimeError(process.stderr.read().decode("utf-8", "replace"))
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(0.1)
                response = client.request("thread/start", {"cwd": str(home), "approvalPolicy": "never",
                    "sandbox": "read-only", "baseInstructions": "Do not use tools. Reply OK."})
                thread_id = response["thread"]["id"]
                client.request("turn/start", {"threadId": thread_id, "input": [{"type": "text", "text": "Reply OK."}]})
                deadline = time.monotonic() + 20
                while True:
                    client.request("thread/read", {"threadId": thread_id, "includeTurns": False})
                    done = next((n for n in client.notifications if n.get("method") == "turn/completed"), None)
                    if done:
                        break
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Quota fixture turn did not finish in 20s.")
                    time.sleep(0.1)
                live = done["params"]["turn"]
                persisted = client.latest_turn(thread_id)
                out = {"liveStatus": live["status"], "liveErrorInfo": (live.get("error") or {}).get("codexErrorInfo"),
                       "persistedStatus": persisted["status"],
                       "persistedErrorInfo": (persisted.get("error") or {}).get("codexErrorInfo"),
                       "completedAtPresent": isinstance(persisted.get("completedAt"), int)}
                print(json.dumps(out, indent=2))
                assert out["liveStatus"] == out["persistedStatus"] == "failed"
                assert out["liveErrorInfo"] == out["persistedErrorInfo"] == "usageLimitExceeded"
                assert out["completedAtPresent"]
            finally:
                if client:
                    client.close()
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=5, check=False)
                else:
                    process.terminate()
                process.wait(timeout=5)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
