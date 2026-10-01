"""Stable Diffusion WebUI Forge Neo 错误警告修复子进程"""

import sys
import json
from pathlib import Path

from sd_webui_all_in_one.file_manager import move_files
from sd_webui_all_in_one.env_check.shared import logger


def _move_broken_config(
    sd_webui_path: Path,
    config_path: Path,
    reason: object,
) -> None:
    """将损坏的 Stable Diffusion WebUI Forge Neo 配置文件移动到临时目录

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        config_path (Path):
            损坏的配置文件路径
        reason (object):
            配置文件被判定为损坏的原因
    """
    logger.warning("加载 Stable Diffusion WebUI Forge Neo 配置文件发生错误: %s", reason)
    tmp_path = sd_webui_path / "tmp" / "config.json"
    logger.warning("尝试将原有损坏的配置文件移动到 '%s'", tmp_path)
    try:
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        move_files(config_path, tmp_path)
    except (OSError, ValueError) as e:
        logger.error("移除原有损坏的配置文件时发生了错误: %s", e)


def fix_alert_worker(
    sd_webui_path: Path,
) -> None:
    """处理 Stable Diffusion WebUI Forge Neo 配置文件

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录

    Raises:
        OSError:
            保存配置文件失败时
    """
    sys.path.insert(0, sd_webui_path.as_posix())
    config_path = sd_webui_path / "config.json"
    if not config_path.is_file():
        logger.debug("配置文件 '%s' 不存在", config_path)
        return

    try:
        from modules.launch_utils import VERSION_UID  # type: ignore
    except ImportError as e:
        logger.debug("未找到 Stable Diffusion WebUI Forge Neo 版本声明: %s", e)
        return

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        _move_broken_config(sd_webui_path, config_path, e)
        return

    if not isinstance(data, dict):
        _move_broken_config(sd_webui_path, config_path, "配置文件内容不是 JSON 对象")
        return

    if data.get("VERSION_UID", None) == VERSION_UID:
        return

    logger.info("尝试抑制 Stable Diffusion WebUI Forge Neo 警告信息")
    data["VERSION_UID"] = VERSION_UID
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except OSError as e:
        logger.warning("尝试保存 Stable Diffusion WebUI Forge Neo 配置文件时发生了错误: %s", e)
        raise e
