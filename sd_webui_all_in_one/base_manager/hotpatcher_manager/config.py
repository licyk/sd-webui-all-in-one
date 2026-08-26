"""Hotpatcher configuration and launch environment."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, TYPE_CHECKING

from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME, ROOT_PATH, SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_PATH
from sd_webui_all_in_one.logger import get_logger

if TYPE_CHECKING:
    from sd_webui_all_in_one_hotpatcher import services

logger = get_logger(name=LOGGER_NAME, level=LOGGER_LEVEL, color=LOGGER_COLOR)
HOTPATCHER_PATH = ROOT_PATH / "patcher"
DEFAULT_HOTPATCHER_CONFIG_PATH = SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_PATH
DEFAULT_RUNTIME_HOST = "127.0.0.1"
DEFAULT_RUNTIME_PORT = 8765
HOTPATCHER_ENV_PREFIX = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_"


def ensure_hotpatcher_import_path() -> Path:
    """
    确保抽取版 hotpatcher 目录可以被导入。

    Returns:
        Path:
            hotpatcher 源码目录。
    """

    path_text = HOTPATCHER_PATH.as_posix()
    if path_text not in sys.path:
        logger.debug("将 hotpatcher 源码目录 %s 插入 sys.path 首位", path_text)
        sys.path.insert(0, path_text)
    return HOTPATCHER_PATH


def _services_module() -> "services":  # ty: ignore[invalid-type-form]
    ensure_hotpatcher_import_path()
    from sd_webui_all_in_one_hotpatcher import services

    logger.debug("加载 hotpatcher services 模块")
    return services


def get_hotpatcher_default_config() -> dict[str, Any]:
    """
    获取 hotpatcher 默认配置

    Returns:
        dict[str, Any]:
            hotpatcher services 提供的默认配置。
    """

    config = _services_module().get_default_config()
    logger.debug("获取 hotpatcher 默认配置")
    return config


def get_hotpatcher_catalog() -> dict[str, Any]:
    """
    获取 hotpatcher 功能目录

    Returns:
        dict[str, Any]:
            hotpatcher features catalog 和已注册补丁信息。
    """

    catalog = _services_module().get_catalog()
    logger.debug("获取 hotpatcher 功能目录")
    return catalog


def normalize_hotpatcher_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    补齐 hotpatcher 配置默认值

    Args:
        config (dict[str, Any]):
            原始配置对象。

    Returns:
        dict[str, Any]:
            补齐默认值后的配置对象。
    """

    logger.debug("补齐 hotpatcher 配置默认值")
    return _services_module().normalize_config(config)


def _resolve_config_path(path: str | Path | None = None) -> Path:
    return Path(path).expanduser() if path is not None else DEFAULT_HOTPATCHER_CONFIG_PATH


def load_hotpatcher_config(path: str | Path | None = None, normalize: bool = True) -> dict[str, Any]:
    """
    读取 hotpatcher JSON 配置文件。

    Args:
        path (str | Path | None):
            配置文件路径。为 None 时使用默认配置路径。
        normalize (bool):
            是否补齐默认值。

    Returns:
        dict[str, Any]:
            配置对象。

    Raises:
        ValueError:
            配置文件内容不是 JSON 对象时抛出。
    """

    config_path = _resolve_config_path(path)
    logger.debug("读取 hotpatcher 配置, 路径: %s, normalize: %s", config_path, normalize)
    if normalize:
        config = _services_module().load_config_file(config_path, write_back=False)
    else:
        with config_path.open("r", encoding="utf-8") as file:
            config = json.load(file)
        if not isinstance(config, dict):
            logger.error("hotpatcher 配置文件 %s 内容不是 JSON 对象", config_path)
            raise ValueError("hotpatcher config file must decode to an object")
    logger.debug("hotpatcher 配置加载完成, 配置键: %s", list(config.keys()))
    return config


def save_hotpatcher_config(path: str | Path | None, config: dict[str, Any]) -> None:
    """
    保存 hotpatcher JSON 配置文件

    Args:
        path (str | Path | None):
            配置文件路径。为 None 时使用默认配置路径。
        config (dict[str, Any]):
            要写出的配置对象。
    """

    config_path = _resolve_config_path(path)
    logger.info("保存 hotpatcher 配置, 路径: %s", config_path)
    _services_module().save_config_file(config_path, config)


def export_hotpatcher_default_config(path: str | Path | None = None, overwrite: bool = False) -> Path:
    """
    导出 hotpatcher 默认配置。

    Args:
        path (str | Path | None):
            输出路径。为 None 时使用默认配置路径。
        overwrite (bool):
            是否覆盖已有文件。

    Returns:
        Path:
            写出的配置文件路径。

    Raises:
        FileExistsError:
            配置文件已存在且未允许覆盖时抛出。
    """

    output_path = _resolve_config_path(path)
    if output_path.exists() and not overwrite:
        logger.warning("导出目标文件已存在且未允许覆盖, 路径: %s", output_path)
        raise FileExistsError(f"Config file already exists: {output_path}")
    logger.info("导出 hotpatcher 默认配置, 路径: %s, overwrite: %s", output_path, overwrite)
    save_hotpatcher_config(output_path, get_hotpatcher_default_config())
    return output_path


def apply_hotpatcher_config(config_or_path: dict[str, Any] | str | Path | None = None) -> dict[str, Any]:
    """
    应用 hotpatcher 配置到当前进程。

    Args:
        config_or_path (dict[str, Any] | str | Path | None):
            配置对象或配置文件路径。为 None 时读取默认配置路径。

    Returns:
        dict[str, Any]:
            services.apply_config 返回的应用结果。
    """

    if isinstance(config_or_path, dict):
        config = config_or_path
        logger.debug("直接应用传入的 hotpatcher 配置对象")
    else:
        logger.debug("从路径加载 hotpatcher 配置: %s", config_or_path)
        config = load_hotpatcher_config(config_or_path, normalize=True)
    result = _services_module().apply_config(config)
    logger.info("hotpatcher 配置应用完成")
    return result


def apply_hotpatcher_launch_env(
    origin_env: dict[str, str] | None = None,
    enabled: bool = False,
    config_path: str | Path | None = None,
    port: int = DEFAULT_RUNTIME_PORT,
    enable_runtime: bool = False,
) -> dict[str, str]:
    """
    为 WebUI 启动环境注入 hotpatcher bootstrap 变量。

    Args:
        origin_env (dict[str, str] | None):
            原始环境变量。
        enabled (bool):
            是否启用 hotpatcher。关闭时会移除现有 hotpatcher 环境变量。
        config_path (str | Path | None):
            配置文件路径。为 None 时优先使用默认配置文件，不存在则注入默认配置 JSON。
        port (int):
            runtime host 端口。
        enable_runtime (bool):
            是否注入 runtime host 连接变量。默认只做本地补丁配置注入。

    Returns:
        dict[str, str]:
            注入后的环境变量。
    """

    env = origin_env.copy() if origin_env is not None else os.environ.copy()
    preserved_keys = {"SD_WEBUI_ALL_IN_ONE_HOTPATCHER_DEBUG"}
    if enable_runtime:
        preserved_keys.update(
            {
                "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN",
                "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TIMEOUT",
            }
        )
    preserved = {key: value for key, value in env.items() if key in preserved_keys}
    env = remove_hotpatcher_launch_env(env)

    if not enabled:
        logger.info("hotpatcher 未启用, 已移除相关启动环境变量")
        return env

    env.update(preserved)
    env = ensure_hotpatcher_pythonpath_first(env)
    if enable_runtime:
        env.update(
            {
                "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME": "1",
                "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST": DEFAULT_RUNTIME_HOST,
                "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT": str(port),
                "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES": "1",
            }
        )

    if config_path is not None:
        env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE"] = "file"
        env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE"] = Path(config_path).expanduser().as_posix()
    elif DEFAULT_HOTPATCHER_CONFIG_PATH.is_file():
        env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE"] = "file"
        env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE"] = DEFAULT_HOTPATCHER_CONFIG_PATH.as_posix()
    else:
        env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE"] = "env"
        env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_JSON"] = json.dumps(
            get_hotpatcher_default_config(),
            ensure_ascii=False,
            separators=(",", ":"),
        )
    config_source = env.get("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE", "unknown")
    config_file = env.get("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_FILE")
    logger.info(
        "hotpatcher 启动环境注入完成, 配置来源: %s, 配置文件: %s, enable_runtime: %s",
        config_source,
        config_file,
        enable_runtime,
    )
    return env


def configure_hotpatcher_for_current_process(enabled: bool = False) -> Any:
    """
    在当前 Python 进程中根据 hotpatcher 环境变量执行 bootstrap

    InvokeAI 这类入口不会新建 Python 子进程, 因此不能依赖 sitecustomize
    在解释器启动时自动执行。

    Args:
        enabled (bool):
            是否启用当前进程 hotpatcher bootstrap。

    Returns:
        Any:
            ``bootstrap.configure_from_env()`` 返回的状态对象。未启用时返回 None。
    """

    if not enabled:
        return None
    logger.info("在当前进程执行 hotpatcher bootstrap")
    ensure_hotpatcher_import_path()
    from sd_webui_all_in_one_hotpatcher.bootstrap import configure_from_env

    state = configure_from_env()
    logger.debug("hotpatcher bootstrap 完成")
    return state


def remove_hotpatcher_launch_env(origin_env: dict[str, str]) -> dict[str, str]:
    """
    移除 hotpatcher 启动环境变量

    Args:
        origin_env (dict[str, str]):
            原始环境变量。

    Returns:
        dict[str, str]:
            移除 hotpatcher 前缀变量后的环境变量。
    """

    env = {key: value for key, value in origin_env.items() if not key.startswith(HOTPATCHER_ENV_PREFIX)}
    logger.debug("已移除 %d 个 hotpatcher 前缀环境变量", len(origin_env) - len(env))
    return env


def ensure_hotpatcher_pythonpath_first(origin_env: dict[str, str]) -> dict[str, str]:
    """
    确保 hotpatcher 目录位于 PYTHONPATH 第一项

    Args:
        origin_env (dict[str, str]):
            原始环境变量。

    Returns:
        dict[str, str]:
            调整 PYTHONPATH 后的环境变量。
    """

    env = origin_env.copy()
    path_text = HOTPATCHER_PATH.as_posix()
    current = env.get("PYTHONPATH", "")
    parts = [item for item in current.split(os.pathsep) if item and item != path_text]
    env["PYTHONPATH"] = os.pathsep.join([path_text, *parts])
    logger.debug("确保 hotpatcher 目录 %s 位于 PYTHONPATH 首位", path_text)
    return env


def build_hotpatcher_runtime_env(
    host: str,
    port: int,
    token: str = "",
    config_source: str = "remote",
) -> dict[str, str]:
    """
    构建让 hotpatcher 进程连接管理器 runtime host 的环境变量。

    Args:
        host (str):
            runtime host 地址。
        port (int):
            runtime host 端口。
        token (str):
            连接 token。
        config_source (str):
            配置来源。

    Returns:
        dict[str, str]:
            需要传给目标进程的环境变量。
    """

    env = {
        "PYTHONPATH": HOTPATCHER_PATH.as_posix(),
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_RUNTIME": "1",
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_HOST": str(host),
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_PORT": str(port),
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_CONFIG_SOURCE": str(config_source),
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_IMPORT_HOOK": "1",
        "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SERVICES": "1",
    }
    if token:
        env["SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TOKEN"] = token
    logger.debug("构建 hotpatcher runtime 连接环境, host: %s, port: %s, config_source: %s", host, port, config_source)
    return env


def launch_hotpatcher_manager_gui(
    config_path: str | Path | None = DEFAULT_HOTPATCHER_CONFIG_PATH,
    host: str = DEFAULT_RUNTIME_HOST,
    port: int = DEFAULT_RUNTIME_PORT,
    token: str = "",
) -> None:
    """
    启动 hotpatcher 配置管理 GUI

    Args:
        config_path (str | Path | None):
            启动时加载的配置文件路径。
        host (str):
            runtime host 监听地址。
        port (int):
            runtime host 监听端口。
        token (str):
            runtime host 连接 token。

    Raises:
        RuntimeError:
            当前 Python 环境未安装 tkinter 时抛出。
        ModuleNotFoundError:
            启动 GUI 时缺少非 tkinter 模块时继续抛出。
    """

    try:
        from sd_webui_all_in_one.base_manager.gui.hotpatcher_manager_gui import launch_hotpatcher_manager_gui as _launch_gui
    except ModuleNotFoundError as e:
        if e.name == "tkinter":
            logger.error("当前 Python 环境未安装 tkinter, 无法启动补丁系统配置管理 GUI")
            raise RuntimeError("当前 Python 环境未安装 tkinter, 无法启动补丁系统配置管理 GUI") from e
        logger.error("启动 GUI 时缺少模块: %s", e.name)
        raise e

    logger.info("启动 hotpatcher 配置管理 GUI, host: %s, port: %s", host, port)
    _launch_gui(config_path=config_path, host=host, port=port, token=token)
