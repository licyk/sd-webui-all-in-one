"""python-build-standalone 资源管理

下载 python-build-standalone 构建的 Python, 重新打包并上传到 HuggingFace / ModelScope 仓库, 以及查询已上传的资源
"""

from sd_webui_all_in_one.python_standalone.types import (
    DEFAULT_ARCHIVE_FORMAT,
    DEFAULT_GITHUB_API_URL,
    DEFAULT_HF_REPO_ID,
    DEFAULT_MS_REPO_ID,
    DEFAULT_PATH_IN_REPO,
    DEFAULT_PLATFORMS,
    DEFAULT_SOURCE_REPO,
    DEFAULT_VARIANT,
    DEFAULT_VERSIONS,
    RESOURCE_TYPE,
    PythonAsset,
    PythonStandaloneResource,
    RepoTarget,
    ResourceListData,
    SyncConfig,
    SyncPlan,
    SyncReport,
    SyncTask,
    SyncTaskResult,
)
from sd_webui_all_in_one.python_standalone.release import (
    fetch_release_assets,
    list_releases,
    parse_asset_name,
    select_assets,
)
from sd_webui_all_in_one.python_standalone.resources import (
    build_download_url,
    build_resource_list_data,
    collect_resources,
    filter_resources,
    parse_resource_path,
    render_resources_markdown,
    render_resources_table,
)
from sd_webui_all_in_one.python_standalone.sync import (
    build_sync_report,
    create_sync_plan,
    plan_tasks,
    render_sync_plan,
    render_sync_report_markdown,
    run_sync,
    sync_exit_code,
)

__all__ = [
    # 常量
    "DEFAULT_ARCHIVE_FORMAT",
    "DEFAULT_GITHUB_API_URL",
    "DEFAULT_HF_REPO_ID",
    "DEFAULT_MS_REPO_ID",
    "DEFAULT_PATH_IN_REPO",
    "DEFAULT_PLATFORMS",
    "DEFAULT_SOURCE_REPO",
    "DEFAULT_VARIANT",
    "DEFAULT_VERSIONS",
    "RESOURCE_TYPE",
    # 类型
    "PythonAsset",
    "PythonStandaloneResource",
    "RepoTarget",
    "ResourceListData",
    "SyncConfig",
    "SyncPlan",
    "SyncReport",
    "SyncTask",
    "SyncTaskResult",
    # Release
    "fetch_release_assets",
    "list_releases",
    "parse_asset_name",
    "select_assets",
    # 资源查询
    "build_download_url",
    "build_resource_list_data",
    "collect_resources",
    "filter_resources",
    "parse_resource_path",
    "render_resources_markdown",
    "render_resources_table",
    # 同步
    "build_sync_report",
    "create_sync_plan",
    "plan_tasks",
    "render_sync_plan",
    "render_sync_report_markdown",
    "run_sync",
    "sync_exit_code",
]
