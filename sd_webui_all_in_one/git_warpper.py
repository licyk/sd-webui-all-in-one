"""Git 调用工具"""

import os
import shutil
import time
from pathlib import Path
from functools import cache
from typing import Literal, overload

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.cmd import DEFAULT_SUBPROCESS_SHELL, run_cmd


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

GIT_CONFIG_ARGS = ["-c", "safe.directory=*", "-c", "core.longpaths=true"]

NON_INTERACTIVE_GIT_ENV = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
"""禁止 Git 与 Git Credential Manager 弹出交互式凭据输入的环境变量, 避免无人值守的拉取操作挂起"""

FETCH_RETRY_DELAY = 2.0
"""拉取失败后重试前的等待时间 (秒)"""


@cache
def get_git_exec() -> Path:
    """检查 Git 命令是否可用并返回 Git 可执行文件地址

    Returns:
        Path:
            当 Git 命令可用时返回 Git 可执行文件路径

    Raises:
        FileNotFoundError:
            当环境中无可用的 Git 命令时
    """
    git_exec = shutil.which("git")
    if git_exec is None:
        raise FileNotFoundError("未找到 Git 命令, 请检查 Git 是否已安装到系统中或者是否已添加到 PATH 变量中")

    return Path(git_exec)


def build_git_command(
    *args: str,
    path: Path | None = None,
) -> list[str]:
    """
    构建 Git 命令

    默认通过运行时配置启用 ``safe.directory=*`` 和 ``core.longpaths=true``。

    Args:
        *args (str):
            Git 参数
        path (Path | None):
            Git 仓库路径

    Returns:
        list[str]: Git 命令参数列表
    """
    command = [get_git_exec().as_posix(), *GIT_CONFIG_ARGS]
    if path is not None:
        command.extend(["-C", path.as_posix()])
    command.extend(args)
    return command


@overload
def run_git(
    *args: str,
    path: Path | None = None,
    custom_env: dict[str, str] | None = None,
    live: Literal[False] = False,
    shell: bool = DEFAULT_SUBPROCESS_SHELL,
    cwd: Path | None = None,
    check: bool = True,
    timeout: float | None = None,
) -> str:
    """
    执行 Git 命令并返回标准输出。

    Args:
        *args (str):
            Git 参数
        path (Path | None):
            Git 仓库路径
        custom_env (dict[str, str] | None):
            自定义环境变量
        live (Literal[False]):
            是否实时输出命令执行日志
        shell (bool):
            是否使用内置 Shell 执行命令
        cwd (Path | None):
            执行进程时的起始路径
        check (bool):
            是否检查进程退出状态
        timeout (float | None):
            子进程执行超时时间（秒）

    Returns:
        str: 命令输出
    """
    ...


@overload
def run_git(
    *args: str,
    path: Path | None = None,
    custom_env: dict[str, str] | None = None,
    live: Literal[True] = True,
    shell: bool = DEFAULT_SUBPROCESS_SHELL,
    cwd: Path | None = None,
    check: bool = True,
    timeout: float | None = None,
) -> str | None:
    """
    执行 Git 命令并实时输出日志。

    Args:
        *args (str):
            Git 参数
        path (Path | None):
            Git 仓库路径
        custom_env (dict[str, str] | None):
            自定义环境变量
        live (Literal[True]):
            是否实时输出命令执行日志
        shell (bool):
            是否使用内置 Shell 执行命令
        cwd (Path | None):
            执行进程时的起始路径
        check (bool):
            是否检查进程退出状态
        timeout (float | None):
            子进程执行超时时间（秒）

    Returns:
        str | None: 命令输出
    """
    ...


@overload
def run_git(
    *args: str,
    path: Path | None = None,
    custom_env: dict[str, str] | None = None,
    live: bool = True,
    shell: bool = DEFAULT_SUBPROCESS_SHELL,
    cwd: Path | None = None,
    check: bool = True,
    timeout: float | None = None,
) -> str | None:
    """
    执行 Git 命令。

    Args:
        *args (str):
            Git 参数
        path (Path | None):
            Git 仓库路径
        custom_env (dict[str, str] | None):
            自定义环境变量
        live (bool):
            是否实时输出命令执行日志
        shell (bool):
            是否使用内置 Shell 执行命令
        cwd (Path | None):
            执行进程时的起始路径
        check (bool):
            是否检查进程退出状态
        timeout (float | None):
            子进程执行超时时间（秒）

    Returns:
        str | None: 命令输出
    """
    ...


def run_git(
    *args: str,
    path: Path | None = None,
    custom_env: dict[str, str] | None = None,
    live: bool = True,
    shell: bool = DEFAULT_SUBPROCESS_SHELL,
    cwd: Path | None = None,
    check: bool = True,
    timeout: float | None = None,
) -> str | None:
    """
    执行 Git 命令

    Args:
        *args (str):
            Git 参数
        path (Path | None):
            Git 仓库路径
        custom_env (dict[str, str] | None):
            自定义环境变量
        live (bool):
            是否实时输出命令执行日志
        shell (bool):
            是否使用内置 Shell 执行命令
        cwd (Path | None):
            执行进程时的起始路径
        check (bool):
            是否检查进程退出状态
        timeout (float | None):
            子进程执行超时时间（秒）

    Returns:
        str | None: 命令输出
    """
    command = build_git_command(*args, path=path)
    if custom_env is None and live is True and shell == DEFAULT_SUBPROCESS_SHELL and cwd is None and check is True and timeout is None:
        return run_cmd(command)
    if custom_env is None and shell == DEFAULT_SUBPROCESS_SHELL and cwd is None and check is True and timeout is None:
        return run_cmd(command, live=live)
    return run_cmd(command, custom_env=custom_env, live=live, shell=shell, cwd=cwd, check=check, timeout=timeout)


def clone(
    repo: str,
    path: Path | None = None,
) -> Path:
    """下载 Git 仓库到本地

    Args:
        repo (str):
            Git 仓库链接
        path (Path | None):
            下载到本地的路径

    Returns:
        Path:
            下载成功时返回路径

    Raises:
        RuntimeError:
            下载 Git 仓库失败时
    """
    if path is None:
        path = Path().cwd()

    try:
        logger.info("下载 %s 到 %s 中", repo, path)
        run_git("clone", "--recurse-submodules", repo, path.as_posix())
        return path
    except RuntimeError as e:
        logger.error("下载 %s 失败: %s", repo, e)
        raise RuntimeError(f"使用 Git 下载 {repo} 时发生错误: {e}") from e


def _read_update_state(
    path: Path,
) -> tuple[str | None, str | None, str | None, bool]:
    """通过一次 git status 读取更新所需的仓库状态

    Args:
        path (Path):
            Git 仓库路径

    Returns:
        (tuple[str | None, str | None, str | None, bool]):
            当前提交, 当前分支 (指针游离时为 None), 上游分支 (未配置时为 None) 和已跟踪文件是否有改动

    Raises:
        RuntimeError:
            执行 git status 失败时
    """
    output = run_git("status", "--porcelain=v2", "--branch", "--untracked-files=no", path=path, live=False)
    commit = branch = upstream = None
    dirty = False
    for line in output.splitlines():
        if line.startswith("# branch.oid "):
            value = line.removeprefix("# branch.oid ").strip()
            commit = None if value == "(initial)" else value
        elif line.startswith("# branch.head "):
            value = line.removeprefix("# branch.head ").strip()
            branch = None if value == "(detached)" else value
        elif line.startswith("# branch.upstream "):
            upstream = line.removeprefix("# branch.upstream ").strip() or None
        elif line and not line.startswith("#"):
            dirty = True
    return commit, branch, upstream, dirty


def non_interactive_env(
    base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """生成禁止 Git 交互式凭据输入的环境变量

    Args:
        base_env (dict[str, str] | None):
            基础环境变量, 为 None 时使用当前进程环境变量

    Returns:
        dict[str, str]:
            附加了 `NON_INTERACTIVE_GIT_ENV` 的环境变量副本
    """
    env = (os.environ if base_env is None else base_env).copy()
    env.update(NON_INTERACTIVE_GIT_ENV)
    return env


def fetch_remote(
    path: Path,
    *args: str,
    live: bool = True,
    custom_env: dict[str, str] | None = None,
    retries: int = 1,
) -> None:
    """以非交互方式执行 git fetch, 失败时重试

    Args:
        path (Path):
            Git 仓库路径
        *args (str):
            git fetch 参数
        live (bool):
            是否实时输出命令执行日志
        custom_env (dict[str, str] | None):
            基础环境变量, 为 None 时使用当前进程环境变量
        retries (int):
            失败后的重试次数

    Raises:
        RuntimeError:
            重试后仍拉取失败时
    """
    env = non_interactive_env(custom_env)
    for attempt in range(retries + 1):
        try:
            run_git("fetch", *args, path=path, custom_env=env, live=live)
            return
        except RuntimeError as e:
            if attempt >= retries:
                raise
            logger.warning("拉取 '%s' 失败, %s 秒后重试 (%s/%s): %s", path, FETCH_RETRY_DELAY, attempt + 1, retries, e)
            time.sleep(FETCH_RETRY_DELAY)


def update(
    path: Path,
    live: bool = True,
    fetch: bool = True,
) -> bool:
    """更新 Git 仓库

    拉取当前分支的上游并重置到上游提交; 当前提交已与上游一致且已跟踪文件无改动时跳过重置。

    Args:
        path (Path):
            Git 仓库路径
        live (bool):
            是否实时输出 Git 命令日志, 并行更新时应关闭以避免输出交错
        fetch (bool):
            是否先拉取远程更新; 刚完成更新检查时可关闭, 直接使用已拉取的远程引用

    Returns:
        bool:
            仓库被重置到新的状态时返回 `True`, 已是最新时返回 `False`

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
        FileNotFoundError:
            未找到 Git 仓库的任何分支时
        RuntimeError:
            更新发生错误时
    """
    logger.info("拉取 %s 更新中", path)
    try:
        commit, branch, upstream, dirty = _read_update_state(path)
    except RuntimeError as e:
        if not is_git_repo(path):
            raise ValueError(f"'{path}' 不是有效的 Git 仓库") from e
        logger.error("读取 '%s' 仓库状态时发生错误: %s", path.as_posix(), e)
        raise RuntimeError(f"更新 '{path}' 时发生错误: {e}") from e

    if branch is None:
        fix_point_offset(path)
        commit, branch, upstream, dirty = _read_update_state(path)
    if branch is None:
        raise FileNotFoundError(f"'{path}' 仓库不存在任何分支")

    try:
        use_submodule = []
        if (path / ".gitmodules").is_file():
            use_submodule = ["--recurse-submodules"]
            run_git("submodule", "init", path=path, live=live)

        if fetch:
            # 配置了上游分支时 git fetch 只拉取该分支所属的远程源
            fetch_remote(path, *([] if upstream else ["--all"]), *use_submodule, live=live)

        target = branch
        target_commit = None
        for ref in [upstream, branch] if upstream else [branch]:
            try:
                target_commit = run_git("rev-parse", "--verify", ref, path=path, live=False).strip()
                target = ref
                break
            except RuntimeError:
                logger.debug("'%s' 仓库中不存在引用 '%s'", path, ref)

        if target_commit is not None and target_commit == commit and not dirty:
            logger.info("'%s' 已是最新版本", path)
            return False

        run_git("reset", "--hard", target, *use_submodule, path=path, live=live)
        logger.info("更新 '%s' 完成: %s -> %s", path, (commit or "")[:7], (target_commit or target)[:7])
        return True
    except RuntimeError as e:
        logger.error("更新 '%s' 时发生错误: %s", path.as_posix(), e)
        raise RuntimeError(f"更新 '{path}' 时发生错误: {e}") from e


def update_submodule(
    path: Path,
) -> None:
    """更新 Git 仓库

    Args:
        path (Path): Git 仓库路径

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
        RuntimeError:
            更新发生错误时
    """
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    logger.info("更新 '%s' 仓库的 Git 子模块中", path)
    try:
        run_git("submodule", "init", path=path)
        run_git("submodule", "update", path=path)
        logger.info("更新 '%s' 仓库的 Git 子模块完成", path)
    except RuntimeError as e:
        logger.info("更新 '%s' 仓库的 Git 子模块时发生错误: %s", path, e)
        raise RuntimeError(f"更新 '{path}' 仓库的 Git 子模块时发生错误: {e}") from e


def check_point_offset(
    path: Path,
) -> bool:
    """检查 Git 仓库的指针是否游离

    Args:
        path (Path):
            Git 仓库路径

    Returns:
        bool:
            当 Git 指针游离时返回`True`

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
    """
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        run_git("symbolic-ref", "HEAD", path=path, live=False)
        return False
    except RuntimeError:
        return True


def get_git_repo_remote_name(
    path: Path,
) -> str | None:
    """获取 Git 仓库的远程源的名称

    Args:
        path (Path):
            Git 仓库路径

    Returns:
        (str | None):
            如果远程源存在则返回主远程源名称或者其他远程源名称, 否则返回 None

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
    """
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        remotes_info = run_git("remote", path=path, live=False).strip().splitlines()
        if not remotes_info:
            return None
        remote_name = "origin" if "origin" in remotes_info else remotes_info[0]
        return remote_name
    except RuntimeError:
        return None


def get_git_repo_current_remote_branch(
    path: Path,
) -> str | None:
    """获取 Git 仓库的当前本地分支对应的远程分支

    通过读取 `branch.<name>.remote` 与 `branch.<name>.merge` 配置解析上游引用,
    不依赖 `@{u}` 语法, 以避免 MSYS2/Cygwin 构建的 Git 在命令行解析时
    将 `{u}` 作为花括号展开, 导致 `@{u}` 变成 `@u` 而无法解析。

    Args:
        path (Path):
            Git 仓库路径

    Returns:
        (str | None):
            如果远程源存在则远程源名称, 否则返回 None

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
    """
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        branch = get_current_branch(path)
        if not branch:
            return None
        remote = run_git("config", f"branch.{branch}.remote", path=path, live=False).strip()
        merge = run_git("config", f"branch.{branch}.merge", path=path, live=False).strip()
        if not remote or not merge:
            return None
        merge_branch = merge.removeprefix("refs/heads/")
        ref = f"refs/remotes/{remote}/{merge_branch}"
        run_git("rev-parse", "--verify", ref, path=path, live=False)
        return run_git("rev-parse", "--abbrev-ref", ref, path=path, live=False).strip()
    except RuntimeError as e:
        logger.debug("'%s' 仓库的当前所在分支无对应的远程分支: %s", path, e)
        return None


def get_git_repo_main_branch(
    path: Path,
) -> tuple[str, str] | tuple[str | None, str | None]:
    """获取 Git 仓库的主分支

    Args:
        path (Path):
            Git 仓库路径

    Returns:
        (tuple[str, str] | tuple[str | None, str |None]):
            远程分支名和远程源的完整路径

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
    """
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    remote_name = get_git_repo_remote_name(path)

    if remote_name is not None:
        try:
            main_branch_path = run_git("symbolic-ref", f"refs/remotes/{remote_name}/HEAD", path=path, live=False)
            main_branch = main_branch_path.removeprefix(f"refs/remotes/{remote_name}/").strip()
            return (main_branch, f"{remote_name}/{main_branch}")
        except RuntimeError:
            logger.debug("未在 '%s' 找到 '%s' 所属的主分支", path, remote_name)
    else:
        logger.debug("'%s' 不存在远程源, 尝试查找本地", path)

    try:
        branches = run_git("for-each-ref", "--format=%(refname:short)", "refs/heads/", path=path, live=False).splitlines()
        branches = [b.strip() for b in branches if b.strip()]
        if "main" in branches:
            return ("main", None)
        if "master" in branches:
            return ("master", None)
        if branches:
            return (branches[0], None)
    except RuntimeError as e:
        logger.warning("获取 '%s' 的本地分支列表失败: %s", path, e)
        return (None, None)
    return (None, None)


def fix_point_offset(
    path: Path,
) -> None:
    """修复 Git 仓库的 Git 指针游离

    Args:
        path (Path):
            Git 仓库路径

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
        FileNotFoundError:
            未找到该 Git 仓库的主分支时
        RuntimeError:
            修复 Git 仓库的指针游离失败时
    """
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        logger.info("修复 %s 的 Git 指针游离中", path)
        run_git("submodule", "init", path=path)
        main_branch, full_main_branch_path = get_git_repo_main_branch(path)

        if main_branch is None:
            logger.error("未找到 '%s' 主分支, 无法修复 Git 指针游离", path)
            raise FileNotFoundError(f"未找到 '{path}' 仓库的主分支, 无法修复 Git 指针游离")

        logger.info("'%s' 主分支: %s, 远程源路径: %s", path.as_posix(), main_branch, full_main_branch_path)
        run_git("checkout", main_branch, path=path)

        if full_main_branch_path is not None:
            run_git("reset", "--recurse-submodules", "--hard", full_main_branch_path, path=path)
        else:
            # 远程分支不存在时则使用本地分支的记录
            run_git("reset", "--recurse-submodules", "--hard", main_branch, path=path)

        logger.info("修复 %s 的 Git 指针游离完成", path)
    except RuntimeError as e:
        logger.error("修复 %s 的 Git 指针游离失败: %s", path, e)
        raise RuntimeError(f"修复 {path} 的 Git 指针游离时发生错误: {e}") from e


def get_current_branch(
    path: Path,
) -> str | None:
    """获取 Git 仓库的当前所处分支

    Args:
        path (Path):
            Git 仓库路径

    Returns:
        (str | None):
            仓库所处分支, 获取失败时返回`None`

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
    """
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        return run_git("branch", "--show-current", path=path, live=False).strip()
    except RuntimeError as e:
        logger.error("获取 %s 当前分支失败: %s", path, e)
        return None


def get_current_branch_remote(
    path: Path,
) -> str | None:
    """获取 Git 仓库的当前分支所属的远程源名称

    Args:
        path (Path):
            Git 仓库路径

    Returns:
        (str | None):
            仓库当前分支所属的远程源名称, 获取失败时返回`None`

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
    """
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        current_branch = get_current_branch(path)
        return run_git("config", f"branch.{current_branch}.remote", path=path, live=False).strip()
    except RuntimeError as e:
        logger.error("获取 %s 当前分支所属的远程源名称失败: %s", path, e)
        return None


def check_local_branch_exists(
    path: Path,
    branch: str,
) -> bool:
    """检查 Git 仓库是否存在某个本地分支

    Args:
        path (Path):
            Git 仓库路径
        branch (str):
            要检查的本地分支

    Returns:
        bool: 分支存在时返回`True`

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时抛出。
    """
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        run_git("show-ref", "--verify", "--quiet", f"refs/heads/{branch}", path=path, live=False)
        return True
    except RuntimeError:
        return False


def get_current_branch_remote_url(
    path: Path,
) -> str | None:
    """获取当前 Git 仓库的所在分支的远程源地址

    Args:
        path (Path):
            Git 仓库路径

    Returns:
        (str | None):
            当前 Git 仓库的所在分支的远程源地址

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
    """
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    custom_env = os.environ.copy()
    custom_env.pop("GIT_CONFIG_GLOBAL", None)

    try:
        current_remote_branch = get_current_branch_remote(path)
        if current_remote_branch is None:
            logger.debug("获取 '%s' 仓库的当前分支所属的远程分支失败", path)
            return None
        else:
            return run_git("remote", "get-url", current_remote_branch, path=path, custom_env=custom_env, live=False).strip()
    except RuntimeError as e:
        logger.debug("获取 '%s' 仓库的当前分支所属的远程源地址失败: %s", path, e)
        return None


def get_current_commit(
    path: Path,
) -> str | None:
    """获取当前 Git 仓库的提交的哈希值

    Args:
        path (Path):
            Git 仓库路径

    Returns:
        (str | None):
            当前 Git 仓库的提交的哈希值

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
    """
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        return run_git("rev-parse", "--short", "HEAD", path=path, live=False).strip()
    except RuntimeError as e:
        logger.debug("获取 '%s' 仓库的提交哈希值失败: %s", path, e)
        return None


def switch_branch(
    path: Path,
    branch: str,
    new_url: str | None = None,
    recurse_submodules: bool = False,
) -> None:
    """切换 Git 仓库的分支和远程源

    Args:
        path (Path):
            Git 仓库路径
        branch (str):
            要切换的分支
        new_url (str | None):
            要切换的远程源
        recurse_submodules (bool):
            是否启用 Git 子模块

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
        RuntimeError:
            切换分支失败时
    """

    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    current_url = get_current_branch_remote_url(path)
    if current_url is None:
        logger.warning("获取 %s 原有的远程源失败", path)

    use_submodules = ["--recurse-submodules"] if recurse_submodules else []
    if new_url is not None:
        logger.info("替换 %s 远程源: %s -> %s", path, current_url, new_url)
        try:
            run_git("remote", "set-url", "origin", new_url, path=path)
        except RuntimeError as e:
            logger.error("替换 %s 远程源失败: %s", path, e)
            raise RuntimeError(f"替换 {path} 远程源发生错误: {e}") from e

    if recurse_submodules:
        try:
            run_git("submodule", "update", "--init", "--recursive", path=path)
        except RuntimeError as e:
            logger.warning("更新 %s 的 Git 子模块信息发生错误: %s", path, e)
    else:
        try:
            run_git("submodule", "deinit", "--all", "-f", path=path)
        except RuntimeError as e:
            logger.warning("更新 %s 的 Git 子模块信息发生错误: %s", path, e)

    logger.info("拉取 %s 远程源更新中", path)
    try:
        run_git("fetch", path=path)
        run_git("submodule", "deinit", "--all", "-f", path=path)
        if not check_local_branch_exists(path, branch):
            run_git("branch", branch, path=path)

        run_git("checkout", branch, "--force", path=path)
        logger.info("应用 %s 的远程源最新内容中", path)
        if recurse_submodules:
            run_git("reset", "--hard", f"origin/{branch}", path=path)
            run_git("submodule", "deinit", "--all", "-f", path=path)
            run_git("submodule", "update", "--init", "--recursive", path=path)

        run_git("reset", "--hard", f"origin/{branch}", *use_submodules, path=path)
        logger.info("切换 %s 分支到 %s 完成", path, branch)
    except RuntimeError as e:
        logger.error("切换 %s 分支到 %s 失败: %s", path, branch, e)
        logger.warning("回退分支切换")
        try:
            if current_url:
                run_git("remote", "set-url", "origin", current_url, path=path)
            if recurse_submodules:
                run_git("submodule", "deinit", "--all", "-f", path=path)

            else:
                run_git("submodule", "update", "--init", "--recursive", path=path)
        except RuntimeError as e1:
            logger.error("回退分支切换失败: %s", e1)
        raise RuntimeError(f"切换 '{path}' 的分支发生错误: {e}") from e


def switch_commit(
    path: Path,
    commit: str,
) -> None:
    """切换 Git 仓库到指定提交记录上

    Args:
        path (Path):
            Git 仓库路径
        commit (str):
            Git 仓库提交记录

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
        RuntimeError:
            切换 Git 仓库的版本失败时
    """
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    logger.info("切换 %s 的 Git 指针到 %s 版本", path, commit)
    try:
        run_git("reset", "--hard", commit, path=path)
    except RuntimeError as e:
        logger.error("切换 %s 的 Git 指针到 %s 版本时失败: %s", path, commit, e)
        raise RuntimeError(f"切换 '{path}' 的 Git 指针到 '{commit}' 版本时失败: {e}") from e


def is_git_repo(
    path: Path,
) -> bool:
    """检查该路径是否为 Git 仓库路径

    Args:
        path (Path):
            要检查的路径

    Returns:
        bool:
            当该路径为 Git 仓库时返回`True`
    """
    try:
        run_git("rev-parse", "--git-dir", path=path, live=False)
        return True
    except RuntimeError:
        return False


def set_git_config(
    username: str | None = None,
    email: str | None = None,
) -> None:
    """配置 Git 信息

    Args:
        username (str | None): 用户名
        email (str | None): 邮箱地址

    Raises:
        RuntimeError: 配置失败时
    """
    logger.info("配置 Git 信息中")
    try:
        if username is not None:
            run_git("config", "--global", "user.name", username)
        if email is not None:
            run_git("config", "--global", "user.email", email)
    except RuntimeError as e:
        logger.error("配置 Git 信息时发生错误: %s", e)
        raise RuntimeError(f"配置 Git 信息时发生错误: {e}") from e
