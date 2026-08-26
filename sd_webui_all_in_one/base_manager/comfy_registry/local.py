"""Implementation grouped from the former ``comfy_registry.py`` module."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    from sd_webui_all_in_one import toml_parser as tomllib

from sd_webui_all_in_one.base_manager.comfy_registry.models import ComfyRegistryLocalInfo


def read_comfy_registry_info(path: Path) -> ComfyRegistryLocalInfo | None:
    """读取本地 Registry 节点元数据。

    Args:
        path (Path):
            自定义节点目录。

    Returns:
        ComfyRegistryLocalInfo | None:
            本地 Registry 节点信息；不是有效 Registry 节点时返回 None。
    """
    pyproject_path = path / "pyproject.toml"
    tracking_path = path / ".tracking"
    if not pyproject_path.is_file() or not tracking_path.is_file():
        return None
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = data.get("project", {})
        if not isinstance(project, dict):
            return None
        raw_name = project.get("name")
        raw_version = project.get("version")
        if not isinstance(raw_name, str) or not raw_name.strip() or raw_version is None:
            return None
        urls = project.get("urls", {})
        repository = urls.get("Repository") if isinstance(urls, dict) else None
        return ComfyRegistryLocalInfo(
            registry_id=raw_name.strip().lower(),
            original_name=raw_name.strip(),
            version=str(raw_version),
            repository=repository if isinstance(repository, str) and repository.strip() else None,
        )
    except Exception:
        return None


def read_comfy_registry_nightly_id(path: Path) -> str | None:
    """读取 Git nightly 节点的 Registry ID 标记。

    Args:
        path (Path):
            Git 自定义节点目录。

    Returns:
        str | None:
            `.git/.cnr-id` 中记录的 Registry ID，不存在时返回 None。
    """
    marker = path / ".git" / ".cnr-id"
    if not marker.is_file():
        return None
    value = marker.read_text(encoding="utf-8").strip()
    return value or None
