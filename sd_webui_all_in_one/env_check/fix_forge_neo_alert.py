"""修复 Stable Diffusion WebUI Forge Neo 的错误警告"""

import sys
import json
import multiprocessing
from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.file_operations.file_manager import move_files


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def fix_alert_worker(
    sd_webui_path: Path,
) -> None:
    """处理 Stable Diffusion WebUI Forge Neo 配置文件

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
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
    except Exception as e:
        logger.debug("加载 Stable Diffusion WebUI Forge Neo 配置文件发生错误: %s", e)
        logger.debug("尝试移除原有损坏的配置文件")
        try:
            tmp_path = sd_webui_path / "tmp" / "config.json"
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            move_files(config_path, tmp_path)
        except Exception as e1:
            logger.debug("移除原有损坏的配置文件时发生了错误: %s", e1)
        return

    if data.get("VERSION_UID", None) == VERSION_UID:
        return

    logger.info("尝试抑制 Stable Diffusion WebUI Forge Neo 警告信息")
    data["VERSION_UID"] = VERSION_UID
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.warning("尝试保存 Stable Diffusion WebUI Forge Neo 配置文件时发生了错误: %s", e)
        raise e


def fix_forge_neo_alert(
    sd_webui_path: Path,
) -> None:
    """修复 Stable Diffusion WebUI Neo 的错误警告

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
    """
    ctx = multiprocessing.get_context("spawn")
    process = ctx.Process(target=fix_alert_worker, args=(sd_webui_path,), name="ForgeNeoAlertFix")
    try:
        logger.debug("启动子进程修复 Stable Diffusion WebUI Neo 的错误警告")
        process.start()
        process.join()
    except Exception as e:
        logger.debug("通过子进程获修复 Stable Diffusion WebUI Neo 的错误警告失败: %s", e)
    finally:
        if process.is_alive():
            process.terminate()  # 如果还活着, 强制终止
            process.join()  # 终止后必须 join 释放僵尸进程资源
        process.close()  # 确保进程资源被回收
