"""Implementation grouped from the former ``comfyui_base.py`` module."""

from __future__ import annotations

from pathlib import Path
from sd_webui_all_in_one.base_manager.comfy_registry import (
    fetch_comfy_registry_versions,
)
from sd_webui_all_in_one.base_manager.snapshot import (
    WebUiSnapshot,
    build_webui_snapshot,
)
from sd_webui_all_in_one.base_manager.environment_info import WebUiEnvironmentInfo, build_webui_environment_info
from sd_webui_all_in_one.base_manager.version_manager import (
    ManagedExtension,
    WebUiUpdateOptions,
    WebUiUpdateStatus,
    check_webui_updates,
)

from .extensions import ComfyUiExtensionManager, collect_comfyui_extensions


def check_comfyui_updates(
    comfyui_path: Path,
    options: WebUiUpdateOptions | None = None,
) -> WebUiUpdateStatus:
    """检查 ComfyUI 的内核、自定义节点和 PyTorch 更新。

    Args:
        comfyui_path (Path): ComfyUI 根目录。
        options (WebUiUpdateOptions | None): 更新检查选项。

    Returns:
        WebUiUpdateStatus: 结构化更新检查结果。
    """
    manager = ComfyUiExtensionManager(comfyui_path, include_files=True)

    def resolve_registry_version(extension: ManagedExtension) -> str | None:
        node_id = extension.registry_id or extension.name.removesuffix(".disabled")
        versions = fetch_comfy_registry_versions(node_id, timeout=(options or WebUiUpdateOptions()).timeout)
        return versions[0].version if versions else None

    return check_webui_updates(
        "comfyui",
        "ComfyUI",
        comfyui_path,
        extension_loader=manager.list_extensions,
        registry_version_resolver=resolve_registry_version,
        options=options,
    )


def get_comfyui_snapshot(
    comfyui_path: Path,
    include_packages: bool = True,
) -> WebUiSnapshot:
    """获取 ComfyUI 环境快照

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        include_packages (bool):
            是否记录当前 Python 环境已安装软件包

    Returns:
        WebUiSnapshot:
            ComfyUI 环境快照
    """
    return build_webui_snapshot(
        webui_name="ComfyUI",
        webui_type="comfyui",
        webui_path=comfyui_path,
        include_packages=include_packages,
        extensions=collect_comfyui_extensions(comfyui_path),
    )


def get_comfyui_environment_info(
    comfyui_path: Path,
    include_packages: bool = True,
) -> WebUiEnvironmentInfo:
    """获取 ComfyUI 环境信息报告。

    Args:
        comfyui_path (Path): ComfyUI 根目录。
        include_packages (bool): 是否记录当前 Python 环境已安装软件包。

    Returns:
        WebUiEnvironmentInfo: 主机信息和 WebUI 快照组成的环境报告。
    """
    return build_webui_environment_info(get_comfyui_snapshot(comfyui_path, include_packages))
