"""Unmodified Codex plus a loopback service, never the user's home or account.

Backend shapes follow openai/codex rust-v0.160.0 account and response fixtures.
Only synthetic service responses and transport fault injection are simulated.
"""
from __future__ import annotations

import base64
import gzip
import json
import os
import subprocess
import tempfile
import threading
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from codex_auto_continuer.appserver import AppServerClient, RpcError
from codex_auto_continuer.config import Config
from codex_auto_continuer.errors import TransportError
from codex_auto_continuer.supervisor import Supervisor
from codex_auto_continuer.ws_unix import UnixWebSocket
from codex_auto_continuer import telemetry

ACCOUNT = "cac-fixture-account"
USER = "cac-fixture-user"
TOKEN = "cac-local-fixture-not-a-real-token"


class Service:
    def __init__(self):
        self.allowed = False
        self.permission_sequence = []
        self.account = ACCOUNT
        self.user = USER
        self.reset_at = int(time.time()) - 60
        self.fail_inference = True
        self.requests = []
        self.user_messages = []
        self.errors = []
        self.allow_rejected_external = False
        self.rejected_external = 0
        self.lock = threading.Lock()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), self.handler())
        self.server.daemon_threads = True
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    @property
    def inference_count(self):
        with self.lock:
            return sum(method == "POST" and path == "/v1/responses" for method, path in self.requests)

    def handler(self):
        service = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(5)

            def log_message(self, *_):
                pass

            def reply(self, status, body, content_type="application/json"):
                body = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def route(self):
                parsed = urlsplit(self.path)
                # Also act as a rejecting proxy for any accidental external HTTP request.
                if parsed.netloc:
                    self.reject_external("Unexpected proxy destination")
                    self.reply(502, {"error": "External network is forbidden in this fixture"})
                    return None
                with service.lock:
                    service.requests.append((self.command, parsed.path))
                if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                    service.errors.append(f"Unexpected fixture authorization for {parsed.path}")
                    self.reply(401, {"error": "Expected synthetic fixture authorization"})
                    return None
                return parsed.path

            def do_CONNECT(self):
                self.reject_external("Unexpected external TLS destination")
                self.reply(502, {"error": "External network is forbidden in this fixture"})

            def reject_external(self, message):
                with service.lock:
                    service.rejected_external += 1
                    if not service.allow_rejected_external:
                        service.errors.append(message)

            def do_GET(self):
                path = self.route()
                if path is None:
                    return
                if path == "/api/codex/usage":
                    if self.headers.get("ChatGPT-Account-Id") != ACCOUNT:
                        service.errors.append("Missing or different account header")
                    with service.lock:
                        allowed = service.permission_sequence.pop(0) if service.permission_sequence else service.allowed
                    self.reply(200, {
                        "account_id": service.account, "user_id": service.user, "plan_type": "pro",
                        "rate_limit": {"allowed": allowed, "limit_reached": not allowed,
                            "primary_window": {"used_percent": 100, "limit_window_seconds": 18000,
                                "reset_after_seconds": 0, "reset_at": service.reset_at}},
                        "rate_limit_reset_credits": {"available_count": 0},
                    })
                elif path == "/api/codex/rate-limit-reset-credits":
                    self.reply(200, {"available_count": 0, "credits": [], "total_earned_count": 0})
                elif path == "/api/codex/accounts/check":
                    self.reply(200, {"accounts": [{"id": ACCOUNT,
                        "workspace_backend_origin": service.base_url,
                        "account_routing_override": "NO_CONSTRAINT"}]})
                elif path == "/api/codex/settings/user":
                    self.reply(200, {})
                else:
                    service.errors.append(f"Unexpected GET route: {path}")
                    self.reply(404, {"error": "Unexpected fixture route"})

            def do_POST(self):
                path = self.route()
                if path is None:
                    return
                raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                if self.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                if path != "/v1/responses":
                    service.errors.append(f"Unexpected POST route: {path}")
                    self.reply(404, {"error": "Unexpected fixture route"})
                    return
                request = json.loads(raw)
                messages = [item for item in request.get("input", []) if item.get("role") == "user"]
                texts = [part.get("text", "") for item in messages[-1:] for part in item.get("content", [])]
                with service.lock:
                    service.user_messages.append("".join(texts))
                if service.fail_inference:
                    self.reply(429, {"error": {"type": "usage_limit_reached", "plan_type": "pro",
                        "resets_at": service.reset_at}})
                    return
                response_id = f"fixture-response-{service.inference_count}"
                events = [
                    {"type": "response.created", "response": {"id": response_id}},
                    {"type": "response.output_item.done", "item": {"type": "message", "role": "assistant",
                        "id": "fixture-message", "content": [{"type": "output_text", "text": "CAC_FIXTURE_OK"}]}},
                    {"type": "response.completed", "response": {"id": response_id, "usage": {
                        "input_tokens": 1, "output_tokens": 1, "total_tokens": 2,
                        "input_tokens_details": None, "output_tokens_details": None}}},
                ]
                body = "".join(f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events).encode()
                self.reply(200, body, "text/event-stream")

        return Handler


def fixture_auth():
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")

    token = ".".join([encode({"alg": "none", "typ": "JWT"}), encode({
        "https://api.openai.com/auth": {"chatgpt_plan_type": "pro", "chatgpt_user_id": USER,
            "chatgpt_account_id": ACCOUNT}}), "c3ludGhldGlj"])
    return {"auth_mode": "chatgpt", "OPENAI_API_KEY": None,
        "tokens": {"id_token": token, "access_token": TOKEN,
            "refresh_token": "cac-fixture-no-refresh", "account_id": ACCOUNT},
        "last_refresh": datetime.now(timezone.utc).isoformat()}


class NativeFixture:
    def __init__(self, root: Path, binary: str, *, managed=False, daemon_binary=None):
        self.root = root
        self.binary = binary
        self.daemon_binary = daemon_binary or binary
        self.managed = managed
        self.stack = ExitStack()
        self.clients = []
        self.supervisors = []

    def __enter__(self):
        try:
            staging = self.root / ".data"
            staging.mkdir(exist_ok=True)
            self.home = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix="n", dir=staging)))
            self.service = self.stack.enter_context(Service())
            self.data = self.home / "cac"
            self.data.mkdir()
            self.telemetry_file = self.data / "telemetry.jsonl"
            previous_trace = telemetry._trace
            telemetry.setup(self.telemetry_file, Config())

            def close_telemetry():
                for handler in telemetry._logger.handlers[:]:
                    handler.close()
                    telemetry._logger.removeHandler(handler)
                telemetry._trace = previous_trace

            self.stack.callback(close_telemetry)
            self.prompt = self.data / "continue-prompt.md"
            self.prompt.write_text("Continue", encoding="utf-8")
            (self.home / "auth.json").write_text(json.dumps(fixture_auth()), encoding="utf-8")
            (self.home / "config.toml").write_text(
                f'chatgpt_base_url = "{self.service.base_url}"\ncli_auth_credentials_store = "file"\n'
                'model_provider = "fixture"\nmodel = "fixture-model"\ncheck_for_update_on_startup = false\n'
                '[features]\napps = false\nplugins = false\nrecommended_plugins = false\nremote_models = false\n'
                'skip_host_skill_discovery = true\n'
                '[analytics]\nenabled = false\n[otel]\nexporter = "none"\n'
                '[model_providers.fixture]\nname = "Loopback fixture"\n'
                f'base_url = "{self.service.base_url}/v1"\n'
                'env_key = "CAC_FIXTURE_KEY"\nwire_api = "responses"\n'
                'supports_websockets = false\nrequest_max_retries = 0\nstream_max_retries = 0\n', encoding="utf-8")
            # Preserve OS/tool discovery, never inherited credentials, profiles or endpoints.
            self.env = {key: value for key, value in os.environ.items() if not any(
                marker in key.upper() for marker in ("CODEX", "OPENAI", "TOKEN", "SECRET", "API_KEY", "PROXY"))}
            self.env.update({"CODEX_HOME": str(self.home), "HOME": str(self.home),
                "USERPROFILE": str(self.home), "LOCALAPPDATA": str(self.home / "local"),
                "XDG_CONFIG_HOME": str(self.home / "config"), "CAC_FIXTURE_KEY": TOKEN,
                "HTTP_PROXY": self.service.base_url, "HTTPS_PROXY": self.service.base_url,
                "ALL_PROXY": self.service.base_url, "NO_PROXY": "127.0.0.1,localhost"})
            self.owner_socket = self.home / "app-server-control/o.sock" if self.managed else self.home / "app-server-control" / "app-server-control.sock"
            self.socket = self.home / "app-server-control/app-server-control.sock" if self.managed else self.owner_socket.parent / "m.sock"
            for path in ((self.socket, self.owner_socket) if self.managed else (self.owner_socket, self.socket)):
                if len(str(path).encode()) > 107:
                    raise ValueError("Native fixture socket exceeds 107 bytes. Use a shorter checkout path.")
                if self.managed and path == self.socket:
                    self.start_managed()
                else:
                    self.start_server(path, default=not self.managed and path == self.owner_socket)
            self.owner = self.client(self.owner_socket)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        try:
            for supervisor in self.supervisors:
                supervisor.close()
            for client in self.clients:
                client.close()
        finally:
            self.stack.close()
        if hasattr(self, "service"):
            assert not self.service.errors, f"Unexpected fixture traffic: {self.service.errors}"

    def start_server(self, path, *, default=False):
        error_path = self.home / f"{path.name}.stderr"
        stderr = self.stack.enter_context(error_path.open("wb"))
        listen = "unix://" if default else f"unix://{path}"
        binary = self.daemon_binary if self.managed else self.binary
        process = subprocess.Popen([binary, "app-server", "--listen", listen],
            cwd=self.home, env=self.env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=stderr,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            start_new_session=os.name != "nt")

        def stop():
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True, timeout=5, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    import signal
                    os.killpg(process.pid, signal.SIGKILL)
                if process.poll() is None:
                    process.kill()
            process.wait(timeout=5)

        self.stack.callback(stop)
        deadline = time.monotonic() + 15
        while True:
            if process.poll() is not None:
                detail = error_path.read_text(encoding="utf-8", errors="replace")
                raise RuntimeError(f"Isolated native server exited: {detail.replace(str(self.home), '<fixture>')}")
            try:
                client = AppServerClient.connect(path, 3)
                client.close()
                return
            except TransportError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Isolated native server did not become ready within 15 seconds.")
                time.sleep(0.1)

    def start_managed(self):
        from codex_auto_continuer.codex import _run
        settings = self.home / "app-server-daemon/settings.json"
        # Native lifecycle commands create their state directory with a private Windows ACL.
        _run(self.binary, ["app-server", "daemon", "stop"], 10, env=self.env)
        assert settings.parent.is_dir(), "Codex did not create its private daemon state directory"
        settings.write_text(json.dumps({"remoteControlEnabled": False, "shutdownGraceSeconds": 0,
            "updater": {"autoUpdateEnabled": False, "updateIntervalMinutes": 120}}), encoding="utf-8")
        def stop():
            result = _run(self.binary, ["app-server", "daemon", "stop"], 15, env=self.env)
            if (self.home / "app-server-daemon/app-server.pid").exists():
                assert result.returncode == 0, "Isolated managed daemon did not stop cleanly: " + result.stderr.replace(str(self.home), "<fixture>")
        self.stack.callback(stop)
        if self.daemon_binary != self.binary:
            import shutil
            source = Path(self.daemon_binary).resolve().parent.parent
            assert (source / "codex-package.json").is_file(), "Mixed daemon needs a complete official package"
            shutil.copytree(source, self.home / "packages/app-server-daemon/current")
        result = _run(self.binary, ["app-server", "daemon", "bootstrap"], 25, env=self.env)
        if result.returncode:
            raise RuntimeError("Isolated daemon bootstrap failed: " + result.stderr.replace(str(self.home), "<fixture>"))

    def client(self, path=None):
        client = AppServerClient.connect(path or self.socket, 5)
        self.clients.append(client)
        return client

    def supervisor(self):
        from codex_auto_continuer.compatibility import Compatibility
        supervisor = Supervisor(Config(dispatch_spacing_seconds=0, rpc_timeout_seconds=5), self.data / "state.json")
        # Select the isolated control socket, not the user's daemon. All RPCs are native.
        supervisor.client = self.client()
        # This isolated harness establishes behavioral evidence, including for untested builds.
        # It is not a production override: every home, socket and credential belongs to the fixture.
        supervisor.compatibility = Compatibility(status="certified", reason="Isolated native certification probe")
        supervisor._probe_required_methods()
        self.supervisors.append(supervisor)
        return supervisor

    def start_thread(self, text="Fixture initial task"):
        thread = self.owner.request("thread/start", {"cwd": str(self.home), "approvalPolicy": "never",
            "sandbox": "read-only", "baseInstructions": "Do not use tools. Reply CAC_FIXTURE_OK."})["thread"]
        assert thread["source"] == "vscode", "Expected native interactive app-server source"
        self.start_turn(thread["id"], text)
        return thread["id"], self.wait_turn(thread["id"])

    def start_turn(self, thread_id, text):
        return self.owner.request("turn/start", {"threadId": thread_id,
            "input": [{"type": "text", "text": text}]})["turn"]

    def wait_turn(self, thread_id, *, after=None):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            self.owner.request("account/read", {})
            done = any(note.get("method") == "turn/completed"
                and note["params"].get("threadId") == thread_id
                and note["params"]["turn"]["id"] != after for note in self.owner.notifications)
            if not done:
                time.sleep(0.1)
                continue
            try:
                status = self.owner.thread_read(thread_id)["status"]["type"]
                if status != "active":
                    turn = self.owner.latest_turn(thread_id)
                    if turn and turn["id"] != after and turn["status"] in {"completed", "failed"}:
                        return turn
            except RpcError as exc:
                errors = [path.read_text(encoding="utf-8", errors="replace")[-5000:]
                    for path in self.home.glob("*.stderr")]
                detail = f"Native fixture history error: {exc.error}; stderr={errors}"
                raise AssertionError(detail.replace(str(self.home), "<fixture>").replace(
                    str(self.home).replace("\\", "\\\\"), "<fixture>")) from exc
            time.sleep(0.1)
        raise TimeoutError("Native fixture turn did not finish within 20 seconds.")

    def assert_quota_failure(self, turn):
        assert turn["status"] == "failed"
        assert turn["error"]["codexErrorInfo"] == "usageLimitExceeded"
        assert type(turn["completedAt"]) in (int, float)

    def turns(self, thread_id):
        return self.owner.request("thread/turns/list", {"threadId": thread_id, "limit": 100,
            "sortDirection": "asc", "itemsView": "notLoaded"})["data"]

    def events(self):
        return [json.loads(line) for line in self.telemetry_file.read_text(encoding="utf-8").splitlines()]


class LostQueueAck:
    """Drop the real response after an accepted send, or disconnect before sending.

    This injects one transport fault. It never invents a queue result or RPC data.
    """
    def __init__(self, websocket: UnixWebSocket, *, accepted: bool):
        self.websocket = websocket
        self.accepted = accepted
        self.request_id = None

    def __getattr__(self, name):
        return getattr(self.websocket, name)

    def send_text(self, text):
        message = json.loads(text)
        if message.get("method") == "thread/queue/add":
            self.request_id = message["id"]
            if not self.accepted:
                self.websocket.close()
                raise TransportError("Fixture disconnect before queue write")
        self.websocket.send_text(text)

    def recv_text(self):
        text = self.websocket.recv_text()
        message = json.loads(text)
        if self.request_id is not None and message.get("id") == self.request_id and "method" not in message:
            assert "result" in message, "Native queue was not accepted"
            self.websocket.close()
            raise TransportError("Fixture lost acknowledged queue response")
        return text
