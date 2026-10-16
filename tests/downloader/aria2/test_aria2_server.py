"""Aria2 RPC 服务器测试"""

import json
import subprocess
import types
import urllib.error
from pathlib import Path

import pytest

from sd_webui_all_in_one.downloader import aria2_server


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
    assert calls[0] == ("aria2.addUri", [["https://example.test/one.bin"], {"dir": tmp_path.as_posix()}], 3)

    calls.clear()
    assert (
        server.download(
            ["https://mirror-a.example.test/one.bin", "https://mirror-b.example.test/one.bin"],
            save_path=tmp_path,
            show_progress=False,
        )
        == tmp_path / "one.bin"
    )
    assert calls[0] == (
        "aria2.addUri",
        [
            ["https://mirror-a.example.test/one.bin", "https://mirror-b.example.test/one.bin"],
            {"dir": tmp_path.as_posix()},
        ],
        3,
    )

    server._rpc_call = lambda method, params=None, retry_count=3: "gid-2" if method == "aria2.addUri" else statuses["gid-2"]
    with pytest.raises(RuntimeError, match="network"):
        server.download("https://example.test/two.bin", save_path=tmp_path, show_progress=False)


def test_aria2_start_reuses_external_server_and_stop_skips(monkeypatch, tmp_path):
    monkeypatch.setattr(aria2_server.shutil, "which", lambda name: "/bin/aria2c" if name == "aria2c" else None)
    monkeypatch.setattr(aria2_server, "is_port_in_use", lambda _port: True)

    server = aria2_server.Aria2cRpcServer(port=6800, download_dir=tmp_path, use_external_server=True)
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

    server = aria2_server.Aria2cRpcServer(port=6800, download_dir=tmp_path, use_config_file=False, use_external_server=False)
    server._start_server()

    assert server.port == 6801
    assert server.rpc_url == "http://localhost:6801/jsonrpc"
    assert commands[0][0][:3] == ["/bin/aria2c", "--enable-rpc=true", "--rpc-listen-port=6801"]
    assert "--split=32" in commands[0][0]
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
