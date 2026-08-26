"""Top-level snapshot restore orchestration."""

from __future__ import annotations

import os
import platform
from pathlib import Path

from sd_webui_all_in_one.base_manager.base import apply_git_base_config_and_github_mirror
from sd_webui_all_in_one.base_manager.snapshot import load_snapshot

from sd_webui_all_in_one.base_manager.snapshot_restore.extensions import (
    _build_extension_restore_plan,
    _build_git_restore_plan,
    _build_missing_kernel_plan,
    _ensure_kernel_target_exists,
    _requires_existing_kernel_target,
    _uses_package_kernel,
    restore_extensions,
    restore_git_repository,
)
from sd_webui_all_in_one.base_manager.snapshot_restore.models import RestoreBlocker, SnapshotRestoreOptions, SnapshotRestorePlan, _finalize_plan, logger
from sd_webui_all_in_one.base_manager.snapshot_restore.packages import _build_package_restore_plan, restore_python_packages


def preview_webui_snapshot_restore(
    snapshot_path: Path,
    webui_path: Path,
    expected_webui_type: str,
    options: SnapshotRestoreOptions | None = None,
) -> SnapshotRestorePlan:
    """预检查 WebUI 快照恢复将执行的变更

    Args:
        snapshot_path (Path):
            快照 JSON 文件路径。
        webui_path (Path):
            WebUI 根目录。
        expected_webui_type (str):
            期望的 WebUI 类型。
        options (SnapshotRestoreOptions | None):
            快照恢复选项。

    Returns:
        SnapshotRestorePlan: 快照恢复预检查计划。
    """
    if options is None:
        options = SnapshotRestoreOptions()

    logger.info("开始预检查快照恢复: %s -> %s", snapshot_path, webui_path)
    snapshot = load_snapshot(snapshot_path)
    webui_type_match = snapshot.webui.type == expected_webui_type
    logger.debug("快照 WebUI 类型: %s, 期望类型: %s", snapshot.webui.type, expected_webui_type)
    plan = SnapshotRestorePlan(
        webui_type_match=webui_type_match,
        expected_webui_type=expected_webui_type,
        snapshot_webui_type=snapshot.webui.type,
        snapshot_webui_name=snapshot.webui.name,
        snapshot_path=snapshot_path,
        webui_path=webui_path,
    )

    if not webui_type_match:
        plan.blockers.append(
            RestoreBlocker(
                code="webui_type_mismatch",
                scope="snapshot",
                message=f"快照 WebUI 类型不匹配: 期望 '{expected_webui_type}', 实际 '{snapshot.webui.type}'",
                target=snapshot.webui.type,
            )
        )
        return _finalize_plan(plan)

    current_python_version = platform.python_version()
    if snapshot.python.version != current_python_version:
        plan.python_version_note = f"快照 Python 版本为 {snapshot.python.version}, 当前 Python 版本为 {current_python_version}; 恢复时不会修改 Python 版本"

    if _requires_existing_kernel_target(snapshot) and not webui_path.exists():
        plan.kernel_change = _build_missing_kernel_plan(snapshot, webui_path)
        plan.blockers.append(
            RestoreBlocker(
                code="kernel_missing",
                scope="kernel",
                message=f"内核目录不存在: {webui_path}",
                target=webui_path.as_posix(),
            )
        )
        return _finalize_plan(plan)

    package_changes, dtype, mirror_url, mirror_kind = _build_package_restore_plan(snapshot, options, plan.warnings)
    plan.package_changes = package_changes
    plan.pytorch_device_type = dtype
    plan.pytorch_mirror_url = mirror_url
    plan.pytorch_mirror_kind = mirror_kind

    if snapshot.kernel is not None and not _uses_package_kernel(snapshot):
        plan.kernel_change = _build_git_restore_plan(snapshot.kernel, webui_path, options)
        if plan.kernel_change.action == "blocked_dirty":
            plan.blockers.append(
                RestoreBlocker(
                    code="kernel_dirty",
                    scope="kernel",
                    message="内核仓库存在未提交变更",
                    target=webui_path.as_posix(),
                    required_options=["force_git_reset"],
                )
            )

    plan.extension_changes = _build_extension_restore_plan(
        snapshot=snapshot,
        webui_path=webui_path,
        options=options,
        warnings=plan.warnings,
        blockers=plan.blockers,
    )
    return _finalize_plan(plan)


def restore_webui_snapshot(
    snapshot_path: Path,
    webui_path: Path,
    expected_webui_type: str,
    options: SnapshotRestoreOptions | None = None,
) -> None:
    """从快照文件恢复 WebUI 环境

    Args:
        snapshot_path (Path):
            快照 JSON 文件路径。
        webui_path (Path):
            WebUI 根目录。
        expected_webui_type (str):
            期望的 WebUI 类型。
        options (SnapshotRestoreOptions | None):
            快照恢复选项。

    Raises:
        ValueError:
            当输入数据无效或快照内容不匹配时抛出。
    """
    if options is None:
        options = SnapshotRestoreOptions()

    logger.info("开始恢复 WebUI 快照: %s -> %s", snapshot_path, webui_path)
    snapshot = load_snapshot(snapshot_path)
    if snapshot.webui.type != expected_webui_type:
        logger.error("快照 WebUI 类型不匹配: 期望 '%s', 实际 '%s'", expected_webui_type, snapshot.webui.type)
        raise ValueError(f"快照 WebUI 类型不匹配: 期望 '{expected_webui_type}', 实际 '{snapshot.webui.type}'")
    if _requires_existing_kernel_target(snapshot):
        _ensure_kernel_target_exists(webui_path)
    logger.debug("快照 WebUI 类型: %s, 名称: %s", snapshot.webui.type, snapshot.webui.name)

    git_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=options.use_github_mirror,
        custom_github_mirror=options.custom_github_mirror,
        origin_env=os.environ.copy(),
    )
    old_git_config = os.environ.get("GIT_CONFIG_GLOBAL")
    git_config = git_env.get("GIT_CONFIG_GLOBAL")
    if git_config is not None:
        os.environ["GIT_CONFIG_GLOBAL"] = git_config

    try:
        restore_python_packages(snapshot=snapshot, options=options)
        if snapshot.kernel is not None and not _uses_package_kernel(snapshot):
            restore_git_repository(repo=snapshot.kernel, target_path=webui_path, options=options)
        restore_extensions(snapshot=snapshot, webui_path=webui_path, options=options)
        logger.info("WebUI 快照恢复完成: %s", webui_path)
    finally:
        logger.debug("恢复 GIT_CONFIG_GLOBAL 环境变量")
        if old_git_config is None:
            os.environ.pop("GIT_CONFIG_GLOBAL", None)
        else:
            os.environ["GIT_CONFIG_GLOBAL"] = old_git_config
