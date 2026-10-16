"""下载入口与下载器回退测试"""

import builtins
import sys
import types

import pytest

from sd_webui_all_in_one.downloader import downloader as downloader_module
from sd_webui_all_in_one.downloader.requests_downloader import models as requests_models


def test_download_file_falls_back_from_aria2_to_requests(monkeypatch, tmp_path):
    calls = []

    def fake_download_executer(url, path, save_name, tool, progress, **_kwargs):
        calls.append((url, path, save_name, tool, progress))
        return path / (save_name or "download.bin")

    monkeypatch.setitem(sys.modules, "requests", types.ModuleType("requests"))
    monkeypatch.setattr(downloader_module, "resolve_aria2_server_class", lambda: None)
    monkeypatch.setattr(downloader_module, "download_executer", fake_download_executer)

    result = downloader_module.download_file("https://example.test/file.bin", path=tmp_path / "downloads", save_name="x.bin", tool="aria2", progress=False)

    assert result == tmp_path / "downloads" / "x.bin"
    assert (tmp_path / "downloads").is_dir()
    assert calls == [("https://example.test/file.bin", tmp_path / "downloads", "x.bin", "requests", False)]


def test_download_file_keeps_aria2_when_resolver_finds_aria2_next(monkeypatch, tmp_path):
    calls = []

    def fake_download_executer(url, path, save_name, tool, progress, **_kwargs):
        calls.append(tool)
        return path / (save_name or "download.bin")

    monkeypatch.setattr(downloader_module, "resolve_aria2_server_class", lambda: object)
    monkeypatch.setattr(downloader_module, "download_executer", fake_download_executer)

    downloader_module.download_file("https://example.test/file.bin", path=tmp_path, tool="aria2", progress=False)

    assert calls == ["aria2"]


def test_download_file_rejects_save_name_outside_target(monkeypatch, tmp_path):
    monkeypatch.setattr(downloader_module, "download_executer", lambda **_kwargs: pytest.fail("不应启动下载器"))

    with pytest.raises(ValueError, match="下载文件名"):
        downloader_module.download_file(
            "https://example.test/file.bin",
            path=tmp_path,
            save_name="../escape.bin",
            progress=False,
        )


def test_download_executer_does_not_outer_retry_state_error(monkeypatch, tmp_path):
    calls = []

    def fail_once(**kwargs):
        calls.append(kwargs)
        raise requests_models._ResumeStateError("bad state")

    monkeypatch.setattr(downloader_module, "download_file_from_url", fail_once)

    with pytest.raises(RuntimeError, match="bad state"):
        downloader_module.download_executer(
            url="https://example.test/file.bin",
            path=tmp_path,
            save_name="file.bin",
            tool="requests",
            progress=False,
        )

    assert len(calls) == 1


def test_download_file_falls_back_to_urllib_when_requests_missing(monkeypatch, tmp_path):
    calls = []
    real_import = builtins.__import__
    install_calls = []

    def fake_import(name, *args, **kwargs):
        if name == "requests":
            raise ImportError("requests missing")
        return real_import(name, *args, **kwargs)

    def fake_try_install_optional_dependency(package_name):
        install_calls.append(package_name)
        return False

    def fake_download_executer(url, path, save_name, tool, progress, **_kwargs):
        calls.append((tool, path))
        return path / (save_name or "download.bin")

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(downloader_module, "try_install_optional_dependency", fake_try_install_optional_dependency)
    monkeypatch.setattr(downloader_module, "resolve_aria2_server_class", lambda: None)
    monkeypatch.setattr(downloader_module, "download_executer", fake_download_executer)

    result = downloader_module.download_file("https://example.test/file.bin", path=tmp_path / "downloads", tool="aria2")

    assert result == tmp_path / "downloads" / "download.bin"
    assert calls == [("urllib", tmp_path / "downloads")]
    assert install_calls == ["requests"]


def test_download_file_installs_requests_before_fallback(monkeypatch, tmp_path):
    calls = []
    install_calls = []
    installed = False
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "requests":
            if not installed:
                raise ImportError("requests missing")
            return types.ModuleType("requests")
        return real_import(name, *args, **kwargs)

    def fake_try_install_optional_dependency(package_name):
        nonlocal installed
        install_calls.append(package_name)
        installed = True
        return True

    def fake_download_executer(url, path, save_name, tool, progress, **_kwargs):
        calls.append((tool, path))
        return path / (save_name or "download.bin")

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(downloader_module, "try_install_optional_dependency", fake_try_install_optional_dependency)
    monkeypatch.setattr(downloader_module, "download_executer", fake_download_executer)

    result = downloader_module.download_file("https://example.test/file.bin", path=tmp_path / "downloads")

    assert result == tmp_path / "downloads" / "download.bin"
    assert calls == [("requests", tmp_path / "downloads")]
    assert install_calls == ["requests"]


def test_download_file_falls_back_when_requests_still_missing_after_install(monkeypatch, tmp_path):
    calls = []
    install_calls = []
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "requests":
            raise ImportError("requests missing")
        return real_import(name, *args, **kwargs)

    def fake_try_install_optional_dependency(package_name):
        install_calls.append(package_name)
        return True

    def fake_download_executer(url, path, save_name, tool, progress, **_kwargs):
        calls.append((tool, path))
        return path / (save_name or "download.bin")

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(downloader_module, "try_install_optional_dependency", fake_try_install_optional_dependency)
    monkeypatch.setattr(downloader_module, "download_executer", fake_download_executer)

    result = downloader_module.download_file("https://example.test/file.bin", path=tmp_path / "downloads")

    assert result == tmp_path / "downloads" / "download.bin"
    assert calls == [("urllib", tmp_path / "downloads")]
    assert install_calls == ["requests"]
