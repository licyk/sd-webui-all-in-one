"""Kernel and extension restore planning and execution."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TypeVar

from sd_webui_all_in_one import git_warpper
import sd_webui_all_in_one.base_manager.comfy_registry as comfy_registry
import sd_webui_all_in_one.base_manager.comfyui_base as comfyui_base
import sd_webui_all_in_one.base_manager.invokeai_base as invokeai_base
import sd_webui_all_in_one.base_manager.sd_webui_base as sd_webui_base
from sd_webui_all_in_one.base_manager.base import DEFAULT_GIT_UPDATE_WORKERS, MIRROR_GIT_UPDATE_WORKERS, clone_repo
from sd_webui_all_in_one.base_manager.repository_inspector import probe_repository, repository_has_commit
from sd_webui_all_in_one.base_manager.snapshot import ExtensionSnapshot, RepositorySnapshot, WebUiSnapshot
from sd_webui_all_in_one.base_manager.version_manager import fetch_repository
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.file_manager import is_folder_empty

from sd_webui_all_in_one.base_manager.snapshot_restore.models import (
    ExtensionRestorePlanItem,
    ExtensionRestoreTools,
    GitRestorePlanItem,
    RegistryRestoreAction,
    RestoreBlocker,
    SnapshotRestoreOptions,
    logger,
)
from sd_webui_all_in_one.base_manager.snapshot_restore.packages import _pypi_env

PACKAGE_KERNEL_WEBUI_TYPES = {"invokeai"}

_T = TypeVar("_T")
_R = TypeVar("_R")


def _map_in_threads(func: Callable[[_T], _R], items: Sequence[_T], max_workers: int = DEFAULT_GIT_UPDATE_WORKERS) -> list[_R]:
    """并行执行任务并保持结果顺序

    Args:
        func (Callable[[_T], _R]):
            对每个条目执行的任务。
        items (Sequence[_T]):
            待处理条目。
        max_workers (int):
            最大并行线程数。

    Returns:
        list[_R]: 与输入顺序一致的结果列表。
    """
    if len(items) <= 1 or max_workers <= 1:
        return [func(item) for item in items]
    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as executor:
        return list(executor.map(func, items))


def normalize_extension_name(
    name: str,
    strip_disabled_suffix: bool = False,
) -> str:
    """规范化扩展名用于快照对比

    Args:
        name (str):
            待规范化的名称。
        strip_disabled_suffix (bool):
            是否移除禁用扩展使用的后缀。

    Returns:
        str: 规范化后的扩展名。
    """
    normalized = name.casefold()
    if strip_disabled_suffix:
        normalized = normalized.removesuffix(".disabled")
    return normalized


def _extension_tools(webui_type: str) -> ExtensionRestoreTools | None:
    if webui_type == "sd_webui":
        return ExtensionRestoreTools(
            directory_name="extensions",
            set_status=sd_webui_base.set_sd_webui_extensions_status,
            uninstall=sd_webui_base.uninstall_sd_webui_extension,
        )
    if webui_type == "comfyui":
        return ExtensionRestoreTools(
            directory_name="custom_nodes",
            set_status=comfyui_base.set_comfyui_custom_node_status,
            uninstall=comfyui_base.uninstall_comfyui_custom_node,
            strip_disabled_suffix=True,
        )
    if webui_type == "invokeai":
        return ExtensionRestoreTools(
            directory_name="nodes",
            set_status=invokeai_base.set_invokeai_custom_nodes_status,
            uninstall=invokeai_base.uninstall_invokeai_custom_node,
        )
    return None


def _repo_target_name(repo: RepositorySnapshot | ExtensionSnapshot) -> str:
    return getattr(repo, "name", None) or repo.path.name


def _same_commit(current_commit: str | None, target_commit: str | None) -> bool:
    if current_commit is None or target_commit is None:
        return False
    return current_commit.startswith(target_commit) or target_commit.startswith(current_commit)


def _build_git_restore_plan(
    repo: RepositorySnapshot | ExtensionSnapshot,
    target_path: Path,
    options: SnapshotRestoreOptions,
) -> GitRestorePlanItem:
    name = _repo_target_name(repo)
    logger.debug("构建 Git 恢复计划: %s (目标: %s)", name, target_path)
    if not repo.is_git_repo:
        return GitRestorePlanItem(
            name=name,
            path=target_path,
            action="skip_non_git_snapshot",
            reason="快照目标不是 Git 仓库",
            target_commit=repo.commit,
            url=repo.url,
        )

    if repo.commit is None:
        return GitRestorePlanItem(
            name=name,
            path=target_path,
            action="skip_missing_commit",
            reason="快照目标缺少 commit",
            url=repo.url,
        )

    # 单次 Git 调用同时取得仓库有效性、当前 commit 和工作区变更状态
    probe = probe_repository(target_path) if target_path.exists() else None
    if probe is not None and not probe.is_git_repo:
        if target_path.is_dir() and is_folder_empty(target_path) and repo.url:
            return GitRestorePlanItem(
                name=name,
                path=target_path,
                action="clone",
                reason="目标路径为空目录, 将 clone 后恢复到快照 commit",
                target_commit=repo.commit,
                url=repo.url,
            )
        return GitRestorePlanItem(
            name=name,
            path=target_path,
            action="skip_non_git_target",
            reason="目标路径已存在且不是 Git 仓库",
            target_commit=repo.commit,
            url=repo.url,
        )

    if probe is None:
        if repo.url is None:
            return GitRestorePlanItem(
                name=name,
                path=target_path,
                action="skip_missing_url",
                reason="目标路径不存在且快照缺少远程地址",
                target_commit=repo.commit,
            )
        return GitRestorePlanItem(
            name=name,
            path=target_path,
            action="clone",
            reason="目标路径不存在, 将 clone 后恢复到快照 commit",
            target_commit=repo.commit,
            url=repo.url,
        )

    dirty = probe.dirty
    current_commit = probe.commit
    # dirty 为 None 表示无法确认工作区状态, 按存在未提交变更处理, 避免强制重置时丢失改动
    if dirty is not False and not options.force_git_reset:
        return GitRestorePlanItem(
            name=name,
            path=target_path,
            action="blocked_dirty",
            reason="目标仓库存在未提交变更, 需要先处理或启用强制恢复" if dirty else "无法检查目标仓库是否存在未提交变更, 需要先处理或启用强制恢复",
            target_commit=repo.commit,
            current_commit=current_commit,
            dirty=dirty,
            url=repo.url,
        )

    if _same_commit(current_commit, repo.commit):
        return GitRestorePlanItem(
            name=name,
            path=target_path,
            action="skip_same_commit",
            reason="当前 commit 与快照一致",
            target_commit=repo.commit,
            current_commit=current_commit,
            dirty=dirty,
            url=repo.url,
        )

    reason = "将切换到快照 commit"
    if dirty and options.force_git_reset:
        reason = "启用了强制恢复, 将覆盖未提交变更并切换到快照 commit"
    return GitRestorePlanItem(
        name=name,
        path=target_path,
        action="switch_commit",
        reason=reason,
        target_commit=repo.commit,
        current_commit=current_commit,
        dirty=dirty,
        url=repo.url,
    )


def _build_missing_kernel_plan(snapshot: WebUiSnapshot, webui_path: Path) -> GitRestorePlanItem:
    kernel = snapshot.kernel
    logger.warning("内核目录不存在, 生成阻断计划: %s", webui_path)
    return GitRestorePlanItem(
        name=_repo_target_name(kernel) if kernel is not None else webui_path.name,
        path=webui_path,
        action="blocked_missing_target",
        reason="内核目录不存在, 请先通过 installer 准备 WebUI kernel 后再恢复快照",
        target_commit=kernel.commit if kernel is not None else None,
        url=kernel.url if kernel is not None else None,
    )


def _ensure_kernel_target_exists(webui_path: Path) -> None:
    logger.debug("检查内核目录: %s", webui_path)
    if not webui_path.exists():
        raise FileNotFoundError(f"内核目录不存在, 请先通过 installer 准备 WebUI kernel 后再恢复快照: {webui_path}")


def _uses_package_kernel(snapshot: WebUiSnapshot) -> bool:
    return snapshot.webui.type in PACKAGE_KERNEL_WEBUI_TYPES


def _requires_existing_kernel_target(snapshot: WebUiSnapshot) -> bool:
    return not _uses_package_kernel(snapshot)


def _sd_webui_extension_enabled(webui_path: Path, name: str) -> bool | None:
    config_path = webui_path / "config.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        logger.warning("读取扩展启用配置失败: %s: %s", config_path, e)
        return None
    if not isinstance(data, dict):
        logger.warning("扩展启用配置内容不是 JSON 对象: %s", config_path)
        return None

    disable_all_extensions = data.get("disable_all_extensions", "none")
    if disable_all_extensions == "all":
        return False
    if disable_all_extensions == "extra":
        return True
    disabled_extensions = data.get("disabled_extensions", [])
    if not isinstance(disabled_extensions, list):
        return None
    return name not in disabled_extensions


def _extension_current_enabled(
    webui_path: Path,
    webui_type: str,
    extension_name: str,
    tools: ExtensionRestoreTools,
) -> bool | None:
    target_path = webui_path / tools.directory_name / extension_name
    if webui_type == "sd_webui":
        return _sd_webui_extension_enabled(webui_path, extension_name)
    if webui_type == "comfyui":
        enabled = comfyui_base.get_comfyui_custom_node_enabled(webui_path, extension_name)
        return enabled if enabled is not None else not extension_name.endswith(".disabled")
    if webui_type == "invokeai":
        return (target_path / "__init__.py").is_file()
    return None


def _extension_source_type(extension: ExtensionSnapshot) -> str:
    source_type = getattr(extension, "source_type", None)
    if source_type:
        return source_type
    return "git" if extension.is_git_repo else "unknown"


def _build_registry_restore_plan(
    extension: ExtensionSnapshot,
    webui_path: Path,
    target_path: Path,
) -> tuple[RegistryRestoreAction, str, str | None, str | None, str | None]:
    registry_id = extension.registry_id or extension.name.removesuffix(".disabled")
    if not registry_id:
        return "skip_registry_missing_id", "快照缺少 Comfy Registry 节点 ID", None, extension.registry_version, None
    logger.debug("构建 Registry 恢复计划: %s (目标版本 %s)", registry_id, extension.registry_version)

    resolved = comfyui_base.resolve_comfyui_custom_node_path(webui_path, extension.name) or comfyui_base.resolve_comfyui_custom_node_path(webui_path, registry_id)
    current_version = None
    if resolved is not None:
        current_info = comfy_registry.read_comfy_registry_info(resolved[0])
        if current_info is not None:
            current_version = current_info.version
    target_version = extension.registry_version
    del target_path
    if resolved is None:
        return "install_registry", "安装 Comfy Registry 节点", current_version, target_version, registry_id
    if target_version and current_version == target_version:
        return "skip_same_registry_version", "Registry 节点版本已一致", current_version, target_version, registry_id
    return "switch_registry_version", "切换 Comfy Registry 节点版本", current_version, target_version, registry_id


def _build_extension_restore_plan(
    snapshot: WebUiSnapshot,
    webui_path: Path,
    options: SnapshotRestoreOptions,
    warnings: list[str],
    blockers: list[RestoreBlocker],
) -> list[ExtensionRestorePlanItem]:
    tools = _extension_tools(snapshot.webui.type)
    if tools is None:
        if snapshot.extensions:
            warnings.append(f"当前 WebUI 类型不支持扩展恢复: {snapshot.webui.type}")
        return []

    items: list[ExtensionRestorePlanItem] = []
    target_names = _target_extension_names(snapshot, tools)
    git_extensions = [extension for extension in snapshot.extensions if _extension_source_type(extension) != "comfy-registry"]
    # 仓库状态检查只读且互不影响, 并行执行以缩短扩展较多时的预检查耗时
    git_plans = _map_in_threads(
        lambda extension: _build_git_restore_plan(extension, _extension_target_path(webui_path, extension, tools), options),
        git_extensions,
    )
    git_plan_by_extension = {id(extension): git_plan for extension, git_plan in zip(git_extensions, git_plans)}
    for extension in snapshot.extensions:
        normalized = normalize_extension_name(extension.name, strip_disabled_suffix=tools.strip_disabled_suffix)
        target_path = _extension_target_path(webui_path, extension, tools)
        source_type = _extension_source_type(extension)
        logger.debug("检查扩展: %s (来源: %s)", extension.name, source_type)
        git_plan = git_plan_by_extension.get(id(extension))
        registry_action = None
        current_version = None
        target_version = None
        registry_id = extension.registry_id
        reason = git_plan.reason if git_plan is not None else ""
        if source_type == "comfy-registry":
            registry_action, reason, current_version, target_version, registry_id = _build_registry_restore_plan(extension, webui_path, target_path)
        current_enabled = _extension_current_enabled(webui_path, snapshot.webui.type, extension.name, tools)
        item = ExtensionRestorePlanItem(
            name=extension.name,
            normalized_name=normalized,
            path=target_path,
            git=git_plan,
            registry_action=registry_action,
            current_enabled=current_enabled,
            target_enabled=extension.enabled,
            source_type=source_type,
            registry_id=registry_id,
            current_version=current_version,
            target_version=target_version,
            reason=reason,
        )
        items.append(item)
        if git_plan is not None and git_plan.action == "blocked_dirty":
            blockers.append(
                RestoreBlocker(
                    code="extension_dirty",
                    scope="extension",
                    message=f"扩展 '{extension.name}' 存在未提交变更",
                    target=extension.name,
                    required_options=["force_git_reset"],
                )
            )

    if options.prune_extensions:
        extension_root = webui_path / tools.directory_name
        if extension_root.is_dir():
            for path in sorted(extension_root.iterdir(), key=lambda item: item.name.casefold()):
                if not path.is_dir() or path.name in {"__pycache__", ".disabled"}:
                    continue
                normalized = normalize_extension_name(path.name, strip_disabled_suffix=tools.strip_disabled_suffix)
                if normalized in target_names:
                    continue
                items.append(
                    ExtensionRestorePlanItem(
                        name=path.name,
                        normalized_name=normalized,
                        path=path,
                        cleanup_action="uninstall",
                        current_enabled=_extension_current_enabled(webui_path, snapshot.webui.type, path.name, tools),
                        reason="启用了清理快照外扩展",
                    )
                )
    return items


def _ensure_git_target(repo: RepositorySnapshot | ExtensionSnapshot, target_path: Path) -> bool:
    if not repo.is_git_repo:
        logger.info("快照目标不是 Git 仓库, 跳过: %s", target_path)
        return False

    if target_path.exists() and not git_warpper.is_git_repo(target_path):
        if target_path.is_dir() and is_folder_empty(target_path) and repo.url:
            clone_repo(repo.url, target_path)
        else:
            logger.warning("目标路径已存在且不是 Git 仓库, 跳过: %s", target_path)
            return False
    elif not target_path.exists():
        if not repo.url:
            logger.warning("目标路径不存在且快照缺少远程地址, 跳过: %s", target_path)
            return False
        clone_repo(repo.url, target_path)

    if not git_warpper.is_git_repo(target_path):
        logger.warning("目标路径不是 Git 仓库, 跳过: %s", target_path)
        return False
    return True


def restore_git_repository(
    repo: RepositorySnapshot | ExtensionSnapshot,
    target_path: Path,
    options: SnapshotRestoreOptions,
) -> bool:
    """恢复 Git 仓库到快照提交

    Args:
        repo (RepositorySnapshot | ExtensionSnapshot):
            快照中的 Git 仓库或扩展记录。
        target_path (Path):
            恢复目标路径。
        options (SnapshotRestoreOptions):
            快照恢复选项。

    Returns:
        bool: 仓库是否已恢复或可视为存在。

    Raises:
        RuntimeError:
            当恢复或 GUI 启动无法安全继续时抛出。
    """
    if repo.commit is None:
        logger.info("快照目标缺少 commit, 跳过: %s", target_path)
        return target_path.is_dir()
    if not repo.is_git_repo:
        logger.info("快照目标不是 Git 仓库, 跳过: %s", target_path)
        return False

    probe = probe_repository(target_path) if target_path.exists() else None
    if probe is None or not probe.is_git_repo:
        if not _ensure_git_target(repo, target_path):
            return False
        probe = probe_repository(target_path)
    logger.debug("恢复 Git 仓库: %s (目标: %s, commit: %s)", _repo_target_name(repo), target_path, repo.commit)

    dirty = probe.dirty
    if dirty is None and not options.force_git_reset:
        # 无法确认工作区状态时不能假设没有改动, 否则后续重置可能丢失用户的未提交变更
        logger.error("无法检查目标仓库是否存在未提交变更, 中止恢复: %s", target_path)
        raise RuntimeError(f"无法检查 '{target_path}' 是否存在未提交变更, 请先处理或使用强制恢复")
    if dirty and not options.force_git_reset:
        logger.error("目标仓库存在未提交变更, 中止恢复: %s", target_path)
        raise RuntimeError(f"'{target_path}' 存在未提交变更, 请先处理或使用强制恢复")

    if dirty is False and _same_commit(probe.commit, repo.commit):
        logger.info("仓库 '%s' 已位于快照 commit %s, 无需切换", target_path, repo.commit)
        return True

    # 快照 commit 已在本地对象库时无需访问远程, 避免每个仓库都产生一次网络往返
    if not repository_has_commit(target_path, repo.commit):
        try:
            fetch_repository(target_path)
        except (RuntimeError, OSError) as e:
            logger.warning("拉取 '%s' 远程引用失败, 将尝试使用本地提交恢复: %s", target_path, e)

    git_warpper.switch_commit(target_path, repo.commit)
    logger.info("已切换仓库 '%s' 到快照 commit %s", target_path, repo.commit)
    return True


def restore_comfy_registry_extension(
    extension: ExtensionSnapshot,
    webui_path: Path,
    options: SnapshotRestoreOptions,
) -> bool:
    """恢复 Comfy Registry 扩展。

    Args:
        extension (ExtensionSnapshot):
            快照中的 Registry 扩展记录。
        webui_path (Path):
            ComfyUI 根目录。
        options (SnapshotRestoreOptions):
            快照恢复选项。

    Returns:
        bool:
            Registry 扩展是否已恢复或可视为存在。
    """
    registry_id = extension.registry_id or extension.name.removesuffix(".disabled")
    if not registry_id:
        logger.warning("快照扩展缺少 Comfy Registry 节点 ID, 跳过: %s", extension.name)
        return False
    logger.debug("恢复 Comfy Registry 节点: %s (版本 %s)", registry_id, extension.registry_version)
    resolved = comfyui_base.resolve_comfyui_custom_node_path(webui_path, extension.name) or comfyui_base.resolve_comfyui_custom_node_path(webui_path, registry_id)
    target_path = resolved[0] if resolved is not None else webui_path / "custom_nodes" / registry_id
    custom_env = _pypi_env(use_pypi_mirror=options.use_pypi_mirror)
    try:
        comfy_registry.switch_comfy_registry_node_version(
            comfyui_path=webui_path,
            node_id=registry_id,
            version=extension.registry_version,
            target_path=target_path if target_path.exists() else None,
            use_uv=options.use_uv,
            custom_env=custom_env,
        )
    except comfy_registry.ComfyRegistryInstallUnavailableError as e:
        logger.warning("快照中的 Comfy Registry 节点不可安装，已跳过: %s", e)
        return False
    logger.info("Comfy Registry 节点已恢复: %s", registry_id)
    return True


def ensure_git_restore_targets_clean(snapshot: WebUiSnapshot, webui_path: Path, options: SnapshotRestoreOptions) -> None:
    """在修改环境前检查所有待恢复 Git 仓库的工作区状态

    任意仓库存在未提交变更时提前终止, 避免恢复进行到一半才因某个仓库被阻断。

    Args:
        snapshot (WebUiSnapshot):
            WebUI 环境快照。
        webui_path (Path):
            WebUI 根目录。
        options (SnapshotRestoreOptions):
            快照恢复选项。

    Raises:
        RuntimeError:
            存在未提交变更或无法确认工作区状态的仓库, 且未启用强制恢复时抛出。
    """
    if options.force_git_reset:
        return

    targets: list[Path] = []
    kernel = snapshot.kernel
    if kernel is not None and not _uses_package_kernel(snapshot) and kernel.is_git_repo and kernel.commit is not None:
        targets.append(webui_path)
    tools = _extension_tools(snapshot.webui.type)
    if tools is not None:
        for extension in snapshot.extensions:
            if _extension_source_type(extension) == "comfy-registry" or not extension.is_git_repo or extension.commit is None:
                continue
            targets.append(_extension_target_path(webui_path, extension, tools))

    existing_targets = [path for path in targets if path.exists()]
    probes = _map_in_threads(probe_repository, existing_targets)
    blocked = [probe.path for probe in probes if probe.is_git_repo and probe.dirty is not False]
    if blocked:
        names = ", ".join(f"'{path}'" for path in blocked)
        logger.error("目标仓库存在未提交变更或无法确认工作区状态, 中止恢复: %s", names)
        raise RuntimeError(f"以下仓库存在未提交变更或无法确认工作区状态, 请先处理或使用强制恢复: {names}")


def _extension_target_path(webui_path: Path, extension: ExtensionSnapshot, tools: ExtensionRestoreTools) -> Path:
    return webui_path / tools.directory_name / extension.name


def _target_extension_names(snapshot: WebUiSnapshot, tools: ExtensionRestoreTools) -> set[str]:
    names = {normalize_extension_name(extension.name, strip_disabled_suffix=tools.strip_disabled_suffix) for extension in snapshot.extensions}
    for extension in snapshot.extensions:
        if extension.registry_id:
            names.add(normalize_extension_name(extension.registry_id, strip_disabled_suffix=tools.strip_disabled_suffix))
    return names


def _prune_extensions(webui_path: Path, snapshot: WebUiSnapshot, tools: ExtensionRestoreTools) -> None:
    extension_root = webui_path / tools.directory_name
    if not extension_root.is_dir():
        logger.debug("扩展目录不存在, 跳过清理: %s", extension_root)
        return

    target_names = _target_extension_names(snapshot, tools)
    for path in sorted(extension_root.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_dir() or path.name in {"__pycache__", ".disabled"}:
            continue
        normalized = normalize_extension_name(path.name, strip_disabled_suffix=tools.strip_disabled_suffix)
        if normalized in target_names:
            continue
        logger.info("卸载快照外扩展: %s", path.name)
        tools.uninstall(webui_path, path.name)


def restore_extensions(snapshot: WebUiSnapshot, webui_path: Path, options: SnapshotRestoreOptions) -> None:
    """恢复 WebUI 扩展

    Args:
        snapshot (WebUiSnapshot):
            WebUI 环境快照。
        webui_path (Path):
            WebUI 根目录。
        options (SnapshotRestoreOptions):
            快照恢复选项。

    Raises:
        AggregateError:
            多个扩展恢复失败时抛出; 仅一个扩展失败时直接抛出其原始异常。
    """
    tools = _extension_tools(snapshot.webui.type)
    if tools is None:
        if snapshot.extensions:
            logger.warning("当前 WebUI 类型不支持扩展恢复: %s", snapshot.webui.type)
        return

    logger.info("开始恢复扩展, 共 %s 个", len(snapshot.extensions))
    registry_extensions: list[ExtensionSnapshot] = []
    git_extensions: list[ExtensionSnapshot] = []
    for extension in snapshot.extensions:
        source_type = _extension_source_type(extension)
        logger.debug("恢复扩展: %s (来源: %s)", extension.name, source_type)
        if source_type == "comfy-registry" and snapshot.webui.type == "comfyui":
            registry_extensions.append(extension)
        else:
            git_extensions.append(extension)

    errors: list[Exception] = []

    def _restore_git_extension(extension: ExtensionSnapshot) -> bool:
        try:
            return restore_git_repository(
                repo=extension,
                target_path=_extension_target_path(webui_path, extension, tools),
                options=options,
            )
        except Exception as e:
            logger.error("恢复扩展 '%s' 失败: %s", extension.name, e)
            errors.append(e)
            return False

    # Git 扩展互相独立, 并行恢复; 镜像源下降低并行数以避免限流
    workers = MIRROR_GIT_UPDATE_WORKERS if options.use_github_mirror else DEFAULT_GIT_UPDATE_WORKERS
    restored_ids = {id(extension) for extension, restored in zip(git_extensions, _map_in_threads(_restore_git_extension, git_extensions, workers)) if restored}

    # Registry 节点会安装 Python 依赖, 保持串行避免并发修改同一环境
    for extension in registry_extensions:
        try:
            if restore_comfy_registry_extension(extension=extension, webui_path=webui_path, options=options):
                restored_ids.add(id(extension))
        except Exception as e:
            logger.error("恢复扩展 '%s' 失败: %s", extension.name, e)
            errors.append(e)

    for extension in snapshot.extensions:
        if id(extension) in restored_ids and extension.enabled is not None:
            tools.set_status(webui_path, extension.name, extension.enabled)
            logger.debug("设置扩展启用状态: %s -> %s", extension.name, extension.enabled)

    if len(errors) == 1:
        raise errors[0]
    if errors:
        raise AggregateError("恢复扩展时发生错误", errors)

    if options.prune_extensions:
        _prune_extensions(webui_path=webui_path, snapshot=snapshot, tools=tools)
    logger.info("扩展恢复完成")
