"""运行时配置加载工具"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..exceptions import capture_exception
from .client import RuntimeClient


def load_config(
    *,
    client: RuntimeClient | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """
    加载运行时配置

    支持从环境变量 JSON、JSON 配置文件、远程宿主或 auto 模式自动选择配置来源。

    Args:
        client (RuntimeClient | None):
            已连接的运行时客户端。远程配置需要该参数, 未传入时会按环境变量连接。
        source (str | None):
            配置来源, 支持 ``env``、``file``、``remote``、``auto``。

    Returns:
        dict[str, Any]:
            配置对象。auto 模式无法获取配置时返回空字典。

    Raises:
        ValueError:
            配置来源非法, 或配置 JSON 不是对象。
    """

    source = (source or os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "auto")).lower()
    if source not in {"env", "file", "remote", "auto"}:
        raise ValueError("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE must be env, file, remote, or auto")

    if source == "env":
        return _load_env_config()

    if source == "file":
        return _load_file_config()

    if source == "remote":
        return _load_remote_config(client)

    env_json = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON")
    if env_json:
        return _load_env_config()

    config_file = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE")
    if config_file:
        return _load_file_config()

    if client is None and not (os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST") and os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT")):
        return {}

    try:
        return _load_remote_config(client)
    except Exception:
        capture_exception()
        return {}


def _load_env_config() -> dict[str, Any]:
    raw = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON")
    if not raw:
        return {}
    config = json.loads(raw)
    if not isinstance(config, dict):
        raise ValueError("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON must decode to an object")
    return config


def _load_file_config() -> dict[str, Any]:
    config_file = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE")
    if not config_file:
        return {}

    config_path = Path(config_file).expanduser()
    with config_path.open("r", encoding="utf-8") as file:
        config = json.load(file)
    if not isinstance(config, dict):
        raise ValueError("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE must decode to an object")
    return config


def _load_remote_config(client: RuntimeClient | None) -> dict[str, Any]:
    if client is None:
        client = RuntimeClient.connect_from_env(required=True)
    assert client is not None
    return client.get_config()
