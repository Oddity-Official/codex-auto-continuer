from __future__ import annotations

import importlib.util
import io
import tarfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "download-probe-codex.py"
spec = importlib.util.spec_from_file_location("download_probe_codex", SCRIPT)
download = importlib.util.module_from_spec(spec)
spec.loader.exec_module(download)


def archive(tmp_path, names, *, link=False):
    path = tmp_path / "package.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        for name in names:
            entry = tarfile.TarInfo(name)
            if link:
                entry.type = tarfile.SYMTYPE
                entry.linkname = "outside"
                tar.addfile(entry)
            else:
                entry.size = 3
                tar.addfile(entry, io.BytesIO(b"abc"))
    return path


@pytest.mark.parametrize("name", ["../escape.exe", "/absolute.exe", "C:/drive.exe", "bin\\codex.exe"])
def test_package_rejects_unsafe_paths_before_extracting(tmp_path, name):
    target = tmp_path / "target"
    with pytest.raises(ValueError, match="unsafe"):
        download.extract_package(archive(tmp_path, ["bin/codex.exe", name]), target)
    assert not target.exists()


def test_package_rejects_links_and_case_collisions(tmp_path):
    with pytest.raises(ValueError, match="unsafe"):
        download.extract_package(archive(tmp_path, ["bin/codex.exe"], link=True), tmp_path / "target")
    with pytest.raises(ValueError, match="colliding"):
        download.extract_package(archive(tmp_path, ["bin/codex.exe", "BIN/./codex.exe"]), tmp_path / "target")
    assert not (tmp_path / "target").exists()


def test_package_enforces_extracted_limit_and_accepts_normal_package(tmp_path, monkeypatch):
    path = archive(tmp_path, ["bin/codex.exe"])
    monkeypatch.setattr(download, "MAX_BYTES", 2)
    with pytest.raises(ValueError, match="limit"):
        download.extract_package(path, tmp_path / "target")
    monkeypatch.setattr(download, "MAX_BYTES", 100)
    download.extract_package(path, tmp_path / "target")
    assert (tmp_path / "target/bin/codex.exe").read_bytes() == b"abc"
