"""Frozen UX release probe; no Codex connection or user-chat dispatch is permitted."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

ROOT = next(path for path in Path(__file__).resolve().parents if (path / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))
from codex_auto_continuer import __version__
from codex_auto_continuer.config import Config, save_config


def main():
    archive = ROOT / f"dist/codex-auto-continuer-{__version__}-windows-x86_64.zip"
    with tempfile.TemporaryDirectory(prefix="UX probe 100% ", dir=ROOT / ".data") as directory:
        stage = Path(directory)
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
            for name in names:
                path = PurePosixPath(name)
                assert not path.is_absolute() and ".." not in path.parts and name.startswith("CodexAutoContinuer/")
            assert bundle.testzip() is None
            manifest = json.loads(bundle.read("CodexAutoContinuer/RELEASE-MANIFEST.json"))
            assert len(names) == len(manifest["files"]) + 1
            for name, entry in manifest["files"].items():
                body = bundle.read("CodexAutoContinuer/" + name)
                assert len(body) == entry["bytes"] and hashlib.sha256(body).hexdigest() == entry["sha256"]
            assert not any("/Docs/" in name or "/data/" in name or "resvg_py" in name for name in names)
            assert any("Licenses/tomlkit/" in name for name in names)
            assert bundle.read("CodexAutoContinuer/Licenses/pystray/source/pystray/_win32.py")
            assert bundle.read("CodexAutoContinuer/README.md").decode("utf-8").splitlines() == (ROOT / "Docs/USER-GUIDE.md").read_text(encoding="utf-8").splitlines()
            bundle.extractall(stage)
        app = stage / "CodexAutoContinuer"
        settings = app / "data/settings.toml"
        log = app / "data/telemetry.jsonl"
        snapshot = app / "data/runtime-status.json"
        env = os.environ | {"LOCALAPPDATA": str(stage / "isolated-control")}
        def command(*args, expected=0, timeout=20):
            process = subprocess.Popen([str(app / "CodexAutoContinuer-CLI.exe"), "--config", str(settings), *args],
                                       env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                       encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                               timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                process.communicate(timeout=5)
                raise
            assert process.returncode == expected, (args, stdout, stderr)
            return stdout.strip()
        def wait(predicate, seconds=15):
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                if predicate():
                    return
                time.sleep(0.1)
            report = {key: current().get(key) for key in ("phase", "errorType", "lastScanAt")}
            events = [json.loads(line)["event"] for line in log.read_text().splitlines()] if log.exists() else []
            raise TimeoutError(f"Expected frozen state was not observed: snapshot={report}, recentEvents={events[-15:]}")
        def current():
            return json.loads(snapshot.read_text()) if snapshot.exists() else {}
        pid = None
        tray = None
        try:
            assert command("--version") == __version__
            assert json.loads(command("status"))["clients"] == ["vscode", "cli", "desktop"]
            assert not settings.exists()
            save_config(settings, Config(clients=(), poll_seconds=1, auto_update=False))
            command("start")
            wait(lambda: current().get("phase") == "paused")
            pid = current()["pid"]
            assert (app / "data/continue-prompt.md").read_text().strip() == "Continue"
            command("once", expected=2)
            assert current()["phase"] != "failed"
            scan = command("scan")
            assert scan.startswith("Scan requested;")
            assert json.loads(scan[scan.index("{"):])["scanned_threads"] == 0
            command("logging", "detailed")
            wait(lambda: '"privacy":"detailed"' in log.read_text())
            assert current()["pid"] == pid
            valid = settings.read_text()
            settings.write_text("clients = [", encoding="utf-8")
            wait(lambda: current().get("phase") == "failed")
            assert current()["pid"] == pid
            settings.write_text(valid, encoding="utf-8")
            wait(lambda: current().get("phase") == "paused")
            prompt = app / "data/continue-prompt.md"
            saved_prompt = prompt.read_bytes()
            prompt.write_text("")
            wait(lambda: current().get("phase") == "failed")
            prompt.write_bytes(saved_prompt)
            wait(lambda: current().get("phase") == "paused")
            assert current()["pid"] == pid
            events = [json.loads(line) for line in log.read_text().splitlines()]
            assert not any(e["event"].startswith("rpc.") or e["event"].startswith("dispatch.") for e in events)
            command("stop", timeout=65)
            assert not json.loads(command("status"))["supervisorRunning"]
            snapshot.write_text(json.dumps({"phase": "failed", "reason": "Synthetic previous-session failure", "pid": 0}), encoding="utf-8")
            tray = subprocess.Popen([str(app / "CodexAutoContinuer.exe"), "--config", str(settings), "tray"], env=env,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            wait(lambda: current().get("phase") == "paused" and current().get("pid") != pid)
            pid = current()["pid"]
            command("stop", timeout=65)
            from codex_auto_continuer.update_install import stop_tray
            previous = os.environ.get("LOCALAPPDATA")
            os.environ["LOCALAPPDATA"] = env["LOCALAPPDATA"]
            try:
                stop_tray(tray.pid, app)
            finally:
                if previous is None:
                    os.environ.pop("LOCALAPPDATA", None)
                else:
                    os.environ["LOCALAPPDATA"] = previous
            tray.wait(timeout=5)
            # Exercise the packaged encryption/review modules without any owner connection.
            from codex_auto_continuer.holding_journal import Journal
            journal = Journal(app / "data/held-inputs.dpapi")
            with journal.transaction("a" * 64) as raw:
                raw["threads"] = {"fixture-thread": {"authorizedTurnId": "fixture-turn", "recoveryIds": [], "paused": ""}}
                raw["records"] = [{"id": "fixture-input", "threadId": "fixture-thread", "clientUserMessageId": "fixture-client",
                    "anchorTurnId": "fixture-turn", "phase": "held", "releasedQueueId": None,
                    "input": [{"type": "text", "text": "PRIVATE_FROZEN_CANARY", "text_elements": []}]}]
                journal.save(raw)
            assert "PRIVATE_FROZEN_CANARY" not in command("held", "list")
            assert "PRIVATE_FROZEN_CANARY" in command("held", "list", "--show-input")
            assert b"PRIVATE_FROZEN_CANARY" not in journal.path.read_bytes()
            command("held", "discard", "fixture-input")
            assert json.loads(command("held", "list")) == []
            assert "PRIVATE_FROZEN_CANARY" not in log.read_text()
            assert not any(json.loads(line)["event"].startswith("rpc.") for line in log.read_text().splitlines())
            print(json.dumps({"version": __version__, "portableFiles": len(manifest["files"]),
                              "zipBytes": archive.stat().st_size, "checksums": "passed", "leanPackage": True,
                              "spacesAndPercentPath": True, "implicitDefaults": True, "samePidHotReload": True,
                              "invalidSettingsPauseAndRepair": True, "invalidPromptPauseAndRepair": True,
                              "correlatedScanFeedback": True, "exclusiveOnce": True, "gracefulStop": True,
                              "staleFailureTrayAutostart": True, "encryptedHeldReview": True,
                              "codexConnections": 0, "userChatsDispatched": 0}, indent=2))
        finally:
            if pid:
                try:
                    command("stop", timeout=65)
                except BaseException:
                    owner = json.loads((Path(env["LOCALAPPDATA"]) / "CodexAutoContinuer/owner.json").read_text())
                    if owner["pid"] != pid or owner["configPath"] != str(settings):
                        raise RuntimeError("Cleanup refuses a process not owned by this probe")
                    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                                   timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
            if tray is not None and tray.poll() is None:
                tray.terminate()
                tray.wait(timeout=5)


if __name__ == "__main__":
    main()
