"""Requests 下载器"""

import base64
import binascii
import hashlib
import json
import math
import os
import random
import re
import shutil
import threading
import time
from collections import Counter
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from email.utils import formatdate
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from typing import cast
from urllib.parse import unquote
from urllib.parse import unquote_to_bytes
from urllib.parse import urlparse

from sd_webui_all_in_one.downloader.hash_utils import compare_hash, normalize_hash_algorithm
from sd_webui_all_in_one.downloader.types import DEFAULT_USER_AGENT, EXISTING_FILE_POLICY_LIST, ExistingFilePolicy, validate_download_file_name
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)


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


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

_CONTENT_RANGE_RE = re.compile(r"(?:bytes\s+|bytes=)?(\d+)-(\d+)/(\d+|\*)", flags=re.IGNORECASE)
_UNSATISFIED_CONTENT_RANGE_RE = re.compile(r"(?:bytes\s+|bytes=)?\*/(\d+|\*)", flags=re.IGNORECASE)

_STATE_FILE_DIGESTS: dict[Path, str] = {}
_STATE_FILE_DIGEST_LOCK = threading.Lock()
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
def _target_download_lock(target_file: Path) -> Iterator[None]:
    """同一目标采用等待语义，并通过 advisory lock 覆盖跨进程任务"""
    normalized_target = target_file.resolve()
    with _TARGET_PATH_LOCKS_GUARD:
        path_lock, users = _TARGET_PATH_LOCKS.get(normalized_target, (threading.Lock(), 0))
        _TARGET_PATH_LOCKS[normalized_target] = (path_lock, users + 1)

    path_lock.acquire()
    lock_file = None
    try:
        lock_path = _lock_path_for(normalized_target)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = lock_path.open("a+b")
        if os.name == "nt":
            import msvcrt

            if lock_file.tell() == 0:
                lock_file.write(b"\0")
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if lock_file is not None:
            try:
                if os.name == "nt":
                    import msvcrt

                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            finally:
                lock_file.close()
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


class _DigestTracker:
    """汇总 HEAD、Range probe 和实际 GET 返回的最强一致 Digest"""

    _PRIORITY = {"sha1": 1, "sha256": 2, "sha512": 3}

    def __init__(self, algorithm: str | None = None, value: str | None = None) -> None:
        self.algorithm = algorithm
        self.value = value
        self.lock = threading.Lock()

    def observe(self, digest_header: str | None) -> None:
        digest = _digest_from_header(digest_header)
        if digest is None:
            return
        algorithm, value = digest
        with self.lock:
            if self.algorithm == algorithm and self.value and self.value != value:
                raise DownloadIntegrityError(f"实际 GET 的 {algorithm} Digest 与已探测值冲突")
            if self.algorithm is None or self._PRIORITY[algorithm] > self._PRIORITY[self.algorithm]:
                self.algorithm = algorithm
                self.value = value

    def expected(self) -> tuple[str, str] | None:
        with self.lock:
            if self.algorithm and self.value:
                return self.algorithm, self.value
            return None


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


def _get_header(
    headers: Any,
    name: str,
) -> str | None:
    """从响应头中大小写不敏感地读取字段"""
    if not headers:
        return None

    getter = getattr(headers, "get", None)
    if callable(getter):
        value = getter(name)
        if value is not None:
            return str(value)

    try:
        items = headers.items()
    except AttributeError:
        return None

    lower_name = name.lower()
    for key, value in items:
        if str(key).lower() == lower_name:
            return str(value)
    return None


def _parse_int_header(
    headers: Any,
    name: str,
) -> int:
    value = _get_header(headers, name)
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _digest_from_header(
    digest_header: str | None,
) -> tuple[str, str] | None:
    if not digest_header:
        return None

    algorithms = {
        "sha-512": ("sha512", hashlib.sha512().digest_size, 3),
        "sha512": ("sha512", hashlib.sha512().digest_size, 3),
        "sha-256": ("sha256", hashlib.sha256().digest_size, 2),
        "sha256": ("sha256", hashlib.sha256().digest_size, 2),
        "sha-1": ("sha1", hashlib.sha1().digest_size, 1),
        "sha1": ("sha1", hashlib.sha1().digest_size, 1),
    }
    values: dict[str, set[str]] = {}
    priorities: dict[str, int] = {}
    for item in digest_header.split(","):
        name, separator, digest = item.strip().partition("=")
        algorithm_info = algorithms.get(name.strip().lower())
        if not separator or algorithm_info is None:
            continue
        algorithm, digest_size, priority = algorithm_info
        digest = digest.strip()
        if digest.startswith(":") and digest.endswith(":") and len(digest) >= 2:
            digest = digest[1:-1]
        try:
            raw_digest = base64.b64decode(digest, validate=True)
        except (binascii.Error, ValueError):
            continue
        if len(raw_digest) == digest_size:
            values.setdefault(algorithm, set()).add(raw_digest.hex())
            priorities[algorithm] = priority
    for algorithm, algorithm_values in values.items():
        if len(algorithm_values) > 1:
            raise DownloadIntegrityError(f"Digest 中 {algorithm} 存在冲突值")
    if not values:
        return None
    strongest = max(values, key=lambda algorithm: priorities[algorithm])
    return strongest, next(iter(values[strongest]))


def _sha256_from_digest_header(digest_header: str | None) -> str | None:
    digest = _digest_from_header(digest_header)
    return digest[1] if digest and digest[0] == "sha256" else None


def _split_content_disposition_parts(
    header: str,
) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    in_quote = False
    escaped = False
    for char in header:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if in_quote and char == "\\":
            escaped = True
            continue
        if char == '"':
            in_quote = not in_quote
            current.append(char)
            continue
        if char == ";" and not in_quote:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    parts.append("".join(current).strip())
    return parts


def _unquote_header_value(
    value: str,
) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]
        result: list[str] = []
        escaped = False
        for char in value:
            if escaped:
                result.append(char)
                escaped = False
            elif char == "\\":
                escaped = True
            else:
                result.append(char)
        value = "".join(result)
    return value


def _decode_rfc5987_value(
    value: str,
) -> str | None:
    charset, separator, rest = value.partition("'")
    if not separator:
        return None
    _language, separator, encoded = rest.partition("'")
    if not separator:
        return None
    try:
        return unquote_to_bytes(encoded).decode(charset or "utf-8")
    except (LookupError, UnicodeDecodeError, ValueError):
        return None


def _safe_content_disposition_filename(
    value: str | None,
) -> str | None:
    if value is None:
        return None
    filename = value.strip()
    try:
        return validate_download_file_name(filename)
    except ValueError:
        return None


def _filename_from_content_disposition(
    content_disposition: str | None,
) -> str | None:
    if not content_disposition:
        return None
    parts = _split_content_disposition_parts(content_disposition)
    params: dict[str, str] = {}
    for part in parts[1:]:
        name, separator, value = part.partition("=")
        if not separator:
            continue
        params[name.strip().lower()] = _unquote_header_value(value)

    extended = _decode_rfc5987_value(params["filename*"]) if "filename*" in params else None
    filename = extended if extended is not None else params.get("filename")
    return _safe_content_disposition_filename(filename)


def _filename_from_url(
    url: str,
) -> str:
    parts = urlparse(url)
    filename = unquote(Path(parts.path).name)
    return _safe_content_disposition_filename(filename) or "download"


def _parse_content_range(
    content_range: str | None,
) -> tuple[int, int, int | None] | None:
    if not content_range:
        return None

    normalized = content_range.strip()
    if _UNSATISFIED_CONTENT_RANGE_RE.match(normalized):
        return None

    match = _CONTENT_RANGE_RE.match(normalized)
    if not match:
        return None

    start = int(match.group(1))
    end = int(match.group(2))
    total = None if match.group(3) == "*" else int(match.group(3))
    return start, end, total


def _response_range_from_headers(
    headers: Any,
) -> tuple[int, int, int | None] | None:
    parsed_range = _parse_content_range(_get_header(headers, "Content-Range"))
    if parsed_range is not None:
        return parsed_range

    content_length = _parse_int_header(headers, "Content-Length")
    if content_length <= 0:
        return None
    return 0, content_length - 1, content_length


def _close_response(
    response: object,
) -> None:
    closer = getattr(response, "close", None)
    if callable(closer):
        closer()


def _request_headers(
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "Want-Digest": "SHA-512;q=1, SHA-256;q=1, SHA-1;q=1",
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def _content_encoding_requires_single_stream(
    content_encoding: str | None,
) -> bool:
    if not content_encoding:
        return False
    return any(item.strip().lower() not in {"", "identity"} for item in content_encoding.split(","))


def _normalize_urls(
    url: _UrlInput,
) -> list[str]:
    if isinstance(url, str):
        urls = [url]
    elif isinstance(url, Sequence):
        urls = list(url)
    else:
        raise ValueError("url 必须是字符串或字符串序列")

    normalized: list[str] = []
    for item in urls:
        if not isinstance(item, str):
            raise ValueError("url 序列中只能包含字符串")
        stripped = item.strip()
        if not stripped:
            raise ValueError("url 不能为空")
        normalized.append(stripped)

    if not normalized:
        raise ValueError("url 序列不能为空")
    return normalized


def _url_host_key(
    url: str,
) -> tuple[str, str, int | None]:
    parts = urlparse(url)
    return (parts.scheme.lower(), (parts.hostname or "").lower(), parts.port)


def _probe_remote_file(
    url: str,
    timeout: Any = 60,
) -> _RemoteFileInfo:
    """探测远端是否支持可靠的 HTTP Range 下载"""
    import requests

    total_size = 0
    etag: str | None = None
    last_modified: str | None = None
    digest_sha256: str | None = None
    digest_algorithm: str | None = None
    digest_value: str | None = None
    content_disposition_filename: str | None = None
    content_encoding: str | None = None
    final_url: str | None = None
    supports_range = False

    try:
        response = requests.head(url, allow_redirects=True, timeout=timeout, headers=_request_headers())
        try:
            status_code = int(response.status_code or 0)
            if 200 <= status_code < 400:
                headers = response.headers
                final_url = str(getattr(response, "url", url) or url)
                total_size = _parse_int_header(headers, "Content-Length")
                etag = _get_header(headers, "ETag")
                last_modified = _get_header(headers, "Last-Modified")
                digest = _digest_from_header(_get_header(headers, "Digest"))
                if digest:
                    digest_algorithm, digest_value = digest
                    digest_sha256 = digest_value if digest_algorithm == "sha256" else None
                content_disposition_filename = _filename_from_content_disposition(_get_header(headers, "Content-Disposition"))
                content_encoding = _get_header(headers, "Content-Encoding")
                supports_range = (_get_header(headers, "Accept-Ranges") or "").lower() == "bytes"
        finally:
            _close_response(response)
    except DownloadIntegrityError:
        raise
    except Exception as e:
        logger.debug("HEAD 探测失败, 尝试使用 Range 请求探测: %s", e)

    if not supports_range or total_size <= 0:
        try:
            response = requests.get(url, stream=True, timeout=timeout, headers=_request_headers({"Range": "bytes=0-0"}))
            try:
                status_code = int(response.status_code or 0)
                headers = response.headers
                if status_code == 206:
                    parsed = _parse_content_range(_get_header(headers, "Content-Range"))
                    if parsed is not None:
                        start, end, content_total = parsed
                        if start == 0 and end == 0 and content_total:
                            total_size = content_total
                            etag = etag or _get_header(headers, "ETag")
                            last_modified = last_modified or _get_header(headers, "Last-Modified")
                            digest = _digest_from_header(_get_header(headers, "Digest"))
                            if digest:
                                if digest_algorithm == digest[0] and digest_value and digest_value != digest[1]:
                                    raise DownloadIntegrityError(f"Range 探测的 {digest[0]} Digest 与 HEAD 冲突")
                                if digest_algorithm is None or {"sha1": 1, "sha256": 2, "sha512": 3}[digest[0]] > {"sha1": 1, "sha256": 2, "sha512": 3}[digest_algorithm]:
                                    digest_algorithm, digest_value = digest
                                    digest_sha256 = digest_value if digest_algorithm == "sha256" else None
                            content_disposition_filename = content_disposition_filename or _filename_from_content_disposition(_get_header(headers, "Content-Disposition"))
                            content_encoding = content_encoding or _get_header(headers, "Content-Encoding")
                            final_url = str(getattr(response, "url", url) or url)
                            supports_range = True
            finally:
                _close_response(response)
        except DownloadIntegrityError:
            raise
        except Exception as e:
            logger.debug("Range 探测失败, 将使用单连接下载: %s", e)

    if _content_encoding_requires_single_stream(content_encoding):
        total_size = 0
        supports_range = False

    return _RemoteFileInfo(
        total_size=total_size,
        supports_range=supports_range and total_size > 0,
        etag=etag,
        last_modified=last_modified,
        digest_sha256=digest_sha256,
        digest_algorithm=digest_algorithm,
        digest_value=digest_value,
        content_disposition_filename=content_disposition_filename,
        content_encoding=content_encoding,
        final_url=final_url or url,
    )


def _probe_remote_files(
    urls: list[str],
    timeout: Any = 60,
) -> _RemoteProbeResult:
    first_result: tuple[str, _RemoteFileInfo] | None = None
    first_sized_result: tuple[str, _RemoteFileInfo] | None = None
    range_results: list[tuple[str, _RemoteFileInfo]] = []
    integrity_errors: list[tuple[str, DownloadIntegrityError]] = []
    for url in urls:
        try:
            remote_info = _probe_remote_file(url, timeout=timeout)
        except DownloadIntegrityError as e:
            integrity_errors.append((url, e))
            logger.warning("隔离 Digest 探测冲突的镜像 %s: %s", url, e)
            continue
        if first_result is None:
            first_result = (url, remote_info)
        if first_sized_result is None and remote_info.total_size > 0:
            first_sized_result = (url, remote_info)
        if remote_info.supports_range and remote_info.total_size > 0:
            range_results.append((url, remote_info))
    if first_result is None:
        if integrity_errors:
            url, error = integrity_errors[-1]
            raise DownloadIntegrityError(f"所有镜像的 Digest 探测均失败，最后镜像 {url}: {error}") from error
        raise ValueError("url 序列不能为空")

    primary_url, remote_info = range_results[0] if range_results else first_sized_result or first_result
    range_urls: list[str] = []
    for candidate_url, candidate_info in range_results:
        if candidate_info.total_size != remote_info.total_size:
            logger.warning("忽略大小不一致的镜像 %s: 期望 %s, 实际 %s", candidate_url, remote_info.total_size, candidate_info.total_size)
            continue
        primary_etag = remote_info.etag if remote_info.etag and not remote_info.etag.strip().startswith("W/") else None
        candidate_etag = candidate_info.etag if candidate_info.etag and not candidate_info.etag.strip().startswith("W/") else None
        if (
            remote_info.digest_algorithm
            and remote_info.digest_algorithm == candidate_info.digest_algorithm
            and remote_info.digest_value
            and candidate_info.digest_value
            and remote_info.digest_value != candidate_info.digest_value
        ):
            logger.warning("忽略 Digest 不一致的镜像 %s", candidate_url)
            continue
        if primary_etag and candidate_etag and primary_etag != candidate_etag:
            logger.warning("忽略强 ETag 不一致的镜像 %s", candidate_url)
            continue
        range_urls.append(candidate_url)
    if len(range_urls) > 1 and not remote_info.digest_value and not (remote_info.etag and not remote_info.etag.strip().startswith("W/")):
        logger.warning("多个镜像缺少强 Digest/ETag，最终结果只能依赖完整文件大小或调用者哈希")
    return _RemoteProbeResult(
        primary_url=primary_url,
        remote_info=remote_info,
        range_urls=range_urls,
        range_host_keys={url: _url_host_key(info.final_url or url) for url, info in range_results if url in range_urls},
        resume_failure_count=len(urls) - len(range_urls),
    )


def _cached_file_not_modified(
    urls: list[str],
    cached_file: Path,
    timeout: Any = 60,
) -> bool:
    import requests

    modified_since = formatdate(cached_file.stat().st_mtime, usegmt=True)
    headers = _request_headers({"If-Modified-Since": modified_since})
    for url in urls:
        try:
            response = requests.head(url, allow_redirects=True, timeout=timeout, headers=headers)
            try:
                status_code = int(response.status_code or 0)
                if status_code == 304:
                    return True
                if 200 <= status_code < 300:
                    return False
            finally:
                _close_response(response)
        except Exception as e:
            logger.debug("conditional-get HEAD 请求失败, 将重新下载: %s", e)
            return False
    return False


def _state_path_for(
    temp_file: Path,
) -> Path:
    return temp_file.with_name(f"{temp_file.name}.state.json")


def _state_temp_path_for(
    state_file: Path,
) -> Path:
    return state_file.with_name(f"{state_file.name}__temp")


def _cleanup_resume_files(
    temp_file: Path,
    state_file: Path,
) -> None:
    temp_file.unlink(missing_ok=True)
    state_file.unlink(missing_ok=True)
    _state_temp_path_for(state_file).unlink(missing_ok=True)
    state_file.with_name(f"{state_file.name}.tmp").unlink(missing_ok=True)
    with _STATE_FILE_DIGEST_LOCK:
        _STATE_FILE_DIGESTS.pop(state_file, None)


def _load_resume_state(
    state_file: Path,
) -> dict[str, object]:
    try:
        raw_state = state_file.read_text(encoding="utf-8")
        state = json.loads(raw_state)
    except OSError as e:
        raise _ResumeStateError(f"无法读取断点续传状态文件: {state_file}") from e
    except json.JSONDecodeError as e:
        raise _ResumeStateError(f"断点续传状态文件不是有效 JSON: {state_file}") from e
    if not isinstance(state, dict):
        raise _ResumeStateError("断点续传状态文件根节点必须是对象")
    with _STATE_FILE_DIGEST_LOCK:
        _STATE_FILE_DIGESTS[state_file] = hashlib.sha1(raw_state.encode("utf-8")).hexdigest()
    return state


def _require_state_int(
    state: dict[str, object],
    key: str,
) -> int:
    value = state.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise _ResumeStateError(f"断点续传状态字段 {key!r} 必须是整数")
    return value


def _require_state_optional_str(
    state: dict[str, object],
    key: str,
) -> str | None:
    value = state.get(key)
    if value is not None and not isinstance(value, str):
        raise _ResumeStateError(f"断点续传状态字段 {key!r} 必须是字符串或 null")
    return value


def _piece_count_for(
    total_size: int,
    piece_length: int,
) -> int:
    return max(1, math.ceil(total_size / piece_length))


def _piece_size_for(
    *,
    total_size: int,
    piece_length: int,
    index: int,
) -> int:
    return min((index + 1) * piece_length, total_size) - index * piece_length


def _range_is_complete_in_bitfield(
    completed: list[bool],
    *,
    total_size: int,
    piece_length: int,
    offset: int,
    length: int,
) -> bool:
    if length <= 0 or offset >= total_size:
        return False
    end_offset = min(offset + length, total_size) - 1
    start_piece = offset // piece_length
    end_piece = end_offset // piece_length
    return all(completed[index] for index in range(start_piece, end_piece + 1))


def _convert_completed_bitfield(
    completed: list[bool],
    *,
    total_size: int,
    source_piece_length: int,
    target_piece_length: int,
) -> list[bool]:
    target_piece_count = _piece_count_for(total_size, target_piece_length)
    converted: list[bool] = []
    for index in range(target_piece_count):
        converted.append(
            _range_is_complete_in_bitfield(
                completed,
                total_size=total_size,
                piece_length=source_piece_length,
                offset=index * target_piece_length,
                length=target_piece_length,
            )
        )
    return converted


def _bitfield_to_hex(
    completed: list[bool],
) -> str:
    data = bytearray(math.ceil(len(completed) / 8))
    for index, done in enumerate(completed):
        if done:
            data[index // 8] |= 1 << (7 - index % 8)
    return data.hex()


def _bitfield_from_hex(
    bitfield: object,
    piece_count: int,
) -> list[bool]:
    if not isinstance(bitfield, str):
        raise _ResumeStateError("断点续传状态字段 'completed_bitfield' 必须是十六进制字符串")

    try:
        data = bytes.fromhex(bitfield)
    except ValueError:
        raise _ResumeStateError("断点续传状态字段 'completed_bitfield' 不是有效十六进制")

    expected_bytes = math.ceil(piece_count / 8)
    if len(data) != expected_bytes:
        raise _ResumeStateError(f"断点续传状态 bitfield 长度不匹配: 期望 {expected_bytes} 字节, 实际 {len(data)} 字节")

    completed: list[bool] = []
    for index in range(piece_count):
        completed.append(bool(data[index // 8] & (1 << (7 - index % 8))))
    for index in range(piece_count, len(data) * 8):
        if data[index // 8] & (1 << (7 - index % 8)):
            raise _ResumeStateError("断点续传状态 bitfield padding 位必须为 0")
    return completed


def _in_flight_bitfield_to_hex(
    *,
    piece_size: int,
    completed_length: int,
) -> str:
    block_count = max(1, math.ceil(piece_size / IN_FLIGHT_BLOCK_LENGTH))
    data = bytearray(math.ceil(block_count / 8))
    completed_blocks = min(block_count, completed_length // IN_FLIGHT_BLOCK_LENGTH)
    if completed_length == piece_size:
        completed_blocks = block_count
    for index in range(completed_blocks):
        data[index // 8] |= 1 << (7 - index % 8)
    return data.hex()


def _validate_in_flight_bitfield(
    *,
    bitfield: object,
    piece_size: int,
    completed_length: int,
) -> None:
    if not isinstance(bitfield, str):
        raise _ResumeStateError("in-flight piece bitfield 必须是十六进制字符串")
    try:
        data = bytes.fromhex(bitfield)
    except ValueError:
        raise _ResumeStateError("in-flight piece bitfield 不是有效十六进制")
    block_count = max(1, math.ceil(piece_size / IN_FLIGHT_BLOCK_LENGTH))
    expected_bytes = math.ceil(block_count / 8)
    if len(data) != expected_bytes:
        raise _ResumeStateError(f"in-flight piece bitfield 长度不匹配: 期望 {expected_bytes} 字节, 实际 {len(data)} 字节")
    expected = _in_flight_bitfield_to_hex(piece_size=piece_size, completed_length=completed_length)
    if bitfield.lower() != expected:
        raise _ResumeStateError("in-flight piece bitfield 与 completed_length 不匹配")


def _in_flight_lengths_from_state(
    in_flight_pieces: object,
    *,
    piece_count: int,
    piece_length: int,
    total_size: int,
    completed: list[bool],
) -> list[int]:
    if in_flight_pieces is None:
        return [0] * piece_count
    if not isinstance(in_flight_pieces, list):
        raise _ResumeStateError("断点续传状态字段 'in_flight_pieces' 必须是数组")

    lengths = [0] * piece_count
    for raw_item in in_flight_pieces:
        if not isinstance(raw_item, dict):
            raise _ResumeStateError("in-flight piece 必须是对象")
        item = cast("dict[str, Any]", raw_item)
        index = item.get("index")
        length = item.get("length")
        completed_length = item.get("completed_length")
        if isinstance(index, bool) or not isinstance(index, int):
            raise _ResumeStateError("in-flight piece index 必须是整数")
        if isinstance(length, bool) or not isinstance(length, int):
            raise _ResumeStateError("in-flight piece length 必须是整数")
        if isinstance(completed_length, bool) or not isinstance(completed_length, int):
            raise _ResumeStateError("in-flight piece completed_length 必须是整数")
        if index < 0 or index >= piece_count:
            raise _ResumeStateError(f"in-flight piece index 越界: {index}")
        if completed[index]:
            raise _ResumeStateError(f"in-flight piece {index} 已在 completed bitfield 中标记完成")
        piece_size = _piece_size_for(total_size=total_size, piece_length=piece_length, index=index)
        if length != piece_size:
            raise _ResumeStateError(f"in-flight piece {index} length 不匹配: 期望 {piece_size}, 实际 {length}")
        if not 0 < completed_length < piece_size:
            raise _ResumeStateError(f"in-flight piece {index} completed_length 越界: {completed_length}")
        if lengths[index] != 0:
            raise _ResumeStateError(f"in-flight piece {index} 重复")
        _validate_in_flight_bitfield(
            bitfield=item.get("bitfield"),
            piece_size=piece_size,
            completed_length=completed_length,
        )
        lengths[index] = completed_length
    return lengths


def _parse_resume_state(
    state: dict[str, object],
    *,
    remote_info: _RemoteFileInfo,
    piece_length: int,
    allow_piece_length_change: bool,
    allow_validator_change: bool = False,
) -> tuple[list[bool], list[int]] | None:
    version = _require_state_int(state, "version")
    if version != STATE_VERSION:
        raise _ResumeStateError(f"断点续传状态版本不匹配: 期望 {STATE_VERSION}, 实际 {version}")
    total_size = _require_state_int(state, "total_size")
    if total_size != remote_info.total_size:
        raise _ResumeStateError(f"断点续传状态文件大小不匹配: 期望 {remote_info.total_size}, 实际 {total_size}")

    saved_digest = state.get("digest_value") or state.get("digest_sha256")
    if saved_digest is not None and not isinstance(saved_digest, str):
        raise _ResumeStateError("断点续传状态 digest_value 必须是字符串或 null")
    saved_digest_algorithm = state.get("digest_algorithm") or ("sha256" if state.get("digest_sha256") else None)
    if saved_digest_algorithm is not None and not isinstance(saved_digest_algorithm, str):
        raise _ResumeStateError("断点续传状态 digest_algorithm 必须是字符串或 null")
    matching_digest_algorithm = bool(saved_digest and remote_info.digest_value and saved_digest_algorithm == remote_info.digest_algorithm)
    if matching_digest_algorithm:
        if saved_digest.lower() != (remote_info.digest_value or "").lower():
            if not allow_validator_change:
                raise _ResumeStateError("远端强 Digest 已变化，拒绝拼接已有断点")
            logger.warning("远端强 Digest 已变化；调用者提供了最终强哈希，将继续恢复并以最终哈希为准")
    else:
        saved_etag = state.get("etag")
        saved_etag = saved_etag if isinstance(saved_etag, str) else None
        remote_etag = remote_info.etag
        saved_strong_etag = saved_etag if saved_etag and not saved_etag.strip().startswith("W/") else None
        remote_strong_etag = remote_etag if remote_etag and not remote_etag.strip().startswith("W/") else None
        if saved_strong_etag and remote_strong_etag and saved_strong_etag != remote_strong_etag:
            if not allow_validator_change:
                raise _ResumeStateError("远端强 ETag 已变化，拒绝拼接已有断点")
            logger.warning("远端强 ETag 已变化；调用者提供了最终强哈希，将继续恢复并以最终哈希为准")
        saved_last_modified = state.get("last_modified")
        saved_last_modified = saved_last_modified if isinstance(saved_last_modified, str) else None
        if not saved_strong_etag and not remote_strong_etag and saved_last_modified and remote_info.last_modified and saved_last_modified != remote_info.last_modified:
            if not allow_validator_change:
                raise _ResumeStateError("远端 Last-Modified 已变化，拒绝拼接已有断点")
            logger.warning("远端 Last-Modified 已变化；调用者提供了最终强哈希，将继续恢复并以最终哈希为准")
        if not matching_digest_algorithm and not (saved_strong_etag and remote_strong_etag):
            logger.warning("断点状态缺少可共同验证的强 Digest/ETag，将按文件大小和弱 validator 保守恢复")

    saved_piece_length = _require_state_int(state, "piece_length")
    if saved_piece_length <= 0:
        raise _ResumeStateError("断点续传状态 piece_length 必须大于 0")
    saved_piece_count = _require_state_int(state, "piece_count")
    expected_saved_piece_count = _piece_count_for(remote_info.total_size, saved_piece_length)
    if saved_piece_count != expected_saved_piece_count:
        raise _ResumeStateError(f"断点续传状态 piece_count 不匹配: 期望 {expected_saved_piece_count}, 实际 {saved_piece_count}")

    completed = _bitfield_from_hex(state.get("completed_bitfield"), saved_piece_count)
    in_flight_lengths = _in_flight_lengths_from_state(
        state.get("in_flight_pieces"),
        piece_count=saved_piece_count,
        piece_length=saved_piece_length,
        total_size=remote_info.total_size,
        completed=completed,
    )
    if saved_piece_length != piece_length:
        if (any(completed) or any(in_flight_lengths)) and not allow_piece_length_change:
            raise _PieceLengthChangedError(f"检测到 piece_length 变化: 状态文件 {saved_piece_length}, 当前配置 {piece_length}")
        converted_completed = _convert_completed_bitfield(
            completed,
            total_size=remote_info.total_size,
            source_piece_length=saved_piece_length,
            target_piece_length=piece_length,
        )
        return converted_completed, [0] * len(converted_completed)
    return completed, in_flight_lengths


def _save_resume_state(
    state_file: Path,
    *,
    urls: list[str],
    remote_info: _RemoteFileInfo,
    options: _DownloadOptions,
    piece_storage: "_PieceStorage",
) -> None:
    completed = piece_storage.snapshot_completed()
    in_flight_pieces = piece_storage.snapshot_in_flight_pieces()
    state = {
        "version": STATE_VERSION,
        "url": urls[0],
        "uris": urls,
        "total_size": remote_info.total_size,
        "etag": remote_info.etag,
        "last_modified": remote_info.last_modified,
        "digest_sha256": remote_info.digest_sha256,
        "digest_algorithm": remote_info.digest_algorithm,
        "digest_value": remote_info.digest_value,
        "content_disposition_filename": remote_info.content_disposition_filename,
        "content_encoding": remote_info.content_encoding,
        "piece_length": options.piece_length,
        "piece_count": len(completed),
        "completed_bitfield": _bitfield_to_hex(completed),
        "in_flight_pieces": in_flight_pieces,
    }
    payload = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    with _STATE_FILE_DIGEST_LOCK:
        if state_file.exists() and _STATE_FILE_DIGESTS.get(state_file) == digest:
            return

    tmp_state_file = _state_temp_path_for(state_file)
    tmp_state_file.write_text(payload, encoding="utf-8")
    with tmp_state_file.open("rb") as file:
        os.fsync(file.fileno())
    tmp_state_file.replace(state_file)
    try:
        directory_fd = os.open(state_file.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as e:
        logger.debug("无法同步断点状态目录 '%s': %s", state_file.parent, e)
    with _STATE_FILE_DIGEST_LOCK:
        _STATE_FILE_DIGESTS[state_file] = digest


def _flush_download_data(temp_file: Path) -> None:
    """在提交 completed/in-flight 状态前把下载数据同步到稳定存储"""
    with temp_file.open("rb") as file:
        os.fsync(file.fileno())


class _ThreadLocalSessionPool:
    """为每个下载线程复用一个 requests Session"""

    def __init__(
        self,
        pool_size: int,
    ) -> None:
        self.pool_size = max(1, pool_size)
        self.local = threading.local()
        self.lock = threading.Lock()
        self.sessions: list[Any] = []

    def get(self) -> Any:
        session = getattr(self.local, "session", None)
        if session is not None:
            return session

        import requests

        session_factory = getattr(requests, "Session", None)
        if callable(session_factory):
            session = session_factory()
            self._configure_session(session)
            with self.lock:
                self.sessions.append(session)
        else:
            session = requests
        self.local.session = session
        return session

    def close_all(self) -> None:
        with self.lock:
            sessions = list(self.sessions)
            self.sessions.clear()
        for session in sessions:
            session.close()

    def _configure_session(
        self,
        session: Any,
    ) -> None:
        import requests

        if not hasattr(requests, "adapters") or not hasattr(session, "mount"):
            return
        for prefix in ("http://", "https://"):
            session.mount(prefix, requests.adapters.HTTPAdapter(pool_connections=self.pool_size, pool_maxsize=self.pool_size))


@dataclass
class _UriHealth:
    successes: int = 0
    failures: int = 0
    total_bytes: int = 0
    total_seconds: float = 0.0
    last_error: str | None = None
    last_success: float | None = None
    cooldown_until: float = 0.0

    @property
    def average_speed(self) -> float:
        return self.total_bytes / self.total_seconds if self.total_seconds > 0 else 0.0

    @property
    def success_rate(self) -> float:
        return self.successes / max(1, self.successes + self.failures)


class _UriPool:
    """aria2 FileEntry URI 池的简化实现"""

    def __init__(
        self,
        urls: list[str],
        max_connection_per_server: int,
        host_keys: dict[str, tuple[str, str, int | None]] | None = None,
    ) -> None:
        self.urls = list(urls)
        self.max_connection_per_server = max(1, max_connection_per_server)
        self.keys = [(host_keys or {}).get(url, _url_host_key(url)) for url in self.urls]
        self.key_by_url = dict(zip(self.urls, self.keys))
        self.in_flight: Counter[tuple[str, str, int | None]] = Counter()
        self.health = {url: _UriHealth() for url in self.urls}
        self.disabled_errors: dict[str, Exception] = {}
        self.next_index = 0
        self.condition = threading.Condition()

    @property
    def capacity(self) -> int:
        return max(1, len(set(self.keys)) * self.max_connection_per_server)

    def acquire(
        self,
        stop_event: threading.Event | None = None,
        excluded_urls: set[str] | None = None,
    ) -> str | None:
        excluded_urls = excluded_urls or set()
        with self.condition:
            while True:
                now = time.monotonic()
                candidates: list[int] = []
                for offset in range(len(self.urls)):
                    index = (self.next_index + offset) % len(self.urls)
                    url = self.urls[index]
                    if url in excluded_urls or url in self.disabled_errors:
                        continue
                    key = self.keys[index]
                    if self.in_flight[key] >= self.max_connection_per_server:
                        continue
                    if self.health[url].cooldown_until <= now:
                        candidates.append(index)

                if candidates:
                    unknown = [index for index in candidates if self.health[self.urls[index]].successes == 0 and self.health[self.urls[index]].failures == 0]
                    if unknown:
                        selected_index = unknown[0]
                    else:
                        selected_index = max(
                            candidates,
                            key=lambda index: (
                                self.health[self.urls[index]].success_rate,
                                self.health[self.urls[index]].average_speed,
                                self.health[self.urls[index]].last_success or 0.0,
                            ),
                        )
                    key = self.keys[selected_index]
                    self.in_flight[key] += 1
                    self.next_index = (selected_index + 1) % len(self.urls)
                    return self.urls[selected_index]

                if all(url in excluded_urls or url in self.disabled_errors for url in self.urls):
                    return None

                if stop_event is not None and stop_event.is_set():
                    return None
                cooldowns = [self.health[url].cooldown_until - now for url in self.urls if url not in excluded_urls and url not in self.disabled_errors and self.health[url].cooldown_until > now]
                self.condition.wait(timeout=min(cooldowns, default=0.1))

    def release(
        self,
        url: str | None,
    ) -> None:
        if url is None:
            return
        key = self.key_by_url[url]
        with self.condition:
            if self.in_flight[key] > 0:
                self.in_flight[key] -= 1
                if self.in_flight[key] <= 0:
                    del self.in_flight[key]
            self.condition.notify_all()

    def report_success(self, url: str, *, byte_count: int, elapsed: float) -> None:
        with self.condition:
            health = self.health[url]
            health.successes += 1
            health.total_bytes += max(0, byte_count)
            health.total_seconds += max(elapsed, 1e-9)
            health.last_success = time.monotonic()
            health.last_error = None
            health.cooldown_until = 0.0
            self.condition.notify_all()

    def report_failure(self, url: str, error: Exception, *, cooldown: float = 0.0, permanent: bool = False) -> None:
        with self.condition:
            health = self.health[url]
            health.failures += 1
            health.last_error = str(error)
            health.cooldown_until = max(health.cooldown_until, time.monotonic() + max(0.0, cooldown))
            if permanent:
                self.disabled_errors[url] = error
            self.condition.notify_all()


class _PieceStorage:
    """aria2 PieceStorage 的轻量 Python 实现"""

    def __init__(
        self,
        *,
        total_size: int,
        piece_length: int,
        completed: list[bool] | None = None,
        in_flight_lengths: list[int] | None = None,
    ) -> None:
        self.total_size = total_size
        self.piece_length = max(1, piece_length)
        self.piece_count = max(1, math.ceil(total_size / self.piece_length))
        self.lock = threading.Lock()
        raw_completed = completed if completed and len(completed) == self.piece_count else [False] * self.piece_count
        raw_in_flight_lengths = in_flight_lengths if in_flight_lengths and len(in_flight_lengths) == self.piece_count else [0] * self.piece_count
        self.completed: list[bool] = []
        self.in_flight_lengths: list[int] = []
        for index in range(self.piece_count):
            piece_size = self._piece_size_unlocked(index)
            is_complete = bool(raw_completed[index])
            in_flight_length = 0 if is_complete else max(0, min(int(raw_in_flight_lengths[index]), piece_size))
            if in_flight_length >= piece_size:
                is_complete = True
                in_flight_length = 0
            self.completed.append(is_complete)
            self.in_flight_lengths.append(0 if is_complete else in_flight_length)
        self.in_use = [False] * self.piece_count
        self.in_use_owner: list[int | None] = [None] * self.piece_count
        self.owner_idle: dict[int, bool] = {}

    def snapshot_completed(self) -> list[bool]:
        with self.lock:
            return list(self.completed)

    def snapshot_in_flight_pieces(self) -> list[dict[str, object]]:
        with self.lock:
            pieces: list[dict[str, object]] = []
            for index, completed_length in enumerate(self.in_flight_lengths):
                if completed_length <= 0 or self.completed[index]:
                    continue
                piece_size = self._piece_size_unlocked(index)
                pieces.append(
                    {
                        "index": index,
                        "length": piece_size,
                        "completed_length": completed_length,
                        "bitfield": _in_flight_bitfield_to_hex(
                            piece_size=piece_size,
                            completed_length=completed_length,
                        ),
                    }
                )
            return pieces

    def completed_piece_count(self) -> int:
        with self.lock:
            return sum(1 for done in self.completed if done)

    def completed_size(self) -> int:
        with self.lock:
            return sum(self._piece_size_unlocked(index) if done else self.in_flight_lengths[index] for index, done in enumerate(self.completed))

    def is_complete(self) -> bool:
        with self.lock:
            return all(self.completed)

    def check_out_segment(
        self,
        min_split_size: int,
        owner_id: int = 0,
    ) -> _Segment | None:
        with self.lock:
            index = self._select_sparse_missing_unused_piece_unlocked(min_split_size)
            if index is None:
                return None

            return self._check_out_piece_unlocked(index, owner_id)

    def check_out_piece(
        self,
        index: int,
        owner_id: int = 0,
    ) -> _Segment | None:
        with self.lock:
            if index < 0 or index >= self.piece_count or self.completed[index] or self.in_use[index]:
                return None
            return self._check_out_piece_unlocked(index, owner_id)

    def check_out_clean_piece(
        self,
        index: int,
        owner_id: int = 0,
    ) -> _Segment | None:
        with self.lock:
            if index < 0 or index >= self.piece_count or self.completed[index] or self.in_use[index] or self.in_flight_lengths[index] > 0:
                return None
            return self._check_out_piece_unlocked(index, owner_id)

    def check_out_clean_idle_piece(
        self,
        index: int,
        owner_id: int = 0,
    ) -> _Segment | None:
        with self.lock:
            if index < 0 or index >= self.piece_count or self.completed[index] or self.in_flight_lengths[index] > 0:
                return None
            current_owner = self.in_use_owner[index]
            if current_owner is None:
                return self._check_out_piece_unlocked(index, owner_id)
            if current_owner == owner_id:
                return self._segment_for_piece_unlocked(index, owner_id)
            if not self.owner_idle.get(current_owner, False):
                return None
            self.in_use_owner[index] = owner_id
            self.owner_idle[owner_id] = True
            return self._segment_for_piece_unlocked(index, owner_id)

    def mark_complete(
        self,
        segment: _Segment,
    ) -> int:
        with self.lock:
            newly_completed = 0
            for index in range(segment.start_piece, segment.end_piece + 1):
                if not self.completed[index]:
                    self.completed[index] = True
                    self.in_flight_lengths[index] = 0
                    newly_completed += 1
                if self.in_use_owner[index] == segment.owner_id:
                    self.in_use[index] = False
                    self.in_use_owner[index] = None
            return newly_completed

    def record_progress(
        self,
        segment: _Segment,
        next_offset: int,
    ) -> None:
        with self.lock:
            index = segment.start_piece
            if index < 0 or index >= self.piece_count or self.completed[index] or self.in_use_owner[index] != segment.owner_id:
                return
            self.owner_idle[segment.owner_id] = False
            piece_start = self._piece_start_unlocked(index)
            piece_size = self._piece_size_unlocked(index)
            in_flight_length = max(0, min(next_offset - piece_start, piece_size))
            if in_flight_length > self.in_flight_lengths[index]:
                self.in_flight_lengths[index] = in_flight_length

    def refresh_segment(
        self,
        segment: _Segment,
    ) -> _Segment | None:
        with self.lock:
            index = segment.start_piece
            if index < 0 or index >= self.piece_count or self.completed[index]:
                return None
            self.in_use[index] = True
            self.in_use_owner[index] = segment.owner_id
            self.owner_idle[segment.owner_id] = True
            return self._segment_for_piece_unlocked(index, segment.owner_id)

    def release(
        self,
        segment: _Segment,
    ) -> None:
        with self.lock:
            for index in range(segment.start_piece, segment.end_piece + 1):
                if self.in_use_owner[index] == segment.owner_id:
                    self.in_use[index] = False
                    self.in_use_owner[index] = None

    def owns_segment(
        self,
        segment: _Segment,
    ) -> bool:
        with self.lock:
            return all(0 <= index < self.piece_count and self.in_use_owner[index] == segment.owner_id for index in range(segment.start_piece, segment.end_piece + 1))

    def _piece_start_unlocked(
        self,
        index: int,
    ) -> int:
        return index * self.piece_length

    def _piece_end_unlocked(
        self,
        index: int,
    ) -> int:
        return min((index + 1) * self.piece_length, self.total_size) - 1

    def _piece_size_unlocked(
        self,
        index: int,
    ) -> int:
        return self._piece_end_unlocked(index) - self._piece_start_unlocked(index) + 1

    def _check_out_piece_unlocked(
        self,
        index: int,
        owner_id: int,
    ) -> _Segment:
        self.in_use[index] = True
        self.in_use_owner[index] = owner_id
        self.owner_idle[owner_id] = True
        return self._segment_for_piece_unlocked(index, owner_id)

    def _segment_for_piece_unlocked(
        self,
        index: int,
        owner_id: int,
    ) -> _Segment:
        piece_start = self._piece_start_unlocked(index)
        start = min(piece_start + self.in_flight_lengths[index], self._piece_end_unlocked(index))
        return _Segment(
            start_piece=index,
            end_piece=index,
            start=start,
            end=self._piece_end_unlocked(index),
            piece_start=piece_start,
            owner_id=owner_id,
        )

    def _select_sparse_missing_unused_piece_unlocked(
        self,
        min_split_size: int,
    ) -> int | None:
        ranges: list[tuple[int, int]] = []
        index = 0
        while index < self.piece_count:
            while index < self.piece_count and (self.completed[index] or self.in_use[index]):
                index += 1
            if index >= self.piece_count:
                break
            start = index
            while index < self.piece_count and not self.completed[index] and not self.in_use[index]:
                index += 1
            end = index
            if start > 0 and self.in_use[start - 1]:
                start = (start + end) // 2
            if start < end:
                ranges.append((start, end))

        if not ranges:
            return None

        max_range = ranges[0]
        for current in ranges[1:]:
            if self._range_is_better_unlocked(current, max_range):
                max_range = current

        start, end = max_range
        if start == 0:
            return 0

        previous_completed = self.completed[start - 1] and not self.in_use[start - 1]
        range_size = (end - start) * self.piece_length
        if previous_completed or range_size >= min_split_size:
            return start
        return None

    def _range_is_better_unlocked(
        self,
        current: tuple[int, int],
        best: tuple[int, int],
    ) -> bool:
        current_size = current[1] - current[0]
        best_size = best[1] - best[0]
        if current_size != best_size:
            return current_size > best_size
        if best[0] <= 0 or current[0] <= 0:
            return False

        best_previous_completed = self.completed[best[0] - 1] and not self.in_use[best[0] - 1]
        current_previous_completed = self.completed[current[0] - 1] and not self.in_use[current[0] - 1]
        return current_previous_completed and not best_previous_completed


class _SegmentManager:
    """aria2 SegmentMan 的轻量 Python 实现"""

    def __init__(
        self,
        piece_storage: _PieceStorage,
        min_split_size: int,
    ) -> None:
        self.piece_storage = piece_storage
        self.min_split_size = min_split_size

    def get_segment(
        self,
        owner_id: int = 0,
    ) -> _Segment | None:
        return self.piece_storage.check_out_segment(self.min_split_size, owner_id)

    def get_next_segment(
        self,
        segment: _Segment,
    ) -> _Segment | None:
        next_index = segment.end_piece + 1
        next_segment = self.piece_storage.check_out_clean_piece(next_index, segment.owner_id)
        if next_segment is not None:
            return next_segment
        return self.piece_storage.check_out_clean_idle_piece(next_index, segment.owner_id)

    def mark_complete(
        self,
        segment: _Segment,
    ) -> int:
        return self.piece_storage.mark_complete(segment)

    def record_progress(
        self,
        segment: _Segment,
        next_offset: int,
    ) -> None:
        self.piece_storage.record_progress(segment, next_offset)

    def refresh_segment(
        self,
        segment: _Segment,
    ) -> _Segment | None:
        return self.piece_storage.refresh_segment(segment)

    def release(
        self,
        segment: _Segment,
    ) -> None:
        self.piece_storage.release(segment)

    def owns_segment(
        self,
        segment: _Segment,
    ) -> bool:
        return self.piece_storage.owns_segment(segment)


def _retry_delay_with_jitter(attempt: int) -> float:
    base_delay = min(0.5 * (2 ** max(0, attempt - 1)), 5.0)
    return min(random.uniform(0.75, 1.25) * base_delay, 5.0)


def _retry_delay_for(
    headers: Any,
    attempt: int,
    *,
    status_code: int,
    retry_wait: int,
) -> float:
    if status_code == 503 and retry_wait > 0:
        return float(retry_wait)
    retry_after = _get_header(headers, "Retry-After")
    if retry_after:
        try:
            return min(float(retry_after), 30.0)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after).timestamp()
                return min(max(0.0, retry_at - time.time()), 30.0)
            except (TypeError, ValueError, OverflowError):
                pass
    if status_code == 503:
        return 0.0
    return _retry_delay_with_jitter(attempt)


def _validate_range_response(
    response: Any,
    *,
    url: str = "<unknown>",
    segment: _Segment,
    total_size: int,
    attempt: int,
    retry_wait: int,
) -> None:
    status_code = int(response.status_code or 0)
    headers = response.headers

    if status_code == 416:
        raise _RangeDownloadNotSupported("远端拒绝 Range 请求: HTTP 416")
    if status_code in RETRYABLE_STATUS_CODES:
        raise _RangeDownloadTemporaryError(
            f"HTTP {status_code}",
            retry_delay=_retry_delay_for(headers, attempt, status_code=status_code, retry_wait=retry_wait),
        )
    if status_code not in {200, 206}:
        raise DownloadPermanentHttpError(
            url=url,
            status_code=status_code,
            segment=segment.byte_range,
            attempt=attempt,
        )

    if _get_header(headers, "Transfer-Encoding") is not None:
        if status_code == 200 and segment.start > 0:
            raise _RangeRequestIgnored("服务器返回 HTTP 200 (含 Transfer-Encoding), 疑似忽略 Range 请求")
        return

    parsed_range = _response_range_from_headers(headers)
    if parsed_range is None:
        raise _RangeDownloadNotSupported("响应缺少可验证的 Content-Range 或 Content-Length")

    start, end, content_total = parsed_range
    expected_end = 0
    range_satisfied = start == segment.start and (expected_end == 0 or expected_end == end) and (total_size == 0 or content_total == total_size)
    if not range_satisfied:
        message = f"Range 响应不匹配: 期望 bytes {segment.start}-/{total_size}, 实际 {_get_header(headers, 'Content-Range') or _get_header(headers, 'Content-Length')}"
        if status_code == 200 and segment.start > 0:
            raise _RangeRequestIgnored(message)
        raise _RangeDownloadNotSupported(message)


def _stream_request_headers(
    segment: _Segment,
    if_range: str | None = None,
) -> dict[str, str]:
    headers = {"Range": f"bytes={segment.start}-"}
    if if_range:
        headers["If-Range"] = if_range
    return _request_headers(headers)


def _download_stream_once(
    request_client: Any,
    *,
    url: str,
    temp_file: Path,
    segment: _Segment,
    total_size: int,
    timeout: Any,
    attempt: int,
    retry_wait: int,
    if_range: str | None,
    digest_tracker: _DigestTracker,
    cancel_event: threading.Event,
    lowest_speed_limit: int,
    lowest_speed_time: int,
    segment_manager: _SegmentManager,
    mark_complete_callback: Any,
    progress_callback: Any | None = None,
) -> None:
    response = None
    current_segment: _Segment | None = segment
    last_complete_segment: _Segment | None = None
    partial_reported_size = 0
    speed_window_started = time.monotonic()
    speed_window_bytes = 0
    try:
        if cancel_event.is_set():
            raise DownloadCancelledError("下载已取消")
        response = request_client.get(url, stream=True, timeout=timeout, headers=_stream_request_headers(segment, if_range))
        digest_tracker.observe(_get_header(response.headers, "Digest"))
        if not segment_manager.owns_segment(segment):
            raise _SegmentOwnershipLost()
        _validate_range_response(response, url=url, segment=segment, total_size=total_size, attempt=attempt, retry_wait=retry_wait)

        offset = segment.start
        with temp_file.open("r+b") as file:
            for chunk in response.iter_content(chunk_size=STREAM_CHUNK_SIZE):
                if cancel_event.is_set():
                    raise DownloadCancelledError("下载已取消")
                if not chunk:
                    continue
                chunk_offset = 0
                while chunk_offset < len(chunk):
                    if current_segment is None:
                        if last_complete_segment is None:
                            return
                        current_segment = segment_manager.get_next_segment(last_complete_segment)
                        if current_segment is None:
                            return
                        offset = current_segment.start
                        partial_reported_size = 0

                    writable_size = min(len(chunk) - chunk_offset, current_segment.end - offset + 1)
                    if writable_size <= 0:
                        mark_complete_callback(current_segment)
                        last_complete_segment = current_segment
                        current_segment = None
                        partial_reported_size = 0
                        continue

                    if not segment_manager.owns_segment(current_segment):
                        raise _SegmentOwnershipLost()
                    file.seek(offset)
                    file.write(chunk[chunk_offset : chunk_offset + writable_size])
                    # state 可能在 progress/complete 回调中立即提交，因此先刷新
                    # Python 文件缓冲，避免控制状态领先于实际写入的数据。
                    file.flush()
                    offset += writable_size
                    chunk_offset += writable_size
                    partial_reported_size += writable_size
                    speed_window_bytes += writable_size
                    segment_manager.record_progress(current_segment, offset)
                    if progress_callback is not None:
                        progress_callback(writable_size, url)

                    speed_window_elapsed = time.monotonic() - speed_window_started
                    if lowest_speed_limit > 0 and lowest_speed_time > 0 and speed_window_elapsed >= lowest_speed_time:
                        current_speed = speed_window_bytes / max(speed_window_elapsed, 1e-9)
                        if current_speed < lowest_speed_limit:
                            raise DownloadLowSpeedError(f"镜像 {url} 在 {speed_window_elapsed:.1f}s 内速度 {current_speed:.1f} B/s 低于 {lowest_speed_limit} B/s")
                        speed_window_started = time.monotonic()
                        speed_window_bytes = 0

                    if offset > current_segment.end:
                        mark_complete_callback(current_segment)
                        last_complete_segment = current_segment
                        current_segment = None
                        partial_reported_size = 0

        if current_segment is not None:
            raise IOError(f"分片大小不匹配: 期望 {current_segment.size}, 实际 {partial_reported_size}")
    except _RangeDownloadNotSupported:
        raise
    except DownloadPermanentHttpError:
        raise
    except DownloadIntegrityError:
        raise
    except DownloadCancelledError:
        raise
    except _SegmentOwnershipLost:
        raise
    except Exception as e:
        classified_error = _classify_network_error(e)
        raise _SegmentDownloadError(current_segment or segment, classified_error) from e
    finally:
        _close_response(response)


def _download_stream_with_retries(
    session_pool: _ThreadLocalSessionPool,
    *,
    uri_pool: _UriPool,
    temp_file: Path,
    segment: _Segment,
    total_size: int,
    timeout: Any,
    max_tries: int,
    retry_wait: int,
    if_range: str | None,
    digest_tracker: _DigestTracker,
    cancel_event: threading.Event,
    lowest_speed_limit: int,
    lowest_speed_time: int,
    stop_event: threading.Event,
    segment_manager: _SegmentManager,
    mark_complete_callback: Any,
    progress_callback: Any | None = None,
) -> None:
    last_error: Exception | None = None
    last_url: str | None = None
    attempts_by_url: Counter[str] = Counter()
    total_attempt_limit = max_tries * len(uri_pool.urls)
    while max_tries == 0 or sum(attempts_by_url.values()) < total_attempt_limit:
        exhausted_urls = {url for url, attempts in attempts_by_url.items() if max_tries != 0 and attempts >= max_tries}
        url = uri_pool.acquire(stop_event, excluded_urls=exhausted_urls)
        if url is None:
            if stop_event.is_set():
                segment_manager.release(segment)
                return
            disabled_errors = list(uri_pool.disabled_errors.values())
            if len(disabled_errors) == 1:
                raise disabled_errors[0]
            if disabled_errors:
                raise DownloadTransientError(f"所有镜像均已被隔离: {[str(error) for error in disabled_errors]}") from disabled_errors[-1]
            segment_manager.release(segment)
            break
        attempts_by_url[url] += 1
        request_attempt = attempts_by_url[url]
        started_at = time.monotonic()
        try:
            _download_stream_once(
                session_pool.get(),
                url=url,
                temp_file=temp_file,
                segment=segment,
                total_size=total_size,
                timeout=timeout,
                attempt=request_attempt,
                retry_wait=retry_wait,
                if_range=if_range,
                digest_tracker=digest_tracker,
                cancel_event=cancel_event,
                lowest_speed_limit=lowest_speed_limit,
                lowest_speed_time=lowest_speed_time,
                segment_manager=segment_manager,
                mark_complete_callback=mark_complete_callback,
                progress_callback=progress_callback,
            )
            uri_pool.report_success(url, byte_count=segment.size, elapsed=time.monotonic() - started_at)
            return
        except _RangeDownloadNotSupported as e:
            uri_pool.report_failure(url, e, permanent=True)
            if len(uri_pool.disabled_errors) >= len(uri_pool.urls):
                raise
            continue
        except DownloadPermanentHttpError as e:
            uri_pool.report_failure(url, e, permanent=True)
            if len(uri_pool.disabled_errors) >= len(uri_pool.urls):
                raise
            continue
        except DownloadIntegrityError as e:
            uri_pool.report_failure(url, e, permanent=True)
            if len(uri_pool.disabled_errors) >= len(uri_pool.urls):
                raise
            continue
        except _SegmentOwnershipLost:
            return
        except DownloadCancelledError:
            raise
        except _SegmentDownloadError as e:
            last_url = url
            failed_range = e.segment.byte_range
            segment_manager.release(e.segment)
            new_segment = segment_manager.get_segment(e.segment.owner_id)
            if new_segment is None:
                return
            segment = new_segment
            last_error = e.error
            delay = e.error.retry_delay if isinstance(e.error, _RangeDownloadTemporaryError) and e.error.retry_delay is not None else _retry_delay_with_jitter(request_attempt)
            uri_pool.report_failure(url, e.error, cooldown=delay if len(uri_pool.urls) > 1 else 0.0)
            logger.warning(
                "镜像 %s 的分片 %s 下载失败 [%s/%s]: %s, %.1fs 后重试",
                url,
                failed_range,
                request_attempt,
                max_tries,
                e.error,
                delay,
            )
            attempts_remain = max_tries == 0 or any(attempts_by_url[candidate] < max_tries for candidate in uri_pool.urls if candidate not in uri_pool.disabled_errors)
            if attempts_remain and len(uri_pool.urls) == 1:
                time.sleep(delay)
        finally:
            uri_pool.release(url)
    segment_manager.release(segment)
    raise DownloadTransientError(f"所有镜像的分片 {segment.byte_range} 下载预算已耗尽: attempts={dict(attempts_by_url)}, last_url={last_url}, last_error={last_error}") from last_error


def _resume_progress_size(
    *,
    temp_file: Path,
    state_file: Path,
    remote_info: _RemoteFileInfo,
    options: _DownloadOptions,
    allow_validator_change: bool = False,
) -> int:
    """校验断点文件并返回可恢复的字节数"""
    state_exists = state_file.exists()
    temp_exists = temp_file.exists()
    if state_exists:
        if not temp_exists:
            state_file.unlink(missing_ok=True)
            return 0
        state = _load_resume_state(state_file)
        validation_info = remote_info
        if remote_info.total_size <= 0:
            saved_total_size = _require_state_int(state, "total_size")
            if saved_total_size <= 0:
                raise _ResumeStateError("断点续传状态 total_size 必须大于 0")
            validation_info = _RemoteFileInfo(
                total_size=saved_total_size,
                supports_range=False,
                etag=remote_info.etag,
                last_modified=remote_info.last_modified,
                digest_sha256=remote_info.digest_sha256,
                digest_algorithm=remote_info.digest_algorithm,
                digest_value=remote_info.digest_value,
                content_disposition_filename=remote_info.content_disposition_filename,
                content_encoding=remote_info.content_encoding,
            )
        temp_size = temp_file.stat().st_size
        if temp_size != validation_info.total_size:
            raise _ResumeStateError(f"临时文件大小与断点续传状态不匹配: 期望 {validation_info.total_size}, 实际 {temp_size}")
        parsed_state = _parse_resume_state(
            state,
            remote_info=validation_info,
            piece_length=options.piece_length,
            allow_piece_length_change=options.allow_piece_length_change,
            allow_validator_change=allow_validator_change,
        )
        if parsed_state is None:
            return 0
        completed, in_flight_lengths = parsed_state
        completed_size = sum(
            _piece_size_for(
                total_size=validation_info.total_size,
                piece_length=options.piece_length,
                index=index,
            )
            for index, is_completed in enumerate(completed)
            if is_completed
        )
        return completed_size + sum(in_flight_lengths)

    if options.continue_download and temp_exists:
        temp_size = temp_file.stat().st_size
        # Range 下载会先把临时文件预分配到完整大小。没有 state 时不能把这种
        # full-size sparse file 当作已完成内容，只能信任严格小于远端大小的顺序文件。
        if temp_size > 0 and (remote_info.total_size <= 0 or temp_size < remote_info.total_size):
            return temp_size
    return 0


def _resume_policy_allows_restart(
    options: _DownloadOptions,
    *,
    failure_count: int,
    total_url_count: int,
) -> bool:
    """按 aria2 always-resume/max-resume-failure-tries 语义判断是否重头下载"""
    if options.always_resume:
        return False
    if failure_count >= total_url_count:
        return True
    return options.max_resume_failure_tries > 0 and failure_count >= options.max_resume_failure_tries


def _download_file_with_ranges(
    urls: list[str],
    uri_host_keys: dict[str, tuple[str, str, int | None]] | None,
    temp_file: Path,
    state_file: Path,
    remote_info: _RemoteFileInfo,
    progress: bool,
    options: _DownloadOptions,
    digest_tracker: _DigestTracker,
    allow_validator_change: bool,
    progress_callback: Any | None = None,
    cancel_event: threading.Event | None = None,
    timeout: Any = 60,
) -> None:
    try:
        from tqdm import tqdm
    except ImportError:
        from sd_webui_all_in_one.simple_tqdm import SimpleTqdm as tqdm

    if remote_info.total_size <= 0:
        raise _RangeDownloadNotSupported("远端未提供可分片下载的文件大小")

    seed_storage = _PieceStorage(total_size=remote_info.total_size, piece_length=options.piece_length)
    state_exists = state_file.exists()
    temp_exists = temp_file.exists()
    temp_size = temp_file.stat().st_size if temp_exists else 0
    if state_exists and not temp_exists:
        state_file.unlink(missing_ok=True)
        state_exists = False
    state = _load_resume_state(state_file) if state_exists else None

    if state_exists and temp_exists:
        if temp_size != remote_info.total_size:
            raise _ResumeStateError(f"临时文件大小与断点续传状态不匹配: 期望 {remote_info.total_size}, 实际 {temp_size}")
        parsed_state = _parse_resume_state(
            state or {},
            remote_info=remote_info,
            piece_length=options.piece_length,
            allow_piece_length_change=options.allow_piece_length_change,
            allow_validator_change=allow_validator_change,
        )
        if parsed_state is None:
            _cleanup_resume_files(temp_file, state_file)
            with temp_file.open("wb") as file:
                file.truncate(remote_info.total_size)
            piece_storage = seed_storage
        else:
            completed, in_flight_lengths = parsed_state
            piece_storage = _PieceStorage(
                total_size=remote_info.total_size,
                piece_length=options.piece_length,
                completed=completed,
                in_flight_lengths=in_flight_lengths,
            )
    elif options.continue_download and not state_exists and temp_exists and 0 < temp_size < remote_info.total_size:
        completed_piece_count = temp_size // options.piece_length
        partial_piece_length = temp_size % options.piece_length
        completed = [index < completed_piece_count for index in range(seed_storage.piece_count)]
        in_flight_lengths = [0] * seed_storage.piece_count
        if completed_piece_count < seed_storage.piece_count:
            in_flight_lengths[completed_piece_count] = partial_piece_length
        with temp_file.open("r+b") as file:
            file.truncate(remote_info.total_size)
        piece_storage = _PieceStorage(
            total_size=remote_info.total_size,
            piece_length=options.piece_length,
            completed=completed,
            in_flight_lengths=in_flight_lengths,
        )
    else:
        _cleanup_resume_files(temp_file, state_file)
        with temp_file.open("wb") as file:
            file.truncate(remote_info.total_size)
        piece_storage = seed_storage

    segment_manager = _SegmentManager(piece_storage, options.min_split_size)
    completed_size = piece_storage.completed_size()
    progress_lock = threading.Lock()
    state_lock = threading.Lock()
    stop_event = cancel_event or threading.Event()
    range_ignored_event = threading.Event()
    completed_since_state_save = 0
    last_state_save = time.monotonic()
    uri_pool = _UriPool(urls, options.max_connection_per_server, host_keys=uri_host_keys)
    worker_count = max(1, min(options.split, piece_storage.piece_count, uri_pool.capacity))
    session_pool = _ThreadLocalSessionPool(pool_size=worker_count)
    if_range = remote_info.etag if remote_info.etag and not remote_info.etag.strip().startswith("W/") else remote_info.last_modified
    metrics_started = time.monotonic()
    last_progress_at = metrics_started
    callback_completed_size = completed_size

    def _update_progress(delta: int, current_url: str) -> None:
        nonlocal callback_completed_size, last_progress_at
        with progress_lock:
            progress_bar.update(delta)
            now = time.monotonic()
            interval = max(now - last_progress_at, 1e-9)
            callback_completed_size += delta
            if progress_callback is not None:
                progress_callback(
                    DownloadProgressEvent(
                        target_path=temp_file.with_name(temp_file.name.removesuffix(".tmp")),
                        total_size=remote_info.total_size,
                        completed_size=callback_completed_size,
                        instantaneous_speed=delta / interval,
                        average_speed=(callback_completed_size - completed_size) / max(now - metrics_started, 1e-9),
                        active_connections=sum(uri_pool.in_flight.values()),
                        current_url=current_url,
                    )
                )
            last_progress_at = now
        _maybe_flush_state()

    def _flush_state() -> None:
        nonlocal last_state_save
        _flush_download_data(temp_file)
        _save_resume_state(
            state_file,
            urls=urls,
            remote_info=remote_info,
            options=options,
            piece_storage=piece_storage,
        )
        last_state_save = time.monotonic()

    def _maybe_flush_state(*, force: bool = False) -> None:
        nonlocal completed_since_state_save
        with state_lock:
            save_due_to_piece_count = completed_since_state_save >= STATE_SAVE_COMPLETED_PIECE_INTERVAL
            save_due_to_time = time.monotonic() - last_state_save >= STATE_SAVE_INTERVAL_SECONDS
            if force or save_due_to_piece_count or save_due_to_time:
                _flush_state()
                completed_since_state_save = 0

    def _mark_segment_complete(segment: _Segment) -> None:
        nonlocal completed_since_state_save
        newly_completed = segment_manager.mark_complete(segment)
        with state_lock:
            completed_since_state_save += newly_completed
            if completed_since_state_save >= STATE_SAVE_COMPLETED_PIECE_INTERVAL or piece_storage.is_complete():
                _flush_state()
                completed_since_state_save = 0

    def _worker() -> None:
        owner_id = threading.get_ident()
        while not stop_event.is_set():
            segment = segment_manager.get_segment(owner_id)
            if segment is None:
                return
            try:
                _download_stream_with_retries(
                    session_pool,
                    uri_pool=uri_pool,
                    temp_file=temp_file,
                    segment=segment,
                    total_size=remote_info.total_size,
                    timeout=timeout,
                    max_tries=options.max_tries,
                    retry_wait=options.retry_wait,
                    if_range=if_range,
                    digest_tracker=digest_tracker,
                    cancel_event=stop_event,
                    lowest_speed_limit=options.lowest_speed_limit,
                    lowest_speed_time=options.lowest_speed_time,
                    stop_event=stop_event,
                    segment_manager=segment_manager,
                    mark_complete_callback=_mark_segment_complete,
                    progress_callback=_update_progress,
                )
            except _RangeRequestIgnored:
                range_ignored_event.set()
                segment_manager.release(segment)
                return
            except Exception:
                segment_manager.release(segment)
                raise

    with tqdm(
        total=remote_info.total_size,
        initial=completed_size,
        unit="B",
        unit_scale=True,
        desc=temp_file.name.removesuffix(".tmp"),
        disable=not progress,
    ) as progress_bar:
        try:
            if not piece_storage.is_complete():
                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    futures = [executor.submit(_worker) for _ in range(worker_count)]
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception:
                            stop_event.set()
                            for pending in futures:
                                pending.cancel()
                            raise
        except Exception:
            _maybe_flush_state(force=True)
            raise
        finally:
            session_pool.close_all()

    if not piece_storage.is_complete():
        _maybe_flush_state(force=True)
        if range_ignored_event.is_set():
            raise _RangeDownloadNotSupported("远端忽略 Range 请求")
        raise IOError("分片下载未完成")
    if temp_file.stat().st_size != remote_info.total_size:
        raise IOError(f"下载文件大小不匹配: 期望 {remote_info.total_size}, 实际 {temp_file.stat().st_size}")


def _download_file_single_stream_once(
    url: str,
    temp_file: Path,
    file_name: str,
    progress: bool,
    attempt: int,
    retry_wait: int,
    digest_tracker: _DigestTracker,
    timeout: Any,
    cancel_event: threading.Event,
    lowest_speed_limit: int,
    lowest_speed_time: int,
    progress_callback: Any | None,
) -> int:
    import requests

    try:
        from tqdm import tqdm
    except ImportError:
        from sd_webui_all_in_one.simple_tqdm import SimpleTqdm as tqdm

    response = requests.get(url, stream=True, timeout=timeout, headers=_request_headers())
    try:
        digest_tracker.observe(_get_header(response.headers, "Digest"))
        status_code = int(response.status_code or 0)
        if status_code in RETRYABLE_STATUS_CODES:
            raise _RangeDownloadTemporaryError(
                f"HTTP {status_code}",
                retry_delay=_retry_delay_for(response.headers, attempt, status_code=status_code, retry_wait=retry_wait),
            )
        if status_code >= 400:
            raise DownloadPermanentHttpError(url=url, status_code=status_code, segment=None, attempt=attempt)
        response.raise_for_status()
        if _get_header(response.headers, "Transfer-Encoding") is not None or _content_encoding_requires_single_stream(_get_header(response.headers, "Content-Encoding")):
            total_size = 0
        else:
            total_size = _parse_int_header(response.headers, "Content-Length")
        completed_size = 0
        metrics_started = time.monotonic()
        last_progress_at = metrics_started
        speed_window_started = metrics_started
        speed_window_bytes = 0
        with tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            desc=file_name,
            disable=not progress,
        ) as progress_bar:
            with open(temp_file, "wb") as file:
                for chunk in response.iter_content(chunk_size=STREAM_CHUNK_SIZE):
                    if cancel_event.is_set():
                        raise DownloadCancelledError("下载已取消")
                    if chunk:
                        file.write(chunk)
                        progress_bar.update(len(chunk))
                        completed_size += len(chunk)
                        speed_window_bytes += len(chunk)
                        now = time.monotonic()
                        if progress_callback is not None:
                            progress_callback(
                                DownloadProgressEvent(
                                    target_path=temp_file.with_name(temp_file.name.removesuffix(".tmp")),
                                    total_size=total_size,
                                    completed_size=completed_size,
                                    instantaneous_speed=len(chunk) / max(now - last_progress_at, 1e-9),
                                    average_speed=completed_size / max(now - metrics_started, 1e-9),
                                    active_connections=1,
                                    current_url=url,
                                )
                            )
                        last_progress_at = now
                        speed_window_elapsed = now - speed_window_started
                        if lowest_speed_limit > 0 and lowest_speed_time > 0 and speed_window_elapsed >= lowest_speed_time:
                            current_speed = speed_window_bytes / max(speed_window_elapsed, 1e-9)
                            if current_speed < lowest_speed_limit:
                                raise DownloadLowSpeedError(f"镜像 {url} 在 {speed_window_elapsed:.1f}s 内速度 {current_speed:.1f} B/s 低于 {lowest_speed_limit} B/s")
                            speed_window_started = now
                            speed_window_bytes = 0
        return total_size
    finally:
        _close_response(response)


def _download_file_single_stream(
    urls: list[str],
    temp_file: Path,
    file_name: str,
    progress: bool,
    max_tries: int,
    retry_wait: int,
    digest_tracker: _DigestTracker,
    timeout: Any,
    cancel_event: threading.Event,
    lowest_speed_limit: int,
    lowest_speed_time: int,
    progress_callback: Any | None,
) -> int:
    attempts_by_url: Counter[str] = Counter()
    permanent_errors: dict[str, str] = {}
    last_error: Exception | None = None
    last_url: str | None = None
    total_attempt_limit = max_tries * len(urls)
    while max_tries == 0 or sum(attempts_by_url.values()) < total_attempt_limit:
        available_urls = [url for url in urls if url not in permanent_errors and (max_tries == 0 or attempts_by_url[url] < max_tries)]
        if not available_urls:
            break
        url = available_urls[sum(attempts_by_url.values()) % len(available_urls)]
        attempts_by_url[url] += 1
        request_attempt = attempts_by_url[url]
        try:
            return _download_file_single_stream_once(
                url=url,
                temp_file=temp_file,
                file_name=file_name,
                progress=progress,
                attempt=request_attempt,
                retry_wait=retry_wait,
                digest_tracker=digest_tracker,
                timeout=timeout,
                cancel_event=cancel_event,
                lowest_speed_limit=lowest_speed_limit,
                lowest_speed_time=lowest_speed_time,
                progress_callback=progress_callback,
            )
        except DownloadCancelledError:
            raise
        except DownloadIntegrityError as e:
            permanent_errors[url] = str(e)
            last_error = e
            last_url = url
            continue
        except DownloadPermanentHttpError as e:
            last_url = url
            permanent_errors[url] = str(e)
            last_error = e
            continue
        except Exception as e:
            last_url = url
            classified_error = _classify_network_error(e)
            last_error = classified_error
            delay = (
                classified_error.retry_delay if isinstance(classified_error, _RangeDownloadTemporaryError) and classified_error.retry_delay is not None else _retry_delay_with_jitter(request_attempt)
            )
            logger.warning("镜像 %s 单流下载失败 [%s/%s]: %s, %.1fs 后重试", url, request_attempt, max_tries, classified_error, delay)
            attempts_remain = max_tries == 0 or any(attempts_by_url[candidate] < max_tries for candidate in urls if candidate not in permanent_errors)
            if attempts_remain and len(available_urls) == 1:
                time.sleep(delay)

    if len(urls) == 1 and isinstance(last_error, DownloadPermanentHttpError):
        raise last_error
    raise DownloadTransientError(f"所有镜像的单流下载预算已耗尽: attempts={dict(attempts_by_url)}, permanent={permanent_errors}, last_url={last_url}, last_error={last_error}") from last_error


def _apply_remote_time(
    cached_file: Path,
    last_modified: str | None,
) -> None:
    if not last_modified:
        return
    try:
        remote_time = parsedate_to_datetime(last_modified).timestamp()
    except (TypeError, ValueError, OverflowError) as e:
        logger.debug("无法解析 Last-Modified 时间 '%s': %s", last_modified, e)
        return
    try:
        current_atime = cached_file.stat().st_atime
        import os

        os.utime(cached_file, (current_atime, remote_time))
    except OSError as e:
        logger.debug("无法应用远端 Last-Modified 时间到 '%s': %s", cached_file, e)


def _finalize_download(
    *,
    temp_file: Path,
    state_file: Path,
    cached_file: Path,
    file_name: str,
    hash_prefix: str | None,
    hash_algorithm: str,
    remote_time: bool,
    last_modified: str | None,
    expected_size: int = 0,
) -> None:
    if expected_size > 0:
        actual_size = temp_file.stat().st_size
        if actual_size < expected_size:
            logger.error("'%s' 下载大小不足, 正在删除临时文件", temp_file)
            _cleanup_resume_files(temp_file, state_file)
            raise DownloadSizeIntegrityError(f"下载文件大小不足: 期望 {expected_size}, 实际 {actual_size}")
        if actual_size > expected_size:
            logger.warning("'%s' 包含多余尾部数据, 将截断到 %s 字节", temp_file, expected_size)
            with temp_file.open("r+b") as file:
                file.truncate(expected_size)

    if hash_prefix and not compare_hash(temp_file, hash_prefix, hash_algorithm):
        logger.error("'%s' 的哈希值不匹配, 正在删除临时文件", temp_file)
        _cleanup_resume_files(temp_file, state_file)
        raise DownloadIntegrityError(f"文件 {hash_algorithm} 哈希值与预期值不匹配: {hash_prefix}")

    temp_file.replace(cached_file)
    if remote_time:
        _apply_remote_time(cached_file, last_modified)
    state_file.unlink(missing_ok=True)
    logger.info("'%s' 下载完成", file_name)


def _normalize_options(
    *,
    split: int,
    max_connection_per_server: int,
    min_split_size: int,
    piece_length: int,
    allow_piece_length_change: bool,
    max_tries: int,
    retry_wait: int,
    continue_download: bool,
    conditional_get: bool,
    remote_time: bool,
    always_resume: bool = True,
    max_resume_failure_tries: int = 0,
    connect_timeout: int = 60,
    read_timeout: int = 60,
    lowest_speed_limit: int = 0,
    lowest_speed_time: int = 0,
) -> _DownloadOptions:
    def _normalize_int_option(
        name: str,
        value: int,
        *,
        minimum: int,
        maximum: int | None = None,
    ) -> int:
        try:
            normalized = int(value)
        except (TypeError, ValueError) as e:
            raise DownloadConfigurationError(f"{name} 必须是整数") from e
        if normalized < minimum:
            raise DownloadConfigurationError(f"{name} 必须大于等于 {minimum}")
        if maximum is not None and normalized > maximum:
            raise DownloadConfigurationError(f"{name} 必须小于等于 {maximum}")
        return normalized

    return _DownloadOptions(
        split=_normalize_int_option("split", split, minimum=1),
        max_connection_per_server=_normalize_int_option(
            "max_connection_per_server",
            max_connection_per_server,
            minimum=1,
            maximum=MAX_CONNECTION_PER_SERVER_MAX,
        ),
        min_split_size=_normalize_int_option(
            "min_split_size",
            min_split_size,
            minimum=ARIA2_SIZE_OPTION_MIN,
            maximum=ARIA2_SIZE_OPTION_MAX,
        ),
        piece_length=_normalize_int_option(
            "piece_length",
            piece_length,
            minimum=ARIA2_SIZE_OPTION_MIN,
            maximum=ARIA2_SIZE_OPTION_MAX,
        ),
        allow_piece_length_change=bool(allow_piece_length_change),
        max_tries=_normalize_int_option("max_tries", max_tries, minimum=0),
        retry_wait=_normalize_int_option("retry_wait", retry_wait, minimum=0, maximum=600),
        continue_download=bool(continue_download),
        conditional_get=bool(conditional_get),
        remote_time=bool(remote_time),
        always_resume=bool(always_resume),
        max_resume_failure_tries=_normalize_int_option(
            "max_resume_failure_tries",
            max_resume_failure_tries,
            minimum=0,
        ),
        connect_timeout=_normalize_int_option("connect_timeout", connect_timeout, minimum=1, maximum=600),
        read_timeout=_normalize_int_option("read_timeout", read_timeout, minimum=1, maximum=600),
        lowest_speed_limit=_normalize_int_option("lowest_speed_limit", lowest_speed_limit, minimum=0),
        lowest_speed_time=_normalize_int_option("lowest_speed_time", lowest_speed_time, minimum=0),
    )


def download_file_from_url(
    url: _UrlInput,
    save_path: Path | None = None,
    file_name: str | None = None,
    progress: bool = True,
    hash_prefix: str | None = None,
    hash_value: str | None = None,
    hash_algorithm: str = "sha256",
    re_download: bool = False,
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
    existing_file_policy: ExistingFilePolicy | None = None,
    connect_timeout: int = 60,
    read_timeout: int = 60,
    lowest_speed_limit: int = 0,
    lowest_speed_time: int = 0,
    progress_callback: Any | None = None,
    cancel_event: threading.Event | None = None,
) -> Path:
    """使用 requests 库下载文件

    Args:
        url (_UrlInput):
            下载链接或同一文件的镜像链接列表
        save_path (Path | None):
            下载路径
        file_name (str | None):
            保存的文件名, 如果为`None`则从`url`中提取文件
        progress (bool):
            是否启用下载进度条
        hash_prefix (str | None):
            sha256 十六进制字符串, 如果提供, 将检查下载文件的哈希值是否与此前缀匹配, 当不匹配时引发`ValueError`
        hash_value (str | None):
            指定算法的完整哈希值或十六进制前缀，优先于 hash_prefix
        hash_algorithm (str):
            hash_value 使用的算法，可选 sha1、sha256、sha512
        re_download (bool):
            强制重新下载文件
        split (int):
            aria2 风格的单文件最大分割数
        max_connection_per_server (int):
            aria2 风格的单服务器最大连接数
        min_split_size (int):
            aria2 风格的最小切分大小
        piece_length (int):
            aria2 风格的 piece 大小
        allow_piece_length_change (bool):
            piece_length 与已有控制文件不一致时, 是否允许转换已完成 bitfield 并丢弃 in-flight 进度
        continue_download (bool):
            没有匹配 state 文件时, 是否从已有临时文件推断断点续传进度
        max_tries (int):
            单个分片的最大尝试次数
        retry_wait (int):
            HTTP 503 重试前等待秒数, 取值范围 0..600
        conditional_get (bool):
            已有本地文件时是否发送 If-Modified-Since, 远端返回 304 时复用本地文件
        remote_time (bool):
            下载完成后是否把本地文件 mtime 设置为远端 Last-Modified
        always_resume (bool):
            已有进度无法可靠续传时是否报错并保留断点, 默认为 True
        max_resume_failure_tries (int):
            always_resume=False 时允许重头下载前的续传失败阈值, 0 表示所有 URI 均失败后重头下载
        existing_file_policy (ExistingFilePolicy | None):
            已有正式文件的处理策略；None 保持兼容映射（re_download=overwrite、continue_download=resume，否则 reuse）

    Returns:
        Path: 下载的文件路径

    Raises:
        ValueError: 当提供了 hash_prefix 但文件哈希值不匹配时
        IOError: 下载过程中发生 IO 异常
    """

    if save_path is None:
        save_path = Path.cwd()

    urls = _normalize_urls(url)
    normalized_hash_algorithm = normalize_hash_algorithm(hash_algorithm)
    explicit_hash_value = hash_value or hash_prefix
    explicit_hash_algorithm = normalized_hash_algorithm if hash_value else "sha256"
    explicit_hash_is_strong = _is_full_hash(explicit_hash_value, explicit_hash_algorithm)
    explicit_file_name = file_name is not None
    if file_name is None:
        file_name = _filename_from_url(urls[0])
    else:
        file_name = validate_download_file_name(file_name)
    cached_file = save_path.resolve() / file_name
    cached_file_exists = cached_file.exists()
    effective_existing_policy = _resolve_existing_file_policy(
        existing_file_policy,
        re_download=re_download,
        continue_download=continue_download,
    )

    if cached_file_exists and effective_existing_policy == "reuse" and not conditional_get:
        if explicit_hash_value and not compare_hash(cached_file, explicit_hash_value, explicit_hash_algorithm):
            raise DownloadIntegrityError(f"已有文件哈希值 ({explicit_hash_algorithm}) 与预期值不匹配: {explicit_hash_value}")
        logger.info("'%s' 已存在于 '%s' 中", file_name, cached_file)
        return cached_file

    if cached_file_exists and not re_download and conditional_get and _cached_file_not_modified(urls, cached_file):
        logger.info("'%s' 未修改, 复用 '%s'", file_name, cached_file)
        return cached_file
    if conditional_get and cached_file_exists:
        effective_existing_policy = "overwrite"

    if effective_existing_policy != "reuse" or not cached_file_exists or conditional_get:
        save_path.mkdir(parents=True, exist_ok=True)

        options = _normalize_options(
            split=split,
            max_connection_per_server=max_connection_per_server,
            min_split_size=min_split_size,
            piece_length=piece_length,
            allow_piece_length_change=allow_piece_length_change,
            max_tries=max_tries,
            retry_wait=retry_wait,
            continue_download=continue_download,
            conditional_get=conditional_get,
            remote_time=remote_time,
            always_resume=always_resume,
            max_resume_failure_tries=max_resume_failure_tries,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            lowest_speed_limit=lowest_speed_limit,
            lowest_speed_time=lowest_speed_time,
        )
        probe_result = _probe_remote_files(urls, timeout=(options.connect_timeout, options.read_timeout))
        primary_url = probe_result.primary_url
        remote_info = probe_result.remote_info
        digest_tracker = _DigestTracker(remote_info.digest_algorithm, remote_info.digest_value)
        ordered_urls = [primary_url] + [candidate for candidate in urls if candidate != primary_url]
        if not explicit_file_name and remote_info.content_disposition_filename:
            file_name = remote_info.content_disposition_filename
            cached_file = save_path.resolve() / file_name
            cached_file_exists = cached_file.exists()
            if effective_existing_policy == "reuse" and not conditional_get and cached_file_exists:
                if explicit_hash_value and not compare_hash(cached_file, explicit_hash_value, explicit_hash_algorithm):
                    raise DownloadIntegrityError(f"已有文件哈希值 ({explicit_hash_algorithm}) 与预期值不匹配: {explicit_hash_value}")
                logger.info("'%s' 已存在于 '%s' 中", file_name, cached_file)
                return cached_file

        if effective_existing_policy == "rename" and cached_file.exists():
            cached_file = _renamed_file_path(cached_file)
            file_name = cached_file.name
            cached_file_exists = False

        with _target_download_lock(cached_file):
            # 探测在锁外进行；等待同目标任务完成后必须重新检查最终文件，
            # 后来的重复任务直接复用先完成任务的原子结果。
            if cached_file.exists() and not re_download and not cached_file_exists:
                logger.info("'%s' 已由另一下载任务保存到 '%s'", file_name, cached_file)
                return cached_file

            if cached_file.exists() and effective_existing_policy == "reuse" and not conditional_get:
                if explicit_hash_value and not compare_hash(cached_file, explicit_hash_value, explicit_hash_algorithm):
                    raise DownloadIntegrityError(f"已有文件哈希值 ({explicit_hash_algorithm}) 与预期值不匹配: {explicit_hash_value}")
                return cached_file
            if cached_file.exists() and effective_existing_policy == "verify":
                if explicit_hash_value:
                    if not compare_hash(cached_file, explicit_hash_value, explicit_hash_algorithm):
                        raise DownloadIntegrityError(f"已有文件哈希值 ({explicit_hash_algorithm}) 与预期值不匹配: {explicit_hash_value}")
                else:
                    _verify_existing_file(cached_file, remote_info=remote_info, hash_prefix=None)
                logger.info("'%s' 已通过大小或哈希校验, 复用 '%s'", file_name, cached_file)
                return cached_file

            temp_file = save_path / f"{file_name}.tmp"
            state_file = _state_path_for(temp_file)
            if effective_existing_policy == "overwrite":
                _cleanup_resume_files(temp_file, state_file)
            elif effective_existing_policy == "resume" and cached_file.exists():
                local_size = cached_file.stat().st_size
                if remote_info.total_size <= 0:
                    raise IOError("远端未提供文件大小，无法把已有正式文件作为断点")
                if local_size > remote_info.total_size:
                    raise IOError(f"已有文件大于远端文件: 远端 {remote_info.total_size}, 本地 {local_size}")
                if local_size == remote_info.total_size:
                    tracker_hash = digest_tracker.expected()
                    expected_hash = (explicit_hash_algorithm, explicit_hash_value) if explicit_hash_value else tracker_hash
                    if expected_hash and not compare_hash(cached_file, expected_hash[1], expected_hash[0]):
                        raise ValueError(f"已有文件哈希值与预期的哈希前缀不匹配: {expected_hash}")
                    logger.info("'%s' 大小已完整, 复用 '%s'", file_name, cached_file)
                    return cached_file
                _cleanup_resume_files(temp_file, state_file)
                shutil.copyfile(cached_file, temp_file)
                options = replace(options, continue_download=True)

            logger.info("下载 '%s' 到 '%s' 中", file_name, cached_file)
            expected_size = remote_info.total_size
            resume_progress_size = _resume_progress_size(
                temp_file=temp_file,
                state_file=state_file,
                remote_info=remote_info,
                options=options,
                allow_validator_change=explicit_hash_is_strong,
            )

            def _restart_with_single_stream(reason: str) -> int:
                if resume_progress_size > 0:
                    logger.warning(
                        "无法继续下载 '%s' (%s), 将丢弃 %s 字节已有进度并从头下载",
                        file_name,
                        reason,
                        resume_progress_size,
                    )
                _cleanup_resume_files(temp_file, state_file)
                stream_size = _download_file_single_stream(
                    urls=ordered_urls,
                    temp_file=temp_file,
                    file_name=file_name,
                    progress=bool(progress),
                    max_tries=options.max_tries,
                    retry_wait=options.retry_wait,
                    digest_tracker=digest_tracker,
                    timeout=(options.connect_timeout, options.read_timeout),
                    cancel_event=cancel_event or threading.Event(),
                    lowest_speed_limit=options.lowest_speed_limit,
                    lowest_speed_time=options.lowest_speed_time,
                    progress_callback=progress_callback,
                )
                return stream_size or remote_info.total_size

            if remote_info.total_size > 0 and remote_info.supports_range:
                try:
                    _download_file_with_ranges(
                        urls=probe_result.range_urls,
                        uri_host_keys=probe_result.range_host_keys,
                        temp_file=temp_file,
                        state_file=state_file,
                        remote_info=remote_info,
                        progress=bool(progress),
                        options=options,
                        digest_tracker=digest_tracker,
                        allow_validator_change=explicit_hash_is_strong,
                        timeout=(options.connect_timeout, options.read_timeout),
                        progress_callback=progress_callback,
                        cancel_event=cancel_event,
                    )
                except _RangeDownloadNotSupported as e:
                    failure_count = min(len(urls), probe_result.resume_failure_count + 1)
                    if resume_progress_size == 0 or _resume_policy_allows_restart(
                        options,
                        failure_count=failure_count,
                        total_url_count=len(urls),
                    ):
                        expected_size = _restart_with_single_stream(str(e))
                    else:
                        logger.error("无法使用 HTTP Range 继续下载 '%s': %s, 已保留临时文件和断点状态", file_name, e)
                        raise IOError(f"无法使用 HTTP Range 继续下载 '{file_name}': {e}") from e
            elif remote_info.total_size > 0:
                if resume_progress_size > 0 and not _resume_policy_allows_restart(
                    options,
                    failure_count=probe_result.resume_failure_count,
                    total_url_count=len(urls),
                ):
                    logger.error("远端不支持 HTTP Range, 无法继续下载 '%s', 已保留临时文件和断点状态", file_name)
                    raise IOError(f"远端不支持 HTTP Range, 无法继续下载 '{file_name}'")
                expected_size = _restart_with_single_stream("远端不支持 HTTP Range")
            else:
                if resume_progress_size > 0 and not _resume_policy_allows_restart(
                    options,
                    failure_count=probe_result.resume_failure_count,
                    total_url_count=len(urls),
                ):
                    logger.error("远端未提供可靠的 Range 元数据, 无法继续下载 '%s', 已保留临时文件和断点状态", file_name)
                    raise IOError(f"远端未提供可靠的 Range 元数据, 无法继续下载 '{file_name}'")
                expected_size = _restart_with_single_stream("远端未提供可靠的 Range 元数据")

            tracker_hash = digest_tracker.expected()
            final_hash = (explicit_hash_algorithm, explicit_hash_value) if explicit_hash_value else tracker_hash
            _finalize_download(
                temp_file=temp_file,
                state_file=state_file,
                cached_file=cached_file,
                file_name=file_name,
                hash_prefix=final_hash[1] if final_hash else None,
                hash_algorithm=final_hash[0] if final_hash else "sha256",
                remote_time=options.remote_time,
                last_modified=remote_info.last_modified,
                expected_size=expected_size,
            )
    return cached_file
