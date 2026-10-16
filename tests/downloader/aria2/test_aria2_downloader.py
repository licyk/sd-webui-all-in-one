"""Aria2 下载入口与服务器池测试"""

import hashlib

import pytest

from sd_webui_all_in_one.downloader import aria2_downloader, aria2_server
from sd_webui_all_in_one.downloader.requests_downloader import http as requests_http


def test_aria2_server_pool_refcounts_and_aria2_wrapper(monkeypatch, tmp_path):
    events = []

    class FakeServer:
        def __enter__(self):
            events.append("enter")
            return self

        def __exit__(self, *_args):
            events.append("exit")

        def download(self, **kwargs):
            events.append(("download", kwargs))
            save_name = kwargs["save_name"] or requests_http._filename_from_url(kwargs["url"][0])
            return kwargs["save_path"] / save_name

    monkeypatch.setattr(aria2_downloader, "resolve_aria2_server_class", lambda: lambda use_external_server=False: FakeServer())

    pool = aria2_downloader._Aria2ServerPool()
    first = pool.acquire()
    second = pool.acquire()
    assert first is second
    assert events == ["enter"]
    pool.release()
    assert events == ["enter"]
    pool.release()
    assert events == ["enter", "exit"]

    monkeypatch.setattr(aria2_downloader, "_server_pool", aria2_downloader._Aria2ServerPool())
    result = aria2_downloader.aria2("https://example.test/asset.bin", path=tmp_path, progress=False)
    assert result == tmp_path / "asset.bin"
    assert events[-2][0] == "download"
    assert events[-2][1]["url"] == ["https://example.test/asset.bin"]
    assert events[-2][1]["save_path"] == tmp_path
    assert events[-2][1]["save_name"] is None
    assert events[-2][1]["options"]["allow-piece-length-change"] == "false"
    assert events[-2][1]["options"]["retry-wait"] == "0"
    assert events[-2][1]["options"]["conditional-get"] == "false"
    assert events[-2][1]["options"]["remote-time"] == "true"
    assert events[-2][1]["options"]["always-resume"] == "true"
    assert events[-2][1]["options"]["max-resume-failure-tries"] == "0"
    assert events[-2][1]["options"]["allow-overwrite"] == "false"
    assert events[-2][1]["options"]["auto-file-renaming"] == "false"
    assert events[-2][1]["options"]["continue"] == "true"

    result = aria2_downloader.aria2(
        "https://example.test/asset.bin",
        path=tmp_path,
        save_name="renamed.bin",
        progress=False,
        allow_piece_length_change=True,
        max_tries=0,
        retry_wait=9,
        conditional_get=True,
        remote_time=False,
        always_resume=False,
        max_resume_failure_tries=2,
        existing_file_policy="overwrite",
    )
    assert result == tmp_path / "renamed.bin"
    assert events[-2][1]["save_name"] == "renamed.bin"
    assert events[-2][1]["options"]["allow-piece-length-change"] == "true"
    assert events[-2][1]["options"]["max-tries"] == "0"
    assert events[-2][1]["options"]["retry-wait"] == "9"
    assert events[-2][1]["options"]["conditional-get"] == "true"
    assert events[-2][1]["options"]["remote-time"] == "false"
    assert events[-2][1]["options"]["always-resume"] == "false"
    assert events[-2][1]["options"]["max-resume-failure-tries"] == "2"
    assert events[-2][1]["options"]["allow-overwrite"] == "true"
    assert events[-2][1]["options"]["auto-file-renaming"] == "false"

    result = aria2_downloader.aria2(
        ["https://mirror-a.example.test/multi.bin", "https://mirror-b.example.test/multi.bin"],
        path=tmp_path,
        progress=False,
    )
    assert result == tmp_path / "multi.bin"
    assert events[-2][1]["url"] == [
        "https://mirror-a.example.test/multi.bin",
        "https://mirror-b.example.test/multi.bin",
    ]
    assert events[-2][1]["save_name"] is None

    monkeypatch.setattr(aria2_downloader, "compare_hash", lambda *_args: True)
    aria2_downloader.aria2(
        "https://example.test/prefix.bin",
        path=tmp_path,
        progress=False,
        hash_prefix="abcd",
    )
    assert "checksum" not in events[-2][1]["options"]

    full_sha512 = hashlib.sha512(b"payload").hexdigest()
    aria2_downloader.aria2(
        "https://example.test/full.bin",
        path=tmp_path,
        progress=False,
        hash_value=full_sha512,
        hash_algorithm="sha512",
    )
    assert events[-2][1]["options"]["checksum"] == f"sha-512={full_sha512}"

    full_sha256 = hashlib.sha256(b"payload").hexdigest().upper()
    aria2_downloader.aria2(
        "https://example.test/full256.bin",
        path=tmp_path,
        progress=False,
        hash_value=full_sha256,
    )
    assert events[-2][1]["options"]["checksum"] == f"sha-256={full_sha256.lower()}"

    before_invalid_call = list(events)
    with pytest.raises(ValueError, match="max_connection_per_server"):
        aria2_downloader.aria2(
            "https://example.test/asset.bin",
            path=tmp_path,
            progress=False,
            max_connection_per_server=17,
        )
    assert events == before_invalid_call


def _reset_aria2_server_class_cache(monkeypatch):
    monkeypatch.setattr(aria2_downloader, "_server_class_resolved", False)
    monkeypatch.setattr(aria2_downloader, "_server_class", None)


def test_resolve_aria2_server_class_prefers_aria2c(monkeypatch):
    _reset_aria2_server_class_cache(monkeypatch)
    monkeypatch.setattr(aria2_server.Aria2cRpcServer, "find_executable", classmethod(lambda _cls: "/bin/aria2c"))
    monkeypatch.setattr(aria2_server.Aria2NextRpcServer, "find_executable", classmethod(lambda _cls: "/bin/aria2-next"))
    monkeypatch.setattr(aria2_downloader, "try_install_optional_dependency", lambda *_args: pytest.fail("不应安装 aria2-next"))

    assert aria2_downloader.resolve_aria2_server_class() is aria2_server.Aria2cRpcServer


def test_resolve_aria2_server_class_uses_existing_aria2_next(monkeypatch):
    _reset_aria2_server_class_cache(monkeypatch)
    monkeypatch.setattr(aria2_server.Aria2cRpcServer, "find_executable", classmethod(lambda _cls: None))
    monkeypatch.setattr(aria2_server.Aria2NextRpcServer, "find_executable", classmethod(lambda _cls: "/bin/aria2-next"))
    monkeypatch.setattr(aria2_downloader, "try_install_optional_dependency", lambda *_args: pytest.fail("不应安装 aria2-next"))

    assert aria2_downloader.resolve_aria2_server_class() is aria2_server.Aria2NextRpcServer


def test_resolve_aria2_server_class_installs_aria2_next(monkeypatch):
    _reset_aria2_server_class_cache(monkeypatch)
    installed = False
    install_calls = []

    def fake_install(package_name, display_name=None):
        nonlocal installed
        install_calls.append(package_name)
        installed = True
        return True

    monkeypatch.setattr(aria2_server.Aria2cRpcServer, "find_executable", classmethod(lambda _cls: None))
    monkeypatch.setattr(aria2_server.Aria2NextRpcServer, "find_executable", classmethod(lambda _cls: "/bin/aria2-next" if installed else None))
    monkeypatch.setattr(aria2_downloader, "try_install_optional_dependency", fake_install)

    assert aria2_downloader.resolve_aria2_server_class() is aria2_server.Aria2NextRpcServer
    assert aria2_downloader.resolve_aria2_server_class() is aria2_server.Aria2NextRpcServer
    assert install_calls == ["aria2-next>=3.0.4"]


@pytest.mark.parametrize("install_result", [False, True])
def test_resolve_aria2_server_class_caches_unavailable_result(monkeypatch, install_result):
    _reset_aria2_server_class_cache(monkeypatch)
    install_calls = []

    def fake_install(package_name, display_name=None):
        install_calls.append(package_name)
        return install_result

    monkeypatch.setattr(aria2_server.Aria2cRpcServer, "find_executable", classmethod(lambda _cls: None))
    monkeypatch.setattr(aria2_server.Aria2NextRpcServer, "find_executable", classmethod(lambda _cls: None))
    monkeypatch.setattr(aria2_downloader, "try_install_optional_dependency", fake_install)

    assert aria2_downloader.resolve_aria2_server_class() is None
    assert aria2_downloader.resolve_aria2_server_class() is None
    assert install_calls == ["aria2-next>=3.0.4"]


def test_aria2_server_pool_raises_when_aria2_unavailable(monkeypatch):
    monkeypatch.setattr(aria2_downloader, "resolve_aria2_server_class", lambda: None)
    pool = aria2_downloader._Aria2ServerPool()

    with pytest.raises(RuntimeError, match="aria2-next"):
        pool.acquire()
    assert pool._ref_count == 0
