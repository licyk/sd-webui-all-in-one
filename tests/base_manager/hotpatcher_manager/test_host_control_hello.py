"""宿主与新版补丁进程的兼容性测试: hello 中的 ``control`` 能力提示、services 通道上的控制命令与完整配置回传。"""

from types import SimpleNamespace
from typing import Any

import pytest

from sd_webui_all_in_one.base_manager.hotpatcher_manager import HotpatcherRuntimeHost, RemoteServiceError, wait_for_service_channel
from sd_webui_all_in_one.base_manager.hotpatcher_manager.config import ensure_hotpatcher_import_path


def _hotpatcher() -> Any:
    ensure_hotpatcher_import_path()
    from sd_webui_all_in_one_hotpatcher import monkey_zoo, services, uninstall_import_hook
    from sd_webui_all_in_one_hotpatcher.runtime import RuntimeClient
    from sd_webui_all_in_one_hotpatcher.runtime.errors import uninstall_error_capture
    from sd_webui_all_in_one_hotpatcher.runtime.logs import uninstall_log_capture
    from sd_webui_all_in_one_hotpatcher.stack_shadow import uninstall_stack_shadower
    from sd_webui_all_in_one_hotpatcher.state import HotpatcherState
    from sd_webui_all_in_one_hotpatcher_ext.uv_pip import unpatch_uv_to_subprocess

    return SimpleNamespace(
        monkey_zoo=monkey_zoo,
        services=services,
        RuntimeClient=RuntimeClient,
        HotpatcherState=HotpatcherState,
        uninstall=(uninstall_error_capture, uninstall_log_capture, uninstall_import_hook, uninstall_stack_shadower),
        unpatch_uv_to_subprocess=unpatch_uv_to_subprocess,
    )


@pytest.fixture
def hp():
    return _hotpatcher()


@pytest.fixture
def state(hp):
    isolated = hp.HotpatcherState()
    yield isolated
    for target in (isolated, None):
        hp.services.clear_current_config(state=target)
        for uninstall in hp.uninstall:
            uninstall(state=target)
    hp.unpatch_uv_to_subprocess()
    hp.monkey_zoo.clear()


def test_host_accepts_control_hello_feature_and_serves_control_commands(hp, state):
    with HotpatcherRuntimeHost(port=0, token="host-token") as host:
        host_name, port = host.server_address
        with hp.RuntimeClient.connect(host_name, port, token="host-token") as client:
            channel = hp.services.install_service_control_channel(client, state=state)
            try:
                assert wait_for_service_channel(host)
                hello = next(entry.message for entry in host.messages if entry.message.get("type") == "hello")
                assert "control" in hello["features"]

                capabilities = host.request_services("hotpatch.capabilities", timeout=5)
                assert capabilities["control_version"] == 1
                assert capabilities["transport"] == "legacy"
                assert "hotpatch.patches.list" in capabilities["commands"]
                assert host.request_services("hotpatch.patches.list", timeout=5) == {"patches": [], "count": 0, "truncated": False}

                # GUI 远程应用回传完整的规范化配置 (包含 control.patch_sets: [] 与 allow_remote_load: false), 不会触发 D6 门禁。
                config = hp.services.get_default_config()
                config["core"]["import_hook"]["enabled"] = False
                config["core"]["stack_shadow"]["enabled"] = False
                config["extensions"]["comfyui_auto_port"]["enabled"] = False
                config["extensions"]["xformers_cutlass"]["enabled"] = False
                assert host.apply_remote_config(config, timeout=5)["errors"] == []

                with pytest.raises(RemoteServiceError) as exc_info:
                    host.request_services("hotpatch.sets.load", {"source": "json"}, timeout=5)
                assert exc_info.value.code == "remote_load_disabled"
            finally:
                channel.close()
