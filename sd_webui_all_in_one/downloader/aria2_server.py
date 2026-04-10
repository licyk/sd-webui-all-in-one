import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import (
    Any,
    Literal,
)
from urllib.parse import urlparse

from sd_webui_all_in_one.utils import (
    find_port,
    is_port_in_use,
)
from sd_webui_all_in_one.downloader.types import DEFAULT_USER_AGENT
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
    ROOT_PATH,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

ARIA2_CONFIG_PATH = ROOT_PATH / "downloader" / "aria2.conf"
"""Aria2 配置文件"""


class Aria2RpcServer:
    """
    aria2 RPC 服务器管理器（上下文管理器）

    自动启动和关闭 aria2 RPC 服务器, 提供下载功能

    支持进程监控、自动重试、崩溃检测等功能

    Attributes:
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
        rpc_url (str):
            RPC 服务器 URL 地址
        process (subprocess.Popen | None):
            aria2c 进程对象
        _session_file (NamedTemporaryFile | None):
            临时会话文件
        _is_external_server (bool):
            是否连接到外部 aria2 服务器

    Examples:
        ```python
        # 使用配置文件启动（默认）
        with Aria2RpcServer(port=6800) as aria2:
            # 下载单个文件
            aria2.download("https://example.com/file.zip", save_path="/tmp")

            # 批量下载
            urls = ["https://example.com/file1.zip", "https://example.com/file2.zip"]
            aria2.download_batch(urls, save_path="/tmp")
        # 退出上下文后自动关闭服务器

        # 使用硬编码参数启动（向后兼容）
        with Aria2RpcServer(port=6800, use_config_file=False) as aria2:
            aria2.download("https://example.com/file.zip", save_path="/tmp")
        ```
    """

    def __init__(
        self,
        port: int | None = 6800,
        secret: str | None = None,
        download_dir: Path | None = None,
        log_file: Path | str | None = None,
        log_level: Literal["debug", "info", "notice", "warn", "error"] | None = "notice",
        user_agent: str | None = DEFAULT_USER_AGENT,
        use_config_file: bool | None = True,
    ) -> None:
        """
        初始化 aria2 RPC 服务器管理器

        Args:
            port (int | None):
                RPC 服务器监听端口, 默认 6800
            secret (str | None):
                RPC 密钥, 用于安全认证, 为 None 时不设置密钥
            download_dir (Path | None):
                默认下载目录, 为 None 时使用当前工作目录
            log_file (Path | None):
                日志文件路径, 为 None 时不记录日志到文件
            log_level (Literal["debug", "info", "notice", "warn", "error"] | None):
                日志级别, 可选: debug, info, notice, warn, error, 默认 "notice"
            user_agent (str | None):
                User-Agent 配置
            use_config_file (bool | None):
                是否使用配置文件启动 aria2, 默认 True
        """
        self.port: int = port
        self.secret: str | None = secret
        self.download_dir: Path = Path(download_dir) if download_dir else Path.cwd()
        self.log_file: Path | None = Path(log_file) if log_file else None
        self.log_level: str = log_level
        self.user_agent = user_agent
        self.use_config_file: bool = use_config_file
        self.rpc_url: str = f"http://localhost:{port}/jsonrpc"
        self.process: subprocess.Popen | None = None
        self._session_file: NamedTemporaryFile | None = None
        self._is_external_server: bool = False  # 标记是否连接到外部服务器

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
                self._is_external_server = True  # 标记为外部服务器
                return
            else:
                self.port = find_port(self.port)
                self.rpc_url = f"http://localhost:{self.port}/jsonrpc"  # 更新 RPC URL
                logger.debug("端口已被占用但无法连接到 aria2 RPC 服务, 尝试更换到 %d 端口创建新的 aria2 RPC 服务", self.port)

        # 创建临时会话文件
        self._session_file = NamedTemporaryFile(mode="w", suffix=".aria2.session", delete=False)
        self._session_file.close()

        # 构建启动命令
        if self.use_config_file and ARIA2_CONFIG_PATH.exists():
            # 使用配置文件启动
            cmd = [
                "aria2c",
                f"--conf-path={ARIA2_CONFIG_PATH.as_posix()}",
                f"--rpc-listen-port={self.port}",
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

            logger.debug("使用配置文件启动 aria2: %s", ARIA2_CONFIG_PATH)
        else:
            # 使用硬编码参数启动（向后兼容）
            cmd = [
                "aria2c",
                "--enable-rpc=true",
                f"--rpc-listen-port={self.port}",
                "--rpc-listen-all=false",
                "--rpc-allow-origin-all=true",
                f"--dir={self.download_dir.as_posix()}",
                "--max-concurrent-downloads=16",
                "--max-connection-per-server=16",
                "--split=16",
                "--min-split-size=1M",
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

            if not self.use_config_file:
                logger.debug("使用硬编码参数启动 aria2")
            else:
                logger.warning("配置文件不存在: %s, 使用硬编码参数启动 aria2", ARIA2_CONFIG_PATH)

        # 启动 aria2 进程
        try:
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
            except Exception:
                pass

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
            except Exception:
                pass

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
        except Exception:
            pass

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
        except Exception:
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
        consecutive_errors: int = 0  # 连续错误计数
        max_consecutive_errors: int = 5  # 最大连续错误次数

        try:
            while True:
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
