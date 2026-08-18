"""通用版本管理服务"""

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments,too-many-locals

import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Callable,
    Iterable,
    Literal,
)

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    PyTorchUpdateStatus,
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
    clone_repo,
    get_pytorch_update_status,
    get_repo_name_from_url,
)
from sd_webui_all_in_one.base_manager.repository_inspector import (
    RepositoryState as RepositoryState,
    inspect_repository,
    run_git_output,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.file_manager import remove_files
from sd_webui_all_in_one.mirror_manager import GITHUB_MIRROR_LIST
from sd_webui_all_in_one.package_analyzer import CommonVersionComparison, PyWhlVersionComparison, get_package_version_from_library, is_prerelease_version, parse_version_component


DEFAULT_EXTENSION_INDEX_URL = "https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui-extensions/master/index.json"
"""AUTOMATIC1111 扩展源地址"""


ExtensionSourceType = Literal["git", "comfy-registry", "file", "unknown"]
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


def configure_git_env(
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> dict[str, str]:
    """
    应用项目已有 Git 配置并返回环境变量

    Args:
        use_github_mirror (bool):
            是否启用 GitHub 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源

    Returns:
        dict[str, str]: 配置后的环境变量
    """
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)
    return custom_env


def _run_git_output(
    path: Path,
    *args: str,
    custom_env: dict[str, str] | None = None,
) -> str:
    """
    执行 Git 命令并返回输出

    Args:
        path (Path):
            Git 仓库路径
        *args (str):
            Git 命令参数
        custom_env (dict[str, str] | None):
            自定义环境变量

    Returns:
        str: 命令输出
    """
    output = git_warpper.run_git(*args, path=path, custom_env=custom_env, live=False)
    return "" if output is None else output.strip()


def _safe_git_value(func: Callable[[Path], str | None], path: Path) -> str | None:
    """
    安全读取 Git 字段

    Args:
        func (Callable[[Path], str | None]):
            Git 字段读取函数
        path (Path):
            Git 仓库路径

    Returns:
        str | None: 字段值, 读取失败时返回 None
    """
    try:
        return func(path)
    except Exception:
        return None


def fetch_repository(
    path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """
    拉取远程引用

    Args:
        path (Path):
            Git 仓库路径
        use_github_mirror (bool):
            是否启用 GitHub 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源

    Raises:
        ValueError:
            目标路径不是 Git 仓库
    """
    if not git_warpper.is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")
    custom_env = configure_git_env(use_github_mirror=use_github_mirror, custom_github_mirror=custom_github_mirror) if use_github_mirror else None
    _run_git_output(path, "fetch", "--all", "--prune", custom_env=custom_env)


def _resolve_update_remote_ref(path: Path, branch: str | None) -> str | None:
    """
    解析用于更新检查的远程引用

    Args:
        path (Path):
            Git 仓库路径
        branch (str | None):
            当前分支

    Returns:
        str | None: 远程引用
    """
    remote_branch = git_warpper.get_git_repo_current_remote_branch(path)
    if remote_branch:
        return remote_branch
    if branch:
        fallback_ref = f"origin/{branch}"
        try:
            _run_git_output(path, "rev-parse", "--verify", fallback_ref)
            return fallback_ref
        except RuntimeError:
            return None
    return None


def _read_repository_dirty(path: Path) -> bool:
    """
    检查 Git 工作区是否有未提交改动

    Args:
        path (Path):
            Git 仓库路径

    Returns:
        bool: 存在未提交改动时返回 True
    """
    try:
        return bool(_run_git_output(path, "status", "--porcelain"))
    except Exception:
        return False


def _read_ahead_behind(path: Path, remote_ref: str) -> tuple[int, int]:
    """
    读取本地与远程引用的领先/落后提交数

    Args:
        path (Path):
            Git 仓库路径
        remote_ref (str):
            远程引用

    Returns:
        tuple[int, int]: 本地领先数量和本地落后数量
    """
    output = _run_git_output(path, "rev-list", "--left-right", "--count", f"HEAD...{remote_ref}")
    parts = output.replace("\t", " ").split()
    if len(parts) < 2:
        return 0, 0
    return int(parts[0]), int(parts[1])


def check_repository_update(
    path: Path,
    fetch: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> RepositoryUpdateStatus:
    """
    检查 Git 仓库是否存在远程更新

    Args:
        path (Path):
            Git 仓库路径
        fetch (bool):
            是否先拉取远程引用
        use_github_mirror (bool):
            是否启用 GitHub 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源

    Returns:
        RepositoryUpdateStatus: 仓库更新状态
    """
    state = inspect_repository(path)
    status = RepositoryUpdateStatus(
        name=state.name,
        path=state.path,
        is_git_repo=state.is_git_repo,
        branch=state.branch,
        current_commit=state.commit,
        is_dirty=False,
        error=state.error,
    )
    if not state.is_git_repo:
        return status

    try:
        if fetch:
            fetch_repository(path, use_github_mirror=use_github_mirror, custom_github_mirror=custom_github_mirror)
        status.is_dirty = _read_repository_dirty(path)
        status.remote_branch = _resolve_update_remote_ref(path, state.branch)
        if status.remote_branch is None:
            status.error = "未找到远程跟踪分支"
            return status
        status.current_commit = _run_git_output(path, "rev-parse", "HEAD")
        status.remote_commit = _run_git_output(path, "rev-parse", status.remote_branch)
        status.ahead, status.behind = _read_ahead_behind(path, status.remote_branch)
        status.has_update = status.behind > 0
        status.error = None
    except Exception as exc:
        status.error = str(exc)
    return status


def list_commits(path: Path, limit: int | None = 100, fetch: bool = True) -> list[CommitInfo]:
    """
    列出最近提交

    Args:
        path (Path):
            Git 仓库路径
        limit (int | None):
            最大提交数量, 为 None 时不限制
        fetch (bool):
            是否先拉取远程引用, 以确保 @{u} 指向最新的远程提交

    Returns:
        list[CommitInfo]: 提交信息列表
    """
    try:
        if not git_warpper.is_git_repo(path):
            return []
    except Exception:
        return []
    if fetch:
        try:
            fetch_repository(path)
        except Exception:
            pass
    current_commit = _safe_git_value(git_warpper.get_current_commit, path)
    format_arg = "--format=%H%x1f%h%x1f%ci%x1f%an%x1f%at%x1f%D%x1f%s"
    args = ["log", "HEAD", "@{u}", format_arg]
    if limit is not None:
        args.extend(["-n", str(limit)])
    try:
        output = run_git_output(path, *args)
    except RuntimeError:
        args = ["log", "HEAD", format_arg]
        if limit is not None:
            args.extend(["-n", str(limit)])
        output = run_git_output(path, *args)
    commits: list[CommitInfo] = []
    for line in output.splitlines():
        parts = line.split("\x1f", 6)
        if len(parts) != 7:
            continue
        commit, short_commit, date, author, timestamp_text, decorations, message = parts
        tags: list[str] = []
        branches: list[str] = []
        for decoration in (item.strip() for item in decorations.split(",")):
            if not decoration:
                continue
            if decoration.startswith("tag: "):
                tags.append(decoration.removeprefix("tag: "))
            elif decoration.startswith("HEAD -> "):
                branches.append(decoration.removeprefix("HEAD -> "))
            else:
                branches.append(decoration)
        commits.append(
            CommitInfo(
                commit=commit,
                short_commit=short_commit,
                date=date,
                message=message,
                author=author,
                timestamp=int(timestamp_text) if timestamp_text else None,
                tags=tuple(tags),
                branches=tuple(branches),
                is_current=bool(current_commit and commit.startswith(current_commit)),
            )
        )
    return commits


def list_branches(path: Path, fetch: bool = True) -> list[BranchInfo]:
    """
    列出本地和远程分支

    Args:
        path (Path):
            Git 仓库路径
        fetch (bool):
            是否先拉取远程引用

    Returns:
        list[BranchInfo]: 分支信息列表
    """
    try:
        if not git_warpper.is_git_repo(path):
            return []
    except Exception:
        return []
    if fetch:
        fetch_repository(path)
    current_branch = _safe_git_value(git_warpper.get_current_branch, path)
    output = run_git_output(path, "branch", "--all", "--format=%(refname:short)")
    branches: dict[str, BranchInfo] = {}
    for raw_name in output.splitlines():
        name = raw_name.strip()
        if not name or "HEAD ->" in name:
            continue
        is_remote = name.startswith("origin/")
        display_name = name.removeprefix("origin/")
        if display_name in branches and branches[display_name].is_remote is False:
            continue
        branches[display_name] = BranchInfo(
            name=display_name,
            is_current=display_name == current_branch,
            is_remote=is_remote,
        )
    return sorted(branches.values(), key=lambda item: (not item.is_current, item.name.lower()))


def switch_repository_branch(
    path: Path,
    branch: str,
    new_url: str | None = None,
    recurse_submodules: bool = False,
) -> None:
    """
    切换仓库分支

    Args:
        path (Path):
            Git 仓库路径
        branch (str):
            目标分支
        new_url (str | None):
            切换前需要设置的新远程地址
        recurse_submodules (bool):
            是否递归更新子模块
    """
    fetch_repository(path)
    git_warpper.switch_branch(
        path=path,
        branch=branch,
        new_url=new_url,
        recurse_submodules=recurse_submodules,
    )


def switch_repository_commit(
    path: Path,
    commit: str,
) -> None:
    """
    切换仓库到指定提交

    Args:
        path (Path):
            Git 仓库路径
        commit (str):
            目标提交 ID
    """
    git_warpper.switch_commit(path=path, commit=commit)


def update_repository(
    path: Path,
) -> None:
    """
    更新仓库

    Args:
        path (Path):
            Git 仓库路径
    """
    git_warpper.update(path)


class ExtensionManager:
    """
    可复用扩展管理器

    抽象扩展目录、启禁用策略、安装、更新、卸载和版本切换流程,
    使不同 WebUI 可以通过不同目录和启禁用函数复用同一套逻辑。
    """

    def __init__(
        self,
        root_path: Path,
        extension_dir_name: str,
        is_enabled: Callable[[str, Path], bool],
        set_enabled: Callable[[str, bool], None],
        ignored_names: Iterable[str] | None = None,
        include_files: bool = False,
    ) -> None:
        """
        初始化扩展管理器

        Args:
            root_path (Path):
                WebUI 根目录
            extension_dir_name (str):
                扩展目录名称
            is_enabled (Callable[[str, Path], bool]):
                扩展启用状态读取函数
            set_enabled (Callable[[str, bool], None]):
                扩展启用状态写入函数
            ignored_names (Iterable[str] | None):
                需要忽略的扩展名称
            include_files (bool):
                是否允许把单文件扩展纳入列表
        """
        self.root_path = Path(root_path)
        self.extension_path = self.root_path / extension_dir_name
        self.is_enabled = is_enabled
        self.set_enabled = set_enabled
        self.ignored_names = set(ignored_names or {"__pycache__"})
        self.include_files = include_files

    def list_extensions(self) -> list[ManagedExtension]:
        """
        获取本地扩展列表

        Returns:
            list[ManagedExtension]: 本地扩展列表
        """
        if not self.extension_path.exists():
            return []
        result: list[ManagedExtension] = []
        for ext_path in sorted(self.extension_path.iterdir(), key=lambda item: item.name.lower()):
            if ext_path.name in self.ignored_names:
                continue
            if not ext_path.is_dir() and not (self.include_files and ext_path.is_file()):
                continue
            repo_state = inspect_repository(ext_path)
            result.append(
                ManagedExtension(
                    name=ext_path.name,
                    path=ext_path,
                    enabled=self.is_enabled(ext_path.name, ext_path),
                    is_git_repo=repo_state.is_git_repo,
                    url=repo_state.url,
                    branch=repo_state.branch,
                    commit=repo_state.commit,
                    commit_date=repo_state.commit_date,
                    message=repo_state.message,
                    error=repo_state.error,
                    source_type="git" if repo_state.is_git_repo else ("file" if ext_path.is_file() else "unknown"),
                )
            )
        return result

    def set_extension_enabled(
        self,
        name: str,
        enabled: bool,
    ) -> None:
        """
        设置扩展启用状态

        Args:
            name (str):
                扩展名称
            enabled (bool):
                是否启用
        """
        self.set_enabled(name, enabled)

    def install_extension(
        self,
        url: str,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> Path:
        """
        从 Git 地址安装扩展

        Args:
            url (str):
                Git 仓库地址
            use_github_mirror (bool):
                是否启用 GitHub 镜像源
            custom_github_mirror (str | list[str] | None):
                自定义 GitHub 镜像源

        Returns:
            Path: 扩展安装路径

        Raises:
            FileExistsError:
                扩展已经存在
        """
        del use_github_mirror, custom_github_mirror
        extension_name = get_repo_name_from_url(url)
        extension_path = self.extension_path / extension_name
        if extension_path.exists():
            raise FileExistsError(f"'{extension_name}' 扩展已存在")
        clone_repo(repo=url, path=extension_path)
        return extension_path

    def update_extension(
        self,
        name: str,
    ) -> None:
        """
        更新扩展

        Args:
            name (str):
                扩展名称

        Raises:
            ValueError:
                扩展不是 Git 仓库
        """
        ext_path = self.extension_path / name
        if not git_warpper.is_git_repo(ext_path):
            raise ValueError(f"'{name}' 不是 Git 仓库，无法更新")
        update_repository(ext_path)

    def update_all(
        self,
    ) -> None:
        """
        更新所有 Git 扩展

        Raises:
            AggregateError:
                一个或多个扩展更新失败
        """
        errors: list[Exception] = []
        for ext in self.list_extensions():
            if not ext.is_git_repo:
                continue
            try:
                update_repository(ext.path)
            except Exception as e:
                errors.append(e)
        if errors:
            raise AggregateError("更新扩展时发生错误", errors)

    def check_updates(
        self,
        fetch: bool = True,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> list[RepositoryUpdateStatus]:
        """
        检查所有扩展是否存在远程更新

        Args:
            fetch (bool):
                是否先拉取远程引用
            use_github_mirror (bool):
                是否启用 GitHub 镜像源
            custom_github_mirror (str | list[str] | None):
                自定义 GitHub 镜像源

        Returns:
            list[RepositoryUpdateStatus]: 扩展更新状态列表
        """
        result: list[RepositoryUpdateStatus] = []
        for ext in self.list_extensions():
            if not ext.is_git_repo:
                result.append(
                    RepositoryUpdateStatus(
                        name=ext.name,
                        path=ext.path,
                        is_git_repo=False,
                        branch=ext.branch,
                        current_commit=ext.commit,
                        error=ext.error or "非 Git 仓库",
                    )
                )
                continue
            status = check_repository_update(
                ext.path,
                fetch=fetch,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
            )
            status.name = ext.name
            result.append(status)
        return result

    def uninstall_extension(
        self,
        name: str,
    ) -> None:
        """
        卸载扩展

        Args:
            name (str):
                扩展名称

        Raises:
            FileNotFoundError:
                扩展未安装
        """
        ext_path = self.extension_path / name
        if not ext_path.exists():
            raise FileNotFoundError(f"'{name}' 扩展未安装")
        remove_files(ext_path)

    def switch_extension_commit(
        self,
        name: str,
        commit: str,
    ) -> None:
        """
        切换扩展到指定提交

        Args:
            name (str):
                扩展名称
            commit (str):
                目标提交 ID
        """
        switch_repository_commit(self.extension_path / name, commit)

    def switch_extension_branch(
        self,
        name: str,
        branch: str,
    ) -> None:
        """
        切换扩展分支

        Args:
            name (str):
                扩展名称
            branch (str):
                目标分支
        """
        switch_repository_branch(self.extension_path / name, branch)


def _pick_extension_name(item: dict[str, Any]) -> str:
    for key in ("name", "title", "extension_name"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    url = item.get("url") or item.get("link") or item.get("git")
    if isinstance(url, str) and url.strip():
        return get_repo_name_from_url(url)
    return "unknown"


def _pick_extension_url(item: dict[str, Any]) -> str:
    for key in ("url", "link", "git", "repo"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _pick_extension_description(item: dict[str, Any]) -> str:
    for key in ("description", "desc", "summary", "info"):
        value = item.get(key)
        if isinstance(value, str):
            return value.strip()
    return ""


def _pick_extension_tags(item: dict[str, Any]) -> tuple[str, ...]:
    value = item.get("tags") or item.get("tag")
    if isinstance(value, str):
        return tuple(x.strip() for x in value.split(",") if x.strip())
    if isinstance(value, list):
        return tuple(str(x).strip() for x in value if str(x).strip())
    return ()


def _pick_extension_files(item: dict[str, Any]) -> tuple[str, ...]:
    value = item.get("files")
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(str(x).strip() for x in value if str(x).strip())
    url = _pick_extension_url(item)
    return (url,) if url else ()


def parse_extension_index(data: Any) -> list[ExtensionIndexItem]:
    """
    解析 A1111 扩展源 JSON

    Args:
        data (Any):
            已反序列化的扩展源数据

    Returns:
        list[ExtensionIndexItem]: 扩展源条目列表
    """
    if isinstance(data, dict):
        raw_extensions = data.get("extensions", [])
    elif isinstance(data, list):
        raw_extensions = data
    else:
        raw_extensions = []

    items: list[ExtensionIndexItem] = []
    for raw_item in raw_extensions:
        if not isinstance(raw_item, dict):
            continue
        url = _pick_extension_url(raw_item)
        if not url:
            continue
        items.append(
            ExtensionIndexItem(
                name=_pick_extension_name(raw_item),
                url=url,
                description=_pick_extension_description(raw_item),
                tags=_pick_extension_tags(raw_item),
                install_type=str(raw_item.get("install_type") or "git-clone"),
                files=_pick_extension_files(raw_item),
                reference=str(raw_item.get("reference") or ""),
            )
        )
    return items


def parse_comfyui_custom_node_index(data: Any) -> list[ExtensionIndexItem]:
    """
    解析 ComfyUI-Manager 自定义节点列表

    Args:
        data (Any):
            已反序列化的自定义节点列表

    Returns:
        list[ExtensionIndexItem]: 扩展源条目列表
    """
    if isinstance(data, dict):
        raw_extensions = data.get("custom_nodes", [])
    elif isinstance(data, list):
        raw_extensions = data
    else:
        raw_extensions = []

    items: list[ExtensionIndexItem] = []
    for raw_item in raw_extensions:
        if not isinstance(raw_item, dict):
            continue
        files = _pick_extension_files(raw_item)
        reference = str(raw_item.get("reference") or "")
        url = files[0] if files else reference
        if not url:
            continue
        title = raw_item.get("title") or raw_item.get("name") or raw_item.get("id")
        name = str(title).strip() if title else get_repo_name_from_url(reference or url)
        tags = _pick_extension_tags(raw_item)
        author = raw_item.get("author")
        author_name = author.strip() if isinstance(author, str) and author.strip() else ""
        if author_name:
            tags = (*tags, author_name)
        install_type = str(raw_item.get("install_type") or "git-clone")
        items.append(
            ExtensionIndexItem(
                name=name,
                url=url,
                description=_pick_extension_description(raw_item),
                tags=tags,
                install_type=install_type,
                files=files,
                reference=reference,
                author=author_name,
            )
        )
    return items


def fetch_extension_index(
    index_url: str = DEFAULT_EXTENSION_INDEX_URL,
    timeout: int | None = 20,
) -> list[ExtensionIndexItem]:
    """
    下载并解析扩展源列表

    Args:
        index_url (str):
            扩展源地址
        timeout (int | None):
            网络请求超时时间

    Returns:
        list[ExtensionIndexItem]: 扩展源条目列表
    """
    req = urllib.request.Request(index_url, headers={"User-Agent": "SD-WebUI-All-In-One"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    return parse_extension_index(json.loads(payload))


def fetch_comfyui_custom_node_index(index_url: str, timeout: int | None = 20) -> list[ExtensionIndexItem]:
    """
    下载并解析 ComfyUI-Manager 扩展源

    Args:
        index_url (str):
            扩展源地址
        timeout (int | None):
            网络请求超时时间

    Returns:
        list[ExtensionIndexItem]: 扩展源条目列表
    """
    req = urllib.request.Request(index_url, headers={"User-Agent": "SD-WebUI-All-In-One"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    return parse_comfyui_custom_node_index(json.loads(payload))


def _pypi_version_sort_key(
    version: str,
) -> tuple[int, PyWhlVersionComparison | CommonVersionComparison]:
    """构造 PyPI 版本号排序键

    PyPI 发布的版本号遵循 PEP 440, 用 PEP 440 比较器排序才能把 ``1.0.post1`` 排在
    ``1.0`` 之后、把 ``1.0rc1`` 排在 ``1.0`` 之前; 通用比较器无法正确处理这两种后缀.
    镜像源可能返回不符合 PEP 440 的版本号, 这类版本号回退到通用比较器, 并统一排在
    可解析版本号之后, 避免解析异常中断整个版本列表.

    Args:
        version (str):
            版本号字符串

    Returns:
        tuple[int, PyWhlVersionComparison | CommonVersionComparison]:
            排序键. 第 1 项区分可解析与不可解析版本号, 保证两类版本号之间不会
            跨比较器比较.
    """
    if parse_version_component(version) is None:
        return (0, CommonVersionComparison(version))
    return (1, PyWhlVersionComparison(version))


def fetch_pypi_versions(
    package_name: str,
    current_version: str | None = None,
    index_url: str = "https://pypi.org/pypi",
    timeout: int | None = 20,
) -> list[PackageVersionInfo]:
    """
    从 PyPI JSON API 获取软件包版本列表

    Args:
        package_name (str):
            PyPI 软件包名称
        current_version (str | None):
            当前安装版本; 为 None 时从当前运行环境解析已安装版本
        index_url (str):
            PyPI 或 PyPI 镜像源地址
        timeout (int | None):
            网络请求超时时间

    Returns:
        list[PackageVersionInfo]: 软件包版本信息列表, 按版本号从新到旧排序.
            每项的 ``is_prerelease`` 标记该版本是预发布版本还是正式发布版本,
            调用方据此区分发布通道, 无需自行解析版本号字符串.
    """
    # 未显式传入当前版本时按运行环境解析, 否则调用方无法得到 is_current 标记。
    if current_version is None:
        current_version = get_package_version_from_library(package_name)
    base_url = index_url.rstrip("/")
    if base_url.endswith("/simple"):
        base_url = base_url.removesuffix("/simple")
    if "pypi.org/simple" in base_url:
        base_url = base_url.replace("pypi.org/simple", "pypi.org/pypi")
    if base_url.endswith("/pypi"):
        url = f"{base_url}/{package_name}/json"
    elif base_url.endswith("/json"):
        url = base_url
    else:
        url = f"{base_url}/pypi/{package_name}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "SD-WebUI-All-In-One"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    summary = ""
    info = payload.get("info")
    if isinstance(info, dict):
        summary = str(info.get("summary") or "")

    releases = payload.get("releases", {})
    if not isinstance(releases, dict):
        return []

    versions: list[PackageVersionInfo] = []
    for version, files in releases.items():
        upload_time = ""
        if isinstance(files, list) and files:
            first_file = files[0]
            if isinstance(first_file, dict):
                upload_time = str(first_file.get("upload_time") or first_file.get("upload_time_iso_8601") or "")
        versions.append(
            PackageVersionInfo(
                version=str(version),
                upload_time=upload_time,
                summary=summary,
                is_current=version == current_version,
                is_prerelease=is_prerelease_version(str(version)),
            )
        )

    return sorted(versions, key=lambda item: _pypi_version_sort_key(item.version), reverse=True)


def filter_extension_index(
    items: Iterable[ExtensionIndexItem],
    keyword: str,
    tags: Iterable[str] | None = None,
) -> list[ExtensionIndexItem]:
    """
    按关键字和标签过滤扩展源条目

    Args:
        items (Iterable[ExtensionIndexItem]):
            扩展源条目列表
        keyword (str):
            搜索关键字
        tags (Iterable[str] | None):
            标签过滤条件

    Returns:
        list[ExtensionIndexItem]: 过滤后的扩展源条目列表
    """
    keyword = keyword.strip().lower()
    selected_tags = {tag.lower() for tag in tags or []}
    result: list[ExtensionIndexItem] = []
    for item in items:
        haystack = " ".join(
            [
                item.name,
                item.description,
                item.url,
                item.registry_id or "",
                item.registry_version or "",
                item.repository or "",
                item.author,
                " ".join(item.tags),
            ]
        ).lower()
        if keyword and keyword not in haystack:
            continue
        if selected_tags and not selected_tags.intersection({tag.lower() for tag in item.tags}):
            continue
        result.append(item)
    return result


def check_package_update(
    package_name: str,
    display_name: str,
    index_url: str,
    timeout: int | None = 20,
    allow_prerelease: bool = False,
) -> PackageUpdateStatus:
    """检查作为 WebUI 内核安装的 PyPI 包是否有更新。

    默认只把正式发布版本作为更新目标。PyPI 上新发布的预发布版本 (如 ``6.10.0rc1``)
    版本号高于当前正式版本, 若直接取版本列表的第一项会误报 "有更新", 并把预发布
    版本显示成最新版本。

    Args:
        package_name (str): PyPI 包名。
        display_name (str): 内核显示名称。
        index_url (str): PyPI JSON API 或镜像地址。
        timeout (int | None): 请求超时时间。
        allow_prerelease (bool): 是否把预发布版本也作为更新目标, 默认为 ``False``。

    Returns:
        PackageUpdateStatus: PyPI 内核包的详细更新状态。
    """
    current_version = get_package_version_from_library(package_name)
    latest_prerelease: str | None = None
    try:
        versions = fetch_pypi_versions(
            package_name,
            current_version=current_version,
            index_url=index_url,
            timeout=timeout,
        )
        # 版本列表已按版本号从新到旧排序, 取符合发布通道的第一项即为最新版本。
        candidates = versions if allow_prerelease else [item for item in versions if not item.is_prerelease]
        latest_version = candidates[0].version if candidates else None
        newest_prerelease = next((item.version for item in versions if item.is_prerelease), None)
        # 预发布通道只在走在正式通道前面时才值得单独报告。
        if newest_prerelease is not None and (latest_version is None or PyWhlVersionComparison(latest_version) < PyWhlVersionComparison(newest_prerelease)):
            latest_prerelease = newest_prerelease
        if latest_version is not None:
            error = None
        elif versions:
            error = "未获取到 PyPI 正式发布版本"
        else:
            error = "未获取到 PyPI 版本列表"
        has_update = latest_version is not None and (
            current_version is None or PyWhlVersionComparison(current_version) < PyWhlVersionComparison(latest_version)
        )
    except Exception as exc:
        latest_version = None
        has_update = False
        error = str(exc)
    return PackageUpdateStatus(
        name=display_name,
        package_name=package_name,
        installed=current_version is not None,
        current_version=current_version,
        latest_version=latest_version,
        has_update=has_update,
        index_url=index_url,
        error=error,
        latest_prerelease=latest_prerelease,
    )


def check_extension_updates(
    extensions: Iterable[ManagedExtension],
    *,
    fetch: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    registry_version_resolver: Callable[[ManagedExtension], str | None] | None = None,
) -> list[ExtensionUpdateStatus]:
    """检查一组已安装扩展的更新状态。

    Args:
        extensions (Iterable[ManagedExtension]): 已安装扩展信息。
        fetch (bool): 是否先获取 Git 远程引用。
        use_github_mirror (bool): 是否启用 GitHub 镜像源。
        custom_github_mirror (str | list[str] | None): 自定义 GitHub 镜像源。
        registry_version_resolver (Callable[[ManagedExtension], str | None] | None):
            Registry 扩展最新版本解析函数。

    Returns:
        list[ExtensionUpdateStatus]: 每个扩展的详细更新状态。
    """
    result: list[ExtensionUpdateStatus] = []
    for extension in extensions:
        status = ExtensionUpdateStatus(
            name=extension.name,
            path=extension.path,
            enabled=extension.enabled,
            source_type=extension.source_type,
            is_git_repo=extension.is_git_repo,
            url=extension.url,
            branch=extension.branch,
            current_version=extension.registry_version or extension.commit,
            registry_id=extension.registry_id,
        )
        if extension.is_git_repo:
            repository = check_repository_update(
                extension.path,
                fetch=fetch,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
            )
            status.remote_branch = repository.remote_branch
            status.current_version = repository.current_commit
            status.latest_version = repository.remote_commit
            status.ahead = repository.ahead
            status.behind = repository.behind
            status.has_update = repository.has_update
            status.error = repository.error
            status.message = "存在远程更新" if repository.has_update else (repository.error or "已是最新版本")
        elif extension.source_type == "comfy-registry" and registry_version_resolver is not None:
            try:
                status.latest_version = registry_version_resolver(extension)
                if status.latest_version is None:
                    status.error = "未获取到 Registry 最新版本"
                elif status.current_version is None:
                    status.error = "未获取到已安装的 Registry 版本"
                else:
                    status.has_update = status.current_version != status.latest_version
                    status.message = "存在 Registry 更新" if status.has_update else "已是最新版本"
            except Exception as exc:
                status.error = str(exc)
        else:
            status.skipped = True
            status.message = f"扩展来源 '{extension.source_type}' 不支持更新检查"
        result.append(status)
    return result


def check_webui_updates(
    webui_type: str,
    display_name: str,
    webui_path: Path,
    *,
    extension_loader: Callable[[], list[ManagedExtension]] | None = None,
    registry_version_resolver: Callable[[ManagedExtension], str | None] | None = None,
    kernel_package_name: str | None = None,
    options: WebUiUpdateOptions | None = None,
) -> WebUiUpdateStatus:
    """聚合单个 WebUI 的内核、扩展和 PyTorch 更新状态。

    Args:
        webui_type (str): WebUI 类型标识。
        display_name (str): WebUI 显示名称。
        webui_path (Path): WebUI 根目录。
        extension_loader (Callable[[], list[ManagedExtension]] | None): 扩展加载函数。
        registry_version_resolver (Callable[[ManagedExtension], str | None] | None): Registry 最新版本解析函数。
        kernel_package_name (str | None): 使用 PyPI 安装的内核包名；为 None 时检查 Git 内核。
        options (WebUiUpdateOptions | None): 更新检查选项。

    Returns:
        WebUiUpdateStatus: WebUI 的完整结构化更新状态。
    """
    options = options or WebUiUpdateOptions()
    errors: list[str] = []
    kernel: RepositoryUpdateStatus | PackageUpdateStatus | None = None
    if options.include_kernel:
        if kernel_package_name is None:
            kernel = check_repository_update(
                webui_path,
                fetch=options.fetch,
                use_github_mirror=options.use_github_mirror,
                custom_github_mirror=options.custom_github_mirror,
            )
        else:
            kernel = check_package_update(
                kernel_package_name,
                display_name,
                options.pypi_index_url,
                timeout=options.timeout,
                allow_prerelease=options.allow_prerelease,
            )

    pytorch = get_pytorch_update_status() if options.include_pytorch else None
    extensions: list[ExtensionUpdateStatus] = []
    if options.include_extensions and extension_loader is not None:
        try:
            extensions = check_extension_updates(
                extension_loader(),
                fetch=options.fetch,
                use_github_mirror=options.use_github_mirror,
                custom_github_mirror=options.custom_github_mirror,
                registry_version_resolver=registry_version_resolver,
            )
        except Exception as exc:
            errors.append(f"加载扩展失败: {exc}")

    kernel_has_update = bool(kernel and kernel.has_update)
    pytorch_has_update = bool(pytorch and pytorch.has_update)
    extension_update_count = sum(item.has_update for item in extensions)
    skipped_count = sum(item.skipped for item in extensions)
    error_count = len(errors) + int(bool(kernel and kernel.error)) + int(bool(pytorch and pytorch.error)) + sum(bool(item.error) for item in extensions)
    summary = WebUiUpdateSummary(
        has_update=kernel_has_update or pytorch_has_update or extension_update_count > 0,
        kernel_has_update=kernel_has_update,
        pytorch_has_update=pytorch_has_update,
        extension_update_count=extension_update_count,
        checked_extension_count=len(extensions) - skipped_count,
        skipped_count=skipped_count,
        error_count=error_count,
    )
    return WebUiUpdateStatus(
        webui_type=webui_type,
        name=display_name,
        path=webui_path,
        kernel=kernel,
        pytorch=pytorch,
        extensions=extensions,
        extensions_supported=extension_loader is not None,
        summary=summary,
        errors=errors,
    )
