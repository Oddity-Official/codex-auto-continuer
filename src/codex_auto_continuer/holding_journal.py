"""Account-bound encrypted inputs with serialized, atomic phase transitions."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

from .atomic import replace_file
from .errors import AlreadyRunningError, ConfigurationError
from .instance_lock import SingleInstanceLock
from .private_data import dpapi

MAX_BYTES = 32 * 1024 * 1024
PHASES = {"saved", "held", "release_requested", "submitted", "uncertain"}


def account_binding(home: Path) -> str:
    """Use only native account metadata; tokens are never retained or logged."""
    try:
        path = home / "auth.json"
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("Oversized native authentication metadata")
        raw = json.loads(path.read_text(encoding="utf-8"))
        account = raw.get("tokens", {}).get("account_id")
        if raw.get("auth_mode") != "chatgpt" or not isinstance(account, str) or not account:
            raise ValueError("Missing ChatGPT account identity")
        return hashlib.sha256((os.path.normcase(str(home.resolve())) + "\0" + account).encode()).hexdigest()
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        raise ConfigurationError("Queue holding cannot verify this Codex home's ChatGPT account metadata. "
            "Standard quota recovery remains available; sign in with locally available account metadata.") from exc


def _string(value):
    return isinstance(value, str) and 0 < len(value) <= 1024


def validate(raw):
    if not isinstance(raw, dict) or set(raw) != {"schema", "binding", "records", "threads"} or raw["schema"] != 1:
        raise ValueError("Invalid journal schema")
    if not isinstance(raw["binding"], str) or len(raw["binding"]) != 64:
        raise ValueError("Invalid account/home binding")
    records, threads = raw["records"], raw["threads"]
    if not isinstance(records, list) or len(records) > 1000 or not isinstance(threads, dict):
        raise ValueError("Invalid journal records")
    seen = set()
    for item in records:
        if (not isinstance(item, dict) or set(item) != {"id", "threadId", "clientUserMessageId", "anchorTurnId",
                "input", "phase", "releasedQueueId"} or
            not all(_string(item[k]) for k in ("id", "threadId", "clientUserMessageId", "anchorTurnId")) or
            item["id"] in seen or item["phase"] not in PHASES or
            (item["releasedQueueId"] is not None and not _string(item["releasedQueueId"])) or
            not isinstance(item["input"], list) or not item["input"] or
            any(not isinstance(p, dict) or not _string(p.get("type")) for p in item["input"])):
            raise ValueError("Invalid held input")
        seen.add(item["id"])
    for identity, item in threads.items():
        if (not _string(identity) or not isinstance(item, dict) or
            set(item) != {"authorizedTurnId", "recoveryIds", "paused"} or
            (item["authorizedTurnId"] is not None and not _string(item["authorizedTurnId"])) or
            not isinstance(item["recoveryIds"], list) or not all(_string(x) for x in item["recoveryIds"]) or
            len(item["recoveryIds"]) > 1000 or not isinstance(item["paused"], str) or len(item["paused"]) > 1024):
            raise ValueError("Invalid held thread metadata")
    if any(item["threadId"] not in threads for item in records):
        raise ValueError("Held input has no thread metadata")
    return raw


class Journal:
    def __init__(self, path: Path):
        self.path = path

    def _read(self, binding=None):
        if self.path.is_symlink() or self.path.is_junction():
            raise ConfigurationError("Refusing a redirected private holding journal.")
        if not self.path.exists():
            if binding is None:
                return None
            return {"schema": 1, "binding": binding, "records": [], "threads": {}}
        try:
            if self.path.stat().st_size > MAX_BYTES + 65536:
                raise ValueError("Oversized journal")
            raw = validate(json.loads(dpapi(self.path.read_bytes(), decrypt=True)))
            if binding is not None and raw["binding"] != binding:
                if raw["records"]:
                    raise ValueError("Account/home changed with inputs still held")
                raw["binding"] = binding
            return raw
        except (OSError, ValueError, TypeError, KeyError, ConfigurationError) as exc:
            raise ConfigurationError("Cannot safely open the private holding journal. Preserve held-inputs.dpapi; "
                "use the original Codex home/account and Windows account. Standard recovery must not bypass held inputs.") from exc

    def _write(self, raw):
        validate(raw)
        plain = json.dumps(raw, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()
        if len(plain) > MAX_BYTES:
            raise ConfigurationError("Private held inputs exceed 32 MiB. Review held requests before capturing more; native input was not deleted.")
        cipher = dpapi(plain)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".held-", dir=self.path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(cipher)
                stream.flush()
                os.fsync(stream.fileno())
            replace_file(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    @contextmanager
    def transaction(self, binding=None):
        lock = SingleInstanceLock(self.path.with_suffix(".lock"))
        deadline = time.monotonic() + 15
        while True:
            try:
                lock.acquire()
                break
            except AlreadyRunningError:
                if time.monotonic() >= deadline:
                    raise ConfigurationError("The holding journal is busy. Wait for the current operation, then retry.")
                time.sleep(0.02)
        try:
            raw = self._read(binding)
            yield raw
        finally:
            lock.release()

    def save(self, raw):
        self._write(raw)

    def read(self):
        with self.transaction() as raw:
            return raw

    def manage(self, action, identity=None):
        with self.transaction() as raw:
            if raw is None:
                return []
            if action == "discard":
                item = next((r for r in raw["records"] if r["id"] == identity), None)
                if item is None or item["phase"] != "held":
                    raise ConfigurationError("Only a confirmed, unsent held input can be discarded. Inspect unconfirmed requests in Codex first.")
                raw["records"].remove(item)
            elif action in {"confirm-unsent", "confirm-consumed"}:
                item = next((r for r in raw["records"] if r["id"] == identity), None)
                if item is None or item["phase"] not in {"saved", "uncertain", "release_requested"}:
                    raise ConfigurationError("Only an unconfirmed input can be explicitly resolved after reviewing Codex.")
                if action == "confirm-unsent":
                    item["phase"] = "held"
                    item["releasedQueueId"] = None
                else:
                    raw["records"].remove(item)
                raw["threads"][item["threadId"]]["paused"] = "Review completed; approve resuming remaining held requests."
            elif action == "resume":
                thread = raw["threads"].get(identity)
                if thread is None:
                    raise ConfigurationError("No held requests for that exact thread ID.")
                # The monitor binds this consent to the current terminal turn before releasing.
                thread["paused"] = "review_approved"
            else:
                raise ConfigurationError("Unknown held-request management action.")
            self.save(raw)
            return [{k: r[k] for k in ("id", "threadId", "phase")} for r in raw["records"]]
