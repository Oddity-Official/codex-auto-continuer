import os

import pytest

from codex_auto_continuer.presentation import (icon_state, state_label, usage_snapshot,
    usage_windows, thread_title, pending_count, UsageWindow)


def test_small_high_dpi_work_area_preserves_footer_and_scrolling():
    from codex_auto_continuer.presentation import thread_list_capacity
    assert thread_list_capacity(1040, 1, 348, 56) == 4
    assert thread_list_capacity(1040, 2, 310, 48) == 2
    assert thread_list_capacity(1040, 2, 358, 48) == 1


def test_obligation_completion_between_snapshot_and_state_read_is_monitoring():
    snapshot = {"pending": 1, "waitingThreads": []}
    assert state_label("waiting", snapshot) == "Monitoring"
    assert icon_state("waiting", snapshot) == ("monitoring", 0)


def test_unrepresentable_authoritative_reset_is_explicitly_unknown():
    assert UsageWindow("5H", 73, 1e300).reset() == "Reset Unknown"
    assert UsageWindow("7D", 41, -1e300).reset() == "Reset Unknown"


def test_unique_thread_wording_and_icon_precedence():
    for count in (0, 1, 2, 3, 4, 9):
        snapshot = {"waitingThreads": [{"threadId": str(n), "phase": "pending"} for n in range(count)],
                    "ordinary_usage_allowed": False}
        if count:
            snapshot["waitingThreads"].append(snapshot["waitingThreads"][0])
        assert pending_count(snapshot) == count
        assert state_label("waiting" if count else "monitoring", snapshot) == (
            f"Waiting For Usage • {count} {'Thread' if count == 1 else 'Threads'}" if count else "Monitoring")
        assert icon_state("monitoring", snapshot) == ("waiting" if count else "monitoring", min(count, 4))
        assert icon_state("stopped", snapshot) == ("stopped", min(count, 4))
        assert icon_state("failed", snapshot) == ("failed", min(count, 4))
    assert icon_state("monitoring", {"warnings": [{"code": "submission_uncertain"}]}) == ("failed", 0)
    assert icon_state("reconnecting", {}) == ("stopped", 0)
    assert icon_state("monitoring", {"compatibility": {"status": "untested"}}) == ("monitoring", 0)


def test_authoritative_ordinary_usage_uses_duration_and_remaining():
    raw = {"rateLimits": {"limitId": "other", "primary": {"usedPercent": 1, "windowDurationMins": 300}},
           "rateLimitsByLimitId": {"codex": {"secondary": {"windowDurationMins": 300, "usedPercent": 27, "resetsAt": 1234},
                                              "primary": {"windowDurationMins": 10080, "usedPercent": 59}}}}
    usage = usage_snapshot(raw, 100)
    windows = usage_windows({"usage": usage}, "monitoring", now=110)
    assert windows[0].remaining == 73 and windows[0].resets_at == 1234
    assert windows[1].percentage(explicit=True) == "41% Remaining"
    assert windows[1].reset() == "Reset Unknown"
    assert not windows[0].stale
    assert usage_windows({"usage": usage}, "reconnecting", now=110)[0].stale
    assert usage_windows({"usage": usage}, "monitoring", now=1000)[0].stale
    assert usage_snapshot({"rateLimits": raw["rateLimits"]}, 100)["windows"] == {}
    assert usage_windows({}, "monitoring")[0].percentage() == "Unavailable"


@pytest.mark.parametrize("used", [None, True, -1, 101, float("nan"), "27"])
def test_unknown_usage_does_not_invent_capacity(used):
    raw = {"rateLimits": {"primary": {"windowDurationMins": 300, "usedPercent": used, "resetsAt": 123}}}
    window = usage_windows({"usage": usage_snapshot(raw, 100)}, "monitoring", now=100)[0]
    assert window.remaining is None and window.resets_at == 123


def test_titles_only_use_authoritative_names():
    assert thread_title(None) == "Untitled Thread"
    assert thread_title(None, available=False) == "Title Unavailable"
    long = "A long title " * 100
    assert thread_title(long) == long  # GDI ellipsizes visually; details keep the full name.


@pytest.mark.skipif(os.name != "nt", reason="Win32 rendering palette")
def test_menu_states_are_distinct_and_disabled_hover_does_not_enable():
    from codex_auto_continuer.windows_ui import row_palette
    assert len({row_palette(), row_palette(selected=True), row_palette(hovered=True), row_palette(disabled=True)}) == 4
    assert row_palette(disabled=True, hovered=True) == row_palette(disabled=True)


def test_status_read_retries_sharing_error_but_does_not_hide_corrupt_json(tmp_path, monkeypatch):
    from pathlib import Path
    from codex_auto_continuer.status import read_runtime
    from codex_auto_continuer.errors import AutoContinuerError
    path = tmp_path / "runtime-status.json"
    path.write_text('{"phase":"monitoring"}')
    original = Path.read_text
    attempts = []
    def read(self, *args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise PermissionError("sharing lock")
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read)
    assert read_runtime(tmp_path / "settings.toml")["phase"] == "monitoring"
    assert len(attempts) == 2
    path.write_text('{bad')
    with pytest.raises(AutoContinuerError) as caught:
        read_runtime(tmp_path / "settings.toml")
    assert type(caught.value.__cause__).__name__ == "JSONDecodeError"


def test_private_telemetry_protects_new_presentation_thread_ids():
    import json
    import logging
    from codex_auto_continuer.telemetry import EventFormatter
    record = logging.LogRecord("events", 20, "test", 1, "cycle.completed", (), None)
    record.fields = {"waitingThreads": [{"threadId": "PRIVATE_ID", "phase": "pending"}]}
    encoded = EventFormatter(False, b"a" * 32).format(record)
    assert "PRIVATE_ID" not in encoded
    assert json.loads(encoded)["fields"]["waitingThreads"][0]["threadId"].startswith("id:")


@pytest.mark.skipif(os.name != "nt", reason="Win32 status panel")
def test_closed_status_view_cannot_retain_or_publish_titles():
    import threading
    from codex_auto_continuer.status_window import StatusWindow
    panel = StatusWindow(lambda: {}, lambda ids: {}, lambda exc: None)
    stopped = threading.Event()
    stopped.set()
    panel._publish({}, {"id": "Private Title"}, stopped)
    assert panel.updates.empty()
    obsolete = threading.Event()
    panel._publish({}, {"id": "Private Title"}, obsolete)
    assert panel.updates.empty()
