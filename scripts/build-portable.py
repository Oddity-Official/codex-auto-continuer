"""Build a clean Windows portable ZIP; never copy a deployed application's data."""
from __future__ import annotations

import hashlib
import importlib.metadata
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
from codex_auto_continuer import __version__
from codex_auto_continuer.icon import tray_image


def main():
    if sys.platform != "win32":
        raise SystemExit("Build Windows releases on Windows. PyInstaller is not a cross-compiler.")
    stage_parent = ROOT / ".data/build-release"
    stage_parent.mkdir(parents=True, exist_ok=True)
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    # Rebuild all runtime states from the lossless master before freezing.
    import runpy
    runpy.run_path(str(ROOT / "scripts/render-icons.py"), run_name="__main__")
    with tempfile.TemporaryDirectory(prefix="release-", dir=stage_parent) as directory:
        stage = Path(directory)
        icon = stage / "continuer.ico"
        tray_image(size=256).save(icon, sizes=[(n, n) for n in (16, 24, 32, 48, 64, 128, 256)])
        env = os.environ | {"CAC_BUILD_ICON": str(icon)}
        process = subprocess.Popen([sys.executable, "-m", "PyInstaller", "--distpath", str(stage / "dist"),
                                    "--workpath", str(stage / "build"), str(ROOT / "scripts/portable.spec")],
                                   cwd=ROOT, env=env, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            if process.wait(timeout=300) != 0:
                raise SystemExit("PyInstaller failed; inspect its diagnostic above. The prior release was preserved.")
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=5,
                           creationflags=subprocess.CREATE_NO_WINDOW)
            process.wait(timeout=5)
            raise SystemExit("Build exceeded 300s; its process tree was stopped. The prior release was preserved.")
        bundle = stage / "dist/CodexAutoContinuer"
        shutil.copy2(ROOT / "Docs/USER-GUIDE.md", bundle / "README.md")
        shutil.copy2(ROOT / "LICENSE", bundle / "LICENSE")
        # Include original dependency notices, not just links to changing websites.
        notices = bundle / "Licenses"
        notices.mkdir()
        shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", notices / "Python-LICENSE.txt")
        for package in ("pystray", "Pillow", "six", "tomlkit", "PyInstaller"):
            dist = importlib.metadata.distribution(package)
            for item in dist.files or []:
                if "license" in str(item).lower() or Path(item).name.lower().startswith("copying"):
                    source = dist.locate_file(item)
                    if source.is_file():
                        target = notices / package / str(item)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, target)
        pystray_dist = importlib.metadata.distribution("pystray")
        for item in pystray_dist.files or []:
            if str(item).replace("\\", "/").startswith("pystray/") and str(item).endswith(".py"):
                target = notices / "pystray/source" / str(item)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(pystray_dist.locate_file(item), target)
        files = sorted(p for p in bundle.rglob("*") if p.is_file())
        manifest = {"version": __version__, "platform": "windows-x86_64",
                    "python": sys.version.split()[0], "dependencies": {
                        name: importlib.metadata.version(name) for name in ("pystray", "Pillow", "six", "tomlkit", "PyInstaller")
                    }, "files": {
            p.relative_to(bundle).as_posix(): {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in files}}
        (bundle / "RELEASE-MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        temporary = output / "portable.tmp"
        try:
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(bundle.rglob("*")):
                    if path.is_file():
                        archive.write(path, "CodexAutoContinuer/" + path.relative_to(bundle).as_posix())
            with zipfile.ZipFile(temporary) as archive:
                if archive.testzip() is not None:
                    raise SystemExit("Portable ZIP failed CRC validation; prior release preserved.")
                for name, entry in manifest["files"].items():
                    payload = archive.read("CodexAutoContinuer/" + name)
                    if len(payload) != entry["bytes"] or hashlib.sha256(payload).hexdigest() != entry["sha256"]:
                        raise SystemExit("Portable ZIP checksum mismatch; prior release preserved.")
                if any("/data/" in name or "/Docs/" in name or "/resvg_py/" in name
                       or name.endswith((".key", ".jsonl")) for name in archive.namelist()):
                    raise SystemExit("Refusing runtime data in a shareable release.")
            target = output / f"codex-auto-continuer-{__version__}-windows-x86_64.zip"
            os.replace(temporary, target)
            print(f"Portable ZIP: {target}\nSHA-256: {hashlib.sha256(target.read_bytes()).hexdigest()}")
        finally:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
