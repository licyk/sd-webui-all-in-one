"""Implementation grouped from the former ``fooocus_base.py`` module."""

from __future__ import annotations

from pathlib import Path
from sd_webui_all_in_one.base_manager.snapshot import WebUiSnapshot, build_webui_snapshot
from sd_webui_all_in_one.base_manager.environment_info import WebUiEnvironmentInfo, build_webui_environment_info
from sd_webui_all_in_one.base_manager.version_manager import WebUiUpdateOptions, WebUiUpdateStatus, check_webui_updates


def check_fooocus_updates(
    fooocus_path: Path,
    options: WebUiUpdateOptions | None = None,
) -> WebUiUpdateStatus:
    """检查 Fooocus 的内核和 PyTorch 更新。

    Args:
        fooocus_path (Path): Fooocus 根目录。
        options (WebUiUpdateOptions | None): 更新检查选项。

    Returns:
        WebUiUpdateStatus: 结构化更新检查结果。
    """
    return check_webui_updates("fooocus", "Fooocus", fooocus_path, options=options)


def get_fooocus_snapshot(
    fooocus_path: Path,
    include_packages: bool = True,
) -> WebUiSnapshot:
    """获取 Fooocus 环境快照

    Args:
        fooocus_path (Path):
            Fooocus 根目录
        include_packages (bool):
            是否记录当前 Python 环境已安装软件包

    Returns:
        WebUiSnapshot:
            Fooocus 环境快照
    """
    return build_webui_snapshot(
        webui_name="Fooocus",
        webui_type="fooocus",
        webui_path=fooocus_path,
        include_packages=include_packages,
    )


def get_fooocus_environment_info(
    fooocus_path: Path,
    include_packages: bool = True,
) -> WebUiEnvironmentInfo:
    """获取 Fooocus 环境信息报告。

    Args:
        fooocus_path (Path): Fooocus 根目录。
        include_packages (bool): 是否记录当前 Python 环境已安装软件包。

    Returns:
        WebUiEnvironmentInfo: 主机信息和 WebUI 快照组成的环境报告。
    """
    return build_webui_environment_info(get_fooocus_snapshot(fooocus_path, include_packages))
