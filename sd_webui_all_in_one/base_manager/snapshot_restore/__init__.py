"""WebUI environment snapshot restore facade."""

from sd_webui_all_in_one.base_manager.snapshot_restore.extensions import (
    PACKAGE_KERNEL_WEBUI_TYPES as PACKAGE_KERNEL_WEBUI_TYPES,
    normalize_extension_name as normalize_extension_name,
    restore_git_repository as restore_git_repository,
    restore_comfy_registry_extension as restore_comfy_registry_extension,
    restore_extensions as restore_extensions,
)
from sd_webui_all_in_one.base_manager.snapshot_restore.models import (
    logger as logger,
    PackageRestoreAction as PackageRestoreAction,
    GitRestoreAction as GitRestoreAction,
    RegistryRestoreAction as RegistryRestoreAction,
    ExtensionCleanupAction as ExtensionCleanupAction,
    DiffStatus as DiffStatus,
    RestoreOptionFlag as RestoreOptionFlag,
    RestoreBlockerCode as RestoreBlockerCode,
    RestoreBlockerScope as RestoreBlockerScope,
    PACKAGE_DIFF_STATUS as PACKAGE_DIFF_STATUS,
    GIT_DIFF_STATUS as GIT_DIFF_STATUS,
    REGISTRY_DIFF_STATUS as REGISTRY_DIFF_STATUS,
    CHANGED_DIFF_STATUSES as CHANGED_DIFF_STATUSES,
    DiffField as DiffField,
    RestoreDiff as RestoreDiff,
    RestoreDiffCounts as RestoreDiffCounts,
    RestoreDiffSummary as RestoreDiffSummary,
    RestoreBlocker as RestoreBlocker,
    SnapshotRestoreOptions as SnapshotRestoreOptions,
    ExtensionRestoreTools as ExtensionRestoreTools,
    PackageRestorePlanItem as PackageRestorePlanItem,
    GitRestorePlanItem as GitRestorePlanItem,
    ExtensionRestorePlanItem as ExtensionRestorePlanItem,
    SnapshotRestorePlan as SnapshotRestorePlan,
)
from sd_webui_all_in_one.base_manager.snapshot_restore.packages import (
    PYTORCH_PACKAGE_NAMES as PYTORCH_PACKAGE_NAMES,
    PROTECTED_PACKAGE_NAMES as PROTECTED_PACKAGE_NAMES,
    restore_python_packages as restore_python_packages,
)
from sd_webui_all_in_one.base_manager.snapshot_restore.service import (
    preview_webui_snapshot_restore as preview_webui_snapshot_restore,
    restore_webui_snapshot as restore_webui_snapshot,
)
