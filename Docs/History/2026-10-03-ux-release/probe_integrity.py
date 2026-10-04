"""Verify source-wheel parity and live release boundaries without opening user content."""
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
            if target and "://" not in target and not target.startswith("mailto:"):
                if not (path.parent / unquote(target)).exists():
                    broken.append(f"{path.relative_to(ROOT)}: {target}")
    assert not broken, broken
    wheel = ROOT / f"dist/codex_auto_continuer-{__version__}-py3-none-any.whl"
    with zipfile.ZipFile(wheel) as package:
        assert package.testzip() is None
        sources = [*sorted((ROOT / "src/codex_auto_continuer").glob("*.py")),
                   *sorted((ROOT / "src/codex_auto_continuer/assets").iterdir())]
        for module in sources:
            assert package.read(module.relative_to(ROOT / "src").as_posix()) == module.read_bytes(), module
        metadata = package.read(f"codex_auto_continuer-{__version__}.dist-info/METADATA").decode()
        assert "Requires-Dist: tomlkit<1,>=0.13" in metadata and "License-Expression: MIT" in metadata
        assert ("# Codex Auto Continuer" in metadata) and ("settings.toml" in metadata)
    manifest = json.loads((ROOT / "App/RELEASE-MANIFEST.json").read_text())
    for name, entry in manifest["files"].items():
        body = (ROOT / "App" / name).read_bytes()
        assert hashlib.sha256(body).hexdigest() == entry["sha256"] and len(body) == entry["bytes"], name
    assert not (ROOT / "App/Docs").exists()
    assert not (ROOT / "App/data/config.json").exists()
    print(json.dumps({"version": __version__, "deployedReleaseFiles": len(manifest["files"]),
                      "wheelSourceAndAssetParity": True, "markdownTargets": "passed",
                      "repositoryDocsExcluded": True, "obsoleteActiveJsonExcluded": True}, indent=2))


if __name__ == "__main__":
    main()
