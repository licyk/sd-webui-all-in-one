"""通用版本管理服务。"""

# ruff: noqa: F401

from sd_webui_all_in_one.base_manager.version_manager.checks import check_extension_updates, check_package_update, check_webui_updates
from sd_webui_all_in_one.base_manager.version_manager.extensions import ExtensionManager
from sd_webui_all_in_one.base_manager.version_manager.indexes import (
    fetch_comfyui_custom_node_index,
    fetch_extension_index,
    fetch_pypi_versions,
    filter_extension_index,
    parse_comfyui_custom_node_index,
    parse_extension_index,
)
from sd_webui_all_in_one.base_manager.version_manager.models import (
    DEFAULT_EXTENSION_INDEX_URL,
    BranchInfo,
    CommitInfo,
    ExtensionIndexItem,
    ExtensionSourceType,
    ExtensionUpdateStatus,
    ManagedExtension,
    PackageUpdateStatus,
    PackageVersionInfo,
    RepositoryUpdateStatus,
    WebUiUpdateOptions,
    WebUiUpdateStatus,
    WebUiUpdateSummary,
)
from sd_webui_all_in_one.base_manager.version_manager.repository import (
    check_repository_update,
    configure_git_env,
    fetch_repository,
    list_branches,
    list_commits,
    switch_repository_branch,
    switch_repository_commit,
    update_repository,
)
from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryState, inspect_repository

__all__ = [
    "check_extension_updates",
    "check_package_update",
    "check_webui_updates",
    "ExtensionManager",
    "fetch_comfyui_custom_node_index",
    "fetch_extension_index",
    "fetch_pypi_versions",
    "filter_extension_index",
    "parse_comfyui_custom_node_index",
    "parse_extension_index",
    "DEFAULT_EXTENSION_INDEX_URL",
    "BranchInfo",
    "CommitInfo",
    "ExtensionIndexItem",
    "ExtensionSourceType",
    "ExtensionUpdateStatus",
    "ManagedExtension",
    "PackageUpdateStatus",
    "PackageVersionInfo",
    "RepositoryUpdateStatus",
    "WebUiUpdateOptions",
    "WebUiUpdateStatus",
    "WebUiUpdateSummary",
    "check_repository_update",
    "configure_git_env",
    "fetch_repository",
    "list_branches",
    "list_commits",
    "switch_repository_branch",
    "switch_repository_commit",
    "update_repository",
    "RepositoryState",
    "inspect_repository",
]
