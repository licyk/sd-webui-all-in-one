"""版本管理数据模型。"""

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments,too-many-locals

from dataclasses import dataclass
from pathlib import Path
from typing import (
    Literal,
    TypeAlias,
)

from sd_webui_all_in_one.base_manager.base import (
    PyTorchUpdateStatus,
)
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


DEFAULT_EXTENSION_INDEX_URL = "https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui-extensions/master/index.json"
"""AUTOMATIC1111 扩展源地址"""


ExtensionSourceType: TypeAlias = Literal["git", "comfy-registry", "file", "unknown"]
"""扩展安装来源类型"""


@dataclass(slots=True)
class CommitInfo:
    """
    Git 提交信息

    Attributes:
        commit (str):
            提交 ID
        message (str):
            提交信息
        date (str):
            提交时间
        is_current (bool):
            是否为当前提交
    """

    commit: str
    message: str
    date: str
    is_current: bool = False
    short_commit: str = ""
    author: str = ""
    timestamp: int | None = None
    tags: tuple[str, ...] = ()
    branches: tuple[str, ...] = ()


@dataclass(slots=True)
class BranchInfo:
    """
    Git 分支信息

    Attributes:
        name (str):
            分支名称
        is_current (bool):
            是否为当前分支
        is_remote (bool):
            是否为远程分支
    """

    name: str
    is_current: bool = False
    is_remote: bool = False


@dataclass(slots=True)
class ManagedExtension:
    """
    通用扩展信息

    Attributes:
        name (str):
            扩展名称
        path (Path):
            扩展路径
        enabled (bool):
            是否启用
        is_git_repo (bool):
            是否为 Git 仓库
        url (str | None):
            扩展远程地址
        branch (str | None):
            当前分支
        commit (str | None):
            当前提交 ID
        commit_date (str | None):
            当前提交时间
        message (str | None):
            当前提交信息
        error (str | None):
            扩展状态错误信息
    """

    name: str
    path: Path
    enabled: bool
    is_git_repo: bool
    url: str | None = None
    branch: str | None = None
    commit: str | None = None
    commit_date: str | None = None
    message: str | None = None
    error: str | None = None
    source_type: ExtensionSourceType = "git"
    registry_id: str | None = None
    registry_version: str | None = None
    download_url: str | None = None
    repository: str | None = None
    dependencies: tuple[str, ...] = ()


@dataclass(slots=True)
class ExtensionIndexItem:
    """
    扩展源条目

    Attributes:
        name (str):
            扩展名称
        url (str):
            扩展下载地址
        description (str):
            扩展简介
        tags (tuple[str, ...]):
            扩展标签
        install_type (str):
            安装类型
        files (tuple[str, ...]):
            扩展文件地址列表
        reference (str):
            扩展参考地址
        author (str):
            扩展作者或发布者名称
        installable (bool):
            扩展源条目是否可直接安装
        install_status (str):
            扩展源条目的安装状态说明
    """

    name: str
    url: str
    description: str = ""
    tags: tuple[str, ...] = ()
    install_type: str = "git-clone"
    files: tuple[str, ...] = ()
    reference: str = ""
    source_type: ExtensionSourceType = "git"
    registry_id: str | None = None
    registry_version: str | None = None
    repository: str | None = None
    download_url: str | None = None
    dependencies: tuple[str, ...] = ()
    author: str = ""
    installable: bool = True
    install_status: str = ""
    installed: bool = False


@dataclass(slots=True)
class PackageVersionInfo:
    """
    PyPI 软件包版本信息

    Attributes:
        version (str):
            版本号
        upload_time (str):
            发布时间
        summary (str):
            软件包简介
        is_current (bool):
            是否为当前版本
        is_prerelease (bool):
            是否为预发布版本 (``a``/``b``/``rc``/``dev``); 正式发布版本为 ``False``
    """

    version: str
    upload_time: str = ""
    summary: str = ""
    is_current: bool = False
    is_prerelease: bool = False


@dataclass(slots=True)
class RepositoryUpdateStatus:
    """
    Git 仓库更新状态

    Attributes:
        name (str):
            仓库名称
        path (Path):
            仓库路径
        is_git_repo (bool):
            是否为 Git 仓库
        branch (str | None):
            当前分支
        remote_branch (str | None):
            用于比较的远程分支
        current_commit (str | None):
            当前提交 ID
        remote_commit (str | None):
            远程提交 ID
        ahead (int):
            本地领先远程的提交数量
        behind (int):
            本地落后远程的提交数量
        has_update (bool):
            是否有可拉取更新
        is_dirty (bool):
            工作区是否有未提交改动
        error (str | None):
            检查错误信息
    """

    name: str
    path: Path
    is_git_repo: bool
    branch: str | None = None
    remote_branch: str | None = None
    current_commit: str | None = None
    remote_commit: str | None = None
    ahead: int = 0
    behind: int = 0
    has_update: bool = False
    is_dirty: bool = False
    error: str | None = None


@dataclass(slots=True)
class PackageUpdateStatus:
    """PyPI 内核包更新状态。

    Attributes:
        latest_version (str | None):
            更新检查采用的最新版本。默认只统计正式发布版本, 预发布版本不参与,
            因此比当前版本新的预发布版本不会产生 ``has_update``。
        latest_prerelease (str | None):
            比 ``latest_version`` 更新的最新预发布版本; 没有则为 ``None``。
            仅用于展示预发布通道的进展, 不影响 ``has_update``。
    """

    name: str
    package_name: str
    installed: bool
    current_version: str | None
    latest_version: str | None
    has_update: bool
    index_url: str
    source_type: Literal["pypi"] = "pypi"
    error: str | None = None
    latest_prerelease: str | None = None


@dataclass(slots=True)
class ExtensionUpdateStatus:
    """WebUI 扩展更新状态。"""

    name: str
    path: Path
    enabled: bool
    source_type: ExtensionSourceType
    is_git_repo: bool
    url: str | None = None
    branch: str | None = None
    remote_branch: str | None = None
    current_version: str | None = None
    latest_version: str | None = None
    ahead: int = 0
    behind: int = 0
    has_update: bool = False
    skipped: bool = False
    registry_id: str | None = None
    message: str = ""
    error: str | None = None


@dataclass(slots=True)
class WebUiUpdateSummary:
    """
    WebUI 更新检查摘要

    Attributes:
        has_update (bool):
            内核或扩展是否存在更新
        kernel_has_update (bool):
            内核是否存在更新
        pytorch_has_update (bool):
            PyTorch 是否存在更新
        extension_update_count (int):
            可更新扩展数量
        checked_extension_count (int):
            已检查扩展数量
        skipped_count (int):
            跳过或无法检查的条目数量
        error_count (int):
            检查失败条目数量
    """

    has_update: bool
    kernel_has_update: bool
    pytorch_has_update: bool
    extension_update_count: int
    checked_extension_count: int
    skipped_count: int
    error_count: int


@dataclass(slots=True)
class WebUiUpdateStatus:
    """单个 WebUI 的完整更新检查结果。"""

    webui_type: str
    name: str
    path: Path
    kernel: RepositoryUpdateStatus | PackageUpdateStatus | None
    pytorch: PyTorchUpdateStatus | None
    extensions: list[ExtensionUpdateStatus]
    extensions_supported: bool
    summary: WebUiUpdateSummary
    errors: list[str]


@dataclass(slots=True)
class WebUiUpdateOptions:
    """WebUI 更新检查选项。"""

    fetch: bool = True
    include_kernel: bool = True
    include_extensions: bool = True
    include_pytorch: bool = True
    use_github_mirror: bool = False
    custom_github_mirror: str | list[str] | None = None
    pypi_index_url: str = "https://pypi.org/pypi"
    timeout: int | None = 20
    allow_prerelease: bool = False
    """PyPI 内核包是否把预发布版本也作为更新目标"""
