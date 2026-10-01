"""Stable Diffusion WebUI 扩展安装脚本执行"""

import os
import sys
import traceback
from pathlib import Path

from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.utils import append_python_path
from sd_webui_all_in_one.env_check.shared import logger


def run_extension_installer(
    sd_webui_base_path: Path,
    extension_dir: Path,
    custom_env: dict[str, str] | None = None,
) -> bool:
    """执行扩展依赖安装脚本

    Args:
        sd_webui_base_path (Path):
            SD WebUI 跟目录, 用于导入自身模块
        extension_dir (Path):
            要执行安装脚本的扩展路径
        custom_env (dict[str, str] | None):
            环境变量字典

    Returns:
        bool: 扩展依赖安装结果
    """
    path_installer = extension_dir / "install.py"
    if not path_installer.is_file():
        return False

    if custom_env is None:
        custom_env = os.environ.copy()
    else:
        custom_env = custom_env.copy()

    custom_env = append_python_path(
        new_path=sd_webui_base_path,
        origin_env=custom_env,
    )

    custom_env["WEBUI_LAUNCH_LIVE_OUTPUT"] = "1"

    try:
        run_cmd(
            command=[Path(sys.executable).as_posix(), path_installer.as_posix()],
            custom_env=custom_env,
            cwd=sd_webui_base_path,
        )
        return True
    except RuntimeError as e:
        logger.error("执行 %s 扩展依赖安装脚本时发生错误: %s", extension_dir.name, e)
        traceback.print_exc()
        return False
