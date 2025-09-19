"""
与 SD 有关的环境管理模块, 可用于 Jupyter Notebook
支持管理的环境:
- SD WebUI / SD WebUI Forge / SD WebUI reForge / SD WebUI Forge Classic / SD WebUI AMDGPU / SD.Next
- ComfyUI
- InvokeAI
- Fooocus
- SD Script
- SD Trainer
- Kohya GUI
"""

import os
import re
import sys
import stat
import copy
import json
import uuid
import time
import shlex
import ctypes
import shutil
import secrets
import inspect
import logging
import hashlib
import datetime
import threading
import traceback
import subprocess
import queue
import importlib.metadata
import importlib.util
from pathlib import Path
from urllib.parse import urlparse
from tempfile import TemporaryDirectory
from typing import Callable, Literal, Any, TypedDict
from collections import namedtuple
from enum import Enum


VERSION = "1.1.13"


class LoggingColoredFormatter(logging.Formatter):
    """Logging 格式化类"""

    COLORS = {
        "DEBUG": "\033[0;36m",  # CYAN
        "INFO": "\033[0;32m",  # GREEN
        "WARNING": "\033[0;33m",  # YELLOW
        "ERROR": "\033[0;31m",  # RED
        "CRITICAL": "\033[0;37;41m",  # WHITE ON RED
        "RESET": "\033[0m",  # RESET COLOR
    }

    def __init__(self, fmt, datefmt=None, color=True):
        super().__init__(fmt, datefmt)
        self.color = color

    def format(self, record):
        colored_record = copy.copy(record)
        levelname = colored_record.levelname

        if self.color:
            seq = self.COLORS.get(levelname, self.COLORS["RESET"])
            colored_record.levelname = "{}{}{}".format(
                seq, levelname, self.COLORS["RESET"]
            )

        return super().format(colored_record)


def get_logger(
    name: str | None = None, level: int | None = logging.INFO, color: bool | None = True
) -> logging.Logger:
    """获取 Loging 对象

    :param name`(str|None)`: Logging 名称
    :param level`(int|None)`: 日志级别
    :param color`(bool|None)`: 是否启用彩色日志
    :return `logging.Logger`: Logging 对象
    """
    stack = inspect.stack()
    calling_filename = os.path.basename(stack[1].filename)
    if name is None:
        name = calling_filename

    _logger = logging.getLogger(name)
    _logger.propagate = False

    if not _logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            LoggingColoredFormatter(
                r"[%(name)s]-|%(asctime)s|-%(levelname)s: %(message)s",
                r"%Y-%m-%d %H:%M:%S",
                color=color,
            )
        )
        _logger.addHandler(handler)

    _logger.setLevel(level)
    _logger.debug("Logger 初始化完成")

    return _logger


logger = get_logger("Manager", color=False)


def run_cmd(
    command: str | list,
    desc: str | None = None,
    errdesc: str | None = None,
    custom_env: dict[str, str] | None = None,
    live: bool | None = True,
    shell: bool | None = None,
) -> str | None:
    """执行 Shell 命令

    :param command`(str|list)`: 要执行的命令
    :param desc`(str|None)`: 执行命令的描述
    :param errdesc`(str|None)`: 执行命令报错时的描述
    :param custom_env`(dict[str,str]|None)`: 自定义环境变量
    :param live`(bool|None)`: 是否实时输出命令执行日志
    :param shell`(bool|None)`: 是否使用内置 Shell 执行命令
    :return `str|None`: 命令执行时输出的内容
    :raises RuntimeError: 当命令执行失败时
    """

    if shell is None:
        shell = sys.platform != "win32"

    if desc is not None:
        logger.info(desc)

    if custom_env is None:
        custom_env = os.environ

    command_str = shlex.join(command) if isinstance(command, list) else command

    if live:
        process_output = []
        process = subprocess.Popen(
            command_str,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding="utf-8",
            env=custom_env,
        )

        for line in process.stdout:
            process_output.append(line)
            print(line, end="", flush=True)
            if sys.stdout and hasattr(sys.stdout, "flush"):
                sys.stdout.flush()

        process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"""{errdesc or "执行命令时发生错误"}
命令: {command_str}
错误代码: {process.returncode}""")

        return "".join(process_output)

    result: subprocess.CompletedProcess[bytes] = subprocess.run(
        command_str,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=shell,
        env=custom_env,
    )

    if result.returncode != 0:
        message = f"""{errdesc or "执行命令时发生错误"}
命令: {command_str}
错误代码: {result.returncode}
标准输出: {result.stdout.decode(encoding="utf8", errors="ignore") if len(result.stdout) > 0 else ""}
错误输出: {result.stderr.decode(encoding="utf8", errors="ignore") if len(result.stderr) > 0 else ""}
"""
        raise RuntimeError(message)

    return result.stdout.decode(encoding="utf8", errors="ignore")


def remove_files(path: str | Path) -> bool:
    """文件删除工具

    :param path`(str|Path)`: 要删除的文件路径
    :return `bool`: 删除结果
    """

    def _handle_remove_readonly(_func, _path, _):
        """处理只读文件的错误处理函数"""
        if os.path.exists(_path):
            os.chmod(_path, stat.S_IWRITE)
            _func(_path)

    try:
        path_obj = Path(path)
        if path_obj.is_file():
            os.chmod(path_obj, stat.S_IWRITE)
            path_obj.unlink()
            return True
        if path_obj.is_dir():
            shutil.rmtree(path_obj, onerror=_handle_remove_readonly)
            return True

        logger.error("路径不存在: %s", path)
        return False
    except Exception as e:
        logger.error("删除失败: %s", e)
        return False


def copy_files(src: Path | str, dst: Path | str) -> bool:
    """复制文件或目录

    :param src`(Path|str)`: 源文件路径
    :param dst`(Path|str)`: 复制文件到指定的路径
    :return `bool`: 复制结果
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)

        # 检查源是否存在
        if not src_path.exists():
            logger.error("源路径不存在: %s", src)
            return False

        # 如果目标是目录，创建完整路径
        if dst_path.is_dir():
            dst_file = dst_path / src_path.name
        else:
            dst_file = dst_path

        # 确保目标目录存在
        dst_file.parent.mkdir(parents=True, exist_ok=True)

        # 复制文件
        if src_path.is_file():
            shutil.copy2(src, dst_file)
        else:
            # 如果是目录，使用 copytree
            if dst_file.exists():
                shutil.rmtree(dst_file)
            shutil.copytree(src, dst_file)

        return True
    except PermissionError as e:
        logger.error("权限错误, 请检查文件权限或以管理员身份运行: %s", e)
        return False
    except Exception as e:
        logger.error("复制失败: %s", e)
        return False


class GitWarpper:
    """Git 工具集合"""

    @staticmethod
    def clone(
        repo: str,
        path: Path | str | None = None,
    ) -> Path | None:
        """下载 Git 仓库到本地

        :param repo`(str)`: Git 仓库链接
        :param path`(Path|str|None)`: 下载到本地的路径
        :return `Path|None`: 下载成功时返回路径, 否则返回`None`
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

    @staticmethod
    def update(path: Path | str) -> bool:
        """更新 Git 仓库

        :param path`(Path|str)`: Git 仓库路径
        :return `bool`: 更新 Git 仓库结果
        """
        path = Path(path) if not isinstance(path, Path) and path is not None else path
        use_submodule = []
        try:
            logger.info("拉取 %s 更新中", path)
            if GitWarpper.check_point_offset(path):
                if GitWarpper.fix_point_offset(path):
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
            branch = GitWarpper.get_current_branch(path)
            ref = run_cmd(
                ["git", "-C", path.as_posix(), "symbolic-ref", "--quiet", "HEAD"],
                live=False,
            )

            if GitWarpper.check_repo_on_origin_remote(path):
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
            run_cmd(
                ["git", "-C", path.as_posix(), "reset", "--hard", origin_branch]
                + use_submodule
            )
            logger.info("更新 %s 完成", path)
            return True
        except Exception as e:
            logger.error("更新 %s 时发生错误: %s", path.as_posix(), e)
            return False

    @staticmethod
    def check_point_offset(path: Path | str) -> bool:
        """检查 Git 仓库的指针是否游离

        :param path`(Path|str)`: Git 仓库路径
        :return `bool`: 当 Git 指针游离时返回`True`
        """
        path = Path(path) if not isinstance(path, Path) and path is not None else path
        try:
            run_cmd(["git", "-C", path.as_posix(), "symbolic-ref", "HEAD"], live=False)
            return False
        except Exception as _:
            return True

    @staticmethod
    def fix_point_offset(path: Path | str) -> bool:
        """修复 Git 仓库的 Git 指针游离

        :param path`(Path|str)`: Git 仓库路径
        :return `bool`: 修复结果
        """
        path = Path(path) if not isinstance(path, Path) and path is not None else path
        try:
            logger.info("修复 %s 的 Git 指针游离中", path)
            # run_cmd(["git", "-C", path.as_posix(), "remote", "prune", "origin"])
            run_cmd(["git", "-C", path.as_posix(), "submodule", "init"])
            branch_info = run_cmd(
                ["git", "-C", path.as_posix(), "branch", "-a"], live=False
            )
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

    @staticmethod
    def get_current_branch(path: Path | str) -> str | None:
        """获取 Git 仓库的当前所处分支

        :param path`(Path|str)`: Git 仓库路径
        :return `str`: 仓库所处分支, 获取失败时返回`None`
        """
        path = Path(path) if not isinstance(path, Path) and path is not None else path
        try:
            return run_cmd(
                ["git", "-C", path.as_posix(), "branch", "--show-current"], live=False
            ).strip()
        except Exception as e:
            logger.error("获取 %s 当前分支失败: %s", path, e)
            return None

    @staticmethod
    def check_repo_on_origin_remote(path: Path | str) -> bool:
        """检查 Git 仓库的远程源是否在 origin

        :param path`(Path|str)`: Git 仓库路径
        :return `bool`: 远程源在 origin 时返回`True`
        """
        path = Path(path) if not isinstance(path, Path) and path is not None else path
        try:
            current_branch = GitWarpper.get_current_branch(path)
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

    @staticmethod
    def check_local_branch_exists(
        path: Path | str,
        branch: str,
    ) -> bool:
        """检查 Git 仓库是否存在某个本地分支

        :param path`(Path|str)`: Git 仓库路径
        :param branch`(str)`: 要检查的本地分支
        :return `bool`: 分支存在时返回`True`
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

    @staticmethod
    def switch_branch(
        path: Path | str,
        branch: str,
        new_url: str | None = None,
        recurse_submodules: bool | None = False,
    ) -> bool:
        """切换 Git 仓库的分支和远程源

        :param path`(Path|str)`: Git 仓库路径
        :param branch`(str)`: 要切换的分支
        :param new_url`(str|None)`: 要切换的远程源
        :param recurse_submodules`(bool|None)`: 是否启用 Git 子模块
        :return `bool`: 切换分支结果
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
                run_cmd(
                    ["git", "-C", path.as_posix(), "submodule", "deinit", "--all", "-f"]
                )
            except Exception as e:
                logger.warning("更新 %s 的 Git 子模块信息发生错误: %s", path, e)

        logger.info("拉取 %s 远程源更新中", path)
        try:
            run_cmd(["git", "-C", path.as_posix(), "fetch"])
            run_cmd(
                ["git", "-C", path.as_posix(), "submodule", "deinit", "--all", "-f"]
            )
            if not GitWarpper.check_local_branch_exists(path, branch):
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
                run_cmd(
                    ["git", "-C", path.as_posix(), "submodule", "deinit", "--all", "-f"]
                )
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

            run_cmd(
                ["git", "-C", path.as_posix(), "reset", "--hard", f"origin/{branch}"]
                + use_submodules
            )
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
            except Exception as e:
                logger.error("回退分支切换失败: %s", e)
            return False

    @staticmethod
    def switch_commit(
        path: Path | str,
        commit: str,
    ) -> bool:
        """切换 Git 仓库到指定提交记录上

        :param path`(Path|str)`: Git 仓库路径
        :param commit`(str)`: Git 仓库提交记录
        :return `bool`: 切换结果
        """
        path = Path(path) if not isinstance(path, Path) and path is not None else path
        logger.info("切换 %s 的 Git 指针到 %s 版本", path, commit)
        try:
            run_cmd(["git", "-C", path.as_posix(), "reset", "--hard", commit])
            return True
        except Exception as e:
            logger.error("切换 %s 的 Git 指针到 %s 版本时失败: %s", path, commit, e)
            return False

    @staticmethod
    def is_git_repo(path: Path | str) -> bool:
        """检查该路径是否为 Git 仓库路径

        :param path`(Path|str)`: 要检查的路径
        :return `bool`: 当该路径为 Git 仓库时返回`True`
        """
        path = Path(path) if not isinstance(path, Path) and path is not None else path
        try:
            run_cmd(
                ["git", "-C", path.as_posix(), "rev-parse", "--git-dir"], live=False
            )
            return True
        except Exception as _:
            return False

    @staticmethod
    def set_git_config(
        username: str | None = None,
        email: str | None = None,
    ) -> bool:
        """配置 Git 信息

        :param username`(str|None)`: 用户名
        :param email`(str|None)`: 邮箱地址
        :return `bool`: 配置成功时返回`True`
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


class Downloader:
    """下载工具"""

    @staticmethod
    def aria2(
        url: str,
        path: Path | str | None = None,
        save_name: str | None = None,
    ) -> Path | None:
        """Aria2 下载工具

        :param url`(str)`: 文件下载链接
        :param path`(Path|str|None)`: 下载文件的路径, 为`None`时使用当前路径
        :param save_name`(str|None)`: 保存的文件名, 为`None`时使用`url`提取保存的文件名
        :return `Path|None`: 下载成功时返回文件路径, 否则返回`None`
        """
        if path is None:
            path = os.getcwd()

        path = Path(path) if not isinstance(path, Path) and path is not None else path
        if save_name is None:
            parts = urlparse(url)
            save_name = os.path.basename(parts.path)

        save_path = path / save_name
        try:
            logger.info("下载 %s 到 %s 中", os.path.basename(url), save_path)
            run_cmd(
                [
                    "aria2c",
                    "--console-log-level=error",
                    "-c",
                    "-x",
                    "16",
                    "-s",
                    "16",
                    "-k",
                    "1M",
                    url,
                    "-d",
                    path.as_posix(),
                    "-o",
                    save_name,
                ]
            )
            return save_path
        except Exception as e:
            logger.error("下载 %s 时发生错误: %s", url, e)
            raise Exception(e)

    @staticmethod
    def load_file_from_url(
        url: str,
        *,
        model_dir: Path | str | None = None,
        progress: bool | None = False,
        file_name: str | None = None,
        hash_prefix: str | None = None,
        re_download: bool | None = False,
    ):
        """使用 requrest 库下载文件

        :param url`(str)`: 下载链接
        :param model`(Path|str|None)`: 下载路径
        :param progress`(bool|None)`: 是否启用下载进度条
        :param file_name`(str|None)`: 保存的文件名, 如果为`None`则从`url`中提取文件
        :param hash_prefix`(str|None)`: sha256 十六进制字符串, 如果提供, 将检查下载文件的哈希值是否与此前缀匹配, 当不匹配时引发`ValueError`
        :param re_download`(bool)`: 强制重新下载文件
        :return `Path`: 下载的文件路径
        """
        import requests
        from tqdm import tqdm

        if model_dir is None:
            model_dir = os.getcwd()

        model_dir = (
            Path(model_dir)
            if not isinstance(model_dir, Path) and model_dir is not None
            else model_dir
        )

        if not file_name:
            parts = urlparse(url)
            file_name = os.path.basename(parts.path)

        cached_file = model_dir.resolve() / file_name

        if re_download or not cached_file.exists():
            model_dir.mkdir(parents=True, exist_ok=True)
            temp_file = model_dir / f"{file_name}.tmp"
            logger.info("下载 %s 到 %s 中", file_name, cached_file)
            response = requests.get(url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            with tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=file_name,
                disable=not progress,
            ) as progress_bar:
                with open(temp_file, "wb") as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            file.write(chunk)
                            progress_bar.update(len(chunk))

            if hash_prefix and not Downloader.compare_sha256(temp_file, hash_prefix):
                logger.error("%s 的哈希值不匹配, 正在删除临时文件", temp_file)
                temp_file.unlink()
                raise ValueError(f"文件哈希值与预期的哈希前缀不匹配: {hash_prefix}")

            temp_file.rename(cached_file)
            logger.info("%s 下载完成", file_name)
        else:
            logger.info("%s 已存在于 %s 中", file_name, cached_file)
        return cached_file

    @staticmethod
    def compare_sha256(file_path: str | Path, hash_prefix: str) -> bool:
        """检查文件的 sha256 哈希值是否与给定的前缀匹配

        :param file_path`(str|Path)`: 文件路径
        :param hash_prefix`(str)`: 哈希前缀
        :return `bool`: 匹配结果
        """
        hash_sha256 = hashlib.sha256()
        blksize = 1024 * 1024

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(blksize), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest().startswith(hash_prefix.strip().lower())

    @staticmethod
    def download_file(
        url: str,
        path: str | Path = None,
        save_name: str | None = None,
        tool: Literal["aria2", "request"] = "aria2",
        retry: int | None = 3,
    ) -> Path | None:
        """下载文件工具

        :param url`(str)`: 文件下载链接
        :param path`(Path|str)`: 文件下载路径
        :param save_name`(str)`: 文件保存名称, 当为`None`时从`url`中解析文件名
        :param tools`(Literal["aria2","request"])`: 下载工具
        :param retry`(int)`: 重试下载的次数
        :return `Path|None`: 保存的文件路径
        """
        count = 0
        while count < retry:
            count += 1
            try:
                if tool == "aria2":
                    output = Downloader.aria2(
                        url=url,
                        path=path,
                        save_name=save_name,
                    )
                    if output is None:
                        continue
                    return output
                elif tool == "request":
                    output = Downloader.load_file_from_url(
                        url=url,
                        model_dir=path,
                        file_name=save_name,
                    )
                    if output is None:
                        continue
                    return output
                else:
                    logger.error("未知下载工具: %s", tool)
                    return None
            except Exception as e:
                logger.error("[%s/%s] 下载 %s 出现错误: %s", count, retry, url, e)

            if count < retry:
                logger.warning("[%s/%s] 重试下载 %s 中", count, retry, url)
            else:
                return None


class EnvManager:
    """依赖环境管理工具"""

    @staticmethod
    def pip_install(
        *args: Any,
        use_uv: bool | None = True,
        custom_env: dict[str, str] | None = None,
    ) -> str:
        """使用 Pip / uv 安装 Python 软件包

        :param *args`(Any)`: 要安装的 Python 软件包 (可使用 Pip / uv 命令行参数, 如`--upgrade`, `--force-reinstall`)
        :param use_uv`(bool|None)`: 使用 uv 代替 Pip 进行安装, 当 uv 安装 Python 软件包失败时, 将回退到 Pip 进行重试
        :param custom_env`(dict[str,str]|None)`: 自定义环境变量
        :return `str`: 命令的执行输出
        :raises RuntimeError: 当 uv 和 pip 都无法安装软件包时抛出异常
        """
        if custom_env is None:
            custom_env = os.environ.copy()
        if use_uv:
            try:
                run_cmd(["uv", "--version"], live=False, custom_env=custom_env)
            except Exception as _:
                logger.info("安装 uv 中")
                run_cmd(
                    [Path(sys.executable).as_posix(), "-m", "pip", "install", "uv"],
                    custom_env=custom_env,
                )

            try:
                return run_cmd(["uv", "pip", "install", *args], custom_env=custom_env)
            except Exception as e:
                logger.warning(
                    "检测到 uv 安装 Python 软件包失败, 尝试回退到 Pip 重试 Python 软件包安装: %s",
                    e,
                )
                return run_cmd(
                    [Path(sys.executable).as_posix(), "-m", "pip", "install", *args],
                    custom_env=custom_env,
                )
        else:
            return run_cmd(
                [Path(sys.executable).as_posix(), "-m", "pip", "install", *args],
                custom_env=custom_env,
            )

    @staticmethod
    def install_manager_depend(
        use_uv: bool | None = True,
        custom_env: dict[str, str] | None = None,
        custom_sys_pkg_cmd: list[list[str]] | list[str] | None = None,
    ) -> bool:
        """安装自身组件依赖

        :param use_uv`(bool|None)`: 使用 uv 代替 Pip 进行安装, 当 uv 安装 Python 软件包失败时, 将回退到 Pip 进行重试
        :param custom_env`(dict[str,str]|None)`: 自定义环境变量
        :param custom_sys_pkg_cmd`(list[list[str]]|list[str]|None)`: 自定义调用系统包管理器命令
        :return `bool`: 组件安装结果
        :notes
            自定义命令的例子:
            ```python
            custom_sys_pkg_cmd = [
                ["apt", "update"],
                ["apt", "install", "aria2", "google-perftools", "p7zip-full", "unzip", "tree", "git", "git-lfs", "-y"]
            ]
            # 另一种等效形式
            custom_sys_pkg_cmd = [
                "apt update",
                "apt install aria2 google-perftools p7zip-full unzip tree git git-lfs -y",
            ]
            ```
            这将分别执行两条命令:
            `apt update`
            `apt install aria2 google-perftools p7zip-full unzip tree git git-lfs -y`
        """
        if custom_env is None:
            custom_env = os.environ.copy()
        if custom_sys_pkg_cmd is None:
            custom_sys_pkg_cmd = [
                ["apt", "update"],
                [
                    "apt",
                    "install",
                    "aria2",
                    "google-perftools",
                    "p7zip-full",
                    "unzip",
                    "tree",
                    "git",
                    "git-lfs",
                    "-y",
                ],
            ]
        try:
            logger.info("安装自身组件依赖中")
            EnvManager.pip_install(
                "uv", "--upgrade", use_uv=False, custom_env=custom_env
            )
            EnvManager.pip_install(
                "modelscope",
                "huggingface_hub[hf_xet]",
                "requests",
                "tqdm",
                "wandb",
                "--upgrade",
                use_uv=use_uv,
                custom_env=custom_env,
            )
            for cmd in custom_sys_pkg_cmd:
                run_cmd(cmd, custom_env=custom_env)
            return True
        except Exception as e:
            logger.error("安装自身组件依赖失败: %s", e)
            return False

    @staticmethod
    def install_pytorch(
        torch_package: str | list | None = None,
        xformers_package: str | list | None = None,
        pytorch_mirror: str | None = None,
        use_uv: bool | None = True,
    ) -> bool:
        """安装 PyTorch / xFormers

        :param torch_package`(str|list|None)`: PyTorch 软件包名称和版本信息, 如`torch==2.0.0 torchvision==0.15.1` / `["torch==2.0.0", "torchvision==0.15.1"]`
        :param xformers_package`(str|list|None)`: xFormers 软件包名称和版本信息, 如`xformers==0.0.18` / `["xformers==0.0.18"]`
        :param pytorch_mirror`(str|None)`: 指定安装 PyTorch / xFormers 时使用的镜像源
        :param use_uv`(bool|None)`: 是否使用 uv 代替 Pip 进行安装
        :return `bool`: 安装 PyTorch / xFormers 成功时返回`True`
        """
        custom_env = os.environ.copy()
        if pytorch_mirror is not None:
            logger.info("使用自定义 PyTorch 镜像源: %s", pytorch_mirror)
            custom_env.pop("PIP_EXTRA_INDEX_URL", None)
            custom_env.pop("PIP_FIND_LINKS", None)
            custom_env.pop("UV_INDEX", None)
            custom_env.pop("UV_FIND_LINKS", None)
            custom_env["PIP_INDEX_URL"] = pytorch_mirror
            custom_env["UV_DEFAULT_INDEX"] = pytorch_mirror

        if torch_package is not None:
            logger.info("安装 PyTorch 中")
            torch_package = (
                torch_package.split()
                if isinstance(torch_package, str)
                else torch_package
            )
            try:
                EnvManager.pip_install(*torch_package, use_uv=use_uv)
                logger.info("安装 PyTorch 成功")
            except Exception as e:
                logger.error("安装 PyTorch 时发生错误: %s", e)
                return False

        if xformers_package is not None:
            logger.info("安装 xFormers 中")
            xformers_package = (
                xformers_package.split()
                if isinstance(xformers_package, str)
                else xformers_package
            )
            try:
                EnvManager.pip_install(*xformers_package, use_uv=use_uv)
                logger.info("安装 xFormers 成功")
            except Exception as e:
                logger.error("安装 xFormers 时发生错误: %s", e)
                return False

        return True

    @staticmethod
    def install_requirements(
        path: Path | str,
        use_uv: bool | None = True,
        custom_env: dict[str, str] | None = None,
    ) -> bool:
        """从 requirements.txt 文件指定安装的依赖

        :param path`(Path|str)`: requirements.txt 文件路径
        :param use_uv`(bool|None)`: 是否使用 uv 代替 Pip 进行安装
        :return `bool`: 安装依赖成功时返回`True`
        """
        if custom_env is None:
            custom_env = os.environ.copy()
        path = Path(path) if not isinstance(path, Path) and path is not None else path

        try:
            logger.info("从 %s 安装 Python 软件包中", path)
            EnvManager.pip_install(
                "-r", path.as_posix(), use_uv=use_uv, custom_env=custom_env
            )
            logger.info("从 %s 安装 Python 软件包成功", path)
            return True
        except Exception as e:
            logger.info("从 %s 安装 Python 软件包时发生错误: %s", path, e)
            return False


class Utils:
    """其他工具集合"""

    @staticmethod
    def clear_up() -> bool:
        """清理 Jupyter Notebook 输出内容

        :return `bool`: 清理输出结果
        """
        try:
            from IPython.display import clear_output

            clear_output(wait=False)
            return True
        except Exception as e:
            logger.error("清理 Jupyter Notebook 输出内容失败: %s", e)
            return False

    @staticmethod
    def check_gpu() -> bool:
        """检查环境中是否有可用的 GPU

        :return `bool`: 当有可用 GPU 时返回`True`
        """
        logger.info("检查当前环境是否有 GPU 可用")
        import tensorflow as tf

        if tf.test.gpu_device_name():
            logger.info("有可用的 GPU")
            return True
        else:
            logger.error("无可用 GPU")
            return False

    @staticmethod
    def get_file_list(path: Path | str, resolve: bool | None = False) -> list[Path]:
        """获取当前路径下的所有文件的绝对路径

        :param path`(Path|str)`: 要获取文件列表的目录
        :param resolve`(bool|None)`: 将路径进行完全解析, 包括链接路径
        :return `list[Path]`: 文件列表的绝对路径
        """
        path = Path(path) if not isinstance(path, Path) and path is not None else path

        if not path.exists():
            return []

        if path.is_file():
            return [path.resolve() if resolve else path.absolute()]

        file_list: list[Path] = []
        for root, _, files in os.walk(path):
            for file in files:
                file_path = Path(root) / file
                file_list.append(
                    file_path.resolve() if resolve else file_path.absolute()
                )

        return file_list

    @staticmethod
    def config_wandb_token(token: str | None = None) -> None:
        """配置 WandB 所需 Token"""
        if token is not None:
            logger.info("配置 WandB Token")
            os.environ["WANDB_API_KEY"] = token

    @staticmethod
    def download_archive_and_unpack(
        url: str, local_dir: Path | str, name: str | None = None, retry: int | None = 3
    ) -> Path | None:
        """下载压缩包并解压到指定路径

        :param url`(str)`: 压缩包下载链接, 压缩包只支持`zip`,`7z`,`tar`格式
        :param local_dir`(Path|str)`: 下载路径
        :param name`(str|None)`: 下载文件保存的名称, 为`None`时从`url`解析文件名
        :param retry`(int|None)`: 重试下载的次数
        :return `Path|None`: 下载成功并解压成功时返回路径
        """
        path = Path("/tmp")
        local_dir = (
            Path(local_dir)
            if not isinstance(local_dir, Path) and local_dir is not None
            else local_dir
        )
        if name is None:
            parts = urlparse(url)
            name = os.path.basename(parts.path)

        archive_format = Path(name).suffix  # 压缩包格式
        origin_file_path = Downloader.download_file(  # 下载文件
            url=url, path=path, save_name=name, tool="aria2", retry=retry
        )

        if origin_file_path is not None:
            # 解压文件
            logger.info("解压 %s 到 %s 中", name, local_dir)
            try:
                if archive_format == ".7z":
                    run_cmd(
                        [
                            "7z",
                            "x",
                            origin_file_path.as_posix(),
                            f"-o{local_dir.as_posix()}",
                        ]
                    )
                    logger.info("%s 解压完成, 路径: %s", name, local_dir)
                    return local_dir
                elif archive_format == ".zip":
                    run_cmd(
                        [
                            "unzip",
                            origin_file_path.as_posix(),
                            "-d",
                            local_dir.as_posix(),
                        ]
                    )
                    logger.info("%s 解压完成, 路径: %s", name, local_dir)
                    return local_dir
                elif archive_format == ".tar":
                    run_cmd(
                        [
                            "tar",
                            "-xvf",
                            origin_file_path.as_posix(),
                            "-C",
                            local_dir.as_posix(),
                        ]
                    )
                    logger.info("%s 解压完成, 路径: %s", name, local_dir)
                    return local_dir
                else:
                    logger.error("%s 的格式不支持解压", name)
                    return None
            except Exception as e:
                logger.error("解压 %s 时发生错误: %s", name, e)
                traceback.print_exc()
                return None
        else:
            logger.error("%s 下载失败", name)
            return None

    @staticmethod
    def config_tcmalloc() -> bool:
        """使用 TCMalloc 优化内存的占用, 通过 LD_PRELOAD 环境变量指定 TCMalloc

        :return `bool`: 配置成功时返回`True`
        """
        # 检查 glibc 版本
        try:
            result = subprocess.run(
                ["ldd", "--version"], capture_output=True, text=True
            )
            libc_ver_line = result.stdout.split("\n")[0]
            libc_ver = re.search(r"(\d+\.\d+)", libc_ver_line)
            if libc_ver:
                libc_ver = libc_ver.group(1)
                logger.info("glibc 版本: %s", libc_ver)
            else:
                logger.error("无法确定 glibc 版本")
                return False
        except Exception as e:
            logger.error("检查 glibc 版本时出错: %s", e)
            return False

        # 从 2.34 开始, libpthread 已经集成到 libc.so 中
        libc_v234 = "2.34"

        # 定义 Tcmalloc 库数组
        tcmalloc_libs = [r"libtcmalloc(_minimal|)\.so\.\d+", r"libtcmalloc\.so\.\d+"]

        # 遍历数组
        for lib_pattern in tcmalloc_libs:
            try:
                # 获取系统库缓存信息
                result = subprocess.run(
                    ["ldconfig", "-p"],
                    capture_output=True,
                    text=True,
                    env=dict(os.environ, PATH="/usr/sbin:" + os.getenv("PATH")),
                )
                libraries = result.stdout.split("\n")

                # 查找匹配的 TCMalloc 库
                for lib in libraries:
                    if re.search(lib_pattern, lib):
                        # 解析库信息
                        match = re.search(r"(.+?)\s+=>\s+(.+)", lib)
                        if match:
                            lib_name, lib_path = (
                                match.group(1).strip(),
                                match.group(2).strip(),
                            )
                            logger.info("检查 TCMalloc: %s => %s", lib_name, lib_path)

                            # 确定库是否链接到 libpthread 和解析未定义符号: pthread_key_create
                            if Utils.compare_versions(libc_ver, libc_v234) < 0:
                                # glibc < 2.34，pthread_key_create 在 libpthread.so 中。检查链接到 libpthread.so
                                ldd_result = subprocess.run(
                                    ["ldd", lib_path], capture_output=True, text=True
                                )
                                if "libpthread" in ldd_result.stdout:
                                    logger.info(
                                        "%s 链接到 libpthread, 执行 LD_PRELOAD=%s",
                                        lib_name,
                                        lib_path,
                                    )
                                    # 设置完整路径 LD_PRELOAD
                                    if (
                                        "LD_PRELOAD" in os.environ
                                        and os.environ["LD_PRELOAD"]
                                    ):
                                        os.environ["LD_PRELOAD"] = (
                                            os.environ["LD_PRELOAD"] + ":" + lib_path
                                        )
                                    else:
                                        os.environ["LD_PRELOAD"] = lib_path
                                    return True
                                else:
                                    logger.info(
                                        "%s 没有链接到 libpthread, 将触发未定义符号: pthread_Key_create 错误",
                                        lib_name,
                                    )
                            else:
                                # libc.so (glibc) 的 2.34 版本已将 pthread 库集成到 glibc 内部
                                logger.info(
                                    "%s 链接到 libc.so, 执行 LD_PRELOAD=%s",
                                    lib_name,
                                    lib_path,
                                )
                                # 设置完整路径 LD_PRELOAD
                                if (
                                    "LD_PRELOAD" in os.environ
                                    and os.environ["LD_PRELOAD"]
                                ):
                                    os.environ["LD_PRELOAD"] = (
                                        os.environ["LD_PRELOAD"] + ":" + lib_path
                                    )
                                else:
                                    os.environ["LD_PRELOAD"] = lib_path
                                return True
            except Exception as e:
                logger.error("检查 TCMalloc 库时出错: %s", e)
                continue

        if "LD_PRELOAD" not in os.environ:
            logger.warning(
                "无法定位 TCMalloc。未在系统上找到 tcmalloc 或 google-perftool, 取消加载内存优化"
            )
            return False

    @staticmethod
    def version_increment(version: str) -> str:
        """增加版本号大小

        :param version`(str)`: 初始版本号
        :return `str`: 增加后的版本号
        """
        version = "".join(re.findall(r"\d|\.", version))
        ver_parts = list(map(int, version.split(".")))
        ver_parts[-1] += 1

        for i in range(len(ver_parts) - 1, 0, -1):
            if ver_parts[i] == 10:
                ver_parts[i] = 0
                ver_parts[i - 1] += 1

        return ".".join(map(str, ver_parts))

    @staticmethod
    def version_decrement(version: str) -> str:
        """减小版本号大小

        :param version`(str)`: 初始版本号
        :return `str`: 减小后的版本号
        """
        version = "".join(re.findall(r"\d|\.", version))
        ver_parts = list(map(int, version.split(".")))
        ver_parts[-1] -= 1

        for i in range(len(ver_parts) - 1, 0, -1):
            if ver_parts[i] == -1:
                ver_parts[i] = 9
                ver_parts[i - 1] -= 1

        while len(ver_parts) > 1 and ver_parts[0] == 0:
            ver_parts.pop(0)

        return ".".join(map(str, ver_parts))

    @staticmethod
    def compare_versions(
        version1: str | int | float, version2: str | int | float
    ) -> int:
        """对比两个版本号大小

        :param version1(str|int|float): 第一个版本号
        :param version2(str|int|float): 第二个版本号
        :return int: 版本对比结果, 1 为第一个版本号大, -1 为第二个版本号大, 0 为两个版本号一样
        """
        version1 = str(version1)
        version2 = str(version2)
        # 将版本号拆分成数字列表
        try:
            nums1 = (
                re.sub(r"[a-zA-Z]+", "", version1)
                .replace("-", ".")
                .replace("_", ".")
                .replace("+", ".")
                .split(".")
            )
            nums2 = (
                re.sub(r"[a-zA-Z]+", "", version2)
                .replace("-", ".")
                .replace("_", ".")
                .replace("+", ".")
                .split(".")
            )
        except Exception as _:
            return 0

        for i in range(max(len(nums1), len(nums2))):
            num1 = (
                int(nums1[i]) if i < len(nums1) else 0
            )  # 如果版本号 1 的位数不够, 则补 0
            num2 = (
                int(nums2[i]) if i < len(nums2) else 0
            )  # 如果版本号 2 的位数不够, 则补 0

            if num1 == num2:
                continue
            elif num1 > num2:
                return 1  # 版本号 1 更大
            else:
                return -1  # 版本号 2 更大

        return 0  # 版本号相同

    @staticmethod
    def mount_google_drive(path: Path | str) -> bool:
        """挂载 Google Drive"""
        path = Path(path) if not isinstance(path, Path) and path is not None else path
        if not path.exists():
            logger.info("挂载 Google Drive 中, 请根据提示进行操作")
            try:
                from google.colab import drive

                drive.mount(path.as_posix())
                logger.info("Google Dirve 挂载完成")
                return True
            except Exception as e:
                logger.error("挂载 Google Drive 时出现问题: %e", e)
                return False
        else:
            logger.info("Google Drive 已挂载")
            return True

    @staticmethod
    def get_cuda_comp_cap() -> float:
        """
        Returns float of CUDA Compute Capability using nvidia-smi
        Returns 0.0 on error
        CUDA Compute Capability
        ref https://developer.nvidia.com/cuda-gpus
        ref https://en.wikipedia.org/wiki/CUDA
        Blackwell consumer GPUs should return 12.0 data-center GPUs should return 10.0

        :return `float`: Comp Cap 版本
        """
        try:
            return max(
                map(
                    float,
                    subprocess.check_output(
                        [
                            "nvidia-smi",
                            "--query-gpu=compute_cap",
                            "--format=noheader,csv",
                        ],
                        text=True,
                    ).splitlines(),
                )
            )
        except Exception as _:
            return 0.0

    @staticmethod
    def get_cuda_version() -> float:
        """获取驱动支持的 CUDA 版本

        :return `float`: CUDA 支持的版本
        """
        try:
            # 获取 nvidia-smi 输出
            output = subprocess.check_output(["nvidia-smi", "-q"], text=True)
            match = re.search(r"CUDA Version\s+:\s+(\d+\.\d+)", output)
            if match:
                return float(match.group(1))
            return 0.0
        except Exception as _:
            return 0.0

    @staticmethod
    def get_pytorch_mirror_type_cuda(torch_ver: str) -> str:
        """获取 CUDA 类型的 PyTorch 镜像源类型

        :param torch_ver`(str)`: PyTorch 版本
        :return `str`: CUDA 类型的 PyTorch 镜像源类型
        """
        # cu118: 2.0.0 ~ 2.4.0
        # cu121: 2.1.1 ~ 2.4.0
        # cu124: 2.4.0 ~ 2.6.0
        # cu126: 2.6.0 ~ 2.7.1
        # cu128: 2.7.0 ~ 2.7.1
        # cu129: 2.8.0 ~
        cuda_comp_cap = Utils.get_cuda_comp_cap()
        cuda_support_ver = Utils.get_cuda_version()

        if Utils.compare_versions(torch_ver, "2.0.0") == -1:
            # torch < 2.0.0: default cu11x
            return "other"
        if (
            Utils.compare_versions(torch_ver, "2.0.0") >= 0
            and Utils.compare_versions(torch_ver, "2.3.1") == -1
        ):
            # 2.0.0 <= torch < 2.3.1: default cu118
            return "cu118"
        if (
            Utils.compare_versions(torch_ver, "2.3.0") >= 0
            and Utils.compare_versions(torch_ver, "2.4.1") == -1
        ):
            # 2.3.0 <= torch < 2.4.1: default cu121
            if Utils.compare_versions(str(int(cuda_support_ver * 10)), "cu121") < 0:
                if (
                    Utils.compare_versions(str(int(cuda_support_ver * 10)), "cu118")
                    >= 0
                ):
                    return "cu118"
            return "cu121"
        if (
            Utils.compare_versions(torch_ver, "2.4.0") >= 0
            and Utils.compare_versions(torch_ver, "2.6.0") == -1
        ):
            # 2.4.0 <= torch < 2.6.0: default cu124
            if Utils.compare_versions(str(int(cuda_support_ver * 10)), "cu124") < 0:
                if (
                    Utils.compare_versions(str(int(cuda_support_ver * 10)), "cu121")
                    >= 0
                ):
                    return "cu121"
                if (
                    Utils.compare_versions(str(int(cuda_support_ver * 10)), "cu118")
                    >= 0
                ):
                    return "cu118"
            return "cu124"
        if (
            Utils.compare_versions(torch_ver, "2.6.0") >= 0
            and Utils.compare_versions(torch_ver, "2.7.0") == -1
        ):
            # 2.6.0 <= torch < 2.7.0: default cu126
            if Utils.compare_versions(str(int(cuda_support_ver * 10)), "cu126") < 0:
                if (
                    Utils.compare_versions(str(int(cuda_support_ver * 10)), "cu124")
                    >= 0
                ):
                    return "cu124"
            if Utils.compare_versions(cuda_comp_cap, "10.0") > 0:
                if (
                    Utils.compare_versions(str(int(cuda_support_ver * 10)), "cu128")
                    >= 0
                ):
                    return "cu128"
            return "cu126"
        if (
            Utils.compare_versions(torch_ver, "2.7.0") >= 0
            and Utils.compare_versions(torch_ver, "2.8.0") == -1
        ):
            # 2.7.0 <= torch < 2.8.0: default cu128
            if Utils.compare_versions(str(int(cuda_support_ver * 10)), "cu128") < 0:
                if (
                    Utils.compare_versions(str(int(cuda_support_ver * 10)), "cu126")
                    >= 0
                ):
                    return "cu126"
            return "cu128"
        if Utils.compare_versions(torch_ver, "2.8.0") >= 0:
            # torch >= 2.8.0: default cu129
            return "cu129"

        return "cu129"

    @staticmethod
    def get_pytorch_mirror_type_rocm(torch_ver: str) -> str:
        """获取 ROCm 类型的 PyTorch 镜像源类型

        :param torch_ver`(str)`: PyTorch 版本
        :return `str`: ROCm 类型的 PyTorch 镜像源类型
        """
        if Utils.compare_versions(torch_ver, "2.4.0") < 0:
            # torch < 2.4.0
            return "other"
        if (
            Utils.compare_versions(torch_ver, "2.4.0") >= 0
            and Utils.compare_versions(torch_ver, "2.5.0") < 0
        ):
            # 2.4.0 <= torch < 2.5.0
            return "rocm61"
        if (
            Utils.compare_versions(torch_ver, "2.5.0") >= 0
            and Utils.compare_versions(torch_ver, "2.6.0") < 0
        ):
            # 2.5.0 <= torch < 2.6.0
            return "rocm62"
        if (
            Utils.compare_versions(torch_ver, "2.6.0") >= 0
            and Utils.compare_versions(torch_ver, "2.7.0") < 0
        ):
            # 2.6.0 < torch < 2.7.0
            return "rocm624"
        if Utils.compare_versions(torch_ver, "2.7.0") >= 0:
            # torch >= 2.7.0
            return "rocm63"

        return "rocm63"

    @staticmethod
    def get_pytorch_mirror_type_ipex(torch_ver: str) -> str:
        """获取 IPEX 类型的 PyTorch 镜像源类型

        :param torch_ver`(str)`: PyTorch 版本
        :return `str`: IPEX 类型的 PyTorch 镜像源类型
        """
        if Utils.compare_versions(torch_ver, "2.0.0") < 0:
            # torch < 2.0.0
            return "other"
        if Utils.compare_versions(torch_ver, "2.0.0") == 0:
            # torch == 2.0.0
            return "ipex_legacy_arc"
        if (
            Utils.compare_versions(torch_ver, "2.0.0") > 0
            and Utils.compare_versions(torch_ver, "2.1.0") < 0
        ):
            # 2.0.0 < torch < 2.1.0
            return "other"
        if Utils.compare_versions(torch_ver, "2.1.0") == 0:
            # torch == 2.1.0
            return "ipex_legacy_arc"
        if Utils.compare_versions(torch_ver, "2.6.0") >= 0:
            # torch >= 2.6.0
            return "xpu"

        return "xpu"

    @staticmethod
    def get_pytorch_mirror_type_cpu(torch_ver: str) -> str:
        """获取 CPU 类型的 PyTorch 镜像源类型

        :param torch_ver`(str)`: PyTorch 版本
        :return `str`: CPU 类型的 PyTorch 镜像源类型
        """
        _ = torch_ver
        return "cpu"

    @staticmethod
    def get_pytorch_mirror_type(
        torch_ver: str, device_type: Literal["cuda", "rocm", "xpu", "cpu"]
    ) -> str:
        """获取 PyTorch 镜像源类型

        :param torch_ver`(str)`: PyTorch 版本号
        :param device_type`(Literal["cuda","rocm","xpu","cpu"])`: 显卡类型
        :return `str`: PyTorch 镜像源类型
        """
        if device_type == "cuda":
            return Utils.get_pytorch_mirror_type_cuda(torch_ver)

        if device_type == "rocm":
            return Utils.get_pytorch_mirror_type_rocm(torch_ver)

        if device_type == "xpu":
            return Utils.get_pytorch_mirror_type_ipex(torch_ver)

        if device_type == "cpu":
            return Utils.get_pytorch_mirror_type_cpu(torch_ver)

        return "other"

    @staticmethod
    def get_env_pytorch_type() -> str:
        """获取当前环境中 PyTorch 版本号对应的类型

        :return `str`: PyTorch 类型 (cuda, rocm, xpu, cpu)
        """
        torch_ipex_legacy_ver_list = [
            "2.0.0a0+gite9ebda2",
            "2.1.0a0+git7bcf7da",
            "2.1.0a0+cxx11.abi",
            "2.0.1a0",
            "2.1.0.post0",
        ]
        try:
            import torch

            torch_ver = torch.__version__
        except Exception as _:
            return "cuda"

        torch_type = torch_ver.split("+").pop()

        if torch_ver in torch_ipex_legacy_ver_list:
            return "xpu"

        if "cu" in torch_type:
            return "cuda"

        if "rocm" in torch_type:
            return "rocm"

        if "xpu" in torch_type:
            return "xpu"

        if "cpu" in torch_type:
            return "cpu"

        return "cuda"

    @staticmethod
    def warning_unexpected_params(
        message: str,
        args: tuple,
        kwargs: dict,
    ) -> None:
        """显示多余参数警告"""
        if args or kwargs:
            logger.warning(message)
            if args:
                logger.warning("多余的位置参数: %s", args)

            if kwargs:
                logger.warning("多余的关键字参数: %s", kwargs)

            logger.warning("请移除这些多余参数以避免引发错误")

    @staticmethod
    def get_sync_files(src_path: Path | str, dst_path: Path | str) -> list[Path]:
        """获取需要进行同步的文件列表 (增量同步)

        :param src_path`(Path|str)`: 同步文件的源路径
        :param dst_path`(Path|str)`: 同步文件到的路径
        :return `list[Path]`: 要进行同步的文件
        """
        from tqdm import tqdm

        if not isinstance(src_path, Path) and src_path is not None:
            src_path = Path(src_path)

        if not isinstance(dst_path, Path) and dst_path is not None:
            dst_path = Path(dst_path)

        src_is_file = src_path.is_file()
        src_files = Utils.get_file_list(src_path)
        logger.info("%s 中的文件数量: %s", src_path, len(src_files))
        dst_files = Utils.get_file_list(dst_path)
        logger.info("%s 中的文件数量: %s", dst_path, len(dst_files))
        if src_path.is_dir() and dst_path.is_file():
            logger.warning("%s 为目录, 而 %s 为文件, 无法进行复制", src_path, dst_path)
            sync_file_list = []
        else:
            dst_files_set = set(dst_files)  # 加快统计速度
            sync_file_list = [
                x
                for x in tqdm(src_files, desc="计算需要同步的文件")
                if (
                    dst_path
                    / x.relative_to(src_path if not src_is_file else src_path.parent)
                )
                not in dst_files_set
            ]
        logger.info("要进行同步的文件数量: %s", len(sync_file_list))
        return sync_file_list

    @staticmethod
    def sync_files(src_path: Path, dst_path: Path) -> None:
        """同步文件 (增量同步)

        :param src_path`(Path|str)`: 同步文件的源路径
        :param dst_path`(Path|str)`: 同步文件到的路径
        """
        from tqdm import tqdm

        logger.info("增量同步文件: %s -> %s", src_path, dst_path)
        file_list = Utils.get_sync_files(src_path, dst_path)
        if len(file_list) == 0:
            logger.info("没有需要同步的文件")
            return
        for file in tqdm(file_list, desc="同步文件"):
            dst = dst_path / file.relative_to(src_path)
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(file, dst)
            except Exception as e:
                traceback.print_exc()
                logger.error("同步 %s 到 %s 时发生错误: %s", file, dst, e)
                if dst.exists():
                    logger.warning("删除未复制完成的文件: %s", dst)
                    try:
                        os.remove(dst)
                    except Exception as e:
                        logger.error("删除未复制完成的文件失败: %s", e)

        logger.info("同步文件完成")

    @staticmethod
    def sync_files_and_create_symlink(
        src_path: Path | str,
        link_path: Path | str,
        src_is_file: bool | None = False,
    ) -> None:
        """同步文件并创建软链接

        :param src_path`(Path|str)`: 源路径
        :param link_path`(Path|str)`: 软链接路径
        :parma src_is_file`(bool|None)`: 源路径是否为文件
        :notes
            当源路径不存在时, 则尝试创建源路径, 并检查链接路径状态

            链接路径若已存在, 并且存在文件, 将检查链接路径中的文件是否存在于源路径中

            在链接路径存在但在源路径不存在的文件将被复制 (增量同步)

            完成增量同步后将链接路径属性, 若为实际路径则对该路径进行重命名; 如果为链接路径则删除链接

            链接路径清理完成后, 在链接路径为源路径创建软链接
        """
        src_path = (
            Path(src_path)
            if not isinstance(src_path, Path) and src_path is not None
            else src_path
        )
        link_path = (
            Path(link_path)
            if not isinstance(link_path, Path) and link_path is not None
            else link_path
        )
        logger.info("链接路径: %s -> %s", src_path, link_path)
        try:
            if src_is_file:
                src_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                src_path.mkdir(parents=True, exist_ok=True)
            if link_path.exists():
                Utils.sync_files(
                    src_path=link_path,
                    dst_path=src_path if not src_is_file else src_path.parent,
                )
                if link_path.is_symlink():
                    link_path.unlink()
                else:
                    shutil.move(
                        link_path,
                        link_path.parent / str(uuid.uuid4()),
                    )
            link_path.symlink_to(src_path)
        except Exception as e:
            logger.error("创建 %s -> %s 的路径链接失败: %s", src_path, link_path, e)


class MultiThreadDownloader:
    """通用多线程下载器"""

    def __init__(
        self,
        download_func: Callable,
        download_args_list: list[Any] | None = None,
        download_kwargs_list: list[dict[str, Any]] | None = None,
    ) -> None:
        """多线程下载器初始化

        :param download_func`(Callable)`: 执行下载任务的函数
        :param download_args_list`(list[Any])`: 传入下载函数的参数列表
        :param download_kwargs_list`(list[dict[str,Any]])`: 传入下载函数的参数字典列表

        :notes
            下载参数列表, 每个元素是一个子列表或字典, 包含传递给下载函数的参数

            格式示例:
            ```python
            # 仅使用位置参数
            download_args_list = [
                [arg1, arg2, arg3, ...],  # 第一个下载任务的参数
                [arg1, arg2, arg3, ...],  # 第二个下载任务的参数
                [arg1, arg2, arg3, ...],  # 第三个下载任务的参数
            ]

            # 仅使用关键字参数
            download_kwargs_list = [
                {"param1": value1, "param2": value2},  # 第一个下载任务的参数
                {"param1": value3, "param2": value4},  # 第二个下载任务的参数
                {"param1": value5, "param2": value6},  # 第三个下载任务的参数
            ]

            # 混合使用位置参数和关键字参数
            download_args_list = [
                [arg1, arg2],
                [arg3, arg4],
                [arg5, arg6],
            ]
            download_kwargs_list = [
                {"param1": value1, "param2": value2},
                {"param1": value3, "param2": value4},
                {"param1": value5, "param2": value6},
            ]
            ```
        """
        self.download_func = download_func
        self.download_args_list = download_args_list or []
        self.download_kwargs_list = download_kwargs_list or []
        self.queue = queue.Queue()
        self.total_tasks = max(
            len(download_args_list or []), len(download_kwargs_list or [])
        )  # 记录总的下载任务数 (以参数列表长度为准)
        self.completed_count = 0  # 记录已完成的任务数
        self.lock = threading.Lock()  # 创建锁以保护对计数器的访问
        self.retry = None
        self.start_time = None

    def worker(self) -> None:
        """工作线程函数, 执行下载任务"""
        while True:
            task = self.queue.get()
            if task is None:
                break

            args, kwargs = task
            count = 0
            while count < self.retry:
                count += 1
                try:
                    self.download_func(*args, **kwargs)
                    break
                except Exception as e:
                    traceback.print_exc()
                    logger.error(
                        "[%s/%s] 执行 %s 时发生错误: %s",
                        count,
                        self.retry,
                        self.download_func,
                        e,
                    )
                    if count < self.retry:
                        logger.warning("[%s/%s] 重试执行中", count, self.retry)

            self.queue.task_done()
            with self.lock:  # 访问共享资源时加锁
                self.completed_count += 1
                self.print_progress()  # 打印进度

    def print_progress(self) -> None:
        """进度条显示"""
        progress = (self.completed_count / self.total_tasks) * 100
        current_time = datetime.datetime.now()
        time_interval = current_time - self.start_time
        hours = time_interval.seconds // 3600
        minutes = (time_interval.seconds // 60) % 60
        seconds = time_interval.seconds % 60
        formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}"

        if self.completed_count > 0:
            speed = self.completed_count / time_interval.total_seconds()
        else:
            speed = 0

        remaining_tasks = self.total_tasks - self.completed_count

        if speed > 0:
            estimated_remaining_time_seconds = remaining_tasks / speed
            estimated_remaining_time = datetime.timedelta(
                seconds=estimated_remaining_time_seconds
            )
            estimated_hours = estimated_remaining_time.seconds // 3600
            estimated_minutes = (estimated_remaining_time.seconds // 60) % 60
            estimated_seconds = estimated_remaining_time.seconds % 60
            formatted_estimated_time = (
                f"{estimated_hours:02}:{estimated_minutes:02}:{estimated_seconds:02}"
            )
        else:
            formatted_estimated_time = "N/A"

        logger.info(
            "下载进度: %.2f%% | %d/%d [%s<%s, %.2f it/s]",
            progress,
            self.completed_count,
            self.total_tasks,
            formatted_time,
            formatted_estimated_time,
            speed,
        )

    def start(
        self,
        num_threads: int | None = 16,
        retry: int | None = 3,
    ) -> None:
        """启动多线程下载器

        :param num_threads`(int)`: 下载线程数, 默认为 16
        :param retry`(int)`: 重试次数, 默认为 3
        """

        # 将重试次数作为属性传递给下载函数
        self.retry = retry

        threads = []
        self.start_time = datetime.datetime.now()
        time.sleep(0.1)  # 避免 print_progress() 计算时间时出现 division by zero

        # 启动工作线程
        for _ in range(num_threads):
            thread = threading.Thread(target=self.worker)
            thread.start()
            threads.append(thread)

        # 准备下载任务参数
        max_tasks = max(len(self.download_args_list), len(self.download_kwargs_list))

        # 将下载任务添加到队列
        for i in range(max_tasks):
            # 获取位置参数
            args = (
                self.download_args_list[i] if i < len(self.download_args_list) else []
            )

            # 获取关键字参数
            kwargs = (
                self.download_kwargs_list[i]
                if i < len(self.download_kwargs_list)
                else {}
            )

            # 将任务参数打包
            self.queue.put((args, kwargs))

        # 等待所有任务完成
        self.queue.join()

        # 停止所有工作线程
        for _ in range(num_threads):
            self.queue.put(None)

        for thread in threads:
            thread.join()


class RepoManager:
    """HuggingFace / ModelScope 仓库管理器"""

    def __init__(
        self,
        hf_token: str | None = None,
        ms_token: str | None = None,
    ) -> None:
        """HuggingFace / ModelScope 仓库管理器初始化

        :param hf_token`(str|None)`: HugggingFace Token, 不为`None`时配置`HF_TOKEN`环境变量
        :param ms_token`(str|None)`: ModelScope Token, 不为`None`时配置`MODELSCOPE_API_TOKEN`环境变量
        """
        try:
            from huggingface_hub import HfApi

            self.hf_api = HfApi(token=hf_token)
            if hf_token is not None:
                os.environ["HF_TOKEN"] = hf_token
                self.hf_token = hf_token
        except Exception as e:
            logger.warning("HuggingFace 库未安装, 部分功能将不可用: %s", e)
        try:
            from modelscope import HubApi

            self.ms_api = HubApi()
            if ms_token is not None:
                os.environ["MODELSCOPE_API_TOKEN"] = ms_token
                self.ms_api.login(access_token=ms_token)
                self.ms_token = ms_token
        except Exception as e:
            logger.warning("ModelScope 库未安装, 部分功能将不可用: %s", e)

    def get_repo_file(
        self,
        api_type: Literal["huggingface", "modelscope"],
        repo_id: str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        retry: int | None = 3,
    ) -> list[str]:
        """获取 HuggingFace / ModelScope 仓库文件列表

        :param api_type`(Literal["huggingface","modelscope"])`: Api 类型
        :param repo_id`(str)`: HuggingFace / ModelScope 仓库 ID
        :param repo_type`(str)`: HuggingFace / ModelScope 仓库类型
        :param retry`(int|None)`: 重试次数
        :return `list[str]`: 仓库文件列表
        """
        if api_type == "huggingface":
            logger.info(
                "获取 HuggingFace 仓库 %s (类型: %s) 的文件列表", repo_id, repo_type
            )
            return self.get_hf_repo_files(repo_id, repo_type, retry)
        if api_type == "modelscope":
            logger.info(
                "获取 ModelScope 仓库 %s (类型: %s) 的文件列表", repo_id, repo_type
            )
            return self.get_ms_repo_files(repo_id, repo_type, retry)

        logger.error("未知 Api 类型: %s", api_type)
        return []

    def get_hf_repo_files(
        self,
        repo_id: str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        retry: int | None = 3,
    ) -> list[str]:
        """获取 HuggingFace 仓库文件列表

        :param repo_id`(str)`: HuggingFace 仓库 ID
        :param repo_type`(str)`: HuggingFace 仓库类型
        :param retry`(int|None)`: 重试次数
        :return `list[str]`: 仓库文件列表
        """
        count = 0
        while count < retry:
            count += 1
            try:
                return self.hf_api.list_repo_files(
                    repo_id=repo_id,
                    repo_type=repo_type,
                )
            except Exception as e:
                logger.error(
                    "[%s/%s] 获取 %s (类型: %s) 仓库的文件列表出现错误: %s",
                    count,
                    retry,
                    repo_id,
                    repo_type,
                    e,
                )
                traceback.print_exc()
                if count < retry:
                    logger.warning("[%s/%s] 重试获取文件列表中", count, retry)
        return []

    def get_ms_repo_files(
        self,
        repo_id: str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        retry: int | None = 3,
    ) -> list[str]:
        """获取 ModelScope 仓库文件列表

        :param repo_id`(str)`: ModelScope 仓库 ID
        :param repo_type`(str)`: ModelScope 仓库类型
        :param retry`(int|None)`: 重试次数
        :return `list[str]`: 仓库文件列表
        """
        file_list = []
        count = 0

        def _get_file_path(repo_files: list) -> list[str]:
            """获取 ModelScope Api 返回的仓库列表中的模型路径"""
            return [file["Path"] for file in repo_files if file["Type"] != "tree"]

        if repo_type == "model":
            while count < retry:
                count += 1
                try:
                    repo_files = self.ms_api.get_model_files(
                        model_id=repo_id, recursive=True
                    )
                    file_list = _get_file_path(repo_files)
                    break
                except Exception as e:
                    traceback.print_exc()
                    logger.error(
                        "[%s/%s] 获取 %s (类型: %s) 仓库的文件列表出现错误: %s",
                        count,
                        retry,
                        repo_id,
                        repo_type,
                        e,
                    )
                    if count < retry:
                        logger.warning("[%s/%s] 重试获取文件列表中", count, retry)
        elif repo_type == "dataset":
            while count < retry:
                count += 1
                try:
                    repo_files = self.ms_api.get_dataset_files(
                        repo_id=repo_id, recursive=True
                    )
                    file_list = _get_file_path(repo_files)
                    break
                except Exception as e:
                    traceback.print_exc()
                    logger.error(
                        "[%s/%s] 获取 %s (类型: %s) 仓库的文件列表出现错误: %s",
                        count,
                        retry,
                        repo_id,
                        repo_type,
                        e,
                    )
                    if count < retry:
                        logger.warning("[%s/%s] 重试获取文件列表中", count, retry)
        elif repo_type == "space":
            # TODO: 支持创空间
            logger.error("%s 仓库类型为创空间, 不支持获取文件列表", repo_id)
        else:
            logger.error("未知的 %s 仓库类型", repo_type)

        return file_list

    def check_repo(
        self,
        api_type: Literal["huggingface", "modelscope"],
        repo_id: str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        visibility: bool | None = False,
    ) -> bool:
        """检查 HuggingFace / ModelScope 仓库是否存在, 当不存在时则自动创建

        :param api_type`(Literal["huggingface","modelscope"])`: Api 类型
        :param repo_id`(str)`: 仓库 ID
        :param repo_type`(str)`: 仓库类型
        :return `bool`: 检查成功时 / 创建仓库成功时返回`True`
        """
        if api_type == "huggingface":
            return self.check_hf_repo(repo_id, repo_type, visibility)
        if api_type == "modelscope":
            return self.check_ms_repo(repo_id, repo_type, visibility)

        logger.error("未知 Api 类型: %s", api_type)
        return False

    def check_hf_repo(
        self,
        repo_id: str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        visibility: bool | None = False,
    ) -> bool:
        """检查 HuggingFace 仓库是否存在, 当不存在时则自动创建

        :param repo_id`(str)`: HuggingFace 仓库 ID
        :param repo_type`(str)`: HuggingFace 仓库类型
        :param visibility`(bool|None)`: HuggingFace 仓库可见性
        :return `bool`: 检查成功时 / 创建仓库成功时返回`True`
        """
        if repo_type in ["model", "dataset", "space"]:
            try:
                if not self.hf_api.repo_exists(repo_id=repo_id, repo_type=repo_type):
                    self.hf_api.create_repo(
                        repo_id=repo_id, repo_type=repo_type, private=visibility
                    )
                return True
            except Exception as e:
                traceback.print_exc()
                logger.error("检查 HuggingFace 仓库时发生错误: %s", e)
                return False

        logger.error("未知 HuggingFace 仓库类型: %s", repo_type)
        return False

    def check_ms_repo(
        self,
        repo_id: str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        visibility: bool | None = False,
    ) -> bool:
        """检查 ModelScope 仓库是否存在, 当不存在时则自动创建

        :param repo_id`(str)`: ModelScope 仓库 ID
        :param repo_type`(str)`: ModelScope 仓库类型
        :param visibility`(bool|None)`: HuggingFace 仓库可见性
        :return `bool`: 检查成功时 / 创建仓库成功时返回`True`
        """
        from modelscope.hub.constants import Visibility

        if repo_type in ["model", "dataset"]:
            try:
                if not self.ms_api.repo_exists(
                    repo_id=repo_id,
                    repo_type=repo_type,
                    token=self.ms_token,
                ):
                    self.ms_api.create_repo(
                        repo_id=repo_id,
                        repo_type=repo_type,
                        visibility=Visibility.PUBLIC
                        if visibility
                        else Visibility.PRIVATE,
                        token=self.ms_token,
                    )
                return True
            except Exception as e:
                traceback.print_exc()
                logger.error("检查 ModelScope 仓库时发生错误: %s", e)
                return False
        if repo_type == "space":
            logger.error("未支持 ModelScope 创空间")
            return False

        logger.error("未知 ModelScope 仓库类型: %s", repo_type)
        return False

    def upload_files_to_repo(
        self,
        api_type: Literal["huggingface", "modelscope"],
        repo_id: str,
        upload_path: Path | str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        visibility: bool | None = False,
        retry: int | None = 3,
    ) -> None:
        """上传文件夹中的内容到 HuggingFace / ModelScope 仓库中

        :param api_type`(Literal["huggingface","modelscope"])`: Api 类型
        :param repo_id`(str)`: 仓库 ID
        :param repo_type`(str)`: 仓库类型
        :param upload_path`(Path|str)`: 要上传的文件夹
        :param visibility`(bool|None)`: 当仓库不存在时自动创建的仓库的可见性
        :param retry`(int|None)`: 上传重试次数
        """
        if api_type in ["huggingface", "modelscope"]:
            if not self.check_repo(
                api_type=api_type,
                repo_id=repo_id,
                repo_type=repo_type,
                visibility=visibility,
            ):
                logger.error("检查 %s (类型: %s) 仓库失败, 无法上传文件")
                return

        upload_path = (
            Path(upload_path)
            if not isinstance(upload_path, Path) and upload_path is not None
            else upload_path
        )

        if api_type == "huggingface":
            self.upload_files_to_huggingface(
                repo_id=repo_id,
                repo_type=repo_type,
                upload_path=upload_path,
                retry=retry,
            )
        elif api_type == "modelscope":
            self.upload_files_to_modelscope(
                repo_id=repo_id,
                repo_type=repo_type,
                upload_path=upload_path,
                retry=retry,
            )
        else:
            logger.error("未知 Api 类型: %s", api_type)

    def upload_files_to_huggingface(
        self,
        repo_id: str,
        upload_path: Path | str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        retry: int | None = 3,
    ) -> None:
        """上传文件夹中的内容到 HuggingFace 仓库中

        :param repo_id`(str)`: HuggingFace 仓库 ID
        :param repo_type`(str)`: HuggingFace 仓库类型
        :param upload_path`(Path|str)`: 要上传到 HuggingFace 仓库的文件夹
        :param retry`(int|None)`: 上传重试次数
        """
        upload_files = Utils.get_file_list(upload_path)
        repo_files = set(
            self.get_repo_file(
                api_type="huggingface",
                repo_id=repo_id,
                repo_type=repo_type,
                retry=retry,
            )
        )
        logger.info(
            "上传到 HuggingFace 仓库: %s -> HuggingFace/%s", upload_path, repo_id
        )
        files_count = len(upload_files)
        count = 0
        for upload_file in upload_files:
            count += 1
            upload_file_rel_path = upload_file.relative_to(upload_path).as_posix()
            if upload_file_rel_path in repo_files:
                logger.info(
                    "[%s/%s] %s 已存在于 HuggingFace 仓库中, 跳过上传",
                    count,
                    files_count,
                    upload_file,
                )
                continue

            logger.info(
                "[%s/%s] 上传 %s 到 %s (类型: %s) 仓库中",
                count,
                files_count,
                upload_file,
                repo_id,
                repo_type,
            )
            retry_num = 0
            while retry_num < retry:
                try:
                    self.hf_api.upload_file(
                        repo_id=repo_id,
                        repo_type=repo_type,
                        path_in_repo=upload_file_rel_path,
                        path_or_fileobj=upload_file,
                        commit_message=f"Upload {upload_file.name}",
                    )
                    break
                except Exception as e:
                    logger.error(
                        "[%s/%s] 上传 %s 时发生错误: %s",
                        count,
                        files_count,
                        upload_file.name,
                        e,
                    )
                    traceback.print_exc()
                    if retry_num < retry:
                        logger.warning(
                            "[%s/%s] 重试上传 %s", count, files_count, upload_file.name
                        )

        logger.info(
            "[%s/%s] 上传 %s 到 %s (类型: %s) 完成",
            count,
            files_count,
            upload_path,
            repo_id,
            repo_type,
        )

    def upload_files_to_modelscope(
        self,
        repo_id: str,
        upload_path: Path | str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        retry: int | None = 3,
    ) -> None:
        """上传文件夹中的内容到 ModelScope 仓库中

        :param repo_id`(str)`: ModelScope 仓库 ID
        :param repo_type`(str)`: ModelScope 仓库类型
        :param upload_path`(Path|str)`: 要上传到 ModelScope 仓库的文件夹
        :param retry`(int|None)`: 上传重试次数
        """
        upload_files = Utils.get_file_list(upload_path)
        repo_files = set(
            self.get_repo_file(
                api_type="modelscope",
                repo_id=repo_id,
                repo_type=repo_type,
                retry=retry,
            )
        )
        logger.info("上传到 ModelScope 仓库: %s -> ModelScope/%s", upload_path, repo_id)
        files_count = len(upload_files)
        count = 0
        for upload_file in upload_files:
            count += 1
            upload_file_rel_path = upload_file.relative_to(upload_path).as_posix()
            if upload_file_rel_path in repo_files:
                logger.info(
                    "[%s/%s] %s 已存在于 ModelScope 仓库中, 跳过上传",
                    count,
                    files_count,
                    upload_file,
                )
                continue

            logger.info(
                "[%s/%s] 上传 %s 到 %s (类型: %s) 仓库中",
                count,
                files_count,
                upload_file,
                repo_id,
                repo_type,
            )
            retry_num = 0
            while retry_num < retry:
                try:
                    self.ms_api.upload_file(
                        repo_id=repo_id,
                        repo_type=repo_type,
                        path_in_repo=upload_file_rel_path,
                        path_or_fileobj=upload_file,
                        commit_message=f"Upload {upload_file.name}",
                        token=self.ms_token,
                    )
                    break
                except Exception as e:
                    logger.error(
                        "[%s/%s] 上传 %s 时发生错误: %s",
                        count,
                        files_count,
                        upload_file.name,
                        e,
                    )
                    traceback.print_exc()
                    if retry_num < retry:
                        logger.warning(
                            "[%s/%s] 重试上传 %s", count, files_count, upload_file.name
                        )

        logger.info(
            "[%s/%s] 上传 %s 到 %s (类型: %s) 完成",
            count,
            files_count,
            upload_path,
            repo_id,
            repo_type,
        )

    def download_files_from_repo(
        self,
        api_type: Literal["huggingface", "modelscope"],
        repo_id: str,
        local_dir: Path | str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        folder: str | None = None,
        retry: int | None = 3,
        num_threads: int | None = 16,
    ) -> Path:
        """从 HuggingFace / ModelScope 仓库下载文文件

        :param api_type`(Literal["huggingface","modelscope"])`: Api 类型
        :param repo_id`(str)`: 仓库 ID
        :param repo_type`(Literal["model","dataset","space"])`: 仓库类型
        :param local_dir`(Path|str)`: 下载路径
        :param folder`(str|None)`: 指定下载某个文件夹, 未指定时则下载整个文件夹
        :param retry`(int|None)`: 重试下载的次数
        :param num_threads`(int|None)`: 下载线程
        :return `Path`: 下载路径
        :notes
            `folder`参数未指定时, 则下载 HuggingFace / ModelScope 仓库中的所有文件, 如果`folder`参数指定了, 例如指定的是`aaaki`

            而仓库的文件结构如下:

            ```markdown
            HuggingFace / ModelScope Repositories
            ├── Nachoneko
            │   ├── 1_nachoneko
            │   │       ├── [メロンブックス (よろず)]Melonbooks Girls Collection 2019 winter 麗.png
            │   │       ├── [メロンブックス (よろず)]Melonbooks Girls Collection 2019 winter 麗.txt
            │   │       ├── [メロンブックス (よろず)]Melonbooks Girls Collection 2020 spring 彩 (オリジナル).png
            │   │       └── [メロンブックス (よろず)]Melonbooks Girls Collection 2020 spring 彩 (オリジナル).txt
            │   ├── 2_nachoneko
            │   │       ├── 0(8).txt
            │   │       ├── 0(8).webp
            │   │       ├── 001_2.png
            │   │       └── 001_2.txt
            │   └── 4_nachoneko
            │           ├── 0b1c8893-c9aa-49e5-8769-f90c4b6866f5.png
            │           ├── 0b1c8893-c9aa-49e5-8769-f90c4b6866f5.txt
            │           ├── 0d5149dd-3bc1-484f-8c1e-a1b94bab3be5.png
            │           └── 0d5149dd-3bc1-484f-8c1e-a1b94bab3be5.txt
            └ aaaki
                ├── 1_aaaki
                │   ├── 1.png
                │   ├── 1.txt
                │   ├── 11.png
                │   ├── 11.txt
                │   ├── 12.png
                │   └── 12.txt
                └── 3_aaaki
                    ├── 14.png
                    ├── 14.txt
                    ├── 16.png
                    └── 16.txt
            ```

            则使用该函数下载 HuggingFace / ModelScope 仓库的文件时将下载`aaaki`文件夹中的所有文件, 而`Nachoneko`文件夹中的文件不会被下载

            `folder`参数使用的是前缀匹配方式, 从路径的开头的字符串进行匹配, 匹配成功则进行下载

            如果要指定下载某个文件, 则`folder`参数需要指定该文件在仓库中的完整路径, 比如`aaaki/1_aaaki/1.png`, 此时只会下载该文件, 其他文件不会被下载

            文件下载下来后, 保存路径为`local_dir/<文件在仓库中的路径>`, 比如`local_dir`为`/kaggle/dataset`, 上面下载单个文件的例子下载下载下来的文件就会保存在`/kaggle/dataset/aaaki/1_aaaki/1.png`
        """
        local_dir = (
            Path(local_dir)
            if not isinstance(local_dir, Path) and local_dir is not None
            else local_dir
        )

        logger.info("从 %s (类型: %s) 下载文件中", repo_id, repo_type)
        if api_type == "huggingface":
            self.download_files_from_huggingface(
                repo_id=repo_id,
                repo_type=repo_type,
                local_dir=local_dir,
                folder=folder,
                retry=retry,
                num_threads=num_threads,
            )
            return local_dir

        if api_type == "modelscope":
            self.download_files_from_modelscope(
                repo_id=repo_id,
                repo_type=repo_type,
                local_dir=local_dir,
                folder=folder,
                retry=retry,
                num_threads=num_threads,
            )
            return local_dir

        logger.error("未知 Api 类型: %s", api_type)
        return None

    def download_files_from_huggingface(
        self,
        repo_id: str,
        local_dir: Path | str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        folder: str | None = None,
        retry: int | None = 3,
        num_threads: int | None = 16,
    ) -> None:
        """从 HuggingFace 仓库下载文文件

        :param repo_id`(str)`: HuggingFace 仓库 ID
        :param repo_type`(Literal["model","dataset","space"])`: HuggingFace 仓库类型
        :param local_dir`(Path|str)`: 下载路径
        :param folder`(str|None)`: 指定下载某个文件夹, 未指定时则下载整个文件夹
        :param retry`(int|None)`: 重试下载的次数
        :param num_threads`(int|None)`: 下载线程
        """
        from huggingface_hub import hf_hub_download

        repo_files = self.get_repo_file(
            api_type="huggingface",
            repo_id=repo_id,
            repo_type=repo_type,
            retry=retry,
        )
        download_task = []

        for repo_file in repo_files:
            if folder is not None and not repo_file.startswith(folder):
                continue
            download_task.append(
                {
                    "repo_id": repo_id,
                    "repo_type": repo_type,
                    "local_dir": local_dir,
                    "filename": repo_file,
                }
            )

        if folder is not None:
            logger.info("指定下载文件: %s", folder)
        logger.info("下载文件数量: %s", len(download_task))

        files_downloader = MultiThreadDownloader(
            download_func=hf_hub_download, download_kwargs_list=download_task
        )
        files_downloader.start(
            num_threads=num_threads,
            retry=retry,
        )

    def download_files_from_modelscope(
        self,
        repo_id: str,
        local_dir: Path | str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        folder: str | None = None,
        retry: int | None = 3,
        num_threads: int | None = 16,
    ) -> None:
        """从 ModelScope 仓库下载文文件

        :param repo_id`(str)`: ModelScope 仓库 ID
        :param repo_type`(Literal["model","dataset","space"])`: ModelScope 仓库类型
        :param local_dir`(Path|str)`: 下载路径
        :param folder`(str|None)`: 指定下载某个文件夹, 未指定时则下载整个文件夹
        :param retry`(int|None)`: 重试下载的次数
        :param num_threads`(int|None)`: 下载线程
        """
        from modelscope import snapshot_download

        repo_files = self.get_repo_file(
            api_type="modelscope",
            repo_id=repo_id,
            repo_type=repo_type,
            retry=retry,
        )
        download_task = []

        for repo_file in repo_files:
            if folder is not None and not repo_file.startswith(folder):
                continue
            download_task.append(
                {
                    "repo_id": repo_id,
                    "repo_type": repo_type,
                    "local_dir": local_dir,
                    "allow_patterns": repo_file,
                }
            )

        if folder is not None:
            logger.info("指定下载文件: %s", folder)
        logger.info("下载文件数量: %s", len(download_task))

        files_downloader = MultiThreadDownloader(
            download_func=snapshot_download, download_kwargs_list=download_task
        )
        files_downloader.start(
            num_threads=num_threads,
            retry=retry,
        )


class MirrorConfigManager:
    """PyPI, HuggingFace, Github 镜像管理工具"""

    @staticmethod
    def set_pypi_index_mirror(mirror: str | None = None) -> None:
        """设置 PyPI Index 镜像源

        :param mirror`(str|None)`: PyPI 镜像源链接, 当不传入镜像源链接时则清除镜像源
        """
        if mirror is not None:
            logger.info(
                "使用 PIP_INDEX_URL, UV_DEFAULT_INDEX 环境变量设置 PyPI Index 镜像源"
            )
            os.environ["PIP_INDEX_URL"] = mirror
            os.environ["UV_DEFAULT_INDEX"] = mirror
        else:
            logger.info(
                "清除 PIP_INDEX_URL, UV_DEFAULT_INDEX 环境变量, 取消使用 PyPI Index 镜像源"
            )
            os.environ.pop("PIP_INDEX_URL", None)
            os.environ.pop("UV_DEFAULT_INDEX", None)

    @staticmethod
    def set_pypi_extra_index_mirror(mirror: str | None = None) -> None:
        """设置 PyPI Extra Index 镜像源

        :param mirror`(str|None)`: PyPI 镜像源链接, 当不传入镜像源链接时则清除镜像源
        """
        if mirror is not None:
            logger.info(
                "使用 PIP_EXTRA_INDEX_URL, UV_INDEX 环境变量设置 PyPI Extra Index 镜像源"
            )
            os.environ["PIP_EXTRA_INDEX_URL"] = mirror
            os.environ["UV_INDEX"] = mirror
        else:
            logger.info(
                "清除 PIP_EXTRA_INDEX_URL, UV_INDEX 环境变量, 取消使用 PyPI Extra Index 镜像源"
            )
            os.environ.pop("PIP_EXTRA_INDEX_URL", None)
            os.environ.pop("UV_INDEX", None)

    @staticmethod
    def set_pypi_find_links_mirror(mirror: str | None = None) -> None:
        """设置 PyPI Find Links 镜像源

        :param mirror`(str|None)`: PyPI 镜像源链接, 当不传入镜像源链接时则清除镜像源
        """
        if mirror is not None:
            logger.info(
                "使用 PIP_FIND_LINKS, UV_FIND_LINKS 环境变量设置 PyPI Find Links 镜像源"
            )
            os.environ["PIP_FIND_LINKS"] = mirror
            os.environ["UV_FIND_LINKS"] = mirror
        else:
            logger.info(
                "清除 PIP_FIND_LINKS, UV_FIND_LINKS 环境变量, 取消使用 PyPI Find Links 镜像源"
            )
            os.environ.pop("PIP_FIND_LINKS", None)
            os.environ.pop("UV_FIND_LINKS", None)

    @staticmethod
    def set_github_mirror(
        mirror: str | list | None = None, config_path: Path | str = None
    ) -> None:
        """设置 Github 镜像源

        :param mirror`(str|list|None)`: Github 镜像源地址

        :notes
            当`mirror`传入的是 Github 镜像源地址, 则直接设置 GIT_CONFIG_GLOBAL 环境变量并直接使用该镜像源地址

            如果传入的是镜像源列表, 则自动测试可用的 Github 镜像源并设置 GIT_CONFIG_GLOBAL 环境变量

            当不传入参数时则清除 GIT_CONFIG_GLOBAL 环境变量并删除 GIT_CONFIG_GLOBAL 环境变量对应的 Git 配置文件

            使用:
            ```python
            set_github_mirror() # 不传入参数时则清除 Github 镜像源

            set_github_mirror("https://ghfast.top/https://github.com") # 只设置一个 Github 镜像源时将直接使用该 Github 镜像源

            set_github_mirror( # 传入 Github 镜像源列表时将自动测试可用的 Github 镜像源并设置
                [
                    "https://ghfast.top/https://github.com",
                    "https://mirror.ghproxy.com/https://github.com",
                    "https://ghproxy.net/https://github.com",
                    "https://gh.api.99988866.xyz/https://github.com",
                    "https://gh-proxy.com/https://github.com",
                    "https://ghps.cc/https://github.com",
                    "https://gh.idayer.com/https://github.com",
                    "https://ghproxy.1888866.xyz/github.com",
                    "https://slink.ltd/https://github.com",
                    "https://github.boki.moe/github.com",
                    "https://github.moeyy.xyz/https://github.com",
                    "https://gh-proxy.net/https://github.com",
                    "https://gh-proxy.ygxz.in/https://github.com",
                    "https://wget.la/https://github.com",
                    "https://kkgithub.com",
                    "https://gitclone.com/github.com",
                ]
            )
            ```
        """
        if mirror is None:
            logger.info("清除 GIT_CONFIG_GLOBAL 环境变量, 取消使用 Github 镜像源")
            git_config = os.environ.pop("GIT_CONFIG_GLOBAL", None)
            if git_config is not None:
                p = Path(git_config)
                if p.exists():
                    p.unlink()
            return

        if config_path is None:
            config_path = os.getcwd()

        config_path = (
            Path(config_path)
            if not isinstance(config_path, Path) and config_path is not None
            else config_path
        )
        git_config_path = config_path / ".gitconfig"
        os.environ["GIT_CONFIG_GLOBAL"] = git_config_path.as_posix()

        if isinstance(mirror, str):
            logger.info("通过 GIT_CONFIG_GLOBAL 环境变量设置 Github 镜像源")
            try:
                run_cmd(
                    [
                        "git",
                        "config",
                        "--global",
                        f"url.{mirror}.insteadOf",
                        "https://github.com",
                    ]
                )
            except Exception as e:
                logger.error("设置 Github 镜像源时发生错误: %s", e)
        elif isinstance(mirror, list):
            mirror_test_path = config_path / "__github_mirror_test__"
            custon_env = os.environ.copy()
            custon_env.pop("GIT_CONFIG_GLOBAL", None)
            for gh in mirror:
                logger.info("测试 Github 镜像源: %s", gh)
                test_repo = f"{gh}/licyk/empty"
                if mirror_test_path.exists():
                    remove_files(mirror_test_path)
                try:
                    run_cmd(
                        ["git", "clone", test_repo, mirror_test_path.as_posix()],
                        custom_env=custon_env,
                        live=False,
                    )
                    if mirror_test_path.exists():
                        remove_files(mirror_test_path)
                    run_cmd(
                        [
                            "git",
                            "config",
                            "--global",
                            f"url.{gh}.insteadOf",
                            "https://github.com",
                        ]
                    )
                    logger.info("该镜像源可用")
                    return
                except Exception as _:
                    logger.info("镜像源不可用")

            logger.info("无可用的 Github 镜像源, 取消使用 Github 镜像源")
            if git_config_path.exists():
                git_config_path.unlink()
            os.environ.pop("GIT_CONFIG_GLOBAL", None)
        else:
            logger.info("未知镜像源参数类型: %s", type(mirror))
            return

    @staticmethod
    def set_huggingface_mirror(mirror: str | None = None) -> None:
        """设置 HuggingFace 镜像源

        :param mirror`(str|None)`: HuggingFace 镜像源链接, 当不传入镜像源链接时则清除镜像源
        """
        if mirror is not None:
            logger.info("使用 HF_ENDPOINT 环境变量设置 HuggingFace 镜像源")
            os.environ["HF_ENDPOINT"] = mirror
        else:
            logger.info("清除 HF_ENDPOINT 环境变量, 取消使用 HuggingFace 镜像源")
            os.environ.pop("HF_ENDPOINT", None)

    @staticmethod
    def set_mirror(
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list | None = None,
        huggingface_mirror: str | None = None,
    ) -> None:
        """镜像源设置

        :param pypi_index_mirror`(str|None)`: PyPI Index 镜像源链接
        :param pypi_extra_index_mirror`(str|None)`: PyPI Extra Index 镜像源链接
        :param pypi_find_links_mirror`(str|None)`: PyPI Find Links 镜像源链接
        :param github_mirror`(str|list|None)`: Github 镜像源链接或者镜像源链接列表
        :param huggingface_mirror`(str|None)`: HuggingFace 镜像源链接
        """
        logger.info("配置镜像源中")
        MirrorConfigManager.set_pypi_index_mirror(pypi_index_mirror)
        MirrorConfigManager.set_pypi_extra_index_mirror(pypi_extra_index_mirror)
        MirrorConfigManager.set_pypi_find_links_mirror(pypi_find_links_mirror)
        MirrorConfigManager.set_github_mirror(github_mirror)
        MirrorConfigManager.set_huggingface_mirror(huggingface_mirror)
        logger.info("镜像源配置完成")

    @staticmethod
    def configure_pip() -> None:
        """使用环境变量配置 Pip / uv"""
        logger.info("配置 Pip / uv")
        os.environ["UV_HTTP_TIMEOUT"] = "30"
        os.environ["UV_CONCURRENT_DOWNLOADS"] = "50"
        os.environ["UV_INDEX_STRATEGY"] = "unsafe-best-match"
        os.environ["UV_PYTHON"] = sys.executable
        os.environ["UV_NO_PROGRESS"] = "1"
        os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        os.environ["PIP_NO_WARN_SCRIPT_LOCATION"] = "0"
        os.environ["PIP_TIMEOUT"] = "30"
        os.environ["PIP_RETRIES"] = "5"
        os.environ["PYTHONUTF8"] = "1"
        os.environ["PYTHONIOENCODING"] = "utf8"


class TunnelManager:
    """内网穿透工具"""

    def __init__(self, workspace: Path | str, port: int) -> None:
        """内网穿透工具初始化

        :param workspace`(Path|str)`: 工作区路径
        :param port`(int)`: 要进行端口映射的端口
        """
        self.workspace = Path(workspace)
        self.port = port

    def ngrok(self, ngrok_token: str | None = None) -> str | None:
        """使用 Ngrok 内网穿透

        :param ngrok_token`(str)`: Ngrok 账号 Token
        :return `str`: Ngrok 内网穿透生成的访问地址
        """
        if ngrok_token is None:
            return None
        logger.info("启动 Ngrok 内网穿透")
        try:
            from pyngrok import conf, ngrok
        except Exception as _:
            try:
                EnvManager.pip_install("pyngrok")
                from pyngrok import conf, ngrok
            except Exception as e:
                logger.error("安装 Ngrok 内网穿透模块失败: %s", e)
                return None

        try:
            conf.get_default().auth_token = ngrok_token
            conf.get_default().monitor_thread = False
            ssh_tunnels = ngrok.get_tunnels(conf.get_default())
            if len(ssh_tunnels) == 0:
                ssh_tunnel = ngrok.connect(self.port, bind_tls=True)
                return ssh_tunnel.public_url
            else:
                return ssh_tunnels[0].public_url
        except Exception as e:
            logger.error("启动 Ngrok 内网穿透时出现了错误: %s", e)
            return None

    def cloudflare(self) -> str | None:
        """使用 CloudFlare 内网穿透

        :return `str`: CloudFlare 内网穿透生成的访问地址
        """
        logger.info("启动 CloudFlare 内网穿透")
        try:
            from pycloudflared import try_cloudflare
        except Exception as _:
            try:
                EnvManager.pip_install("pycloudflared")
                from pycloudflared import try_cloudflare
            except Exception as e:
                logger.error("安装 CloudFlare 内网穿透失败: %s", e)
                return None

        try:
            return try_cloudflare(self.port).tunnel
        except Exception as e:
            logger.error("启动 CloudFlare 内网穿透时出现了错误: %s", e)
            return None

    def gradio(self) -> str | None:
        """使用 Gradio 进行内网穿透

        :return `(str|None)`: 使用内网穿透得到的访问地址, 如果启动内网穿透失败则不返回地址
        """
        logger.info("启动 Gradio 内网穿透")
        try:
            from gradio_tunneling.main import setup_tunnel
        except Exception as _:
            try:
                EnvManager.pip_install("gradio-tunneling")
                from gradio_tunneling.main import setup_tunnel
            except Exception as e:
                logger.error("安装 Gradio Tunneling 内网穿透时出现了错误: %s", e)
                return None

        try:
            tunnel_url = setup_tunnel(
                local_host="127.0.0.1",
                local_port=self.port,
                share_token=secrets.token_urlsafe(32),
                share_server_address=None,
            )
            return tunnel_url
        except Exception as e:
            logger.error("启动 Gradio 内网穿透时出现错误: %s", e)
            return None

    def gen_key(self, path: Path | str) -> bool:
        """生成 SSH 密钥

        :param path`(str|Path)`: 生成 SSH 密钥的路径
        :return `bool`: 生成成功时返回`True`
        """
        path = Path(path) if not isinstance(path, Path) and path is not None else path
        try:
            arg_string = f'ssh-keygen -t rsa -b 4096 -N "" -q -f {path.as_posix()}'
            args = shlex.split(arg_string)
            subprocess.run(args, check=True)
            path.chmod(0o600)
            return True
        except Exception as e:
            logger.error("生成 SSH 密钥失败: %s", e)
            return False

    def ssh_tunnel(
        self,
        launch_args: list,
        host_pattern: re.Pattern[str],
        line_limit: int,
    ) -> str | None:
        """使用 SSH 进行内网穿透

        :param launch_args`(list)`: 启动 SSH 内网穿透的参数
        :param host_pattern`(re.Pattern[str])`: 用于匹配内网穿透地址的正则表达式
        :param line_limit`(int)`: 内网穿透地址所在的输出行数
        :return `str|None`: 内网穿透地址
        :notes
            基础 SSH 命令为: `ssh -o StrictHostKeyChecking=no -i <ssh_path>`
        """
        ssh_name = "id_rsa"
        ssh_path = self.workspace / ssh_name

        tmp = None
        if not ssh_path.exists():
            if not self.gen_key(ssh_path):
                tmp = TemporaryDirectory()
                ssh_path = Path(tmp.name) / ssh_name
                self.gen_key(ssh_path)

        command = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            ssh_path.as_posix(),
        ] + launch_args
        command_str = shlex.join(command) if isinstance(command, list) else command
        tunnel = subprocess.Popen(
            command_str,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding="utf-8",
        )

        output_queue = queue.Queue()
        lines = []

        def _read_output():
            for line in iter(tunnel.stdout.readline, ""):
                output_queue.put(line)
            tunnel.stdout.close()

        thread = threading.Thread(target=_read_output)
        thread.daemon = True
        thread.start()

        for _ in range(line_limit):
            try:
                line = output_queue.get(timeout=10)
                lines.append(line)
                if line.startswith("Warning"):
                    print(line, end="")

                url_match = host_pattern.search(line)
                if url_match:
                    return url_match.group("url")
            except queue.Empty:
                break

        return None

    def localhost_run(self) -> str | None:
        """使用 localhost.run 进行内网穿透

        :param `(str|None)`: 使用内网穿透得到的访问地址, 如果启动内网穿透失败则不返回地址
        """
        logger.info("启动 localhost.run 内网穿透")
        urls = self.ssh_tunnel(
            launch_args=["-R", f"80:127.0.0.1:{self.port}", "localhost.run"],
            host_pattern=re.compile(r"(?P<url>https?://\S+\.lhr\.life)"),
            line_limit=27,
        )
        if urls is not None:
            return urls
        logger.error("启动 localhost.run 内网穿透失败")
        return None

    def remote_moe(self) -> str | None:
        """使用 remote.moe 进行内网穿透

        :param `(str|None)`: 使用内网穿透得到的访问地址, 如果启动内网穿透失败则不返回地址
        """
        logger.info("启动 remote.moe 内网穿透")
        urls = self.ssh_tunnel(
            launch_args=["-R", f"80:127.0.0.1:{self.port}", "remote.moe"],
            host_pattern=re.compile(r"(?P<url>https?://\S+\.remote\.moe)"),
            line_limit=10,
        )
        if urls is not None:
            return urls
        logger.error("启动 remote.moe 内网穿透失败")
        return None

    def pinggy_io(self) -> str | None:
        """使用 pinggy.io 进行内网穿透

        :param `(str|None)`: 使用内网穿透得到的访问地址, 如果启动内网穿透失败则不返回地址
        """
        logger.info("启动 pinggy.io 内网穿透")
        urls = self.ssh_tunnel(
            launch_args=["-p", "443", f"-R0:127.0.0.1:{self.port}", "free.pinggy.io"],
            host_pattern=re.compile(r"(?P<url>https?://\S+\.pinggy\.link)"),
            line_limit=10,
        )
        if urls is not None:
            return urls
        logger.error("启动 pinggy.io 内网穿透失败")
        return None

    def start_tunnel(
        self,
        use_ngrok: bool | None = False,
        ngrok_token: str | None = None,
        use_cloudflare: bool | None = False,
        use_remote_moe: bool | None = False,
        use_localhost_run: bool | None = False,
        use_gradio: bool | None = False,
        use_pinggy_io: bool | None = False,
        message: str | None = None,
    ) -> tuple[str]:
        """启动内网穿透

        :param use_ngrok`(bool|None)`: 启用 Ngrok 内网穿透
        :param ngrok_token`(str|None)`: Ngrok 账号 Token
        :param use_cloudflare`(bool|None)`: 启用 CloudFlare 内网穿透
        :param use_remote_moe`(bool|None)`: 启用 remote.moe 内网穿透
        :param use_localhost_run`(bool|None)`: 使用 localhost.run 内网穿透
        :param use_gradio`(bool|None)`: 使用 Gradio 内网穿透
        :param use_pinggy_io`(bool|None)`: 使用 pinggy.io 内网穿透
        :param message`(str|None)`: 描述信息
        :return `tuple[str]`: 内网穿透地址
        """

        if any(
            [
                use_cloudflare,
                use_ngrok and ngrok_token,
                use_remote_moe,
                use_localhost_run,
                use_gradio,
                use_pinggy_io,
            ]
        ):
            logger.info("启动内网穿透")
        else:
            return

        cloudflare_url = self.cloudflare() if use_cloudflare else None
        ngrok_url = self.ngrok(ngrok_token) if use_ngrok and ngrok_token else None
        remote_moe_url = self.remote_moe() if use_remote_moe else None
        localhost_run_url = self.localhost_run() if use_localhost_run else None
        gradio_url = self.gradio() if use_gradio else None
        pinggy_io_url = self.pinggy_io() if use_pinggy_io else None

        logger.info("http://127.0.0.1:%s 的内网穿透地址", self.port)
        print(
            "=================================================================================="
        )
        if message is not None:
            print(f"{message}")
        print(f":: CloudFlare: {cloudflare_url}")
        print(f":: Ngrok: {ngrok_url}")
        print(f":: remote.moe: {remote_moe_url}")
        print(f":: localhost_run: {localhost_run_url}")
        print(f":: Gradio: {gradio_url}")
        print(f":: pinggy.io: {pinggy_io_url}")
        print(
            "=================================================================================="
        )
        return (
            cloudflare_url,
            ngrok_url,
            remote_moe_url,
            localhost_run_url,
            gradio_url,
            pinggy_io_url,
        )


class RequirementCheck:
    """依赖检查工具"""

    # 提取版本标识符组件的正则表达式
    # ref:
    # https://peps.python.org/pep-0440
    # https://packaging.python.org/en/latest/specifications/version-specifiers
    VERSION_PATTERN = r"""
        v?
        (?:
            (?:(?P<epoch>[0-9]+)!)?                           # epoch
            (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
            (?P<pre>                                          # pre-release
                [-_\.]?
                (?P<pre_l>(a|b|c|rc|alpha|beta|pre|preview))
                [-_\.]?
                (?P<pre_n>[0-9]+)?
            )?
            (?P<post>                                         # post release
                (?:-(?P<post_n1>[0-9]+))
                |
                (?:
                    [-_\.]?
                    (?P<post_l>post|rev|r)
                    [-_\.]?
                    (?P<post_n2>[0-9]+)?
                )
            )?
            (?P<dev>                                          # dev release
                [-_\.]?
                (?P<dev_l>dev)
                [-_\.]?
                (?P<dev_n>[0-9]+)?
            )?
        )
        (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
    """

    # 编译正则表达式
    package_version_parse_regex = re.compile(
        r"^\s*" + VERSION_PATTERN + r"\s*$",
        re.VERBOSE | re.IGNORECASE,
    )

    # 定义版本组件的命名元组
    VersionComponent = namedtuple(
        "VersionComponent",
        [
            "epoch",
            "release",
            "pre_l",
            "pre_n",
            "post_n1",
            "post_l",
            "post_n2",
            "dev_l",
            "dev_n",
            "local",
            "is_wildcard",
        ],
    )

    @staticmethod
    def parse_version(version_str: str) -> VersionComponent:
        """解释 Python 软件包版本号

        参数:
            version_str (`str`):
                Python 软件包版本号

        返回值:
            `VersionComponent`: 版本组件的命名元组

        异常:
            `ValueError`: 如果 Python 版本号不符合 PEP440 规范
        """
        # 检测并剥离通配符
        wildcard = version_str.endswith(".*") or version_str.endswith("*")
        clean_str = version_str.rstrip("*").rstrip(".") if wildcard else version_str

        match = RequirementCheck.package_version_parse_regex.match(clean_str)
        if not match:
            logger.error(f"未知的版本号字符串: {version_str}")
            raise ValueError(f"Invalid version string: {version_str}")

        components = match.groupdict()

        # 处理 release 段 (允许空字符串)
        release_str = components["release"] or "0"
        release_segments = [int(seg) for seg in release_str.split(".")]

        # 构建命名元组
        return RequirementCheck.VersionComponent(
            epoch=int(components["epoch"] or 0),
            release=release_segments,
            pre_l=components["pre_l"],
            pre_n=int(components["pre_n"]) if components["pre_n"] else None,
            post_n1=int(components["post_n1"]) if components["post_n1"] else None,
            post_l=components["post_l"],
            post_n2=int(components["post_n2"]) if components["post_n2"] else None,
            dev_l=components["dev_l"],
            dev_n=int(components["dev_n"]) if components["dev_n"] else None,
            local=components["local"],
            is_wildcard=wildcard,
        )

    @staticmethod
    def compare_version_objects(v1: VersionComponent, v2: VersionComponent) -> int:
        """比较两个版本字符串 Python 软件包版本号

        参数:
            v1 (`VersionComponent`):
                第 1 个 Python 版本号标识符组件
            v2 (`VersionComponent`):
                第 2 个 Python 版本号标识符组件

        返回值:
            `int`: 如果版本号 1 大于 版本号 2, 则返回`1`, 小于则返回`-1`, 如果相等则返回`0`
        """

        # 比较 epoch
        if v1.epoch != v2.epoch:
            return v1.epoch - v2.epoch

        # 对其 release 长度, 缺失部分补 0
        if len(v1.release) != len(v2.release):
            for _ in range(abs(len(v1.release) - len(v2.release))):
                if len(v1.release) < len(v2.release):
                    v1.release.append(0)
                else:
                    v2.release.append(0)

        # 比较 release
        for n1, n2 in zip(v1.release, v2.release):
            if n1 != n2:
                return n1 - n2
        # 如果 release 长度不同，较短的版本号视为较小 ?
        # 但是这样是行不通的! 比如 0.15.0 和 0.15, 处理后就会变成 [0, 15, 0] 和 [0, 15]
        # 计算结果就会变成 len([0, 15, 0]) > len([0, 15])
        # 但 0.15.0 和 0.15 实际上是一样的版本
        # if len(v1.release) != len(v2.release):
        #     return len(v1.release) - len(v2.release)

        # 比较 pre-release
        if v1.pre_l and not v2.pre_l:
            return -1  # pre-release 小于正常版本
        elif not v1.pre_l and v2.pre_l:
            return 1
        elif v1.pre_l and v2.pre_l:
            pre_order = {
                "a": 0,
                "b": 1,
                "c": 2,
                "rc": 3,
                "alpha": 0,
                "beta": 1,
                "pre": 0,
                "preview": 0,
            }
            if pre_order[v1.pre_l] != pre_order[v2.pre_l]:
                return pre_order[v1.pre_l] - pre_order[v2.pre_l]
            elif v1.pre_n is not None and v2.pre_n is not None:
                return v1.pre_n - v2.pre_n
            elif v1.pre_n is None and v2.pre_n is not None:
                return -1
            elif v1.pre_n is not None and v2.pre_n is None:
                return 1

        # 比较 post-release
        if v1.post_n1 is not None:
            post_n1 = v1.post_n1
        elif v1.post_l:
            post_n1 = int(v1.post_n2) if v1.post_n2 else 0
        else:
            post_n1 = 0

        if v2.post_n1 is not None:
            post_n2 = v2.post_n1
        elif v2.post_l:
            post_n2 = int(v2.post_n2) if v2.post_n2 else 0
        else:
            post_n2 = 0

        if post_n1 != post_n2:
            return post_n1 - post_n2

        # 比较 dev-release
        if v1.dev_l and not v2.dev_l:
            return -1  # dev-release 小于 post-release 或正常版本
        elif not v1.dev_l and v2.dev_l:
            return 1
        elif v1.dev_l and v2.dev_l:
            if v1.dev_n is not None and v2.dev_n is not None:
                return v1.dev_n - v2.dev_n
            elif v1.dev_n is None and v2.dev_n is not None:
                return -1
            elif v1.dev_n is not None and v2.dev_n is None:
                return 1

        # 比较 local version
        if v1.local and not v2.local:
            return -1  # local version 小于 dev-release 或正常版本
        elif not v1.local and v2.local:
            return 1
        elif v1.local and v2.local:
            local1 = v1.local.split(".")
            local2 = v2.local.split(".")
            # 和 release 的处理方式一致, 对其 local version 长度, 缺失部分补 0
            if len(local1) != len(local2):
                for _ in range(abs(len(local1) - len(local2))):
                    if len(local1) < len(local2):
                        local1.append(0)
                    else:
                        local2.append(0)
            for l1, l2 in zip(local1, local2):
                if l1.isdigit() and l2.isdigit():
                    l1, l2 = int(l1), int(l2)
                if l1 != l2:
                    return (l1 > l2) - (l1 < l2)
            return len(local1) - len(local2)

        return 0  # 版本相同

    @staticmethod
    def compare_versions(version1: str, version2: str) -> int:
        """比较两个版本字符串 Python 软件包版本号

        参数:
            version1 (`str`):
                版本号 1
            version2 (`str`):
                版本号 2

        返回值:
            `int`: 如果版本号 1 大于 版本号 2, 则返回`1`, 小于则返回`-1`, 如果相等则返回`0`
        """
        v1 = RequirementCheck.parse_version(version1)
        v2 = RequirementCheck.parse_version(version2)
        return RequirementCheck.compare_version_objects(v1, v2)

    @staticmethod
    def compatible_version_matcher(spec_version: str):
        """PEP 440 兼容性版本匹配 (~= 操作符)

        返回值:
            `_is_compatible(version_str: str) -> bool`: 一个接受 version_str (`str`) 参数的判断函数
        """
        # 解析规范版本
        spec = RequirementCheck.parse_version(spec_version)

        # 获取有效 release 段 (去除末尾的零)
        clean_release = []
        for num in spec.release:
            if num != 0 or (clean_release and clean_release[-1] != 0):
                clean_release.append(num)

        # 确定最低版本和前缀匹配规则
        if len(clean_release) == 0:
            logger.error("解析到错误的兼容性发行版本号")
            raise ValueError("Invalid version for compatible release clause")

        # 生成前缀匹配模板 (忽略后缀)
        prefix_length = len(clean_release) - 1
        if prefix_length == 0:
            # 处理类似 ~= 2 的情况 (实际 PEP 禁止，但这里做容错)
            prefix_pattern = [spec.release[0]]
            min_version = RequirementCheck.parse_version(f"{spec.release[0]}")
        else:
            prefix_pattern = list(spec.release[:prefix_length])
            min_version = spec

        def _is_compatible(version_str: str) -> bool:
            target = RequirementCheck.parse_version(version_str)

            # 主版本前缀检查
            target_prefix = target.release[: len(prefix_pattern)]
            if target_prefix != prefix_pattern:
                return False

            # 最低版本检查 (自动忽略 pre/post/dev 后缀)
            return RequirementCheck.compare_version_objects(target, min_version) >= 0

        return _is_compatible

    @staticmethod
    def version_match(spec: str, version: str) -> bool:
        """PEP 440 版本前缀匹配

        参数:
            spec (`str`): 版本匹配表达式 (e.g. '1.1.*')
            version (`str`): 需要检测的实际版本号 (e.g. '1.1a1')

        返回值:
            `bool`: 是否匹配
        """
        # 分离通配符和本地版本
        spec_parts = spec.split("+", 1)
        spec_main = spec_parts[0].rstrip(".*")  # 移除通配符
        has_wildcard = spec.endswith(".*") and "+" not in spec

        # 解析规范版本 (不带通配符)
        try:
            spec_ver = RequirementCheck.parse_version(spec_main)
        except ValueError:
            return False

        # 解析目标版本 (忽略本地版本)
        target_ver = RequirementCheck.parse_version(version.split("+", 1)[0])

        # 前缀匹配规则
        if has_wildcard:
            # 生成补零后的 release 段
            spec_release = spec_ver.release.copy()
            while len(spec_release) < len(target_ver.release):
                spec_release.append(0)

            # 比较前 N 个 release 段 (N 为规范版本长度)
            return (
                target_ver.release[: len(spec_ver.release)] == spec_ver.release
                and target_ver.epoch == spec_ver.epoch
            )
        else:
            # 严格匹配时使用原比较函数
            return RequirementCheck.compare_versions(spec_main, version) == 0

    @staticmethod
    def is_v1_ge_v2(v1: str, v2: str) -> bool:
        """查看 Python 版本号 v1 是否大于或等于 v2

        参数:
            v1 (`str`):
                第 1 个 Python 软件包版本号

            v2 (`str`):
                第 2 个 Python 软件包版本号

        返回值:
            `bool`: 如果 v1 版本号大于或等于 v2 版本号则返回`True`
            e.g.:
                1.1, 1.0 -> True
                1.0, 1.0 -> True
                0.9, 1.0 -> False
        """
        return RequirementCheck.compare_versions(v1, v2) >= 0

    @staticmethod
    def is_v1_gt_v2(v1: str, v2: str) -> bool:
        """查看 Python 版本号 v1 是否大于 v2

        参数:
            v1 (`str`):
                第 1 个 Python 软件包版本号

            v2 (`str`):
                第 2 个 Python 软件包版本号

        返回值:
            `bool`: 如果 v1 版本号大于 v2 版本号则返回`True`
            e.g.:
                1.1, 1.0 -> True
                1.0, 1.0 -> False
        """
        return RequirementCheck.compare_versions(v1, v2) > 0

    @staticmethod
    def is_v1_eq_v2(v1: str, v2: str) -> bool:
        """查看 Python 版本号 v1 是否等于 v2

        参数:
            v1 (`str`):
                第 1 个 Python 软件包版本号

            v2 (`str`):
                第 2 个 Python 软件包版本号

        返回值:
            `bool`: 如果 v1 版本号等于 v2 版本号则返回`True`
            e.g.:
                1.0, 1.0 -> True
                0.9, 1.0 -> False
                1.1, 1.0 -> False
        """
        return RequirementCheck.compare_versions(v1, v2) == 0

    @staticmethod
    def is_v1_lt_v2(v1: str, v2: str) -> bool:
        """查看 Python 版本号 v1 是否小于 v2

        参数:
            v1 (`str`):
                第 1 个 Python 软件包版本号

            v2 (`str`):
                第 2 个 Python 软件包版本号

        返回值:
            `bool`: 如果 v1 版本号小于 v2 版本号则返回`True`
            e.g.:
                0.9, 1.0 -> True
                1.0, 1.0 -> False
        """
        return RequirementCheck.compare_versions(v1, v2) < 0

    @staticmethod
    def is_v1_le_v2(v1: str, v2: str) -> bool:
        """查看 Python 版本号 v1 是否小于或等于 v2

        参数:
            v1 (`str`):
                第 1 个 Python 软件包版本号

            v2 (`str`):
                第 2 个 Python 软件包版本号

        返回值:
            `bool`: 如果 v1 版本号小于或等于 v2 版本号则返回`True`
            e.g.:
                0.9, 1.0 -> True
                1.0, 1.0 -> True
                1.1, 1.0 -> False
        """
        return RequirementCheck.compare_versions(v1, v2) <= 0

    @staticmethod
    def is_v1_c_eq_v2(v1: str, v2: str) -> bool:
        """查看 Python 版本号 v1 是否大于等于 v2, (兼容性版本匹配)

        参数:
            v1 (`str`):
                第 1 个 Python 软件包版本号, 该版本由 ~= 符号指定

            v2 (`str`):
                第 2 个 Python 软件包版本号

        返回值:
            `bool`: 如果 v1 版本号等于 v2 版本号则返回`True`
            e.g.:
                1.0*, 1.0a1 -> True
                0.9*, 1.0 -> False
        """
        func = RequirementCheck.compatible_version_matcher(v1)
        return func(v2)

    @staticmethod
    def version_string_is_canonical(version: str) -> bool:
        """判断版本号标识符是否符合标准

        参数:
            version (`str`):
                版本号字符串

        返回值:
            `bool`: 如果版本号标识符符合 PEP 440 标准, 则返回`True`

        """
        return (
            re.match(
                r"^([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?$",
                version,
            )
            is not None
        )

    @staticmethod
    def is_package_has_version(package: str) -> bool:
        """检查 Python 软件包是否指定版本号

        参数:
            package (`str`):
                Python 软件包名

        返回值:
            `bool`: 如果 Python 软件包存在版本声明, 如`torch==2.3.0`, 则返回`True`
        """
        return package != (
            package.replace("===", "")
            .replace("~=", "")
            .replace("!=", "")
            .replace("<=", "")
            .replace(">=", "")
            .replace("<", "")
            .replace(">", "")
            .replace("==", "")
        )

    @staticmethod
    def get_package_name(package: str) -> str:
        """获取 Python 软件包的包名, 去除末尾的版本声明

        参数:
            package (`str`):
                Python 软件包名

        返回值:
            `str`: 返回去除版本声明后的 Python 软件包名
        """
        return (
            package.split("===")[0]
            .split("~=")[0]
            .split("!=")[0]
            .split("<=")[0]
            .split(">=")[0]
            .split("<")[0]
            .split(">")[0]
            .split("==")[0]
            .strip()
        )

    @staticmethod
    def get_package_version(package: str) -> str:
        """获取 Python 软件包的包版本号

        参数:
            package (`str`):
                Python 软件包名

        返回值:
            `str`: 返回 Python 软件包的包版本号
        """
        return (
            package.split("===")
            .pop()
            .split("~=")
            .pop()
            .split("!=")
            .pop()
            .split("<=")
            .pop()
            .split(">=")
            .pop()
            .split("<")
            .pop()
            .split(">")
            .pop()
            .split("==")
            .pop()
            .strip()
        )

    WHEEL_PATTERN = r"""
        ^                           # 字符串开始
        (?P<distribution>[^-]+)     # 包名 (匹配第一个非连字符段)
        -                           # 分隔符
        (?:                         # 版本号和可选构建号组合
            (?P<version>[^-]+)      # 版本号 (至少一个非连字符段)
            (?:-(?P<build>\d\w*))?  # 可选构建号 (以数字开头)
        )
        -                           # 分隔符
        (?P<python>[^-]+)           # Python 版本标签
        -                           # 分隔符
        (?P<abi>[^-]+)              # ABI 标签
        -                           # 分隔符
        (?P<platform>[^-]+)         # 平台标签
        \.whl$                      # 固定后缀
    """

    @staticmethod
    def parse_wheel_filename(filename: str) -> str:
        """解析 Python wheel 文件名并返回 distribution 名称

        参数:
            filename (`str`):
                wheel 文件名, 例如 pydantic-1.10.15-py3-none-any.whl

        返回值:
            `str`: distribution 名称, 例如 pydantic

        异常:
            `ValueError`: 如果文件名不符合 PEP491 规范
        """
        match = re.fullmatch(RequirementCheck.WHEEL_PATTERN, filename, re.VERBOSE)
        if not match:
            logger.error("未知的 Wheel 文件名: %s", filename)
            raise ValueError(f"Invalid wheel filename: {filename}")
        return match.group("distribution")

    @staticmethod
    def parse_wheel_version(filename: str) -> str:
        """解析 Python wheel 文件名并返回 version 名称

        参数:
            filename (`str`):
                wheel 文件名, 例如 pydantic-1.10.15-py3-none-any.whl

        返回值:
            `str`: version 名称, 例如 1.10.15

        异常:
            `ValueError`: 如果文件名不符合 PEP491 规范
        """
        match = re.fullmatch(RequirementCheck.WHEEL_PATTERN, filename, re.VERBOSE)
        if not match:
            logger.error("未知的 Wheel 文件名: %s", filename)
            raise ValueError(f"Invalid wheel filename: {filename}")
        return match.group("version")

    @staticmethod
    def parse_wheel_to_package_name(filename: str) -> str:
        """解析 Python wheel 文件名并返回 <distribution>==<version>

        参数:
            filename (`str`):
                wheel 文件名, 例如 pydantic-1.10.15-py3-none-any.whl

        返回值:
            `str`: <distribution>==<version> 名称, 例如 pydantic==1.10.15
        """
        distribution = RequirementCheck.parse_wheel_filename(filename)
        version = RequirementCheck.parse_wheel_version(filename)
        return f"{distribution}=={version}"

    @staticmethod
    def remove_optional_dependence_from_package(filename: str) -> str:
        """移除 Python 软件包声明中可选依赖

        参数:
            filename (`str`):
                Python 软件包名

        返回值:
            `str`: 移除可选依赖后的软件包名, e.g. diffusers[torch]==0.10.2 -> diffusers==0.10.2
        """
        return re.sub(r"\[.*?\]", "", filename)

    @staticmethod
    def parse_requirement_list(requirements: list) -> list:
        """将 Python 软件包声明列表解析成标准 Python 软件包名列表

        参数:
            requirements (`list`):
                Python 软件包名声明列表
                e.g:
                ```python
                requirements = [
                    'torch==2.3.0',
                    'diffusers[torch]==0.10.2',
                    'NUMPY',
                    '-e .',
                    '--index-url https://pypi.python.org/simple',
                    '--extra-index-url https://download.pytorch.org/whl/cu124',
                    '--find-links https://download.pytorch.org/whl/torch_stable.html',
                    '-e git+https://github.com/Nerogar/mgds.git@2c67a5a#egg=mgds',
                    'git+https://github.com/WASasquatch/img2texture.git',
                    'https://github.com/Panchovix/pydantic-fixreforge/releases/download/main_v1/pydantic-1.10.15-py3-none-any.whl',
                    'prodigy-plus-schedule-free==1.9.1 # prodigy+schedulefree optimizer',
                    'protobuf<5,>=4.25.3',
                ]
                ```

        返回值:
            `list`: 将 Python 软件包名声明列表解析成标准声明列表
            e.g. 上述例子中的软件包名声明列表将解析成:
            ```python
                requirements = [
                    'torch==2.3.0',
                    'diffusers==0.10.2',
                    'numpy',
                    'mgds',
                    'img2texture',
                    'pydantic==1.10.15',
                    'prodigy-plus-schedule-free==1.9.1',
                    'protobuf<5',
                    'protobuf>=4.25.3',
                ]
                ```
        """
        package_list = []
        canonical_package_list = []
        requirement: str
        for requirement in requirements:
            requirement = requirement.strip()
            logger.debug("原始 Python 软件包名: %s", requirement)

            if (
                requirement is None
                or requirement == ""
                or requirement.startswith("#")
                or "# skip_verify" in requirement
                or requirement.startswith("--index-url")
                or requirement.startswith("--extra-index-url")
                or requirement.startswith("--find-links")
                or requirement.startswith("-e .")
            ):
                continue

            # -e git+https://github.com/Nerogar/mgds.git@2c67a5a#egg=mgds -> mgds
            # git+https://github.com/WASasquatch/img2texture.git -> img2texture
            # git+https://github.com/deepghs/waifuc -> waifuc
            if requirement.startswith("-e git+http") or requirement.startswith(
                "git+http"
            ):
                egg_match = re.search(r"egg=([^#&]+)", requirement)
                if egg_match:
                    package_list.append(egg_match.group(1).split("-")[0])
                    continue

                package_name = os.path.basename(requirement)
                package_name = (
                    package_name.split(".git")[0]
                    if package_name.endswith(".git")
                    else package_name
                )
                package_list.append(package_name)
                continue

            # https://github.com/Panchovix/pydantic-fixreforge/releases/download/main_v1/pydantic-1.10.15-py3-none-any.whl -> pydantic==1.10.15
            if requirement.startswith("https://") or requirement.startswith("http://"):
                package_name = RequirementCheck.parse_wheel_to_package_name(
                    os.path.basename(requirement)
                )
                package_list.append(package_name)
                continue

            # 常规 Python 软件包声明
            # prodigy-plus-schedule-free==1.9.1 # prodigy+schedulefree optimizer -> prodigy-plus-schedule-free==1.9.1
            cleaned_requirements = (
                re.sub(r"\s*#.*$", "", requirement).strip().split(",")
            )
            if len(cleaned_requirements) > 1:
                package_name = RequirementCheck.get_package_name(
                    cleaned_requirements[0].strip()
                )
                for package_name_with_version_marked in cleaned_requirements:
                    version_symbol = str.replace(
                        package_name_with_version_marked, package_name, "", 1
                    )
                    format_package_name = (
                        RequirementCheck.remove_optional_dependence_from_package(
                            f"{package_name}{version_symbol}".strip()
                        )
                    )
                    package_list.append(format_package_name)
            else:
                format_package_name = (
                    RequirementCheck.remove_optional_dependence_from_package(
                        cleaned_requirements[0].strip()
                    )
                )
                package_list.append(format_package_name)

        # 处理包名大小写并统一成小写
        for p in package_list:
            p: str = p.lower().strip()
            logger.debug("预处理后的 Python 软件包名: %s", p)
            if not RequirementCheck.is_package_has_version(p):
                logger.debug("%s 无版本声明", p)
                canonical_package_list.append(p)
                continue

            if RequirementCheck.version_string_is_canonical(
                RequirementCheck.get_package_version(p)
            ):
                canonical_package_list.append(p)
            else:
                logger.debug("%s 软件包名的版本不符合标准", p)

        return canonical_package_list

    @staticmethod
    def remove_duplicate_object_from_list(origin: list) -> list:
        """对`list`进行去重

        参数:
            origin (`list`):
                原始的`list`

        返回值:
            `list`: 去重后的`list`, e.g. [1, 2, 3, 2] -> [1, 2, 3]
        """
        return list(set(origin))

    @staticmethod
    def read_packages_from_requirements_file(file_path: str | Path) -> list:
        """从 requirements.txt 文件中读取 Python 软件包版本声明列表

        参数:
            file_path (`str`, `Path`):
                requirements.txt 文件路径

        返回值:
            `list`: 从 requirements.txt 文件中读取的 Python 软件包声明列表
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.readlines()
        except Exception as e:
            logger.error("打开 %s 时出现错误: %s\n请检查文件是否出现损坏", file_path, e)
            return []

    @staticmethod
    def get_package_version_from_library(package_name: str) -> str | None:
        """获取已安装的 Python 软件包版本号

        参数:
            package_name (`str`):

        返回值:
            (`str` | `None`): 如果获取到 Python 软件包版本号则返回版本号字符串, 否则返回`None`
        """
        try:
            ver = importlib.metadata.version(package_name)
        except Exception as _:
            ver = None

        if ver is None:
            try:
                ver = importlib.metadata.version(package_name.lower())
            except Exception as _:
                ver = None

        if ver is None:
            try:
                ver = importlib.metadata.version(package_name.replace("_", "-"))
            except Exception as _:
                ver = None

        return ver

    @staticmethod
    def is_package_installed(package: str) -> bool:
        """判断 Python 软件包是否已安装在环境中

        参数:
            package (`str`):
                Python 软件包名

        返回值:
            `bool`: 如果 Python 软件包未安装或者未安装正确的版本, 则返回`False`
        """
        # 分割 Python 软件包名和版本号
        if "===" in package:
            pkg_name, pkg_version = [x.strip() for x in package.split("===")]
        elif "~=" in package:
            pkg_name, pkg_version = [x.strip() for x in package.split("~=")]
        elif "!=" in package:
            pkg_name, pkg_version = [x.strip() for x in package.split("!=")]
        elif "<=" in package:
            pkg_name, pkg_version = [x.strip() for x in package.split("<=")]
        elif ">=" in package:
            pkg_name, pkg_version = [x.strip() for x in package.split(">=")]
        elif "<" in package:
            pkg_name, pkg_version = [x.strip() for x in package.split("<")]
        elif ">" in package:
            pkg_name, pkg_version = [x.strip() for x in package.split(">")]
        elif "==" in package:
            pkg_name, pkg_version = [x.strip() for x in package.split("==")]
        else:
            pkg_name, pkg_version = package.strip(), None

        env_pkg_version = RequirementCheck.get_package_version_from_library(pkg_name)
        logger.debug(
            "已安装 Python 软件包检测: pkg_name: %s, env_pkg_version: %s, pkg_version: %s",
            pkg_name,
            env_pkg_version,
            pkg_version,
        )

        if env_pkg_version is None:
            return False

        if pkg_version is not None:
            # ok = env_pkg_version === / == pkg_version
            if "===" in package or "==" in package:
                logger.debug("包含条件: === / ==")
                if RequirementCheck.is_v1_eq_v2(env_pkg_version, pkg_version):
                    logger.debug("%s == %s", env_pkg_version, pkg_version)
                    return True

            # ok = env_pkg_version ~= pkg_version
            if "~=" in package:
                logger.debug("包含条件: ~=")
                if RequirementCheck.is_v1_c_eq_v2(pkg_version, env_pkg_version):
                    logger.debug("%s ~= %s", pkg_version, env_pkg_version)
                    return True

            # ok = env_pkg_version != pkg_version
            if "!=" in package:
                logger.debug("包含条件: !=")
                if not RequirementCheck.is_v1_eq_v2(env_pkg_version, pkg_version):
                    logger.debug("%s != %s", env_pkg_version, pkg_version)
                    return True

            # ok = env_pkg_version <= pkg_version
            if "<=" in package:
                logger.debug("包含条件: <=")
                if RequirementCheck.is_v1_le_v2(env_pkg_version, pkg_version):
                    logger.debug("%s <= %s", env_pkg_version, pkg_version)
                    return True

            # ok = env_pkg_version >= pkg_version
            if ">=" in package:
                logger.debug("包含条件: >=")
                if RequirementCheck.is_v1_ge_v2(env_pkg_version, pkg_version):
                    logger.debug("%s >= %s", env_pkg_version, pkg_version)
                    return True

            # ok = env_pkg_version < pkg_version
            if "<" in package:
                logger.debug("包含条件: <")
                if RequirementCheck.is_v1_lt_v2(env_pkg_version, pkg_version):
                    logger.debug("%s < %s", env_pkg_version, pkg_version)
                    return True

            # ok = env_pkg_version > pkg_version
            if ">" in package:
                logger.debug("包含条件: >")
                if RequirementCheck.is_v1_gt_v2(env_pkg_version, pkg_version):
                    logger.debug("%s > %s", env_pkg_version, pkg_version)
                    return True

            logger.debug("%s 需要安装", package)
            return False

        return True

    @staticmethod
    def validate_requirements(requirement_path: str | Path) -> bool:
        """检测环境依赖是否完整

        参数:
            requirement_path (`str`, `Path`):
                依赖文件路径

        返回值:
            `bool`: 如果有缺失依赖则返回`False`
        """
        origin_requires = RequirementCheck.read_packages_from_requirements_file(
            requirement_path
        )
        requires = RequirementCheck.parse_requirement_list(origin_requires)
        for package in requires:
            if not RequirementCheck.is_package_installed(package):
                return False

        return True

    @staticmethod
    def check_env(
        requirement_path: Path | str,
        name: str | None = None,
        use_uv: bool | None = True,
    ) -> None:
        """检测依赖完整性并安装缺失依赖

        :param requirement_path`(Path|str)`: 依赖文件路径
        :param name`(str|None)`: 显示的名称
        :param use_uv`(bool|None)`: 是否使用 uv 安装依赖
        """
        if not os.path.exists(requirement_path):
            logger.error(f"未找到 {requirement_path} 文件, 无法检查依赖完整性")
            return
        if name is None:
            name = str(requirement_path).split("/")[-2]
        logger.info(f"检查 {name} 依赖完整性中")
        if not RequirementCheck.validate_requirements(requirement_path):
            logger.info(f"安装 {name} 依赖中")
            try:
                EnvManager.install_requirements(requirement_path, use_uv)
                logger.info(f"安装 {name} 依赖完成")
            except Exception as e:
                logger.error(f"安装 {name} 依赖出现错误: {e}")
                return
        logger.info(f"{name} 依赖完整性检查完成")

    @staticmethod
    def check_numpy(use_uv: bool | None = True) -> None:
        """检查 Numpy 是否需要降级

        :param use_uv`(bool|None)`: 是否使用 uv 安装依赖
        """
        logger.info("检查 Numpy 是否需要降级")
        try:
            numpy_ver = importlib.metadata.version("numpy")
            if RequirementCheck.is_v1_gt_v2(numpy_ver, "1.26.4"):
                logger.info("降级 Numoy 中")
                EnvManager.pip_install("numpy==1.26.4", use_uv=use_uv)
                logger.info("Numpy 降级完成")
            else:
                logger.info("Numpy 无需降级")
        except Exception as e:
            logger.error(f"检查 Numpy 时出现错误: {e}")

    @staticmethod
    def fix_torch() -> None:
        """检测并修复 PyTorch 的 libomp 问题"""
        logger.info("检测 PyTorch 的 libomp 问题")
        try:
            torch_spec = importlib.util.find_spec("torch")
            for folder in torch_spec.submodule_search_locations:
                lib_folder = os.path.join(folder, "lib")
                test_file = os.path.join(lib_folder, "fbgemm.dll")
                dest = os.path.join(lib_folder, "libomp140.x86_64.dll")
                if os.path.exists(dest):
                    break

                with open(test_file, "rb") as f:
                    contents = f.read()
                    if b"libomp140.x86_64.dll" not in contents:
                        break
                try:
                    _ = ctypes.cdll.LoadLibrary(test_file)
                except FileNotFoundError as _:
                    logger.warning("检测到 PyTorch 版本存在 libomp 问题, 进行修复")
                    shutil.copyfile(os.path.join(lib_folder, "libiomp5md.dll"), dest)
        except Exception as _:
            pass


class ComponentEnvironmentDetails(TypedDict):
    """ComfyUI 组件的环境信息结构"""

    requirement_path: str  # 依赖文件路径
    is_disabled: bool  # 组件是否禁用
    requires: list[str]  # 需要的依赖列表
    has_missing_requires: bool  # 是否存在缺失依赖
    missing_requires: list[str]  # 具体缺失的依赖项
    has_conflict_requires: bool  # 是否存在冲突依赖
    conflict_requires: list[str]  # 具体冲突的依赖项


ComfyUIEnvironmentComponent = dict[
    str, ComponentEnvironmentDetails
]  # ComfyUI 环境组件表字典


class ComfyUIRequirementCheck(RequirementCheck):
    """ComfyUI 依赖检查工具"""

    @staticmethod
    def create_comfyui_environment_dict(
        comfyui_path: str | Path,
    ) -> ComfyUIEnvironmentComponent:
        """创建 ComfyUI 环境组件表字典

        参数:
            comfyui_path (`str`, `Path`):
                ComfyUI 根路径

        返回值:
            `ComfyUIEnvironmentComponent`: ComfyUI 环境组件表字典
        """
        comfyui_env_data: ComfyUIEnvironmentComponent = {
            "ComfyUI": {
                "requirement_path": os.path.join(comfyui_path, "requirements.txt"),
                "is_disabled": False,
                "requires": [],
                "has_missing_requires": False,
                "missing_requires": [],
                "has_conflict_requires": False,
                "conflict_requires": [],
            },
        }
        custom_nodes_path = os.path.join(comfyui_path, "custom_nodes")
        for custom_node in os.listdir(custom_nodes_path):
            if os.path.isfile(os.path.join(custom_nodes_path, custom_node)):
                continue

            custom_node_requirement_path = os.path.join(
                custom_nodes_path, custom_node, "requirements.txt"
            )
            custom_node_is_disabled = (
                True if custom_node.endswith(".disabled") else False
            )

            comfyui_env_data[custom_node] = {
                "requirement_path": (
                    custom_node_requirement_path
                    if os.path.exists(custom_node_requirement_path)
                    else None
                ),
                "is_disabled": custom_node_is_disabled,
                "requires": [],
                "has_missing_requires": False,
                "missing_requires": [],
                "has_conflict_requires": False,
                "conflict_requires": [],
            }

        return comfyui_env_data

    @staticmethod
    def update_comfyui_environment_dict(
        env_data: ComfyUIEnvironmentComponent,
        component_name: str,
        requirement_path: str | None = None,
        is_disabled: bool | None = None,
        requires: list[str] | None = None,
        has_missing_requires: bool | None = None,
        missing_requires: list[str] | None = None,
        has_conflict_requires: bool | None = None,
        conflict_requires: list[str] | None = None,
    ) -> None:
        """更新 ComfyUI 环境组件表字典

        参数:
            env_data (`ComfyUIEnvironmentComponent`):
                ComfyUI 环境组件表字典

            component_name (`str`):
                ComfyUI 组件名称

            requirement_path (`str`, `None`):
                ComfyUI 组件依赖文件路径

            is_disabled (`bool`, `None`):
                ComfyUI 组件是否被禁用

            requires (`list[str]`, `None`):
                ComfyUI 组件需要的依赖列表

            has_missing_requires (`bool`, `None`):
                ComfyUI 组件是否存在缺失依赖

            missing_requires (`list[str]`, `None`):
                ComfyUI 组件缺失依赖列表

            has_conflict_requires (`bool`, `None`):
                ComfyUI 组件是否存在冲突依赖

            conflict_requires (`list[str]`, `None`):
                ComfyUI 组件冲突依赖列表
        """
        env_data[component_name] = {
            "requirement_path": (
                requirement_path
                if requirement_path
                else env_data.get(component_name).get("requirement_path")
            ),
            "is_disabled": (
                is_disabled
                if is_disabled
                else env_data.get(component_name).get("is_disabled")
            ),
            "requires": (
                requires if requires else env_data.get(component_name).get("requires")
            ),
            "has_missing_requires": (
                has_missing_requires
                if has_missing_requires
                else env_data.get(component_name).get("has_missing_requires")
            ),
            "missing_requires": (
                missing_requires
                if missing_requires
                else env_data.get(component_name).get("missing_requires")
            ),
            "has_conflict_requires": (
                has_conflict_requires
                if has_conflict_requires
                else env_data.get(component_name).get("has_conflict_requires")
            ),
            "conflict_requires": (
                conflict_requires
                if conflict_requires
                else env_data.get(component_name).get("conflict_requires")
            ),
        }

    @staticmethod
    def update_comfyui_component_requires_list(
        env_data: ComfyUIEnvironmentComponent,
    ) -> None:
        """更新 ComfyUI 环境组件表字典, 根据字典中的 requirement_path 确定 Python 软件包版本声明文件, 并解析后写入 requires 字段

        参数:
            env_data (`ComfyUIEnvironmentComponent`):
                ComfyUI 环境组件表字典
        """
        for component_name, details in env_data.items():
            if details.get("is_disabled"):
                continue

            requirement_path = details.get("requirement_path")
            if requirement_path is None:
                continue

            origin_requires = (
                ComfyUIRequirementCheck.read_packages_from_requirements_file(
                    requirement_path
                )
            )
            requires = ComfyUIRequirementCheck.parse_requirement_list(origin_requires)
            ComfyUIRequirementCheck.update_comfyui_environment_dict(
                env_data=env_data,
                component_name=component_name,
                requires=requires,
            )

    @staticmethod
    def update_comfyui_component_missing_requires_list(
        env_data: ComfyUIEnvironmentComponent,
    ) -> None:
        """更新 ComfyUI 环境组件表字典, 根据字典中的 requires 检查缺失的 Python 软件包, 并保存到 missing_requires 字段和设置 has_missing_requires 状态

        参数:
            env_data (`ComfyUIEnvironmentComponent`):
                ComfyUI 环境组件表字典
        """
        for component_name, details in env_data.items():
            if details.get("is_disabled"):
                continue

            requires = details.get("requires")
            has_missing_requires = False
            missing_requires = []

            for package in requires:
                if not ComfyUIRequirementCheck.is_package_installed(package):
                    has_missing_requires = True
                    missing_requires.append(package)

            ComfyUIRequirementCheck.update_comfyui_environment_dict(
                env_data=env_data,
                component_name=component_name,
                has_missing_requires=has_missing_requires,
                missing_requires=missing_requires,
            )

    @staticmethod
    def update_comfyui_component_conflict_requires_list(
        env_data: ComfyUIEnvironmentComponent, conflict_package_list: list
    ) -> None:
        """更新 ComfyUI 环境组件表字典, 根据 conflicconflict_package_listt_package 检查 ComfyUI 组件冲突的 Python 软件包, 并保存到 conflict_requires 字段和设置 has_conflict_requires 状态

        参数:
            env_data (`ComfyUIEnvironmentComponent`):
                ComfyUI 环境组件表字典

            conflict_package_list (`list`):
                冲突的 Python 软件包列表
        """
        for component_name, details in env_data.items():
            if details.get("is_disabled"):
                continue

            requires = details.get("requires")
            has_conflict_requires = False
            conflict_requires = []

            for conflict_package in conflict_package_list:
                for package in requires:
                    if ComfyUIRequirementCheck.is_package_has_version(
                        package
                    ) and ComfyUIRequirementCheck.get_package_name(
                        conflict_package
                    ) == ComfyUIRequirementCheck.get_package_name(package):
                        has_conflict_requires = True
                        conflict_requires.append(package)

            ComfyUIRequirementCheck.update_comfyui_environment_dict(
                env_data=env_data,
                component_name=component_name,
                has_conflict_requires=has_conflict_requires,
                conflict_requires=conflict_requires,
            )

    @staticmethod
    def get_comfyui_component_requires_list(
        env_data: ComfyUIEnvironmentComponent,
    ) -> list:
        """从 ComfyUI 环境组件表字典读取所有组件的 requires

        参数:
            env_data (`ComfyUIEnvironmentComponent`):
                ComfyUI 环境组件表字典

        返回值:
            `list`: ComfyUI 环境组件的 Python 软件包列表
        """
        package_list = []
        for _, details in env_data.items():
            if details.get("is_disabled"):
                continue

            package_list += details.get("requires")

        return ComfyUIRequirementCheck.remove_duplicate_object_from_list(package_list)

    @staticmethod
    def statistical_need_install_require_component(
        env_data: ComfyUIEnvironmentComponent,
    ) -> list:
        """根据 ComfyUI 环境组件表字典中的 has_missing_requires 和 has_conflict_requires 字段确认需要安装依赖的列表

        参数:
            env_data (`ComfyUIEnvironmentComponent`):
                ComfyUI 环境组件表字典

        返回值:
            `list`: ComfyUI 环境组件的依赖文件路径列表
        """
        requirement_list = []
        for _, details in env_data.items():
            if details.get("has_missing_requires") or details.get(
                "has_conflict_requires"
            ):
                requirement_list.append(
                    Path(details.get("requirement_path")).as_posix()
                )

        return requirement_list

    @staticmethod
    def statistical_has_conflict_component(
        env_data: ComfyUIEnvironmentComponent, conflict_package_list: list
    ) -> list:
        """根据 ComfyUI 环境组件表字典中的 has_conflict_requires 字段确认需要安装依赖的列表

        参数:
            env_data (`ComfyUIEnvironmentComponent`):
                ComfyUI 环境组件表字典

        返回值:
            `list`: ComfyUI 环境组件的依赖文件路径列表
        """
        content = []
        for conflict_package in conflict_package_list:
            content.append(
                ComfyUIRequirementCheck.get_package_name(f"{conflict_package}:")
            )
            for component_name, details in env_data.items():
                for conflict_component_package in details.get("conflict_requires"):
                    if (
                        ComfyUIRequirementCheck.get_package_name(
                            conflict_component_package
                        )
                        == conflict_package
                    ):
                        content.append(
                            f" - {component_name}: {conflict_component_package}"
                        )

        return content[:-1] if len(content) > 0 and content[-1] == "" else content

    @staticmethod
    def fitter_has_version_package(package_list: list) -> list:
        """过滤不包含版本的 Python 软件包, 仅保留包含版本号声明的 Python 软件包

        参数:
            package_list (`list`):
                Python 软件包列表

        返回值:
            `list`: 仅包含版本号的 Python 软件包列表
        """
        return [
            p for p in package_list if ComfyUIRequirementCheck.is_package_has_version(p)
        ]

    @staticmethod
    def detect_conflict_package(pkg1: str, pkg2: str) -> bool:
        """检测 Python 软件包版本号声明是否存在冲突

        参数:
            pkg1 (`str`):
                第 1 个 Python 软件包名称

            pkg2 (`str`):
                第 2 个 Python 软件包名称

        返回值:
            `bool`: 如果 Python 软件包版本声明出现冲突则返回`True`
        """
        # 进行 2 次循环, 第 2 次循环时交换版本后再进行判断
        for i in range(2):
            if i == 1:
                if pkg1 == pkg2:
                    break
                else:
                    pkg1, pkg2 = pkg2, pkg1

            ver1 = ComfyUIRequirementCheck.get_package_version(pkg1)
            ver2 = ComfyUIRequirementCheck.get_package_version(pkg2)
            logger.debug(
                "冲突依赖检测: pkg1: %s, pkg2: %s, ver1: %s, ver2: %s",
                pkg1,
                pkg2,
                ver1,
                ver2,
            )

            # >=, <=
            if ">=" in pkg1 and "<=" in pkg2:
                if ComfyUIRequirementCheck.is_v1_gt_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s > %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

            # >=, <
            if ">=" in pkg1 and "<" in pkg2 and "=" not in pkg2:
                if ComfyUIRequirementCheck.is_v1_ge_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s >= %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

            # >, <=
            if ">" in pkg1 and "=" not in pkg1 and "<=" in pkg2:
                if ComfyUIRequirementCheck.is_v1_ge_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s >= %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

            # >, <
            if ">" in pkg1 and "=" not in pkg1 and "<" in pkg2 and "=" not in pkg2:
                if ComfyUIRequirementCheck.is_v1_ge_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s >= %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

            # >, ==
            if ">" in pkg1 and "=" not in pkg1 and "==" in pkg2:
                if ComfyUIRequirementCheck.is_v1_ge_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s >= %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

            # >=, ==
            if ">=" in pkg1 and "==" in pkg2:
                if ComfyUIRequirementCheck.is_v1_gt_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s > %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

            # <, ==
            if "<" in pkg1 and "=" not in pkg1 and "==" in pkg2:
                if ComfyUIRequirementCheck.is_v1_le_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s <= %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

            # <=, ==
            if "<=" in pkg1 and "==" in pkg2:
                if ComfyUIRequirementCheck.is_v1_lt_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s < %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

            # !=, ==
            if "!=" in pkg1 and "==" in pkg2:
                if ComfyUIRequirementCheck.is_v1_eq_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s == %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

            # >, ~=
            if ">" in pkg1 and "=" not in pkg1 and "~=" in pkg2:
                if ComfyUIRequirementCheck.is_v1_ge_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s >= %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

            # >=, ~=
            if ">=" in pkg1 and "~=" in pkg2:
                if ComfyUIRequirementCheck.is_v1_gt_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s > %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

            # <, ~=
            if "<" in pkg1 and "=" not in pkg1 and "~=" in pkg2:
                if ComfyUIRequirementCheck.is_v1_le_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s <= %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

            # <=, ~=
            if "<=" in pkg1 and "~=" in pkg2:
                if ComfyUIRequirementCheck.is_v1_lt_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s < %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

            # !=, ~=
            # 这个也没什么必要
            # if '!=' in pkg1 and '~=' in pkg2:
            #     if is_v1_c_eq_v2(ver1, ver2):
            #         logger.debug(
            #             '冲突依赖: %s, %s, 版本冲突: %s ~= %s',
            #             pkg1, pkg2, ver1, ver2)
            #         return True

            # ~=, == / ~=, ===
            if ("~=" in pkg1 and "==" in pkg2) or ("~=" in pkg1 and "===" in pkg2):
                if ComfyUIRequirementCheck.is_v1_gt_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s > %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

            # ~=, ~=
            # ~= 类似 >= V.N, == V.*, 所以该部分的比较没必要使用
            # if '~=' in pkg1 and '~=' in pkg2:
            #     if not is_v1_c_eq_v2(ver1, ver2):
            #         logger.debug(
            #             '冲突依赖: %s, %s, 版本冲突: %s !~= %s',
            #             pkg1, pkg2, ver1, ver2)
            #         return True

            # ==, == / ===, ===
            if ("==" in pkg1 and "==" in pkg2) or ("===" in pkg1 and "===" in pkg2):
                if not ComfyUIRequirementCheck.is_v1_eq_v2(ver1, ver2):
                    logger.debug(
                        "冲突依赖: %s, %s, 版本冲突: %s != %s", pkg1, pkg2, ver1, ver2
                    )
                    return True

        return False

    @staticmethod
    def detect_conflict_package_from_list(package_list: list) -> list:
        """检测 Python 软件包版本声明列表中存在冲突的软件包

        参数:
            package_list (`list`):
                Python 软件包版本声明列表

        返回值:
            `list`: 冲突的 Python 软件包列表
        """
        conflict_package = []
        for i in package_list:
            for j in package_list:
                if ComfyUIRequirementCheck.get_package_name(
                    i
                ) == ComfyUIRequirementCheck.get_package_name(
                    j
                ) and ComfyUIRequirementCheck.detect_conflict_package(i, j):
                    conflict_package.append(ComfyUIRequirementCheck.get_package_name(i))

        return ComfyUIRequirementCheck.remove_duplicate_object_from_list(
            conflict_package
        )

    @staticmethod
    def display_comfyui_environment_dict(
        env_data: ComfyUIEnvironmentComponent,
    ) -> None:
        """列出 ComfyUI 环境组件字典内容

        参数:
            env_data (`ComfyUIEnvironmentComponent`):
                ComfyUI 环境组件表字典
        """
        logger.debug("ComfyUI 环境组件表")
        for component_name, details in env_data.items():
            logger.debug("Component: %s", component_name)
            logger.debug(" - requirement_path: %s", details["requirement_path"])
            logger.debug(" - is_disabled: %s", details["is_disabled"])
            logger.debug(" - requires: %s", details["requires"])
            logger.debug(" - has_missing_requires: %s", details["has_missing_requires"])
            logger.debug(" - missing_requires: %s", details["missing_requires"])
            logger.debug(
                " - has_conflict_requires: %s", details["has_conflict_requires"]
            )
            logger.debug(" - conflict_requires: %s", details["conflict_requires"])
            print()

    @staticmethod
    def display_check_result(requirement_list: list, conflict_result: list) -> None:
        """显示 ComfyUI 运行环境检查结果

        参数:
            requirement_list (`list`):
                ComfyUI 组件依赖文件路径列表

            conflict_result (`list`):
                冲突组件统计信息
        """
        if len(requirement_list) > 0:
            logger.debug("需要安装 ComfyUI 组件列表")
            for requirement in requirement_list:
                component_name = requirement.split("/")[-2]
                logger.debug("%s:", component_name)
                logger.debug(" - %s", requirement)
            print()

        if len(conflict_result) > 0:
            logger.debug("ComfyUI 冲突组件")
            for text in conflict_result:
                logger.debug(text)
            print()

    @staticmethod
    def check_comfyui_env(
        comfyui_root_path: Path | str,
        install_conflict_component_requirement: bool | None = False,
        use_uv: bool | None = True,
        debug_mode: bool | None = False,
    ) -> None:
        """检查并安装 ComfyUI 的依赖环境

        :param comfyui_root_path`(Path|str)`: ComfyUI 根目录
        :param install_conflict_component_requirement`(bool|None)`: 检测到冲突依赖时是否按顺序安装组件依赖
        :param use_uv`(bool|None)`: 是否使用 uv 安装依赖
        :param debug_mode`(bool|None)`: 显示调试信息
        """
        if not os.path.exists(os.path.join(comfyui_root_path, "requirements.txt")):
            logger.error("ComfyUI 依赖文件缺失, 请检查 ComfyUI 是否安装完整")
            return

        if not os.path.exists(os.path.join(comfyui_root_path, "custom_nodes")):
            logger.error("ComfyUI 自定义节点文件夹未找到, 请检查 ComfyUI 是否安装完整")
            return

        logger.info("检测 ComfyUI 环境中")
        env_data = ComfyUIRequirementCheck.create_comfyui_environment_dict(
            comfyui_root_path
        )
        ComfyUIRequirementCheck.update_comfyui_component_requires_list(env_data)
        ComfyUIRequirementCheck.update_comfyui_component_missing_requires_list(env_data)
        pkg_list = ComfyUIRequirementCheck.get_comfyui_component_requires_list(env_data)
        has_version_pkg = ComfyUIRequirementCheck.fitter_has_version_package(pkg_list)
        conflict_pkg = ComfyUIRequirementCheck.detect_conflict_package_from_list(
            has_version_pkg
        )
        ComfyUIRequirementCheck.update_comfyui_component_conflict_requires_list(
            env_data, conflict_pkg
        )
        req_list = ComfyUIRequirementCheck.statistical_need_install_require_component(
            env_data
        )
        conflict_info = ComfyUIRequirementCheck.statistical_has_conflict_component(
            env_data, conflict_pkg
        )

        if debug_mode:
            ComfyUIRequirementCheck.display_comfyui_environment_dict(env_data)
            ComfyUIRequirementCheck.display_check_result(req_list, conflict_info)

        if len("".join(conflict_info)) > 0:
            logger.warning(
                "检测到当前 ComfyUI 环境中安装的插件之间存在依赖冲突情况, 该问题并非致命, 但建议只保留一个插件, 否则部分功能可能无法正常使用"
            )
            logger.warning(
                "您可以选择按顺序安装依赖, 由于这将向环境中安装不符合版本要求的组件, 您将无法完全解决此问题, 但可避免组件由于依赖缺失而无法启动的情况"
            )
            logger.warning("检测到冲突的依赖:")
            print("".join(conflict_info))
            if not install_conflict_component_requirement:
                logger.info("忽略警告并继续启动 ComfyUI")
                return

        for req in req_list:
            name = req.split("/")[-2]
            logger.info(f"安装 {name} 的依赖中")
            try:
                EnvManager.install_requirements(req, use_uv)
            except Exception as e:
                logger.error(f"安装 {name} 的依赖失败: {e}")

        logger.info("ComfyUI 环境检查完成")


class OrtType(str, Enum):
    """onnxruntime-gpu 的类型

    版本说明:
    - CU121CUDNN8: CUDA 12.1 + cuDNN8
    - CU121CUDNN9: CUDA 12.1 + cuDNN9
    - CU118: CUDA 11.8
    """

    CU121CUDNN8 = "cu121cudnn8"
    CU121CUDNN9 = "cu121cudnn9"
    CU118 = "cu118"

    def __str__(self):
        return self.value


class OnnxRuntimeGPUCheck:
    """检查 onnxruntime-gpu"""

    @staticmethod
    def get_onnxruntime_version_file() -> Path | None:
        """获取记录 onnxruntime 版本的文件路径

        :return Path | None: 记录 onnxruntime 版本的文件路径
        """
        package = "onnxruntime-gpu"
        version_file = "onnxruntime/capi/version_info.py"
        try:
            util = [
                p for p in importlib.metadata.files(package) if version_file in str(p)
            ][0]
            info_path = Path(util.locate())
        except Exception as _:
            info_path = None

        return info_path

    @staticmethod
    def get_onnxruntime_support_cuda_version() -> tuple[str | None, str | None]:
        """获取 onnxruntime 支持的 CUDA, cuDNN 版本

        :return tuple[str | None, str | None]: onnxruntime 支持的 CUDA, cuDNN 版本
        """
        ver_path = OnnxRuntimeGPUCheck.get_onnxruntime_version_file()
        cuda_ver = None
        cudnn_ver = None
        try:
            with open(ver_path, "r", encoding="utf8") as f:
                for line in f:
                    if "cuda_version" in line:
                        cuda_ver = OnnxRuntimeGPUCheck.get_value_from_variable(
                            line, "cuda_version"
                        )
                    if "cudnn_version" in line:
                        cudnn_ver = OnnxRuntimeGPUCheck.get_value_from_variable(
                            line, "cudnn_version"
                        )
        except Exception as _:
            pass

        return cuda_ver, cudnn_ver

    @staticmethod
    def get_value_from_variable(content: str, var_name: str) -> str | None:
        """从字符串 (Python 代码片段) 中找出指定字符串变量的值

        :param content(str): 待查找的内容
        :param var_name(str): 待查找的字符串变量
        :return str | None: 返回字符串变量的值
        """
        pattern = rf'{var_name}\s*=\s*"([^"]+)"'
        match = re.search(pattern, content)
        return match.group(1) if match else None

    @staticmethod
    def get_torch_cuda_ver() -> tuple[str | None, str | None, str | None]:
        """获取 Torch 的本体, CUDA, cuDNN 版本

        :return tuple[str | None, str | None, str | None]: Torch, CUDA, cuDNN 版本
        """
        try:
            import torch

            torch_ver = torch.__version__
            cuda_ver = torch.version.cuda
            cudnn_ver = torch.backends.cudnn.version()
            return (
                str(torch_ver) if torch_ver is not None else None,
                str(cuda_ver) if cuda_ver is not None else None,
                str(cudnn_ver) if cudnn_ver is not None else None,
            )
        except Exception as _:
            return None, None, None

    @staticmethod
    def need_install_ort_ver(ignore_ort_install: bool = True) -> OrtType | None:
        """判断需要安装的 onnxruntime 版本

        :param ignore_ort_install(bool): 当 onnxruntime 未安装时跳过检查
        :return OrtType: 需要安装的 onnxruntime-gpu 类型
        """
        # 检测是否安装了 Torch
        torch_ver, cuda_ver, cuddn_ver = OnnxRuntimeGPUCheck.get_torch_cuda_ver()
        # 缺少 Torch / CUDA / cuDNN 版本时取消判断
        if torch_ver is None or cuda_ver is None or cuddn_ver is None:
            if not ignore_ort_install:
                try:
                    _ = importlib.metadata.version("onnxruntime-gpu")
                except Exception as _:
                    # onnxruntime-gpu 没有安装时
                    return OrtType.CU121CUDNN9
            return None

        # onnxruntime 记录的 cuDNN 支持版本只有一位数, 所以 Torch 的 cuDNN 版本只能截取一位
        cuddn_ver = cuddn_ver[0]

        # 检测是否安装了 onnxruntime-gpu
        ort_support_cuda_ver, ort_support_cudnn_ver = (
            OnnxRuntimeGPUCheck.get_onnxruntime_support_cuda_version()
        )
        # 通常 onnxruntime 的 CUDA 版本和 cuDNN 版本会同时存在, 所以只需要判断 CUDA 版本是否存在即可
        if ort_support_cuda_ver is not None:
            # 当 onnxruntime 已安装

            # 判断 Torch 中的 CUDA 版本
            if Utils.compare_versions(cuda_ver, "12.0") >= 0:
                # CUDA >= 12.0

                # 比较 onnxtuntime 支持的 CUDA 版本是否和 Torch 中所带的 CUDA 版本匹配
                if Utils.compare_versions(ort_support_cuda_ver, "12.0") >= 0:
                    # CUDA 版本为 12.x, torch 和 ort 的 CUDA 版本匹配

                    # 判断 Torch 和 onnxruntime 的 cuDNN 是否匹配
                    if Utils.compare_versions(ort_support_cudnn_ver, cuddn_ver) > 0:
                        # ort cuDNN 版本 > torch cuDNN 版本
                        return OrtType.CU121CUDNN8
                    elif Utils.compare_versions(ort_support_cudnn_ver, cuddn_ver) < 0:
                        # ort cuDNN 版本 < torch cuDNN 版本
                        return OrtType.CU121CUDNN9
                    else:
                        # 版本相等, 无需重装
                        return None
                else:
                    # CUDA 版本非 12.x, 不匹配
                    if Utils.compare_versions(cuddn_ver, "8") > 0:
                        return OrtType.CU121CUDNN9
                    else:
                        return OrtType.CU121CUDNN8
            else:
                # CUDA <= 11.8
                if Utils.compare_versions(ort_support_cuda_ver, "12.0") < 0:
                    return None
                else:
                    return OrtType.CU118
        else:
            if ignore_ort_install:
                return None

            if Utils.compare_versions(cuda_ver, "12.0") >= 0:
                if Utils.compare_versions(cuddn_ver, "8") > 0:
                    return OrtType.CU121CUDNN9
                else:
                    return OrtType.CU121CUDNN8
            else:
                return OrtType.CU118

    @staticmethod
    def check_onnxruntime_gpu(
        use_uv: bool | None = True, ignore_ort_install: bool | None = False
    ):
        """检查并修复 Onnxruntime GPU 版本问题

        :param use_uv`(bool|None)`: 是否使用 uv 安装依赖
        :param ignore_ort_install`(bool|None)`: 当 onnxruntime 未安装时跳过检查
        """
        logger.info("检查 Onnxruntime GPU 版本问题中")
        ver = OnnxRuntimeGPUCheck.need_install_ort_ver(ignore_ort_install)
        if ver is None:
            logger.info("Onnxruntime GPU 无版本问题")
            return
        custom_env = os.environ.copy()
        custom_env.pop("PIP_EXTRA_INDEX_URL", None)
        custom_env.pop("UV_INDEX", None)
        custom_env.pop("PIP_FIND_LINKS", None)
        custom_env.pop("UV_FIND_LINKS", None)

        try:
            if ver == OrtType.CU118:
                custom_env["PIP_INDEX_URL"] = (
                    "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-11/pypi/simple/"
                )
                custom_env["UV_DEFAULT_INDEX"] = (
                    "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-11/pypi/simple/"
                )
                run_cmd(
                    [
                        Path(sys.executable).as_posix(),
                        "-m",
                        "pip",
                        "uninstall",
                        "onnxruntime-gpu",
                        "-y",
                    ]
                )
                EnvManager.pip_install(
                    "onnxruntime-gpu>=1.18.1",
                    "--no-cache-dir",
                    use_uv=use_uv,
                    custom_env=custom_env,
                )
            elif ver == OrtType.CU121CUDNN9:
                run_cmd(
                    [
                        Path(sys.executable).as_posix(),
                        "-m",
                        "pip",
                        "uninstall",
                        "onnxruntime-gpu",
                        "-y",
                    ]
                )
                EnvManager.pip_install(
                    "onnxruntime-gpu>=1.19.0", "--no-cache-dir", use_uv=use_uv
                )
            elif ver == OrtType.CU121CUDNN8:
                custom_env["PIP_INDEX_URL"] = (
                    "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/"
                )
                custom_env["UV_DEFAULT_INDEX"] = (
                    "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/"
                )
                run_cmd(
                    [
                        Path(sys.executable).as_posix(),
                        "-m",
                        "pip",
                        "uninstall",
                        "onnxruntime-gpu",
                        "-y",
                    ]
                )
                EnvManager.pip_install(
                    "onnxruntime-gpu==1.17.1",
                    "--no-cache-dir",
                    use_uv=use_uv,
                    custom_env=custom_env,
                )
        except Exception as e:
            logger.error(f"修复 Onnxruntime GPU 版本问题时出现错误: {e}")
            return

        logger.info("Onnxruntime GPU 版本问题修复完成")


class CUDAMalloc:
    """配置 CUDA Malloc 内存优化"""

    @staticmethod
    def get_gpu_names():
        if os.name == "nt":
            import ctypes

            # Define necessary C structures and types
            class DISPLAY_DEVICEA(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.c_ulong),
                    ("DeviceName", ctypes.c_char * 32),
                    ("DeviceString", ctypes.c_char * 128),
                    ("StateFlags", ctypes.c_ulong),
                    ("DeviceID", ctypes.c_char * 128),
                    ("DeviceKey", ctypes.c_char * 128),
                ]

            # Load user32.dll
            user32 = ctypes.windll.user32

            # Call EnumDisplayDevicesA
            def enum_display_devices():
                device_info = DISPLAY_DEVICEA()
                device_info.cb = ctypes.sizeof(device_info)
                device_index = 0
                gpu_names = set()

                while user32.EnumDisplayDevicesA(
                    None, device_index, ctypes.byref(device_info), 0
                ):
                    device_index += 1
                    gpu_names.add(device_info.DeviceString.decode("utf-8"))
                return gpu_names

            return enum_display_devices()
        else:
            gpu_names = set()
            out = subprocess.check_output(["nvidia-smi", "-L"])
            for line in out.split(b"\n"):
                if len(line) > 0:
                    gpu_names.add(line.decode("utf-8").split(" (UUID")[0])
            return gpu_names

    blacklist = {
        "GeForce GTX TITAN X",
        "GeForce GTX 980",
        "GeForce GTX 970",
        "GeForce GTX 960",
        "GeForce GTX 950",
        "GeForce 945M",
        "GeForce 940M",
        "GeForce 930M",
        "GeForce 920M",
        "GeForce 910M",
        "GeForce GTX 750",
        "GeForce GTX 745",
        "Quadro K620",
        "Quadro K1200",
        "Quadro K2200",
        "Quadro M500",
        "Quadro M520",
        "Quadro M600",
        "Quadro M620",
        "Quadro M1000",
        "Quadro M1200",
        "Quadro M2000",
        "Quadro M2200",
        "Quadro M3000",
        "Quadro M4000",
        "Quadro M5000",
        "Quadro M5500",
        "Quadro M6000",
        "GeForce MX110",
        "GeForce MX130",
        "GeForce 830M",
        "GeForce 840M",
        "GeForce GTX 850M",
        "GeForce GTX 860M",
        "GeForce GTX 1650",
        "GeForce GTX 1630",
        "Tesla M4",
        "Tesla M6",
        "Tesla M10",
        "Tesla M40",
        "Tesla M60",
    }

    gpu_keywords = ["NVIDIA", "GeForce", "Tesla", "Quadro"]

    @staticmethod
    def cuda_malloc_supported():
        try:
            names = CUDAMalloc.get_gpu_names()
        except Exception as _:
            names = set()
        for x in names:
            if any(keyword in x for keyword in CUDAMalloc.gpu_keywords):
                for b in CUDAMalloc.blacklist:
                    if b in x:
                        return False
        return True

    @staticmethod
    def is_nvidia_device():
        try:
            names = CUDAMalloc.get_gpu_names()
        except Exception as _:
            names = set()
        for x in names:
            if any(keyword in x for keyword in CUDAMalloc.gpu_keywords):
                return True
        return False

    @staticmethod
    def get_pytorch_cuda_alloc_conf(is_cuda=True):
        if CUDAMalloc.is_nvidia_device():
            if CUDAMalloc.cuda_malloc_supported():
                if is_cuda:
                    return "cuda_malloc"
                else:
                    return "pytorch_malloc"
            else:
                return "pytorch_malloc"
        else:
            return None

    @staticmethod
    def set_cuda_malloc():
        try:
            version = ""
            torch_spec = importlib.util.find_spec("torch")
            for folder in torch_spec.submodule_search_locations:
                ver_file = os.path.join(folder, "version.py")
                if os.path.isfile(ver_file):
                    spec = importlib.util.spec_from_file_location(
                        "torch_version_import", ver_file
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    version = module.__version__
            if int(version[0]) >= 2:  # enable by default for torch version 2.0 and up
                if "+cu" in version:  # only on cuda torch
                    malloc_type = CUDAMalloc.get_pytorch_cuda_alloc_conf()
                else:
                    malloc_type = CUDAMalloc.get_pytorch_cuda_alloc_conf(False)
            else:
                malloc_type = None
        except Exception as _:
            malloc_type = None

        if malloc_type == "cuda_malloc":
            logger.info("设置 CUDA 内存分配器为 CUDA 内置异步分配器")
            os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "backend:cudaMallocAsync"
        elif malloc_type == "pytorch_malloc":
            logger.info("设置 CUDA 内存分配器为 PyTorch 原生分配器")
            os.environ["PYTORCH_CUDA_ALLOC_CONF"] = (
                "garbage_collection_threshold:0.9,max_split_size_mb:512"
            )
        else:
            logger.warning("显卡非 Nvidia 显卡, 无法设置 CUDA 内存分配器")


class BaseManager:
    """管理工具基础类"""

    def __init__(
        self,
        workspace: str | Path,
        workfolder: str,
        hf_token: str | None = None,
        ms_token: str | None = None,
        port: int | None = 7860,
    ) -> None:
        """管理工具初始化

        :param workspace`(str|Path)`: 工作区路径
        :param workfolder`(str)`: 工作区的文件夹名称
        :param hf_token`(str|None)`: HuggingFace Token
        :param ms_token`(str|None)`: ModelScope Token
        :param port`(int|None)`: 内网穿透端口
        """
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.workfolder = workfolder
        self.git = GitWarpper()
        self.downloader = Downloader()
        self.env = EnvManager()
        self.utils = Utils()
        self.repo = RepoManager(hf_token, ms_token)
        self.mirror = MirrorConfigManager()
        self.tun = TunnelManager(workspace, port)
        self.env_check = RequirementCheck()
        self.ort_check = OnnxRuntimeGPUCheck()
        self.cuda_malloc = CUDAMalloc()
        self.remove_files = remove_files
        self.run_cmd = run_cmd
        self.copy_files = copy_files
        self.get_logger = get_logger
        self.multi_thread_downloader_class = MultiThreadDownloader

    def restart_repo_manager(
        self,
        hf_token: str | None = None,
        ms_token: str | None = None,
    ) -> None:
        """重新初始化 HuggingFace / ModelScope 仓库管理工具

        :param hf_token`(str|None)`: HugggingFace Token, 不为`None`时配置`HF_TOKEN`环境变量
        :param ms_token`(str|None)`: ModelScope Token, 不为`None`时配置`MODELSCOPE_API_TOKEN`环境变量
        """
        logger.info("重启 HuggingFace / ModelScope 仓库管理模块")
        self.repo = RepoManager(
            hf_token=hf_token,
            ms_token=ms_token,
        )

    def get_model(
        self,
        url: str,
        path: str | Path,
        filename: str | None = None,
        tool: Literal["aria2", "request"] = "aria2",
        retry: int | None = 3,
    ) -> Path | None:
        """下载模型文件到本地中

        :param url`(str)`: 模型文件的下载链接
        :param path`(str|Path)`: 模型文件下载到本地的路径
        :param filename`(str)`: 指定下载的模型文件名称
        :param retry`(int)`: 重试下载的次数, 默认为 3
        :return `Path`: 文件保存路径
        """
        return self.downloader.download_file(
            url=url, path=path, save_name=filename, tool=tool, retry=retry
        )

    def get_model_from_list(
        self, path: str | Path, model_list: list[str, int], retry: int | None = 3
    ) -> None:
        """从模型列表下载模型

        :param path`(str|Path)`: 将模型下载到的本地路径
        :param model_list`(list[str|int])`: 模型列表
        :param retry`(int|None)`: 重试下载的次数, 默认为 3

        :notes
            `model_list`需要指定模型下载的链接和下载状态, 例如
            ```python
            model_list = [
                ["url1", 0],
                ["url2", 1],
                ["url3", 0],
                ["url4", 1, "file.safetensors"]
            ]
            ```

            在这个例子中, 第一个参数指定了模型的下载链接, 第二个参数设置了是否要下载这个模型, 当这个值为 1 时则下载该模型

            第三个参数是可选参数, 用于指定下载到本地后的文件名称

            则上面的例子中`url2`和`url4`下载链接所指的文件将被下载, 并且`url4`所指的文件将被重命名为`file.safetensors`
        """
        for model in model_list:
            try:
                url = model[0]
                status = model[1]
                filename = model[2] if len(model) > 2 else None
            except Exception as e:
                logger.error("模型下载列表长度不合法: %s\n出现异常的列表:%s", e, model)
                continue
            if status >= 1:
                if filename is None:
                    self.get_model(url=url, path=path, retry=retry)
                else:
                    self.get_model(url=url, path=path, filename=filename, retry=retry)

    def tcmalloc_colab(self) -> None:
        """配置 TCMalloc (Colab)"""
        logger.info("配置 TCMalloc 内存优化")
        url = "https://github.com/licyk/sd-webui-all-in-one/raw/main/libtcmalloc_minimal.so.4"
        libtcmalloc_path = self.workspace / "libtcmalloc_minimal.so.4"
        self.downloader.download_file(
            url=url, path=self.workspace, save_name="libtcmalloc_minimal.so.4"
        )
        os.environ["LD_PRELOAD"] = libtcmalloc_path.as_posix()


class SDScriptsManager(BaseManager):
    """sd-scripts 管理工具"""

    def check_env(
        self,
        use_uv: bool | None = True,
        requirements_file: str | None = "requirements.txt",
    ) -> None:
        """检查 sd-scripts 运行环境

        :param use_uv`(bool|None)`: 使用 uv 安装依赖
        :param requirements_file`(str|None)`: 依赖文件名
        """
        sd_webui_path = self.workspace / self.workfolder
        requirement_path = sd_webui_path / requirements_file
        self.env_check.check_env(
            requirement_path=requirement_path,
            name="sd-scripts",
            use_uv=use_uv,
        )
        self.env_check.fix_torch()
        self.ort_check.check_onnxruntime_gpu(use_uv=use_uv, ignore_ort_install=False)
        self.env_check.check_numpy(use_uv=use_uv)

    def install(
        self,
        torch_ver: str | list | None = None,
        xformers_ver: str | list | None = None,
        git_branch: str | None = None,
        git_commit: str | None = None,
        model_path: str | Path = None,
        model_list: list[str, int] | None = None,
        use_uv: bool | None = True,
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list | None = None,
        huggingface_mirror: str | None = None,
        pytorch_mirror: str | None = None,
        sd_scripts_repo: str | None = None,
        sd_scripts_requirements: str | None = None,
        retry: int | None = 3,
        huggingface_token: str | None = None,
        modelscope_token: str | None = None,
        wandb_token: str | None = None,
        git_username: str | None = None,
        git_email: str | None = None,
        check_avaliable_gpu: bool | None = False,
        enable_tcmalloc: bool | None = True,
        enable_cuda_malloc: bool | None = True,
        *args,
        **kwargs,
    ) -> None:
        """安装 sd-scripts 和其余环境

        :param torch_ver`(str|None)`: 指定的 PyTorch 软件包包名, 并包括版本号
        :param xformers_ver`(str|None)`: 指定的 xFormers 软件包包名, 并包括版本号
        :param git_branch`(str|None)`: 指定要切换 sd-scripts 的分支
        :param git_commit`(str|None)`: 指定要切换到 sd-scripts 的提交记录
        :param model_path`(str|Path|None)`: 指定模型下载的路径
        :param model_list`(list[str|int]|None)`: 模型下载列表
        :param use_uv`(bool|None)`: 使用 uv 替代 Pip 进行 Python 软件包的安装
        :param pypi_index_mirror`(str|None)`: PyPI Index 镜像源链接
        :param pypi_extra_index_mirror`(str|None)`: PyPI Extra Index 镜像源链接
        :param pypi_find_links_mirror`(str|None)`: PyPI Find Links 镜像源链接
        :param github_mirror`(str|list|None)`: Github 镜像源链接或者镜像源链接列表
        :param huggingface_mirror`(str|None)`: HuggingFace 镜像源链接
        :param pytorch_mirror`(str|None)`: PyTorch 镜像源链接
        :param sd_scripts_repo`(str|None)`: sd-scripts 仓库地址, 未指定时默认为`https://github.com/kohya-ss/sd-scripts`
        :param sd_scripts_requirements`(str|None)`: sd-scripts 的依赖文件名, 未指定时默认为`requirements.txt`
        :param retry`(int|None)`: 设置下载模型失败时重试次数
        :param huggingface_token`(str|None)`: 配置 HuggingFace Token
        :param modelscope_tokenn`(str|None)`: 配置 ModelScope Token
        :param wandb_token`(str|None)`: 配置 WandB Token
        :param git_username`(str|None)`: Git 用户名
        :param git_email`(str|None)`: Git 邮箱
        :param check_avaliable_gpu`(bool|None)`: 检查是否有可用的 GPU, 当 GPU 不可用时引发`Exception`
        :param enable_tcmalloc`(bool|None)`: 启用 TCMalloc 内存优化
        :param enable_cuda_malloc`(bool|None)`: 启用 CUDA 显存优化
        :notes
            self.install() 将会以下几件事
            1. 配置 PyPI / Github / HuggingFace 镜像源
            2. 配置 Pip / uv
            3. 安装管理工具自身依赖
            4. 安装 sd-scripts
            5. 安装 PyTorch / xFormers
            6. 安装 sd-scripts 的依赖
            7. 下载模型
            8. 配置 HuggingFace / ModelScope / WandB Token 环境变量
            9. 配置其他工具
        """
        self.utils.warning_unexpected_params(
            message="SDScriptsManager.install() 接收到不期望参数, 请检查参数输入是否正确",
            args=args,
            kwargs=kwargs,
        )
        logger.info("配置 sd-scripts 环境中")
        os.chdir(self.workspace)
        sd_scripts_path = self.workspace / self.workfolder
        requirement_path = sd_scripts_path / (
            sd_scripts_requirements
            if sd_scripts_requirements is not None
            else "requirements.txt"
        )
        sd_scripts_repo = (
            sd_scripts_repo
            if sd_scripts_repo is not None
            else "https://github.com/kohya-ss/sd-scripts"
        )
        model_path = (
            model_path if model_path is not None else (self.workspace / "sd-models")
        )
        model_list = model_list if model_list else []
        # 检查是否有可用的 GPU
        if check_avaliable_gpu and not self.utils.check_gpu():
            raise Exception(
                "没有可用的 GPU, 请在 kaggle -> Notebook -> Session options -> ACCELERATOR 选择 GPU T4 x 2\n如果不能使用 GPU, 请检查 Kaggle 账号是否绑定了手机号或者尝试更换账号!"
            )
        # 配置镜像源
        self.mirror.set_mirror(
            pypi_index_mirror=pypi_index_mirror,
            pypi_extra_index_mirror=pypi_extra_index_mirror,
            pypi_find_links_mirror=pypi_find_links_mirror,
            github_mirror=github_mirror,
            huggingface_mirror=huggingface_mirror,
        )
        self.mirror.configure_pip()  # 配置 Pip / uv
        self.env.install_manager_depend(use_uv=use_uv)  # 准备 Notebook 的运行依赖
        # 下载 sd-scripts
        self.git.clone(
            repo=sd_scripts_repo,
            path=sd_scripts_path,
        )
        self.git.update(sd_scripts_path)  # 更新 sd-scripts
        # 切换指定的 sd-scripts 分支
        if git_branch is not None:
            self.git.switch_branch(path=sd_scripts_path, branch=git_branch)
        # 切换到指定的 sd-scripts 提交记录
        if git_commit is not None:
            self.git.switch_commit(path=sd_scripts_path, commit=git_commit)
        # 安装 PyTorch 和 xFormers
        self.env.install_pytorch(
            torch_package=torch_ver,
            xformers_package=xformers_ver,
            pytorch_mirror=pytorch_mirror,
            use_uv=use_uv,
        )
        # 安装 sd-scripts 的依赖
        os.chdir(sd_scripts_path)
        self.env.install_requirements(path=requirement_path, use_uv=use_uv)
        os.chdir(self.workspace)
        # 安装使用 sd-scripts 进行训练所需的其他软件包
        logger.info("安装其他 Python 模块中")
        try:
            self.env.pip_install(
                "lycoris-lora", "dadaptation", "open-clip-torch", use_uv=use_uv
            )
        except Exception as e:
            logger.error("安装额外 Python 软件包时发生错误: %s", e)
        # 更新 urllib3
        try:
            self.env.pip_install("urllib3", "--upgrade", use_uv=False)
        except Exception as e:
            logger.error("更新 urllib3 时发生错误: %s", e)
        self.env_check.check_numpy(use_uv=use_uv)
        self.get_model_from_list(path=model_path, model_list=model_list, retry=retry)
        self.restart_repo_manager(
            hf_token=huggingface_token,
            ms_token=modelscope_token,
        )
        self.utils.config_wandb_token(wandb_token)
        self.git.set_git_config(
            username=git_username,
            email=git_email,
        )
        if enable_tcmalloc:
            self.utils.config_tcmalloc()
        if enable_cuda_malloc:
            self.cuda_malloc.set_cuda_malloc()
        logger.info("sd-scripts 环境配置完成")


class FooocusManager(BaseManager):
    """Fooocus 管理工具"""

    def mount_drive(
        self,
        extras: list[dict[str, str | bool]] = None,
    ) -> None:
        """挂载 Google Drive 并创建 Fooocus 输出文件夹

        :param extras`(list[dict[str,str|bool]])`: 挂载额外目录

        :notes
            挂载额外目录需要使用`link_dir`指定要挂载的路径, 并且使用相对路径指定

            相对路径的起始位置为`{self.workspace}/{self.workfolder}`

            若额外链接路径为文件, 需指定`is_file`属性为`True`

            例如:
            ```python
            extras = [
                {"link_dir": "models/loras"},
                {"link_dir": "custom_nodes"},
                {"link_dir": "extra_model_paths.yaml", "is_file": True},
            ]
            ```
            默认挂载的目录和文件: `outputs`, `presets`, `language`, `wildcards`, `config.txt`
        """
        drive_path = Path("/content/drive")
        if not (drive_path / "MyDrive").exists():
            if not self.utils.mount_google_drive(drive_path):
                raise Exception("挂载 Google Drive 失败, 请尝试重新挂载 Google Drive")

        drive_output = drive_path / "MyDrive" / "fooocus_output"
        fooocus_path = self.workspace / self.workfolder
        drive_fooocus_output_path = drive_output / "outputs"
        fooocus_output_path = fooocus_path / "outputs"
        drive_fooocus_presets_path = drive_output / "presets"
        fooocus_presets_path = fooocus_path / "presets"
        drive_fooocus_language_path = drive_output / "language"
        fooocus_language_path = fooocus_path / "language"
        drive_fooocus_wildcards_path = drive_output / "wildcards"
        fooocus_wildcards_path = fooocus_path / "wildcards"
        drive_fooocus_config = drive_output / "config.txt"
        fooocus_config = fooocus_path / "config.txt"
        self.utils.sync_files_and_create_symlink(
            src_path=drive_fooocus_output_path,
            link_path=fooocus_output_path,
        )
        self.utils.sync_files_and_create_symlink(
            src_path=drive_fooocus_presets_path,
            link_path=fooocus_presets_path,
        )
        self.utils.sync_files_and_create_symlink(
            src_path=drive_fooocus_language_path,
            link_path=fooocus_language_path,
        )
        self.utils.sync_files_and_create_symlink(
            src_path=drive_fooocus_wildcards_path,
            link_path=fooocus_wildcards_path,
        )
        if fooocus_config.exists() or drive_fooocus_config.exists():
            self.utils.sync_files_and_create_symlink(
                src_path=drive_fooocus_config,
                link_path=fooocus_config,
                src_is_file=True,
            )
        if extras is None:
            return
        for extra in extras:
            link_dir = extra.get("link_dir")
            is_file = extra.get("is_file", False)
            if link_dir is None:
                continue
            full_link_path = fooocus_path / link_dir
            full_drive_path = drive_output / link_dir
            if is_file and (
                not full_link_path.exists() and not full_drive_path.exists()
            ):
                # 链接路径指定的是文件并且源文件和链接文件都不存在时则取消链接
                continue
            self.utils.sync_files_and_create_symlink(
                src_path=full_drive_path,
                link_path=full_link_path,
                src_is_file=is_file,
            )

    def get_sd_model(
        self,
        url: str,
        filename: str = None,
        model_type: str | None = "checkpoints",
    ) -> Path | None:
        """下载模型

        :param url`(str)`: 模型的下载链接
        :param filename`(str|None)`: 模型下载后保存的名称
        :param model_type`(str|None)`: 模型的类型
        :return `Path|None`: 模型保存路径
        """
        path = self.workspace / self.workfolder / "models" / model_type
        return self.get_model(url=url, path=path, filename=filename, tool="aria2")

    def get_sd_model_from_list(
        self,
        model_list: list[dict[str]],
    ) -> None:
        """从模型列表下载模型

        :param model_list`(list[str|int])`: 模型列表

        :notes
            `model_list`需要指定`url`(模型下载链接), 可选参数为`type`(模型类型), `filename`(模型保存名称), 例如
            ```python
            model_list = [
                {"url": "url1", "type": "checkpoints"},
                {"url": "url2", "filename": "file.safetensors"},
                {"url": "url3", "type": "loras", "filename": "lora1.safetensors"},
                {"url": "url4"},
            ]
            ```
        """
        for model in model_list:
            url = model.get("url")
            filename = model.get("filename")
            model_type = model.get("type", "checkpoints")
            self.get_sd_model(url=url, filename=filename, model_type=model_type)

    def install_config(
        self,
        preset: str | None = None,
        translation: str | None = None,
    ) -> None:
        """下载 Fooocus 配置文件

        :param preset`(str|None)`: Fooocus 预设文件下载链接, 下载后将保存在`{self.workspace}/{self.workfolder}/presets/custom.json`
        :param path_config`(str|None)`: Fooocus 路径配置文件下载链接, 下载后将保存在`{self.workspace}/{self.workfolder}/config.txt`
        :param translation`(str|None)`: Fooocus 翻译文件下载链接, 下载后将保存在`{self.workspace}/{self.workfolder}/language/zh.json`
        """
        path = self.workspace / self.workfolder
        preset_path = path / "presets"
        language_path = path / "language"
        logger.info("下载配置文件")
        if preset is not None:
            self.downloader.download_file(
                url=preset, path=preset_path, save_name="custom.json", tool="aria2"
            )
        if translation is not None:
            self.downloader.download_file(
                url=translation, path=language_path, save_name="zh.json", tool="aria2"
            )

    def pre_download_model(
        self,
        path: str | Path,
        thread_num: int | None = 16,
        downloader: Literal["aria2", "request", "mix"] = "mix",
    ) -> None:
        """根据 Fooocus 配置文件预下载模型

        :param path`(str|Path)`: Fooocus 配置文件路径
        :param thread_num`(int|None)`: 下载模型的线程数
        :param downloader`(Literal["aria2","request","mix"])`: 预下载模型时使用的下载器 (`aria2`, `request`, `mix`)
        """
        path = Path(path) if not isinstance(path, Path) and path is not None else path
        if path.exists():
            try:
                with open(path, "r", encoding="utf8") as file:
                    data = json.load(file)
            except Exception as e:
                logger.warning("打开 Fooocus 配置文件时出现错误: %s", e)
                data = {}
        else:
            data = {}

        if downloader == "aria2":
            sd_model_downloader = "aria2"
            vae_downloader = "aria2"
            embedding_downloader = "aria2"
            lora_downloader = "aria2"
        elif downloader == "request":
            sd_model_downloader = "request"
            vae_downloader = "request"
            embedding_downloader = "request"
            lora_downloader = "request"
        elif downloader == "mix":
            sd_model_downloader = "aria2"
            vae_downloader = "aria2"
            embedding_downloader = "request"
            lora_downloader = "request"
        else:
            sd_model_downloader = "aria2"
            vae_downloader = "aria2"
            embedding_downloader = "aria2"
            lora_downloader = "aria2"

        sd_model_list: dict = data.get("checkpoint_downloads", {})
        lora_list: dict = data.get("lora_downloads", {})
        vae_list: dict = data.get("vae_downloads", {})
        embedding_list: dict = data.get("embeddings_downloads", {})
        fooocus_path = self.workspace / self.workfolder
        sd_model_path = fooocus_path / "models" / "checkpoints"
        lora_path = fooocus_path / "models" / "loras"
        vae_path = fooocus_path / "models" / "vae"
        embedding_path = fooocus_path / "models" / "embeddings"

        downloader_params = []
        downloader_params += [
            {
                "url": sd_model_list.get(i),
                "path": sd_model_path,
                "save_name": i,
                "tool": sd_model_downloader,
            }
            for i in sd_model_list
        ]
        downloader_params += [
            {
                "url": lora_list.get(i),
                "path": lora_path,
                "save_name": i,
                "tool": lora_downloader,
            }
            for i in lora_list
        ]
        downloader_params += [
            {
                "url": vae_list.get(i),
                "path": vae_path,
                "save_name": i,
                "tool": vae_downloader,
            }
            for i in vae_list
        ]
        downloader_params += [
            {
                "url": embedding_list.get(i),
                "path": embedding_path,
                "save_name": i,
                "tool": embedding_downloader,
            }
            for i in embedding_list
        ]

        model_downloader = MultiThreadDownloader(
            download_func=self.downloader.download_file,
            download_kwargs_list=downloader_params,
        )
        model_downloader.start(num_threads=thread_num)
        logger.info("预下载 Fooocus 模型完成")

    def check_env(
        self,
        use_uv: bool | None = True,
        requirements_file: str | None = "requirements_versions.txt",
    ) -> None:
        """检查 Fooocus 运行环境

        :param use_uv`(bool|None)`: 使用 uv 安装依赖
        :param requirements_file`(str|None)`: 依赖文件名
        """
        sd_webui_path = self.workspace / self.workfolder
        requirement_path = sd_webui_path / requirements_file
        self.env_check.check_env(
            requirement_path=requirement_path,
            name="Fooocus",
            use_uv=use_uv,
        )
        self.env_check.fix_torch()
        self.ort_check.check_onnxruntime_gpu(use_uv=use_uv, ignore_ort_install=True)
        self.env_check.check_numpy(use_uv=use_uv)

    def install(
        self,
        torch_ver: str | list | None = None,
        xformers_ver: str | list | None = None,
        use_uv: bool | None = True,
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list | None = None,
        huggingface_mirror: str | None = None,
        pytorch_mirror: str | None = None,
        fooocus_repo: str | None = None,
        fooocus_requirements: str | None = None,
        fooocus_preset: str | None = None,
        fooocus_translation: str | None = None,
        model_downloader: Literal["aria2", "request", "mix"] = "mix",
        download_model_thread: int | None = 16,
        check_avaliable_gpu: bool | None = False,
        enable_tcmalloc: bool | None = True,
        enable_cuda_malloc: bool | None = True,
        *args,
        **kwargs,
    ) -> None:
        """安装 Fooocus

        :param torch_ver`(str|None)`: 指定的 PyTorch 软件包包名, 并包括版本号
        :param xformers_ver`(str|None)`: 指定的 xFormers 软件包包名, 并包括版本号
        :param use_uv`(bool|None)`: 使用 uv 替代 Pip 进行 Python 软件包的安装
        :param pypi_index_mirror`(str|None)`: PyPI Index 镜像源链接
        :param pypi_extra_index_mirror`(str|None)`: PyPI Extra Index 镜像源链接
        :param pypi_find_links_mirror`(str|None)`: PyPI Find Links 镜像源链接
        :param github_mirror`(str|list|None)`: Github 镜像源链接或者镜像源链接列表
        :param huggingface_mirror`(str|None)`: HuggingFace 镜像源链接
        :param pytorch_mirror`(str|None)`: PyTorch 镜像源链接
        :param fooocus_repo`(str|None)`: Fooocus 仓库地址
        :param fooocus_requirements`(str|None)`: Fooocus 依赖文件名
        :param fooocus_preset`(str|None)`: Fooocus 预设文件下载链接
        :param fooocus_translation`(str|None)`: Fooocus 翻译文件下载地址
        :param model_downloader`(Literal["aria2","request","mix"])`: 预下载模型时使用的模型下载器
        :param download_model_thread`(int|None)`: 预下载模型的线程
        :param check_avaliable_gpu`(bool|None)`: 是否检查可用的 GPU, 当检查时没有可用 GPU 将引发`Exception`
        :param enable_tcmalloc`(bool|None)`: 是否启用 TCMalloc 内存优化
        :param enable_cuda_malloc`(bool|None)`: 启用 CUDA 显存优化
        """
        self.utils.warning_unexpected_params(
            message="FooocusManager.install() 接收到不期望参数, 请检查参数输入是否正确",
            args=args,
            kwargs=kwargs,
        )
        logger.info("开始安装 Fooocus")
        os.chdir(self.workspace)
        fooocus_path = self.workspace / self.workfolder
        fooocus_repo = (
            "https://github.com/lllyasviel/Fooocus"
            if fooocus_repo is None
            else fooocus_repo
        )
        fooocus_preset = (
            "https://github.com/licyk/sd-webui-all-in-one/raw/main/fooocus_config.json"
            if fooocus_preset is None
            else fooocus_preset
        )
        fooocus_translation = (
            "https://github.com/licyk/sd-webui-all-in-one/raw/main/fooocus_zh_cn.json"
            if fooocus_translation is None
            else fooocus_translation
        )
        requirements_path = fooocus_path / (
            "requirements_versions.txt"
            if fooocus_requirements is None
            else fooocus_requirements
        )
        config_file = fooocus_path / "presets" / "custom.json"
        if check_avaliable_gpu and not self.utils.check_gpu():
            raise Exception(
                "没有可用的 GPU, 请在 Colab -> 代码执行程序 > 更改运行时类型 -> 硬件加速器 选择 GPU T4\n如果不能使用 GPU, 请尝试更换账号!"
            )
        logger.info("Fooocus 内核分支: %s", fooocus_repo)
        logger.info("Fooocus 预设配置: %s", fooocus_preset)
        logger.info("Fooocus 翻译配置: %s", fooocus_translation)
        self.mirror.set_mirror(
            pypi_index_mirror=pypi_index_mirror,
            pypi_extra_index_mirror=pypi_extra_index_mirror,
            pypi_find_links_mirror=pypi_find_links_mirror,
            github_mirror=github_mirror,
            huggingface_mirror=huggingface_mirror,
        )
        self.mirror.configure_pip()
        self.env.install_manager_depend(use_uv)
        self.git.clone(fooocus_repo, fooocus_path)
        self.git.update(fooocus_path)
        self.env.install_pytorch(
            torch_package=torch_ver,
            xformers_package=xformers_ver,
            pytorch_mirror=pytorch_mirror,
            use_uv=use_uv,
        )
        os.chdir(fooocus_path)
        self.env.install_requirements(requirements_path, use_uv)
        os.chdir(self.workspace)
        self.install_config(
            preset=fooocus_preset,
            translation=fooocus_translation,
        )
        if enable_tcmalloc:
            self.tcmalloc_colab()
        if enable_cuda_malloc:
            self.cuda_malloc.set_cuda_malloc()
        self.pre_download_model(
            path=config_file,
            thread_num=download_model_thread,
            downloader=model_downloader,
        )
        logger.info("Fooocus 安装完成")


class ComfyUIManager(BaseManager):
    """ComfyUI 管理工具"""

    def __init__(
        self,
        workspace: str | Path,
        workfolder: str,
        hf_token: str | None = None,
        ms_token: str | None = None,
        port: int | None = 8188,
    ) -> None:
        """管理工具初始化

        :param workspace`(str|Path)`: 工作区路径
        :param workfolder`(str)`: 工作区的文件夹名称
        :param hf_token`(str|None)`: HuggingFace Token
        :param ms_token`(str|None)`: ModelScope Token
        :param port`(int|None)`: 内网穿透端口
        """
        super().__init__(
            workspace=workspace,
            workfolder=workfolder,
            hf_token=hf_token,
            ms_token=ms_token,
            port=port,
        )
        self.env_check = ComfyUIRequirementCheck()

    def mount_drive(
        self,
        extras: list[dict[str, str | bool]] = None,
    ) -> None:
        """挂载 Google Drive 并创建 ComfyUI 输出文件夹

        :param extras`(list[dict[str,str|bool]])`: 挂载额外目录

        :notes
            挂载额外目录需要使用`link_dir`指定要挂载的路径, 并且使用相对路径指定

            相对路径的起始位置为`{self.workspace}/{self.workfolder}`

            若额外链接路径为文件, 需指定`is_file`属性为`True`

            例如:
            ```python
            extras = [
                {"link_dir": "models/loras"},
                {"link_dir": "custom_nodes"},
                {"link_dir": "extra_model_paths.yaml", "is_file": True},
            ]
            ```
            默认挂载的目录和文件: `output`, `user`, `input`, `extra_model_paths.yaml`
        """
        drive_path = Path("/content/drive")
        if not (drive_path / "MyDrive").exists():
            if not self.utils.mount_google_drive(drive_path):
                raise Exception("挂载 Google Drive 失败, 请尝试重新挂载 Google Drive")

        drive_output = drive_path / "MyDrive" / "comfyui_output"
        comfyui_path = self.workspace / self.workfolder
        drive_comfyui_output_path = drive_output / "output"
        comfyui_output_path = comfyui_path / "output"
        drive_comfyui_user_path = drive_output / "user"
        comfyui_user_path = comfyui_path / "user"
        drive_comfyui_input_path = drive_output / "input"
        comfyui_input_path = comfyui_path / "input"
        drive_comfyui_model_path_config = drive_output / "extra_model_paths.yaml"
        comfyui_model_path_config = comfyui_path / "extra_model_paths.yaml"
        self.utils.sync_files_and_create_symlink(
            src_path=drive_comfyui_output_path,
            link_path=comfyui_output_path,
        )
        self.utils.sync_files_and_create_symlink(
            src_path=drive_comfyui_user_path,
            link_path=comfyui_user_path,
        )
        self.utils.sync_files_and_create_symlink(
            src_path=drive_comfyui_input_path,
            link_path=comfyui_input_path,
        )
        if (
            comfyui_model_path_config.exists()
            or drive_comfyui_model_path_config.exists()
        ):
            self.utils.sync_files_and_create_symlink(
                src_path=drive_comfyui_model_path_config,
                link_path=comfyui_model_path_config,
                src_is_file=True,
            )
        if extras is None:
            return
        for extra in extras:
            link_dir = extra.get("link_dir")
            is_file = extra.get("is_file", False)
            if link_dir is None:
                continue
            full_link_path = comfyui_path / link_dir
            full_drive_path = drive_output / link_dir
            if is_file and (
                not full_link_path.exists() and not full_drive_path.exists()
            ):
                # 链接路径指定的是文件并且源文件和链接文件都不存在时则取消链接
                continue
            self.utils.sync_files_and_create_symlink(
                src_path=full_drive_path,
                link_path=full_link_path,
                src_is_file=is_file,
            )

    def get_sd_model(
        self,
        url: str,
        filename: str = None,
        model_type: str | None = "checkpoints",
    ) -> Path | None:
        """下载模型

        :param url`(str)`: 模型的下载链接
        :param filename`(str|None)`: 模型下载后保存的名称
        :param model_type`(str|None)`: 模型的类型
        :return `Path|None`: 模型保存路径
        """
        path = self.workspace / self.workfolder / "models" / model_type
        return self.get_model(url=url, path=path, filename=filename, tool="aria2")

    def get_sd_model_from_list(
        self,
        model_list: list[dict[str]],
    ) -> None:
        """从模型列表下载模型

        :param model_list`(list[str|int])`: 模型列表

        :notes
            `model_list`需要指定`url`(模型下载链接), 可选参数为`type`(模型类型), `filename`(模型保存名称), 例如
            ```python
            model_list = [
                {"url": "url1", "type": "checkpoints"},
                {"url": "url2", "filename": "file.safetensors"},
                {"url": "url3", "type": "loras", "filename": "lora1.safetensors"},
                {"url": "url4"},
            ]
            ```
        """
        for model in model_list:
            url = model.get("url")
            filename = model.get("filename")
            model_type = model.get("type", "checkpoints")
            self.get_sd_model(url=url, filename=filename, model_type=model_type)

    def install_config(
        self,
        setting: str | None = None,
    ) -> None:
        """下载 ComfyUI 配置文件

        :param setting`(str|None)`: ComfyUI 设置文件下载链接, 下载后将保存在`{self.workspace}/{self.workfolder}/user/default/comfy.settings.json`
        """
        setting_path = self.workspace / self.workfolder / "user" / "default"
        logger.info("下载配置文件")
        if setting is not None:
            self.downloader.download_file(
                url=setting,
                path=setting_path,
                save_name="comfy.settings.json",
                tool="aria2",
            )

    def install_custom_node(
        self,
        custom_node: str,
    ) -> Path | None:
        """安装 ComfyUI 自定义节点

        :param custom_node`(str)`: 自定义节点下载地址
        :return `Path|None`: 自定义节点安装路径
        """
        custom_node_path = self.workspace / self.workfolder / "custom_nodes"
        name = os.path.basename(custom_node)
        install_path = custom_node_path / name
        logger.info("安装 %s 自定义节点中", name)
        p = self.git.clone(repo=custom_node, path=install_path)
        if p is not None:
            logger.info("安装 %s 自定义节点完成", name)
            return p
        logger.error("安装 %s 自定义节点失败", name)
        return None

    def install_custom_nodes_from_list(
        self,
        custom_node_list: list[str],
    ) -> None:
        """安装 ComfyUI 自定义节点

        :param custom_node_list`(list[str])`: 自定义节点列表
        """
        logger.info("安装 ComfyUI 自定义节点中")
        for node in custom_node_list:
            self.install_custom_node(node)
        logger.info("安装 ComfyUI 自定义节点完成")

    def update_custom_nodes(self) -> None:
        """更新 ComfyUI 自定义节点"""
        custom_node_path = self.workspace / self.workfolder / "custom_nodes"
        custom_node_list = [
            x
            for x in custom_node_path.iterdir()
            if x.is_dir() and (x / ".git").is_dir()
        ]
        for i in custom_node_list:
            logger.info("更新 %s 自定义节点中", i.name)
            if self.git.update(i):
                logger.info("更新 %s 自定义节点成功", i.name)
            else:
                logger.info("更新 %s 自定义节点失败", i.name)

    def check_env(
        self,
        use_uv: bool | None = True,
        install_conflict_component_requirement: bool | None = True,
        requirements_file: str | None = "requirements.txt",
    ) -> None:
        """检查 ComfyUI 运行环境

        :param use_uv`(bool|None)`: 使用 uv 安装依赖
        :param install_conflict_component_requirement`(bool|None)`: 检测到冲突依赖时是否按顺序安装组件依赖
        :param requirements_file`(str|None)`: 依赖文件名
        """
        comfyui_path = self.workspace / self.workfolder
        requirement_path = comfyui_path / requirements_file
        self.env_check.check_env(
            requirement_path=requirement_path, name="ComfyUI", use_uv=use_uv
        )
        self.env_check.check_comfyui_env(
            comfyui_root_path=comfyui_path,
            install_conflict_component_requirement=install_conflict_component_requirement,
            use_uv=use_uv,
        )
        self.env_check.fix_torch()
        self.ort_check.check_onnxruntime_gpu(use_uv=use_uv, ignore_ort_install=True)
        self.env_check.check_numpy(use_uv=use_uv)

    def install(
        self,
        torch_ver: str | list | None = None,
        xformers_ver: str | list | None = None,
        use_uv: bool | None = True,
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list | None = None,
        huggingface_mirror: str | None = None,
        pytorch_mirror: str | None = None,
        comfyui_repo: str | None = None,
        comfyui_requirements: str | None = None,
        comfyui_setting: str | None = None,
        custom_node_list: list[str] | None = None,
        model_list: list[dict[str, str]] | None = None,
        check_avaliable_gpu: bool | None = False,
        enable_tcmalloc: bool | None = True,
        enable_cuda_malloc: bool | None = True,
        *args,
        **kwargs,
    ) -> None:
        """安装 ComfyUI

        :param torch_ver`(str|None)`: 指定的 PyTorch 软件包包名, 并包括版本号
        :param xformers_ver`(str|None)`: 指定的 xFormers 软件包包名, 并包括版本号
        :param use_uv`(bool|None)`: 使用 uv 替代 Pip 进行 Python 软件包的安装
        :param pypi_index_mirror`(str|None)`: PyPI Index 镜像源链接
        :param pypi_extra_index_mirror`(str|None)`: PyPI Extra Index 镜像源链接
        :param pypi_find_links_mirror`(str|None)`: PyPI Find Links 镜像源链接
        :param github_mirror`(str|list|None)`: Github 镜像源链接或者镜像源链接列表
        :param huggingface_mirror`(str|None)`: HuggingFace 镜像源链接
        :param pytorch_mirror`(str|None)`: PyTorch 镜像源链接
        :param comfyui_repo`(str|None)`: ComfyUI 仓库地址
        :param comfyui_requirements`(str|None)`: ComfyUI 依赖文件名
        :param comfyui_setting`(str|None)`: ComfyUI 设置文件下载链接
        :param custom_node_list`(list[str])`: 自定义节点列表
        :param model_list`(list[dict[str,str]])`: 模型下载列表
        :param check_avaliable_gpu`(bool|None)`: 是否检查可用的 GPU, 当检查时没有可用 GPU 将引发`Exception`
        :param enable_tcmalloc`(bool|None)`: 是否启用 TCMalloc 内存优化
        :param enable_cuda_malloc`(bool|None)`: 启用 CUDA 显存优化
        """
        self.utils.warning_unexpected_params(
            message="ComfyUIManager.install() 接收到不期望参数, 请检查参数输入是否正确",
            args=args,
            kwargs=kwargs,
        )
        logger.info("开始安装 ComfyUI")
        os.chdir(self.workspace)
        comfyui_path = self.workspace / self.workfolder
        comfyui_repo = (
            "https://github.com/comfyanonymous/ComfyUI"
            if comfyui_repo is None
            else comfyui_repo
        )
        comfyui_setting = (
            "https://github.com/licyk/sd-webui-all-in-one/raw/main/comfy.settings.json"
            if comfyui_setting is None
            else comfyui_setting
        )
        requirements_path = comfyui_path / (
            "requirements.txt" if comfyui_requirements is None else comfyui_requirements
        )
        if check_avaliable_gpu and not self.utils.check_gpu():
            raise Exception(
                "没有可用的 GPU, 请在 Colab -> 代码执行程序 > 更改运行时类型 -> 硬件加速器 选择 GPU T4\n如果不能使用 GPU, 请尝试更换账号!"
            )
        self.mirror.set_mirror(
            pypi_index_mirror=pypi_index_mirror,
            pypi_extra_index_mirror=pypi_extra_index_mirror,
            pypi_find_links_mirror=pypi_find_links_mirror,
            github_mirror=github_mirror,
            huggingface_mirror=huggingface_mirror,
        )
        self.mirror.configure_pip()
        self.env.install_manager_depend(use_uv)
        self.git.clone(comfyui_repo, comfyui_path)
        if custom_node_list is not None:
            self.install_custom_nodes_from_list(custom_node_list)
        self.git.update(comfyui_path)
        self.update_custom_nodes()
        self.env.install_pytorch(
            torch_package=torch_ver,
            xformers_package=xformers_ver,
            pytorch_mirror=pytorch_mirror,
            use_uv=use_uv,
        )
        os.chdir(comfyui_path)
        self.env.install_requirements(requirements_path, use_uv)
        os.chdir(self.workspace)
        self.install_config(comfyui_setting)
        if model_list is not None:
            self.get_sd_model_from_list(model_list)
        if enable_tcmalloc:
            self.tcmalloc_colab()
        if enable_cuda_malloc:
            self.cuda_malloc.set_cuda_malloc()
        logger.info("ComfyUI 安装完成")


class SDWebUIManager(BaseManager):
    """Stable Diffusion WebUI 管理工具"""

    def mount_drive(
        self,
        extras: list[dict[str, str | bool]] = None,
    ) -> None:
        """挂载 Google Drive 并创建 Stable Diffusion WebUI 输出文件夹

        :param extras`(list[dict[str,str|bool]])`: 挂载额外目录

        :notes
            挂载额外目录需要使用`link_dir`指定要挂载的路径, 并且使用相对路径指定

            相对路径的起始位置为`{self.workspace}/{self.workfolder}`

            若额外链接路径为文件, 需指定`is_file`属性为`True`

            例如:
            ```python
            extras = [
                {"link_dir": "models/loras"},
                {"link_dir": "custom_nodes"},
                {"link_dir": "extra_model_paths.yaml", "is_file": True},
            ]
            ```
            默认挂载的目录和文件: `outputs`, `config_states`, `params.txt`, `config.json`, `ui-config.json`, `styles.csv`
        """
        drive_path = Path("/content/drive")
        if not (drive_path / "MyDrive").exists():
            if not self.utils.mount_google_drive(drive_path):
                raise Exception("挂载 Google Drive 失败, 请尝试重新挂载 Google Drive")

        drive_output = drive_path / "MyDrive" / "sd_webui_output"
        sd_webui_path = self.workspace / self.workfolder
        drive_sd_webui_output_path = drive_output / "outputs"
        sd_webui_output_path = sd_webui_path / "outputs"
        drive_sd_webui_config_states_path = drive_output / "config_states"
        sd_webui_config_states_path = sd_webui_path / "config_states"
        drive_sd_webui_params = drive_output / "params.txt"
        sd_webui_params = sd_webui_path / "params.txt"
        drive_sd_webui_config = drive_output / "config.json"
        sd_webui_config = sd_webui_path / "config.json"
        drive_sd_webui_ui_config = drive_output / "ui-config.json"
        sd_webui_ui_config = sd_webui_path / "ui-config.json"
        drive_sd_webui_styles = drive_output / "styles.csv"
        sd_webui_styles = sd_webui_path / "styles.csv"
        self.utils.sync_files_and_create_symlink(
            src_path=drive_sd_webui_output_path,
            link_path=sd_webui_output_path,
        )
        self.utils.sync_files_and_create_symlink(
            src_path=drive_sd_webui_config_states_path,
            link_path=sd_webui_config_states_path,
        )
        if sd_webui_params.exists() or drive_sd_webui_params.exists():
            self.utils.sync_files_and_create_symlink(
                src_path=drive_sd_webui_params,
                link_path=sd_webui_params,
                src_is_file=True,
            )
        if sd_webui_config.exists() or drive_sd_webui_config.exists():
            self.utils.sync_files_and_create_symlink(
                src_path=drive_sd_webui_config,
                link_path=sd_webui_config,
                src_is_file=True,
            )
        if sd_webui_ui_config.exists() or drive_sd_webui_ui_config.exists():
            self.utils.sync_files_and_create_symlink(
                src_path=drive_sd_webui_ui_config,
                link_path=sd_webui_ui_config,
                src_is_file=True,
            )
        if sd_webui_styles.exists() or drive_sd_webui_styles.exists():
            self.utils.sync_files_and_create_symlink(
                src_path=drive_sd_webui_styles,
                link_path=sd_webui_styles,
                src_is_file=True,
            )
        if extras is None:
            return
        for extra in extras:
            link_dir = extra.get("link_dir")
            is_file = extra.get("is_file", False)
            if link_dir is None:
                continue
            full_link_path = sd_webui_path / link_dir
            full_drive_path = drive_output / link_dir
            if is_file and (
                not full_link_path.exists() and not full_drive_path.exists()
            ):
                # 链接路径指定的是文件并且源文件和链接文件都不存在时则取消链接
                continue
            self.utils.sync_files_and_create_symlink(
                src_path=full_drive_path,
                link_path=full_link_path,
                src_is_file=is_file,
            )

    def get_sd_model(
        self,
        url: str,
        filename: str = None,
        model_type: str | None = "Stable-diffusion",
    ) -> Path | None:
        """下载模型

        :param url`(str)`: 模型的下载链接
        :param filename`(str|None)`: 模型下载后保存的名称
        :param model_type`(str|None)`: 模型的类型
        :return `Path|None`: 模型保存路径
        """
        if model_type == "embeddings":
            path = self.workspace / self.workfolder / model_type
        else:
            path = self.workspace / self.workfolder / "models" / model_type
        return self.get_model(url=url, path=path, filename=filename, tool="aria2")

    def get_sd_model_from_list(
        self,
        model_list: list[dict[str]],
    ) -> None:
        """从模型列表下载模型

        :param model_list`(list[str|int])`: 模型列表

        :notes
            `model_list`需要指定`url`(模型下载链接), 可选参数为`type`(模型类型), `filename`(模型保存名称), 例如
            ```python
            model_list = [
                {"url": "url1", "type": "Stable-diffusion"},
                {"url": "url2", "filename": "file.safetensors"},
                {"url": "url3", "type": "loras", "filename": "lora1.safetensors"},
                {"url": "url4"},
            ]
            ```
        """
        for model in model_list:
            url = model.get("url")
            filename = model.get("filename")
            model_type = model.get("type", "Stable-diffusion")
            self.get_sd_model(url=url, filename=filename, model_type=model_type)

    def install_config(
        self,
        setting: str | None = None,
        requirements: str | None = None,
        requirements_file: str | None = None,
    ) -> None:
        """下载 Stable Diffusion WebUI 配置文件

        :param setting`(str|None)`: Stable Diffusion WebUI 设置文件下载链接, 下载后将保存在`{self.workspace}/{self.workfolder}/config.json`
        :param requirements`(str|None)`: Stable Diffusion WebUI 依赖表文件下载链接, 下载后将保存在`{self.workspace}/{self.workfolder}/{requirements_file}`
        :param requirements_file`(str|None)`: Stable Diffusion WebUI 依赖表文件名
        """
        setting_path = self.workspace / self.workfolder
        logger.info("下载配置文件")
        if setting is not None:
            self.downloader.download_file(
                url=setting, path=setting_path, save_name="config.json", tool="aria2"
            )
        if requirements is not None:
            try:
                (setting_path / requirements_file).unlink(missing_ok=True)
                self.downloader.download_file(
                    url=requirements,
                    path=setting_path,
                    save_name=requirements_file,
                    tool="aria2",
                )
            except Exception as e:
                logger.error("下载 Stable Diffusion WebUI 依赖文件出现错误: %s", e)

    def install_extension(
        self,
        extension: str,
    ) -> Path | None:
        """安装 Stable Diffusion WebUI 扩展

        :param extension`(str)`: 扩展下载地址
        :return `Path|None`: 扩展安装路径
        """
        extension_path = self.workspace / self.workfolder / "extensions"
        name = os.path.basename(extension)
        install_path = extension_path / name
        logger.info("安装 %s 扩展中", name)
        p = self.git.clone(repo=extension, path=install_path)
        if p is not None:
            logger.info("安装 %s 扩展完成", name)
            return p
        logger.error("安装 %s 扩展失败", name)
        return None

    def install_extensions_from_list(
        self,
        extension_list: list[str],
    ) -> None:
        """安装 Stable Diffusion WebUI 扩展

        :param extension_list`(list[str])`: 扩展列表
        """
        logger.info("安装 Stable Diffusion WebUI 扩展中")
        for extension in extension_list:
            self.install_extension(extension)
        logger.info("安装 Stable Diffusion WebUI 扩展完成")

    def run_extension_installer(
        self, sd_webui_base_path: Path, extension_dir: Path
    ) -> bool:
        """执行扩展依赖安装脚本

        :param sd_webui_base_path`(Path)`: SD WebUI 跟目录, 用于导入自身模块
        :param extension_dir`(Path)`: 要执行安装脚本的扩展路径
        :return `bool`: 扩展依赖安装结果
        """
        path_installer = extension_dir / "install.py"
        if not path_installer.is_file():
            return

        try:
            env = os.environ.copy()
            py_path = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{sd_webui_base_path}{os.pathsep}{py_path}"
            env["WEBUI_LAUNCH_LIVE_OUTPUT"] = "1"
            run_cmd(
                command=[Path(sys.executable).as_posix(), path_installer.as_posix()],
                custom_env=env,
            )
            return True
        except Exception as e:
            logger.info("执行 %s 扩展依赖安装脚本时发生错误: %s", extension_dir.name, e)
            traceback.print_exc()
            return False

    def install_extension_requirements(
        self,
        sd_webui_base_path: Path,
        arg_disable_extra_extensions: bool = False,
        arg_disable_all_extensions: bool = False,
    ) -> None:
        """安装 SD WebUI 扩展依赖

        :param sd_webui_base_path`(Path)`: SD WebUI 根目录
        :param arg_disable_extra_extensions`(bool)`: 是否禁用 SD WebUI 额外扩展
        :param arg_disable_all_extensions`(bool)`: 是否禁用 SD WebUI 所有扩展
        """
        settings_file = sd_webui_base_path / "config.json"
        extensions_dir = sd_webui_base_path / "extensions"
        builtin_extensions_dir = sd_webui_base_path / "extensions-builtin"
        ext_install_list = []
        ext_builtin_install_list = []
        settings = {}

        try:
            with open(settings_file, "r", encoding="utf8") as file:
                settings = json.load(file)
        except Exception as e:
            logger.warning("Stable Diffusion WebUI 配置文件无效: %s", e)

        disabled_extensions = set(settings.get("disabled_extensions", []))
        disable_all_extensions = settings.get("disable_all_extensions", "none")

        if disable_all_extensions == "all" or arg_disable_all_extensions:
            logger.info("已禁用所有 Stable Diffusion WebUI 扩展, 不执行扩展依赖检查")
            return

        if (
            extensions_dir.is_dir()
            and disable_all_extensions != "extra"
            and not arg_disable_extra_extensions
        ):
            ext_install_list = [
                x
                for x in extensions_dir.glob("*")
                if x.name not in disabled_extensions and (x / "install.py").is_file()
            ]

        if builtin_extensions_dir.is_dir():
            ext_builtin_install_list = [
                x
                for x in builtin_extensions_dir.glob("*")
                if x.name not in disabled_extensions and (x / "install.py").is_file()
            ]

        install_list = ext_install_list + ext_builtin_install_list
        extension_count = len(install_list)

        if extension_count == 0:
            logger.info("无待安装依赖的 Stable Diffusion WebUI 扩展")
            return

        count = 0
        for ext in install_list:
            count += 1
            ext_name = ext.name
            logger.info(
                "[%s/%s] 执行 %s 扩展的依赖安装脚本中", count, extension_count, ext_name
            )
            if self.run_extension_installer(
                sd_webui_base_path=sd_webui_base_path,
                extension_dir=ext,
            ):
                logger.info(
                    "[%s/%s] 执行 %s 扩展的依赖安装脚本成功",
                    count,
                    extension_count,
                    ext_name,
                )
            else:
                logger.warning(
                    "[%s/%s] 执行 %s 扩展的依赖安装脚本失败, 可能会导致该扩展运行异常",
                    count,
                    extension_count,
                    ext_name,
                )

        logger.info(
            "[%s/%s] 安装 Stable Diffusion WebUI 扩展依赖结束", count, extension_count
        )

    def update_extensions(self) -> None:
        """更新 Stable Diffusion WebUI 扩展"""
        extension_path = self.workspace / self.workfolder / "extensions"
        extension_list = [
            x for x in extension_path.iterdir() if x.is_dir() and (x / ".git").is_dir()
        ]
        for i in extension_list:
            logger.info("更新 %s 扩展中", i.name)
            if self.git.update(i):
                logger.info("更新 %s 扩展成功", i.name)
            else:
                logger.info("更新 %s 扩展失败", i.name)

    def check_env(
        self,
        use_uv: bool | None = True,
        requirements_file: str | None = "requirements_versions.txt",
    ) -> None:
        """检查 Stable Diffusion WebUI 运行环境

        :param use_uv`(bool|None)`: 使用 uv 安装依赖
        :param requirements_file`(str|None)`: 依赖文件名
        """
        sd_webui_path = self.workspace / self.workfolder
        requirement_path = sd_webui_path / requirements_file
        self.env_check.check_env(
            requirement_path=requirement_path,
            name="Stable Diffusion WebUI",
            use_uv=use_uv,
        )
        self.install_extension_requirements(sd_webui_base_path=sd_webui_path)
        self.env_check.fix_torch()
        self.ort_check.check_onnxruntime_gpu(use_uv=use_uv, ignore_ort_install=True)
        self.env_check.check_numpy(use_uv=use_uv)

    def install(
        self,
        torch_ver: str | list | None = None,
        xformers_ver: str | list | None = None,
        use_uv: bool | None = True,
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list | None = None,
        huggingface_mirror: str | None = None,
        pytorch_mirror: str | None = None,
        sd_webui_repo: str | None = None,
        sd_webui_branch: str | None = None,
        sd_webui_requirements: str | None = None,
        sd_webui_requirements_url: str | None = None,
        sd_webui_setting: str | None = None,
        extension_list: list[str] | None = None,
        model_list: list[dict[str, str]] | None = None,
        check_avaliable_gpu: bool | None = False,
        enable_tcmalloc: bool | None = True,
        enable_cuda_malloc: bool | None = True,
        *args,
        **kwargs,
    ) -> None:
        """安装 Stable Diffusion WebUI

        :param torch_ver`(str|None)`: 指定的 PyTorch 软件包包名, 并包括版本号
        :param xformers_ver`(str|None)`: 指定的 xFormers 软件包包名, 并包括版本号
        :param use_uv`(bool|None)`: 使用 uv 替代 Pip 进行 Python 软件包的安装
        :param pypi_index_mirror`(str|None)`: PyPI Index 镜像源链接
        :param pypi_extra_index_mirror`(str|None)`: PyPI Extra Index 镜像源链接
        :param pypi_find_links_mirror`(str|None)`: PyPI Find Links 镜像源链接
        :param github_mirror`(str|list|None)`: Github 镜像源链接或者镜像源链接列表
        :param huggingface_mirror`(str|None)`: HuggingFace 镜像源链接
        :param pytorch_mirror`(str|None)`: PyTorch 镜像源链接
        :param sd_webui_repo`(str|None)`: Stable Diffusion WebUI 仓库地址
        :param sd_webui_branch`(str|None)`: Stable Diffusion WebUI 分支
        :param sd_webui_requirements`(str|None)`: Stable Diffusion WebUI 依赖文件名
        :param sd_webui_requirements_url`(str|None)`: Stable Diffusion WebUI 依赖文件下载地址
        :param sd_webui_setting`(str|None)`: Stable Diffusion WebUI 预设文件下载链接
        :param extension_list`(list[str])`: 扩展列表
        :param model_list`(list[dict[str,str]])`: 模型下载列表
        :param check_avaliable_gpu`(bool|None)`: 是否检查可用的 GPU, 当检查时没有可用 GPU 将引发`Exception`
        :param enable_tcmalloc`(bool|None)`: 是否启用 TCMalloc 内存优化
        :param enable_cuda_malloc`(bool|None)`: 启用 CUDA 显存优化
        """
        self.utils.warning_unexpected_params(
            message="SDWebUIManager.install() 接收到不期望参数, 请检查参数输入是否正确",
            args=args,
            kwargs=kwargs,
        )
        logger.info("开始安装 Stable Diffusion WebUI")
        os.chdir(self.workspace)
        sd_webui_path = self.workspace / self.workfolder
        sd_webui_repo = (
            "https://github.com/AUTOMATIC1111/stable-diffusion-webui"
            if sd_webui_repo is None
            else sd_webui_repo
        )
        sd_webui_setting = (
            "https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_webui_config.json"
            if sd_webui_setting is None
            else sd_webui_setting
        )
        requirements_path = sd_webui_path / (
            "requirements_versions.txt"
            if sd_webui_requirements is None
            else sd_webui_requirements
        )
        if check_avaliable_gpu and not self.utils.check_gpu():
            raise Exception(
                "没有可用的 GPU, 请在 Colab -> 代码执行程序 > 更改运行时类型 -> 硬件加速器 选择 GPU T4\n如果不能使用 GPU, 请尝试更换账号!"
            )
        self.mirror.set_mirror(
            pypi_index_mirror=pypi_index_mirror,
            pypi_extra_index_mirror=pypi_extra_index_mirror,
            pypi_find_links_mirror=pypi_find_links_mirror,
            github_mirror=github_mirror,
            huggingface_mirror=huggingface_mirror,
        )
        self.mirror.configure_pip()
        self.env.install_manager_depend(use_uv)
        self.git.clone(sd_webui_repo, sd_webui_path)
        if extension_list is not None:
            self.install_extensions_from_list(extension_list)
        self.git.update(sd_webui_path)
        self.update_extensions()
        if sd_webui_branch is not None:
            self.git.switch_branch(
                path=sd_webui_path,
                branch=sd_webui_branch,
                recurse_submodules=True,
            )
        self.env.install_pytorch(
            torch_package=torch_ver,
            xformers_package=xformers_ver,
            pytorch_mirror=pytorch_mirror,
            use_uv=use_uv,
        )
        os.chdir(sd_webui_path)
        self.install_config(
            setting=sd_webui_setting,
            requirements=sd_webui_requirements_url,
            requirements_file=requirements_path.name,
        )
        self.env.install_requirements(requirements_path, use_uv)
        os.chdir(self.workspace)
        if model_list is not None:
            self.get_sd_model_from_list(model_list)
        if enable_tcmalloc:
            self.tcmalloc_colab()
        if enable_cuda_malloc:
            self.cuda_malloc.set_cuda_malloc()
        logger.info("Stable Diffusion WebUI 安装完成")


# PyTorch 镜像源字典
PYTORCH_MIRROR_DICT = {
    "other": "https://download.pytorch.org/whl",
    "cpu": "https://download.pytorch.org/whl/cpu",
    "xpu": "https://download.pytorch.org/whl/xpu",
    "rocm61": "https://download.pytorch.org/whl/rocm6.1",
    "rocm62": "https://download.pytorch.org/whl/rocm6.2",
    "rocm624": "https://download.pytorch.org/whl/rocm6.2.4",
    "rocm63": "https://download.pytorch.org/whl/rocm6.3",
    "rocm64": "https://download.pytorch.org/whl/rocm6.4",
    "cu118": "https://download.pytorch.org/whl/cu118",
    "cu121": "https://download.pytorch.org/whl/cu121",
    "cu124": "https://download.pytorch.org/whl/cu124",
    "cu126": "https://download.pytorch.org/whl/cu126",
    "cu128": "https://download.pytorch.org/whl/cu128",
    "cu129": "https://download.pytorch.org/whl/cu129",
}


class InvokeAIComponentManager:
    """InvokeAI 组件管理器"""

    def __init__(self, pytorch_mirror_dict: dict[str, str] = None) -> None:
        """InvokeAI 组件管理器初始化

        :param pytorch_mirror_dict`(dict[str,str]|None)`: PyTorch 镜像源字典, 需包含不同镜像源类型对应的镜像地址
        """
        if pytorch_mirror_dict is None:
            pytorch_mirror_dict = PYTORCH_MIRROR_DICT
        self.pytorch_mirror_dict = pytorch_mirror_dict

    def update_pytorch_mirror_dict(self, pytorch_mirror_dict: dict[str, str]) -> None:
        """更新 PyTorch 镜像源字典

        :param pytorch_mirror_dict`(dict[str,str])`: PyTorch 镜像源字典, 需包含不同镜像源类型对应的镜像地址
        """
        logger.info("更新 PyTorch 镜像源信息")
        self.pytorch_mirror_dict = pytorch_mirror_dict

    def get_pytorch_mirror_url(self, mirror_type: str) -> str | None:
        """获取 PyTorch 类型对应的镜像源

        :param mirror_type`(str)`: PyTorch 类型
        :return `str|None`: 对应的 PyTorch 镜像源
        """
        return self.pytorch_mirror_dict.get(mirror_type)

    def get_invokeai_require_torch_version(self) -> str:
        """获取 InvokeAI 依赖的 PyTorch 版本

        :return `str`: PyTorch 版本
        """
        try:
            invokeai_requires = importlib.metadata.requires("invokeai")
        except Exception as _:
            return "2.2.2"

        torch_version = "torch==2.2.2"

        for require in invokeai_requires:
            if RequirementCheck.get_package_name(
                require
            ) == "torch" and RequirementCheck.is_package_has_version(require):
                torch_version = require.split(";")[0]
                break

        if torch_version.startswith("torch>") and not torch_version.startswith(
            "torch>="
        ):
            return Utils.version_increment(
                RequirementCheck.get_package_version(torch_version)
            )
        elif torch_version.startswith("torch<") and not torch_version.startswith(
            "torch<="
        ):
            return Utils.version_decrement(
                RequirementCheck.get_package_version(torch_version)
            )
        elif torch_version.startswith("torch!="):
            return Utils.version_increment(
                RequirementCheck.get_package_version(torch_version)
            )
        else:
            return RequirementCheck.get_package_version(torch_version)

    def get_pytorch_mirror_type_for_ivnokeai(
        self,
        device_type: Literal["cuda", "rocm", "xpu", "cpu"],
    ) -> str:
        """获取 InvokeAI 安装 PyTorch 所需的 PyTorch 镜像源类型

        :param device_type`(Literal["cuda","rocm","xpu","cpu"])`: 显卡设备类型
        """
        torch_ver = self.get_invokeai_require_torch_version()
        return Utils.get_pytorch_mirror_type(
            torch_ver=torch_ver, device_type=device_type
        )

    def get_pytorch_for_invokeai(self) -> str:
        """获取 InvokeAI 所依赖的 PyTorch 包版本声明

        :param `str`: PyTorch 包版本声明
        """
        pytorch_ver = []
        try:
            invokeai_requires = importlib.metadata.requires("invokeai")
        except Exception as _:
            invokeai_requires = []

        torch_added = False
        torchvision_added = False
        torchaudio_added = False

        for require in invokeai_requires:
            require = require.split(";")[0].strip()
            package_name = RequirementCheck.get_package_name(require)

            if package_name == "torch" and not torch_added:
                pytorch_ver.append(require)
                torch_added = True

            if package_name == "torchvision" and not torchvision_added:
                pytorch_ver.append(require)
                torchvision_added = True

            if package_name == "torchaudio" and not torchaudio_added:
                pytorch_ver.append(require)
                torchaudio_added = True

        return " ".join([str(x).strip() for x in pytorch_ver])

    def get_xformers_for_invokeai(self) -> str:
        """获取 InvokeAI 所依赖的 xFormers 包版本声明

        :param `str`: xFormers 包版本声明
        """
        pytorch_ver = []
        try:
            invokeai_requires = importlib.metadata.requires("invokeai")
        except Exception as _:
            invokeai_requires = []

        xformers_added = False

        for require in invokeai_requires:
            require = require.split(";")[0].strip()
            package_name = RequirementCheck.get_package_name(require)

            if package_name == "xformers" and not xformers_added:
                pytorch_ver.append(require)
                xformers_added = True

        return " ".join([str(x).strip() for x in pytorch_ver])

    def sync_invokeai_component(
        self,
        device_type: str,
        use_uv: bool | None = True,
    ) -> None:
        """同步 InvokeAI 组件

        :param device_type`(str)`: 显卡设备类型
        :param use_uv`(bool|None)`: 是否使用 uv 安装 Python 软件包
        :return `bool`: 同步组件结果
        """
        logger.info("获取安装配置")
        invokeai_ver = importlib.metadata.version("invokeai")
        torch_ver = self.get_invokeai_require_torch_version()
        pytorch_mirror_type = Utils.get_pytorch_mirror_type(
            torch_ver=torch_ver,
            device_type=device_type,
        )
        pytorch_mirror = self.get_pytorch_mirror_url(pytorch_mirror_type)
        pytorch_package = self.get_pytorch_for_invokeai()
        xformers_package = self.get_xformers_for_invokeai()
        pytorch_package_args = []
        if pytorch_mirror_type in ["cpu", "xpu", "ipex_legacy_arc", "rocm62", "other"]:
            for i in pytorch_package.split():
                pytorch_package_args.append(i.strip())
        else:
            for i in pytorch_package.split():
                pytorch_package_args.append(i.strip())
            for i in xformers_package.split():
                pytorch_package_args.append(i.strip())

        try:
            logger.info("同步 PyTorch 组件中")
            if pytorch_mirror is not None:
                EnvManager.install_pytorch(
                    torch_package=pytorch_package_args,
                    pytorch_mirror=pytorch_mirror,
                    use_uv=use_uv,
                )
            else:
                EnvManager.install_pytorch(
                    torch_package=pytorch_package_args,
                    use_uv=use_uv,
                )
            logger.info("同步 InvokeAI 其他组件中")
            EnvManager.pip_install(f"invokeai=={invokeai_ver}", use_uv=use_uv)
            logger.info("同步 InvokeAI 组件完成")
            return True
        except Exception as e:
            logger.error("同步 InvokeAI 组件时发生了错误: %s", e)
            return False

    def install_invokeai(
        self,
        device_type: str,
        upgrade: bool | None = False,
        use_uv: bool | None = True,
    ) -> None:
        """安装 InvokeAI

        :param device_type`(str)`: 显卡设备类型
        :param upgrade`(bool|None)`: 更新 InvokeAI
        :param use_uv`(bool|None)`: 是否使用 uv 安装 Python 软件包
        """
        logger.info("安装 InvokeAI 核心中")
        try:
            if upgrade:
                EnvManager.pip_install(
                    "invokeai", "--no-deps", "--upgrade", use_uv=use_uv
                )
            else:
                EnvManager.pip_install("invokeai", "--no-deps", use_uv=use_uv)

            self.sync_invokeai_component(
                device_type=device_type,
                use_uv=use_uv,
            )
        except Exception as e:
            logger.error("安装 InvokeAI 失败: %s", e)


class InvokeAIManager(BaseManager):
    """InvokeAI 管理模块"""

    def __init__(
        self,
        workspace: str | Path,
        workfolder: str,
        hf_token: str | None = None,
        ms_token: str | None = None,
        port: int | None = 9090,
    ) -> None:
        """管理工具初始化

        :param workspace`(str|Path)`: 工作区路径
        :param workfolder`(str)`: 工作区的文件夹名称
        :param hf_token`(str|None)`: HuggingFace Token
        :param ms_token`(str|None)`: ModelScope Token
        :param port`(int|None)`: 内网穿透端口
        """
        super().__init__(
            workspace=workspace,
            workfolder=workfolder,
            hf_token=hf_token,
            ms_token=ms_token,
            port=port,
        )
        self.component = InvokeAIComponentManager()

    def mount_drive(self) -> None:
        """挂载 Google Drive 并创建 InvokeAI 输出文件夹, 并设置 INVOKEAI_ROOT 环境变量指定 InvokeAI 输出目录"""
        drive_path = Path("/content/drive")
        if not (drive_path / "MyDrive").exists():
            if not self.utils.mount_google_drive(drive_path):
                raise Exception("挂载 Google Drive 失败, 请尝试重新挂载 Google Drive")

        invokeai_output = drive_path / "MyDrive" / "invokeai_output"
        invokeai_output.mkdir(parents=True, exist_ok=True)
        os.environ["INVOKEAI_ROOT"] = invokeai_output.as_posix()

    def import_model_to_invokeai(
        self,
        model_list: list[str],
    ) -> None:
        """将模型列表导入到 InvokeAI 中

        :param model_list`(list[str])`: 模型路径列表
        """
        try:
            logger.info("导入 InvokeAI 模块中")
            import asyncio
            from invokeai.app.services.model_manager.model_manager_default import (
                ModelManagerService,
            )
            from invokeai.app.services.model_install.model_install_common import (
                InstallStatus,
            )
            from invokeai.app.services.model_records.model_records_sql import (
                ModelRecordServiceSQL,
            )
            from invokeai.app.services.download.download_default import (
                DownloadQueueService,
            )
            from invokeai.app.services.events.events_fastapievents import (
                FastAPIEventService,
            )
            from invokeai.app.services.config.config_default import get_config
            from invokeai.app.services.shared.sqlite.sqlite_util import init_db
            from invokeai.app.services.image_files.image_files_disk import (
                DiskImageFileStorage,
            )
            from invokeai.app.services.invoker import Invoker
        except Exception as e:
            logger.error("导入 InvokeAI 模块失败, 无法自动导入模型: %s", e)
            return

        def _get_invokeai_model_manager() -> ModelManagerService:
            logger.info("初始化 InvokeAI 模型管理服务中")
            configuration = get_config()
            output_folder = configuration.outputs_path
            image_files = DiskImageFileStorage(f"{output_folder}/images")
            db = init_db(config=configuration, logger=logger, image_files=image_files)
            event_handler_id = 1234
            loop = asyncio.get_event_loop()
            events = FastAPIEventService(event_handler_id, loop=loop)

            model_manager = ModelManagerService.build_model_manager(
                app_config=configuration,
                model_record_service=ModelRecordServiceSQL(db=db, logger=logger),
                download_queue=DownloadQueueService(
                    app_config=configuration, event_bus=events
                ),
                events=FastAPIEventService(event_handler_id, loop=loop),
            )

            logger.info("初始化 InvokeAI 模型管理服务完成")
            return model_manager

        def _import_model(
            model_manager: ModelManagerService, inplace: bool, model_path: str | Path
        ) -> bool:
            model_path = Path(model_path)
            file_name = model_path.name
            try:
                logger.info(f"导入 {file_name} 模型到 InvokeAI 中")
                job = model_manager.install.heuristic_import(
                    source=model_path.as_posix(), inplace=inplace
                )
                result = model_manager.install.wait_for_job(job)
                if result.status == InstallStatus.COMPLETED:
                    logger.info(f"导入 {file_name} 模型到 InvokeAI 成功")
                    return True
                else:
                    logger.error(
                        f"导入 {file_name} 模型到 InvokeAI 时出现了错误: {result.error}"
                    )
                    return False
            except Exception as e:
                logger.error(f"导入 {file_name} 模型到 InvokeAI 时出现了错误: {e}")
                return False

        install_model_to_local = False
        install_result = []
        count = 0
        task_sum = len(model_list)
        if task_sum == 0:
            logger.info("无需要导入的模型")
            return
        logger.info("InvokeAI 根目录: {}".format(os.environ.get("INVOKEAI_ROOT")))
        try:
            model_manager = _get_invokeai_model_manager()
            logger.info("启动 InvokeAI 模型管理服务")
            model_manager.start(Invoker)
        except Exception as e:
            logger.error("启动 InvokeAI 模型管理服务失败, 无法导入模型: %s", e)
            return
        logger.info(
            "就地安装 (仅本地) 模式: {}".format(
                "禁用" if install_model_to_local else "启用"
            )
        )
        for model in model_list:
            count += 1
            file_name = os.path.basename(model)
            logger.info(f"[{count}/{task_sum}] 添加模型: {file_name}")
            result = _import_model(
                model_manager=model_manager,
                inplace=not install_model_to_local,
                model_path=model,
            )
            install_result.append([model, file_name, result])
        logger.info("关闭 InvokeAI 模型管理服务")
        try:
            model_manager.stop(Invoker)
        except Exception as e:
            logger.error("关闭 InvokeAI 模型管理服务出现错误: %s", e)
        logger.info("导入 InvokeAI 模型结果")
        print("-" * 70)
        for _, file, status in install_result:
            status = "导入成功" if status else "导入失败"
            print(f"- {file}: {status}")

        print("-" * 70)
        has_failed = False
        for _, _, x in install_result:
            if not x:
                has_failed = True
                break

        if has_failed:
            logger.warning("导入失败的模型列表和模型路径")
            print("-" * 70)
            for model, file_name, status in install_result:
                if not status:
                    print(f"- {file_name}: {model}")
            print("-" * 70)
            logger.warning(
                "导入失败的模型可尝试通过在 InvokeAI 的模型管理 -> 添加模型 -> 链接和本地路径, 手动输入模型路径并添加"
            )

        logger.info("导入模型结束")

    def import_model(self) -> None:
        """导入模型到 InvokeAI 中"""
        model_path = self.workspace / self.workfolder / "sd-models"
        model_list = Utils.get_file_list(model_path)
        try:
            self.mount_drive()
        except Exception as e:
            logger.error("挂载 Google Drive 失败, 无法导入模型: %s", e)
            return
        self.import_model_to_invokeai(model_list)

    def get_sd_model(
        self,
        url: str,
        filename: str = None,
    ) -> Path | None:
        """下载模型

        :param url`(str)`: 模型的下载链接
        :param filename`(str|None)`: 模型下载后保存的名称
        :param model_type`(str|None)`: 模型的类型
        :return `Path|None`: 模型保存路径
        """
        path = self.workspace / self.workfolder / "sd-models"
        return self.get_model(url=url, path=path, filename=filename, tool="aria2")

    def get_sd_model_from_list(
        self,
        model_list: list[str],
        retry: int | None = 3,
    ) -> None:
        """从模型列表下载模型

        :param model_list`(list[str])`: 模型列表
        :param retry`(int|None)`: 重试下载的次数, 默认为 3
        """
        new_model_list = [[model, 1] for model in model_list]
        self.get_model_from_list(
            path=self.workspace / self.workfolder / "sd-models",
            model_list=new_model_list,
            retry=retry,
        )

    def check_env(
        self,
        use_uv: bool | None = True,
    ) -> None:
        """检查 InvokeAI 运行环境

        :param use_uv`(bool|None)`: 使用 uv 安装依赖
        """
        self.env_check.fix_torch()
        self.ort_check.check_onnxruntime_gpu(use_uv=use_uv, ignore_ort_install=True)
        self.env_check.check_numpy(use_uv=use_uv)

    def install(
        self,
        device_type: Literal["cuda", "rocm", "xpu", "cpu"] = "cuda",
        use_uv: bool | None = True,
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list | None = None,
        huggingface_mirror: str | None = None,
        pytorch_mirror_dict: dict[str, str] | None = None,
        model_list: list[str] | None = None,
        check_avaliable_gpu: bool | None = False,
        enable_tcmalloc: bool | None = True,
        enable_cuda_malloc: bool | None = True,
        *args,
        **kwargs,
    ) -> None:
        """安装 InvokeAI

        :param device_type`(Literal["cuda","rocm","xpu","cpu"])`: 显卡设备类型
        :param use_uv`(bool|None)`: 使用 uv 替代 Pip 进行 Python 软件包的安装
        :param pypi_index_mirror`(str|None)`: PyPI Index 镜像源链接
        :param pypi_extra_index_mirror`(str|None)`: PyPI Extra Index 镜像源链接
        :param pypi_find_links_mirror`(str|None)`: PyPI Find Links 镜像源链接
        :param github_mirror`(str|list|None)`: Github 镜像源链接或者镜像源链接列表
        :param huggingface_mirror`(str|None)`: HuggingFace 镜像源链接
        :param pytorch_mirror_dict`(dict[str,str]|None)`: PyTorch 镜像源字典, 需包含不同镜像源对应的 PyTorch 镜像源链接
        :param model_list`(list[str])`: 模型下载列表
        :param check_avaliable_gpu`(bool|None)`: 是否检查可用的 GPU, 当检查时没有可用 GPU 将引发`Exception`
        :param enable_tcmalloc`(bool|None)`: 是否启用 TCMalloc 内存优化
        :param enable_cuda_malloc`(bool|None)`: 启用 CUDA 显存优化
        """
        self.utils.warning_unexpected_params(
            message="InvokeAIManager.install() 接收到不期望参数, 请检查参数输入是否正确",
            args=args,
            kwargs=kwargs,
        )
        logger.info("开始安装 InvokeAI")
        os.chdir(self.workspace)
        if check_avaliable_gpu and not self.utils.check_gpu():
            raise Exception(
                "没有可用的 GPU, 请在 Colab -> 代码执行程序 > 更改运行时类型 -> 硬件加速器 选择 GPU T4\n如果不能使用 GPU, 请尝试更换账号!"
            )
        self.mirror.set_mirror(
            pypi_index_mirror=pypi_index_mirror,
            pypi_extra_index_mirror=pypi_extra_index_mirror,
            pypi_find_links_mirror=pypi_find_links_mirror,
            github_mirror=github_mirror,
            huggingface_mirror=huggingface_mirror,
        )
        self.mirror.configure_pip()
        self.env.install_manager_depend(use_uv)
        if pytorch_mirror_dict is not None:
            self.component.update_pytorch_mirror_dict(pytorch_mirror_dict)
        self.component.install_invokeai(
            device_type=device_type,
            upgrade=True,
            use_uv=use_uv,
        )
        if model_list is not None:
            self.get_sd_model_from_list(model_list=model_list)
        if enable_tcmalloc:
            self.tcmalloc_colab()
        if enable_cuda_malloc:
            self.cuda_malloc.set_cuda_malloc()
        logger.info("InvokeAI 安装完成")


class SDTrainerManager(BaseManager):
    """SD Trainer 管理工具"""

    def mount_drive(
        self,
        extras: list[dict[str, str | bool]] = None,
    ) -> None:
        """挂载 Google Drive 并创建 SD Trainer 输出文件夹

        :param extras`(list[dict[str,str|bool]])`: 挂载额外目录

        :notes
            挂载额外目录需要使用`link_dir`指定要挂载的路径, 并且使用相对路径指定

            相对路径的起始位置为`{self.workspace}/{self.workfolder}`

            若额外链接路径为文件, 需指定`is_file`属性为`True`

            例如:
            ```python
            extras = [
                {"link_dir": "models/loras"},
                {"link_dir": "custom_nodes"},
                {"link_dir": "extra_model_paths.yaml", "is_file": True},
            ]

            ```
            默认挂载的目录和文件: `outputs`, `output`, `config`, `train`, `logs`
        """
        drive_path = Path("/content/drive")
        if not (drive_path / "MyDrive").exists():
            if not self.utils.mount_google_drive(drive_path):
                raise Exception("挂载 Google Drive 失败, 请尝试重新挂载 Google Drive")

        drive_output = drive_path / "MyDrive" / "sd_trainer_output"
        sd_trainer_path = self.workspace / self.workfolder
        drive_sd_trainer_outputs_path = drive_output / "outputs"
        sd_trainer_outputs_path = sd_trainer_path / "outputs"
        drive_sd_trainer_output_path = drive_output / "output"
        sd_trainer_output_path = sd_trainer_path / "output"
        drive_sd_trainer_config_path = drive_output / "config"
        sd_trainer_config_path = sd_trainer_path / "config"
        drive_sd_trainer_train_path = drive_output / "train"
        sd_trainer_train_path = sd_trainer_path / "train"
        drive_sd_trainer_logs_path = drive_output / "logs"
        sd_trainer_logs_path = sd_trainer_path / "logs"
        self.utils.sync_files_and_create_symlink(
            src_path=drive_sd_trainer_outputs_path,
            link_path=sd_trainer_outputs_path,
        )
        self.utils.sync_files_and_create_symlink(
            src_path=drive_sd_trainer_output_path,
            link_path=sd_trainer_output_path,
        )
        self.utils.sync_files_and_create_symlink(
            src_path=drive_sd_trainer_config_path,
            link_path=sd_trainer_config_path,
        )
        self.utils.sync_files_and_create_symlink(
            src_path=drive_sd_trainer_train_path,
            link_path=sd_trainer_train_path,
        )
        self.utils.sync_files_and_create_symlink(
            src_path=drive_sd_trainer_logs_path,
            link_path=sd_trainer_logs_path,
        )
        if extras is None:
            return
        for extra in extras:
            link_dir = extra.get("link_dir")
            is_file = extra.get("is_file", False)
            if link_dir is None:
                continue
            full_link_path = sd_trainer_path / link_dir
            full_drive_path = drive_output / link_dir
            if is_file and (
                not full_link_path.exists() and not full_drive_path.exists()
            ):
                # 链接路径指定的是文件并且源文件和链接文件都不存在时则取消链接
                continue
            self.utils.sync_files_and_create_symlink(
                src_path=full_drive_path,
                link_path=full_link_path,
                src_is_file=is_file,
            )

    def get_sd_model(
        self,
        url: str,
        filename: str = None,
    ) -> Path | None:
        """下载模型

        :param url`(str)`: 模型的下载链接
        :param filename`(str|None)`: 模型下载后保存的名称
        :return `Path|None`: 模型保存路径
        """
        path = self.workspace / self.workfolder / "sd-models"
        return self.get_model(url=url, path=path, filename=filename, tool="aria2")

    def get_sd_model_from_list(
        self,
        model_list: list[dict[str]],
    ) -> None:
        """从模型列表下载模型

        :param model_list`(list[str|int])`: 模型列表

        :notes
            `model_list`需要指定`url`(模型下载链接), 可选参数为`filename`(模型保存名称), 例如
            ```python
            model_list = [
                {"url": "url1", "type": "checkpoints"},
                {"url": "url2", "filename": "file.safetensors"},
                {"url": "url4"},
            ]
            ```
        """
        for model in model_list:
            url = model.get("url")
            filename = model.get("filename")
            self.get_sd_model(url=url, filename=filename)

    def check_protobuf(
        self,
        use_uv: bool | None = True,
    ) -> None:
        """检查 protobuf 版本问题

        :param use_uv`(bool|None)`: 使用 uv 安装依赖
        """
        logger.info("检查 protobuf 版本问题中")
        try:
            ver = importlib.metadata.version("protobuf")
            if not self.env_check.is_v1_eq_v2(ver, "3.20.0"):
                logger.info("重新安装 protobuf 中")
                self.env.pip_install("protobuf==3.20.0", use_uv=use_uv)
                logger.info("重新安装 protobuf 成功")
                return
            logger.info("protobuf 检查完成")
        except Exception as e:
            traceback.print_exc()
            logger.error("检查 protobuf 时发送错误: %s", e)

    def check_env(
        self,
        use_uv: bool | None = True,
        requirements_file: str | None = "requirements.txt",
    ) -> None:
        """检查 SD Trainer 运行环境

        :param use_uv`(bool|None)`: 使用 uv 安装依赖
        :param requirements_file`(str|None)`: 依赖文件名
        """
        sd_trainer_path = self.workspace / self.workfolder
        requirement_path = sd_trainer_path / requirements_file
        self.env_check.check_env(
            requirement_path=requirement_path, name="SD Trainer", use_uv=use_uv
        )
        self.env_check.fix_torch()
        self.ort_check.check_onnxruntime_gpu(use_uv=use_uv, ignore_ort_install=False)
        self.check_protobuf(use_uv=use_uv)
        self.env_check.check_numpy(use_uv=use_uv)

    def install(
        self,
        torch_ver: str | list | None = None,
        xformers_ver: str | list | None = None,
        use_uv: bool | None = True,
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list | None = None,
        huggingface_mirror: str | None = None,
        pytorch_mirror: str | None = None,
        sd_trainer_repo: str | None = None,
        sd_trainer_requirements: str | None = None,
        model_list: list[dict[str, str]] | None = None,
        check_avaliable_gpu: bool | None = False,
        enable_tcmalloc: bool | None = True,
        enable_cuda_malloc: bool | None = True,
        *args,
        **kwargs,
    ) -> None:
        """安装 SD Trainer

        :param torch_ver`(str|None)`: 指定的 PyTorch 软件包包名, 并包括版本号
        :param xformers_ver`(str|None)`: 指定的 xFormers 软件包包名, 并包括版本号
        :param use_uv`(bool|None)`: 使用 uv 替代 Pip 进行 Python 软件包的安装
        :param pypi_index_mirror`(str|None)`: PyPI Index 镜像源链接
        :param pypi_extra_index_mirror`(str|None)`: PyPI Extra Index 镜像源链接
        :param pypi_find_links_mirror`(str|None)`: PyPI Find Links 镜像源链接
        :param github_mirror`(str|list|None)`: Github 镜像源链接或者镜像源链接列表
        :param huggingface_mirror`(str|None)`: HuggingFace 镜像源链接
        :param pytorch_mirror`(str|None)`: PyTorch 镜像源链接
        :param sd_trainer_repo`(str|None)`: SD Trainer 仓库地址
        :param sd_trainer_requirements`(str|None)`: SD Trainer 依赖文件名
        :param model_list`(list[dict[str,str]])`: 模型下载列表
        :param check_avaliable_gpu`(bool|None)`: 是否检查可用的 GPU, 当检查时没有可用 GPU 将引发`Exception`
        :param enable_tcmalloc`(bool|None)`: 是否启用 TCMalloc 内存优化
        :param enable_cuda_malloc`(bool|None)`: 启用 CUDA 显存优化
        """
        self.utils.warning_unexpected_params(
            message="SDTrainerManager.install() 接收到不期望参数, 请检查参数输入是否正确",
            args=args,
            kwargs=kwargs,
        )
        logger.info("开始安装 SD Trainer")
        os.chdir(self.workspace)
        comfyui_path = self.workspace / self.workfolder
        sd_trainer_repo = (
            "https://github.com/Akegarasu/lora-scripts"
            if sd_trainer_repo is None
            else sd_trainer_repo
        )
        requirements_path = comfyui_path / (
            "requirements.txt"
            if sd_trainer_requirements is None
            else sd_trainer_requirements
        )
        if check_avaliable_gpu and not self.utils.check_gpu():
            raise Exception(
                "没有可用的 GPU, 请在 Colab -> 代码执行程序 > 更改运行时类型 -> 硬件加速器 选择 GPU T4\n如果不能使用 GPU, 请尝试更换账号!"
            )
        self.mirror.set_mirror(
            pypi_index_mirror=pypi_index_mirror,
            pypi_extra_index_mirror=pypi_extra_index_mirror,
            pypi_find_links_mirror=pypi_find_links_mirror,
            github_mirror=github_mirror,
            huggingface_mirror=huggingface_mirror,
        )
        self.mirror.configure_pip()
        self.env.install_manager_depend(use_uv)
        self.git.clone(sd_trainer_repo, comfyui_path)
        self.git.update(comfyui_path)
        self.env.install_pytorch(
            torch_package=torch_ver,
            xformers_package=xformers_ver,
            pytorch_mirror=pytorch_mirror,
            use_uv=use_uv,
        )
        os.chdir(comfyui_path)
        self.env.install_requirements(requirements_path, use_uv)
        os.chdir(self.workspace)
        if model_list is not None:
            self.get_sd_model_from_list(model_list)
        if enable_tcmalloc:
            self.tcmalloc_colab()
        if enable_cuda_malloc:
            self.cuda_malloc.set_cuda_malloc()
        logger.info("SD Trainer 安装完成")
