"""Implementation grouped from the former ``sd_webui_base.py`` module."""

from __future__ import annotations

import json
from pathlib import Path
from sd_webui_all_in_one.base_manager.repository_inspector import inspect_repository
from sd_webui_all_in_one.base_manager.version_manager import (
    ManagedExtension,
    WebUiUpdateOptions,
    WebUiUpdateStatus,
    check_webui_updates,
)
from sd_webui_all_in_one.base_manager.snapshot import (
    WebUiSnapshot,
    build_webui_snapshot,
    collect_git_extensions,
)
from sd_webui_all_in_one.base_manager.environment_info import WebUiEnvironmentInfo, build_webui_environment_info

from .extensions import list_sd_webui_extensions


def check_sd_webui_updates(
    sd_webui_path: Path,
    options: WebUiUpdateOptions | None = None,
) -> WebUiUpdateStatus:
    """检查 Stable Diffusion WebUI 的内核、扩展和 PyTorch 更新。

    Args:
        sd_webui_path (Path): Stable Diffusion WebUI 根目录。
        options (WebUiUpdateOptions | None): 更新检查选项。

    Returns:
        WebUiUpdateStatus: 结构化更新检查结果。
    """

    def load_extensions() -> list[ManagedExtension]:
        result: list[ManagedExtension] = []
        for item in list_sd_webui_extensions(sd_webui_path):
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
        "sd_webui",
        "Stable Diffusion WebUI",
        sd_webui_path,
        extension_loader=load_extensions,
        options=options,
    )


def get_sd_webui_snapshot(
    sd_webui_path: Path,
    include_packages: bool = True,
) -> WebUiSnapshot:
    """获取 Stable Diffusion WebUI 环境快照

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        include_packages (bool):
            是否记录当前 Python 环境已安装软件包

    Returns:
        WebUiSnapshot:
            Stable Diffusion WebUI 环境快照
    """
    config_path = sd_webui_path / "config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except Exception:
        settings = {}

    disabled_extensions = set(settings.get("disabled_extensions", []))
    disable_all_extensions = settings.get("disable_all_extensions", "none")

    def _extension_enabled(name: str, _path: Path) -> bool:
        if disable_all_extensions == "all":
            return False
        if disable_all_extensions != "extra":
            return name not in disabled_extensions
        return True

    return build_webui_snapshot(
        webui_name="Stable Diffusion WebUI",
        webui_type="sd_webui",
        webui_path=sd_webui_path,
        include_packages=include_packages,
        extensions=collect_git_extensions(
            sd_webui_path / "extensions",
            enabled_resolver=_extension_enabled,
        ),
    )


def get_sd_webui_environment_info(
    sd_webui_path: Path,
    include_packages: bool = True,
) -> WebUiEnvironmentInfo:
    """获取 Stable Diffusion WebUI 环境信息报告。

    Args:
        sd_webui_path (Path): Stable Diffusion WebUI 根目录。
        include_packages (bool): 是否记录当前 Python 环境已安装软件包。

    Returns:
        WebUiEnvironmentInfo: 主机信息和 WebUI 快照组成的环境报告。
    """
    return build_webui_environment_info(get_sd_webui_snapshot(sd_webui_path, include_packages))
