"""Implementation grouped from the former ``sd_trainer_base.py`` module."""

from __future__ import annotations

from pathlib import Path
from sd_webui_all_in_one.base_manager.snapshot import WebUiSnapshot, build_webui_snapshot
from sd_webui_all_in_one.base_manager.environment_info import WebUiEnvironmentInfo, build_webui_environment_info
from sd_webui_all_in_one.base_manager.version_manager import WebUiUpdateOptions, WebUiUpdateStatus, check_webui_updates


def check_sd_trainer_updates(
    sd_trainer_path: Path,
    options: WebUiUpdateOptions | None = None,
) -> WebUiUpdateStatus:
    """检查 SD Trainer 的内核和 PyTorch 更新。

    Args:
        sd_trainer_path (Path): SD Trainer 根目录。
        options (WebUiUpdateOptions | None): 更新检查选项。

    Returns:
        WebUiUpdateStatus: 结构化更新检查结果。
    """
    return check_webui_updates("sd_trainer", "SD Trainer", sd_trainer_path, options=options)


def get_sd_trainer_snapshot(
    sd_trainer_path: Path,
    include_packages: bool = True,
) -> WebUiSnapshot:
    """获取 SD Trainer 环境快照

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        include_packages (bool):
            是否记录当前 Python 环境已安装软件包

    Returns:
        WebUiSnapshot:
            SD Trainer 环境快照
    """
    return build_webui_snapshot(
        webui_name="SD Trainer",
        webui_type="sd_trainer",
        webui_path=sd_trainer_path,
        include_packages=include_packages,
    )


def get_sd_trainer_environment_info(
    sd_trainer_path: Path,
    include_packages: bool = True,
) -> WebUiEnvironmentInfo:
    """获取 SD Trainer 环境信息报告。

    Args:
        sd_trainer_path (Path): SD Trainer 根目录。
        include_packages (bool): 是否记录当前 Python 环境已安装软件包。

    Returns:
        WebUiEnvironmentInfo: 主机信息和 WebUI 快照组成的环境报告。
    """
    return build_webui_environment_info(get_sd_trainer_snapshot(sd_trainer_path, include_packages))
