"""WebUI environment snapshots.

The package facade preserves the former ``base_manager.snapshot`` public API;
implementation details are grouped by responsibility in sibling modules.
"""

from sd_webui_all_in_one.base_manager.snapshot.codec import (
    snapshot_from_dict as snapshot_from_dict,
)
from sd_webui_all_in_one.base_manager.snapshot.collection import (
    collect_python_info as collect_python_info,
    collect_system_info as collect_system_info,
    collect_installed_packages as collect_installed_packages,
    repository_state_to_snapshot as repository_state_to_snapshot,
    repository_dirty as repository_dirty,
    collect_repository_snapshot as collect_repository_snapshot,
    collect_git_extensions as collect_git_extensions,
    build_webui_snapshot as build_webui_snapshot,
)
from sd_webui_all_in_one.base_manager.snapshot.io import (
    load_snapshot as load_snapshot,
    comfyui_manager_snapshot_from_dict as comfyui_manager_snapshot_from_dict,
)
from sd_webui_all_in_one.base_manager.snapshot.models import (
    SNAPSHOT_SCHEMA_VERSION as SNAPSHOT_SCHEMA_VERSION,
    logger as logger,
    JsonPrimitive as JsonPrimitive,
    JsonValue as JsonValue,
    JsonObject as JsonObject,
    SourceType as SourceType,
    ExtensionSourceType as ExtensionSourceType,
    ExtensionEnabledResolver as ExtensionEnabledResolver,
    default_system_snapshot as default_system_snapshot,
    DirectUrlVcsInfo as DirectUrlVcsInfo,
    DirectUrlDirInfo as DirectUrlDirInfo,
    DirectUrlArchiveInfo as DirectUrlArchiveInfo,
    DirectUrlSnapshot as DirectUrlSnapshot,
    WheelSnapshot as WheelSnapshot,
    PackageSnapshot as PackageSnapshot,
    PythonSnapshot as PythonSnapshot,
    SystemSnapshot as SystemSnapshot,
    RepositorySnapshot as RepositorySnapshot,
    ExtensionSnapshot as ExtensionSnapshot,
    WebUiIdentitySnapshot as WebUiIdentitySnapshot,
    WebUiSnapshot as WebUiSnapshot,
    SnapshotSummary as SnapshotSummary,
    SavedSnapshot as SavedSnapshot,
    utc_now_iso as utc_now_iso,
    snapshot_to_dict as snapshot_to_dict,
    json_safe as json_safe,
)
from sd_webui_all_in_one.base_manager.snapshot.storage import (
    save_snapshot as save_snapshot,
    default_snapshot_output as default_snapshot_output,
    resolve_snapshot_output as resolve_snapshot_output,
    list_webui_snapshots as list_webui_snapshots,
    create_webui_snapshot as create_webui_snapshot,
    delete_snapshot as delete_snapshot,
)
