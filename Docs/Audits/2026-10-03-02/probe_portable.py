"""Validate the frozen release on Windows without retaining disposable runtime data."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

ROOT = next(path for path in Path(__file__).resolve().parents if (path / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))
from codex_auto_continuer.config import lock_path, owner_path
from codex_auto_continuer.instance_lock import is_running


def wait_for(predicate, seconds=20):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.1)
    raise TimeoutError("Frozen release did not reach the expected state.")


def main():
    if is_running(lock_path()):
        raise RuntimeError("Stop monitoring before the isolated portable probe.")
    archive = ROOT / "dist/codex-auto-continuer-0.2.0-windows-x86_64.zip"
    with tempfile.TemporaryDirectory(prefix="portable probe 100% ", dir=ROOT / ".data") as directory:
        path = Path(directory)
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                parts = PurePosixPath(name)
                if parts.is_absolute() or ".." in parts.parts or not name.startswith("CodexAutoContinuer/"):
                    raise RuntimeError("Unexpected release ZIP path.")
            bundle.extractall(path)
        app = path / "CodexAutoContinuer"
        exe = app / "CodexAutoContinuer-CLI.exe"
        config = app / "data/config.json"
        def command(*args, expected=0, timeout=45):
            result = subprocess.run([str(exe), "--config", str(config), *args], capture_output=True, text=True,
                                    encoding="utf-8", timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != expected:
                raise RuntimeError(f"Frozen command {args[0]} returned {result.returncode}, expected {expected}: {result.stderr}")
            return result.stdout.strip()
        log = app / "data/telemetry.jsonl"
        def cycle_count():
            return log.read_text().count('"cycle.completed"') if log.exists() else 0
        try:
            assert command("--version") == "0.2.0"
            command("init")
            assert json.loads(command("status"))["configPath"] == str(config)
            command("start")
            wait_for(lambda: cycle_count() > 0)
            active = json.loads((app / "data/runtime-status.json").read_text())
            command("once", expected=2)
            assert json.loads((app / "data/runtime-status.json").read_text())["phase"] != "failed"
            before = cycle_count()
            command("scan")
            wait_for(lambda: cycle_count() > before)
            private = log.read_text()
            assert '"privacy":"private"' in private and '"cwd"' not in private and '"name"' not in private
            command("logging", "detailed", timeout=90)
            wait_for(lambda: '"privacy":"detailed"' in log.read_text())
            restarted = json.loads((app / "data/runtime-status.json").read_text())
            assert restarted["pid"] != active["pid"]
            command("stop", timeout=65)
            assert not json.loads(command("status"))["supervisorRunning"]
            assert '"cwd"' in log.read_text()
            print(json.dumps({"version": "0.2.0", "spacesAndPercentPath": True, "localData": True,
                              "startScanStop": True, "exclusiveOnce": True, "settingsRestart": True,
                              "privateAndDetailedTelemetry": True}, indent=2))
        finally:
            if is_running(lock_path()):
                owner = json.loads(owner_path().read_text())
                if owner["configPath"] != str(config):
                    raise RuntimeError("Another app owns monitoring; probe cleanup will not stop it.")
                try:
                    command("stop", timeout=65)
                finally:
                    if is_running(lock_path()):
                        subprocess.run(["taskkill", "/PID", str(owner["pid"]), "/T", "/F"], capture_output=True,
                                       timeout=5, creationflags=subprocess.CREATE_NO_WINDOW, check=True)


if __name__ == "__main__":
    main()
