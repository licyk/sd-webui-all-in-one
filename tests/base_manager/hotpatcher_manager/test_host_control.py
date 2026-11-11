"""宿主控制接口测试: 能力探测、``request_control`` 便捷方法、监听切换 (rebind) 与空 token 非回环警告。"""

import json
import socket
import threading
from types import SimpleNamespace
from typing import Any

import pytest

from sd_webui_all_in_one.base_manager.hotpatcher_manager import HotpatcherRuntimeHost, RemoteServiceError
from sd_webui_all_in_one.base_manager.hotpatcher_manager import host as host_module
from sd_webui_all_in_one.base_manager.hotpatcher_manager.config import ensure_hotpatcher_import_path

WAIT = 5
TOKEN_A = "host-token-alpha"
TOKEN_B = "host-token-bravo"


def _hotpatcher() -> Any:
    ensure_hotpatcher_import_path()
    from sd_webui_all_in_one_hotpatcher import services
    from sd_webui_all_in_one_hotpatcher.runtime import connection
    from sd_webui_all_in_one_hotpatcher.runtime.client import RuntimeClient
    from sd_webui_all_in_one_hotpatcher.runtime.faults import install_faulthandler
    from sd_webui_all_in_one_hotpatcher.state import HotpatcherState

    return SimpleNamespace(
        services=services,
        connection=connection,
        RuntimeClient=RuntimeClient,
        install_faulthandler=install_faulthandler,
        HotpatcherState=HotpatcherState,
    )


@pytest.fixture
def hp():
    return _hotpatcher()


@pytest.fixture
def state(hp):
    isolated = hp.HotpatcherState()
    yield isolated
    manager = isolated.connection_manager
    if manager is not None:
        manager.close()
    channel = isolated.bootstrap_service_control_channel
    if channel is not None:
        channel.close()
    if isolated.fault_channel is not None:
        isolated.fault_channel.close()
    client = isolated.bootstrap_runtime_client
    if client is not None and hasattr(client, "close"):
        client.close()
    hp.services.clear_current_config(state=isolated)


class _Watch:
    """收集宿主的状态与日志回调, 用条件变量等待而不是轮询。"""

    def __init__(self):
        self.cond = threading.Condition()
        self.statuses: list[str] = []
        self.logs: list[Any] = []

    def status(self, text):
        with self.cond:
            self.statuses.append(text)
            self.cond.notify_all()

    def log(self, entry):
        with self.cond:
            self.logs.append(entry)
            self.cond.notify_all()

    def count(self, prefix):
        with self.cond:
            return sum(1 for item in self.statuses if item.startswith(prefix))

    def wait(self, predicate, timeout=WAIT):
        with self.cond:
            return self.cond.wait_for(predicate, timeout)

    def wait_status(self, prefix, at_least=1):
        return self.wait(lambda: sum(1 for item in self.statuses if item.startswith(prefix)) >= at_least)


def _host(watch, *, token=TOKEN_A, **kwargs):
    return HotpatcherRuntimeHost(port=0, token=token, get_config=dict, on_status=watch.status, on_log=watch.log, **kwargs)


def _wire(hp, state, host, watch, *, token=TOKEN_A, fault=True):
    """像 bootstrap 一样连接宿主: 主连接、services 通道、(可选) fault 通道。"""

    channels = watch.count("services channel connected")
    client = hp.RuntimeClient.connect(*host.server_address, token=token, timeout=2)
    state.bootstrap_runtime_client = client
    state.bootstrap_service_control_channel = hp.services.install_service_control_channel(client, state=state)
    assert watch.wait_status("services channel connected", channels + 1)
    if fault:
        faults = watch.count("fault channel connected")
        hp.install_faulthandler(client, enable=False, state=state, timeout=2)
        assert watch.wait_status("fault channel connected", faults + 1)
    return client


def _send(file, message):
    file.write((json.dumps(message) + "\n").encode("utf-8"))
    file.flush()


def _send_raw(sock, message):
    sock.sendall((json.dumps(message) + "\n").encode("utf-8"))


def _accepted(address, token):
    """以 token 打开主连接并发出 config.get; 收到响应表示宿主接受该 token。"""

    with socket.create_connection(address, timeout=WAIT) as sock, sock.makefile("rwb") as file:
        _send(file, {"type": "hello", "version": 1, "features": [], "token": token})
        _send(file, {"id": "probe", "type": "config.get", "payload": {}})
        return bool(file.readline())


def _refused(address):
    try:
        socket.create_connection(address, timeout=WAIT).close()
    except OSError:
        return True
    return False


def _wait_host_state(host, predicate):
    with host._state:  # pylint: disable=protected-access
        return host._state.wait_for(predicate, WAIT)  # pylint: disable=protected-access


class _FakePeer:
    """脚本化的 services 通道对端: ``legacy`` 以 unknown_request 拒绝 hotpatch.*; ``control`` 声明支持控制命令。"""

    def __init__(self, address, *, token=TOKEN_A, mode="control", on_update=None, silent_probes=0):
        self.mode = mode
        self.on_update = on_update
        self.silent_probes = silent_probes
        self.requests: list[dict[str, Any]] = []
        self.sock = socket.create_connection(address, timeout=WAIT)
        self.file = self.sock.makefile("rwb")
        _send(self.file, {"type": "channel.open", "channel": "services", "token": token})
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        try:
            for line in self.file:
                message = json.loads(line.decode("utf-8"))
                self.requests.append(message)
                reply, after = self._reply(message)
                if reply is not None:
                    _send(self.file, reply)
                if after is not None:
                    after()
        except (OSError, ValueError):
            return

    def _reply(self, message):
        message_type = message["type"]
        ok = {"id": message["id"], "ok": True}
        if message_type.startswith("services."):
            return {**ok, "payload": {"config": {}}}, None
        if self.mode == "legacy":
            error = {"code": "unknown_request", "message": f"unknown services request: {message_type}"}
            return {"id": message["id"], "ok": False, "error": error}, None
        if message_type == "hotpatch.capabilities":
            if self.silent_probes > 0:
                self.silent_probes -= 1
                return None, None
            commands = ["hotpatch.capabilities", "hotpatch.connection.update", "hotpatch.patches.list"]
            return {**ok, "payload": {"control_version": 1, "transport": "legacy", "commands": commands, "aliases": {}}}, None
        if message_type == "hotpatch.connection.update":
            payload = message["payload"]
            return {**ok, "payload": {"status": "scheduled"}}, (lambda: self.on_update(payload)) if self.on_update else None
        return {**ok, "payload": {"patches": [], "count": 0, "truncated": False}}, None

    def close(self):
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.file.close()
        self.sock.close()
        self.thread.join(WAIT)


# ---------------------------------------------------------------------------
# request_control 与真实补丁进程
# ---------------------------------------------------------------------------


def test_request_control_round_trip_against_real_child(hp, state):
    watch = _Watch()
    with _host(watch) as host:
        assert host.capability_status == "disconnected" and host.client_capabilities is None
        _wire(hp, state, host, watch, fault=False)
        # 默认不主动探测: 能力未知, 属性读取不会阻塞也不会发请求。
        assert host.capability_status == "unknown" and not host.control_available

        capabilities = host.get_capabilities()
        assert capabilities["control_version"] == 1 and capabilities["transport"] == "legacy"
        assert host.control_available and host.client_capabilities == capabilities
        capabilities["commands"].clear()
        assert host.client_capabilities["commands"], "client_capabilities 返回副本"

        assert host.list_patches() == {"patches": [], "count": 0, "truncated": False}
        assert host.list_sets()["sets"] == []
        assert isinstance(host.list_features(), dict)
        assert host.get_status()
        assert host.set_strict(True) == {"strict": True, "previous": False}
        assert host.set_strict(False) == {"strict": False, "previous": True}
        assert set(host.get_trace()) >= {"enabled", "tags", "file", "available_tags"}
        assert host.set_trace("all")["enabled"] is True
        assert host.set_trace(None)["enabled"] is False
        events = host.read_patch_events(0, limit=50)
        assert set(events) >= {"events", "start_cursor", "next_cursor", "truncated", "has_more"}
        assert host.read_patch_events(events["next_cursor"])["events"] == []
        assert "module" in json.dumps(host.explain_module("json"))
        connection = host.get_connection()
        assert connection["connected"] is True and TOKEN_A not in json.dumps(connection)

        with pytest.raises(RemoteServiceError) as missing:
            host.unload_patch("hp-missing")
        assert missing.value.code == "not_found"
        with pytest.raises(RemoteServiceError) as gated:
            host.load_patch("json")
        assert gated.value.code == "remote_load_disabled"
        with pytest.raises(RemoteServiceError) as unknown:
            host.request_control("hotpatch.does.not.exist")
        assert unknown.value.code == "unsupported"

        # services.* 请求与原有接口保持不变。
        assert "config" in host.request_services("services.defaults.get", timeout=WAIT)

        hello = next(item for item in host.main_connections if item["type"] == "hello")
        assert hello["connected"] and hello["version"] == 1 and "control" in hello["features"]
        assert "token" not in hello


def test_auto_probe_caches_capabilities_in_background(hp, state):
    watch = _Watch()
    with _host(watch, auto_probe=True) as host:
        _wire(hp, state, host, watch, fault=False)
        assert watch.wait_status("hotpatcher runtime control available")
        assert host.control_available and host.client_capabilities["control_version"] == 1


def test_legacy_peer_is_detected_and_control_wrappers_raise():
    watch = _Watch()
    with _host(watch, auto_probe=True) as host:
        peer = _FakePeer(host.server_address, mode="legacy")
        try:
            assert watch.wait_status("legacy hotpatcher runtime")
            assert host.capability_status == "legacy" and not host.control_available
            assert host.client_capabilities == {"legacy": True}

            calls = [
                host.get_capabilities,
                host.get_status,
                host.list_patches,
                lambda: host.unload_patch("x"),
                host.list_sets,
                lambda: host.load_patch("json"),
                lambda: host.unload_patch_set("x"),
                lambda: host.reload_patch_set("x"),
                host.list_features,
                lambda: host.enable_feature("x"),
                lambda: host.disable_feature("x"),
                host.read_patch_events,
                host.get_trace,
                lambda: host.set_trace("all"),
                lambda: host.set_strict(True),
                lambda: host.explain_module("json"),
                host.get_connection,
                lambda: host.test_connection({"port": 1}),
                lambda: host.update_connection({"port": 1}),
            ]
            for call in calls:
                with pytest.raises(RemoteServiceError) as exc_info:
                    call()
                assert exc_info.value.code == "unsupported"
            # 只探测一次; 包装函数不会向旧版对端发送 hotpatch.* 命令。
            assert [item["type"] for item in peer.requests] == ["hotpatch.capabilities"]
            # services.* 回退路径保持可用。
            assert host.request_services("services.defaults.get", timeout=WAIT) == {"config": {}}
        finally:
            peer.close()


def test_probe_timeout_stays_unknown_and_is_retried():
    watch = _Watch()
    with _host(watch) as host:
        peer = _FakePeer(host.server_address, silent_probes=1)
        try:
            assert watch.wait_status("services channel connected")
            with pytest.raises(RemoteServiceError) as exc_info:
                host.get_capabilities(timeout=0.2)
            assert exc_info.value.code == "probe_failed"
            assert host.capability_status == "unknown"
            assert host.get_capabilities()["control_version"] == 1
            assert host.control_available
        finally:
            peer.close()


def test_control_requires_a_services_channel():
    with HotpatcherRuntimeHost(port=0) as host:
        with pytest.raises(RemoteServiceError) as exc_info:
            host.list_patches()
        assert exc_info.value.code == "channel_unavailable"


# ---------------------------------------------------------------------------
# rebind
# ---------------------------------------------------------------------------


def test_rebind_with_control_child_switches_listener_token_and_channels(hp, state):
    watch = _Watch()
    with _host(watch) as host:
        client = _wire(hp, state, host, watch)
        old_address = host.server_address
        old_channel = host._service_channel  # pylint: disable=protected-access

        report = host.rebind(port=0, token=TOKEN_B)

        assert report["status"] == "switched", report
        new_address = host.server_address
        assert new_address[1] != old_address[1] and report["address"] == list(new_address)
        assert report["previous_address"] == list(old_address) and report["token_changed"] is True
        assert TOKEN_B not in json.dumps(report)
        assert host.token == TOKEN_B and host.port == new_address[1]
        assert _refused(old_address)
        assert (client.port, client.token) == (new_address[1], TOKEN_B)

        # 旧通道后关闭不会清掉新通道 (按身份移除)。
        assert old_channel.closed
        assert host.service_channel_available and host._service_channel is not old_channel  # pylint: disable=protected-access
        # 切换完成后的最后一条状态反映新监听 (而不是旧通道的断开)。
        assert watch.statuses[-1].startswith(f"runtime host listening on {new_address[0]}:{new_address[1]}")
        assert host.list_patches()["count"] == 0

        # 日志与事件经由新监听到达; 旧主连接已断开, 新主连接以新端口为监听。
        assert client.emit_event("log.record", {"level": "INFO", "logger": "t", "message": "after-rebind"})
        assert watch.wait(lambda: any(entry.payload.get("message") == "after-rebind" for entry in watch.logs))
        assert _wait_host_state(host, lambda: all(not item["connected"] for item in host.main_connections if item["listener"][1] == old_address[1]))
        assert any(item["connected"] and item["listener"][1] == new_address[1] for item in host.main_connections)

        # 窗口结束: 只接受新 token。
        assert _accepted(new_address, TOKEN_B)
        assert not _accepted(new_address, TOKEN_A)


def test_rebind_token_only_reuses_the_listener(hp, state):
    watch = _Watch()
    with _host(watch) as host:
        client = _wire(hp, state, host, watch, fault=False)
        address = host.server_address
        report = host.rebind(token=TOKEN_B)
        assert report["status"] == "switched", report
        assert host.server_address == address and client.token == TOKEN_B
        assert host.list_sets()["count"] == 0
        assert _accepted(address, TOKEN_B) and not _accepted(address, TOKEN_A)


def test_rebind_with_legacy_child_is_unsupported_and_keeps_listener():
    watch = _Watch()
    with _host(watch) as host:
        address = host.server_address
        peer = _FakePeer(host.server_address, mode="legacy")
        try:
            assert watch.wait_status("services channel connected")
            report = host.rebind(port=0, token=TOKEN_B)
            assert report["status"] == "unsupported" and report["reason"] == "legacy_runtime"
            assert host.server_address == address and host.token == TOKEN_A
            assert _accepted(address, TOKEN_A) and not _accepted(address, TOKEN_B)
            assert host.request_services("services.defaults.get", timeout=WAIT) == {"config": {}}
        finally:
            peer.close()


def test_rebind_with_empty_token_child_is_unsupported():
    watch = _Watch()
    with _host(watch, token="") as host:
        address = host.server_address
        peer = _FakePeer(host.server_address, token="")
        try:
            assert watch.wait_status("services channel connected")
            report = host.rebind(port=0)
            assert report["status"] == "unsupported" and report["reason"] == "token_required"
            assert host.server_address == address
            assert [item["type"] for item in peer.requests] == ["hotpatch.capabilities"]
        finally:
            peer.close()


@pytest.mark.parametrize("stage", ["services", "fault"])
def test_rebind_rolls_back_when_the_child_rolls_back(hp, state, stage):
    watch = _Watch()
    with _host(watch) as host:
        client = _wire(hp, state, host, watch)
        old_address = host.server_address

        def failing(*_args):
            raise OSError(f"{stage} opener failed")

        options = {"services_opener" if stage == "services" else "fault_opener": failing}
        state.connection_manager = hp.connection.ConnectionManager(client, state=state, **options).attach()

        report = host.rebind(port=0, token=TOKEN_B)

        assert report["status"] == "rolled_back" and report["stage"] == "wait", report
        assert report["error"]["code"] == "child_rollback"
        assert host.server_address == old_address and host.token == TOKEN_A
        assert _refused(tuple(report["previous_address"])) is False
        # 旧通道继续服务 (新通道先到后关时回退到旧通道)。
        assert host.service_channel_available and host.list_patches()["count"] == 0
        assert (client.port, client.token) == (old_address[1], TOKEN_A)
        assert _accepted(old_address, TOKEN_A) and not _accepted(old_address, TOKEN_B)


def test_rebind_rolls_back_when_the_child_never_arrives():
    watch = _Watch()
    updates: list[dict[str, Any]] = []
    with _host(watch) as host:
        old_address = host.server_address
        peer = _FakePeer(host.server_address, on_update=updates.append)
        try:
            assert watch.wait_status("services channel connected")
            report = host.rebind(port=0, token=TOKEN_B, timeout=0.5)
            assert report["status"] == "rolled_back" and report["error"]["code"] == "timeout", report
            assert updates and updates[0]["token"] == TOKEN_B and "host" not in updates[0]
            assert _refused((old_address[0], updates[0]["port"]))
            assert host.server_address == old_address and host.token == TOKEN_A
            assert host.list_patches()["count"] == 0
            assert _accepted(old_address, TOKEN_A) and not _accepted(old_address, TOKEN_B)
        finally:
            peer.close()


def test_rebind_accepts_both_tokens_only_during_the_window():
    watch = _Watch()
    observed: dict[str, Any] = {}
    with _host(watch) as host:
        old_address = host.server_address

        def on_update(payload):
            new_address = (old_address[0], payload["port"])
            # 与补丁进程一致: 先以新 token 建立新主连接; 期间的短暂连接 (hello 后关闭) 不会被当成回滚。
            main = socket.create_connection(new_address, timeout=WAIT)
            observed["main"] = main
            _send_raw(main, {"type": "hello", "version": 1, "features": ["control"], "token": TOKEN_B})
            observed["old"] = _accepted(new_address, TOKEN_A)
            observed["new"] = _accepted(new_address, TOKEN_B)
            observed["wrong"] = _accepted(new_address, "wrong-token")
            observed["old_listener_new_token"] = _accepted(old_address, TOKEN_B)
            observed["peer"] = _FakePeer(new_address, token=TOKEN_B)
            # 新通道就绪后关闭旧通道 (补丁进程的提交信号)。
            peer.sock.shutdown(socket.SHUT_RDWR)

        peer = _FakePeer(host.server_address, on_update=on_update)
        try:
            assert watch.wait_status("services channel connected")
            report = host.rebind(port=0, token=TOKEN_B)
            assert report["status"] == "switched", report
            assert observed["old"] and observed["new"] and observed["old_listener_new_token"]
            assert not observed["wrong"]
            # 窗口结束后旧 token 失效。
            assert _accepted(host.server_address, TOKEN_B)
            assert not _accepted(host.server_address, TOKEN_A)
        finally:
            peer.close()
            if "peer" in observed:
                observed["peer"].close()
            if "main" in observed:
                observed["main"].close()


def test_rebind_without_child_moves_the_listener():
    watch = _Watch()
    with _host(watch) as host:
        old_address = host.server_address
        report = host.rebind(port=0)
        assert report["status"] == "switched" and report["child"] is None and report["token_changed"] is False
        assert host.server_address != old_address and _refused(old_address)
        assert _accepted(host.server_address, TOKEN_A)

        address = host.server_address
        report = host.rebind(token=TOKEN_B)
        assert report["status"] == "switched" and report["child"] is None and report["token_changed"] is True
        assert host.server_address == address
        assert _accepted(address, TOKEN_B) and not _accepted(address, TOKEN_A)


def test_rebind_validation_and_stopped_host():
    host = HotpatcherRuntimeHost(port=0, token=TOKEN_A)
    report = host.rebind(token=TOKEN_B)
    assert report["status"] == "switched" and report["listening"] is False
    assert (host.port, host.token) == (0, TOKEN_B)
    with host:
        with pytest.raises(ValueError):
            host.rebind()
        with pytest.raises(ValueError):
            host.rebind(token=TOKEN_B)


def test_rebind_listen_failure_keeps_the_old_listener():
    watch = _Watch()
    with _host(watch) as host, socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        address = host.server_address
        report = host.rebind(port=busy.getsockname()[1])
        assert report["status"] == "rolled_back" and report["stage"] == "listen"
        assert host.server_address == address and _accepted(address, TOKEN_A)


# ---------------------------------------------------------------------------
# 空 token 非回环警告
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("bind_host", "token", "warned"),
    [("0.0.0.0", "", True), ("0.0.0.0", TOKEN_A, False), ("127.0.0.1", "", False), ("localhost", "", False)],
)
def test_warns_when_bound_to_non_loopback_without_token(monkeypatch, bind_host, token, warned):
    warnings: list[str] = []
    monkeypatch.setattr(host_module.logger, "warning", lambda message, *args: warnings.append(message % args))
    with HotpatcherRuntimeHost(host=bind_host, port=0, token=token):
        pass
    assert any("非回环" in item for item in warnings) is warned


def test_rebind_to_non_loopback_without_token_warns(monkeypatch):
    warnings: list[str] = []
    monkeypatch.setattr(host_module.logger, "warning", lambda message, *args: warnings.append(message % args))
    with HotpatcherRuntimeHost(port=0) as host:
        assert not warnings
        assert host.rebind(host="0.0.0.0", port=0)["status"] == "switched"
        assert any("非回环" in item for item in warnings)
