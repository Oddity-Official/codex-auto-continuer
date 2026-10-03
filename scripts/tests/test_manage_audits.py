"""Regression checks for archive retention and deletion safety."""

from datetime import date, datetime
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

spec = importlib.util.spec_from_file_location("manage_audits", Path(__file__).parents[1] / "manage-audits.py")
audits = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audits)


def clock(day):
    return datetime.fromisoformat(f"{day}T12:00:00+00:00")


def folder(root, name, archived=False):
    path = root / "History" / name if archived else root / name
    path.mkdir(parents=True)
    (path / "AUDIT.md").write_text("report", encoding="utf-8")
    (path / "probe.py").write_text("probe", encoding="utf-8")
    (path / "nested").mkdir()
    (path / "nested" / "AUDIT.md").write_text("not the root report", encoding="utf-8")
    return path


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_start_rotates_and_same_day_suffix_survives_history(tmp_path):
    root = tmp_path / "Audits"
    folder(root, "2026-09-29", archived=True)
    current = folder(root, "2026-09-29-02")
    new = audits.maintain(root, "start", date(2026, 9, 29), clock("2026-09-29"))
    assert new.name == "2026-09-29-03"
    assert (new / "AUDIT.md").is_file()
    assert not current.exists()
    assert (root / "History" / current.name / "probe.py").read_text() == "probe"


def test_archive_collision_fails_before_any_change(tmp_path):
    folder(tmp_path, "2026-09-29")
    folder(tmp_path, "2026-09-29", archived=True)
    before = snapshot(tmp_path)
    with pytest.raises(audits.AuditError, match="collision"):
        audits.maintain(tmp_path, "start", date(2026, 9, 29), clock("2026-09-29"))
    assert snapshot(tmp_path) == before


def test_weekly_boundary_preserves_report_and_current_audit(tmp_path):
    current = folder(tmp_path, "2020-01-01")
    seven = folder(tmp_path, "2026-09-22", archived=True)
    eight = folder(tmp_path, "2026-09-21", archived=True)
    audits.maintain(tmp_path, now=clock("2026-09-29"))
    assert (current / "probe.py").is_file()
    assert (seven / "probe.py").is_file()
    assert list(eight.iterdir()) == [eight / "AUDIT.md"]


def test_monthly_check_uses_persisted_time_not_every_run(tmp_path):
    old = folder(tmp_path, "2026-08-29", archived=True)
    audits.maintain(tmp_path, now=clock("2026-09-29"))
    assert old.exists()  # Exactly one calendar month old.
    audits.maintain(tmp_path, now=clock("2026-10-01"))
    assert old.exists()  # Monthly check is not due yet.
    state = json.loads((tmp_path / audits.STATE).read_text())
    assert state["last_run_utc"].startswith("2026-10-01")
    assert state["last_monthly_cleanup_utc"].startswith("2026-09-29")
    audits.maintain(tmp_path, now=clock("2026-10-29"))
    assert not old.exists()


@pytest.mark.parametrize(("start", "expected"), [
    (date(2024, 1, 31), date(2024, 2, 29)),
    (date(2025, 1, 31), date(2025, 2, 28)),
    (date(2026, 12, 31), date(2027, 1, 31)),
])
def test_calendar_month_boundaries(start, expected):
    assert audits.next_month(start) == expected


def test_dry_run_does_not_rotate_prune_or_advance_state(tmp_path):
    folder(tmp_path, "2026-09-29")
    folder(tmp_path, "2020-01-01", archived=True)
    before = snapshot(tmp_path)
    audits.maintain(tmp_path, "start", date(2026, 9, 29), clock("2026-09-29"), dry_run=True)
    assert snapshot(tmp_path) == before
    missing = tmp_path / "missing"
    audits.maintain(missing, now=clock("2026-09-29"), dry_run=True)
    assert not missing.exists()


@pytest.mark.parametrize("value", ["broken", "{}", '{"version": 42}', json.dumps({
    "version": 1, "last_run_utc": "2030-01-01T12:00:00+00:00",
    "last_monthly_cleanup_utc": "2030-01-01T12:00:00+00:00",
}), json.dumps({
    "version": 1, "last_run_utc": "2026-09-01T12:00:00",
    "last_monthly_cleanup_utc": "2026-09-01T12:00:00",
})])
def test_invalid_state_fails_closed(tmp_path, value):
    folder(tmp_path, "2020-01-01", archived=True)
    (tmp_path / audits.STATE).write_text(value)
    before = snapshot(tmp_path)
    with pytest.raises(audits.AuditError, match="Invalid retention state"):
        audits.maintain(tmp_path, now=clock("2026-09-29"))
    assert snapshot(tmp_path) == before


def test_unrecognised_or_reportless_directory_is_not_deleted(tmp_path):
    folder(tmp_path, "2020-01-01", archived=True)
    suspect = tmp_path / "History" / "2020-02-30"
    suspect.mkdir()
    before = snapshot(tmp_path)
    with pytest.raises(audits.AuditError, match="Invalid audit folder date"):
        audits.maintain(tmp_path, now=clock("2026-09-29"))
    assert suspect.is_dir()
    suspect.rename(suspect.with_name("2020-02-28"))
    with pytest.raises(audits.AuditError, match="must contain AUDIT.md"):
        audits.maintain(tmp_path, now=clock("2026-09-29"))
    assert snapshot(tmp_path) == before


def test_busy_lock_and_failed_deletion_do_not_advance_state(tmp_path, monkeypatch):
    folder(tmp_path, "2020-01-01", archived=True)
    lock = tmp_path / audits.LOCK
    lock.write_text("pid=1")
    with pytest.raises(audits.AuditError, match="locked"):
        audits.maintain(tmp_path, now=clock("2026-09-29"))
    assert lock.read_text() == "pid=1"
    lock.unlink()

    def denied(*args):
        raise PermissionError("denied")

    monkeypatch.setattr(audits.shutil, "rmtree", denied)
    with pytest.raises(PermissionError):
        audits.maintain(tmp_path, now=clock("2026-09-29"))
    assert not (tmp_path / audits.STATE).exists()
    assert not lock.exists()


def test_linked_archive_cannot_delete_external_files(tmp_path):
    root = tmp_path / "Audits"
    old = folder(root, "2020-01-01", archived=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "keep.txt"
    sentinel.write_text("keep")
    link = old / "linked"
    if audits.os.name == "nt":
        command = f"New-Item -ItemType Junction -Path '{str(link).replace(chr(39), chr(39)*2)}' -Target '{str(outside).replace(chr(39), chr(39)*2)}' | Out-Null"
        result = subprocess.run(["pwsh", "-NoProfile", "-Command", command], capture_output=True, timeout=15)
        assert result.returncode == 0, result.stderr
    else:
        link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(audits.AuditError, match="linked/reparse"):
        audits.maintain(root, now=clock("2026-09-29"))
    assert sentinel.read_text() == "keep"
    assert (old / "AUDIT.md").is_file()
