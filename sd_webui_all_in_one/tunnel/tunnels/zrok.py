"""Zrok 内网穿透实现"""

import queue
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import uuid
import platform
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from sd_webui_all_in_one.cmd import (
    preprocess_command,
    run_cmd,
)
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.downloader import download_file
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.tunnel.base import BaseTunnel


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class ZrokTunnel(BaseTunnel):
    """Zrok 内网穿透

    使用 Zrok 实现内网穿透. 需要提供 Zrok Token. 

    Attributes:
        zrok_token (str):
            Zrok 账号 Token
    """

    def __init__(
        self,
        port: int,
        workspace: Path,
        zrok_token: str,
    ) -> None:
        """初始化 Zrok 内网穿透

        Args:
            port (int):
                要进行端口映射的端口
            workspace (Path):
                工作区路径
            zrok_token (str):
                Zrok 账号 Token
        """
        super().__init__(port, workspace)
        self.zrok_token = zrok_token
        self._zrok_bin: Optional[Path] = None

    def _get_latest_zrok_release(
        self,
    ) -> list[list[str]]:
        """获取最新的 Zrok 发行内容下载列表

        Returns:
            list[list[str]]: 获取到的发行版下载列表 [[文件名, 下载链接], ...]

        Raises:
            FileNotFoundError: 获取 Zrok 发行版本列表失败时
        """
        import requests

        url = "https://api.github.com/repos/openziti/zrok/releases/latest"
        data = {
            "Accept": "application/vnd.github+json",
        }
        logger.info("获取 Zrok 发行版本列表")
        response = requests.get(url=url, data=data)
        res = response.json()

        if response.status_code < 200 or response.status_code > 300:
            logger.error("获取 Zrok 发行版本列表失败")
            raise FileNotFoundError("获取 Zrok 发行版本列表失败")

        file_list = []
        for i in res.get("assets", []):
            file_list.append([i.get("name"), i.get("browser_download_url")])
        return file_list

    def _get_appropriate_zrok_package(
        self,
        packages: list[list[str]],
    ) -> tuple[str, str]:
        """获取适合当前平台的 Zrok 版本

        Args:
            packages (list[list[str]]): 发行版下载列表

        Returns:
            tuple[str, str]: (文件名, 下载链接)

        Raises:
            OSError: 未找到适合当前平台的 Zrok 时
        """

        def _get_current_platform_and_arch() -> tuple[str, str]:
            _arch = platform.machine()
            _platform = sys.platform
            _platform = _platform.replace("win32", "windows").replace("cygwin", "windows").replace("linux2", "linux")
            _arch = _arch.replace("x86_64", "amd64").replace("AMD64", "amd64").replace("aarch64", "arm64").replace("armv7l", "armv7")
            return _platform, _arch

        zrok_package_name_pattern = r"""
            ^
            (?P<software>[\w]+?)                        # 软件名
            _
            (?P<version>[\d.]+)                         # 版本号 (数字和点)
            _
            (?P<platform>[\w]+?)                        # 系统类型
            _
            (?P<arch>[\w]+?)                            # 架构
            \.
            (?P<extension>[a-z0-9]+(?:\.[a-z0-9]+)?)    # 扩展名 (支持多级扩展)
            $
        """

        # 编译正则表达式 (忽略大小写, 详细模式)
        zrok_name_parse_regex = re.compile(zrok_package_name_pattern, re.VERBOSE | re.IGNORECASE)

        current_platform, current_arch = _get_current_platform_and_arch()

        for p, url in packages:
            match = zrok_name_parse_regex.match(p)
            if match:
                groups = match.groupdict()
                support_arch = groups.get("arch")
                support_platform = groups.get("platform")
                if current_platform == support_platform and support_arch == current_arch:
                    logger.info("找到合适 Zrok 版本: %s", p)
                    return p, url

        logger.error("未找到适合当前平台的 Zrok")
        raise OSError("未找到适合当前平台的 Zrok")

    def _install_zrok(
        self,
    ) -> Path:
        """安装 Zrok

        Returns:
            Path: Zrok 可执行文件路径

        Raises:
            RuntimeError: Zrok 安装失败时
        """
        if sys.platform == "win32":
            bin_extension_name = ".exe"
        else:
            bin_extension_name = ""

        zrok_bin = self.workspace / f"zrok{bin_extension_name}"

        # 检查是否已安装
        if zrok_bin.is_file():
            try:
                run_cmd([zrok_bin.as_posix(), "version"], live=False)
                logger.info("Zrok 已安装")
                return zrok_bin
            except RuntimeError:
                pass

        logger.info("安装 Zrok 中")

        # 备份旧版本
        if zrok_bin.exists():
            shutil.move(zrok_bin, zrok_bin.parent / f"zrok_{uuid.uuid4()}")

        # 下载并安装
        release = self._get_latest_zrok_release()
        package_name, download_url = self._get_appropriate_zrok_package(release)

        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            try:
                zrok_archive_file = download_file(
                    url=download_url,
                    path=tmp_dir,
                    save_name=package_name,
                )
                with tarfile.open(zrok_archive_file, "r:gz") as tar:
                    tar.extractall(path=tmp_dir)
                zrok_bin_in_tmp_dir = tmp_dir / f"zrok2{bin_extension_name}"
                shutil.move(zrok_bin_in_tmp_dir, zrok_bin)
                logger.info("Zrok 安装成功")
                return zrok_bin
            except Exception as e:
                logger.error("Zrok 安装失败: %s", e)
                raise RuntimeError(f"Zrok 安装时发生错误: {e}") from e

    def start(
        self,
    ) -> str:
        """启动 Zrok 内网穿透

        Returns:
            str: Zrok 内网穿透地址

        Raises:
            RuntimeError: 启动 Zrok 内网穿透失败时
        """
        logger.info("启动 Zrok 内网穿透中")

        # 安装 Zrok
        self._zrok_bin = self._install_zrok()

        # 初始化 Zrok 配置
        logger.info("初始化 Zrok 配置")
        try:
            run_cmd([self._zrok_bin.as_posix(), "disable"], live=False)
        except RuntimeError:
            pass

        try:
            run_cmd([self._zrok_bin.as_posix(), "enable", self.zrok_token])
            logger.info("Zrok 配置初始化完成")
        except RuntimeError as e:
            logger.error("初始化 Zrok 配置失败, 无法使用 Zrok 内网穿透: %s", e)
            raise RuntimeError(f"初始化 Zrok 配置失败, 无法使用 Zrok 内网穿透: {e}") from e

        # 启动 Zrok 隧道
        # Zrok 输出格式：rp179091kyw1.shares.zrok.io 或 https://xxx.share.zrok.io
        host_pattern = re.compile(r"(?P<url>(?:https?://)?[\w]+\.(?:share|shares)\.zrok\.io)")

        command = [self._zrok_bin.as_posix(), "share", "public", str(self.port), "--headless"]
        command_to_exec = preprocess_command(command, shell=True)

        self._process = subprocess.Popen(
            command_to_exec,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding="utf-8",
        )

        output_queue = queue.Queue()
        lines_collected = []

        def _read_output():
            """读取进程输出"""
            try:
                for line in iter(self._process.stdout.readline, ""):
                    if line:
                        output_queue.put(("LINE", line))
                        # 检查是否包含 URL
                        url_match = host_pattern.search(line)
                        if url_match:
                            output_queue.put(("URL", url_match.group("url")))
            except Exception as e:
                logger.error("读取 Zrok 输出时发生错误: %s", e)
            finally:
                if self._process.stdout:
                    self._process.stdout.close()

        thread = threading.Thread(target=_read_output)
        thread.daemon = True
        thread.start()

        # 等待 URL 出现
        start_ts = time.time()
        while time.time() - start_ts < 60:
            try:
                item = output_queue.get(timeout=1)
                if isinstance(item, tuple):
                    if item[0] == "URL":
                        url = item[1]
                        # 如果 URL 没有协议前缀, 添加 https://
                        if not url.startswith(("http://", "https://")):
                            url = f"https://{url}"
                        self._url = url
                        logger.info("Zrok 内网穿透启动完成")
                        return self._url
                    elif item[0] == "LINE":
                        line = item[1].strip()
                        lines_collected.append(line)
                        # 打印输出以便调试
                        if line:
                            logger.debug("Zrok 输出: %s", line)
            except queue.Empty:
                # 检查进程是否已退出
                if self._process.poll() is not None:
                    logger.error("Zrok 进程意外退出, 退出码: %s", self._process.poll())
                    logger.error("收集到的输出行数: %d", len(lines_collected))
                    if lines_collected:
                        logger.error("最后几行输出: %s", lines_collected[-5:])
                    break

        logger.error("启动 Zrok 内网穿透失败, 超时或进程退出")
        logger.error("总共收集到 %d 行输出", len(lines_collected))
        raise RuntimeError("启动 Zrok 内网穿透失败")

    def stop(
        self,
    ) -> None:
        """停止 Zrok 内网穿透

        先禁用 Zrok, 再终止进程. 
        """
        # 禁用 Zrok
        if self._zrok_bin:
            try:
                logger.info("正在禁用 Zrok")
                run_cmd([self._zrok_bin.as_posix(), "disable"], live=False)
                logger.info("Zrok 已禁用")
            except Exception as e:
                logger.error("禁用 Zrok 失败: %s", e)

        # 终止进程
        super().stop()
