"""Snapshot file loading and foreign-format adapters."""

from __future__ import annotations

import json
from pathlib import Path

from sd_webui_all_in_one.base_manager.base import get_repo_name_from_url

from .codec import _require_object, snapshot_from_dict
from .collection import collect_python_info, collect_system_info
from .models import (
    SNAPSHOT_SCHEMA_VERSION,
    ExtensionSnapshot,
    JsonObject,
    JsonValue,
    PackageSnapshot,
    RepositorySnapshot,
    WebUiIdentitySnapshot,
    WebUiSnapshot,
    logger,
    utc_now_iso,
)


def load_snapshot(path: Path) -> WebUiSnapshot:
    """从 JSON 文件加载 WebUI 快照

    Args:
        path (Path):
            快照 JSON 文件路径。

    Returns:
        WebUiSnapshot: 从文件加载的 WebUI 环境快照。

    Raises:
        ValueError:
            当输入数据无效或快照内容不匹配时抛出。
    """
    logger.info("加载快照文件: %s", path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logger.error("快照文件不是有效 JSON: %s", path)
        raise ValueError(f"快照文件不是有效 JSON: {path}") from e
    snapshot_data = _require_object(data, "snapshot")
    logger.debug("快照文件顶层键数量: %s", len(snapshot_data))
    if _is_comfyui_manager_snapshot(snapshot_data):
        return comfyui_manager_snapshot_from_dict(snapshot_data, path)
    return snapshot_from_dict(snapshot_data)


def _is_comfyui_manager_snapshot(data: JsonObject) -> bool:
    return any(key in data for key in ("git_custom_nodes", "cnr_custom_nodes", "file_custom_nodes")) and "schema_version" not in data


def _package_snapshots_from_comfyui_manager_pips(value: JsonValue) -> list[PackageSnapshot]:
    if not isinstance(value, dict):
        return []
    packages: list[PackageSnapshot] = []
    for name, version in value.items():
        if not isinstance(name, str):
            logger.debug("跳过非字符串包名")
            continue
        if isinstance(version, str) and version:
            packages.append(PackageSnapshot(name=name, version=version))
            logger.debug("解析 pip 包: %s %s", name, version)
    result = sorted(packages, key=lambda item: item.name.lower())
    logger.debug("ComfyUI-Manager pip 包: %s 个", len(result))
    return result


def comfyui_manager_snapshot_from_dict(data: JsonObject, snapshot_path: Path | None = None) -> WebUiSnapshot:
    """将 ComfyUI-Manager 原生快照转换为本项目快照对象。

    Args:
        data (JsonObject):
            ComfyUI-Manager 原生快照数据。
        snapshot_path (Path | None):
            快照文件路径，用于推导快照来源目录。

    Returns:
        WebUiSnapshot:
            转换后的本项目快照对象。
    """
    extensions: list[ExtensionSnapshot] = []
    git_nodes = data.get("git_custom_nodes", {})
    if isinstance(git_nodes, dict):
        for url, raw_info in git_nodes.items():
            if not isinstance(url, str) or not url:
                continue
            info = raw_info if isinstance(raw_info, dict) else {}
            name = get_repo_name_from_url(url)
            commit = info.get("hash") if isinstance(info.get("hash"), str) else None
            disabled = info.get("disabled") if isinstance(info.get("disabled"), bool) else False
            logger.debug("解析 ComfyUI-Manager git 节点: %s (%s)", name, url)
            extensions.append(
                ExtensionSnapshot(
                    name=name,
                    path=Path("custom_nodes") / name,
                    enabled=not disabled,
                    is_git_repo=True,
                    url=url,
                    commit=commit,
                    source_type="git",
                )
            )
    git_node_count = len(extensions)
    logger.debug("ComfyUI-Manager git 节点数量: %s", git_node_count)

    cnr_nodes = data.get("cnr_custom_nodes", {})
    if isinstance(cnr_nodes, dict):
        for node_id, version in cnr_nodes.items():
            if not isinstance(node_id, str) or not node_id:
                continue
            version_text = str(version) if version is not None else None
            logger.debug("解析 ComfyUI-Manager CNR 节点: %s (%s)", node_id, version_text)
            extensions.append(
                ExtensionSnapshot(
                    name=node_id,
                    path=Path("custom_nodes") / node_id,
                    enabled=True,
                    is_git_repo=False,
                    source_type="comfy-registry",
                    registry_id=node_id,
                    registry_version=version_text,
                )
            )
    cnr_node_count = len(extensions) - git_node_count
    logger.debug("ComfyUI-Manager CNR 节点数量: %s", cnr_node_count)

    file_nodes = data.get("file_custom_nodes", [])
    if isinstance(file_nodes, list):
        for raw_item in file_nodes:
            if not isinstance(raw_item, dict):
                continue
            filename = raw_item.get("filename")
            if not isinstance(filename, str) or not filename:
                continue
            disabled = raw_item.get("disabled") if isinstance(raw_item.get("disabled"), bool) else filename.endswith(".disabled")
            logger.debug("解析 ComfyUI-Manager 文件节点: %s", filename)
            extensions.append(
                ExtensionSnapshot(
                    name=filename,
                    path=Path("custom_nodes") / filename,
                    enabled=not disabled,
                    is_git_repo=False,
                    source_type="file",
                )
            )
    file_node_count = len(extensions) - git_node_count - cnr_node_count
    logger.debug("ComfyUI-Manager 文件节点数量: %s", file_node_count)

    comfyui_commit = data.get("comfyui")
    kernel = None
    if isinstance(comfyui_commit, str) and comfyui_commit:
        logger.debug("ComfyUI-Manager 内核提交: %s", comfyui_commit)
        kernel = RepositorySnapshot(
            path=Path("."),
            name="ComfyUI",
            is_git_repo=True,
            commit=comfyui_commit,
        )

    packages = _package_snapshots_from_comfyui_manager_pips(data.get("pips"))
    logger.debug("ComfyUI-Manager pip 包数量: %s", len(packages))
    logger.info("转换 ComfyUI-Manager 快照完成: 扩展 %s 个, 包 %s 个", len(extensions), len(packages))
    return WebUiSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        created_at=utc_now_iso(),
        webui=WebUiIdentitySnapshot(name="ComfyUI", type="comfyui", path=snapshot_path.parent if snapshot_path else Path(".")),
        python=collect_python_info(),
        packages=packages,
        kernel=kernel,
        extensions=extensions,
        system=collect_system_info(),
    )
