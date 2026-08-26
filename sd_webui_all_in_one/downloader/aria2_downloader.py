"""Aria2 下载工具"""

import threading
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sd_webui_all_in_one.downloader.aria2_server import Aria2RpcServer
from sd_webui_all_in_one.downloader.requests_downloader import (
    DEFAULT_MAX_CONNECTION_PER_SERVER,
    DEFAULT_MIN_SPLIT_SIZE,
    DEFAULT_PIECE_LENGTH,
    DEFAULT_SPLIT,
    _filename_from_url,
    _is_full_hash,
    _normalize_options,
    _normalize_urls,
    _resolve_existing_file_policy,
)
from sd_webui_all_in_one.downloader.types import ExistingFilePolicy, validate_download_file_name
from sd_webui_all_in_one.downloader.hash_utils import compare_hash, normalize_hash_algorithm
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class _Aria2ServerPool:
    """
    Aria2RpcServer 共享实例池

    使用引用计数管理共享的 Aria2RpcServer 实例生命周期:
    - 首次获取时自动创建并启动服务器
    - 每次获取引用计数 +1, 每次释放引用计数 -1
    - 引用计数归零时自动关闭并清理服务器实例

    线程安全, 适用于多线程并发下载场景
    """

    def __init__(
        self,
    ) -> None:
        self._lock: threading.Lock = threading.Lock()
        self._server: Aria2RpcServer | None = None
        self._ref_count: int = 0

    def acquire(self) -> Aria2RpcServer:
        """
        获取共享的 Aria2RpcServer 实例, 若不存在则创建并启动

        引用计数 +1, 线程安全

        Returns:
            Aria2RpcServer: 共享的服务器实例
        """
        with self._lock:
            if self._server is None:
                logger.debug("创建共享 Aria2RpcServer 实例")
                self._server = Aria2RpcServer(use_external_server=False)
                self._server.__enter__()  # pylint: disable=unnecessary-dunder-call

            self._ref_count += 1
            logger.debug("Aria2RpcServer 引用计数: %d", self._ref_count)
            return self._server

    def release(
        self,
    ) -> None:
        """
        释放对共享 Aria2RpcServer 实例的引用

        引用计数 -1, 若归零则关闭并清理实例, 线程安全
        """
        with self._lock:
            self._ref_count -= 1
            logger.debug("Aria2RpcServer 引用计数: %d", self._ref_count)

            if self._ref_count <= 0 and self._server is not None:
                logger.debug("所有下载任务已完成, 关闭共享 Aria2RpcServer 实例")
                try:
                    self._server.__exit__(None, None, None)
                except Exception as e:
                    logger.error("关闭共享 Aria2RpcServer 实例时出错: %s", e)
                finally:
                    self._server = None
                    self._ref_count = 0


_server_pool: _Aria2ServerPool = _Aria2ServerPool()
"""模块级共享服务器池"""


def _verify_existing_file_size(urls: list[str], save_path: Path) -> None:
    last_error: Exception | None = None
    for url in urls:
        try:
            request = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(request, timeout=60) as response:
                content_length = response.headers.get("Content-Length")
        except Exception as e:
            last_error = e
            continue
        if content_length is None:
            continue
        try:
            remote_size = int(content_length)
        except ValueError as e:
            last_error = e
            continue
        local_size = save_path.stat().st_size
        if local_size != remote_size:
            raise IOError(f"已有文件大小不匹配: 期望 {remote_size}, 实际 {local_size}")
        return
    raise ValueError(f"远端未提供可用的文件大小，无法验证已有文件: {last_error}")


def aria2(
    url: str | Sequence[str],
    path: Path | None = None,
    save_name: str | None = None,
    progress: bool = True,
    hash_prefix: str | None = None,
    hash_value: str | None = None,
    hash_algorithm: str = "sha256",
    split: int = DEFAULT_SPLIT,
    max_connection_per_server: int = DEFAULT_MAX_CONNECTION_PER_SERVER,
    min_split_size: int = DEFAULT_MIN_SPLIT_SIZE,
    piece_length: int = DEFAULT_PIECE_LENGTH,
    allow_piece_length_change: bool = False,
    continue_download: bool = False,
    max_tries: int = 5,
    retry_wait: int = 0,
    conditional_get: bool = False,
    remote_time: bool = True,
    always_resume: bool = True,
    max_resume_failure_tries: int = 0,
    existing_file_policy: ExistingFilePolicy = "resume",
    connect_timeout: int = 60,
    read_timeout: int = 60,
    lowest_speed_limit: int = 0,
    lowest_speed_time: int = 0,
    progress_callback: Any | None = None,
    cancel_event: threading.Event | None = None,
) -> Path:
    """Aria2 下载工具

    多次并发调用时共享同一个 Aria2RpcServer 实例, 所有下载任务完成后自动关闭服务器

    Args:
        url (str | Sequence[str]):
            文件下载链接或同一文件的镜像链接列表
        path (Path | None):
            下载文件的路径, 为`None`时使用当前路径
        save_name (str | None):
            保存的文件名, 为`None`时使用`url`提取保存的文件名
        progress (bool):
            是否启用下载进度条
        hash_prefix (str | None):
            兼容的 SHA-256 哈希前缀
        hash_value (str | None):
            显式完整哈希值或前缀
        hash_algorithm (str):
            hash_value 使用的算法
        split (int):
            aria2 单文件最大分割数
        max_connection_per_server (int):
            aria2 单服务器最大连接数
        min_split_size (int):
            aria2 最小切分大小
        piece_length (int):
            aria2 piece 大小
        allow_piece_length_change (bool):
            piece length 与已有控制文件不一致时, 是否允许 aria2 转换已完成 bitfield
        continue_download (bool):
            是否启用断点续传
        max_tries (int):
            最大尝试次数
        retry_wait (int):
            HTTP 503 重试前等待秒数
        conditional_get (bool):
            已有本地文件时是否启用 aria2 conditional-get
        remote_time (bool):
            是否启用 aria2 remote-time
        always_resume (bool):
            无法续传时是否继续报错而不重头下载
        max_resume_failure_tries (int):
            always_resume=False 时允许重头下载前的续传失败阈值
        existing_file_policy (ExistingFilePolicy):
            已有正式文件的处理策略

    Returns:
        Path: 下载成功时返回文件路径

    Raises:
        RuntimeError: 下载出现错误
    """
    if path is None:
        path = Path().cwd()
    if save_name is not None:
        save_name = validate_download_file_name(save_name)

    path = Path(path) if not isinstance(path, Path) and path is not None else path
    urls = _normalize_urls(url)
    display_name = save_name if save_name is not None else _filename_from_url(urls[0])
    save_path = path / display_name
    normalized_hash_algorithm = normalize_hash_algorithm(hash_algorithm) if hash_value else "sha256"
    expected_hash = hash_value or hash_prefix
    effective_existing_policy = _resolve_existing_file_policy(
        existing_file_policy,
        re_download=False,
        continue_download=continue_download,
    )
    if save_path.exists() and effective_existing_policy == "reuse":
        if expected_hash and not compare_hash(save_path, expected_hash, normalized_hash_algorithm):
            raise ValueError(f"已有文件哈希值 ({normalized_hash_algorithm}) 与预期值不匹配: {expected_hash}")
        return save_path
    if save_path.exists() and effective_existing_policy == "verify":
        if expected_hash:
            if not compare_hash(save_path, expected_hash, normalized_hash_algorithm):
                raise ValueError(f"已有文件哈希值 ({normalized_hash_algorithm}) 与预期值不匹配: {expected_hash}")
            return save_path
        _verify_existing_file_size(urls, save_path)
        return save_path
    normalized_options = _normalize_options(
        split=split,
        max_connection_per_server=max_connection_per_server,
        min_split_size=min_split_size,
        piece_length=piece_length,
        allow_piece_length_change=allow_piece_length_change,
        continue_download=continue_download,
        max_tries=max_tries,
        retry_wait=retry_wait,
        conditional_get=conditional_get,
        remote_time=remote_time,
        always_resume=always_resume,
        max_resume_failure_tries=max_resume_failure_tries,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
        lowest_speed_limit=lowest_speed_limit,
        lowest_speed_time=lowest_speed_time,
    )
    server = _server_pool.acquire()
    try:
        logger.info("下载 %s 到 %s 中", display_name, save_path)
        options: dict[str, Any] = {
            "split": str(normalized_options.split),
            "max-connection-per-server": str(normalized_options.max_connection_per_server),
            "min-split-size": str(normalized_options.min_split_size),
            "piece-length": str(normalized_options.piece_length),
            "allow-piece-length-change": "true" if normalized_options.allow_piece_length_change else "false",
            "continue": "true" if normalized_options.continue_download else "false",
            "max-tries": str(normalized_options.max_tries),
            "retry-wait": str(normalized_options.retry_wait),
            "conditional-get": "true" if normalized_options.conditional_get else "false",
            "remote-time": "true" if normalized_options.remote_time else "false",
            "always-resume": "true" if normalized_options.always_resume else "false",
            "max-resume-failure-tries": str(normalized_options.max_resume_failure_tries),
            "allow-overwrite": "true" if effective_existing_policy == "overwrite" else "false",
            "auto-file-renaming": "true" if effective_existing_policy == "rename" else "false",
            "connect-timeout": str(normalized_options.connect_timeout),
            "timeout": str(normalized_options.read_timeout),
            "lowest-speed-limit": str(normalized_options.lowest_speed_limit),
        }
        if effective_existing_policy == "resume":
            options["continue"] = "true"
        if hash_value and _is_full_hash(hash_value, normalized_hash_algorithm):
            options["checksum"] = f"{normalized_hash_algorithm}={hash_value.strip().lower()}"
        result = server.download(
            url=urls,
            save_path=path,
            save_name=save_name,
            options=options,
            show_progress=bool(progress),
            progress_callback=progress_callback,
            cancel_event=cancel_event,
        )
        if expected_hash and not compare_hash(result, expected_hash, normalized_hash_algorithm):
            raise ValueError(f"下载文件哈希值 ({normalized_hash_algorithm}) 与预期值不匹配: {expected_hash}")
        return result
    except RuntimeError as e:
        logger.error("下载 %s 时发生错误: %s", url, e)
        raise RuntimeError(e) from e
    finally:
        _server_pool.release()
