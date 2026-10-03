"""Rotate audit workspaces and apply bounded, calendar-based retention."""

import argparse
import calendar
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent / "Docs" / "Audits"
STATE = ".maintenance.json"
LOCK = ".audit.lock"
NAME = re.compile(r"(\d{4}-\d{2}-\d{2})(?:-([0-9]{2,}))?\Z")


class AuditError(Exception):
    pass


def next_month(value):
    year = value.year + (value.month == 12)
    month = value.month % 12 + 1
    return value.replace(year=year, month=month,
                         day=min(value.day, calendar.monthrange(year, month)[1]))


def audit_date(name):
    match = NAME.fullmatch(name)
    if not match or (match[2] and (int(match[2]) < 2 or f"{int(match[2]):02d}" != match[2])):
        raise AuditError(f"Unrecognised audit folder: {name}. Use YYYY-MM-DD or YYYY-MM-DD-02.")
    try:
        return date.fromisoformat(match[1])
    except ValueError as error:
        raise AuditError(f"Invalid audit folder date: {name}.") from error


def check_plain(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise AuditError(f"Refusing linked/reparse path: {path}. Move real audit files here instead.")
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise AuditError(f"Unsupported filesystem entry: {path}.")


def check_tree(path, root):
    if not path.absolute().is_relative_to(root.absolute()) or path == root:
        raise AuditError(f"Unsafe maintenance target: {path}.")
    check_plain(path)
    if path.is_dir():
        for child in path.iterdir():
            check_tree(child, root)


def inventory(root):
    # Check ancestors too: resolving a junction before inspection would hide it.
    for path in reversed((root, *root.parents)):
        if path.exists() or path.is_symlink():
            check_plain(path)
    if not root.exists():
        return [], []
    active, archived = [], []
    for child in root.iterdir():
        check_tree(child, root)
        if child.name == "History":
            if not child.is_dir():
                raise AuditError(f"History must be a directory: {child}.")
            for old in child.iterdir():
                if old.name == ".gitkeep" and old.is_file():
                    continue
                audit_date(old.name)
                archived.append(old)
        elif child.name in {"README.md", ".gitattributes", STATE, LOCK} and child.is_file():
            continue
        else:
            audit_date(child.name)
            active.append(child)
    for folder in active + archived:
        if not folder.is_dir() or not (folder / "AUDIT.md").is_file():
            raise AuditError(f"Audit folder must contain AUDIT.md: {folder}. Restore the report before retrying.")
    return sorted(active), sorted(archived)


def read_state(root, now):
    path = root / STATE
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if set(value) != {"version", "last_run_utc", "last_monthly_cleanup_utc"} or value["version"] != 1:
            raise ValueError("unsupported state schema")
        times = {key: datetime.fromisoformat(value[key]) for key in
                 ("last_run_utc", "last_monthly_cleanup_utc")}
        if any(t.utcoffset() != timedelta(0) or t > now for t in times.values()):
            raise ValueError("timestamps must be UTC and not in the future")
        if times["last_monthly_cleanup_utc"] > times["last_run_utc"]:
            raise ValueError("monthly cleanup is later than last run")
        return times
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise AuditError(f"Invalid retention state at {path}: {error}. Restore a valid state; do not reset it blindly.") from error


def make_plan(root, command, started, now):
    active, archived = inventory(root)
    previous = read_state(root, now)
    monthly = previous is None or now >= next_month(previous["last_monthly_cleanup_utc"])
    moves, new = [], None
    if command == "start":
        if started > now.date() + timedelta(days=1):
            raise AuditError("The audit date is in the future. Use today's date in the user's timezone.")
        used = {folder.name for folder in active + archived}
        name, suffix = started.isoformat(), 2
        while name in used:
            name = f"{started.isoformat()}-{suffix:02d}"
            suffix += 1
        new = root / name
        for folder in active:
            destination = root / "History" / folder.name
            if destination.exists():
                raise AuditError(f"Archive collision at {destination}. Rename the conflicting audit before retrying.")
            moves.append((folder, destination))
        archived += active
    actions = []
    for folder in sorted(archived):
        destination = root / "History" / folder.name
        born = audit_date(folder.name)
        if monthly and now.date() > next_month(born):
            actions.append(("remove archive", folder, destination))
        elif (now.date() - born).days > 7:
            for child in folder.iterdir():
                if child.name != "AUDIT.md":
                    actions.append(("prune support", child, destination / child.name))
    return moves, new, actions, monthly, previous


@contextmanager
def maintenance_lock(root):
    path = root / LOCK
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise AuditError(f"Audit maintenance is locked at {path}. Check its PID; remove a stale lock only after confirming no run is active.") from error
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as handle:
            handle.write(f"pid={os.getpid()}\n")
        yield
    finally:
        path.unlink()


def write_state(root, now, monthly, previous):
    value = {"version": 1, "last_run_utc": now.isoformat(),
             "last_monthly_cleanup_utc": (now if monthly else previous["last_monthly_cleanup_utc"]).isoformat()}
    descriptor, name = tempfile.mkstemp(prefix=".maintenance-", suffix=".tmp", dir=root)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, root / STATE)
    finally:
        Path(name).unlink(missing_ok=True)


def maintain(root=ROOT, command="cleanup", started=None, now=None, dry_run=False):
    root = Path(root).absolute()
    now = now or datetime.now(timezone.utc)
    if now.utcoffset() != timedelta(0):
        raise AuditError("Maintenance time must be timezone-aware UTC.")
    if command not in {"start", "cleanup"} or (command == "start" and started is None):
        raise AuditError("Start requires an explicit audit date.")
    # Preflight before even creating a lock or missing directory.
    plan = make_plan(root, command, started, now)
    if dry_run:
        describe(plan, dry_run=True)
        return plan[1]
    root.mkdir(parents=True, exist_ok=True)
    with maintenance_lock(root):
        plan = make_plan(root, command, started, now)
        moves, new, actions, monthly, previous = plan
        (root / "History").mkdir(exist_ok=True)
        for source, destination in moves:
            check_tree(source, root)
            source.rename(destination)
        if new:
            new.mkdir()
            (new / "AUDIT.md").write_text(
                f"# {root.parent.parent.name} audit\n\nAudit date: {started}\nStarted at: {now.isoformat()}\n",
                encoding="utf-8", newline="\n")
        for _, _, destination in actions:
            check_tree(destination, root)
            if destination.is_dir():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        write_state(root, now, monthly, previous)
        describe(plan)
    return new


def describe(plan, dry_run=False):
    moves, new, actions, monthly, _ = plan
    prefix = "Would " if dry_run else "Completed: "
    for source, destination in moves:
        print(f"{prefix}archive {source} -> {destination}")
    if new:
        print(f"{prefix}start {new}")
    for action, _, destination in actions:
        print(f"{prefix}{action}: {destination}")
    print(f"Monthly retention {'due' if monthly else 'not due'}; "
          f"{len(actions)} deletion target(s). {'No changes made.' if dry_run else 'Retention state saved.'}")


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("start", "cleanup"))
    parser.add_argument("--date", type=date.fromisoformat, help="Audit date in the user's timezone; required for start.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without changing files or state.")
    args = parser.parse_args()
    if args.command == "start" and args.date is None:
        parser.error("start requires --date YYYY-MM-DD")
    if args.command == "cleanup" and args.date is not None:
        parser.error("--date applies only to start")
    try:
        maintain(command=args.command, started=args.date, dry_run=args.dry_run)
    except (AuditError, OSError) as error:
        print(f"Audit maintenance failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
