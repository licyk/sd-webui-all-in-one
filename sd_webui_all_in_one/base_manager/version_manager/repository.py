"""Git 仓库版本操作。"""

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments,too-many-locals

import os
from pathlib import Path
from typing import (
    Callable,
    Literal,
)

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
)
from sd_webui_all_in_one.base_manager.repository_inspector import (
    inspect_repository,
    read_branch_upstream,
    read_ref_commit,
    read_repository_tracking_state,
    run_git_output,
)
from sd_webui_all_in_one.mirror_manager import GITHUB_MIRROR_LIST

from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


DEFAULT_EXTENSION_INDEX_URL = "https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui-extensions/master/index.json"
"""AUTOMATIC1111 扩展源地址"""


ExtensionSourceType = Literal["git", "comfy-registry", "file", "unknown"]
"""扩展安装来源类型"""


CHECK_FETCH_TIMEOUT = 300.0
"""检查更新时单次拉取的超时时间 (秒), 防止连接挂起导致检查无法结束"""

CHECK_FETCH_GIT_ENV = {"GIT_HTTP_LOW_SPEED_LIMIT": "1000", "GIT_HTTP_LOW_SPEED_TIME": "20"}
"""检查更新时的 HTTP 低速中止阈值: 连续 20 秒低于 1000 字节/秒时中止拉取, 避免停滞的镜像连接长时间占用线程"""


from sd_webui_all_in_one.base_manager.version_manager.models import BranchInfo, CommitInfo, RepositoryUpdateStatus


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
    logger.debug("配置 Git 环境变量, 启用镜像源: %s", use_github_mirror)
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
    logger.debug("执行 Git 命令: git %s (路径: %s)", " ".join(args), path)
    output = git_warpper.run_git(*args, path=path, custom_env=custom_env, live=False)
    logger.debug("Git 命令输出: %s", output)
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
    except Exception as exc:
        logger.error("读取 Git 字段失败: %s", exc)
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
        logger.error("目标路径不是有效的 Git 仓库, 无法拉取远程引用: %s", path)
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")
    logger.info("开始拉取远程引用: %s", path)
    custom_env = configure_git_env(use_github_mirror=use_github_mirror, custom_github_mirror=custom_github_mirror) if use_github_mirror else None
    git_warpper.fetch_remote(path, "--all", "--prune", live=False, custom_env=custom_env)
    logger.info("拉取远程引用完成: %s", path)


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
        logger.debug("解析到远程跟踪分支: %s", remote_branch)
        return remote_branch
    if branch:
        fallback_ref = f"origin/{branch}"
        logger.warning("获取远程跟踪分支失败, 回退到引用 %s: %s", fallback_ref, path)
        try:
            _run_git_output(path, "rev-parse", "--verify", fallback_ref)
            return fallback_ref
        except RuntimeError:
            logger.warning("回退引用 %s 不存在: %s", fallback_ref, path)
            return None
    logger.debug("未找到用于更新检查的远程引用: %s", path)
    return None


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
        logger.warning("解析领先/落后提交数失败, 原始输出: %s", output)
        return 0, 0
    logger.debug("与 %s 的领先/落后提交数: 领先 %s, 落后 %s", remote_ref, parts[0], parts[1])
    return int(parts[0]), int(parts[1])


def _upstream_fetch_args(path: Path, branch: str | None) -> list[str] | None:
    """
    生成检查更新时仅拉取当前分支上游所需的 git fetch 参数

    Args:
        path (Path):
            Git 仓库路径
        branch (str | None):
            当前分支

    Returns:
        list[str] | None: git fetch 参数, 无需联网拉取 (detached HEAD 或上游为本地分支) 时返回 None
    """
    if branch is None:
        logger.debug("仓库处于 detached HEAD 状态, 跳过拉取: %s", path)
        return None
    upstream = read_branch_upstream(path, branch)
    if upstream is None:
        # 未配置上游时沿用 origin/<分支> 作为更新检查的远程引用
        return ["--no-tags", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}"]
    if upstream.remote == ".":
        logger.debug("上游为本地分支, 跳过拉取: %s", path)
        return None
    if upstream.tracking_ref is None:
        # 远程源使用自定义 refspec, 交给 Git 按配置更新远程跟踪引用
        return ["--no-tags", upstream.remote]
    return ["--no-tags", upstream.remote, f"+{upstream.merge}:{upstream.tracking_ref}"]


def fetch_repository_upstream(
    path: Path,
    branch: str | None,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """
    仅拉取当前分支的上游分支, 用于检查更新

    相比拉取全部远程源的分支和标签, 只需协商一个引用; 同时限制拉取时间, 避免连接挂起。

    Args:
        path (Path):
            Git 仓库路径
        branch (str | None):
            当前分支
        use_github_mirror (bool):
            是否启用 GitHub 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源

    Raises:
        RuntimeError:
            拉取失败或超时时
    """
    args = _upstream_fetch_args(path, branch)
    if args is None:
        return
    custom_env = configure_git_env(use_github_mirror=use_github_mirror, custom_github_mirror=custom_github_mirror) if use_github_mirror else os.environ.copy()
    for key, value in CHECK_FETCH_GIT_ENV.items():
        custom_env.setdefault(key, value)
    logger.debug("拉取上游分支: %s (git fetch %s)", path, " ".join(args))
    git_warpper.fetch_remote(path, *args, live=False, custom_env=custom_env, timeout=CHECK_FETCH_TIMEOUT)


def check_repository_update(
    path: Path,
    fetch: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> RepositoryUpdateStatus:
    """
    检查 Git 仓库是否存在远程更新

    只拉取当前分支的上游, 然后通过一次 git status 读取上游、领先/落后提交数和工作区状态,
    远程提交直接从引用文件读取。正常情况下每个仓库只需一次拉取和一次本地 Git 调用。

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
    logger.info("检查仓库更新中: %s", path)
    state = inspect_repository(path, details=False)
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
        logger.warning("仓库 '%s' 不是 Git 仓库, 跳过更新检查", path)
        return status

    try:
        if fetch:
            fetch_repository_upstream(path, state.branch, use_github_mirror=use_github_mirror, custom_github_mirror=custom_github_mirror)
        tracking = read_repository_tracking_state(path)
        status.is_dirty = tracking.dirty
        status.current_commit = tracking.commit or status.current_commit
        if tracking.upstream is not None and tracking.upstream_exists:
            status.remote_branch = tracking.upstream
            status.ahead, status.behind = tracking.ahead, tracking.behind
        else:
            status.remote_branch = _resolve_update_remote_ref(path, tracking.branch) if tracking.branch is not None else None
            if status.remote_branch is None:
                status.error = "未找到远程跟踪分支"
                logger.warning("未找到远程跟踪分支, 跳过更新检查: %s", path)
                return status
            status.ahead, status.behind = _read_ahead_behind(path, status.remote_branch)
        status.remote_commit = read_ref_commit(
            path,
            f"refs/remotes/{status.remote_branch}",
            f"refs/heads/{status.remote_branch}",
        ) or _run_git_output(path, "rev-parse", "--verify", status.remote_branch)
        status.has_update = status.behind > 0
        status.error = None
        logger.info("仓库更新检查完成: %s, 当前提交 %s, 远程提交 %s, 是否有更新: %s", path, status.current_commit, status.remote_commit, status.has_update)
    except Exception as exc:
        status.error = str(exc)
        logger.error("检查仓库更新失败: %s", exc)
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
            是否先拉取远程引用, 以确保上游引用指向最新的远程提交

    Returns:
        list[CommitInfo]: 提交信息列表
    """
    logger.info("获取提交列表中: %s", path)
    if not git_warpper.is_git_repo(path):
        logger.warning("路径不是 Git 仓库, 返回空提交列表: %s", path)
        return []
    if fetch:
        try:
            fetch_repository(path)
        except (RuntimeError, OSError) as exc:
            logger.warning("拉取远程引用失败, 继续获取提交列表: %s", exc)
    current_commit = _safe_git_value(git_warpper.get_current_commit, path)
    current_branch = _safe_git_value(git_warpper.get_current_branch, path)
    upstream_ref = _resolve_update_remote_ref(path, current_branch)
    format_arg = "--format=%H%x1f%h%x1f%ci%x1f%an%x1f%at%x1f%D%x1f%s"
    if upstream_ref:
        args = ["log", "HEAD", upstream_ref, format_arg]
        if limit is not None:
            args.extend(["-n", str(limit)])
        try:
            output = run_git_output(path, *args)
        except RuntimeError:
            logger.warning("获取上游引用 %s 相关提交失败, 回退到仅获取本地提交: %s", upstream_ref, path)
            args = ["log", "HEAD", format_arg]
            if limit is not None:
                args.extend(["-n", str(limit)])
            output = run_git_output(path, *args)
    else:
        args = ["log", "HEAD", format_arg]
        if limit is not None:
            args.extend(["-n", str(limit)])
        output = run_git_output(path, *args)
    commits: list[CommitInfo] = []
    for line in output.splitlines():
        parts = line.split("\x1f", 6)
        if len(parts) != 7:
            logger.warning("解析提交行失败, 跳过: %s", line)
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
        logger.debug("解析到提交: %s %s", short_commit, message)
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
    logger.info("获取提交列表完成: %s, 共 %s 条", path, len(commits))
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
    logger.info("获取分支列表中: %s", path)
    if not git_warpper.is_git_repo(path):
        logger.warning("路径不是 Git 仓库, 返回空分支列表: %s", path)
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
        logger.debug("解析到分支: %s (远程: %s)", display_name, is_remote)
        branches[display_name] = BranchInfo(
            name=display_name,
            is_current=display_name == current_branch,
            is_remote=is_remote,
        )
    logger.info("获取分支列表完成: %s, 共 %s 个分支", path, len(branches))
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
    logger.info("切换仓库分支中: %s -> %s", path, branch)
    fetch_repository(path)
    git_warpper.switch_branch(
        path=path,
        branch=branch,
        new_url=new_url,
        recurse_submodules=recurse_submodules,
    )
    logger.info("切换仓库分支完成: %s -> %s", path, branch)


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
    logger.info("切换仓库到指定提交: %s -> %s", path, commit)
    git_warpper.switch_commit(path=path, commit=commit)
    logger.info("切换仓库到指定提交完成: %s -> %s", path, commit)


def update_repository(
    path: Path,
) -> bool:
    """
    更新仓库

    Args:
        path (Path):
            Git 仓库路径

    Returns:
        bool: 仓库发生更新时返回 True, 已是最新时返回 False
    """
    logger.info("更新仓库中: %s", path)
    updated = git_warpper.update(path)
    logger.info("更新仓库完成: %s", path)
    return updated
