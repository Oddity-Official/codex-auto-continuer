"""Presentation derived from canonical recovery state, without conversation storage."""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UsageWindow:
    label: str
    remaining: float | None = None
    resets_at: float | None = None
    stale: bool = False

    def percentage(self, *, explicit=False):
        if self.remaining is None:
            return "Unavailable"
        return f"{self.remaining:g}%" + (" Remaining" if explicit else "")

    def reset(self, now=None):
        if self.resets_at is None:
            return "Reset Unknown"
        try:
            local = datetime.fromtimestamp(self.resets_at).astimezone()
        except (ValueError, OverflowError, OSError):
            return "Reset Unknown"
        current = datetime.fromtimestamp(time.time() if now is None else now).astimezone()
        clock = local.strftime("%I:%M %p").lstrip("0")
        date = local.strftime("%b ") + str(local.day)
        if local.year != current.year:
            date += f", {local.year}"
        return (clock if local.date() == current.date() else f"{date}, {clock}") if self.label == "5H" else date


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def usage_snapshot(raw: dict, observed_at: float) -> dict:
    # The ordinary Codex bucket is explicit; never borrow a model-specific quota.
    buckets = raw.get("rateLimitsByLimitId") or {}
    bucket = buckets.get("codex") if isinstance(buckets, dict) else None
    if not isinstance(bucket, dict):
        candidate = raw.get("rateLimits")
        bucket = candidate if isinstance(candidate, dict) and candidate.get("limitId") in (None, "codex") else {}
    windows = {}
    for key in ("primary", "secondary"):
        window = bucket.get(key)
        if not isinstance(window, dict):
            continue
        duration = window.get("windowDurationMins")
        label = {300: "5H", 10080: "7D"}.get(duration) if type(duration) is int else None
        if label is None:
            continue
        used, reset = window.get("usedPercent"), window.get("resetsAt")
        windows[label] = {"remaining": round(100 - used, 1) if finite(used) and 0 <= used <= 100 else None,
                          "resetsAt": reset if finite(reset) else None}
    return {"observedAt": observed_at, "windows": windows}


def usage_windows(snapshot, state, *, now=None, poll_seconds=30):
    now = time.time() if now is None else now
    usage = snapshot.get("usage") or (snapshot.get("lastScan") or {}).get("usage") or {}
    observed = usage.get("observedAt")
    stale = state in {"stopped", "paused", "failed", "reconnecting", "starting"} or not finite(observed) or now - observed > max(60, poll_seconds * 2)
    values = usage.get("windows") or {}
    return tuple(UsageWindow(label, values.get(label, {}).get("remaining"),
                             values.get(label, {}).get("resetsAt"), stale) for label in ("5H", "7D"))


def pending_threads(obligations):
    return tuple({"threadId": item.thread_id, "phase": item.phase} for item in obligations)


def pending_count(snapshot):
    if "waitingThreads" in snapshot:
        return len({row["threadId"] for row in snapshot["waitingThreads"]})
    return max(0, snapshot.get("pending", 0))


def needs_attention(state, snapshot):
    return state == "failed" or any(w.get("code") == "submission_uncertain" for w in snapshot.get("warnings", []))


def state_label(state, snapshot):
    count = pending_count(snapshot)
    if needs_attention(state, snapshot):
        label = "Needs Attention"
    elif state in {"stopped", "paused"}:
        return "Stopped"
    elif state in {"starting", "reconnecting"}:
        return "Starting" if state == "starting" else "Reconnecting"
    elif count and (snapshot.get("ordinary_usage_allowed") is True or any(
            row["phase"] != "pending" for row in snapshot.get("waitingThreads", []))):
        label = "Resuming"
    elif count:
        label = "Waiting For Usage"
    else:
        return {"monitoring": "Monitoring", "waiting": "Monitoring", "scanning": "Scanning",
                "starting": "Starting", "reconnecting": "Reconnecting"}[state]
    return label + (f" • {count} {'Thread' if count == 1 else 'Threads'}" if count else "")


def icon_state(state, snapshot):
    count = pending_count(snapshot)
    arrow = ("failed" if needs_attention(state, snapshot) else "stopped" if state in {
        "stopped", "paused", "starting", "reconnecting"} else "waiting" if count else "monitoring")
    return arrow, min(4, count)


def thread_reason(row):
    return {"pending": "Waiting For Usage", "dispatching": "Reconciling",
            "submitted": "Resuming", "uncertain": "Send Unconfirmed — Checking Whether Codex Accepted It"}[row["phase"]]


def thread_title(name, *, available=True):
    if not available:
        return "Title Unavailable"
    return name if isinstance(name, str) and name.strip() else "Untitled Thread"


def thread_list_capacity(work_height, scale, content_top, row_height):
    # Reserve the footer, native frame and a small work-area margin.
    return max(1, min(4, int((work_height / scale - content_top - 110) / row_height)))
