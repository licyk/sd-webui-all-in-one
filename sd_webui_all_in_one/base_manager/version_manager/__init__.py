"""通用版本管理服务。"""

# ruff: noqa: F401

from .checks import check_extension_updates, check_package_update, check_webui_updates
from .extensions import ExtensionManager
from .indexes import (
    fetch_comfyui_custom_node_index,
    fetch_extension_index,
    fetch_pypi_versions,
    filter_extension_index,
    parse_comfyui_custom_node_index,
    parse_extension_index,
)
from .models import (
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
from .repository import (
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

__all__ = [name for name in globals() if not name.startswith("_")]
