"""Stable Diffusion WebUI 扩展依赖安装"""

import json
from pathlib import Path

from sd_webui_all_in_one.env_check.shared import logger
from sd_webui_all_in_one.env_check.sd_webui_extension_dependency_installer.runner import (
    run_extension_installer,
)


def install_extension_requirements(
    sd_webui_path: Path,
    custom_env: dict[str, str] | None = None,
) -> None:
    """安装 SD WebUI 扩展依赖

    Args:
        sd_webui_path (Path):
            SD WebUI 根目录
        custom_env (dict[str, str] | None):
            环境变量字典
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
    except FileNotFoundError:
        logger.debug("Stable Diffusion WebUI 配置文件不存在: %s", settings_file)
    except (OSError, ValueError) as e:
        logger.warning("Stable Diffusion WebUI 配置文件无效, 将按所有扩展均已启用处理: %s", e)

    if not isinstance(settings, dict):
        logger.warning("Stable Diffusion WebUI 配置文件内容不是 JSON 对象, 将按所有扩展均已启用处理")
        settings = {}

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
            custom_env=custom_env,
        ):
            logger.info("[%s/%s] 执行 %s 扩展的依赖安装脚本成功", count, extension_count, ext_name)
        else:
            logger.warning("[%s/%s] 执行 %s 扩展的依赖安装脚本失败, 可能会导致该扩展运行异常", count, extension_count, ext_name)

    logger.info("[%s/%s] 安装 Stable Diffusion WebUI 扩展依赖结束", count, extension_count)
