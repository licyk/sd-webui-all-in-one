"""文件下载工具"""

import os
import time
import queue
import shutil
import hashlib
import datetime
import threading
import traceback
import subprocess
import json
import urllib.request
import urllib.error
from pathlib import Path
from urllib.parse import urlparse
from tempfile import (
    TemporaryDirectory,
    NamedTemporaryFile,
)
from typing import (
    Any,
    Callable,
    Literal,
    TypeAlias,
    get_args,
)

from sd_webui_all_in_one.utils import (
    find_port,
    is_port_in_use,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    RETRY_TIMES,
    LOGGER_NAME,
)
from sd_webui_all_in_one.retry_decorator import retryable
from sd_webui_all_in_one.file_operations.archive_manager import extract_archive
from sd_webui_all_in_one.custom_exceptions import AggregateError


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

DownloadToolType: TypeAlias = Literal["aria2", "requests", "urllib"]
"""可用的下载器类型"""

DOWNLOAD_TOOL_TYPE_LIST: list[str] = list(get_args(DownloadToolType))
"""可用的下载器类型列表"""


class MultiThreadDownloader:
    """通用多线程下载器

    Attributes:
        download_func (Callable):
            执行下载任务的函数
        download_args_list (list[Any]):
            传入下载函数的位置参数列表
        download_kwargs_list (list[dict[str, Any]]):
            传入下载函数的关键字参数列表
        queue (queue.Queue):
            任务队列, 用于存储待执行的下载任务
        total_tasks (int):
            总的下载任务数
        completed_count (int):
            已完成的任务数
        lock (threading.Lock):
            线程锁, 用于保护对计数器的访问
        retry (int | None):
            重试次数
        start_time (datetime.datetime | None):
            下载开始时间
        error_list (list[Exception]):
            错误列表
    """

    def __init__(
        self,
        download_func: Callable,
        download_args_list: list[Any] | None = None,
        download_kwargs_list: list[dict[str, Any]] | None = None,
    ) -> None:
        """多线程下载器初始化

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
        Args:
            download_func (Callable): 执行下载任务的函数
            download_args_list (list[Any]): 传入下载函数的参数列表
            download_kwargs_list (list[dict[str, Any]]): 传入下载函数的参数字典列表
        """
        self.download_func = download_func
        self.download_args_list = download_args_list or []
        self.download_kwargs_list = download_kwargs_list or []
        self.queue = queue.Queue()
        self.total_tasks = max(len(download_args_list or []), len(download_kwargs_list or []))  # 记录总的下载任务数 (以参数列表长度为准)
        self.completed_count = 0  # 记录已完成的任务数
        self.lock = threading.Lock()  # 创建锁以保护对计数器的访问
        self.retry: int | None = None
        self.start_time: datetime.datetime | None = None
        self.error_list: list[Exception] = []

    def worker(
        self,
    ) -> None:
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
                    self.error_list.append(e)
                    traceback.print_exc()
                    logger.error("[%s/%s] 执行 %s 时发生错误: %s", count, self.retry, self.download_func, e)
                    if count < self.retry:
                        logger.warning("[%s/%s] 重试执行中", count, self.retry)
                    else:
                        logger.error("[%s/%s] %s 已达到最大重试次数", count, self.retry, self.download_func)

            self.queue.task_done()
            with self.lock:  # 访问共享资源时加锁
                self.completed_count += 1
                self.print_progress()  # 打印进度

    def print_progress(
        self,
    ) -> None:
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
            estimated_remaining_time = datetime.timedelta(seconds=estimated_remaining_time_seconds)
            estimated_hours = estimated_remaining_time.seconds // 3600
            estimated_minutes = (estimated_remaining_time.seconds // 60) % 60
            estimated_seconds = estimated_remaining_time.seconds % 60
            formatted_estimated_time = f"{estimated_hours:02}:{estimated_minutes:02}:{estimated_seconds:02}"
        else:
            formatted_estimated_time = "N/A"

        logger.info("下载进度: %.2f%% | %d/%d [%s<%s, %.2f it/s]", progress, self.completed_count, self.total_tasks, formatted_time, formatted_estimated_time, speed)

    def start(
        self,
        num_threads: int | None = 16,
        retry_count: int | None = 3,
    ) -> None:
        """启动多线程下载器

        Args:
            num_threads (int): 下载线程数, 默认为 16
            retry (int): 重试次数, 默认为 3

        Raises:
            AggregateError:
                下载任务出现错误时
        """

        # 将重试次数作为属性传递给下载函数
        self.retry = retry_count

        threads: list[threading.Thread] = []
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
            args = self.download_args_list[i] if i < len(self.download_args_list) else []

            # 获取关键字参数
            kwargs = self.download_kwargs_list[i] if i < len(self.download_kwargs_list) else {}

            # 将任务参数打包
            self.queue.put((args, kwargs))

        # 等待所有任务完成
        self.queue.join()

        # 停止所有工作线程
        for _ in range(num_threads):
            self.queue.put(None)

        for thread in threads:
            thread.join()

        if self.error_list:
            raise AggregateError("执行多线程下载任务时发生了错误", self.error_list)
        else:
            logger.info("多线程下载任务运行结束")


DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
"""默认 User-Agent 配置"""


class Aria2RpcServer:
    """
    aria2 RPC 服务器管理器（上下文管理器）

    自动启动和关闭 aria2 RPC 服务器, 提供下载功能

    Attributes:
        port (int):
            RPC 服务器监听端口
        secret (str | None):
            RPC 密钥, 用于安全认证
        max_concurrent_downloads (int):
            最大并发下载数
        max_connection_per_server (int):
            每个服务器的最大连接数
        split (int):
            分段下载数
        min_split_size (str):
            最小分段大小
        download_dir (Path):
            默认下载目录
        log_file (Path | None):
            日志文件路径
        log_level (str):
            日志级别
        rpc_url (str):
            RPC 服务器 URL 地址
        process (subprocess.Popen | None):
            aria2c 进程对象
        _session_file (NamedTemporaryFile | None):
            临时会话文件

    Examples:
        ```python
        with Aria2RpcServer(port=6800) as aria2:
            # 下载单个文件
            aria2.download("https://example.com/file.zip", save_path="/tmp")

            # 批量下载
            urls = ["https://example.com/file1.zip", "https://example.com/file2.zip"]
            aria2.download_batch(urls, save_path="/tmp")
        # 退出上下文后自动关闭服务器
        ```
    """

    def __init__(
        self,
        port: int | None = 6800,
        secret: str | None = None,
        max_concurrent_downloads: int | None = 16,
        max_connection_per_server: int | None = 16,
        split: int | None = 16,
        min_split_size: str | None = "1M",
        download_dir: Path | None = None,
        log_file: Path | str | None = None,
        log_level: Literal["debug", "info", "notice", "warn", "error"] | None = "notice",
        user_agent: str | None = DEFAULT_USER_AGENT,
    ) -> None:
        """
        初始化 aria2 RPC 服务器管理器

        Args:
            port (int | None):
                RPC 服务器监听端口, 默认 6800
            secret (str | None):
                RPC 密钥, 用于安全认证, 为 None 时不设置密钥
            max_concurrent_downloads (int | None):
                最大并发下载数, 默认 16
            max_connection_per_server (int | None):
                每个服务器的最大连接数, 默认 16
            split (int | None):
                分段下载数, 默认 16
            min_split_size (str | None):
                最小分段大小, 默认 "1M"
            download_dir (Path | None):
                默认下载目录, 为 None 时使用当前工作目录
            log_file (Path | None):
                日志文件路径, 为 None 时不记录日志到文件
            log_level (Literal["debug", "info", "notice", "warn", "error"] | None):
                日志级别, 可选: debug, info, notice, warn, error, 默认 "notice"
            user_agent (str | None):
                User-Agent 配置
        """
        self.port: int = port
        self.secret: str | None = secret
        self.max_concurrent_downloads: int = max_concurrent_downloads
        self.max_connection_per_server: int = max_connection_per_server
        self.split: int = split
        self.min_split_size: str = min_split_size
        self.download_dir: Path = Path(download_dir) if download_dir else Path.cwd()
        self.log_file: Path | None = Path(log_file) if log_file else None
        self.log_level: str = log_level
        self.user_agent = user_agent
        self.rpc_url: str = f"http://localhost:{port}/jsonrpc"
        self.process: subprocess.Popen | None = None
        self._session_file: NamedTemporaryFile | None = None

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
                未找到 aria2c 命令或服务器启动超时
        """

        # 检查 aria2c 是否可用
        if shutil.which("aria2c") is None:
            raise RuntimeError("未找到 aria2c 命令, 请先安装 aria2")

        # 检查端口是否已被占用
        if is_port_in_use(self.port):
            logger.debug("端口 %d 已被占用, 尝试连接现有服务", self.port)
            if self._test_connection():
                logger.debug("成功连接到现有 aria2 RPC 服务")
                return
            else:
                self.port = find_port(self.port)
                logger.debug("端口 %s 已被占用但无法连接到 aria2 RPC 服务, 尝试更换到 %s 端口创建新的 aria2 RPC 服务", self.port, self.port)

        # 创建临时会话文件
        self._session_file = NamedTemporaryFile(mode="w", suffix=".aria2.session", delete=False)
        self._session_file.close()

        # 构建启动命令
        cmd = [
            "aria2c",
            "--enable-rpc=true",
            f"--rpc-listen-port={self.port}",
            "--rpc-listen-all=false",
            "--rpc-allow-origin-all=true",
            f"--dir={self.download_dir.as_posix()}",
            f"--max-concurrent-downloads={self.max_concurrent_downloads}",
            f"--max-connection-per-server={self.max_connection_per_server}",
            f"--split={self.split}",
            f"--min-split-size={self.min_split_size}",
            "--continue=true",
            "--file-allocation=none",
            "--console-log-level=error",
            f"--log-level={self.log_level}",
            f"--save-session={self._session_file.name}",
            "--save-session-interval=10",
            "--connect-timeout=60",
            "--timeout=60",
            "--retry-wait=10",
            "--max-tries=5",
            "--check-certificate=false",
            "--http-accept-gzip=true",
            "--referer=*",
            f"--user-agent={self.user_agent}",
        ]

        if self.secret:
            cmd.append(f"--rpc-secret={self.secret}")

        if self.log_file:
            cmd.append(f"--log={self.log_file.as_posix()}")

        # 启动 aria2 进程
        try:
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)

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
        if self.process is None:
            return

        try:
            # 尝试通过 RPC 优雅关闭
            try:
                self._rpc_call("aria2.shutdown")
                logger.debug("已发送关闭信号到 aria2 RPC 服务器")
            except Exception:
                pass

            # 等待进程结束
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.debug("aria2 进程未响应, 强制终止")
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
            except Exception:
                pass

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
        except Exception:
            return False

    def _rpc_call(
        self,
        method: str,
        params: list[Any] | None = None,
    ) -> Any:
        """
        调用 aria2 RPC 方法

        Args:
            method (str):
                RPC 方法名
            params (list[Any] | None):
                方法参数列表

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

        request = urllib.request.Request(self.rpc_url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                result: dict[str, Any] = json.loads(response.read().decode("utf-8"))

                # 检查 RPC 错误
                if "error" in result:
                    error: dict[str, Any] = result["error"]
                    raise RuntimeError(f"RPC Error {error['code']}: {error['message']}")

                return result.get("result")

        except urllib.error.URLError as e:
            raise RuntimeError(f"无法连接到 aria2 RPC 服务器: {e}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON 解析错误: {e}") from e

    def download(
        self,
        url: str,
        save_path: Path | None = None,
        save_name: str | None = None,
        options: dict[str, Any] | None = None,
        show_progress: bool = True,
        wait_complete: bool = True,
    ) -> Path:
        """
        下载单个文件

        Args:
            url (str):
                下载链接
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

        Returns:
            Path: 下载文件的路径

        Raises:
            RuntimeError: 添加下载任务失败
        """
        if save_path is None:
            save_path = self.download_dir

        if save_name is None:
            parts = urlparse(url)
            save_name = os.path.basename(parts.path)
            if not save_name:
                save_name = "download"

        # 构建下载选项
        download_options: dict[str, Any] = {
            "dir": save_path.as_posix(),
            "out": save_name,
        }

        if options:
            download_options.update(options)

        # 添加下载任务
        try:
            gid: str = self._rpc_call("aria2.addUri", [[url], download_options])
            logger.debug("下载任务已创建, GID: %s, 文件: %s", gid, save_name)
        except Exception as e:
            raise RuntimeError(f"添加下载任务失败: {e}") from e

        if not wait_complete:
            return save_path / save_name

        # 等待下载完成并显示进度
        return self._wait_download(gid, save_name, show_progress)

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

        pbar: Any = None
        try:
            while True:
                # 查询下载状态
                status: dict[str, Any] = self._rpc_call("aria2.tellStatus", [gid])

                total: int = int(status.get("totalLength", 0))
                completed: int = int(status.get("completedLength", 0))
                current_status: str = status.get("status", "unknown")

                # 初始化进度条
                if show_progress and pbar is None and total > 0:
                    pbar: tqdm = tqdm(total=total, unit="B", unit_scale=True, unit_divisor=1024, desc=file_name, initial=completed)

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

                time.sleep(0.5)  # 每 0.5 秒更新一次

        except KeyboardInterrupt:
            if pbar is not None:
                pbar.close()
            logger.warning("下载被用户中断, GID: %s", gid)
            # 尝试暂停任务
            try:
                self._rpc_call("aria2.pause", [gid])
            except Exception:
                pass
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
        params: list[str] = [gid]
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


def aria2(
    url: str,
    path: Path | None = None,
    save_name: str | None = None,
    progress: bool | None = True,
) -> Path:
    """Aria2 下载工具

    Args:
        url (str):
            文件下载链接
        path (Path | None):
            下载文件的路径, 为`None`时使用当前路径
        save_name (str | None):
            保存的文件名, 为`None`时使用`url`提取保存的文件名
        progress (bool | None):
            是否启用下载进度条

    Returns:
        Path: 下载成功时返回文件路径

    Raises:
        RuntimeError: 下载出现错误
    """
    if path is None:
        path = Path().cwd()

    path = Path(path) if not isinstance(path, Path) and path is not None else path
    if save_name is None:
        parts = urlparse(url)
        save_name = os.path.basename(parts.path)

    save_path = path / save_name
    try:
        logger.info("下载 %s 到 %s 中", os.path.basename(url), save_path)
        with Aria2RpcServer() as aria2_server:
            return aria2_server.download(
                url=url,
                save_path=path,
                show_progress=progress,
            )
    except RuntimeError as e:
        logger.error("下载 %s 时发生错误: %s", url, e)
        raise RuntimeError(e) from e


def download_file_from_url(
    url: str,
    save_path: Path | None = None,
    file_name: str | None = None,
    progress: bool | None = True,
    hash_prefix: str | None = None,
    re_download: bool | None = False,
) -> Path:
    """使用 requrests 库下载文件

    Args:
        url (str):
            下载链接
        save_path (Path | None):
            下载路径
        file_name (str | None):
            保存的文件名, 如果为`None`则从`url`中提取文件
        progress (bool | None):
            是否启用下载进度条
        hash_prefix (str | None):
            sha256 十六进制字符串, 如果提供, 将检查下载文件的哈希值是否与此前缀匹配, 当不匹配时引发`ValueError`
        re_download (bool):
            强制重新下载文件

    Returns:
        Path: 下载的文件路径

    Raises:
        ValueError: 当提供了 hash_prefix 但文件哈希值不匹配时
    """
    import requests

    try:
        from tqdm import tqdm
    except ImportError:
        from sd_webui_all_in_one.simple_tqdm import SimpleTqdm as tqdm

    if save_path is None:
        save_path = Path.cwd()

    if not file_name:
        parts = urlparse(url)
        file_name = Path(parts.path).name

    cached_file = save_path.resolve() / file_name

    if re_download or not cached_file.exists():
        save_path.mkdir(parents=True, exist_ok=True)
        temp_file = save_path / f"{file_name}.tmp"
        logger.info("下载 '%s' 到 '%s' 中", file_name, cached_file)
        response = requests.get(url, stream=True, timeout=60)
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

        if hash_prefix and not compare_sha256(temp_file, hash_prefix):
            logger.error("'%s' 的哈希值不匹配, 正在删除临时文件", temp_file)
            temp_file.unlink()
            raise ValueError(f"文件哈希值与预期的哈希前缀不匹配: {hash_prefix}")

        temp_file.rename(cached_file)
        logger.info("'%s' 下载完成", file_name)
    else:
        logger.info("'%s' 已存在于 '%s' 中", file_name, cached_file)
    return cached_file


def download_file_from_url_urllib(
    url: str,
    save_path: Path | None = None,
    file_name: str | None = None,
    progress: bool | None = True,
    hash_prefix: str | None = None,
    re_download: bool | None = False,
) -> Path:
    """使用 urllib 库下载文件

    Args:
        url (str):
            下载链接
        save_path (Path | None):
            下载路径
        file_name (str | None):
            保存的文件名, 如果为`None`则从`url`中提取文件
        progress (bool | None):
            是否启用下载进度条
        hash_prefix (str | None):
            sha256 十六进制字符串, 如果提供, 将检查下载文件的哈希值是否与此前缀匹配, 当不匹配时引发`ValueError`
        re_download (bool):
            强制重新下载文件

    Returns:
        Path: 下载的文件路径

    Raises:
        ValueError: 当提供了 hash_prefix 但文件哈希值不匹配时
    """

    try:
        from tqdm import tqdm
    except ImportError:
        from sd_webui_all_in_one.simple_tqdm import SimpleTqdm as tqdm

    if save_path is None:
        save_path = Path.cwd()

    if not file_name:
        parts = urlparse(url)
        file_name = Path(parts.path).name

    cached_file = save_path.resolve() / file_name

    if re_download or not cached_file.exists():
        save_path.mkdir(parents=True, exist_ok=True)
        temp_file = save_path / f"{file_name}.tmp"
        logger.info("下载 '%s' 到 '%s' 中", file_name, cached_file)

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            total_size = int(response.getheader("Content-Length", 0))
            with tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=file_name,
                disable=not progress,
            ) as progress_bar:
                with open(temp_file, "wb") as file:
                    while True:
                        chunk = response.read(1024)
                        if not chunk:
                            break
                        file.write(chunk)
                        progress_bar.update(len(chunk))

        if hash_prefix and not compare_sha256(temp_file, hash_prefix):
            logger.error("'%s' 的哈希值不匹配, 正在删除临时文件", temp_file)
            temp_file.unlink()
            raise ValueError(f"文件哈希值与预期的哈希前缀不匹配: {hash_prefix}")

        temp_file.rename(cached_file)
        logger.info("'%s' 下载完成", file_name)
    else:
        logger.info("'%s' 已存在于 '%s' 中", file_name, cached_file)
    return cached_file


def compare_sha256(
    file_path: str | Path,
    hash_prefix: str,
) -> bool:
    """检查文件的 sha256 哈希值是否与给定的前缀匹配

    Args:
        file_path (str | Path): 文件路径
        hash_prefix (str): 哈希前缀
    Returns:
        bool: 匹配结果
    """
    hash_sha256 = hashlib.sha256()
    blksize = 1024 * 1024

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(blksize), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest().startswith(hash_prefix.strip().lower())


@retryable(
    times=RETRY_TIMES,
    describe="执行下载器",
    catch_exceptions=(IOError, RuntimeError, ValueError),
    raise_exception=(RuntimeError),
    retry_on_none=False,
)
def download_executer(
    url: str,
    path: Path,
    save_name: str | None,
    tool: DownloadToolType,
    progress: bool,
) -> Path:
    """底层下载执行器

    Args:
        url (str):
            下载链接
        path (Path):
            保存路径
        save_name (str | None):
            保存名称
        tool (DownloadToolType):
            工具名称
        progress (bool):
            是否显示进度

    Returns:
        Path:
            成功返回路径
    """
    if tool == "aria2":
        return aria2(url=url, path=path, save_name=save_name, progress=progress)
    elif tool == "requests":
        return download_file_from_url(url=url, save_path=path, file_name=save_name, progress=progress)
    elif tool == "urllib":
        return download_file_from_url_urllib(url=url, save_path=path, file_name=save_name, progress=progress)
    return None


def download_file(
    url: str,
    path: Path | None = None,
    save_name: str | None = None,
    tool: DownloadToolType | None = "aria2",
    progress: bool | None = True,
) -> Path:
    """下载文件工具

    Args:
        url (str):
            文件下载链接
        path (Path | None):
            文件下载路径
        save_name (str | None):
            文件保存名称
        tool (DownloadToolType | None):
            下载工具
        progress (bool | None):
            是否启用下载进度条

    Returns:
        Path: 保存的文件路径
    """
    path.mkdir(parents=True, exist_ok=True)

    selected_tool = str(tool)
    if selected_tool == "aria2" and shutil.which("aria2c") is None:
        logger.warning("未安装 Aria2, 将切换到 requests 进行下载")
        selected_tool = "requests"

    try:
        if selected_tool == "requests":
            import requests

            _ = requests
    except ImportError:
        logger.warning("未安装 requests, 将切换到 urllib 进行下载")
        selected_tool = "urllib"

    return download_executer(url=url, path=path, save_name=save_name, tool=selected_tool, progress=progress)


def download_archive_and_unpack(
    url: str,
    local_dir: Path,
    name: str | None = None,
) -> None:
    """下载压缩包并解压到指定路径

    Args:
        url (str):
            压缩包下载链接, 压缩包支持的格式: .zip, .7z, .rar, .tar, .tar.Z, .tar.lz, .tar.lzma, .tar.bz2, .tar.7z, .tar.gz, .tar.xz, .tar.zst
        local_dir (Path):
            下载路径
        name (str | None):
            下载文件保存的名称, 为`None`时从`url`解析文件名

    Raises:
        RuntimeError:
            下载并解压压缩包时发生错误时
    """
    with TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        if name is None:
            parts = urlparse(url)
            name = os.path.basename(parts.path)

        try:
            origin_file_path = download_file(
                url=url,
                path=path,
                save_name=name,
            )
            logger.info("解压 %s 到 %s 中", name, local_dir)
            extract_archive(
                archive_path=origin_file_path,
                extract_to=local_dir,
            )
            logger.info("%s 解压完成, 路径: %s", name, local_dir)
        except Exception as e:
            logger.error("解压 %s 时发生错误: %s", name, e)
            raise RuntimeError(f"下载 {name} 并解压压缩包时发生错误: {e}") from e
