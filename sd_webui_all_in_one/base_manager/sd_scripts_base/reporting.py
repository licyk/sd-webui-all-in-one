"""Implementation grouped from the former ``sd_scripts_base.py`` module."""

from __future__ import annotations

from pathlib import Path
from sd_webui_all_in_one.base_manager.snapshot import WebUiSnapshot, build_webui_snapshot
from sd_webui_all_in_one.base_manager.environment_info import WebUiEnvironmentInfo, build_webui_environment_info
from sd_webui_all_in_one.base_manager.version_manager import WebUiUpdateOptions, WebUiUpdateStatus, check_webui_updates


def check_sd_scripts_updates(
    sd_scripts_path: Path,
    options: WebUiUpdateOptions | None = None,
) -> WebUiUpdateStatus:
    """检查 SD Scripts 的内核和 PyTorch 更新。

    Args:
        sd_scripts_path (Path): SD Scripts 根目录。
        options (WebUiUpdateOptions | None): 更新检查选项。

    Returns:
        WebUiUpdateStatus: 结构化更新检查结果。
    """
    return check_webui_updates("sd_scripts", "SD Scripts", sd_scripts_path, options=options)


def get_sd_scripts_snapshot(
    sd_scripts_path: Path,
    include_packages: bool = True,
) -> WebUiSnapshot:
    """获取 SD Scripts 环境快照

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录
        include_packages (bool):
            是否记录当前 Python 环境已安装软件包

    Returns:
        WebUiSnapshot:
            SD Scripts 环境快照
    """
    return build_webui_snapshot(
        webui_name="SD Scripts",
        webui_type="sd_scripts",
        webui_path=sd_scripts_path,
        include_packages=include_packages,
    )


def get_sd_scripts_environment_info(
    sd_scripts_path: Path,
    include_packages: bool = True,
) -> WebUiEnvironmentInfo:
    """获取 SD Scripts 环境信息报告。

    Args:
        sd_scripts_path (Path): SD Scripts 根目录。
        include_packages (bool): 是否记录当前 Python 环境已安装软件包。

    Returns:
        WebUiEnvironmentInfo: 主机信息和 WebUI 快照组成的环境报告。
    """
    return build_webui_environment_info(get_sd_scripts_snapshot(sd_scripts_path, include_packages))
