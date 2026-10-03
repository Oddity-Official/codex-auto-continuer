"""Bounded, read-only native daemon probe. Never stores conversation text."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
sys.path.insert(0, str(ROOT / "src"))

from codex_auto_continuer.appserver import AppServerClient
from codex_auto_continuer.codex import daemon_version, find_codex
from codex_auto_continuer.supervisor import _parse_rate_limits, _session_source_label


def main():
    daemon = daemon_version(find_codex(), 10)
    client = AppServerClient.connect(daemon.socket_path, 5)
    try:
        limits = _parse_rate_limits(client.rate_limits())
        threads = client.thread_list(limit=100)["data"]
        sources = {}
        originators = {}
        statuses = {}
        turns = []
        for thread in threads:
            source = _session_source_label(thread["source"])
            sources[source] = sources.get(source, 0) + 1
            originator = thread.get("originator")
            originators[str(originator)] = originators.get(str(originator), 0) + 1
            status = thread["status"]["type"]
            statuses[status] = statuses.get(status, 0) + 1
            if len(turns) < 12 and status != "active":
                turn = client.latest_turn(thread["id"])
                turns.append({
                    "source": source,
                    "threadStatus": status,
                    "turnFields": sorted(turn) if turn else [],
                    "turnStatus": turn.get("status") if turn else None,
                    "errorInfo": (turn.get("error") or {}).get("codexErrorInfo") if turn else None,
                    "completedAt": turn.get("completedAt") if turn else None,
                })
        print(json.dumps({
            "cliVersion": daemon.cli_version,
            "appServerVersion": daemon.app_server_version,
            "userAgent": client.user_agent,
            "ordinaryUsageAllowed": limits.ordinary_usage_allowed,
            "sources": sources, "originators": originators,
            "threadStatuses": statuses, "sampledTurns": turns,
        }, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
