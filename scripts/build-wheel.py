"""Build a source wheel without inheriting stale Setuptools files from this checkout."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from codex_auto_continuer.atomic import replace_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    staging = ROOT / ".data"
    staging.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wheel-build-", dir=staging) as directory:
        stage = Path(directory)
        source = stage / "source"
        source.mkdir()
        for name in ("pyproject.toml", "README.md", "LICENSE"):
            shutil.copy2(ROOT / name, source / name)
        shutil.copytree(ROOT / "Licenses", source / "Licenses")
        shutil.copytree(ROOT / "src", source / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"))
        process = subprocess.Popen([sys.executable, "-m", "pip", "wheel", "--disable-pip-version-check",
            "--no-deps", "--no-build-isolation", "--wheel-dir", str(stage / "wheels"), str(source)],
            cwd=stage, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            start_new_session=os.name != "nt")
        try:
            code = process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                import signal
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
            raise SystemExit("Wheel build exceeded 120 seconds; its process tree was stopped.") from None
        if code:
            raise SystemExit("Wheel build failed; the prior wheel was preserved. Install the declared build dependencies.")
        wheels = list((stage / "wheels").glob("*.whl"))
        if len(wheels) != 1:
            raise SystemExit("Expected exactly one CAC wheel; the prior wheel was preserved.")
        wheel = wheels[0]
        expected = {path.relative_to(source / "src").as_posix(): path
            for path in (source / "src/codex_auto_continuer").rglob("*") if path.is_file()}
        with zipfile.ZipFile(wheel) as archive:
            if archive.testzip() is not None or {
                name for name in archive.namelist() if name.startswith("codex_auto_continuer/")
            } != set(expected) or any(archive.read(name) != path.read_bytes() for name, path in expected.items()):
                raise SystemExit("Wheel does not match the exact current package files; the prior wheel was preserved.")
        args.out.mkdir(parents=True, exist_ok=True)
        target = args.out / wheel.name
        fd, name = tempfile.mkstemp(prefix="wheel-", suffix=".tmp", dir=args.out)
        temporary = Path(name)
        try:
            with os.fdopen(fd, "wb") as output:
                output.write(wheel.read_bytes())
                output.flush()
                os.fsync(output.fileno())
            replace_file(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        print(json.dumps({"wheel": wheel.name, "packageFiles": len(expected),
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "sourceMatch": True}))


if __name__ == "__main__":
    main()
