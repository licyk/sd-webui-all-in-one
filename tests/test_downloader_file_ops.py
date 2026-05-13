import builtins
import os
import sys
import tarfile
import types
import zipfile
from pathlib import Path

import pytest

from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.downloader import archive_downloader
from sd_webui_all_in_one.downloader import downloader as downloader_module
from sd_webui_all_in_one.downloader.multi_thread import MultiThreadDownloader
from sd_webui_all_in_one.file_operations import archive_manager
from sd_webui_all_in_one.file_operations import file_manager


def test_download_file_falls_back_from_aria2_to_requests(monkeypatch, tmp_path):
    calls = []

    def fake_download_executer(url, path, save_name, tool, progress):
        calls.append((url, path, save_name, tool, progress))
        return path / (save_name or "download.bin")

    monkeypatch.setattr(downloader_module.shutil, "which", lambda name: None if name == "aria2c" else "/bin/tool")
    monkeypatch.setattr(downloader_module, "download_executer", fake_download_executer)

    result = downloader_module.download_file("https://example.test/file.bin", path=tmp_path / "downloads", save_name="x.bin", tool="aria2", progress=False)

    assert result == tmp_path / "downloads" / "x.bin"
    assert (tmp_path / "downloads").is_dir()
    assert calls == [("https://example.test/file.bin", tmp_path / "downloads", "x.bin", "requests", False)]


def test_download_file_falls_back_to_urllib_when_requests_missing(monkeypatch, tmp_path):
    calls = []
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "requests":
            raise ImportError("requests missing")
        return real_import(name, *args, **kwargs)

    def fake_download_executer(url, path, save_name, tool, progress):
        calls.append((tool, path))
        return path / (save_name or "download.bin")

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(downloader_module.shutil, "which", lambda name: None if name == "aria2c" else "/bin/tool")
    monkeypatch.setattr(downloader_module, "download_executer", fake_download_executer)

    result = downloader_module.download_file("https://example.test/file.bin", path=tmp_path / "downloads", tool="aria2")

    assert result == tmp_path / "downloads" / "download.bin"
    assert calls == [("urllib", tmp_path / "downloads")]


def test_download_archive_and_unpack_uses_url_name_and_wraps_errors(monkeypatch, tmp_path):
    calls = []

    def fake_download_file(url, path, save_name):
        calls.append(("download", url, path, save_name))
        archive = path / save_name
        archive.write_text("data", encoding="utf-8")
        return archive

    def fake_extract_archive(archive_path, extract_to):
        calls.append(("extract", archive_path.name, extract_to))

    monkeypatch.setattr(archive_downloader, "download_file", fake_download_file)
    monkeypatch.setattr(archive_downloader, "extract_archive", fake_extract_archive)

    archive_downloader.download_archive_and_unpack("https://example.test/releases/pkg.zip?download=1", tmp_path / "out")

    assert calls[0][0] == "download"
    assert calls[0][3] == "pkg.zip"
    assert calls[1] == ("extract", "pkg.zip", tmp_path / "out")

    monkeypatch.setattr(archive_downloader, "extract_archive", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad archive")))

    with pytest.raises(RuntimeError) as exc:
        archive_downloader.download_archive_and_unpack("https://example.test/pkg.zip", tmp_path / "out")

    assert "bad archive" in str(exc.value)


def test_multi_thread_downloader_runs_args_kwargs_and_aggregates_errors():
    calls = []

    def download(name, suffix=""):
        calls.append((name, suffix))

    downloader = MultiThreadDownloader(
        download_func=download,
        download_args_list=[["a"], ["b"]],
        download_kwargs_list=[{"suffix": "1"}, {"suffix": "2"}],
    )

    downloader.start(num_threads=2, retry_count=1)

    assert sorted(calls) == [("a", "1"), ("b", "2")]

    def always_fails(name):
        raise ValueError(name)

    failing = MultiThreadDownloader(download_func=always_fails, download_args_list=[["bad"]])

    with pytest.raises(AggregateError) as exc:
        failing.start(num_threads=1, retry_count=2)

    assert len(exc.value.exceptions) == 2


def test_file_operations_copy_move_remove_scan_and_sync(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("a", encoding="utf-8")
    nested = src / "nested"
    nested.mkdir()
    (nested / "b.txt").write_text("b", encoding="utf-8")

    copied = tmp_path / "copied"
    file_manager.copy_files(src, copied)
    assert (copied / "a.txt").read_text(encoding="utf-8") == "a"
    assert (copied / "nested" / "b.txt").read_text(encoding="utf-8") == "b"

    moved = tmp_path / "moved.txt"
    file_manager.move_files(copied / "a.txt", moved)
    assert moved.read_text(encoding="utf-8") == "a"
    assert not (copied / "a.txt").exists()

    files = {p.name for p in file_manager.get_file_list(src, show_progress=False)}
    assert files == {"a.txt", "b.txt"}

    dst = tmp_path / "dst"
    (dst / "nested").mkdir(parents=True)
    (dst / "a.txt").write_text("a", encoding="utf-8")
    missing = file_manager.get_sync_files(src, dst)
    assert [p.relative_to(src).as_posix() for p in missing] == ["nested/b.txt"]

    file_manager.sync_files(src, dst)
    assert (dst / "nested" / "b.txt").read_text(encoding="utf-8") == "b"

    file_manager.remove_files(moved)
    assert not moved.exists()


def test_sync_files_and_create_symlink_preserves_existing_link_contents(tmp_path):
    src = tmp_path / "drive" / "models"
    link = tmp_path / "workspace" / "models"
    link.mkdir(parents=True)
    (link / "old.txt").write_text("old", encoding="utf-8")

    file_manager.sync_files_and_create_symlink(src, link)

    assert link.is_symlink()
    assert link.resolve() == src.resolve()
    assert (src / "old.txt").read_text(encoding="utf-8") == "old"


def test_archive_manager_zip_tar_and_unsupported(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "rarfile", types.SimpleNamespace(RarFile=object))
    monkeypatch.setitem(sys.modules, "py7zr", types.SimpleNamespace(SevenZipFile=object))
    monkeypatch.setitem(sys.modules, "zstandard", types.SimpleNamespace(ZstdDecompressor=object))

    source = tmp_path / "source.txt"
    source.write_text("payload", encoding="utf-8")

    zip_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(source, arcname="source.txt")
    zip_out = tmp_path / "zip-out"
    archive_manager.extract_archive(zip_path, zip_out)
    assert (zip_out / "source.txt").read_text(encoding="utf-8") == "payload"

    tar_path = tmp_path / "sample.tar"
    with tarfile.open(tar_path, "w") as tf:
        tf.add(source, arcname="source.txt")
    tar_out = tmp_path / "tar-out"
    archive_manager.extract_archive(tar_path, tar_out)
    assert (tar_out / "source.txt").read_text(encoding="utf-8") == "payload"

    created_zip = tmp_path / "created.zip"
    archive_manager.create_archive([source], created_zip)
    assert archive_manager.is_supported_archive_format(created_zip) is True
    assert zipfile.is_zipfile(created_zip)

    with pytest.raises(ValueError):
        archive_manager.extract_archive(tmp_path / "bad.exe", tmp_path / "bad-out")

