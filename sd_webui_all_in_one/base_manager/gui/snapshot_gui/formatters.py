"""Implementation grouped from the former ``snapshot_gui.py`` module."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from sd_webui_all_in_one.base_manager.snapshot import WebUiSnapshot, load_snapshot
from sd_webui_all_in_one.base_manager.snapshot_restore import (
    SnapshotRestorePlan,
)
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger

from .models import SnapshotListItem

SnapshotFactory = Callable[[bool], WebUiSnapshot]

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def format_snapshot_timestamp(value: str) -> str:
    """将快照 ISO 时间戳转换为当前系统本地时间显示

    Args:
        value (str):
            快照 ISO 时间戳字符串。

    Returns:
        str: 适合界面展示的时间字符串。
    """
    try:
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        timestamp = datetime.fromisoformat(normalized)
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone()
        suffix = (timestamp.strftime("%Z") or timestamp.strftime("%z")) if timestamp.tzinfo is not None else ""
        return f"{timestamp:%Y-%m-%d %H:%M:%S}{f' {suffix}' if suffix else ''}"
    except (AttributeError, TypeError, ValueError, OSError):
        return value


def list_snapshot_files(snapshot_dir: Path) -> list[SnapshotListItem]:
    """读取目录中的有效快照文件列表

    Args:
        snapshot_dir (Path):
            快照文件目录。

    Returns:
        list[SnapshotListItem]: 快照文件列表。
    """
    if not snapshot_dir.is_dir():
        return []

    items: list[SnapshotListItem] = []
    for path in snapshot_dir.glob("*.json"):
        if not path.is_file():
            continue
        try:
            snapshot = load_snapshot(path)
        except (OSError, ValueError):
            continue
        items.append(
            SnapshotListItem(
                path=path,
                filename=path.name,
                created_at=snapshot.created_at,
                created_at_display=format_snapshot_timestamp(snapshot.created_at),
                webui_name=snapshot.webui.name,
                webui_type=snapshot.webui.type,
                package_count=len(snapshot.packages),
                extension_count=len(snapshot.extensions),
            )
        )
    return sorted(items, key=lambda item: (item.created_at, item.filename), reverse=True)


def format_snapshot_path(path: Path) -> str:
    """格式化快照 GUI 中展示的本地路径。

    Args:
        path (Path):
            需要展示的本地路径。

    Returns:
        str: POSIX 风格的路径字符串。
    """
    return path.as_posix()


def build_restore_blocking_guidance(plan: SnapshotRestorePlan) -> list[str]:
    """根据恢复阻断项生成处理建议

    Args:
        plan (SnapshotRestorePlan):
            快照恢复预检查结果。

    Returns:
        list[str]: 面向用户的恢复阻塞处理建议。
    """
    guidance: list[str] = []
    codes = {blocker.code for blocker in plan.blockers}
    if "webui_type_mismatch" in codes:
        guidance.append(f"请使用 {plan.snapshot_webui_type} 对应的快照管理器恢复该快照, 或选择 {plan.expected_webui_type} 类型的快照。跨 WebUI 类型恢复会被终止, 避免写错内核和扩展目录。")
    if "kernel_missing" in codes and plan.kernel_change is not None:
        guidance.append(
            f"请先通过 installer 准备对应的 WebUI kernel, 确认内核目录存在后再恢复: {format_snapshot_path(plan.kernel_change.path)}。该问题不能通过强制恢复开关绕过, 因为扩展恢复依赖 kernel 目录。"
        )

    dirty_targets: list[str] = []
    if plan.kernel_change is not None and plan.kernel_change.action == "blocked_dirty":
        dirty_targets.append(f"内核: {format_snapshot_path(plan.kernel_change.path)}")
    for item in plan.extension_changes:
        if item.git is not None and item.git.action == "blocked_dirty":
            dirty_targets.append(f"扩展 {item.name}: {format_snapshot_path(item.path)}")
    if dirty_targets:
        guidance.append(f"存在 Git 未提交变更: {'; '.join(dirty_targets)}。建议先提交、stash 或备份这些变更后再恢复。")
        guidance.append("如果确认要丢弃这些未提交变更, 可以勾选“允许覆盖 Git 未提交变更”后再次恢复。风险: 该开关会强制恢复上述 Git 仓库, 未提交的文件修改可能被永久覆盖。")

    if plan.blockers and not guidance:
        guidance.append("请根据阻断信息处理当前环境或更换快照文件后再次恢复。")
    return guidance


def format_restore_blocking_message(plan: SnapshotRestorePlan) -> str:
    """格式化无法恢复时展示给用户的提示

    Args:
        plan (SnapshotRestorePlan):
            快照恢复预检查结果。

    Returns:
        str: 恢复阻塞提示文本。
    """
    lines = [blocker.message for blocker in plan.blockers]
    guidance = build_restore_blocking_guidance(plan)
    if guidance:
        lines.extend(("", "处理建议:"))
        lines.extend(f"- {item}" for item in guidance)
    return "\n".join(lines)
