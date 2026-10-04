"""Bootstrap a signed update for a portable build that predates the updater."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from codex_auto_continuer.config import load_config
from codex_auto_continuer.updates import check_release, launch_update, parse_json, version, write_json
from codex_auto_continuer.update_install import no_links


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--tray-pid", type=int)
    parser.add_argument("--private", action="store_true", help="Use the existing gh login for this private publisher.")
    args = parser.parse_args()
    no_links(args.app)
    app, config = args.app.resolve(strict=True), args.config.resolve()
    result = subprocess.run([str(app / "CodexAutoContinuer-CLI.exe"), "--version"], capture_output=True,
        timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=True)
    installed = result.stdout.decode("utf-8").strip()
    version(installed)
    manifest = parse_json((app / "RELEASE-MANIFEST.json").read_bytes())
    if manifest["version"] != installed:
        raise SystemExit("Installed EXE and release manifest versions differ. Resolve that mismatch before bootstrapping an update.")
    cfg = replace(load_config(config), update_use_github_cli_auth=args.private)
    report = check_release(config, cfg, stage=True, app_root=app, installed_version=installed)
    write_json(config.parent / "update-status.json", report)
    if report["status"] == "staged":
        launch_update(Path(report["job"]), args.tray_pid)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
