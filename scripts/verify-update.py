"""Opt-in signed GitHub update/recovery probe using real frozen builds and synthetic data."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from codex_auto_continuer.state import Obligation, State, save_state
from codex_auto_continuer.updates import check_release, launch_update, parse_json, write_json
from codex_auto_continuer.config import Config


def command(executable, *args, env, timeout=90):
    process = subprocess.Popen(
        [str(executable), *args], env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        output, error = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        process.communicate(timeout=5)
        raise AssertionError("Update probe command exceeded its deadline") from None
    assert process.returncode == 0, f"Probe command failed with exit {process.returncode}; inspect retained fixture diagnostics"
    return output


def wait_job(job, wanted, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if job.exists():
            record = parse_json(job.read_bytes())
            if record.get("status") == wanted:
                return record
            failure = job.parent / "failure.json"
            if failure.exists():
                raise AssertionError(parse_json(failure.read_bytes())["reason"])
        time.sleep(0.2)
    raise AssertionError("Update did not reach its expected terminal status within the deadline")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-archive", type=Path, required=True)
    parser.add_argument("--private", action="store_true")
    args = parser.parse_args()
    if os.name != "nt":
        raise SystemExit("This probe requires native Windows and real portable EXEs.")
    stage = ROOT / ".data" / ("update-probe-" + uuid.uuid4().hex)
    stage.mkdir(parents=True)
    env = os.environ | {"LOCALAPPDATA": str(stage / "control")}
    with zipfile.ZipFile(args.baseline_archive) as archive:
        assert archive.testzip() is None
        archive.extractall(stage)
    app = stage / "CodexAutoContinuer"
    cli = app / "CodexAutoContinuer-CLI.exe"
    gui = app / "CodexAutoContinuer.exe"
    settings = app / "data/settings.toml"
    settings.parent.mkdir()
    # Existing obligations would otherwise make clients=[] reconcile against the user's Codex.
    # A deliberately absent executable proves this probe cannot connect or dispatch to it.
    settings.write_text('clients = []\ncodex_executable = ' + json.dumps(str(stage / "absent-codex.exe")) + '\n', encoding="utf-8")
    (settings.parent / "continue-prompt.md").write_text("Synthetic saved prompt", encoding="utf-8")
    obligation = Obligation.create("synthetic-chat", "synthetic-failed-turn", time.time(), None)
    obligation.phase = "uncertain"
    save_state(settings.parent / "state.json", State(obligations=[obligation]))
    from codex_auto_continuer.holding_journal import Journal
    journal = Journal(settings.parent / "held-inputs.dpapi")
    with journal.transaction("a" * 64) as raw:
        raw["threads"] = {"synthetic-chat": {"authorizedTurnId": "synthetic-failed-turn", "recoveryIds": [], "paused": ""}}
        raw["records"] = [{"id": "synthetic-input", "threadId": "synthetic-chat", "clientUserMessageId": "synthetic-client",
            "anchorTurnId": "synthetic-failed-turn", "phase": "held", "releasedQueueId": None,
            "input": [{"type": "text", "text": "PRIVATE_UPDATE_CANARY", "text_elements": []}]}]
        journal.save(raw)
    from codex_auto_continuer.quota_retry import QuotaRetry
    retry = QuotaRetry(settings.parent / "quota-retry.json")
    retry.rejected("synthetic-chat", "synthetic-rejected-turn", time.time() - 1, {}, time.time())
    protected = {name: (settings.parent / name).read_bytes() for name in ("settings.toml", "continue-prompt.md", "state.json", "held-inputs.dpapi", "quota-retry.json")}
    original_version = command(cli, "--version", env=env).decode().strip()
    original_manifest = parse_json((app / "RELEASE-MANIFEST.json").read_bytes())
    original_local = os.environ.get("LOCALAPPDATA")
    os.environ["LOCALAPPDATA"] = env["LOCALAPPDATA"]
    try:
        tray = subprocess.Popen([str(gui), "--config", str(settings), "tray"], env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            assert tray.poll() is None
            snapshot = settings.parent / "runtime-status.json"
            if snapshot.exists() and parse_json(snapshot.read_bytes()).get("phase") in {"failed", "reconnecting"}:
                break
            time.sleep(0.2)
        else:
            raise AssertionError("Isolated baseline did not report its deliberately absent Codex executable")
        result = check_release(settings, Config(update_use_github_cli_auth=args.private), stage=True,
                               app_root=app, installed_version=original_version)
        assert result["status"] == "staged", "Use a real older baseline build, not a fabricated version"
        job = Path(result["job"])
        write_json(settings.parent / "update-status.json", result)
        launch_update(job, tray.pid)
        terminal = wait_job(job, "completed")
        assert command(cli, "--version", env=env).decode().strip() == result["version"]
        assert all((settings.parent / name).read_bytes() == data for name, data in protected.items())
        # Code-only rollback must retain state written after successful installation.
        newer = State(obligations=[obligation], observations=[])
        newer.obligations[0].detected_at += 1
        save_state(settings.parent / "state.json", newer)
        newer_state = (settings.parent / "state.json").read_bytes()
        ready = parse_json((settings.parent / "tray-ready.json").read_bytes())
        request = parse_json(job.read_bytes())
        request["tray_pid"] = ready["pid"]
        request["requester_pid"] = None
        write_json(job, request)
        worker = job.parent / "bundle/CodexAutoContinuer/CodexAutoContinuer-CLI.exe"
        command(worker, "_update-worker", str(job), "--recover", env=env)
        terminal = wait_job(job, "rolled_back")
        assert command(cli, "--version", env=env).decode().strip() == original_version
        assert (settings.parent / "state.json").read_bytes() == newer_state
        assert (settings.parent / "continue-prompt.md").read_bytes() == protected["continue-prompt.md"]
        assert (settings.parent / "held-inputs.dpapi").read_bytes() == protected["held-inputs.dpapi"]
        assert (settings.parent / "quota-retry.json").read_bytes() == protected["quota-retry.json"]
        for name, entry in original_manifest["files"].items():
            assert hashlib.sha256((app / name).read_bytes()).hexdigest() == entry["sha256"]
        print(json.dumps({"baseline": original_version, "updated": result["version"], "update": "completed", "rollback": "rolled_back",
              "protectedFiles": list(protected), "newerStatePreserved": True, "originalCodeHashes": len(original_manifest["files"]), "userCodexConnections": 0}, indent=2))
    finally:
        try:
            command(cli, "--config", str(settings), "stop", env=env)
            from codex_auto_continuer.update_install import stop_tray
            # A rolled-back pre-updater build has no ready marker. Find only the fixture's GUI.
            output = subprocess.run(["pwsh", "-NoProfile", "-Command", "Get-CimInstance Win32_Process -Filter \"Name = 'CodexAutoContinuer.exe'\" | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"],
                capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
            records = json.loads(output.stdout or b"[]")
            for row in records if isinstance(records, list) else [records]:
                if row.get("ExecutablePath") and Path(row["ExecutablePath"]).resolve() == gui.resolve():
                    stop_tray(row["ProcessId"], app)
        finally:
            if original_local is None:
                os.environ.pop("LOCALAPPDATA", None)
            else:
                os.environ["LOCALAPPDATA"] = original_local


if __name__ == "__main__":
    main()
