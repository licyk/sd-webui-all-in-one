"""Requests 下载器共享模型、错误和目标文件策略。"""

import hashlib
import os
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from sd_webui_all_in_one.downloader.hash_utils import compare_hash, normalize_hash_algorithm
from sd_webui_all_in_one.downloader.types import EXISTING_FILE_POLICY_LIST, ExistingFilePolicy


DEFAULT_SPLIT = 32
"""aria2 风格的单文件最大分割数"""

DEFAULT_MAX_CONNECTION_PER_SERVER = 16
"""aria2 风格的单服务器最大连接数"""

DEFAULT_MIN_SPLIT_SIZE = 20 * 1024 * 1024
"""aria2 风格的最小切分大小"""

DEFAULT_PIECE_LENGTH = 1024 * 1024
"""aria2 风格的 piece 大小"""

MAX_CONNECTION_PER_SERVER_MAX = 16
"""aria2 max-connection-per-server 上限"""

ARIA2_SIZE_OPTION_MIN = 1024 * 1024
"""aria2 min-split-size/piece-length 下限"""

ARIA2_SIZE_OPTION_MAX = 1024 * 1024 * 1024
"""aria2 min-split-size/piece-length 上限"""

STREAM_CHUNK_SIZE = 1024 * 1024
"""HTTP 响应读取块大小"""

STATE_SAVE_COMPLETED_PIECE_INTERVAL = 8
"""断点续传状态写入间隔"""

STATE_SAVE_INTERVAL_SECONDS = 10.0
"""低速下载的断点续传状态最长写入间隔"""

STATE_VERSION = 5
"""HTTP Range 断点续传 JSON 状态版本"""

IN_FLIGHT_BLOCK_LENGTH = 16 * 1024
"""aria2 Piece 默认 block 大小"""

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
"""分片下载时可重试的 HTTP 状态码"""

_TARGET_PATH_LOCKS: dict[Path, tuple[threading.Lock, int]] = {}
_TARGET_PATH_LOCKS_GUARD = threading.Lock()


class DownloadError:
    """requests 下载器结构化错误基类"""


class DownloadConfigurationError(ValueError, DownloadError):
    """参数或路径配置错误"""


class DownloadStateError(RuntimeError, DownloadError):
    """断点状态损坏或不兼容"""


class DownloadTransientError(IOError, DownloadError):
    """允许在当前请求预算内重试的临时错误"""


class DownloadIntegrityError(ValueError, DownloadError):
    """大小、Digest 或调用者哈希校验失败"""


class DownloadSizeIntegrityError(IOError, DownloadError):
    """文件大小校验失败"""


class DownloadPermanentHttpError(RuntimeError, DownloadError):
    """不应重试的 HTTP 响应错误"""

    def __init__(
        self,
        *,
        url: str,
        status_code: int,
        segment: tuple[int, int] | None,
        attempt: int,
    ) -> None:
        self.url = url
        self.status_code = status_code
        self.segment = segment
        self.attempt = attempt
        segment_text = f", segment={segment}" if segment is not None else ""
        super().__init__(f"永久 HTTP 错误: url={url}, status={status_code}{segment_text}, attempt={attempt}")


class DownloadCancelledError(IOError, DownloadError):
    """下载任务被调用者取消"""


class DownloadLowSpeedError(DownloadTransientError):
    """连接在指定窗口内持续低于最低速度"""


class DownloadConnectTimeoutError(DownloadTransientError):
    """建立连接超时"""


class DownloadReadTimeoutError(DownloadTransientError):
    """读取响应数据超时"""


def _classify_network_error(error: Exception) -> Exception:
    error_name = type(error).__name__.lower()
    if "connecttimeout" in error_name:
        return DownloadConnectTimeoutError(f"建立连接超时: {error}")
    if "readtimeout" in error_name:
        return DownloadReadTimeoutError(f"读取响应超时: {error}")
    return error


class _RangeDownloadNotSupported(RuntimeError, DownloadError):
    """远端不支持可靠的 HTTP Range 下载"""


class _ResumeStateError(DownloadStateError):
    """断点续传状态文件不可恢复"""


def _lock_path_for(target_file: Path) -> Path:
    return target_file.with_name(f".{target_file.name}.download.lock")


def _windows_mutex_name(target_file: Path) -> str:
    normalized_path = os.path.normcase(str(target_file))
    path_digest = hashlib.sha256(os.fsencode(normalized_path)).hexdigest()
    return f"Local\\sd-webui-all-in-one-download-{path_digest}"


def _resolve_existing_file_policy(
    existing_file_policy: ExistingFilePolicy | None,
    *,
    re_download: bool,
    continue_download: bool,
) -> ExistingFilePolicy:
    if re_download:
        return "overwrite"
    if existing_file_policy is not None:
        if existing_file_policy not in EXISTING_FILE_POLICY_LIST:
            raise DownloadConfigurationError(f"不支持的已有文件处理策略: {existing_file_policy}")
        return existing_file_policy
    if continue_download:
        return "resume"
    return "reuse"


def _renamed_file_path(cached_file: Path) -> Path:
    index = 1
    while True:
        candidate = cached_file.with_name(f"{cached_file.stem} ({index}){cached_file.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def _is_full_hash(value: str | None, algorithm: str) -> bool:
    if not value:
        return False
    normalized = value.strip()
    expected_length = {"sha1": 40, "sha256": 64, "sha512": 128}[normalize_hash_algorithm(algorithm)]
    return len(normalized) == expected_length and all(char in "0123456789abcdefABCDEF" for char in normalized)


def _verify_existing_file(
    cached_file: Path,
    *,
    remote_info: "_RemoteFileInfo",
    hash_prefix: str | None,
) -> None:
    expected_hash = hash_prefix or remote_info.digest_value
    expected_algorithm = "sha256" if hash_prefix else remote_info.digest_algorithm
    if expected_hash and expected_algorithm:
        if not compare_hash(cached_file, expected_hash, expected_algorithm):
            raise DownloadIntegrityError(f"已有文件哈希值 ({expected_algorithm}) 与预期值不匹配: {expected_hash}")
        return
    if remote_info.total_size <= 0:
        raise ValueError("远端未提供大小或哈希，无法验证已有文件")
    actual_size = cached_file.stat().st_size
    if actual_size != remote_info.total_size:
        raise DownloadSizeIntegrityError(f"已有文件大小不匹配: 期望 {remote_info.total_size}, 实际 {actual_size}")


@contextmanager
def _posix_target_download_lock(lock_path: Path) -> Iterator[None]:
    """获取可安全删除的 POSIX 文件锁。"""
    import fcntl

    while True:
        lock_file = lock_path.open("a+b")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                lock_path_stat = lock_path.stat()
            except FileNotFoundError:
                pass
            else:
                if os.path.samestat(os.fstat(lock_file.fileno()), lock_path_stat):
                    break
        except BaseException:
            lock_file.close()
            raise
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()

    try:
        yield
    finally:
        try:
            lock_path.unlink(missing_ok=True)
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()


@contextmanager
def _windows_target_download_lock(target_file: Path) -> Iterator[None]:
    """使用 Windows 命名互斥量协调同一目标，不创建磁盘锁文件。"""
    import ctypes
    from ctypes import wintypes

    win_dll = getattr(ctypes, "WinDLL")
    win_error = getattr(ctypes, "WinError")
    get_last_error = getattr(ctypes, "get_last_error")
    kernel32 = win_dll("kernel32.dll", use_last_error=True)
    kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
    kernel32.ReleaseMutex.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL

    mutex_handle = kernel32.CreateMutexW(None, False, _windows_mutex_name(target_file))
    if not mutex_handle:
        raise win_error(get_last_error())

    wait_result = kernel32.WaitForSingleObject(mutex_handle, 0xFFFFFFFF)
    if wait_result not in {0x00000000, 0x00000080}:
        error = win_error(get_last_error())
        kernel32.CloseHandle(mutex_handle)
        raise error

    try:
        yield
    finally:
        try:
            if not kernel32.ReleaseMutex(mutex_handle):
                raise win_error(get_last_error())
        finally:
            kernel32.CloseHandle(mutex_handle)


@contextmanager
def _target_download_lock(target_file: Path) -> Iterator[None]:
    """同一目标采用等待语义，并通过系统锁覆盖跨进程任务。"""
    normalized_target = target_file.resolve()
    with _TARGET_PATH_LOCKS_GUARD:
        path_lock, users = _TARGET_PATH_LOCKS.get(normalized_target, (threading.Lock(), 0))
        _TARGET_PATH_LOCKS[normalized_target] = (path_lock, users + 1)

    path_lock.acquire()
    try:
        if os.name == "nt":
            with _windows_target_download_lock(normalized_target):
                yield
        else:
            lock_path = _lock_path_for(normalized_target)
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            with _posix_target_download_lock(lock_path):
                yield
    finally:
        path_lock.release()
        with _TARGET_PATH_LOCKS_GUARD:
            current_lock, users = _TARGET_PATH_LOCKS[normalized_target]
            if users == 1:
                del _TARGET_PATH_LOCKS[normalized_target]
            else:
                _TARGET_PATH_LOCKS[normalized_target] = (current_lock, users - 1)


class _PieceLengthChangedError(_ResumeStateError):
    """控制文件中的 piece length 与当前配置不同"""


class _RangeRequestIgnored(_RangeDownloadNotSupported):
    """远端忽略了非零起点的 Range 请求"""


class _RangeDownloadTemporaryError(DownloadTransientError):
    """分片下载过程中的可重试错误"""

    def __init__(
        self,
        message: str,
        retry_delay: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_delay = retry_delay


class _SegmentDownloadError(RuntimeError):
    """下载流在某个 segment 上失败"""

    def __init__(
        self,
        segment: "_Segment",
        error: Exception,
    ) -> None:
        super().__init__(str(error))
        self.segment = segment
        self.error = error


class _SegmentOwnershipLost(RuntimeError):
    """Segment 已被另一个 idle worker 接管"""


_UrlInput = str | Sequence[str]


@dataclass(frozen=True)
class _RemoteFileInfo:
    """远端文件元数据"""

    total_size: int
    supports_range: bool
    etag: str | None = None
    last_modified: str | None = None
    digest_sha256: str | None = None
    digest_algorithm: str | None = None
    digest_value: str | None = None
    content_disposition_filename: str | None = None
    content_encoding: str | None = None
    final_url: str | None = None


@dataclass(frozen=True)
class _DownloadOptions:
    """aria2 风格下载选项"""

    split: int
    max_connection_per_server: int
    min_split_size: int
    piece_length: int
    allow_piece_length_change: bool
    max_tries: int
    retry_wait: int
    continue_download: bool
    conditional_get: bool
    remote_time: bool
    always_resume: bool = True
    max_resume_failure_tries: int = 0
    connect_timeout: int = 60
    read_timeout: int = 60
    lowest_speed_limit: int = 0
    lowest_speed_time: int = 0


@dataclass(frozen=True)
class DownloadProgressEvent:
    """描述一次下载进度回调携带的状态。"""

    target_path: Path
    total_size: int
    completed_size: int
    instantaneous_speed: float
    average_speed: float
    active_connections: int
    current_url: str


@dataclass(frozen=True)
class _RemoteProbeResult:
    """多 URI 探测结果及可安全用于 Range 下载的 URI"""

    primary_url: str
    remote_info: _RemoteFileInfo
    range_urls: list[str]
    range_host_keys: dict[str, tuple[str, str, int | None]]
    resume_failure_count: int


@dataclass(frozen=True)
class _Segment:
    """连续 piece 组成的下载段"""

    start_piece: int
    end_piece: int
    start: int
    end: int
    piece_start: int
    owner_id: int = 0

    @property
    def piece_count(self) -> int:
        return self.end_piece - self.start_piece + 1

    @property
    def size(self) -> int:
        return self.end - self.start + 1

    @property
    def byte_range(self) -> tuple[int, int]:
        return self.start, self.end
