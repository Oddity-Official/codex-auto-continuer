"""Compare completed monitoring intervals; print only aggregate counts and sizes."""
import gzip
import json
import sys
from pathlib import Path


def intervals(path, version):
    parts = []
    size = count = 0
    previous_completion = False
    for line in path.read_bytes().splitlines(keepends=True):
        event = json.loads(line)
        if event.get("version") != version:
            continue
        size += len(line)
        count += 1
        if event["event"] == "cycle.completed":
            if previous_completion:
                parts.append({"bytes": size, "events": count, "chatsChecked": event["fields"]["scanned_threads"],
                              "dispatched": event["fields"]["dispatched"]})
            previous_completion = True
            size = count = 0
    recent = parts[-10:]
    assert recent
    return {"intervals": len(recent), "meanBytes": round(sum(p["bytes"] for p in recent) / len(recent), 1),
            "meanEvents": round(sum(p["events"] for p in recent) / len(recent), 1),
            "chatsChecked": sorted({p["chatsChecked"] for p in recent}),
            "dispatched": sum(p["dispatched"] for p in recent)}


old, current = map(Path, sys.argv[1:])
before = intervals(old, "0.2.1")
after = intervals(current, "0.3.0")
backup = current.with_name(current.name + ".1.gz")
assert gzip.decompress(backup.read_bytes()) == old.read_bytes()
print(json.dumps({"old": before, "new": after,
                  "observedByteReductionPercent": round(100 * (1 - after["meanBytes"] / before["meanBytes"]), 1),
                  "historicalLogBytes": old.stat().st_size, "compressedHistoricalBytes": backup.stat().st_size,
                  "compressedBackupExact": True, "comparison": "Same host, clients, poll interval and Detailed privacy; short observational sample, not a universal benchmark"}, indent=2))
