import hashlib
import json
import sys
import types
import urllib.error
from pathlib import Path

import pytest

from sd_webui_all_in_one.downloader import aria2_downloader
from sd_webui_all_in_one.downloader import aria2_server
from sd_webui_all_in_one.downloader import requests_downloader
from sd_webui_all_in_one.downloader import urllib_downloader
from sd_webui_all_in_one.downloader.hash_utils import compare_sha256


class FakeRequestsResponse:
    def __init__(self, chunks, status_code=200):
        self._chunks = chunks
        self.status_code = status_code
        self.headers = {"content-length": str(sum(len(chunk) for chunk in chunks))}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("bad status")

    def iter_content(self, chunk_size=1024):
        assert chunk_size == 1024
        yield from self._chunks


def test_requests_downloader_cache_redownload_and_hash(monkeypatch, tmp_path):
    calls = []
    payload = b"hello world"

    fake_requests = types.SimpleNamespace(
        get=lambda url, stream=True, timeout=60: calls.append((url, stream, timeout)) or FakeRequestsResponse([payload[:5], payload[5:]])
    )
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    expected_hash = hashlib.sha256(payload).hexdigest()
    result = requests_downloader.download_file_from_url(
        "https://example.test/files/model.bin",
        save_path=tmp_path / "downloads",
        progress=False,
        hash_prefix=expected_hash[:12],
    )

    assert result == (tmp_path / "downloads" / "model.bin").resolve()
    assert result.read_bytes() == payload
    assert calls == [("https://example.test/files/model.bin", True, 60)]

    cached = requests_downloader.download_file_from_url(
        "https://example.test/files/model.bin",
        save_path=tmp_path / "downloads",
        progress=False,
    )
    assert cached == result
    assert len(calls) == 1

    with pytest.raises(ValueError):
        requests_downloader.download_file_from_url(
            "https://example.test/files/model.bin",
            save_path=tmp_path / "downloads",
            progress=False,
            hash_prefix="badbad",
            re_download=True,
        )
    assert not (tmp_path / "downloads" / "model.bin.tmp").exists()


class FakeUrllibResponse:
    def __init__(self, payload):
        self.payload = payload
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def getheader(self, name, default=None):
        return str(len(self.payload)) if name == "Content-Length" else default

    def read(self, size):
        chunk = self.payload[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


def test_urllib_downloader_uses_user_agent_cache_and_hash(monkeypatch, tmp_path):
    payload = b"urllib payload"
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, request.headers.get("User-agent"), timeout))
        return FakeUrllibResponse(payload)

    monkeypatch.setattr(urllib_downloader.urllib.request, "urlopen", fake_urlopen)

    result = urllib_downloader.download_file_from_url_urllib(
        "https://example.test/archive.tar.gz",
        save_path=tmp_path,
        progress=False,
        hash_prefix=hashlib.sha256(payload).hexdigest()[:8],
    )

    assert result == (tmp_path / "archive.tar.gz").resolve()
    assert result.read_bytes() == payload
    assert calls == [("https://example.test/archive.tar.gz", "Mozilla/5.0", 60)]

    urllib_downloader.download_file_from_url_urllib("https://example.test/archive.tar.gz", save_path=tmp_path, progress=False)
    assert len(calls) == 1


def test_compare_sha256_strips_and_lowercases_prefix(tmp_path):
    file_path = tmp_path / "data.bin"
    file_path.write_bytes(b"abc")
    digest = hashlib.sha256(b"abc").hexdigest()

    assert compare_sha256(file_path, f"  {digest[:10].upper()}  ") is True
    assert compare_sha256(file_path, "0" * 10) is False


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
            return kwargs["save_path"] / "asset.bin"

    monkeypatch.setattr(aria2_downloader, "Aria2RpcServer", lambda use_external_server=False: FakeServer())

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
    assert events[-2][1]["url"] == "https://example.test/asset.bin"
    assert events[-2][1]["save_path"] == tmp_path


def test_aria2_rpc_call_includes_token_and_retries(monkeypatch):
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"result": {"version": "1.37.0"}}).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, json.loads(request.data.decode("utf-8")), timeout))
        if len(calls) == 1:
            raise urllib.error.URLError("not ready")
        return FakeResponse()

    monkeypatch.setattr(aria2_server.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(aria2_server.time, "sleep", lambda _seconds: None)

    server = aria2_server.Aria2RpcServer(port=6801, secret="secret")
    assert server._rpc_call("aria2.getVersion", ["x"], retry_count=2) == {"version": "1.37.0"}
    assert calls[1][1]["params"] == ["token:secret", "x"]


def test_aria2_rpc_call_errors_on_rpc_error_and_bad_json(monkeypatch):
    class ErrorResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"error": {"code": 1, "message": "boom"}}).encode("utf-8")

    monkeypatch.setattr(aria2_server.urllib.request, "urlopen", lambda *_args, **_kwargs: ErrorResponse())
    server = aria2_server.Aria2RpcServer(port=6801)
    with pytest.raises(RuntimeError, match="RPC Error 1"):
        server._rpc_call("aria2.tellStatus")

    class BadJsonResponse(ErrorResponse):
        def read(self):
            return b"{"

    monkeypatch.setattr(aria2_server.urllib.request, "urlopen", lambda *_args, **_kwargs: BadJsonResponse())
    with pytest.raises(RuntimeError, match="JSON"):
        server._rpc_call("aria2.tellStatus")


def test_aria2_download_and_batch_waiting(monkeypatch, tmp_path):
    server = aria2_server.Aria2RpcServer(download_dir=tmp_path)
    server.process = types.SimpleNamespace(poll=lambda: None)
    monkeypatch.setattr(aria2_server.time, "sleep", lambda _seconds: None)

    calls = []
    statuses = {
        "gid-1": {"status": "complete", "totalLength": "10", "completedLength": "10", "files": [{"path": (tmp_path / "one.bin").as_posix()}]},
        "gid-2": {"status": "error", "totalLength": "10", "completedLength": "1", "errorMessage": "network", "errorCode": "7"},
    }

    def fake_rpc(method, params=None, retry_count=3):
        calls.append((method, params, retry_count))
        if method == "aria2.addUri":
            return "gid-1"
        if method == "aria2.tellStatus":
            return statuses[params[0]]
        raise AssertionError(method)

    server._rpc_call = fake_rpc
    assert server.download("https://example.test/one.bin", save_path=tmp_path, show_progress=False) == tmp_path / "one.bin"
    assert calls[0] == ("aria2.addUri", [["https://example.test/one.bin"], {"dir": tmp_path.as_posix(), "out": "one.bin"}], 3)

    server._rpc_call = lambda method, params=None, retry_count=3: "gid-2" if method == "aria2.addUri" else statuses["gid-2"]
    with pytest.raises(RuntimeError, match="network"):
        server.download("https://example.test/two.bin", save_path=tmp_path, show_progress=False)


def test_aria2_start_reuses_external_server_and_stop_skips(monkeypatch, tmp_path):
    monkeypatch.setattr(aria2_server.shutil, "which", lambda name: "/bin/aria2c" if name == "aria2c" else None)
    monkeypatch.setattr(aria2_server, "is_port_in_use", lambda _port: True)

    server = aria2_server.Aria2RpcServer(port=6800, download_dir=tmp_path, use_external_server=True)
    monkeypatch.setattr(server, "_test_connection", lambda: True)
    monkeypatch.setattr(server, "_rpc_call", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not stop external")))

    server._start_server()
    assert server._is_external_server is True
    assert server.process is None
    server._stop_server()


def test_aria2_wait_download_detects_process_crash(tmp_path):
    server = aria2_server.Aria2RpcServer(download_dir=tmp_path, log_file=tmp_path / "aria2.log")
    server.process = types.SimpleNamespace(poll=lambda: 1, stderr=None)

    with pytest.raises(RuntimeError, match="aria2 进程已崩溃"):
        server._wait_download("gid", "file.bin", show_progress=False)
