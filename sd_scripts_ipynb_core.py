"""
SD Scripts 环境管理模块, 可用于 Jupyter Notebook
"""
import os
import re
import sys
import stat
import copy
import json
import time
import shlex
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
from pathlib import Path
from urllib.parse import urlparse
from tempfile import TemporaryDirectory
from typing import Callable, Literal, Any


VERSION = "1.0.9"


class LoggingColoredFormatter(logging.Formatter):
    """Logging 格式化类"""
    COLORS = {
        "DEBUG": "\033[0;36m",          # CYAN
        "INFO": "\033[0;32m",           # GREEN
        "WARNING": "\033[0;33m",        # YELLOW
        "ERROR": "\033[0;31m",          # RED
        "CRITICAL": "\033[0;37;41m",    # WHITE ON RED
        "RESET": "\033[0m",             # RESET COLOR
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
    name: str | None = None,
    level: int | None = logging.INFO,
    color: bool | None = True
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
                r"[%(name)s]-|%(asctime)s|-%(levelname)s: %(message)s", r"%Y-%m-%d %H:%M:%S",
                color=color
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
    custom_env: list | None = None,
    live: bool | None = True,
    shell: bool | None = None
) -> str | None:
    """执行 Shell 命令

    :param command`(str|list)`: 要执行的命令
    :param desc`(str|None)`: 执行命令的描述
    :param errdesc`(str|None)`: 执行命令报错时的描述
    :param custom_env`(str|None)`: 自定义环境变量
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

    result: subprocess.CompletedProcess = subprocess.run(
        command_str,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=shell,
        env=custom_env
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

        path = Path(path) if not isinstance(
            path, Path) and path is not None else path

        try:
            logger.info("下载 %s 到 %s 中", repo, path)
            run_cmd(["git", "clone", "--recurse-submodules", repo, str(path)])
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
        path = Path(path) if not isinstance(
            path, Path) and path is not None else path
        use_submodule = []
        try:
            logger.info("拉取 %s 更新中", path)
            if GitWarpper.check_point_offset(path):
                if GitWarpper.fix_point_offset(path):
                    logger.error("更新 %s 失败", path)
                    return False

            if len(run_cmd(["git", "-C", str(path), "submodule", "status"], live=False).strip()) != 0:
                use_submodule = ["--recurse-submodules"]
                run_cmd(["git", "-C", str(path), "submodule", "init"])

            run_cmd(["git", "-C", str(path), "fetch", "--all"] + use_submodule)
            branch = GitWarpper.get_current_branch(path)
            ref = run_cmd(["git", "-C", str(path), "symbolic-ref",
                          "--quiet", "HEAD"], live=False)

            if GitWarpper.check_repo_on_origin_remote(path):
                origin_branch = f"origin/{branch}"
            else:
                origin_branch = str.replace(ref, "refs/heads/", "", 1)
                try:
                    _ = run_cmd(["git", "-C", str(path), "config", "--get",
                                f"branch.{origin_branch}.remote"], live=False)
                    origin_branch = run_cmd(
                        ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "{}@{upstream}".format(origin_branch)], live=False)
                except Exception as _:
                    pass
            run_cmd(["git", "-C", str(path), "reset",
                    "--hard", origin_branch] + use_submodule)
            logger.info("更新 %s 完成", path)
            return True
        except Exception as e:
            logger.error("更新 %s 时发生错误: %s", str(path), e)
            return False

    @staticmethod
    def check_point_offset(path: Path | str) -> bool:
        """检查 Git 仓库的指针是否游离

        :param path`(Path|str)`: Git 仓库路径
        :return `bool`: 当 Git 指针游离时返回`True`
        """
        path = Path(path) if not isinstance(
            path, Path) and path is not None else path
        try:
            _ = run_cmd(["git", "-C", str(path),
                        "symbolic-ref", "HEAD"], live=False)
            return False
        except Exception as _:
            return True

    @staticmethod
    def fix_point_offset(path: Path | str) -> bool:
        """修复 Git 仓库的 Git 指针游离

        :param path`(Path|str)`: Git 仓库路径
        :return `bool`: 修复结果
        """
        path = Path(path) if not isinstance(
            path, Path) and path is not None else path
        try:
            logger.info("修复 %s 的 Git 指针游离中", path)
            # run_cmd(["git", "-C", str(path), "remote", "prune", "origin"])
            run_cmd(["git", "-C", str(path), "submodule", "init"])
            branch_info = run_cmd(
                ["git", "-C", str(path), "branch", "-a"], live=False)
            main_branch = None
            for info in branch_info.split("\n"):
                if "/HEAD" in info:
                    main_branch = info.split(
                        " -> ").pop().strip().split("/").pop()
                    break
            if main_branch is None:
                logger.error("未找到 %s 主分支, 无法修复 Git 指针游离", path)
                return False
            logger.info("%s 主分支: %s", str(path), main_branch)
            run_cmd(["git", "-C", str(path), "checkout", main_branch])
            run_cmd(["git", "-C", str(path), "reset",
                    "--recurse-submodules", "--hard", f"origin/{main_branch}"])
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
        path = Path(path) if not isinstance(
            path, Path) and path is not None else path
        try:
            return run_cmd(["git", "-C", str(path), "branch", "--show-current"], live=False).strip()
        except Exception as e:
            logger.error("获取 %s 当前分支失败: %s", path, e)
            return None

    @staticmethod
    def check_repo_on_origin_remote(path: Path | str) -> bool:
        """检查 Git 仓库的远程源是否在 origin

        :param path`(Path|str)`: Git 仓库路径
        :return `bool`: 远程源在 origin 时返回`True`
        """
        path = Path(path) if not isinstance(
            path, Path) and path is not None else path
        try:
            current_branch = GitWarpper.get_current_branch(path)
            _ = run_cmd(["git", "-C", str(path), "show-ref", "--verify",
                        "--quiet", f"refs/remotes/origin/{current_branch}"], live=False)
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
        path = Path(path) if not isinstance(
            path, Path) and path is not None else path
        try:
            _ = run_cmd(["git", "-C", str(path), "show-ref", "--verify",
                        "--quiet", f"refs/heads/{branch}"], live=False)
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
        path = Path(path) if not isinstance(
            path, Path) and path is not None else path
        custom_env = os.environ.copy()
        custom_env.pop("GIT_CONFIG_GLOBAL", None)
        try:
            current_url = run_cmd(
                ["git", "-C", str(path), "remote", "get-url", "origin"], custom_env=custom_env, live=False)
        except Exception as e:
            current_url = "None"
            logger.warning("获取 %s 原有的远程源失败: %s", path, e)

        use_submodules = ["--recurse-submodules"] if recurse_submodules else []
        if new_url is not None:
            logger.info("替换 %s 远程源: %s -> %s", path, current_url, new_url)
            try:
                run_cmd(["git", "-C", str(path), "remote",
                        "set-url", "origin", new_url])
            except Exception as e:
                logger.error("替换 %s 远程源失败: %s", path, e)
                return False

        if recurse_submodules:
            try:
                run_cmd(["git", "-C", str(path), "submodule",
                        "update", "--init", "--recursive"])
            except Exception as e:
                logger.warning("更新 %s 的 Git 子模块信息发生错误: %s", path, e)
        else:
            try:
                run_cmd(["git", "-C", str(path), "submodule",
                        "deinit", "--all", "-f"])
            except Exception as e:
                logger.warning("更新 %s 的 Git 子模块信息发生错误: %s", path, e)

        logger.info("拉取 %s 远程源更新中", path)
        try:
            run_cmd(["git", "-C", str(path), "fetch"])
            run_cmd(["git", "-C", str(path), "submodule", "deinit", "--all", "-f"])
            if not GitWarpper.check_local_branch_exists(path, branch):
                run_cmd(["git", "-C", str(path), "branch", branch])

            run_cmd(["git", "-C", str(path), "checkout", branch, "--force"])
            logger.info("应用 %s 的远程源最新内容中", path)
            if recurse_submodules:
                run_cmd(["git", "-C", str(path), "reset",
                        "--hard", f"origin/{branch}"])
                run_cmd(["git", "-C", str(path), "submodule",
                        "deinit", "--all", "-f"])
                run_cmd(["git", "-C", str(path), "submodule",
                        "update", "--init", "--recursive"])

            run_cmd(["git", "-C", str(path), "reset", "--hard",
                    f"origin/{branch}"] + use_submodules)
            logger.info("切换 %s 分支到 %s 完成", path, branch)
            return True
        except Exception as e:
            logger.error("切换 %s 分支到 %s 失败: %s", path, branch, e)
            logger.warning("回退分支切换")
            try:
                run_cmd(["git", "-C", str(path), "remote",
                        "set-url", "origin", current_url])
                if recurse_submodules:
                    run_cmd(["git", "-C", str(path), "submodule",
                            "deinit", "--all", "-f"])

                else:
                    run_cmd(["git", "-C", str(path), "submodule",
                            "update", "--init", "--recursive"])
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
        path = Path(path) if not isinstance(
            path, Path) and path is not None else path
        logger.info("切换 %s 的 Git 指针到 %s 版本", path, commit)
        try:
            run_cmd(["git", "-C", str(path), "reset", "--hard", commit])
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
        path = Path(path) if not isinstance(
            path, Path) and path is not None else path
        try:
            _ = run_cmd(["git", "-C", str(path), "rev-parse",
                        "--git-dir"], live=False)
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

        path = Path(path) if not isinstance(
            path, Path) and path is not None else path
        if save_name is None:
            parts = urlparse(url)
            save_name = os.path.basename(parts.path)

        save_path = path / save_name
        try:
            logger.info("下载 %s 到 %s 中", os.path.basename(url), save_path)
            run_cmd(["aria2c", "--console-log-level=error", "-c", "-x", "16",
                    "-s", "16", "-k", "1M", url, "-d", str(path), "-o", save_name])
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

        model_dir = Path(model_dir) if not isinstance(
            model_dir, Path) and model_dir is not None else model_dir

        if not file_name:
            parts = urlparse(url)
            file_name = os.path.basename(parts.path)

        cached_file = model_dir.resolve() / file_name

        if re_download or not cached_file.exists():
            model_dir.mkdir(exist_ok=True)
            temp_file = model_dir / f"{file_name}.tmp"
            logger.info("下载 %s 到 %s 中", file_name, cached_file)
            response = requests.get(url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            with tqdm(total=total_size, unit="B", unit_scale=True, desc=file_name, disable=not progress) as progress_bar:
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
        tools: Literal["aria2", "request"] = "aria2",
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
                if tools == "aria2":
                    output = Downloader.aria2(
                        url=url,
                        path=path,
                        save_name=save_name,
                    )
                    if output is None:
                        continue
                    return output
                elif tools == "request":
                    output = Downloader.load_file_from_url(
                        url=url,
                        model_dir=path,
                        file_name=save_name,
                    )
                    if output is None:
                        continue
                    return output
                else:
                    logger.error("未知下载工具: %s", tools)
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
    ) -> str:
        """使用 Pip / uv 安装 Python 软件包

        :param *args`(Any)`: 要安装的 Python 软件包 (可使用 Pip / uv 命令行参数, 如`--upgrade`, `--force-reinstall`)
        :param use_uv`(bool|None)`: 使用 uv 代替 Pip 进行安装, 当 uv 安装 Python 软件包失败时, 将回退到 Pip 进行重试
        :return `str`: 命令的执行输出
        :raises RuntimeError: 当 uv 和 pip 都无法安装软件包时抛出异常
        """
        if use_uv:
            try:
                _ = run_cmd(["uv", "--version"], live=False)
            except Exception as _:
                logger.info("安装 uv 中")
                run_cmd([sys.executable, "-m", "pip", "install", "uv"])

            try:
                return run_cmd(["uv", "pip", "install", *args])
            except Exception as e:
                logger.warning(
                    "检测到 uv 安装 Python 软件包失败, 尝试回退到 Pip 重试 Python 软件包安装: %s", e)
                return run_cmd([sys.executable, "-m", "pip", "install", *args])
        else:
            return run_cmd([sys.executable, "-m", "pip", "install", *args])

    @staticmethod
    def install_manager_depend(use_uv: bool | None = True) -> bool:
        """安装自身组件依赖

        :param use_uv`(bool|None)`: 使用 uv 代替 Pip 进行安装, 当 uv 安装 Python 软件包失败时, 将回退到 Pip 进行重试
        :return `bool`: 组件安装结果
        """
        try:
            logger.info("安装自身组件依赖中")
            EnvManager.pip_install("uv", "--upgrade", use_uv=False)
            EnvManager.pip_install(
                "modelscope", "huggingface_hub", "requests", "tqdm", "wandb", "--upgrade", use_uv=use_uv)
            run_cmd(["apt", "update"])
            run_cmd(["apt", "install", "aria2", "google-perftools",
                    "p7zip-full", "unzip", "tree", "git", "git-lfs", "-y"])
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
            torch_package = torch_package.split() if isinstance(
                torch_package, str) else torch_package
            try:
                EnvManager.pip_install(*torch_package, use_uv=use_uv)
                logger.info("安装 PyTorch 成功")
            except Exception as e:
                logger.error("安装 PyTorch 时发生错误: %s", e)
                return False

        if xformers_package is not None:
            logger.info("安装 xFormers 中")
            xformers_package = xformers_package.split() if isinstance(
                xformers_package, str) else xformers_package
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
    ) -> bool:
        """从 requirements.txt 文件指定安装的依赖

        :param path`(Path|str)`: requirements.txt 文件路径
        :param use_uv`(bool|None)`: 是否使用 uv 代替 Pip 进行安装
        :return `bool`: 安装依赖成功时返回`True`
        """
        path = Path(path) if not isinstance(
            path, Path) and path is not None else path

        try:
            logger.info("从 %s 安装 Python 软件包中", path)
            EnvManager.pip_install("-r", str(path), use_uv=use_uv)
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
    def get_file_list(path: Path | str) -> list[Path]:
        """获取当前路径下的所有文件的绝对路径

        :param path`(Path|str)`: 要获取文件列表的目录
        :return `list[Path]`: 文件列表的绝对路径
        """
        path = Path(path) if not isinstance(
            path, Path) and path is not None else path

        if not path.exists():
            return []

        return [
            p.absolute()
            for p in path.rglob("*")
            if p.is_file()
        ]

    @staticmethod
    def config_wandb_token(token: str | None = None) -> None:
        """配置 WandB 所需 Token"""
        if token is not None:
            logger.info("配置 WandB Token")
            os.environ["WANDB_API_KEY"] = token

    @staticmethod
    def download_archive_and_unpack(
        url: str,
        local_dir: Path | str,
        name: str | None = None,
        retry: int | None = 3
    ) -> Path | None:
        """下载压缩包并解压到指定路径

        :param url`(str)`: 压缩包下载链接, 压缩包只支持`zip`,`7z`,`tar`格式
        :param local_dir`(Path|str)`: 下载路径
        :param name`(str|None)`: 下载文件保存的名称, 为`None`时从`url`解析文件名
        :param retry`(int|None)`: 重试下载的次数
        :return `Path|None`: 下载成功并解压成功时返回路径
        """
        path = Path("/tmp")
        if name is None:
            parts = urlparse(url)
            name = os.path.basename(parts.path)

        archive_format = Path(name).suffix  # 压缩包格式
        origin_file_path = Downloader.download_file(  # 下载文件
            url=url,
            path=path,
            save_name=name,
            tools="aria2",
            retry=retry
        )

        if origin_file_path is not None:
            # 解压文件
            logger.info("解压 %s 到 %s 中", name, local_dir)
            try:
                if archive_format == ".7z":
                    run_cmd(
                        ["7z", "x", str(origin_file_path), f"-o{local_dir}"])
                    logger.info("%s 解压完成, 路径: %s", name, local_dir)
                    return local_dir
                elif archive_format == ".zip":
                    run_cmd(["unzip", str(origin_file_path),
                            "-d", str(local_dir)])
                    logger.info("%s 解压完成, 路径: %s", name, local_dir)
                    return local_dir
                elif archive_format == ".tar":
                    run_cmd(["tar", "-xvf", str(origin_file_path),
                            "-C", str(local_dir)])
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
                ["ldd", "--version"], capture_output=True, text=True)
            libc_ver_line = result.stdout.split('\n')[0]
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
        tcmalloc_libs = [
            r"libtcmalloc(_minimal|)\.so\.\d+", r"libtcmalloc\.so\.\d+"]

        # 遍历数组
        for lib_pattern in tcmalloc_libs:
            try:
                # 获取系统库缓存信息
                result = subprocess.run(["ldconfig", "-p"], capture_output=True, text=True,
                                        env=dict(os.environ, PATH="/usr/sbin:" + os.getenv("PATH")))
                libraries = result.stdout.split("\n")

                # 查找匹配的 TCMalloc 库
                for lib in libraries:
                    if re.search(lib_pattern, lib):
                        # 解析库信息
                        match = re.search(r"(.+?)\s+=>\s+(.+)", lib)
                        if match:
                            lib_name, lib_path = match.group(
                                1).strip(), match.group(2).strip()
                            logger.info("检查 TCMalloc: %s => %s",
                                        lib_name, lib_path)

                            # 确定库是否链接到 libpthread 和解析未定义符号: pthread_key_create
                            if Utils.compare_versions(libc_ver, libc_v234) < 0:
                                # glibc < 2.34，pthread_key_create 在 libpthread.so 中。检查链接到 libpthread.so
                                ldd_result = subprocess.run(
                                    ["ldd", lib_path], capture_output=True, text=True)
                                if "libpthread" in ldd_result.stdout:
                                    logger.info(
                                        "%s 链接到 libpthread, 执行 LD_PRELOAD=%s", lib_name, lib_path)
                                    # 设置完整路径 LD_PRELOAD
                                    if "LD_PRELOAD" in os.environ and os.environ["LD_PRELOAD"]:
                                        os.environ["LD_PRELOAD"] = os.environ["LD_PRELOAD"] + \
                                            ":" + lib_path
                                    else:
                                        os.environ["LD_PRELOAD"] = lib_path
                                    return True
                                else:
                                    logger.info(
                                        "%s 没有链接到 libpthread, 将触发未定义符号: pthread_Key_create 错误", lib_name)
                            else:
                                # libc.so (glibc) 的 2.34 版本已将 pthread 库集成到 glibc 内部
                                logger.info(
                                    "%s 链接到 libc.so, 执行 LD_PRELOAD=%s", lib_name, lib_path)
                                # 设置完整路径 LD_PRELOAD
                                if "LD_PRELOAD" in os.environ and os.environ["LD_PRELOAD"]:
                                    os.environ["LD_PRELOAD"] = os.environ["LD_PRELOAD"] + \
                                        ":" + lib_path
                                else:
                                    os.environ["LD_PRELOAD"] = lib_path
                                return True
            except Exception as e:
                logger.error("检查 TCMalloc 库时出错: %s", e)
                continue

        if "LD_PRELOAD" not in os.environ:
            print("无法定位 TCMalloc。未在系统上找到 tcmalloc 或 google-perftool, 取消加载内存优化")
            return False

    @staticmethod
    def compare_versions(version1: str, version2: str) -> int:
        """对比两个版本号大小

        :param version1(str): 第一个版本号
        :param version2(str): 第二个版本号
        :return int: 版本对比结果, 1 为第一个版本号大, -1 为第二个版本号大, 0 为两个版本号一样
        """
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
            num1 = int(nums1[i]) if i < len(
                nums1) else 0  # 如果版本号 1 的位数不够, 则补 0
            num2 = int(nums2[i]) if i < len(
                nums2) else 0  # 如果版本号 2 的位数不够, 则补 0

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
        path = Path(path) if not isinstance(
            path, Path) and path is not None else path
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
        self.total_tasks = max(len(download_args_list or []), len(
            download_kwargs_list or []))  # 记录总的下载任务数 (以参数列表长度为准)
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
                    logger.error("[%s/%s] 执行 %s 时发生错误: %s", count,
                                 self.retry, self.download_func, e)
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
                seconds=estimated_remaining_time_seconds)
            estimated_hours = estimated_remaining_time.seconds // 3600
            estimated_minutes = (estimated_remaining_time.seconds // 60) % 60
            estimated_seconds = estimated_remaining_time.seconds % 60
            formatted_estimated_time = f"{estimated_hours:02}:{estimated_minutes:02}:{estimated_seconds:02}"
        else:
            formatted_estimated_time = "N/A"

        logger.info(
            "下载进度: %.2f%% | %d/%d [%s<%s, %.2f it/s]",
            progress, self.completed_count, self.total_tasks, formatted_time, formatted_estimated_time, speed)

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
        max_tasks = max(len(self.download_args_list),
                        len(self.download_kwargs_list))

        # 将下载任务添加到队列
        for i in range(max_tasks):
            # 获取位置参数
            args = self.download_args_list[i] if i < len(
                self.download_args_list) else []

            # 获取关键字参数
            kwargs = self.download_kwargs_list[i] if i < len(
                self.download_kwargs_list) else {}

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
            logger.info("获取 HuggingFace 仓库 %s (类型: %s) 的文件列表",
                        repo_id, repo_type)
            return self.get_hf_repo_files(repo_id, repo_type, retry)
        if api_type == "modelscope":
            logger.info("获取 ModelScope 仓库 %s (类型: %s}) 的文件列表",
                        repo_id, repo_type)
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
                logger.error("[%s/%s] 获取 %s (类型: %s) 仓库的文件列表出现错误: %s", count, retry,
                             repo_id, repo_type, e)
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
        """ 获取 ModelScope 仓库文件列表

        :param repo_id`(str)`: ModelScope 仓库 ID
        :param repo_type`(str)`: ModelScope 仓库类型
        :param retry`(int|None)`: 重试次数
        :return `list[str]`: 仓库文件列表
        """
        file_list = []
        count = 0

        def _get_file_path(repo_files: list) -> list[str]:
            """获取 ModelScope Api 返回的仓库列表中的模型路径"""
            return [
                file["Path"]
                for file in repo_files
                if file["Type"] != "tree"
            ]

        if repo_type == "model":
            while count < retry:
                count += 1
                try:
                    repo_files = self.ms_api.get_model_files(
                        model_id=repo_id,
                        recursive=True
                    )
                    file_list = _get_file_path(repo_files)
                    break
                except Exception as e:
                    traceback.print_exc()
                    logger.error("[%s/%s] 获取 %s (类型: %s) 仓库的文件列表出现错误: %s", count, retry,
                                 repo_id, repo_type, e)
                    if count < retry:
                        logger.warning("[%s/%s] 重试获取文件列表中", count, retry)
        elif repo_type == "dataset":
            while count < retry:
                count += 1
                try:
                    repo_files = self.ms_api.get_dataset_files(
                        repo_id=repo_id,
                        recursive=True
                    )
                    file_list = _get_file_path(repo_files)
                    break
                except Exception as e:
                    traceback.print_exc()
                    logger.error("[%s/%s] 获取 %s (类型: %s) 仓库的文件列表出现错误: %s", count, retry,
                                 repo_id, repo_type, e)
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
                if not self.hf_api.repo_exists(
                    repo_id=repo_id,
                    repo_type=repo_type
                ):
                    self.hf_api.create_repo(
                        repo_id=repo_id,
                        repo_type=repo_type,
                        private=visibility
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
                        visibility=Visibility.PUBLIC if visibility else Visibility.PRIVATE,
                        token=self.ms_token
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

        upload_path = Path(upload_path) if not isinstance(
            upload_path, Path) and upload_path is not None else upload_path

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
        repo_files = self.get_repo_file(
            api_type="huggingface",
            repo_id=repo_id,
            repo_type=repo_type,
            retry=retry,
        )
        logger.info("上传到 HuggingFace 仓库: %s -> HuggingFace/%s",
                    upload_path, repo_id)
        files_count = len(upload_files)
        count = 0
        for upload_file in upload_files:
            count += 1
            upload_file_rel_path = upload_file.relative_to(
                upload_path).as_posix()
            if upload_file_rel_path in repo_files:
                logger.info("[%s/%s] %s 已存在于 HuggingFace 仓库中, 跳过上传",
                            count, files_count, upload_file)
                continue

            logger.info("[%s/%s] 上传 %s 到 %s (类型: %s) 仓库中", count,
                        files_count, upload_file, repo_id, repo_type)
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
                    logger.error("[%s/%s] 上传 %s 时发生错误: %s", count,
                                 files_count, upload_file.name, e)
                    traceback.print_exc()
                    if retry_num < retry:
                        logger.warning("[%s/%s] 重试上传 %s", count,
                                       files_count, upload_file.name)

        logger.info("[%s/%s] 上传 %s 到 %s (类型: %s) 完成", count,
                    files_count, upload_path, repo_id, repo_type)

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
        repo_files = self.get_repo_file(
            api_type="modelscope",
            repo_id=repo_id,
            repo_type=repo_type,
            retry=retry,
        )
        logger.info("上传到 ModelScope 仓库: %s -> ModelScope/%s",
                    upload_path, repo_id)
        files_count = len(upload_files)
        count = 0
        for upload_file in upload_files:
            count += 1
            upload_file_rel_path = upload_file.relative_to(
                upload_path).as_posix()
            if upload_file_rel_path in repo_files:
                logger.info("[%s/%s] %s 已存在于 ModelScope 仓库中, 跳过上传",
                            count, files_count, upload_file)
                continue

            logger.info("[%s/%s] 上传 %s 到 %s (类型: %s) 仓库中", count,
                        files_count, upload_file, repo_id, repo_type)
            retry_num = 0
            while retry_num < retry:
                try:
                    self.ms_api.upload_file(
                        repo_id=repo_id,
                        repo_type=repo_type,
                        path_in_repo=upload_file_rel_path,
                        path_or_fileobj=upload_file,
                        commit_message=f"Upload {upload_file.name}",
                        token=self.ms_token
                    )
                    break
                except Exception as e:
                    logger.error("[%s/%s] 上传 %s 时发生错误: %s", count,
                                 files_count, upload_file.name, e)
                    traceback.print_exc()
                    if retry_num < retry:
                        logger.warning("[%s/%s] 重试上传 %s", count,
                                       files_count, upload_file.name)

        logger.info("[%s/%s] 上传 %s 到 %s (类型: %s) 完成", count,
                    files_count, upload_path, repo_id, repo_type)

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
        local_dir = Path(local_dir) if not isinstance(
            local_dir, Path) and local_dir is not None else local_dir

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
            download_task.append({
                "repo_id": repo_id,
                "repo_type": repo_type,
                "local_dir": local_dir,
                "filename": repo_file,
            })

        if folder is not None:
            logger.info("指定下载文件: %s", folder)
        logger.info("下载文件数量: %s", len(download_task))

        files_downloader = MultiThreadDownloader(
            download_func=hf_hub_download,
            download_kwargs_list=download_task
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
            download_task.append({
                "repo_id": repo_id,
                "repo_type": repo_type,
                "local_dir": local_dir,
                "allow_patterns": repo_file,
            })

        if folder is not None:
            logger.info("指定下载文件: %s", folder)
        logger.info("下载文件数量: %s", len(download_task))

        files_downloader = MultiThreadDownloader(
            download_func=snapshot_download,
            download_kwargs_list=download_task
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
                "使用 PIP_INDEX_URL, UV_DEFAULT_INDEX 环境变量设置 PyPI Index 镜像源")
            os.environ["PIP_INDEX_URL"] = mirror
            os.environ["UV_DEFAULT_INDEX"] = mirror
        else:
            logger.info(
                "清除 PIP_INDEX_URL, UV_DEFAULT_INDEX 环境变量, 取消使用 PyPI Index 镜像源")
            os.environ.pop("PIP_INDEX_URL", None)
            os.environ.pop("UV_DEFAULT_INDEX", None)

    @staticmethod
    def set_pypi_extra_index_mirror(mirror: str | None = None) -> None:
        """设置 PyPI Extra Index 镜像源

        :param mirror`(str|None)`: PyPI 镜像源链接, 当不传入镜像源链接时则清除镜像源
        """
        import os
        if mirror is not None:
            logger.info(
                "使用 PIP_EXTRA_INDEX_URL, UV_INDEX 环境变量设置 PyPI Extra Index 镜像源")
            os.environ["PIP_EXTRA_INDEX_URL"] = mirror
            os.environ["UV_INDEX"] = mirror
        else:
            logger.info(
                "清除 PIP_EXTRA_INDEX_URL, UV_INDEX 环境变量, 取消使用 PyPI Extra Index 镜像源")
            os.environ.pop("PIP_EXTRA_INDEX_URL", None)
            os.environ.pop("UV_INDEX", None)

    @staticmethod
    def set_pypi_find_links_mirror(mirror: str | None = None) -> None:
        """设置 PyPI Find Links 镜像源

        :param mirror`(str|None)`: PyPI 镜像源链接, 当不传入镜像源链接时则清除镜像源
        """
        if mirror is not None:
            logger.info(
                "使用 PIP_FIND_LINKS, UV_FIND_LINKS 环境变量设置 PyPI Find Links 镜像源")
            os.environ["PIP_FIND_LINKS"] = mirror
            os.environ["UV_FIND_LINKS"] = mirror
        else:
            logger.info(
                "清除 PIP_FIND_LINKS, UV_FIND_LINKS 环境变量, 取消使用 PyPI Find Links 镜像源")
            os.environ.pop("PIP_FIND_LINKS", None)
            os.environ.pop("UV_FIND_LINKS", None)

    @staticmethod
    def set_github_mirror(mirror: str | list | None = None, config_path: Path | str = None) -> None:
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

        config_path = Path(config_path) if not isinstance(
            config_path, Path) and config_path is not None else config_path
        git_config_path = config_path / ".gitconfig"
        os.environ["GIT_CONFIG_GLOBAL"] = str(git_config_path)

        if isinstance(mirror, str):
            logger.info("通过 GIT_CONFIG_GLOBAL 环境变量设置 Github 镜像源")
            try:
                run_cmd(["git", "config", "--global",
                        f"url.{mirror}.insteadOf", "https://github.com"])
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
                    run_cmd(["git", "clone", test_repo, str(
                        mirror_test_path)], custom_env=custon_env, live=False)
                    if mirror_test_path.exists():
                        remove_files(mirror_test_path)
                    run_cmd(["git", "config", "--global",
                            f"url.{gh}.insteadOf", "https://github.com"])
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
        huggingface_mirror: str | None = None
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
        MirrorConfigManager.set_pypi_extra_index_mirror(
            pypi_extra_index_mirror)
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
                share_server_address=None
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
        path = Path(path) if not isinstance(
            path, Path) and path is not None else path
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

        command = ["ssh", "-o", "StrictHostKeyChecking=no",
                   "-i", ssh_path.as_posix()] + launch_args
        command_str = shlex.join(command) if isinstance(
            command, list) else command
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
            for line in iter(tunnel.stdout.readline, ''):
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
            launch_args=["-p", "443",
                         f"-R0:127.0.0.1:{self.port}", "free.pinggy.io"],
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
    ) -> tuple[str]:
        """启动内网穿透

        :param use_ngrok`(bool|None)`: 启用 Ngrok 内网穿透
        :param ngrok_token`(str|None)`: Ngrok 账号 Token
        :param use_cloudflare`(bool|None)`: 启用 CloudFlare 内网穿透
        :param use_remote_moe`(bool|None)`: 启用 remote.moe 内网穿透
        :param use_localhost_run`(bool|None)`: 使用 localhost.run 内网穿透
        :param use_gradio`(bool|None)`: 使用 Gradio 内网穿透
        :param use_pinggy_io`(bool|None)`: 使用 pinggy.io 内网穿透
        :return `tuple[str]`: 内网穿透地址
        """

        if any([
                use_cloudflare,
                use_ngrok and ngrok_token,
                use_remote_moe,
                use_localhost_run,
                use_gradio,
                use_pinggy_io]):
            logger.info("启动内网穿透")
        else:
            return

        cloudflare_url = self.cloudflare() if use_cloudflare else None
        ngrok_url = self.ngrok(
            ngrok_token) if use_ngrok and ngrok_token else None
        remote_moe_url = self.remote_moe() if use_remote_moe else None
        localhost_run_url = self.localhost_run() if use_localhost_run else None
        gradio_url = self.gradio() if use_gradio else None
        pinggy_io_url = self.pinggy_io() if use_pinggy_io else None

        logger.info("http://127.0.0.1:%s 的内网穿透地址", self.port)
        print("==================================================================================")
        print(f":: CloudFlare: {cloudflare_url}")
        print(f":: Ngrok: {ngrok_url}")
        print(f":: remote.moe: {remote_moe_url}")
        print(f":: localhost_run: {localhost_run_url}")
        print(f":: Gradio: {gradio_url}")
        print(f":: pinggy.io: {pinggy_io_url}")
        print("==================================================================================")
        return cloudflare_url, ngrok_url, remote_moe_url, localhost_run_url, gradio_url, pinggy_io_url


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
        self.workspace.mkdir(exist_ok=True)
        self.workfolder = workfolder
        self.git = GitWarpper()
        self.downloader = Downloader()
        self.env = EnvManager()
        self.utils = Utils()
        self.repo = RepoManager(hf_token, ms_token)
        self.mirror = MirrorConfigManager()
        self.tun = TunnelManager(workspace, port)
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
        retry: int | None = 3
    ) -> Path:
        """下载模型文件到本地中

        :param url`(str)`: 模型文件的下载链接
        :param path`(str|Path)`: 模型文件下载到本地的路径
        :param filename`(str)`: 指定下载的模型文件名称
        :param retry`(int)`: 重试下载的次数, 默认为 3
        :return `Path`: 文件保存路径
        """
        if filename is None:
            parts = urlparse(url)
            filename = os.path.basename(parts.path)

        count = 0
        while count < retry:
            count += 1
            file_path = Downloader.aria2(
                url=url,
                path=path,
                save_name=filename,
            )
            if file_path is None:
                logger.warning("[%s/%s] 重试下载 %s", count, retry, url)
                continue
            else:
                logger.info("[%s/%s] 下载 %s 成功, 路径: %s",
                            count, retry, url, file_path)
                return file_path
        return None

    def get_model_from_list(
        self,
        path: str | Path,
        model_list: list[str, int],
        retry: int | None = 3
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
                    self.get_model(
                        url=url,
                        path=path,
                        retry=retry
                    )
                else:
                    self.get_model(
                        url=url,
                        path=path,
                        filename=filename,
                        retry=retry
                    )


class SDScriptsManager(BaseManager):
    """sd-scripts 管理工具"""

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
        sd_scripts_requirment: str | None = None,
        retry: int | None = 3,
        huggingface_token: str | None = None,
        modelscope_token: str | None = None,
        wandb_token: str | None = None,
        git_username: str | None = None,
        git_email: str | None = None,
        check_avaliable_gpu: bool | None = False,
        enable_tcmalloc: bool | None = True,
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
        :param sd_scripts_requirment`(str|None)`: sd-scripts 的依赖文件名, 未指定时默认为`requirements.txt`
        :param retry`(int|None)`: 设置下载模型失败时重试次数
        :param huggingface_token`(str|None)`: 配置 HuggingFace Token
        :param modelscope_tokenn`(str|None)`: 配置 ModelScope Token
        :param wandb_token`(str|None)`: 配置 WandB Token
        :param git_username`(str|None)`: Git 用户名
        :param git_email`(str|None)`: Git 邮箱
        :param check_avaliable_gpu`(bool|None)`: 检查是否有可用的 GPU, 当 GPU 不可用时引发`Exception`
        :param enable_tcmalloc`(bool|None)`: 启用 TCMalloc 内存优化
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
        logger.info("配置 sd-scripts 环境中")
        os.chdir(self.workspace)
        sd_scripts_path = self.workspace / self.workfolder
        requirement_path = sd_scripts_path / \
            (sd_scripts_requirment if sd_scripts_requirment is not None else "requirements.txt")
        sd_scripts_repo = sd_scripts_repo if sd_scripts_repo is not None else "https://github.com/kohya-ss/sd-scripts"
        model_path = model_path if model_path is not None else (
            self.workspace / "sd-models")
        model_list = model_list if model_list else []
        # 检查是否有可用的 GPU
        if check_avaliable_gpu and not self.utils.check_gpu():
            raise Exception(
                "没有可用的 GPU, 请在 kaggle -> Notebook -> Session options -> ACCELERATOR 选择 GPU T4 x 2\n如果不能使用 GPU, 请检查 Kaggle 账号是否绑定了手机号或者尝试更换账号!")
        # 配置镜像源
        self.mirror.set_mirror(
            pypi_index_mirror=pypi_index_mirror,
            pypi_extra_index_mirror=pypi_extra_index_mirror,
            pypi_find_links_mirror=pypi_find_links_mirror,
            github_mirror=github_mirror,
            huggingface_mirror=huggingface_mirror
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
            self.git.switch_branch(
                path=sd_scripts_path,
                branch=git_branch
            )
        # 切换到指定的 sd-scripts 提交记录
        if git_commit is not None:
            self.git.switch_commit(
                path=sd_scripts_path,
                commit=git_commit
            )
        # 安装 PyTorch 和 xFormers
        self.env.install_pytorch(
            torch_package=torch_ver,
            xformers_package=xformers_ver,
            pytorch_mirror=pytorch_mirror,
            use_uv=use_uv
        )
        # 安装 sd-scripts 的依赖
        os.chdir(sd_scripts_path)
        self.env.install_requirements(
            path=requirement_path,
            use_uv=use_uv
        )
        os.chdir(self.workspace)
        # 安装使用 sd-scripts 进行训练所需的其他软件包
        logger.info("安装其他 Python 模块中")
        try:
            self.env.pip_install(
                "lycoris-lora",
                "dadaptation",
                "open-clip-torch",
                use_uv=use_uv
            )
        except Exception as e:
            logger.error("安装额外 Python 软件包时发生错误: %s", e)
        # 更新 urllib3
        try:
            self.env.pip_install(
                "urllib3",
                "--upgrade",
                use_uv=False
            )
        except Exception as e:
            logger.error("更新 urllib3 时发生错误: %s", e)
        try:
            self.env.pip_install(
                "numpy==1.26.4",
                use_uv=use_uv
            )
        except Exception as e:
            logger.error("降级 numpy 时发生错误: %s", e)
        self.get_model_from_list(
            path=model_path,
            model_list=model_list,
            retry=retry
        )
        self.restart_repo_manager(
            hf_token=huggingface_token,
            ms_token=modelscope_token,
        )
        self.utils.config_wandb_token(wandb_token)
        self.git.set_git_config(
            username=git_username,
            email=git_email,
        )
        enable_tcmalloc and self.utils.config_tcmalloc()
        logger.info("sd-scripts 环境配置完成")


class FooocusManager(BaseManager):
    """Fooocus 管理工具"""

    def mount_drive(self) -> None:
        """挂载 Google Drive 并创建 Fooocus 输出文件夹"""
        drive_path = Path("/content/drive")
        if not (drive_path / "MyDrive").exists():
            if not self.utils.mount_google_drive(drive_path):
                raise Exception("挂载 Google Drive 失败, 请尝试重新挂载 Google Drive")

        fooocus_output = drive_path / "MyDrive" / "fooocus_output"
        fooocus_output.mkdir(exist_ok=True)

    def get_sd_model(
        self,
        url: str,
        filename: str = None
    ) -> None:
        """下载大模型

        :param url`(str)`: 模型的下载链接
        :param filename`(str|None)`: 模型下载后保存的名称
        """
        path = self.workspace / self.workfolder / "models" / "checkpoints"
        return self.downloader.download_file(url=url, path=path, save_name=filename, tools="aria2")

    def get_lora_model(
        self,
        url: str,
        filename: str = None
    ) -> None:
        """下载 LoRA 模型

        :param url`(str)`: 模型的下载链接
        :param filename`(str|None)`: 模型下载后保存的名称
        """
        path = self.workspace / self.workfolder / "models" / "loras"
        return self.downloader.download_file(url=url, path=path, save_name=filename, tools="aria2")

    def get_vae_model(
        self,
        url: str,
        filename: str = None
    ) -> None:
        """下载 VAE 模型

        :param url`(str)`: 模型的下载链接
        :param filename`(str|None)`: 模型下载后保存的名称
        """
        path = self.workspace / self.workfolder / "models" / "vae"
        return self.downloader.download_file(url=url, path=path, save_name=filename, tools="aria2")

    def get_embedding_model(
        self,
        url: str,
        filename: str = None
    ) -> None:
        """下载 Embedding 模型

        :param url`(str)`: 模型的下载链接
        :param filename`(str|None)`: 模型下载后保存的名称
        """
        path = self.workspace / self.workfolder / "models" / "embeddings"
        return self.downloader.download_file(url=url, path=path, save_name=filename, tools="aria2")

    def install_config(
        self,
        preset: str | None = None,
        path_config: str | None = None,
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
        preset and self.downloader.download_file(
            url=preset, path=preset_path, save_name="custom.json", tools="aria2")
        path_config and self.downloader.download_file(
            url=path_config, path=path, save_name="config.txt", tools="aria2")
        translation and self.downloader.download_file(
            url=translation, path=language_path, save_name="zh.json", tools="aria2")

    def pre_download_model(
        self,
        path: str | Path,
        thread_num: int | None = 16,
        downloader: Literal["aria2", "requests", "mix"] = "mix"
    ) -> None:
        """根据 Fooocus 配置文件预下载模型

        :param path`(str|Path)`: Fooocus 配置文件路径
        :param thread_num`(int|None)`: 下载模型的线程数
        :param downloader`(Literal["aria2","request","mix"])`: 预下载模型时使用的下载器 (`aria2`, `requests`, `mix`)
        """
        path = Path(path) if not isinstance(
            path, Path) and path is not None else path
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
                "tools": sd_model_downloader
            }
            for i in sd_model_list
        ]
        downloader_params += [
            {
                "url": lora_list.get(i),
                "path": lora_path,
                "save_name": i,
                "tools": lora_downloader
            }
            for i in lora_list
        ]
        downloader_params += [
            {
                "url": vae_list.get(i),
                "path": vae_path,
                "save_name": i,
                "tools": vae_downloader
            }
            for i in vae_list
        ]
        downloader_params += [
            {
                "url": embedding_list.get(i),
                "path": embedding_path,
                "save_name": i,
                "tools": embedding_downloader
            }
            for i in embedding_list
        ]

        model_downloader = MultiThreadDownloader(
            download_func=self.downloader.download_file,
            download_kwargs_list=downloader_params,
        )
        model_downloader.start(num_threads=thread_num)
        logger.info("预下载 Fooocus 模型完成")

    def tcmalloc_colab(self) -> None:
        """配置 TCMalloc (Colab)"""
        logger.info("配置 TCMalloc 内存优化")
        url = "https://github.com/licyk/term-sd/releases/download/archive/libtcmalloc_minimal.so.4"
        libtcmalloc_path = self.workspace / "libtcmalloc_minimal.so.4"
        self.downloader.download_file(
            url=url, path=self.workspace, save_name="libtcmalloc_minimal.so.4")
        os.environ["LD_PRELOAD"] = str(libtcmalloc_path)

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
        fooocus_requirment: str | None = None,
        fooocus_preset: str | None = None,
        fooocus_path_config: str | None = None,
        fooocus_translation: str | None = None,
        model_downloader: Literal["aria2", "request", "mix"] = "mix",
        download_model_thread: int | None = 16,
        check_avaliable_gpu: bool | None = False,
        enable_tcmalloc: bool | None = True,
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
        :param fooocus_requirment`(str|None)`: Fooocus 依赖文件名
        :param fooocus_preset`(str|None)`: Fooocus 预设文件下载链接
        :param fooocus_path_config`(str|None)`: Fooocus 路径配置文件下载地址
        :param fooocus_translation`(str|None)`: Fooocus 翻译文件下载地址
        :param model_downloader`(Literal["aria2","request","mix"])`: 预下载模型时使用的模型下载器
        :param download_model_thread`(int|None)`: 预下载模型的线程
        :param check_avaliable_gpu`(bool|None)`: 是否检查可用的 GPU, 当检查时没有可用 GPU 将引发`Exception`
        :param enable_tcmalloc`(bool|None)`: 是否启用 TCMalloc 内存优化
        """
        logger.info("开始安装 Fooocus")
        os.chdir(self.workspace)
        fooocus_path = self.workspace / self.workfolder
        fooocus_repo = "https://github.com/lllyasviel/Fooocus" if fooocus_repo is None else fooocus_repo
        fooocus_preset = "https://github.com/licyk/term-sd/releases/download/archive/fooocus_config.json" if fooocus_preset is None else fooocus_preset
        fooocus_path_config = "https://github.com/licyk/term-sd/releases/download/archive/fooocus_path_config_colab.json" if fooocus_path_config is None else fooocus_path_config
        fooocus_translation = "https://github.com/licyk/term-sd/releases/download/archive/fooocus_zh_cn.json" if fooocus_translation is None else fooocus_translation
        requirment_path = fooocus_path / \
            ("requirements_versions.txt" if fooocus_requirment is None else fooocus_requirment)
        config_file = fooocus_path / "presets" / "custom.json"
        if check_avaliable_gpu and not self.utils.check_gpu():
            raise Exception(
                "没有可用的 GPU, 请在 Colab -> 代码执行程序 > 更改运行时类型 -> 硬件加速器 选择 GPU T4\n如果不能使用 GPU, 请尝试更换账号!")
        logger.info("Fooocus 内核分支: %s", fooocus_repo)
        logger.info("Fooocus 预设配置: %s", fooocus_preset)
        logger.info("Fooocus 路径配置: %s", fooocus_path_config)
        logger.info("Fooocus 翻译配置: %s", fooocus_translation)
        self.mirror.set_mirror(
            pypi_index_mirror=pypi_index_mirror,
            pypi_extra_index_mirror=pypi_extra_index_mirror,
            pypi_find_links_mirror=pypi_find_links_mirror,
            github_mirror=github_mirror,
            huggingface_mirror=huggingface_mirror
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
        self.env.install_requirements(requirment_path, use_uv)
        os.chdir(self.workspace)
        self.install_config(
            preset=fooocus_preset,
            path_config=fooocus_path_config,
            translation=fooocus_translation
        )
        enable_tcmalloc and self.tcmalloc_colab()
        self.pre_download_model(
            path=config_file,
            thread_num=download_model_thread,
            downloader=model_downloader,
        )
        logger.info("Fooocus 安装完成")
