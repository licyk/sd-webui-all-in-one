"""通用版本管理服务"""

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments,too-many-locals

import configparser
import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    clone_repo,
    get_repo_name_from_url,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.file_operations import remove_files
from sd_webui_all_in_one.mirror_manager import GITHUB_MIRROR_LIST
from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.package_analyzer.ver_cmp import CommonVersionComparison


DEFAULT_EXTENSION_INDEX_URL = "https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui-extensions/master/index.json"
"""AUTOMATIC1111 扩展源地址"""


@dataclass(slots=True)
class RepositoryState:
    """
    Git 仓库状态

    Attributes:
        path (Path):
            仓库路径
        is_git_repo (bool):
            是否为 Git 仓库
        name (str):
            仓库名称
        url (str | None):
            当前远程地址
        branch (str | None):
            当前分支
        commit (str | None):
            当前提交 ID
        commit_date (str | None):
            当前提交时间
        message (str | None):
            当前提交信息
        error (str | None):
            仓库探测错误信息
    """

    path: Path
    is_git_repo: bool
    name: str
    url: str | None = None
    branch: str | None = None
    commit: str | None = None
    commit_date: str | None = None
    message: str | None = None
    error: str | None = None


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
    """

    name: str
    url: str
    description: str = ""
    tags: tuple[str, ...] = ()
    install_type: str = "git-clone"
    files: tuple[str, ...] = ()
    reference: str = ""


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
    """

    version: str
    upload_time: str = ""
    summary: str = ""
    is_current: bool = False


def configure_git_env(
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> dict[str, str]:
    """
    应用项目已有 Git 配置并返回环境变量

    Args:
        use_github_mirror (bool | None):
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
    git_config_global = custom_env.get("GIT_CONFIG_GLOBAL")
    if git_config_global:
        os.environ["GIT_CONFIG_GLOBAL"] = git_config_global
    return custom_env


def _git_output(path: Path, *args: str) -> str:
    """
    执行 Git 命令并返回输出

    Args:
        path (Path):
            Git 仓库路径
        *args (str):
            Git 命令参数

    Returns:
        str: 命令输出
    """
    git_exec = git_warpper.get_git_exec()
    output = run_cmd([git_exec.as_posix(), "-C", path.as_posix(), *args], live=False)
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


def _resolve_git_dir(path: Path) -> Path | None:
    """
    解析仓库的 .git 目录

    Args:
        path (Path):
            仓库路径

    Returns:
        Path | None: .git 目录路径, 无法解析时返回 None
    """
    git_path = path / ".git"
    if git_path.is_dir():
        return git_path
    if not git_path.is_file():
        return None

    try:
        content = git_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not content.startswith("gitdir:"):
        return None

    git_dir = Path(content.split(":", 1)[1].strip())
    if not git_dir.is_absolute():
        git_dir = path / git_dir
    return git_dir if git_dir.exists() else None


def _resolve_common_git_dir(git_dir: Path) -> Path:
    """
    解析 Git 公共目录

    Args:
        git_dir (Path):
            .git 目录路径

    Returns:
        Path: Git 公共目录路径
    """
    common_dir_file = git_dir / "commondir"
    if not common_dir_file.is_file():
        return git_dir

    try:
        common_dir = Path(common_dir_file.read_text(encoding="utf-8").strip())
    except OSError:
        return git_dir
    if not common_dir.is_absolute():
        common_dir = git_dir / common_dir
    return common_dir


def _read_repository_branch(git_dir: Path) -> str | None:
    """
    从 HEAD 文件读取当前分支

    Args:
        git_dir (Path):
            .git 目录路径

    Returns:
        str | None: 当前分支, detached HEAD 或读取失败时返回 None
    """
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    ref_prefix = "ref: refs/heads/"
    if head.startswith(ref_prefix):
        return head.removeprefix(ref_prefix)
    return None


def _read_repository_remote_url(git_dir: Path, branch: str | None) -> str | None:
    """
    从 Git 配置读取当前分支远程地址

    Args:
        git_dir (Path):
            .git 目录路径
        branch (str | None):
            当前分支

    Returns:
        str | None: 远程地址
    """
    common_git_dir = _resolve_common_git_dir(git_dir)
    config_path = common_git_dir / "config"
    if not config_path.is_file():
        return None

    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        parser.read(config_path, encoding="utf-8")
    except configparser.Error:
        return None

    remote_name = "origin"
    if branch is not None:
        branch_section = f'branch "{branch}"'
        remote_name = parser.get(branch_section, "remote", fallback=remote_name)

    remote_section = f'remote "{remote_name}"'
    remote_url = parser.get(remote_section, "url", fallback=None)
    if remote_url is not None:
        return remote_url
    return parser.get('remote "origin"', "url", fallback=None)


def _read_repository_head(path: Path) -> tuple[str | None, str | None, str | None]:
    """
    使用一次 Git 命令读取当前提交信息

    Args:
        path (Path):
            仓库路径

    Returns:
        tuple[str | None, str | None, str | None]: 提交 ID、提交时间和提交信息
    """
    try:
        output = _git_output(path, "show", "-s", "--format=%H%x1f%ci%x1f%s", "HEAD")
    except Exception:
        return None, None, None

    parts = output.split("\x1f", 2)
    if len(parts) != 3:
        return None, None, None
    commit, commit_date, message = parts
    return commit or None, commit_date or None, message or None


def inspect_repository(path: Path) -> RepositoryState:
    """
    读取仓库状态

    非 Git 目录不会抛出未处理异常, 而是通过 RepositoryState.error 返回错误信息。

    Args:
        path (Path):
            仓库路径

    Returns:
        RepositoryState: 仓库状态
    """
    path = Path(path)
    state = RepositoryState(path=path, is_git_repo=False, name=path.name)
    if not path.exists():
        state.error = "路径不存在"
        return state

    git_dir = _resolve_git_dir(path)
    if git_dir is None:
        state.error = "非 Git 仓库"
        return state

    state.is_git_repo = True
    state.branch = _read_repository_branch(git_dir)
    state.url = _read_repository_remote_url(git_dir, state.branch)
    state.commit, state.commit_date, state.message = _read_repository_head(path)
    return state


def fetch_repository(
    path: Path,
) -> None:
    """
    拉取远程引用

    Args:
        path (Path):
            Git 仓库路径

    Raises:
        ValueError:
            目标路径不是 Git 仓库
    """
    if not git_warpper.is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")
    _git_output(path, "fetch", "--all", "--prune")


def list_commits(path: Path, limit: int | None = 100) -> list[CommitInfo]:
    """
    列出最近提交

    Args:
        path (Path):
            Git 仓库路径
        limit (int | None):
            最大提交数量, 为 None 时不限制

    Returns:
        list[CommitInfo]: 提交信息列表
    """
    try:
        if not git_warpper.is_git_repo(path):
            return []
    except Exception:
        return []
    current_commit = _safe_git_value(git_warpper.get_current_commit, path)
    format_arg = "--format=%h%x1f%ci%x1f%s"
    args = ["log", format_arg]
    if limit is not None:
        args.extend(["-n", str(limit)])
    output = _git_output(path, *args)
    commits: list[CommitInfo] = []
    for line in output.splitlines():
        parts = line.split("\x1f", 2)
        if len(parts) != 3:
            continue
        commit, date, message = parts
        commits.append(
            CommitInfo(
                commit=commit,
                date=date,
                message=message,
                is_current=bool(current_commit and commit.startswith(current_commit)),
            )
        )
    return commits


def list_branches(path: Path, fetch: bool | None = True) -> list[BranchInfo]:
    """
    列出本地和远程分支

    Args:
        path (Path):
            Git 仓库路径
        fetch (bool | None):
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
    output = _git_output(path, "branch", "--all", "--format=%(refname:short)")
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
    recurse_submodules: bool | None = False,
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
        recurse_submodules (bool | None):
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
        include_files: bool | None = False,
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
            include_files (bool | None):
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
        use_github_mirror: bool | None = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> Path:
        """
        从 Git 地址安装扩展

        Args:
            url (str):
                Git 仓库地址
            use_github_mirror (bool | None):
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
        if isinstance(author, str) and author.strip():
            tags = (*tags, author.strip())
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
            当前安装版本
        index_url (str):
            PyPI 或 PyPI 镜像源地址
        timeout (int | None):
            网络请求超时时间

    Returns:
        list[PackageVersionInfo]: 软件包版本信息列表
    """
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
            )
        )

    return sorted(versions, key=lambda item: CommonVersionComparison(item.version), reverse=True)


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
        haystack = " ".join([item.name, item.description, item.url, " ".join(item.tags)]).lower()
        if keyword and keyword not in haystack:
            continue
        if selected_tags and not selected_tags.intersection({tag.lower() for tag in item.tags}):
            continue
        result.append(item)
    return result
