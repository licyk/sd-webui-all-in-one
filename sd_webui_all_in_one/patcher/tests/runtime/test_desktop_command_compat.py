"""桌面端 ``config.apply`` 命令结果兼容性测试

冻结 ``bootstrap._handle_desktop_command`` 的返回结构与错误码, 桌面端依赖 ``applyResult`` 的 applied/warnings/errors 结构。
"""

import importlib.util
import sys

import pytest

from sd_webui_all_in_one_hotpatcher import bootstrap, monkey_zoo, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher.runtime.desktop_broker import DesktopBrokerCommandError
from sd_webui_all_in_one_hotpatcher.runtime.errors import uninstall_error_capture
from sd_webui_all_in_one_hotpatcher.runtime.logs import uninstall_log_capture
from sd_webui_all_in_one_hotpatcher.services import clear_current_config, get_current_config
from sd_webui_all_in_one_hotpatcher.stack_shadow import uninstall_stack_shadower
from sd_webui_all_in_one_hotpatcher.state import HotpatcherState
from sd_webui_all_in_one_hotpatcher_ext.uv_pip import unpatch_uv_to_subprocess


def _reset(state: HotpatcherState) -> None:
    for target in (state, None):
        clear_current_config(state=target)
        uninstall_error_capture(state=target)
        uninstall_log_capture(state=target)
        uninstall_import_hook(state=target)
        uninstall_stack_shadower(state=target)
    unpatch_uv_to_subprocess()
    monkey_zoo.clear()


@pytest.fixture
def state():
    isolated = HotpatcherState()
    _reset(isolated)
    meta_path_before = list(sys.meta_path)
    spec_from_file_location_before = importlib.util.spec_from_file_location
    yield isolated
    _reset(isolated)
    assert sys.meta_path == meta_path_before
    assert importlib.util.spec_from_file_location is spec_from_file_location_before


def test_config_apply_returns_apply_result_envelope(state):
    result = bootstrap._handle_desktop_command(
        "config.apply",
        {"config": {"runtime": {"errors": {"enabled": True}}}},
        state=state,
    )

    assert list(result) == ["applyResult"]
    apply_result = result["applyResult"]
    assert list(apply_result) == ["applied", "warnings", "errors"]
    assert apply_result["applied"][:2] == ["core.import_hook", "core.stack_shadow"]
    assert all(isinstance(feature, str) for feature in apply_result["applied"])
    assert apply_result["warnings"] == [{"feature": "runtime.errors", "message": "runtime_client is required to enable errors"}]
    assert apply_result["errors"] == []
    assert get_current_config(state=state)["runtime"]["errors"]["enabled"] is True


def test_unknown_command_raises_typed_error(state):
    with pytest.raises(DesktopBrokerCommandError) as exc_info:
        bootstrap._handle_desktop_command("file.delete", {}, state=state)

    assert exc_info.value.code == "unknown_command"
    assert str(exc_info.value) == "unsupported desktop broker command: file.delete"


@pytest.mark.parametrize("payload", [{}, {"config": None}, {"config": []}, {"config": "{}"}])
def test_non_object_config_raises_invalid_command_payload(state, payload):
    with pytest.raises(DesktopBrokerCommandError) as exc_info:
        bootstrap._handle_desktop_command("config.apply", payload, state=state)

    assert exc_info.value.code == "invalid_command_payload"
    assert str(exc_info.value) == "config.apply payload.config must be an object"
    assert state.current_config is None
