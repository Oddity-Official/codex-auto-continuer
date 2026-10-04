"""Check release identity, notices, source parity and Markdown targets without changing runtime."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import unquote

ROOT = next(path for path in Path(__file__).resolve().parents if (path / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))
from codex_auto_continuer import __version__


def main():
    broken = []
    for path in [ROOT / "README.md", *sorted((ROOT / "Docs").rglob("*.md"))]:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            target = target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (path.parent / unquote(target)).exists():
                broken.append(f"{path.relative_to(ROOT)}: {target}")
    assert not broken, "Broken Markdown targets:\n" + "\n".join(broken)
    portable = ROOT / f"dist/codex-auto-continuer-{__version__}-windows-x86_64.zip"
    with zipfile.ZipFile(portable) as bundle:
        assert bundle.testzip() is None
        manifest = json.loads(bundle.read("CodexAutoContinuer/RELEASE-MANIFEST.json"))
        assert manifest["version"] == __version__
        assert len(bundle.namelist()) == len(manifest["files"]) + 1
        for name, entry in manifest["files"].items():
            body = bundle.read("CodexAutoContinuer/" + name)
            assert len(body) == entry["bytes"] and hashlib.sha256(body).hexdigest() == entry["sha256"], name
        assert not any("/data/" in name or name.endswith((".jsonl", ".key")) for name in bundle.namelist())
        prefix = "CodexAutoContinuer/Licenses/pystray/pystray-0.19.5.dist-info/"
        assert bundle.read(prefix + "COPYING") and bundle.read(prefix + "COPYING.LGPL")
        assert bundle.read("CodexAutoContinuer/Licenses/pystray/source/pystray/_win32.py")
        assert bundle.read("CodexAutoContinuer/LICENSE") == (ROOT / "LICENSE").read_bytes()
        for path in [ROOT / "README.md", *sorted((ROOT / "Docs").rglob("*.md"))]:
            assert bundle.read("CodexAutoContinuer/" + path.relative_to(ROOT).as_posix()) == path.read_bytes(), path
    wheel = ROOT / f"dist/codex_auto_continuer-{__version__}-py3-none-any.whl"
    with zipfile.ZipFile(wheel) as package:
        modules = sorted((ROOT / "src/codex_auto_continuer").glob("*.py"))
        for module in modules:
            assert package.read("codex_auto_continuer/" + module.name) == module.read_bytes(), module
        metadata = package.read(f"codex_auto_continuer-{__version__}.dist-info/METADATA").decode()
        assert "Requires-Python: >=3.13" in metadata and "License-Expression: MIT" in metadata
        assert "Requires-Dist: pystray==0.19.5" in metadata and "Requires-Dist: Pillow<13,>=10" in metadata
        assert package.read(f"codex_auto_continuer-{__version__}.dist-info/licenses/LICENSE")
    print(json.dumps({"version": __version__, "portableFiles": len(manifest["files"]),
                      "wheelModules": len(modules), "hashes": "passed", "notices": "passed",
                      "runtimeExcluded": True, "markdownTargets": "passed"}, indent=2))


if __name__ == "__main__":
    main()
