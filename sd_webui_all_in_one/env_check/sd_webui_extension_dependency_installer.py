"""Stable Diffusion WebUI 扩展依赖安装工具"""

import os
import sys
import json
import traceback
from pathlib import Path

from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL

logger = get_logger(
    name="SD WebUI Ext Req Installer",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def run_extension_installer(
    sd_webui_base_path: Path,
    extension_dir: Path,
) -> bool:
    """执行扩展依赖安装脚本

    Args:
        sd_webui_base_path (Path):
            SD WebUI 跟目录, 用于导入自身模块
        extension_dir (Path):
            要执行安装脚本的扩展路径

    Returns:
        bool: 扩展依赖安装结果
    """
    path_installer = extension_dir / "install.py"
    if not path_installer.is_file():
        return

    try:
        env = os.environ.copy()
        py_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{sd_webui_base_path}{os.pathsep}{py_path}"
        env["WEBUI_LAUNCH_LIVE_OUTPUT"] = "1"
        run_cmd(
            command=[Path(sys.executable).as_posix(), path_installer.as_posix()],
            custom_env=env,
            cwd=sd_webui_base_path,
        )
        return True
    except Exception as e:
        logger.info("执行 %s 扩展依赖安装脚本时发生错误: %s", extension_dir.name, e)
        traceback.print_exc()
        return False


def install_extension_requirements(
    sd_webui_path: Path,
) -> None:
    """安装 SD WebUI 扩展依赖

    Args:
        sd_webui_path (Path):
            SD WebUI 根目录
    """
    settings_file = sd_webui_path / "config.json"
    extensions_dir = sd_webui_path / "extensions"
    builtin_extensions_dir = sd_webui_path / "extensions-builtin"
    ext_install_list = []
    ext_builtin_install_list = []
    settings = {}

    # 获取 Stable Diffusion WebUI 的配置, 用于查询插件是否被禁用
    try:
        with open(settings_file, "r", encoding="utf-8") as file:
            settings = json.load(file)
    except Exception as e:
        logger.warning("Stable Diffusion WebUI 配置文件无效: %s", e)

    disabled_extensions = set(settings.get("disabled_extensions", []))
    disable_all_extensions = settings.get("disable_all_extensions", "none")

    if disable_all_extensions == "all":
        logger.info("已禁用所有 Stable Diffusion WebUI 扩展, 不执行扩展依赖检查")
        return

    if extensions_dir.is_dir() and disable_all_extensions != "extra":
        ext_install_list = [x for x in extensions_dir.glob("*") if x.name not in disabled_extensions and (x / "install.py").is_file()]

    if builtin_extensions_dir.is_dir():
        ext_builtin_install_list = [x for x in builtin_extensions_dir.glob("*") if x.name not in disabled_extensions and (x / "install.py").is_file()]

    install_list = ext_install_list + ext_builtin_install_list
    extension_count = len(install_list)

    if extension_count == 0:
        logger.info("无待安装依赖的 Stable Diffusion WebUI 扩展")
        return

    count = 0
    for ext in install_list:
        count += 1
        ext_name = ext.name
        logger.info("[%s/%s] 执行 %s 扩展的依赖安装脚本中", count, extension_count, ext_name)
        if run_extension_installer(
            sd_webui_base_path=sd_webui_path,
            extension_dir=ext,
        ):
            logger.info("[%s/%s] 执行 %s 扩展的依赖安装脚本成功", count, extension_count, ext_name)
        else:
            logger.warning("[%s/%s] 执行 %s 扩展的依赖安装脚本失败, 可能会导致该扩展运行异常", count, extension_count, ext_name)

    logger.info("[%s/%s] 安装 Stable Diffusion WebUI 扩展依赖结束", count, extension_count)
