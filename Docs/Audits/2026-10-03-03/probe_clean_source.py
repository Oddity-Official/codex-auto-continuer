"""Exercise the documented setup/build in a fresh, self-contained source export."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = next(path for path in Path(__file__).resolve().parents if (path / "pyproject.toml").exists())


def run(root, arguments, timeout):
    process = subprocess.Popen(arguments, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                       timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        process.communicate(timeout=5)
        raise
    # Keep full console diagnostics local; persisted reports use aggregate outcomes only.
    print(output, flush=True)
    if process.returncode:
        raise RuntimeError(f"Clean source command failed with exit {process.returncode}")
    return output


def main():
    spec = importlib.util.spec_from_file_location("workflow", ROOT / "scripts/project-workflow.py")
    workflow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(workflow)
    files = workflow.collect(ROOT, workflow.settings(ROOT))
    with tempfile.TemporaryDirectory(prefix="pub-", dir=ROOT / ".data") as temporary:
        clean = Path(temporary)
        for name, path in files.items():
            target = clean / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        assert not any((clean / name).exists() for name in ("App", "data", ".venv", "dist", ".git"))
        run(clean, [sys.executable, "-m", "venv", ".venv"], 60)
        python = clean / ".venv/Scripts/python.exe"
        run(clean, [str(python), "-m", "pip", "install", "--timeout", "30", ".[dev,build]"], 180)
        gate = run(clean, ["pwsh", "-NoProfile", "-File", "scripts/verify-windows.ps1"], 300)
        assert str(python) in gate and "163 passed" in gate and "0.3.0" in gate
        run(clean, ["pwsh", "-NoProfile", "-File", "scripts/build-portable.ps1"], 360)
        run(clean, [str(python), "-m", "pip", "wheel", "--timeout", "30", "--no-deps",
                    "--no-build-isolation", "--wheel-dir", "dist", "."], 120)
        frozen = run(clean, [str(python), "Docs/History/2026-10-03-ux-release/probe_portable.py"], 150)
        assert '"userChatsDispatched": 0' in frozen and '"codexConnections": 0' in frozen
        print(json.dumps({"sourceFiles": len(files), "freshVirtualEnvironment": True,
                          "parentCheckoutRequired": False, "nativeGate": "163 passed",
                          "portableBuild": "passed", "wheelBuild": "passed", "frozenProbe": "passed",
                          "userChatsDispatched": 0, "githubHostedRun": "not performed"}, indent=2))


if __name__ == "__main__":
    main()
