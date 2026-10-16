"""Hotpatcher 配置测试"""

import json
import os
import subprocess
import sys

import pytest

from sd_webui_all_in_one.base_manager.hotpatcher_manager import (
    DEFAULT_HOTPATCHER_CONFIG_PATH,
    HOTPATCHER_PATH,
    export_hotpatcher_default_config,
    get_hotpatcher_catalog,
    get_hotpatcher_default_config,
    load_hotpatcher_config,
    save_hotpatcher_config,
)
from sd_webui_all_in_one.config import SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_PATH


def test_hotpatcher_import_path_is_injected(monkeypatch):
    patcher_path = HOTPATCHER_PATH.as_posix()
    monkeypatch.setattr(sys, "path", [item for item in sys.path if item != patcher_path])

    config = get_hotpatcher_default_config()

    assert patcher_path in sys.path
    assert "core" in config


def test_hotpatcher_catalog_schema_is_json_serializable():
    catalog = get_hotpatcher_catalog()

    assert json.loads(json.dumps(catalog, ensure_ascii=False)) == catalog
    services = catalog["features"]["services"]
    assert services["title"] == "服务控制"
    assert services["settings"]["apply_on_bootstrap"]["type"] == "bool"
    assert "default" in services["settings"]["apply_on_bootstrap"]
    assert catalog["features"]["extensions.comfyui_auto_port"]["settings"]["enabled"]["default"] is True
    assert catalog["features"]["extensions.uv_pip"]["settings"]["symlink"]["type"] == "bool"


def test_hotpatcher_config_export_load_save_and_overwrite_guard(tmp_path):
    output = tmp_path / "hotpatcher.json"

    exported = export_hotpatcher_default_config(output)

    assert exported == output
    assert load_hotpatcher_config(output)["core"]["import_hook"]["enabled"] is True
    with pytest.raises(FileExistsError):
        export_hotpatcher_default_config(output)

    partial = tmp_path / "partial.json"
    partial.write_text(json.dumps({"extensions": {"hf_endpoint_mirror": {"enabled": True}}}), encoding="utf-8")
    normalized = load_hotpatcher_config(partial, normalize=True)
    assert normalized["extensions"]["hf_endpoint_mirror"]["enabled"] is True
    assert "zluda" in normalized["extensions"]
    assert "uv_pip" in normalized["extensions"]

    saved = tmp_path / "saved.json"
    save_hotpatcher_config(saved, {"core": {"import_hook": {"enabled": True}}})
    saved_config = json.loads(saved.read_text(encoding="utf-8"))
    assert saved_config["core"]["import_hook"]["enabled"] is True
    assert "runtime" in saved_config


def test_default_hotpatcher_config_path_uses_launch_path():
    assert DEFAULT_HOTPATCHER_CONFIG_PATH == SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_PATH
    assert DEFAULT_HOTPATCHER_CONFIG_PATH.name == "patcher_config.json"


def test_hotpatcher_config_path_can_be_configured_with_env(tmp_path):
    config_path = tmp_path / "custom-hotpatcher.json"
    env = os.environ.copy()
    env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_PATH"] = config_path.as_posix()
    code = """
import json
from sd_webui_all_in_one.config import SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_PATH
from sd_webui_all_in_one.base_manager.hotpatcher_manager import DEFAULT_HOTPATCHER_CONFIG_PATH

print(json.dumps({
    "config": SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_PATH.as_posix(),
    "default": DEFAULT_HOTPATCHER_CONFIG_PATH.as_posix(),
}, sort_keys=True))
"""

    output = subprocess.check_output([sys.executable, "-c", code], env=env, text=True, timeout=10)

    assert json.loads(output) == {
        "config": config_path.as_posix(),
        "default": config_path.as_posix(),
    }


def test_hotpatcher_get_runtime_config_returns_deepcopy():
    from sd_webui_all_in_one.patcher.sd_webui_all_in_one_hotpatcher.bootstrap import get_runtime_config
    from sd_webui_all_in_one.patcher.sd_webui_all_in_one_hotpatcher.state import HotpatcherState

    state = HotpatcherState()
    state.bootstrap_runtime_config = {
        "core": {"import_hook": {"enabled": True}},
        "items": ["existing"],
    }

    snapshot = get_runtime_config(state=state)
    snapshot["core"]["import_hook"]["enabled"] = False
    snapshot["items"].append("changed")

    assert state.bootstrap_runtime_config["core"]["import_hook"]["enabled"] is True
    assert state.bootstrap_runtime_config["items"] == ["existing"]
