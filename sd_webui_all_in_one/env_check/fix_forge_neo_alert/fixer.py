"""Stable Diffusion WebUI Forge Neo 错误警告修复"""

import multiprocessing
from pathlib import Path

from sd_webui_all_in_one.env_check.shared import logger
from sd_webui_all_in_one.env_check.fix_forge_neo_alert.worker import (
    fix_alert_worker,
)


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
        if process.exitcode != 0:
            logger.warning("修复 Stable Diffusion WebUI Neo 的错误警告的子进程异常退出, 退出码: %s", process.exitcode)
    except Exception as e:
        # 该修复仅用于抑制无害的警告信息, 失败时不应阻止 WebUI 启动
        logger.warning("通过子进程修复 Stable Diffusion WebUI Neo 的错误警告失败: %s", e)
    finally:
        if process.is_alive():
            process.terminate()  # 如果还活着, 强制终止
            process.join()  # 终止后必须 join 释放僵尸进程资源
        process.close()  # 确保进程资源被回收
