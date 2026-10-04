"""Generate a sanitized schema report, never a behavioral certificate."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from codex_auto_continuer import __version__
from codex_auto_continuer.codex import _run, codex_version, find_codex
from codex_auto_continuer.compatibility import RECORD, contract_digest, schema_contract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-executable", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--refresh-contract", action="store_true", help="Developer-only: replace the generated contract, not certificates. Review the diff.")
    args = parser.parse_args()
    binary = find_codex(args.codex_executable)
    version = codex_version(binary, 10)
    stage = ROOT / ".data"
    stage.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="schema-", dir=stage) as temporary:
        result = _run(binary, ["app-server", "generate-json-schema", "--experimental", "--out", temporary], 20)
        if result.returncode:
            raise SystemExit("Codex experimental schema generation failed.")
        contract = schema_contract(Path(temporary))
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    changed = [key for key in contract if contract[key] != record["contract"][key]]
    digest = contract_digest(contract)
    with Path(binary).open("rb") as stream:
        binary_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    report = {"cac_version": __version__, "codex_version": version, "binary_sha256": binary_hash,
        "schema_sha256": digest, "changed_methods": changed, "behavior_certified": False}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.refresh_contract:
        record["contract"] = contract
        RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if changed and not args.refresh_contract else 0


if __name__ == "__main__":
    raise SystemExit(main())
