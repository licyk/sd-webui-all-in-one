"""Hotpatcher 启动环境: host / token 参数、用户覆盖变量保留、两个构建函数的连接变量一致性。"""

import os

import pytest

from sd_webui_all_in_one.base_manager.hotpatcher_manager import (
    DEFAULT_RUNTIME_PORT,
    HOTPATCHER_PATH,
    apply_hotpatcher_launch_env,
    build_hotpatcher_runtime_env,
    ensure_hotpatcher_pythonpath_first,
)
from sd_webui_all_in_one.base_manager.hotpatcher_manager import config as hotpatcher_config

P = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_"
CONNECTION_KEYS = (f"{P}RUNTIME", f"{P}HOST", f"{P}PORT", f"{P}SERVICES", f"{P}TOKEN")
DEBUG_OVERRIDES = {f"{P}DEBUG": "1", f"{P}TRACE": "load,unload", f"{P}TRACE_FILE": "/tmp/trace.log", f"{P}STRICT": "1"}
RUNTIME_OVERRIDES = {
    f"{P}TOKEN": "inherited",
    f"{P}TIMEOUT": "3",
    f"{P}CONNECT_TIMEOUT": "1.5",
    f"{P}REQUEST_TIMEOUT": "7",
    f"{P}EVENT_WRITE_TIMEOUT": "0.5",
    f"{P}RECONNECT": "1",
    f"{P}ALLOW_NON_LOOPBACK": "1",
}
NOT_PRESERVED = {f"{P}TRANSPORT_MODE": "desktop_broker", f"{P}LOG_POLICY": "drop", f"{P}HOST": "10.0.0.9", f"{P}PORT": "1"}


@pytest.fixture
def config_file(monkeypatch, tmp_path):
    path = tmp_path / "patcher_config.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(hotpatcher_config, "DEFAULT_HOTPATCHER_CONFIG_PATH", path)
    return path


def test_default_runtime_output_is_unchanged(config_file):
    origin = {"PYTHONPATH": "existing", f"{P}TOKEN": "secret", "OTHER": "kept"}

    env = apply_hotpatcher_launch_env(origin, enabled=True, enable_runtime=True)

    assert env == {
        "PYTHONPATH": os.pathsep.join([HOTPATCHER_PATH.as_posix(), "existing"]),
        "OTHER": "kept",
        f"{P}TOKEN": "secret",
        f"{P}RUNTIME": "1",
        f"{P}HOST": "127.0.0.1",
        f"{P}PORT": str(DEFAULT_RUNTIME_PORT),
        f"{P}SERVICES": "1",
        f"{P}CONFIG_SOURCE": "file",
        f"{P}CONFIG_FILE": config_file.as_posix(),
    }
    assert apply_hotpatcher_launch_env(origin, enabled=True, enable_runtime=True, host="127.0.0.1", token=None) == env


def test_host_and_token_parameters(config_file):
    origin = {f"{P}TOKEN": "inherited"}

    env = apply_hotpatcher_launch_env(origin, enabled=True, enable_runtime=True, host="localhost", port=9001, token="explicit")
    assert (env[f"{P}HOST"], env[f"{P}PORT"], env[f"{P}TOKEN"]) == ("localhost", "9001", "explicit")

    assert apply_hotpatcher_launch_env(origin, enabled=True, enable_runtime=True)[f"{P}TOKEN"] == "inherited"
    assert f"{P}TOKEN" not in apply_hotpatcher_launch_env(origin, enabled=True, enable_runtime=True, token="")
    assert apply_hotpatcher_launch_env({}, enabled=True, enable_runtime=True, token="fresh")[f"{P}TOKEN"] == "fresh"

    # 未启用 runtime 时 host / token 不注入任何连接变量。
    local = apply_hotpatcher_launch_env(origin, enabled=True, host="localhost", token="explicit")
    assert not any(key in local for key in CONNECTION_KEYS)
    # 非回环 host 不会隐式添加 ALLOW_NON_LOOPBACK。
    assert f"{P}ALLOW_NON_LOOPBACK" not in apply_hotpatcher_launch_env({}, enabled=True, enable_runtime=True, host="0.0.0.0")


def test_user_overrides_are_preserved(config_file):
    origin = {**DEBUG_OVERRIDES, **RUNTIME_OVERRIDES, **NOT_PRESERVED}

    runtime = apply_hotpatcher_launch_env(origin, enabled=True, enable_runtime=True, port=9002)
    for key, value in {**DEBUG_OVERRIDES, **RUNTIME_OVERRIDES}.items():
        assert runtime[key] == value, key
    assert f"{P}TRANSPORT_MODE" not in runtime and f"{P}LOG_POLICY" not in runtime
    assert (runtime[f"{P}HOST"], runtime[f"{P}PORT"]) == ("127.0.0.1", "9002")

    # 调试变量与 runtime 无关, 未启用 runtime 时同样保留; 连接变量只在启用 runtime 时保留。
    local = apply_hotpatcher_launch_env(origin, enabled=True)
    for key, value in DEBUG_OVERRIDES.items():
        assert local[key] == value, key
    assert not any(key in local for key in RUNTIME_OVERRIDES)
    assert not any(key in local for key in NOT_PRESERVED)

    # 关闭 hotpatcher 时仍然移除全部前缀变量。
    disabled = apply_hotpatcher_launch_env(origin, enabled=False)
    assert not any(key.startswith(P) for key in disabled)


@pytest.mark.parametrize(("host", "port", "token"), [("127.0.0.1", 8765, ""), ("localhost", 9100, "secret")])
def test_builders_agree_on_connection_variables(config_file, host, port, token):
    partial = build_hotpatcher_runtime_env(host, port, token=token)
    launch = apply_hotpatcher_launch_env({"PYTHONPATH": "existing"}, enabled=True, enable_runtime=True, host=host, port=port, token=token)

    assert {key: partial.get(key) for key in CONNECTION_KEYS} == {key: launch.get(key) for key in CONNECTION_KEYS}
    # 部分环境的 PYTHONPATH 等价于对空环境前置 hotpatcher 目录。
    assert partial["PYTHONPATH"] == ensure_hotpatcher_pythonpath_first({})["PYTHONPATH"] == HOTPATCHER_PATH.as_posix()
    assert launch["PYTHONPATH"].split(os.pathsep)[0] == partial["PYTHONPATH"]

    # 文档约定的合并方式: 合并 PYTHONPATH 以外的变量后再前置 hotpatcher 目录, 保留原有路径。
    merged = ensure_hotpatcher_pythonpath_first({"PYTHONPATH": "existing", **{key: value for key, value in partial.items() if key != "PYTHONPATH"}})
    assert merged["PYTHONPATH"] == launch["PYTHONPATH"]
    assert {key: merged.get(key) for key in CONNECTION_KEYS} == {key: launch.get(key) for key in CONNECTION_KEYS}
