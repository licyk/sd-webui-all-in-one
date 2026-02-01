"""Git 调用工具"""

import os
import shutil
from pathlib import Path
from functools import cache

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR
from sd_webui_all_in_one.cmd import run_cmd


logger = get_logger(
    name="Git Warpper",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


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
    git_exec = get_git_exec()

    if path is None:
        path = Path().cwd()

    try:
        logger.info("下载 %s 到 %s 中", repo, path)
        run_cmd([git_exec.as_posix(), "clone", "--recurse-submodules", repo, path.as_posix()])
        return path
    except RuntimeError as e:
        logger.error("下载 %s 失败: %s", repo, e)
        raise RuntimeError(f"使用 Git 下载 {repo} 时发生错误: {e}") from e


def update(
    path: Path,
) -> None:
    """更新 Git 仓库

    Args:
        path (Path): Git 仓库路径

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
        FileNotFoundError:
            未找到 Git 仓库的任何分支时
        RuntimeError:
            更新发生错误时
    """
    git_exec = get_git_exec()
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    use_submodule = []
    logger.info("拉取 %s 更新中", path)
    if check_point_offset(path):
        fix_point_offset(path)

    try:
        if run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "submodule", "status"], live=False).strip() != "":
            use_submodule = ["--recurse-submodules"]
            run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "submodule", "init"])

        run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "fetch", "--all"] + use_submodule)
        branch = get_current_branch(path)
        remote_branch = get_git_repo_current_remote_branch(path)

        if remote_branch is not None:
            origin_branch = remote_branch
        elif branch is not None:
            origin_branch = branch
        else:
            raise FileNotFoundError(f"'{path}' 仓库不存在任何分支")

        run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "reset", "--hard", origin_branch] + use_submodule)
        logger.info("更新 '%s' 完成", path)
    except RuntimeError as e:
        logger.error("更新 '%s' 时发生错误: %s", path.as_posix(), e)
        raise RuntimeError(f"更新 '{path}' 时发生错误: {e}") from e


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
    git_exec = get_git_exec()
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "symbolic-ref", "HEAD"], live=False)
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
    git_exec = get_git_exec()
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        remotes_info = run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "remote"], live=False).strip().splitlines()
        if not remotes_info:
            return None
        remote_name = "origin" if "origin" in remotes_info else remotes_info[0]
        return remote_name
    except RuntimeError:
        return None


def get_git_repo_current_remote_branch(
    path: Path,
) -> None:
    """获取 Git 仓库的当前本地分支对应的远程分支

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
    git_exec = get_git_exec()
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        return run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "rev-parse", "--abbrev-ref", "--symbolic-full-name", r"'@{u}'"], live=False).strip()
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
    git_exec = get_git_exec()
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    remote_name = get_git_repo_remote_name(path)

    if remote_name is not None:
        try:
            main_branch_path = run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "symbolic-ref", f"refs/remotes/{remote_name}/HEAD"], live=False)
            main_branch = main_branch_path.removeprefix(f"refs/remotes/{remote_name}/").strip()
            return (main_branch, f"{remote_name}/{main_branch}")
        except RuntimeError:
            logger.debug("未在 '%s' 找到 '%s' 所属的主分支", path, remote_name)
    else:
        logger.debug("'%s' 不存在远程源, 尝试查找本地")

    try:
        branches = run_cmd([git_exec.as_posix(), "-C", path.as_posix(), " for-each-ref", "--format=%(refname:short)", "refs/heads/"], live=False).splitlines()
        branches = [b.strip() for b in branches if b.strip()]
        if "main" in branches:
            return ("main", None)
        if "master" in branches:
            return ("master", None)
        if branches:
            return (branches[0], None)
    except RuntimeError:
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
    git_exec = get_git_exec()
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        logger.info("修复 %s 的 Git 指针游离中", path)
        run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "submodule", "init"])
        main_branch, full_main_branch_path = get_git_repo_main_branch(path)

        if main_branch is None:
            logger.error("未找到 '%s' 主分支, 无法修复 Git 指针游离", path)
            raise FileNotFoundError(f"未找到 '{path}' 仓库的主分支, 无法修复 Git 指针游离")

        logger.info("'%s' 主分支: %s, 远程源路径: %s", path.as_posix(), main_branch, full_main_branch_path)
        run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "checkout", main_branch])

        if full_main_branch_path is not None:
            run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "reset", "--recurse-submodules", "--hard", full_main_branch_path])
        else:
            # 远程分支不存在时则使用本地分支的记录
            run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "reset", "--recurse-submodules", "--hard", main_branch])

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
    git_exec = get_git_exec()
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        return run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "branch", "--show-current"], live=False).strip()
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
    git_exec = get_git_exec()
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        current_branch = get_current_branch(path)
        return run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "config", f"branch.{current_branch}.remote"], live=False).strip()
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
    """
    git_exec = get_git_exec()
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], live=False)
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
    git_exec = get_git_exec()
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
            return run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "remote", "get-url", current_remote_branch], custom_env=custom_env, live=False).strip()
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
    git_exec = get_git_exec()
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    try:
        return run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "rev-parse", "--short", "HEAD"], live=False).strip()
    except RuntimeError as e:
        logger.debug("获取 '%s' 仓库的提交哈希值失败: %s", path, e)
        return None


def switch_branch(
    path: Path,
    branch: str,
    new_url: str | None = None,
    recurse_submodules: bool | None = False,
) -> None:
    """切换 Git 仓库的分支和远程源

    Args:
        path (Path):
            Git 仓库路径
        branch (str):
            要切换的分支
        new_url (str | None):
            要切换的远程源
        recurse_submodules (bool | None):
            是否启用 Git 子模块

    Raises:
        ValueError:
            所指路径不是有效的 Git 仓库时
        RuntimeError:
            切换分支失败时
    """

    git_exec = get_git_exec()
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    custom_env = os.environ.copy()
    custom_env.pop("GIT_CONFIG_GLOBAL", None)

    current_url = get_current_branch_remote_url(path)
    if current_url is None:
        logger.warning("获取 %s 原有的远程源失败", path)

    use_submodules = ["--recurse-submodules"] if recurse_submodules else []
    if new_url is not None:
        logger.info("替换 %s 远程源: %s -> %s", path, current_url, new_url)
        try:
            run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "remote", "set-url", "origin", new_url])
        except RuntimeError as e:
            logger.error("替换 %s 远程源失败: %s", path, e)
            raise RuntimeError(f"替换 {path} 远程源发生错误: {e}") from e

    if recurse_submodules:
        try:
            run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "submodule", "update", "--init", "--recursive"])
        except RuntimeError as e:
            logger.warning("更新 %s 的 Git 子模块信息发生错误: %s", path, e)
    else:
        try:
            run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "submodule", "deinit", "--all", "-f"])
        except RuntimeError as e:
            logger.warning("更新 %s 的 Git 子模块信息发生错误: %s", path, e)

    logger.info("拉取 %s 远程源更新中", path)
    try:
        run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "fetch"])
        run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "submodule", "deinit", "--all", "-f"])
        if not check_local_branch_exists(path, branch):
            run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "branch", branch])

        run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "checkout", branch, "--force"])
        logger.info("应用 %s 的远程源最新内容中", path)
        if recurse_submodules:
            run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "reset", "--hard", f"origin/{branch}"])
            run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "submodule", "deinit", "--all", "-f"])
            run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "submodule", "update", "--init", "--recursive"])

        run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "reset", "--hard", f"origin/{branch}"] + use_submodules)
        logger.info("切换 %s 分支到 %s 完成", path, branch)
    except RuntimeError as e:
        logger.error("切换 %s 分支到 %s 失败: %s", path, branch, e)
        logger.warning("回退分支切换")
        try:
            if current_url:
                run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "remote", "set-url", "origin", current_url])
            if recurse_submodules:
                run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "submodule", "deinit", "--all", "-f"])

            else:
                run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "submodule", "update", "--init", "--recursive"])
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
    git_exec = get_git_exec()
    if not is_git_repo(path):
        raise ValueError(f"'{path}' 不是有效的 Git 仓库")

    logger.info("切换 %s 的 Git 指针到 %s 版本", path, commit)
    try:
        run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "reset", "--hard", commit])
    except RuntimeError as e:
        logger.error("切换 %s 的 Git 指针到 %s 版本时失败: %s", path, commit, e)
        raise RuntimeError(f"切换 '{path}' 的 Git 指针到 '{commit}' 版本时失败: {e}") from e


def is_git_repo(path: Path) -> bool:
    """检查该路径是否为 Git 仓库路径

    Args:
        path (Path):
            要检查的路径

    Returns:
        bool:
            当该路径为 Git 仓库时返回`True`
    """
    git_exec = get_git_exec()
    try:
        run_cmd([git_exec.as_posix(), "-C", path.as_posix(), "rev-parse", "--git-dir"], live=False)
        return True
    except RuntimeError:
        return False


def set_git_config(
    username: str | None = None,
    email: str | None = None,
) -> bool:
    """配置 Git 信息

    Args:
        username (str | None): 用户名
        email (str | None): 邮箱地址

    Raises:
        RuntimeError: 配置失败时
    """
    git_exec = get_git_exec()
    logger.info("配置 Git 信息中")
    try:
        if username is not None:
            run_cmd([git_exec.as_posix(), "config", "--global", "user.name", username])
        if email is not None:
            run_cmd([git_exec.as_posix(), "config", "--global", "user.email", email])
    except RuntimeError as e:
        logger.error("配置 Git 信息时发生错误: %s", e)
        raise RuntimeError(f"配置 Git 信息时发生错误: {e}") from e
