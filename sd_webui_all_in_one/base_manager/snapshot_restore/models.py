"""Restore options, plans, blockers, and structured diffs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME

logger = get_logger(name=LOGGER_NAME, level=LOGGER_LEVEL, color=LOGGER_COLOR)

PackageRestoreAction = Literal["install", "update", "skip_same_version", "skip_protected", "skip_missing_local_path", "uninstall", "install_pytorch_special"]
GitRestoreAction = Literal[
    "clone", "switch_commit", "skip_same_commit", "skip_non_git_snapshot", "skip_non_git_target", "skip_missing_url", "skip_missing_commit", "blocked_dirty", "blocked_missing_target"
]
RegistryRestoreAction = Literal["install_registry", "switch_registry_version", "skip_same_registry_version", "skip_registry_missing_id", "skip_registry_unavailable"]
ExtensionCleanupAction = Literal["keep", "uninstall"]
DiffStatus = Literal["added", "removed", "modified", "unchanged", "skipped", "blocked"]
RestoreOptionFlag = Literal["prune_packages", "prune_extensions", "force_git_reset"]
RestoreBlockerCode = Literal["webui_type_mismatch", "kernel_missing", "kernel_dirty", "extension_dirty"]
RestoreBlockerScope = Literal["snapshot", "kernel", "package", "extension"]

PACKAGE_DIFF_STATUS: dict[PackageRestoreAction, DiffStatus] = {
    "install": "added",
    "update": "modified",
    "uninstall": "removed",
    "skip_same_version": "unchanged",
    "skip_protected": "skipped",
    "skip_missing_local_path": "skipped",
}
GIT_DIFF_STATUS: dict[GitRestoreAction, DiffStatus] = {
    "clone": "added",
    "switch_commit": "modified",
    "skip_same_commit": "unchanged",
    "skip_non_git_snapshot": "skipped",
    "skip_non_git_target": "skipped",
    "skip_missing_url": "skipped",
    "skip_missing_commit": "skipped",
    "blocked_dirty": "blocked",
    "blocked_missing_target": "blocked",
}
REGISTRY_DIFF_STATUS: dict[RegistryRestoreAction, DiffStatus] = {
    "install_registry": "added",
    "switch_registry_version": "modified",
    "skip_same_registry_version": "unchanged",
    "skip_registry_missing_id": "skipped",
    "skip_registry_unavailable": "skipped",
}
CHANGED_DIFF_STATUSES: frozenset[DiffStatus] = frozenset({"added", "removed", "modified"})


@dataclass(slots=True)
class DiffField:
    """恢复项中单个字段的前后对比"""

    key: str
    current: str | None = None
    target: str | None = None


@dataclass(slots=True)
class RestoreDiff:
    """恢复项的结构化差异

    `status` 描述该项在恢复后相对当前环境的变化类别, `fields` 给出参与对比的
    具体字段, 供调用方以类似 git diff 的方式呈现。
    """

    status: DiffStatus
    fields: list[DiffField] = field(default_factory=list)


@dataclass(slots=True)
class RestoreDiffCounts:
    """按差异类别统计的恢复项数量"""

    added: int = 0
    removed: int = 0
    modified: int = 0
    unchanged: int = 0
    skipped: int = 0
    blocked: int = 0

    def count(self, status: DiffStatus) -> None:
        """累加一个差异类别的计数

        Args:
            status (DiffStatus):
                需要累加的差异类别。
        """
        setattr(self, status, getattr(self, status) + 1)

    @property
    def changed(self) -> int:
        """需要实际写入的恢复项数量。

        Returns:
            int: 恢复项数量
        """
        return self.added + self.removed + self.modified


@dataclass(slots=True)
class RestoreDiffSummary:
    """整个快照恢复计划的差异统计"""

    packages: RestoreDiffCounts = field(default_factory=RestoreDiffCounts)
    kernel: RestoreDiffCounts = field(default_factory=RestoreDiffCounts)
    extensions: RestoreDiffCounts = field(default_factory=RestoreDiffCounts)
    total_changes: int = 0


@dataclass(slots=True)
class RestoreBlocker:
    """阻止快照恢复的前置条件

    `required_options` 列出启用后可以解除该阻断的恢复选项开关; 为空表示该阻断
    无法通过开关绕过, 必须先修复环境或更换快照。
    """

    code: RestoreBlockerCode
    scope: RestoreBlockerScope
    message: str
    target: str | None = None
    required_options: list[RestoreOptionFlag] = field(default_factory=list)


@dataclass(slots=True)
class SnapshotRestoreOptions:
    """快照恢复选项"""

    prune_packages: bool = False
    prune_extensions: bool = False
    force_git_reset: bool = False
    use_uv: bool = True
    use_pypi_mirror: bool = True
    use_github_mirror: bool = False
    custom_github_mirror: str | list[str] | None = None


@dataclass(slots=True)
class ExtensionRestoreTools:
    """WebUI 扩展恢复工具"""

    directory_name: str
    set_status: Callable[[Path, str, bool], None]
    uninstall: Callable[[Path, str], None]
    strip_disabled_suffix: bool = False


@dataclass(slots=True)
class PackageRestorePlanItem:
    """Python 包恢复预检查项"""

    name: str
    normalized_name: str
    action: PackageRestoreAction
    reason: str
    target_version: str | None = None
    current_version: str | None = None
    source_type: str | None = None
    editable: bool = False
    local_path: Path | None = None
    pytorch_device_type: str | None = None
    diff: RestoreDiff = field(init=False)

    def __post_init__(self) -> None:
        self.diff = _package_diff(self)


@dataclass(slots=True)
class GitRestorePlanItem:
    """Git 仓库恢复预检查项"""

    name: str
    path: Path
    action: GitRestoreAction
    reason: str
    target_commit: str | None = None
    current_commit: str | None = None
    dirty: bool | None = None
    url: str | None = None
    diff: RestoreDiff = field(init=False)

    def __post_init__(self) -> None:
        self.diff = _git_diff(self)


@dataclass(slots=True)
class ExtensionRestorePlanItem:
    """WebUI 扩展恢复预检查项"""

    name: str
    normalized_name: str
    path: Path
    git: GitRestorePlanItem | None = None
    registry_action: RegistryRestoreAction | None = None
    cleanup_action: ExtensionCleanupAction = "keep"
    current_enabled: bool | None = None
    target_enabled: bool | None = None
    source_type: str | None = None
    registry_id: str | None = None
    current_version: str | None = None
    target_version: str | None = None
    reason: str = ""
    diff: RestoreDiff = field(init=False)

    def __post_init__(self) -> None:
        self.diff = _extension_diff(self)


@dataclass(slots=True)
class SnapshotRestorePlan:
    """WebUI 快照恢复预检查结果"""

    webui_type_match: bool
    expected_webui_type: str
    snapshot_webui_type: str
    snapshot_webui_name: str
    snapshot_path: Path
    webui_path: Path
    python_version_note: str | None = None
    package_changes: list[PackageRestorePlanItem] = field(default_factory=list)
    kernel_change: GitRestorePlanItem | None = None
    extension_changes: list[ExtensionRestorePlanItem] = field(default_factory=list)
    pytorch_device_type: str | None = None
    pytorch_mirror_url: str | None = None
    pytorch_mirror_kind: str | None = None
    warnings: list[str] = field(default_factory=list)
    blockers: list[RestoreBlocker] = field(default_factory=list)
    diff_summary: RestoreDiffSummary = field(default_factory=RestoreDiffSummary)
    required_options: list[RestoreOptionFlag] = field(default_factory=list)
    restorable: bool = False


def _finalize_plan(plan: SnapshotRestorePlan) -> SnapshotRestorePlan:
    """补全恢复计划的派生字段

    汇总差异统计, 收集可解除阻断的恢复选项开关, 并给出当前选项下是否可以恢复。

    Args:
        plan (SnapshotRestorePlan):
            已经填充完变更项和阻断项的恢复计划。

    Returns:
        SnapshotRestorePlan: 补全派生字段后的同一个恢复计划。
    """
    plan.diff_summary = _build_diff_summary(plan)
    required: list[RestoreOptionFlag] = []
    for blocker in plan.blockers:
        for flag in blocker.required_options:
            if flag not in required:
                required.append(flag)
    plan.required_options = required
    plan.restorable = plan.webui_type_match and not plan.blockers
    logger.debug(
        "恢复计划汇总: 包变更 %s, 内核变更 %s, 扩展变更 %s, 阻断 %s, 可恢复: %s",
        plan.diff_summary.packages.changed,
        plan.diff_summary.kernel.changed,
        plan.diff_summary.extensions.changed,
        len(plan.blockers),
        plan.restorable,
    )
    return plan


def _diff_bool(value: bool | None) -> str | None:
    return None if value is None else ("true" if value else "false")


def _package_diff(item: PackageRestorePlanItem) -> RestoreDiff:
    if item.action == "install_pytorch_special":
        # PyTorch 走特殊安装源, 同一个动作同时覆盖新装和升级两种情况。
        status: DiffStatus = "modified" if item.current_version is not None else "added"
    else:
        status = PACKAGE_DIFF_STATUS[item.action]
    return RestoreDiff(
        status=status,
        fields=[
            DiffField(
                key="version",
                current=item.current_version,
                target=item.target_version,
            )
        ],
    )


def _git_diff(item: GitRestorePlanItem) -> RestoreDiff:
    return RestoreDiff(
        status=GIT_DIFF_STATUS[item.action],
        fields=[
            DiffField(
                key="commit",
                current=item.current_commit,
                target=item.target_commit,
            )
        ],
    )


def _extension_diff(item: ExtensionRestorePlanItem) -> RestoreDiff:
    fields: list[DiffField] = []
    if item.cleanup_action == "uninstall":
        status: DiffStatus = "removed"
    elif item.registry_action is not None:
        status = REGISTRY_DIFF_STATUS[item.registry_action]
        fields.append(
            DiffField(
                key="registry_version",
                current=item.current_version,
                target=item.target_version,
            )
        )
    elif item.git is not None:
        status = item.git.diff.status
        fields.extend(item.git.diff.fields)
    else:
        status = "unchanged"

    if item.target_enabled is not None and item.current_enabled != item.target_enabled:
        fields.append(
            DiffField(
                key="enabled",
                current=_diff_bool(item.current_enabled),
                target=_diff_bool(item.target_enabled),
            )
        )
        if status == "unchanged":
            # 仓库内容一致但启用状态需要切换, 恢复仍会写入该扩展。
            status = "modified"
    return RestoreDiff(status=status, fields=fields)


def _build_diff_summary(plan: SnapshotRestorePlan) -> RestoreDiffSummary:
    summary = RestoreDiffSummary()
    for item in plan.package_changes:
        summary.packages.count(item.diff.status)
    if plan.kernel_change is not None:
        summary.kernel.count(plan.kernel_change.diff.status)
    for extension in plan.extension_changes:
        summary.extensions.count(extension.diff.status)
    summary.total_changes = summary.packages.changed + summary.kernel.changed + summary.extensions.changed
    return summary
