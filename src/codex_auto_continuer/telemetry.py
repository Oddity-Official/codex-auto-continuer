from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import platform
import traceback
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from . import __version__
from .config import Config
from .errors import ConfigurationError

_IDENTIFIERS = {"threadId", "turnId", "failedTurnId", "clientUserMessageId", "queuedSubmissionId", "parentThreadId"}
_PERSONAL = {"name", "cwd", "path", "prompt_file", "codex_executable", "socketPath", "configPath", "executable", "userAgent"}
_ERROR_TAGS = {
    "contextWindowExceeded", "sessionBudgetExceeded", "usageLimitExceeded", "rateLimitExceeded",
    "flexUnavailable", "serverOverloaded", "cyberPolicy", "misalignmentPolicyViolation", "tooManyDenials",
    "internalServerError", "unauthorized", "badRequest", "threadRollbackFailed", "sandboxError", "other",
    "httpConnectionFailed", "responseStreamConnectionFailed", "responseStreamDisconnected",
    "responseTooManyFailedAttempts", "activeTurnNotSteerable",
}
_logger = logging.getLogger("codex_auto_continuer.events")
_logger.propagate = False


class EventFormatter(logging.Formatter):
    def __init__(self, detailed: bool, key: bytes):
        super().__init__()
        self.detailed = detailed
        self.key = key

    def protect(self, value: Any, field: str = "") -> Any:
        if not self.detailed and field in _PERSONAL:
            return None
        if not self.detailed and field in _IDENTIFIERS and isinstance(value, str):
            return "id:" + hmac.new(self.key, value.encode(), hashlib.sha256).hexdigest()[:20]
        if isinstance(value, dict):
            return {k: self.protect(v, k) for k, v in value.items() if self.detailed or k not in _PERSONAL}
        if isinstance(value, (list, tuple)):
            return [self.protect(v) for v in value]
        return value

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "schema": 1,
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "pid": os.getpid(), "version": __version__,
            "privacy": "detailed" if self.detailed else "private",
            "event": record.getMessage(),
            "fields": self.protect(getattr(record, "fields", {})),
        }, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def setup(path: Path, cfg: Config) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    key_file = path.parent / "telemetry.key"
    if not key_file.exists():
        try:
            with key_file.open("xb") as handle:
                handle.write(os.urandom(32))
        except FileExistsError:
            pass
    key = key_file.read_bytes()
    if len(key) != 32:
        raise ConfigurationError("Invalid telemetry.key; preserve it and inspect runtime data before restarting.")
    for handler in _logger.handlers[:]:
        handler.close()
        _logger.removeHandler(handler)
    handler = RotatingFileHandler(path, maxBytes=cfg.log_max_mb * 1024 * 1024, backupCount=cfg.log_backups, encoding="utf-8")
    handler.setFormatter(EventFormatter(cfg.detailed_telemetry, key))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False
    # Logging failures must not silently discard the only dispatch diagnostic.
    def fail(record):
        raise OSError("Cannot write local telemetry. Check free space and permissions before restarting.")
    handler.handleError = fail
    emit("process.started", python=platform.python_version(), os=platform.system(), osRelease=platform.release(),
         architecture=platform.machine(), executable=os.path.realpath(os.sys.executable))


def emit(event: str, **fields: Any) -> None:
    _logger.info(event, extra={"fields": fields})


def failure(event: str, exc: BaseException, **fields: Any) -> None:
    # Never serialize exception text or locals: either can contain credentials or conversation content.
    frames = [{"module": Path(frame.filename).name, "line": frame.lineno, "function": frame.name}
              for frame in traceback.extract_tb(exc.__traceback__)]
    emit(event, errorType=type(exc).__name__, frames=frames, **fields)


def thread_summary(thread: dict) -> dict:
    status = thread.get("status")
    return {key: thread.get(key) for key in
            ("source", "originator", "name", "cwd", "createdAt", "updatedAt", "archived", "modelProvider")} | {
        "threadId": thread.get("id"),
        "status": {key: status.get(key) for key in ("type", "activeFlags")} if isinstance(status, dict) else None,
    }


def turn_summary(turn: dict) -> dict:
    error = turn.get("error")
    info = error.get("codexErrorInfo") if isinstance(error, dict) else None
    http_status = None
    # Error info can be a structured enum. Keep verified tags and numeric status, never arbitrary payloads.
    if isinstance(info, dict):
        tag = next(iter(info), None)
        payload = info.get(tag)
        if isinstance(payload, dict) and type(payload.get("httpStatusCode")) is int:
            http_status = payload["httpStatusCode"]
        info = tag
    if info is not None and (not isinstance(info, str) or info not in _ERROR_TAGS):
        info = "unrecognized"
        http_status = None
    return {key: turn.get(key) for key in ("status", "startedAt", "completedAt", "durationMs")} | {
        "turnId": turn.get("id"), "errorInfo": info, "httpStatusCode": http_status,
    }


def rpc_summary(method: str, value: Any) -> dict:
    if not isinstance(value, dict):
        return {"resultType": type(value).__name__}
    if method == "account/rateLimits/read":
        def snapshot(item):
            if not isinstance(item, dict):
                return None
            out = {key: item.get(key) for key in ("limitId", "planType")}
            for name in ("primary", "secondary"):
                window = item.get(name)
                out[name] = ({key: window.get(key) for key in ("usedPercent", "windowDurationMins", "resetsAt")}
                             if isinstance(window, dict) else None)
            return out
        buckets = value.get("rateLimitsByLimitId")
        return {"ordinaryUsageAllowed": value.get("ordinaryUsageAllowed"), "rateLimits": snapshot(value.get("rateLimits")),
                "buckets": [snapshot(item) for item in buckets.values()] if isinstance(buckets, dict) else []}
    if method == "thread/list":
        return {"threads": [thread_summary(item) for item in value.get("data", []) if isinstance(item, dict)],
                "hasNextPage": value.get("nextCursor") is not None}
    if method in {"thread/read", "thread/resume"}:
        thread = value.get("thread")
        return {"thread": thread_summary(thread)} if isinstance(thread, dict) else {"threadPresent": False}
    if method == "thread/turns/list":
        return {"turns": [turn_summary(item) for item in value.get("data", []) if isinstance(item, dict)]}
    if method in {"thread/queue/add", "thread/queue/list"}:
        items = [value.get("queuedSubmission")] if method.endswith("add") else value.get("data", [])
        return {"queue": [{"queuedSubmissionId": item.get("id"), "clientUserMessageId": item.get("clientUserMessageId")}
                          for item in items if isinstance(item, dict)]}
    if method == "thread/queue/delete":
        return {"deleted": value.get("deleted")}
    if method == "initialize":
        return {"userAgent": value.get("userAgent")}
    return {"resultKeys": sorted(value)}


def rpc_request_fields(params: dict | None) -> dict:
    params = params or {}
    return {key: params[key] for key in
            ("threadId", "clientUserMessageId", "queuedSubmissionId", "limit", "itemsView", "includeTurns", "excludeTurns")
            if key in params}


def notification_summary(method: str, params: Any) -> dict:
    if not isinstance(params, dict):
        return {}
    result = {"threadId": params.get("threadId")}
    if method in {"turn/started", "turn/completed"} and isinstance(params.get("turn"), dict):
        result["turn"] = turn_summary(params["turn"])
    if method == "thread/status/changed" and isinstance(params.get("status"), dict):
        result["status"] = {key: params["status"].get(key) for key in ("type", "activeFlags")}
    if method == "thread/tokenUsage/updated" and isinstance(params.get("tokenUsage"), dict):
        usage = params["tokenUsage"]
        result["tokenUsage"] = {
            name: {key: value for key, value in usage[name].items() if type(value) is int}
            for name in ("total", "last") if isinstance(usage.get(name), dict)
        }
    return result
