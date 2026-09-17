"""Product-specific version GUI helpers."""

from __future__ import annotations

import json
from pathlib import Path

from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def _load_sd_webui_config(sd_webui_path: Path) -> dict:
    """读取 Stable Diffusion WebUI 配置文件

    Raises:
        OSError: 配置文件无法读取时
        ValueError: 配置文件不是有效的 JSON 对象时
    """
    config_path = sd_webui_path / "config.json"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"配置文件 '{config_path}' 的内容不是 JSON 对象")
    return data


def _save_sd_webui_config(
    sd_webui_path: Path,
    data: dict,
) -> None:
    config_path = sd_webui_path / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def _sd_webui_extension_enabled(sd_webui_path: Path, name: str, _path: Path) -> bool:
    try:
        settings = _load_sd_webui_config(sd_webui_path)
    except (OSError, ValueError) as e:
        # 仅用于展示状态, 配置损坏时按 WebUI 默认行为视为启用
        logger.warning("读取 Stable Diffusion WebUI 配置文件失败, 扩展 '%s' 的启用状态按默认值显示: %s", name, e)
        return True
    disabled_extensions = set(settings.get("disabled_extensions", []))
    disable_all_extensions = settings.get("disable_all_extensions", "none")
    if disable_all_extensions == "all":
        return False
    if disable_all_extensions == "extra":
        return True
    return name not in disabled_extensions


def _set_sd_webui_extension_enabled(
    sd_webui_path: Path,
    name: str,
    enabled: bool,
) -> None:
    settings = _load_sd_webui_config(sd_webui_path)
    disabled_extensions = settings.setdefault("disabled_extensions", [])
    if not isinstance(disabled_extensions, list):
        disabled_extensions = []
        settings["disabled_extensions"] = disabled_extensions
    if enabled and name in disabled_extensions:
        disabled_extensions.remove(name)
    elif not enabled and name not in disabled_extensions:
        disabled_extensions.append(name)
    _save_sd_webui_config(sd_webui_path, settings)
