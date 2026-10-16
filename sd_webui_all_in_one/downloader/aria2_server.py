"""Aria2 RPC 服务器"""

import hashlib
import importlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import (
    Any,
    Literal,
)
from urllib.parse import urlparse

from sd_webui_all_in_one.downloader.requests_downloader.http import _filename_from_url, _normalize_urls
from sd_webui_all_in_one.downloader.requests_downloader.models import DownloadCancelledError, DownloadProgressEvent
from sd_webui_all_in_one.utils import (
    find_port,
    is_port_in_use,
)
from sd_webui_all_in_one.downloader.types import DEFAULT_USER_AGENT
from sd_webui_all_in_one.package_analyzer import Version
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    ARIA2_NEXT_MINIMUM_VER,
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
    ROOT_PATH,
    SD_WEBUI_ALL_IN_ONE_CACHE_PATH,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

ARIA2_CONFIG_PATH = ROOT_PATH / "downloader" / "aria2.conf"
"""Aria2 配置文件"""

ARIA2_NEXT_CONFIG_PATH = ROOT_PATH / "downloader" / "aria2-next.conf"
"""Aria2 Next 配置文件"""

ARIA2_NEXT_STATE_PATH = SD_WEBUI_ALL_IN_ONE_CACHE_PATH / "aria2-next"
"""Aria2 Next 持久化引擎状态目录, 保存断点续传进度"""

ARIA2_NEXT_UNSUPPORTED_DOWNLOAD_OPTIONS = (
    "piece-length",
    "allow-piece-length-change",
    "always-resume",
    "conditional-get",
    "max-resume-failure-tries",
)
"""aria2-next 不支持或已弃用的 aria2 下载任务选项"""


class Aria2RpcServer:
    """
    aria2 RPC 服务器管理器基类（上下文管理器）

    自动启动和关闭 aria2 RPC 服务器, 提供下载功能

    支持进程监控、自动重试、崩溃检测等功能

    子类需要实现`find_executable()`和`_builtin_options()`, 并可通过`config_path`指定配置文件:
    - `Aria2cRpcServer`: 使用 aria2c 可执行文件
    - `Aria2NextRpcServer`: 使用 aria2-next 可执行文件

    Attributes:
        product_name (str):
            下载器名称, 用于日志和错误信息
        config_path (Path | None):
            启动时使用的配置文件路径
        port (int):
            RPC 服务器监听端口
        secret (str | None):
            RPC 密钥, 用于安全认证
        download_dir (Path):
            默认下载目录
        log_file (Path | None):
            日志文件路径
        log_level (str):
            日志级别
        user_agent (str):
            User-Agent 配置
        use_config_file (bool):
            是否使用配置文件启动 aria2
        use_external_server (bool):
            是否允许连接到外部已存在的 aria2 服务器。
            当多个实例同时运行时, 若某个实例提前完成下载并关闭服务器,
            可能导致其他连接到同一服务器的实例崩溃。
            设为 False 可强制每个实例启动独立的 aria2 进程, 避免此问题。
        rpc_url (str):
            RPC 服务器 URL 地址
        process (subprocess.Popen | None):
            aria2 进程对象
        _session_file (Any | None):
            临时会话文件
        _is_external_server (bool):
            是否连接到外部 aria2 服务器

    Examples:
        ```python
        # 使用配置文件启动（默认）
        with Aria2cRpcServer(port=6800) as aria2:
            # 下载单个文件
            aria2.download("https://example.com/file.zip", save_path="/tmp")

            # 批量下载
            urls = ["https://example.com/file1.zip", "https://example.com/file2.zip"]
            aria2.download_batch(urls, save_path="/tmp")
        # 退出上下文后自动关闭服务器

        # 使用硬编码参数启动（向后兼容）
        with Aria2cRpcServer(port=6800, use_config_file=False) as aria2:
            aria2.download("https://example.com/file.zip", save_path="/tmp")

        # 多实例并发下载时, 禁用外部服务器复用以避免相互干扰
        with Aria2cRpcServer(port=6800, use_external_server=False) as aria2:
            aria2.download("https://example.com/file.zip", save_path="/tmp")
        ```
    """

    product_name: str = "aria2"
    config_path: Path | None = None

    def __init__(
        self,
        port: int = 6800,
        secret: str | None = None,
        download_dir: Path | None = None,
        log_file: Path | str | None = None,
        log_level: Literal["debug", "info", "notice", "warn", "error"] | None = "notice",
        user_agent: str | None = DEFAULT_USER_AGENT,
        use_config_file: bool = True,
        use_external_server: bool = True,
    ) -> None:
        """
        初始化 aria2 RPC 服务器管理器

        Args:
            port (int):
                RPC 服务器监听端口, 默认 6800
            secret (str | None):
                RPC 密钥, 用于安全认证, 为 None 时不设置密钥
            download_dir (Path | None):
                默认下载目录, 为 None 时使用当前工作目录
            log_file (Path | str | None):
                日志文件路径, 为 None 时不记录日志到文件
            log_level (Literal["debug", "info", "notice", "warn", "error"] | None):
                日志级别, 可选: debug, info, notice, warn, error, 默认 "notice"
            user_agent (str | None):
                User-Agent 配置
            use_config_file (bool):
                是否使用配置文件启动 aria2, 默认 True
            use_external_server (bool):
                是否允许连接到外部已存在的 aria2 服务器, 默认 True。
                当多个实例同时运行时, 若某个实例提前完成下载并关闭服务器,
                可能导致其他连接到同一服务器的实例崩溃。
                设为 False 可强制每个实例启动独立的 aria2 进程, 避免此问题。
        """
        self.port: int = port
        self.secret: str | None = secret
        self.download_dir: Path = Path(download_dir) if download_dir else Path.cwd()
        self.log_file: Path | None = Path(log_file) if log_file else None
        self.log_level: str = log_level or "notice"
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.use_config_file: bool = use_config_file
        self.use_external_server: bool = use_external_server
        self.rpc_url: str = f"http://localhost:{self.port}/jsonrpc"
        self.process: subprocess.Popen | None = None
        self._session_file: Any | None = None
        self._is_external_server: bool = False  # 标记是否连接到外部服务器

    @classmethod
    def find_executable(
        cls,
    ) -> str | None:
        """
        查找下载器可执行文件

        Returns:
            (str | None): 可执行文件路径, 未找到时返回 None

        Raises:
            NotImplementedError: 基类未实现该方法
        """
        raise NotImplementedError(f"{cls.__name__} 未实现 find_executable()")

    @classmethod
    def is_available(
        cls,
    ) -> bool:
        """
        检查下载器可执行文件是否可用

        Returns:
            bool: 找到可执行文件时返回 True
        """
        return cls.find_executable() is not None

    def _builtin_options(
        self,
    ) -> list[str]:
        """
        获取不使用配置文件时的内置启动参数

        Returns:
            list[str]: 内置启动参数列表

        Raises:
            NotImplementedError: 基类未实现该方法
        """
        raise NotImplementedError(f"{type(self).__name__} 未实现 _builtin_options()")

    def _extra_args(
        self,
    ) -> list[str]:
        """
        获取额外的启动参数, 在启动进程前调用

        Returns:
            list[str]: 额外启动参数列表
        """
        return []

    def _prepare_download_options(
        self,
        urls: list[str],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        """
        在添加下载任务前将 aria2 下载任务选项转换为当前下载器支持的选项

        Args:
            urls (list[str]):
                下载任务的链接列表
            options (dict[str, Any]):
                aria2 下载任务选项

        Returns:
            (dict[str, Any]): 转换后的下载任务选项
        """
        return options

    def __enter__(
        self,
    ) -> "Aria2RpcServer":
        """
        进入上下文管理器, 启动 aria2 RPC 服务器

        Returns:
            Aria2RpcServer: 返回实例本身
        """
        self._start_server()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> bool:
        """
        退出上下文管理器, 关闭 aria2 RPC 服务器

        Args:
            exc_type (type[BaseException] | None):
                异常类型
            exc_val (BaseException | None):
                异常值
            exc_tb (Any | None):
                异常追踪信息

        Returns:
            bool: False, 表示不抑制异常
        """
        self._stop_server()
        return False

    def _start_server(
        self,
    ) -> None:
        """
        启动 aria2 RPC 服务器

        Raises:
            RuntimeError:
                未找到下载器可执行文件或服务器启动超时
        """

        # 检查下载器是否可用
        executable = self.find_executable()
        if executable is None:
            raise RuntimeError(f"未找到 {self.product_name} 可执行文件, 请先安装 {self.product_name}")

        # 检查端口是否已被占用
        if is_port_in_use(self.port):
            logger.debug("端口 %d 已被占用, 尝试连接现有服务", self.port)
            if self.use_external_server and self._test_connection():
                logger.debug("成功连接到现有 aria2 RPC 服务")
                self._is_external_server = True  # 标记为外部服务器
                return
            else:
                if not self.use_external_server:
                    logger.debug("已禁用外部服务器复用, 跳过连接现有 aria2 RPC 服务, 尝试更换端口创建独立实例")
                else:
                    logger.debug("端口已被占用但无法连接到 aria2 RPC 服务, 尝试更换端口创建新的 aria2 RPC 服务")
                self.port = find_port(self.port)
                self.rpc_url = f"http://localhost:{self.port}/jsonrpc"  # 更新 RPC URL
                logger.debug("已更换到 %d 端口", self.port)

        # 创建临时会话文件
        self._session_file = NamedTemporaryFile(mode="w", suffix=".aria2.session", delete=False)
        self._session_file.close()

        # 构建启动命令
        config_path = self.config_path
        if self.use_config_file and config_path is not None and config_path.exists():
            # 使用配置文件启动
            cmd = [
                executable,
                f"--conf-path={config_path.as_posix()}",
                f"--rpc-listen-port={self.port}",
            ]
            logger.debug("使用配置文件启动 %s: %s", self.product_name, config_path)
        else:
            # 使用硬编码参数启动（向后兼容）
            cmd = [
                executable,
                "--enable-rpc=true",
                f"--rpc-listen-port={self.port}",
                "--rpc-listen-all=false",
                "--rpc-allow-origin-all=true",
                *self._builtin_options(),
            ]
            if not self.use_config_file:
                logger.debug("使用硬编码参数启动 %s", self.product_name)
            else:
                logger.warning("配置文件不存在: %s, 使用硬编码参数启动 %s", config_path, self.product_name)

        cmd += [
            f"--dir={self.download_dir.as_posix()}",
            "--console-log-level=error",
            f"--log-level={self.log_level}",
            f"--save-session={self._session_file.name}",
            f"--user-agent={self.user_agent}",
        ]

        if self.secret:
            cmd.append(f"--rpc-secret={self.secret}")

        if self.log_file:
            cmd.append(f"--log={self.log_file.as_posix()}")

        # 启动 aria2 进程
        try:
            cmd += self._extra_args()
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            # 等待服务器启动
            max_wait: int = 10  # 最多等待 10 秒
            for _ in range(max_wait):
                if self._test_connection():
                    logger.debug("aria2 RPC 服务器已启动, 监听端口: %d", self.port)
                    return
                time.sleep(1)

            raise RuntimeError("aria2 RPC 服务器启动超时")

        except Exception as e:
            self._cleanup()
            raise RuntimeError(f"启动 aria2 RPC 服务器失败: {e}") from e

    def _stop_server(
        self,
    ) -> None:
        """
        关闭 aria2 RPC 服务器

        尝试通过 RPC 优雅关闭, 如果无响应则强制终止进程
        """
        # 如果连接的是外部服务器,不需要关闭
        if self._is_external_server:
            logger.debug("连接的是外部 aria2 RPC 服务器, 跳过关闭操作")
            return

        if self.process is None:
            return

        try:
            # 尝试通过 RPC 优雅关闭
            try:
                self._rpc_call("aria2.shutdown")
                logger.debug("已发送关闭信号到 aria2 RPC 服务器")
            except Exception as e:
                # RPC 关闭失败时仍会等待并在超时后强制终止进程
                logger.debug("通过 RPC 关闭 aria2 失败, 等待进程退出: %s", e)

            # 等待进程结束
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("aria2 进程未响应, 强制终止")
                self.process.kill()
                self.process.wait()

            logger.debug("aria2 RPC 服务器已关闭")

        except Exception as e:
            logger.error("关闭 aria2 RPC 服务器时出错: %s", e)

        finally:
            self._cleanup()

    def _cleanup(
        self,
    ) -> None:
        """清理临时会话文件"""
        if self._session_file and os.path.exists(self._session_file.name):
            try:
                os.unlink(self._session_file.name)
            except OSError as e:
                logger.warning("删除 aria2 临时会话文件 '%s' 失败: %s", self._session_file.name, e)

    def _check_process_alive(
        self,
    ) -> bool:
        """
        检查 aria2 进程是否仍在运行

        Returns:
            bool: 进程运行中返回 True, 否则返回 False
        """
        if self._is_external_server:
            # 外部服务器,通过 RPC 测试连接
            return self._test_connection()

        if self.process is None:
            return False

        # 检查进程是否已退出
        return self.process.poll() is None

    def _get_process_error_output(
        self,
    ) -> str:
        """
        获取 aria2 进程的错误输出

        Returns:
            str: 错误输出内容
        """
        if self.process is None or self._is_external_server:
            return ""

        try:
            # 尝试读取 stderr
            if self.process.stderr:
                stderr_output = self.process.stderr.read()
                if stderr_output:
                    return stderr_output.decode("utf-8", errors="ignore")
        except (OSError, ValueError) as e:
            logger.debug("读取 aria2 进程错误输出失败: %s", e)

        return ""

    def _test_connection(
        self,
    ) -> bool:
        """
        测试 RPC 连接是否可用

        Returns:
            bool: 连接可用返回 True, 否则返回 False
        """
        try:
            self._rpc_call("aria2.getVersion")
            return True
        except Exception as e:
            logger.debug("aria2 RPC 连接测试失败: %s", e)
            return False

    def _rpc_call(
        self,
        method: str,
        params: list[Any] | None = None,
        retry_count: int = 3,
    ) -> Any:
        """
        调用 aria2 RPC 方法

        Args:
            method (str):
                RPC 方法名
            params (list[Any] | None):
                方法参数列表
            retry_count (int):
                重试次数, 默认 3 次

        Returns:
            Any:
                RPC 响应结果

        Raises:
            RuntimeError:
                RPC 调用失败或无法连接到服务器
        """
        if params is None:
            params = []

        # 如果设置了密钥, 添加到参数列表开头
        if self.secret:
            params = [f"token:{self.secret}"] + params

        # 构造 JSON-RPC 请求
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": "1", "method": method, "params": params}

        # 发送 HTTP POST 请求
        data: bytes = json.dumps(payload).encode("utf-8")
        headers: dict[str, str] = {"Content-Type": "application/json"}

        last_error: Exception | None = None

        for attempt in range(retry_count):
            try:
                request = urllib.request.Request(self.rpc_url, data=data, headers=headers, method="POST")

                with urllib.request.urlopen(request, timeout=30) as response:
                    result: dict[str, Any] = json.loads(response.read().decode("utf-8"))

                    # 检查 RPC 错误
                    if "error" in result:
                        error: dict[str, Any] = result["error"]
                        raise RuntimeError(f"RPC Error {error['code']}: {error['message']}")

                    return result.get("result")

            except (urllib.error.URLError, TimeoutError) as e:
                last_error = e
                if attempt < retry_count - 1:
                    logger.debug("RPC 调用失败 (尝试 %d/%d): %s, 1 秒后重试", attempt + 1, retry_count, e)
                    time.sleep(1)
                continue
            except json.JSONDecodeError as e:
                raise RuntimeError(f"JSON 解析错误: {e}") from e

        # 所有重试都失败
        raise RuntimeError(f"无法连接到 aria2 RPC 服务器 (已重试 {retry_count} 次): {last_error}") from last_error

    def download(
        self,
        url: str | Sequence[str],
        save_path: Path | None = None,
        save_name: str | None = None,
        options: dict[str, Any] | None = None,
        show_progress: bool = True,
        wait_complete: bool = True,
        progress_callback: Any | None = None,
        cancel_event: Any | None = None,
    ) -> Path:
        """
        下载单个文件

        Args:
            url (str | Sequence[str]):
                下载链接或同一文件的镜像链接列表
            save_path (Path | None):
                保存路径, 为 None 时使用默认下载目录
            save_name (str | None):
                保存的文件名, 为 None 时从 URL 提取
            options (dict[str, Any] | None):
                额外的 aria2 下载选项
            show_progress (bool):
                是否显示下载进度, 默认 True
            wait_complete (bool):
                是否等待下载完成, 默认 True
            progress_callback (Any | None):
                接收下载进度事件的回调函数
            cancel_event (Any | None):
                用于请求取消下载的事件对象

        Returns:
            Path: 下载文件的路径

        Raises:
            RuntimeError: 添加下载任务失败
        """
        if save_path is None:
            save_path = self.download_dir

        urls = _normalize_urls(url)
        explicit_save_name = save_name is not None
        if save_name is None:
            save_name = _filename_from_url(urls[0])

        # 构建下载选项
        download_options: dict[str, Any] = {
            "dir": save_path.as_posix(),
        }
        if explicit_save_name:
            download_options["out"] = save_name

        if options:
            download_options.update(options)
        download_options = self._prepare_download_options(urls, download_options)

        # 添加下载任务
        try:
            gid: str = self._rpc_call("aria2.addUri", [urls, download_options])
            logger.debug("下载任务已创建, GID: %s, 文件: %s", gid, save_name)
        except Exception as e:
            raise RuntimeError(f"添加下载任务失败: {e}") from e

        if not wait_complete:
            return save_path / save_name

        # 等待下载完成并显示进度
        return self._wait_download(gid, save_name, show_progress, progress_callback=progress_callback, cancel_event=cancel_event)

    def download_batch(
        self,
        urls: list[str],
        save_path: Path | None = None,
        options: dict[str, Any] | None = None,
        show_progress: bool = True,
    ) -> list[Path]:
        """
        批量下载文件

        Args:
            urls (list[str]):
                下载链接列表
            save_path (Path | None):
                保存路径, 为 None 时使用默认下载目录
            options (dict[str, Any] | None):
                额外的 aria2 下载选项
            show_progress (bool):
                是否显示下载进度, 默认 True

        Returns:
            list[Path]:
                下载文件的路径列表

        Raises:
            RuntimeError:
                没有成功添加任何下载任务
        """
        if save_path is None:
            save_path = self.download_dir

        gid_list: list[str] = []
        file_names: list[str] = []

        # 添加所有下载任务
        for url in urls:
            parts = urlparse(url)
            file_name: str = os.path.basename(parts.path)
            if not file_name:
                file_name = f"download_{len(gid_list) + 1}"

            download_options: dict[str, Any] = {
                "dir": save_path.as_posix(),
                "out": file_name,
            }

            if options:
                download_options.update(options)
            download_options = self._prepare_download_options([url], download_options)

            try:
                gid: str = self._rpc_call("aria2.addUri", [[url], download_options])
                gid_list.append(gid)
                file_names.append(file_name)
                logger.debug("下载任务已创建, GID: %s, 文件: %s", gid, file_name)
            except Exception as e:
                logger.error("添加下载任务失败: %s, URL: %s", e, url)

        if not gid_list:
            raise RuntimeError("没有成功添加任何下载任务")

        # 等待所有下载完成
        result_paths: list[Path] = []
        for gid, file_name in zip(gid_list, file_names):
            try:
                path: Path = self._wait_download(gid, file_name, show_progress)
                result_paths.append(path)
            except Exception as e:
                logger.error("下载失败: %s, GID: %s", e, gid)

        return result_paths

    def _wait_download(
        self,
        gid: str,
        file_name: str,
        show_progress: bool = True,
        progress_callback: Any | None = None,
        cancel_event: Any | None = None,
    ) -> Path:
        """
        等待下载完成并显示进度

        Args:
            gid (str):
                下载任务的 GID
            file_name (str):
                文件名
            show_progress (bool):
                是否显示进度条

        Returns:
            Path:
                下载文件的路径

        Raises:
            RuntimeError:
                下载失败或被中断
        """
        try:
            from tqdm import tqdm
        except ImportError:
            from sd_webui_all_in_one.simple_tqdm import SimpleTqdm as tqdm

        pbar: tqdm | None = None
        consecutive_errors: int = 0  # 连续错误计数
        max_consecutive_errors: int = 5  # 最大连续错误次数
        started_at = time.monotonic()

        try:
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    try:
                        self._rpc_call("aria2.remove", [gid], retry_count=1)
                    finally:
                        raise DownloadCancelledError("下载已取消")
                # 检查 aria2 进程是否仍在运行
                if not self._check_process_alive():
                    if pbar is not None:
                        pbar.close()

                    error_output = self._get_process_error_output()
                    error_msg = "aria2 进程已崩溃或退出"
                    if error_output:
                        error_msg += f"\n进程错误输出:\n{error_output}"

                    if self.log_file and self.log_file.exists():
                        error_msg += f"\n详细日志请查看: {self.log_file}"

                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                try:
                    # 查询下载状态
                    status: dict[str, Any] = self._rpc_call("aria2.tellStatus", [gid], retry_count=2)
                    consecutive_errors = 0  # 重置错误计数

                    total: int = int(status.get("totalLength", 0))
                    completed: int = int(status.get("completedLength", 0))
                    current_status: str = status.get("status", "unknown")
                    if progress_callback is not None:
                        files = status.get("files", [])
                        current_path = Path(files[0]["path"]) if files else self.download_dir / file_name
                        uris = files[0].get("uris", []) if files else []
                        current_url = uris[0].get("uri", "") if uris else ""
                        progress_callback(
                            DownloadProgressEvent(
                                target_path=current_path,
                                total_size=total,
                                completed_size=completed,
                                instantaneous_speed=float(status.get("downloadSpeed", 0)),
                                average_speed=completed / max(time.monotonic() - started_at, 1e-9),
                                active_connections=int(status.get("connections", 0)),
                                current_url=current_url,
                            )
                        )

                    # 初始化进度条
                    if show_progress and pbar is None and total > 0:
                        pbar = tqdm(total=total, unit="B", unit_scale=True, unit_divisor=1024, desc=file_name, initial=completed)

                    # 更新进度条
                    if pbar is not None:
                        if completed > pbar.n:
                            pbar.update(completed - pbar.n)

                    # 检查下载状态
                    if current_status == "complete":
                        if pbar is not None:
                            pbar.close()

                        # 获取下载文件的完整路径
                        files: list[dict[str, Any]] = status.get("files", [])
                        if files:
                            file_path: Path = Path(files[0]["path"])
                            logger.info("下载完成: %s", file_path)
                            return file_path
                        else:
                            # 如果无法从状态中获取路径, 使用默认路径
                            file_path = self.download_dir / file_name
                            logger.info("下载完成: %s", file_path)
                            return file_path

                    elif current_status == "error":
                        if pbar is not None:
                            pbar.close()

                        error_msg: str = status.get("errorMessage", "未知错误")
                        error_code: str = status.get("errorCode", "")
                        raise RuntimeError(f"下载失败: {error_msg} (错误代码: {error_code})")

                    elif current_status == "removed":
                        if pbar is not None:
                            pbar.close()
                        raise RuntimeError("下载任务已被移除")

                except RuntimeError as e:
                    raise e
                except Exception as e:
                    # 其他异常(如网络超时)进行计数
                    consecutive_errors += 1
                    logger.debug("查询下载状态时出错 (%d/%d): %s", consecutive_errors, max_consecutive_errors, e)

                    if consecutive_errors >= max_consecutive_errors:
                        if pbar is not None:
                            pbar.close()
                        raise RuntimeError(f"连续 {max_consecutive_errors} 次查询下载状态失败, 可能 aria2 进程已崩溃") from e

                    # 等待后继续尝试
                    time.sleep(2)
                    continue

                time.sleep(0.3)

        except KeyboardInterrupt:
            if pbar is not None:
                pbar.close()
            logger.warning("下载被用户中断, GID: %s", gid)
            # 尝试暂停任务
            try:
                self._rpc_call("aria2.pause", [gid], retry_count=1)
            except Exception as e:
                logger.warning("暂停 aria2 下载任务失败, GID: %s, 错误: %s", gid, e)
            raise

        except Exception as e:
            if pbar is not None:
                pbar.close()
            raise RuntimeError(f"等待下载完成时出错: {e}") from e

    def get_version(
        self,
    ) -> dict[str, Any]:
        """
        获取 aria2 版本信息

        Returns:
            dict[str, Any]: 版本信息字典
        """
        return self._rpc_call("aria2.getVersion")

    def get_global_stat(
        self,
    ) -> dict[str, Any]:
        """
        获取全局统计信息

        Returns:
            dict[str, Any]: 全局统计信息字典
        """
        return self._rpc_call("aria2.getGlobalStat")

    def pause(
        self,
        gid: str,
    ) -> str:
        """
        暂停下载任务

        Args:
            gid (str): 下载任务的 GID

        Returns:
            str: 操作的 GID
        """
        return self._rpc_call("aria2.pause", [gid])

    def unpause(
        self,
        gid: str,
    ) -> str:
        """
        恢复下载任务

        Args:
            gid (str): 下载任务的 GID

        Returns:
            str: 操作的 GID
        """
        return self._rpc_call("aria2.unpause", [gid])

    def remove(
        self,
        gid: str,
    ) -> str:
        """
        删除下载任务

        Args:
            gid (str): 下载任务的 GID

        Returns:
            str: 操作的 GID
        """
        return self._rpc_call("aria2.remove", [gid])

    def tell_status(
        self,
        gid: str,
        keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        获取下载任务状态

        Args:
            gid (str):
                任务 GID
            keys (list[str] | None):
                要获取的状态字段列表, 为 None 时获取所有字段

        Returns:
            dict[str, Any]: 任务状态信息
        """
        params: list[Any] = [gid]
        if keys:
            params.append(keys)
        return self._rpc_call("aria2.tellStatus", params)

    def tell_active(
        self,
    ) -> list[dict[str, Any]]:
        """
        获取所有活动的下载任务

        Returns:
            list[dict[str, Any]]: 活动任务列表
        """
        return self._rpc_call("aria2.tellActive")

    def tell_waiting(
        self,
        offset: int = 0,
        num: int = 100,
    ) -> list[dict[str, Any]]:
        """
        获取等待中的下载任务

        Args:
            offset (int):
                偏移量, 默认 0
            num (int):
                获取数量, 默认 100

        Returns:
            list[dict[str, Any]]: 等待任务列表
        """
        return self._rpc_call("aria2.tellWaiting", [offset, num])

    def tell_stopped(
        self,
        offset: int = 0,
        num: int = 100,
    ) -> list[dict[str, Any]]:
        """
        获取已停止的下载任务

        Args:
            offset (int):
                偏移量, 默认 0
            num (int):
                获取数量, 默认 100

        Returns:
            list[dict[str, Any]]: 已停止任务列表
        """
        return self._rpc_call("aria2.tellStopped", [offset, num])


class Aria2cRpcServer(Aria2RpcServer):
    """
    使用 aria2c 可执行文件的 aria2 RPC 服务器管理器

    启动时使用`aria2.conf`配置文件
    """

    product_name: str = "aria2"
    config_path: Path | None = ARIA2_CONFIG_PATH

    @classmethod
    def find_executable(
        cls,
    ) -> str | None:
        """
        查找 aria2c 可执行文件

        Returns:
            (str | None): aria2c 可执行文件路径, 未找到时返回 None
        """
        return shutil.which("aria2c")

    def _builtin_options(
        self,
    ) -> list[str]:
        """
        获取不使用配置文件时 aria2c 的内置启动参数

        Returns:
            list[str]: 内置启动参数列表
        """
        return [
            "--max-concurrent-downloads=16",
            "--max-connection-per-server=16",
            "--split=32",
            "--min-split-size=20M",
            "--piece-length=1M",
            "--continue=true",
            "--file-allocation=none",
            "--save-session-interval=10",
            "--connect-timeout=60",
            "--timeout=60",
            "--retry-wait=10",
            "--max-tries=5",
            "--check-certificate=false",
            "--http-accept-gzip=true",
            "--referer=*",
        ]


class Aria2NextRpcServer(Aria2RpcServer):
    """
    使用 aria2-next 可执行文件的 aria2 RPC 服务器管理器

    仅支持`ARIA2_NEXT_MINIMUM_VER`及以上版本。启动时使用`aria2-next.conf`配置文件,
    下载任务选项会转换为 aria2-next 支持的选项

    aria2-next 不会在下载文件旁写入控制文件, 断点进度只保存在`--state-dir`中并以 GID 为索引,
    因此使用持久化的状态目录, 并根据保存路径生成固定的 GID, 使中断的任务在下次启动时能够正确续传
    """

    product_name: str = "aria2-next"
    config_path: Path | None = ARIA2_NEXT_CONFIG_PATH

    @classmethod
    def find_executable(
        cls,
    ) -> str | None:
        """
        查找满足最低版本要求的 aria2-next 可执行文件

        依次检查 PATH 中的 aria2-next 和 aria2-next Python 软件包提供的可执行文件,
        以支持未将 Python 脚本目录加入 PATH 的环境

        Returns:
            (str | None): aria2-next 可执行文件路径, 未找到满足版本要求的可执行文件时返回 None
        """
        candidates: list[str] = []
        executable = shutil.which("aria2-next")
        if executable is not None:
            candidates.append(executable)

        try:
            aria2_next_module = importlib.import_module("aria2_next")
            candidates.append(aria2_next_module.find_aria2_next_bin())
        except ImportError:
            pass
        except (AttributeError, OSError) as e:
            logger.debug("通过 aria2-next 软件包查找可执行文件失败: %s", e)

        for candidate in dict.fromkeys(candidates):
            version = get_aria2_next_version(candidate)
            if version is None:
                logger.debug("无法获取 aria2-next 版本, 跳过: %s", candidate)
                continue
            if Version.parse(version) < Version.parse(ARIA2_NEXT_MINIMUM_VER):
                logger.warning("aria2-next 版本 %s 低于最低要求 %s, 跳过: %s", version, ARIA2_NEXT_MINIMUM_VER, candidate)
                continue
            return candidate
        return None

    def _builtin_options(
        self,
    ) -> list[str]:
        """
        获取不使用配置文件时 aria2-next 的内置启动参数

        Returns:
            list[str]: 内置启动参数列表
        """
        return [
            "--max-concurrent-downloads=16",
            "--max-connection-per-server=16",
            "--split=32",
            "--min-split-size=20M",
            "--continue=true",
            "--file-allocation=none",
            "--save-session-interval=10",
            "--connect-timeout=60",
            "--timeout=60",
            "--retry-wait=10",
            "--max-tries=5",
            "--check-certificate=false",
            "--http-accept-gzip=true",
            "--referer=*",
        ]

    def _extra_args(
        self,
    ) -> list[str]:
        """
        使用持久化的引擎状态目录, 保存断点续传进度

        Returns:
            list[str]: 额外启动参数列表
        """
        ARIA2_NEXT_STATE_PATH.mkdir(parents=True, exist_ok=True)
        return [f"--state-dir={ARIA2_NEXT_STATE_PATH.as_posix()}"]

    def _prepare_download_options(
        self,
        urls: list[str],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        """
        将 aria2 下载任务选项转换为 aria2-next 支持的选项

        - 移除 aria2-next 不支持或已弃用的选项
        - 未指定`gid`时根据保存路径生成固定的 GID, 并清理当前进程中同 GID 的已结束任务记录

        Args:
            urls (list[str]):
                下载任务的链接列表
            options (dict[str, Any]):
                aria2 下载任务选项

        Returns:
            (dict[str, Any]): 转换后的下载任务选项
        """
        prepared = dict(options)
        dropped = [key for key in ARIA2_NEXT_UNSUPPORTED_DOWNLOAD_OPTIONS if prepared.pop(key, None) is not None]
        if dropped:
            logger.debug("aria2-next 不支持以下下载选项, 已忽略: %s", ", ".join(dropped))

        if "gid" not in prepared:
            save_dir = Path(prepared.get("dir", self.download_dir))
            save_name = prepared.get("out") or _filename_from_url(urls[0])
            gid = make_download_gid(save_dir / save_name)
            prepared["gid"] = gid
            try:
                # 同一进程内重复下载同一文件时, 需要先移除已结束任务的记录才能复用 GID
                self._rpc_call("aria2.removeDownloadResult", [gid], retry_count=1)
            except RuntimeError:
                pass
        return prepared


def get_aria2_next_version(
    executable: str,
) -> str | None:
    """
    获取 aria2-next 可执行文件的版本号

    Args:
        executable (str):
            aria2-next 可执行文件路径

    Returns:
        (str | None): 版本号, 获取失败时返回 None
    """
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=30,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.debug("获取 aria2-next 版本失败: %s", e)
        return None

    version_match = re.search(r"aria2[ -]next version (\d+\.\d+\.\d+)", result.stdout, flags=re.IGNORECASE)
    return version_match.group(1) if version_match else None


def make_download_gid(
    save_path: Path,
) -> str:
    """
    根据保存路径生成固定的 aria2 GID

    aria2-next 以 GID 为索引保存断点进度, 同一保存路径使用相同的 GID 才能在重新启动后续传

    Args:
        save_path (Path):
            下载文件的保存路径

    Returns:
        str: 16 位十六进制 GID
    """
    normalized_path = os.path.normcase(os.path.abspath(save_path))
    return hashlib.sha256(normalized_path.encode("utf-8")).hexdigest()[:16]
