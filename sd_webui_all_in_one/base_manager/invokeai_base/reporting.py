"""Implementation grouped from the former ``invokeai_base.py`` module."""

from __future__ import annotations

from pathlib import Path
from sd_webui_all_in_one.base_manager.repository_inspector import inspect_repository
from sd_webui_all_in_one.base_manager.snapshot import (
    WebUiSnapshot,
    build_webui_snapshot,
    collect_git_extensions,
)
from sd_webui_all_in_one.base_manager.environment_info import WebUiEnvironmentInfo, build_webui_environment_info
from sd_webui_all_in_one.base_manager.version_manager import (
    ManagedExtension,
    WebUiUpdateOptions,
    WebUiUpdateStatus,
    check_webui_updates,
)

from .extensions import list_invokeai_custom_nodes


def check_invokeai_updates(
    invokeai_path: Path,
    options: WebUiUpdateOptions | None = None,
) -> WebUiUpdateStatus:
    """检查 InvokeAI 的内核、自定义节点和 PyTorch 更新。

    Args:
        invokeai_path (Path): InvokeAI 根目录。
        options (WebUiUpdateOptions | None): 更新检查选项。

    Returns:
        WebUiUpdateStatus: 结构化更新检查结果。
    """

    def load_extensions() -> list[ManagedExtension]:
        """加载 InvokeAI 自定义节点。"""
        result: list[ManagedExtension] = []
        for item in list_invokeai_custom_nodes(invokeai_path):
            path = item.get("path")
            if not isinstance(path, Path):
                continue
            state = inspect_repository(path)
            result.append(
                ManagedExtension(
                    name=item.get("name") or path.name,
                    path=path,
                    enabled=bool(item.get("status")),
                    is_git_repo=state.is_git_repo,
                    url=state.url,
                    branch=state.branch,
                    commit=state.commit,
                    commit_date=state.commit_date,
                    message=state.message,
                    error=state.error,
                    source_type="git" if state.is_git_repo else "unknown",
                )
            )
        return result

    return check_webui_updates(
        "invokeai",
        "InvokeAI",
        invokeai_path,
        extension_loader=load_extensions,
        kernel_package_name="invokeai",
        options=options,
    )


def get_invokeai_snapshot(
    invokeai_path: Path,
    include_packages: bool = True,
) -> WebUiSnapshot:
    """获取 InvokeAI 环境快照

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        include_packages (bool):
            是否记录当前 Python 环境已安装软件包

    Returns:
        WebUiSnapshot:
            InvokeAI 环境快照
    """
    return build_webui_snapshot(
        webui_name="InvokeAI",
        webui_type="invokeai",
        webui_path=invokeai_path,
        include_packages=include_packages,
        extensions=collect_git_extensions(
            invokeai_path / "nodes",
            enabled_resolver=lambda _name, path: (path / "__init__.py").is_file(),
        ),
    )


def get_invokeai_environment_info(
    invokeai_path: Path,
    include_packages: bool = True,
) -> WebUiEnvironmentInfo:
    """获取 InvokeAI 环境信息报告。

    Args:
        invokeai_path (Path): InvokeAI 根目录。
        include_packages (bool): 是否记录当前 Python 环境已安装软件包。

    Returns:
        WebUiEnvironmentInfo: 主机信息和 WebUI 快照组成的环境报告。
    """
    return build_webui_environment_info(get_invokeai_snapshot(invokeai_path, include_packages))
