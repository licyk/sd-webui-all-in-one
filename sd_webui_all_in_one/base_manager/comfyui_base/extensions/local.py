"""Implementation grouped from the former ``extensions.py`` module."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypedDict
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    apply_github_raw_file_mirror,
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
)
from sd_webui_all_in_one.base_manager.repository_inspector import inspect_repository
from sd_webui_all_in_one.base_manager.comfy_registry import (
    read_comfy_registry_info,
    read_comfy_registry_nightly_id,
    switch_comfy_registry_node_version,
)
from sd_webui_all_in_one.base_manager.snapshot import (
    ExtensionSnapshot,
    collect_repository_snapshot,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.file_manager import (
    move_files,
    remove_files,
)
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
)
from sd_webui_all_in_one.env_check import (
    ComfyUIConflictAnalysisResult,
    check_comfyui_component_dependencies,
)
from sd_webui_all_in_one.base_manager.comfyui_base.shared import logger

from sd_webui_all_in_one.base_manager.comfyui_base.extensions.catalog import COMFYUI_CUSTOM_NODE_LIST_PATH


def _normalize_custom_node_name(name: str) -> str:
    return name.removesuffix(".disabled").split("@", 1)[0]


def set_comfyui_custom_node_list_mirror(
    custom_github_mirror: str | list[str] | None = None,
) -> str | None:
    """配置 ComfyUI 自定义节点列表镜像源

    Args:
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源列表

    Returns:
        str | None:
            自定义节点列表镜像 URL, 未启用或无可用镜像时返回 None
    """
    return apply_github_raw_file_mirror(
        raw_file_path=COMFYUI_CUSTOM_NODE_LIST_PATH,
        custom_github_mirror=custom_github_mirror,
    )


class ComfyUiLocalExtensionInfo(TypedDict, total=False):
    """ComfyUI 本地扩展信息"""

    name: str
    """ComfyUI 扩展名称"""

    status: bool
    """当前 ComfyUI 扩展是否已经启用"""

    path: Path
    """ComfyUI 本地路径"""

    url: str | None
    """ComfyUI 扩展远程地址"""

    commit: str | None
    """ComfyUI 扩展的提交信息"""

    branch: str | None
    """ComfyUI 扩展的当前分支"""

    source_type: str
    """扩展安装来源"""

    registry_id: str | None
    """Comfy Registry 节点 ID"""

    registry_version: str | None
    """Comfy Registry 节点版本"""

    repository: str | None
    """Comfy Registry 记录的仓库地址"""

    error: str | None
    """扩展状态错误信息"""


ComfyUiLocalExtensionInfoList = list[ComfyUiLocalExtensionInfo]


def _comfyui_custom_nodes_path(comfyui_path: Path) -> Path:
    return comfyui_path / "custom_nodes"


def _disabled_custom_nodes_path(comfyui_path: Path) -> Path:
    return _comfyui_custom_nodes_path(comfyui_path) / ".disabled"


def _iter_comfyui_custom_node_paths(
    comfyui_path: Path,
    include_files: bool = False,
) -> list[tuple[str, Path, bool]]:
    custom_nodes_path = _comfyui_custom_nodes_path(comfyui_path)
    if not custom_nodes_path.is_dir():
        return []

    result: list[tuple[str, Path, bool]] = []
    for path in sorted(custom_nodes_path.iterdir(), key=lambda item: item.name.lower()):
        if path.name in {".disabled", "__pycache__"}:
            continue
        if path.is_dir():
            result.append((path.name, path, not path.name.endswith(".disabled")))
        elif include_files and path.is_file() and (path.suffix == ".py" or path.name.endswith(".py.disabled")):
            result.append((path.name, path, not path.name.endswith(".disabled")))

    disabled_root = custom_nodes_path / ".disabled"
    if disabled_root.is_dir():
        for path in sorted(disabled_root.iterdir(), key=lambda item: item.name.lower()):
            if path.name == "__pycache__":
                continue
            if path.is_dir() or (include_files and path.is_file() and (path.suffix == ".py" or path.name.endswith(".py.disabled"))):
                result.append((_normalize_custom_node_name(path.name), path, False))
    return result


def resolve_comfyui_custom_node_path(
    comfyui_path: Path,
    custom_node_name: str,
) -> tuple[Path, bool] | None:
    """查找 ComfyUI 自定义节点路径和启用状态。

    Args:
        comfyui_path (Path):
            ComfyUI 根目录。
        custom_node_name (str):
            自定义节点名称。

    Returns:
        tuple[Path, bool] | None:
            节点路径和启用状态；未找到时返回 None。
    """
    custom_nodes_path = _comfyui_custom_nodes_path(comfyui_path)
    name = custom_node_name.removesuffix(".disabled")
    candidates = [
        (custom_nodes_path / name, True),
        (custom_nodes_path / f"{name}.disabled", False),
        (_disabled_custom_nodes_path(comfyui_path) / name, False),
    ]
    disabled_root = _disabled_custom_nodes_path(comfyui_path)
    if disabled_root.is_dir():
        candidates.extend((path, False) for path in disabled_root.glob(f"{name}@*"))
    for path, enabled in candidates:
        if path.exists():
            return path, enabled
    return None


def get_comfyui_custom_node_enabled(comfyui_path: Path, custom_node_name: str) -> bool | None:
    """读取 ComfyUI 自定义节点启用状态。

    Args:
        comfyui_path (Path):
            ComfyUI 根目录。
        custom_node_name (str):
            自定义节点名称。

    Returns:
        bool | None:
            启用状态；未找到节点时返回 None。
    """
    resolved = resolve_comfyui_custom_node_path(comfyui_path, custom_node_name)
    if resolved is None:
        return None
    return resolved[1]


def list_comfyui_custom_nodes(
    comfyui_path: Path,
    include_files: bool = False,
) -> ComfyUiLocalExtensionInfoList:
    """获取 ComfyUI 本地扩展列表

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        include_files (bool):
            是否包含单文件自定义节点

    Returns:
        ComfyUiLocalExtensionInfoList:
            ComfyUI 本地扩展列表
    """

    try:
        from tqdm import tqdm
    except ImportError:
        from sd_webui_all_in_one.simple_tqdm import SimpleTqdm as tqdm

    info_list: ComfyUiLocalExtensionInfoList = []
    ext_dirs = _iter_comfyui_custom_node_paths(comfyui_path, include_files=include_files)

    def _process_extension(entry: tuple[str, Path, bool]) -> ComfyUiLocalExtensionInfo | None:
        name, path, status = entry
        if path.name == "__pycache__":
            return None

        repo_state = inspect_repository(path)
        source_type = "git" if repo_state.is_git_repo else ("file" if path.is_file() else "unknown")
        registry_id = None
        registry_version = None
        repository = None
        if repo_state.is_git_repo:
            registry_id = read_comfy_registry_nightly_id(path)
        else:
            cnr_info = read_comfy_registry_info(path)
            if cnr_info is not None:
                source_type = "comfy-registry"
                registry_id = cnr_info.registry_id
                registry_version = cnr_info.version
                repository = cnr_info.repository

        return {
            "name": name,
            "status": status,
            "path": path,
            "url": repo_state.url,
            "commit": repo_state.commit,
            "branch": repo_state.branch,
            "source_type": source_type,
            "registry_id": registry_id,
            "registry_version": registry_version,
            "repository": repository,
            "error": repo_state.error,
        }

    logger.info("获取 ComfyUI 扩展列表中")
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_ext = {executor.submit(_process_extension, ext): ext for ext in ext_dirs}
        for future in tqdm(as_completed(future_to_ext), total=len(ext_dirs), desc="获取 ComfyUI 扩展数据"):
            try:
                result = future.result(timeout=5)
                if result:
                    info_list.append(result)
            except Exception as e:
                ext_name = future_to_ext[future][0]
                logger.error("处理扩展 '%s' 时发生异常: %s", ext_name, e)

    logger.info("获取 ComfyUI 扩展列表中完成")
    return info_list


def set_comfyui_custom_node_status(
    comfyui_path: Path,
    custom_node_name: str,
    status: bool,
) -> None:
    """设置 ComfyUI 启用状态

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        custom_node_name (str):
            ComfyUI 扩展名称
        status (bool):
            设置扩展的启用状态
            - `True`: 启用
            - `False`: 禁用

    Raises:
        FileNotFoundError:
            ComfyUI 扩展未找到时
    """
    custom_node_name = custom_node_name.removesuffix(".disabled")
    custom_node_path = _comfyui_custom_nodes_path(comfyui_path)
    resolved = resolve_comfyui_custom_node_path(comfyui_path, custom_node_name)
    if resolved is None:
        raise FileNotFoundError(f"'{custom_node_name}' 扩展未找到, 请检查该扩展是否已安装")

    enable_path = custom_node_path / f"{custom_node_name}"
    disabled_path = custom_node_path / f"{custom_node_name}.disabled"
    dot_disabled_path = _disabled_custom_nodes_path(comfyui_path) / custom_node_name
    current_path, current_enabled = resolved
    if status:
        if not current_enabled and current_path.parent.name == ".disabled":
            move_files(current_path, enable_path)
        elif disabled_path.exists():
            move_files(disabled_path, enable_path)
        logger.info("启用 '%s' 扩展成功", custom_node_name)
    else:
        if current_enabled and enable_path.exists():
            if read_comfy_registry_info(enable_path) is not None:
                dot_disabled_path.parent.mkdir(parents=True, exist_ok=True)
                move_files(enable_path, dot_disabled_path)
            else:
                move_files(enable_path, disabled_path)
        logger.info("禁用 '%s' 扩展成功", custom_node_name)


def update_comfyui_custom_nodes(
    comfyui_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 ComfyUI 扩展

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源

    Raises:
        AggregateError:
            检查 ComfyUI 环境发生错误时
        FileNotFoundError:
            未找到 ComfyUI 扩展目录时
    """
    custom_nodes_path = comfyui_path / "custom_nodes"
    err: list[Exception] = []
    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)

    if not custom_nodes_path.is_dir():
        raise FileNotFoundError("未找到 ComfyUI 扩展目录")

    update_targets = [ext for ext in custom_nodes_path.iterdir() if ext.is_dir() and (ext / ".git").exists()]
    task_sum = len(update_targets)
    count = 0

    for ext in update_targets:
        count += 1
        logger.info("[%s/%s] 更新 '%s' 扩展中", count, task_sum, ext.name)
        try:
            git_warpper.update(ext)
        except Exception as e:
            err.append(e)
            logger.error("[%s/%s] 更新 '%s' 扩展时发生错误: %s", count, task_sum, ext.name, e)

    cnr_targets = [item for item in list_comfyui_custom_nodes(comfyui_path) if item.get("source_type") == "comfy-registry"]
    for item in cnr_targets:
        node_id = item.get("registry_id") or _normalize_custom_node_name(item["name"])
        try:
            logger.info("更新 Comfy Registry 节点 '%s' 中", node_id)
            switch_comfy_registry_node_version(comfyui_path, node_id=node_id, version=None, target_path=item["path"])
        except Exception as e:
            err.append(e)
            logger.error("更新 Comfy Registry 节点 '%s' 时发生错误: %s", node_id, e)

    if err:
        raise AggregateError("更新 ComfyUI 扩展时发生错误", err)

    logger.info("更新 ComfyUI 扩展完成")


def collect_comfyui_extensions(comfyui_path: Path) -> list[ExtensionSnapshot]:
    """采集 ComfyUI 自定义节点快照。

    Args:
        comfyui_path (Path):
            ComfyUI 根目录。

    Returns:
        list[ExtensionSnapshot]:
            自定义节点快照列表，包含 Git、Comfy Registry 和文件节点。
    """
    extensions: list[ExtensionSnapshot] = []
    for info in list_comfyui_custom_nodes(comfyui_path, include_files=True):
        name = info["name"]
        path = info["path"]
        source_type = info.get("source_type") or "unknown"
        if source_type == "git":
            repo = collect_repository_snapshot(path)
            extensions.append(
                ExtensionSnapshot(
                    name=name,
                    path=path,
                    enabled=info.get("status"),
                    is_git_repo=True,
                    url=repo.url,
                    branch=repo.branch,
                    commit=repo.commit,
                    commit_date=repo.commit_date,
                    message=repo.message,
                    error=repo.error,
                    dirty=repo.dirty,
                    source_type="git",
                    registry_id=info.get("registry_id"),
                )
            )
            continue

        extensions.append(
            ExtensionSnapshot(
                name=name,
                path=path,
                enabled=info.get("status"),
                is_git_repo=False,
                url=info.get("url") or info.get("repository"),
                branch=info.get("branch"),
                commit=info.get("commit"),
                error=info.get("error"),
                source_type="comfy-registry" if source_type == "comfy-registry" else ("file" if source_type == "file" else "unknown"),
                registry_id=info.get("registry_id"),
                registry_version=info.get("registry_version"),
                repository=info.get("repository"),
            )
        )
    return extensions


def check_comfyui_custom_node_dependencies(comfyui_path: Path) -> ComfyUIConflictAnalysisResult:
    """检查 ComfyUI 自定义节点依赖状态。

    Args:
        comfyui_path (Path): ComfyUI 根目录。

    Returns:
        ComfyUIConflictAnalysisResult: ComfyUI 自定义节点依赖检查结果。
    """
    return check_comfyui_component_dependencies(comfyui_path)


def uninstall_comfyui_custom_node(
    comfyui_path: Path,
    custom_node_name: str,
) -> None:
    """卸载 ComfyUI 扩展

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        custom_node_name (str):
            ComfyUI 扩展名称

    Raises:
        FileNotFoundError:
            要卸载的扩展未找到时
        RuntimeError:
            卸载扩展发生错误时
    """
    resolved = resolve_comfyui_custom_node_path(comfyui_path, custom_node_name)
    if resolved is None:
        raise FileNotFoundError(f"'{custom_node_name}' 扩展未安装")
    custom_node_path, _enabled = resolved

    try:
        logger.info("卸载 '%s' 扩展中", custom_node_name)
        remove_files(custom_node_path)
        logger.info("卸载 '%s' 扩展完成", custom_node_name)
    except Exception as e:
        logger.info("卸载 '%s' 扩展时发生错误: %s", custom_node_name, e)
        raise RuntimeError(f"卸载 '{custom_node_name}' 扩展时发生错误:{e}") from e
