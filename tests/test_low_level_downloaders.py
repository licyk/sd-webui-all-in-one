import hashlib
import json
import subprocess
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


class FakeTqdm:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.n = kwargs.get("initial", 0)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def update(self, value):
        self.n += value

    def close(self):
        pass


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
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

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

    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))
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


def test_aria2_start_uses_free_port_and_stop_cleans_session(monkeypatch, tmp_path):
    commands = []

    class FakeProcess:
        def __init__(self, command, **kwargs):
            commands.append((command, kwargs))
            self.stderr = None
            self.killed = False
            self.waits = []

        def poll(self):
            return None

        def wait(self, timeout=None):
            self.waits.append(timeout)
            return 0

        def kill(self):
            self.killed = True

    monkeypatch.setattr(aria2_server.shutil, "which", lambda name: "/bin/aria2c" if name == "aria2c" else None)
    monkeypatch.setattr(aria2_server, "is_port_in_use", lambda _port: True)
    monkeypatch.setattr(aria2_server, "find_port", lambda port: port + 1)
    monkeypatch.setattr(aria2_server.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(aria2_server.Aria2RpcServer, "_test_connection", lambda _self: True)

    server = aria2_server.Aria2RpcServer(port=6800, download_dir=tmp_path, use_config_file=False, use_external_server=False)
    server._start_server()

    assert server.port == 6801
    assert server.rpc_url == "http://localhost:6801/jsonrpc"
    assert commands[0][0][:3] == ["aria2c", "--enable-rpc=true", "--rpc-listen-port=6801"]
    session_path = Path(server._session_file.name)
    assert session_path.exists()

    rpc_calls = []
    server._rpc_call = lambda method, *args, **kwargs: rpc_calls.append((method, args, kwargs))
    server._stop_server()

    assert rpc_calls[0][0] == "aria2.shutdown"
    assert server.process.waits == [5]
    assert not session_path.exists()


def test_aria2_stop_kills_timeout_process_and_removes_session(tmp_path):
    events = []

    class FakeProcess:
        stderr = None

        def poll(self):
            return None

        def wait(self, timeout=None):
            events.append(("wait", timeout))
            if timeout == 5:
                raise subprocess.TimeoutExpired("aria2c", timeout)
            return 0

        def kill(self):
            events.append("kill")

    session_file = tmp_path / "session.aria2"
    session_file.write_text("", encoding="utf-8")

    server = aria2_server.Aria2RpcServer(download_dir=tmp_path)
    server.process = FakeProcess()
    server._session_file = types.SimpleNamespace(name=session_file.as_posix())
    server._rpc_call = lambda method, *args, **kwargs: events.append(method)

    server._stop_server()

    assert events == ["aria2.shutdown", ("wait", 5), "kill", ("wait", None)]
    assert not session_file.exists()


def test_aria2_download_batch_keeps_successful_downloads(monkeypatch, tmp_path):
    server = aria2_server.Aria2RpcServer(download_dir=tmp_path)
    add_calls = []

    def fake_rpc(method, params=None, retry_count=3):
        if method != "aria2.addUri":
            raise AssertionError(method)
        url = params[0][0]
        add_calls.append(params)
        if "bad-add" in url:
            raise RuntimeError("add bad")
        return "gid-fail" if "bad-wait" in url else f"gid-{len(add_calls)}"

    def fake_wait(gid, file_name, show_progress):
        if gid == "gid-fail":
            raise RuntimeError("download bad")
        return tmp_path / file_name

    server._rpc_call = fake_rpc
    server._wait_download = fake_wait

    result = server.download_batch(
        ["https://example.test/one.bin", "https://example.test/bad-add.bin", "https://example.test/bad-wait.bin"],
        save_path=tmp_path,
        options={"split": "8"},
        show_progress=False,
    )

    assert result == [tmp_path / "one.bin"]
    assert add_calls[0][1]["out"] == "one.bin"
    assert add_calls[0][1]["split"] == "8"
    assert add_calls[2][1]["out"] == "bad-wait.bin"

    server._rpc_call = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("all bad"))
    with pytest.raises(RuntimeError, match="没有成功添加任何下载任务"):
        server.download_batch(["https://example.test/fail.bin"], save_path=tmp_path, show_progress=False)


def test_aria2_wait_download_removed_and_repeated_query_failures(monkeypatch, tmp_path):
    server = aria2_server.Aria2RpcServer(download_dir=tmp_path)
    server.process = types.SimpleNamespace(poll=lambda: None, stderr=None)
    monkeypatch.setattr(aria2_server.time, "sleep", lambda _seconds: None)

    server._rpc_call = lambda method, params=None, retry_count=3: {"status": "removed", "totalLength": "0", "completedLength": "0"}
    with pytest.raises(RuntimeError, match="下载任务已被移除"):
        server._wait_download("gid", "removed.bin", show_progress=False)

    attempts = []

    def failing_rpc(method, params=None, retry_count=3):
        attempts.append((method, params, retry_count))
        raise ValueError("temporary rpc parse error")

    server._rpc_call = failing_rpc
    with pytest.raises(RuntimeError, match="连续 5 次查询下载状态失败"):
        server._wait_download("gid", "broken.bin", show_progress=False)

    assert len(attempts) == 5


def test_aria2_rpc_wrapper_methods_delegate_to_expected_methods():
    server = aria2_server.Aria2RpcServer()
    calls = []

    def fake_rpc(method, params=None, retry_count=3):
        calls.append((method, params, retry_count))
        return {"method": method, "params": params}

    server._rpc_call = fake_rpc

    assert server.get_version()["method"] == "aria2.getVersion"
    assert server.get_global_stat()["method"] == "aria2.getGlobalStat"
    assert server.pause("gid")["params"] == ["gid"]
    assert server.unpause("gid")["method"] == "aria2.unpause"
    assert server.remove("gid")["method"] == "aria2.remove"
    assert server.tell_status("gid", ["status"])["params"] == ["gid", ["status"]]
    assert server.tell_active()["method"] == "aria2.tellActive"
    assert server.tell_waiting(2, 3)["params"] == [2, 3]
    assert server.tell_stopped(4, 5)["params"] == [4, 5]

    assert calls == [
        ("aria2.getVersion", None, 3),
        ("aria2.getGlobalStat", None, 3),
        ("aria2.pause", ["gid"], 3),
        ("aria2.unpause", ["gid"], 3),
        ("aria2.remove", ["gid"], 3),
        ("aria2.tellStatus", ["gid", ["status"]], 3),
        ("aria2.tellActive", None, 3),
        ("aria2.tellWaiting", [2, 3], 3),
        ("aria2.tellStopped", [4, 5], 3),
    ]
