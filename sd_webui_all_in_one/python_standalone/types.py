"""python-build-standalone 资源管理类型定义"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypeAlias, TypedDict

from sd_webui_all_in_one.downloader.types import DownloadToolType
from sd_webui_all_in_one.repo_manager import ApiType, RepoType

RESOURCE_TYPE = "python-standalone"
"""资源类型标识"""

DEFAULT_SOURCE_REPO = "astral-sh/python-build-standalone"
"""默认 python-build-standalone 发布仓库"""

DEFAULT_GITHUB_API_URL = "https://api.github.com"
"""默认 GitHub API 地址"""

DEFAULT_HF_REPO_ID = "licyk/sd-webui-all-in-one"
"""默认 HuggingFace 仓库 ID"""

DEFAULT_MS_REPO_ID = "licyks/sd-webui-all-in-one"
"""默认 ModelScope 仓库 ID"""

DEFAULT_PATH_IN_REPO = "python"
"""默认仓库中的 Python 资源目录"""

DEFAULT_VARIANT = "install_only"
"""默认构建变体"""

DEFAULT_ARCHIVE_FORMAT = ".zip"
"""默认重新打包格式"""

DEFAULT_VERSIONS: list[str] = ["3.10", "3.11", "3.12", "3.13", "3.14"]
"""默认处理的 Python 主次版本号"""

DEFAULT_PLATFORMS: dict[str, str] = {
    "windows/amd64": "x86_64-pc-windows-msvc",
    "windows/aarch64": "aarch64-pc-windows-msvc",
    "linux/amd64": "x86_64-unknown-linux-gnu",
    "linux/aarch64": "aarch64-unknown-linux-gnu",
    "macos/amd64": "x86_64-apple-darwin",
    "macos/aarch64": "aarch64-apple-darwin",
}
"""平台 (仓库路径形式 <系统>/<架构>) 到构建目标三元组的映射"""

SOURCE_DISPLAY_NAME: dict[str, str] = {
    "huggingface": "HuggingFace",
    "modelscope": "ModelScope",
}
"""下载源展示名称"""

SOURCE_SHORT_NAME: dict[str, str] = {
    "huggingface": "HF",
    "modelscope": "MS",
}
"""下载源简称"""

SyncAction: TypeAlias = Literal["skip", "upload-only", "build"]
"""同步任务动作: 跳过 / 只上传已有打包结果 / 下载打包并上传"""

SyncStatus: TypeAlias = Literal["skipped", "success", "failed", "cancelled"]
"""同步任务结果状态"""


@dataclass(frozen=True)
class PythonAsset:
    """python-build-standalone Release 中的一个 CPython 构建文件

    Attributes:
        name (str): 文件名
        url (str): 下载链接
        version (str): Python 版本, 如 3.12.8
        build_date (str): 构建日期 (即 Release 标签)
        build_type (str): 构建类型, 如 x86_64-unknown-linux-gnu-install_only
        size (int | None): 文件大小
        sha256 (str | None): 文件 SHA256
    """

    name: str
    url: str
    version: str
    build_date: str
    build_type: str
    size: int | None = None
    sha256: str | None = None

    @property
    def version_tuple(self) -> tuple[int, ...]:
        """版本号元组, 用于比较版本

        Returns:
            tuple[int, ...]: 版本号元组, 如 (3, 12, 8)
        """
        return version_tuple(self.version)

    @property
    def minor(self) -> str:
        """主次版本号

        Returns:
            str: 主次版本号, 如 3.12
        """
        return ".".join(self.version.split(".")[:2])


@dataclass(frozen=True)
class RepoTarget:
    """HuggingFace / ModelScope 仓库配置

    Attributes:
        source (ApiType): 仓库 API 类型
        repo_id (str): 仓库 ID
        repo_type (RepoType): 仓库类型
    """

    source: ApiType
    repo_id: str
    repo_type: RepoType = "model"

    @property
    def display_name(self) -> str:
        """仓库展示名称

        Returns:
            str: 展示名称, 如 HuggingFace:licyk/sd-webui-all-in-one
        """
        return f"{SOURCE_DISPLAY_NAME[self.source]}:{self.repo_id}"


@dataclass
class SyncConfig:
    """下载、重新打包并上传 Python 的配置

    Attributes:
        targets (list[RepoTarget]): 上传目标仓库, 为空时只下载和打包
        release_tag (str): python-build-standalone Release 标签, latest 表示最新版本
        source_repo (str): python-build-standalone 发布仓库
        github_api_url (str): GitHub API 地址
        github_token (str | None): GitHub Token
        versions (list[str]): Python 主次版本号列表
        platforms (dict[str, str]): 要处理的平台到构建目标三元组的映射
        variant (str): 构建变体
        archive_format (str): 重新打包格式
        path_in_repo (str): 仓库中的 Python 资源目录
        revision (str | None): 仓库分支
        public (bool): 仓库不存在需要创建时是否设为公开
        output_dir (Path): 打包结果保存目录
        work_dir (Path | None): 临时工作目录, 为 None 时使用系统临时目录
        keep_temp (bool): 是否保留临时文件
        force (bool): 是否忽略仓库状态强制重新完成全部任务
        workers (int): 同时执行的任务数
        upload_threads (int): 单个仓库上传线程数
        download_tool (DownloadToolType): 下载工具
        download_split (int): 单个文件下载分片数
        verify_hash (bool): 是否校验下载文件的 SHA256
        progress (bool): 是否显示进度条
    """

    targets: list[RepoTarget] = field(default_factory=list)
    release_tag: str = "latest"
    source_repo: str = DEFAULT_SOURCE_REPO
    github_api_url: str = DEFAULT_GITHUB_API_URL
    github_token: str | None = None
    versions: list[str] = field(default_factory=lambda: list(DEFAULT_VERSIONS))
    platforms: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_PLATFORMS))
    variant: str = DEFAULT_VARIANT
    archive_format: str = DEFAULT_ARCHIVE_FORMAT
    path_in_repo: str = DEFAULT_PATH_IN_REPO
    revision: str | None = None
    public: bool = False
    output_dir: Path = field(default_factory=lambda: Path("python_dist"))
    work_dir: Path | None = None
    keep_temp: bool = False
    force: bool = False
    workers: int = 4
    upload_threads: int = 1
    download_tool: DownloadToolType = "requests"
    download_split: int = 5
    verify_hash: bool = True
    progress: bool = False


@dataclass
class SyncTask:
    """一个 Python 构建的同步任务

    Attributes:
        asset (PythonAsset): 源构建文件
        platform (str): 平台, 如 linux/amd64
        triple (str): 构建目标三元组
        variant (str): 构建变体
        archive_format (str): 重新打包格式
        archive_name (str): 重新打包后的文件名
        repo_path (str): 在仓库中的路径
        present_targets (list[RepoTarget]): 仓库中已有该文件的目标
        missing_targets (list[RepoTarget]): 需要上传的目标
        action (SyncAction): 任务动作
    """

    asset: PythonAsset
    platform: str
    triple: str
    variant: str
    archive_format: str
    archive_name: str
    repo_path: str
    present_targets: list[RepoTarget] = field(default_factory=list)
    missing_targets: list[RepoTarget] = field(default_factory=list)
    action: SyncAction = "build"

    @property
    def label(self) -> str:
        """任务标签, 用于日志

        Returns:
            str: 任务标签, 如 3.12 linux/amd64
        """
        return f"{self.asset.minor} {self.platform}"

    @property
    def slug(self) -> str:
        """任务目录名

        Returns:
            str: 任务目录名, 如 3.12-linux-amd64
        """
        return re.sub(r"[^\w.-]+", "-", f"{self.asset.minor}-{self.platform}-{self.variant}")


@dataclass
class SyncPlan:
    """同步计划

    Attributes:
        release_tag (str): 实际使用的 Release 标签
        source_repo (str): python-build-standalone 发布仓库
        targets (list[RepoTarget]): 上传目标仓库
        tasks (list[SyncTask]): 任务列表
    """

    release_tag: str
    source_repo: str
    targets: list[RepoTarget]
    tasks: list[SyncTask]


@dataclass
class SyncTaskResult:
    """同步任务执行结果

    Attributes:
        task (SyncTask): 任务
        status (SyncStatus): 结果状态
        uploaded (list[RepoTarget]): 本次上传成功的目标
        archive (Path | None): 打包结果路径
        error (str | None): 错误信息
        duration (float): 耗时 (秒)
    """

    task: SyncTask
    status: SyncStatus
    uploaded: list[RepoTarget] = field(default_factory=list)
    archive: Path | None = None
    error: str | None = None
    duration: float = 0.0


class PythonStandaloneResource(TypedDict):
    """已上传 / 已打包的 Python 资源信息"""

    type: str
    """资源类型, 固定为 python-standalone"""

    name: str
    """文件名"""

    implementation: str
    """Python 实现, 如 cpython"""

    version: str
    """Python 版本"""

    minor: str
    """主次版本号"""

    build_date: str
    """构建日期"""

    platform: str
    """系统"""

    arch: str
    """架构"""

    triple: str | None
    """构建目标三元组"""

    variant: str
    """构建变体"""

    archive_format: str
    """压缩包格式"""

    path: str
    """仓库中的路径"""

    size: int | None
    """文件大小"""

    sha256: str | None
    """文件 SHA256"""

    urls: dict[str, str]
    """各下载源的下载链接"""


class SyncReportResource(PythonStandaloneResource):
    """同步报告中的资源信息"""

    action: SyncAction
    """任务动作"""

    status: SyncStatus
    """任务结果状态"""

    uploaded_to: list[str]
    """本次上传成功的下载源"""

    error: str | None
    """错误信息"""

    duration: float
    """耗时 (秒)"""


class SyncReportSummary(TypedDict):
    """同步报告统计"""

    total: int
    """任务总数"""

    success: int
    """成功数"""

    failed: int
    """失败数"""

    skipped: int
    """跳过数"""

    cancelled: int
    """取消数"""


class SyncReport(TypedDict):
    """同步报告"""

    type: str
    """资源类型"""

    generated_at: str
    """生成时间 (UTC)"""

    source_repo: str
    """python-build-standalone 发布仓库"""

    release_tag: str
    """Release 标签"""

    targets: list[str]
    """上传目标仓库"""

    summary: SyncReportSummary
    """统计"""

    resources: list[SyncReportResource]
    """资源列表"""


class ResourceListData(TypedDict):
    """已上传资源查询结果"""

    type: str
    """资源类型"""

    generated_at: str
    """生成时间 (UTC)"""

    sources: list[str]
    """查询的仓库"""

    latest_only: bool
    """是否只包含最新构建"""

    resources: list[PythonStandaloneResource]
    """资源列表"""


def version_tuple(version: str) -> tuple[int, ...]:
    """把版本号转换为可比较的元组, 忽略预发布等后缀

    Args:
        version (str): 版本号, 如 3.14.0rc1
    Returns:
        tuple[int, ...]: 版本号元组, 如 (3, 14, 0)
    """
    return tuple(int(part) for part in re.sub(r"[^\d.].*$", "", version).split(".") if part)
