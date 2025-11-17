"""Git 调用工具"""

import os
import traceback
from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR
from sd_webui_all_in_one.cmd import run_cmd


logger = get_logger(
    name="Git Warpper",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def clone(
    repo: str,
    path: Path | str | None = None,
) -> Path | None:
    """下载 Git 仓库到本地

    Args:
        repo (str): Git 仓库链接
        path (Path | str | None): 下载到本地的路径
    Returns:
        (Path | None): 下载成功时返回路径, 否则返回`None`
    """
    if path is None:
        path = os.getcwd()

    path = Path(path) if not isinstance(path, Path) and path is not None else path

    try:
        logger.info("下载 %s 到 %s 中", repo, path)
        run_cmd(["git", "clone", "--recurse-submodules", repo, path.as_posix()])
        return path
    except Exception as e:
        logger.error("下载 %s 失败: %s", repo, e)
        return None


def update(path: Path | str) -> bool:
    """更新 Git 仓库

    Args:
        path (Path | str): Git 仓库路径
    Returns:
        bool: 更新 Git 仓库结果
    """
    path = Path(path) if not isinstance(path, Path) and path is not None else path
    use_submodule = []
    try:
        logger.info("拉取 %s 更新中", path)
        if check_point_offset(path):
            if fix_point_offset(path):
                logger.error("更新 %s 失败", path)
                return False

        if (
            len(
                run_cmd(
                    ["git", "-C", path.as_posix(), "submodule", "status"],
                    live=False,
                ).strip()
            )
            != 0
        ):
            use_submodule = ["--recurse-submodules"]
            run_cmd(["git", "-C", path.as_posix(), "submodule", "init"])

        run_cmd(["git", "-C", path.as_posix(), "fetch", "--all"] + use_submodule)
        branch = get_current_branch(path)
        ref = run_cmd(
            ["git", "-C", path.as_posix(), "symbolic-ref", "--quiet", "HEAD"],
            live=False,
        )

        if check_repo_on_origin_remote(path):
            origin_branch = f"origin/{branch}"
        else:
            origin_branch = str.replace(ref, "refs/heads/", "", 1)
            try:
                run_cmd(
                    [
                        "git",
                        "-C",
                        path.as_posix(),
                        "config",
                        "--get",
                        f"branch.{origin_branch}.remote",
                    ],
                    live=False,
                )
                origin_branch = run_cmd(
                    [
                        "git",
                        "-C",
                        path.as_posix(),
                        "rev-parse",
                        "--abbrev-ref",
                        f"{origin_branch}@{{upstream}}",
                    ],
                    live=False,
                )
            except Exception as _:
                pass
        run_cmd(["git", "-C", path.as_posix(), "reset", "--hard", origin_branch] + use_submodule)
        logger.info("更新 %s 完成", path)
        return True
    except Exception as e:
        logger.error("更新 %s 时发生错误: %s", path.as_posix(), e)
        return False


def check_point_offset(path: Path | str) -> bool:
    """检查 Git 仓库的指针是否游离

    Args:
        path (Path | str): Git 仓库路径
    Returns:
        bool: 当 Git 指针游离时返回`True`
    """
    path = Path(path) if not isinstance(path, Path) and path is not None else path
    try:
        run_cmd(["git", "-C", path.as_posix(), "symbolic-ref", "HEAD"], live=False)
        return False
    except Exception as _:
        return True


def fix_point_offset(path: Path | str) -> bool:
    """修复 Git 仓库的 Git 指针游离

    Args:
        path (Path | str): Git 仓库路径
    Returns:
        bool: 修复结果
    """
    path = Path(path) if not isinstance(path, Path) and path is not None else path
    try:
        logger.info("修复 %s 的 Git 指针游离中", path)
        # run_cmd(["git", "-C", path.as_posix(), "remote", "prune", "origin"])
        run_cmd(["git", "-C", path.as_posix(), "submodule", "init"])
        branch_info = run_cmd(["git", "-C", path.as_posix(), "branch", "-a"], live=False)
        main_branch = None
        for info in branch_info.split("\n"):
            if "/HEAD" in info:
                main_branch = info.split(" -> ").pop().strip().split("/").pop()
                break
        if main_branch is None:
            logger.error("未找到 %s 主分支, 无法修复 Git 指针游离", path)
            return False
        logger.info("%s 主分支: %s", path.as_posix(), main_branch)
        run_cmd(["git", "-C", path.as_posix(), "checkout", main_branch])
        run_cmd(
            [
                "git",
                "-C",
                path.as_posix(),
                "reset",
                "--recurse-submodules",
                "--hard",
                f"origin/{main_branch}",
            ]
        )
        logger.info("修复 %s 的 Git 指针游离完成", path)
        return True
    except Exception as e:
        logger.error("修复 %s 的 Git 指针游离失败: %s", path, e)
        traceback.print_exc()
        return False


def get_current_branch(path: Path | str) -> str | None:
    """获取 Git 仓库的当前所处分支

    Args:
        path (Path | str): Git 仓库路径
    Returns:
        (str | None): 仓库所处分支, 获取失败时返回`None`
    """
    path = Path(path) if not isinstance(path, Path) and path is not None else path
    try:
        return run_cmd(["git", "-C", path.as_posix(), "branch", "--show-current"], live=False).strip()
    except Exception as e:
        logger.error("获取 %s 当前分支失败: %s", path, e)
        return None


def check_repo_on_origin_remote(path: Path | str) -> bool:
    """检查 Git 仓库的远程源是否在 origin

    Args:
        path (Path | str): Git 仓库路径
    Returns:
        bool: 远程源在 origin 时返回`True`
    """
    path = Path(path) if not isinstance(path, Path) and path is not None else path
    try:
        current_branch = get_current_branch(path)
        run_cmd(
            [
                "git",
                "-C",
                path.as_posix(),
                "show-ref",
                "--verify",
                "--quiet",
                f"refs/remotes/origin/{current_branch}",
            ],
            live=False,
        )
        return True
    except Exception as _:
        return False


def check_local_branch_exists(
    path: Path | str,
    branch: str,
) -> bool:
    """检查 Git 仓库是否存在某个本地分支

    Args:
        path (Path | str): Git 仓库路径
        branch (str): 要检查的本地分支
    Returns:
        bool: 分支存在时返回`True`
    """
    path = Path(path) if not isinstance(path, Path) and path is not None else path
    try:
        run_cmd(
            [
                "git",
                "-C",
                path.as_posix(),
                "show-ref",
                "--verify",
                "--quiet",
                f"refs/heads/{branch}",
            ],
            live=False,
        )
        return True
    except Exception as _:
        return False


def switch_branch(
    path: Path | str,
    branch: str,
    new_url: str | None = None,
    recurse_submodules: bool | None = False,
) -> bool:
    """切换 Git 仓库的分支和远程源

    Args:
        path (Path | str): Git 仓库路径
        branch (str): 要切换的分支
        new_url (str | None): 要切换的远程源
        recurse_submodules (bool | None): 是否启用 Git 子模块
    Returns:
        bool: 切换分支结果
    """
    path = Path(path) if not isinstance(path, Path) and path is not None else path
    custom_env = os.environ.copy()
    custom_env.pop("GIT_CONFIG_GLOBAL", None)
    try:
        current_url = run_cmd(
            ["git", "-C", path.as_posix(), "remote", "get-url", "origin"],
            custom_env=custom_env,
            live=False,
        )
    except Exception as e:
        current_url = "None"
        logger.warning("获取 %s 原有的远程源失败: %s", path, e)

    use_submodules = ["--recurse-submodules"] if recurse_submodules else []
    if new_url is not None:
        logger.info("替换 %s 远程源: %s -> %s", path, current_url, new_url)
        try:
            run_cmd(
                [
                    "git",
                    "-C",
                    path.as_posix(),
                    "remote",
                    "set-url",
                    "origin",
                    new_url,
                ]
            )
        except Exception as e:
            logger.error("替换 %s 远程源失败: %s", path, e)
            return False

    if recurse_submodules:
        try:
            run_cmd(
                [
                    "git",
                    "-C",
                    path.as_posix(),
                    "submodule",
                    "update",
                    "--init",
                    "--recursive",
                ]
            )
        except Exception as e:
            logger.warning("更新 %s 的 Git 子模块信息发生错误: %s", path, e)
    else:
        try:
            run_cmd(["git", "-C", path.as_posix(), "submodule", "deinit", "--all", "-f"])
        except Exception as e:
            logger.warning("更新 %s 的 Git 子模块信息发生错误: %s", path, e)

    logger.info("拉取 %s 远程源更新中", path)
    try:
        run_cmd(["git", "-C", path.as_posix(), "fetch"])
        run_cmd(["git", "-C", path.as_posix(), "submodule", "deinit", "--all", "-f"])
        if not check_local_branch_exists(path, branch):
            run_cmd(["git", "-C", path.as_posix(), "branch", branch])

        run_cmd(["git", "-C", path.as_posix(), "checkout", branch, "--force"])
        logger.info("应用 %s 的远程源最新内容中", path)
        if recurse_submodules:
            run_cmd(
                [
                    "git",
                    "-C",
                    path.as_posix(),
                    "reset",
                    "--hard",
                    f"origin/{branch}",
                ]
            )
            run_cmd(["git", "-C", path.as_posix(), "submodule", "deinit", "--all", "-f"])
            run_cmd(
                [
                    "git",
                    "-C",
                    path.as_posix(),
                    "submodule",
                    "update",
                    "--init",
                    "--recursive",
                ]
            )

        run_cmd(["git", "-C", path.as_posix(), "reset", "--hard", f"origin/{branch}"] + use_submodules)
        logger.info("切换 %s 分支到 %s 完成", path, branch)
        return True
    except Exception as e:
        logger.error("切换 %s 分支到 %s 失败: %s", path, branch, e)
        logger.warning("回退分支切换")
        try:
            run_cmd(
                [
                    "git",
                    "-C",
                    path.as_posix(),
                    "remote",
                    "set-url",
                    "origin",
                    current_url,
                ]
            )
            if recurse_submodules:
                run_cmd(
                    [
                        "git",
                        "-C",
                        path.as_posix(),
                        "submodule",
                        "deinit",
                        "--all",
                        "-f",
                    ]
                )

            else:
                run_cmd(
                    [
                        "git",
                        "-C",
                        path.as_posix(),
                        "submodule",
                        "update",
                        "--init",
                        "--recursive",
                    ]
                )
        except Exception as e1:
            logger.error("回退分支切换失败: %s", e1)
        return False


def switch_commit(
    path: Path | str,
    commit: str,
) -> bool:
    """切换 Git 仓库到指定提交记录上

    Args:
        path (Path | str): Git 仓库路径
        commit (str): Git 仓库提交记录
    Returns:
        bool: 切换结果
    """
    path = Path(path) if not isinstance(path, Path) and path is not None else path
    logger.info("切换 %s 的 Git 指针到 %s 版本", path, commit)
    try:
        run_cmd(["git", "-C", path.as_posix(), "reset", "--hard", commit])
        return True
    except Exception as e:
        logger.error("切换 %s 的 Git 指针到 %s 版本时失败: %s", path, commit, e)
        return False


def is_git_repo(path: Path | str) -> bool:
    """检查该路径是否为 Git 仓库路径

    Args:
        path (Path | str): 要检查的路径
    Returns:
        bool: 当该路径为 Git 仓库时返回`True`
    """
    path = Path(path) if not isinstance(path, Path) and path is not None else path
    try:
        run_cmd(["git", "-C", path.as_posix(), "rev-parse", "--git-dir"], live=False)
        return True
    except Exception as _:
        return False


def set_git_config(
    username: str | None = None,
    email: str | None = None,
) -> bool:
    """配置 Git 信息

    Args:
        username (str | None): 用户名
        email (str | None): 邮箱地址
    Returns:
        bool: 配置成功时返回`True`
    """
    logger.info("配置 Git 信息中")
    try:
        if username is not None:
            run_cmd(["git", "config", "--global", "user.name", username])
        if email is not None:
            run_cmd(["git", "config", "--global", "user.email", email])
        return True
    except Exception as e:
        logger.error("配置 Git 信息时发生错误: %s", e)
        return False
