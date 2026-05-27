"""Requests 下载器"""

import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sd_webui_all_in_one.downloader.hash_utils import compare_sha256
from sd_webui_all_in_one.downloader.types import DEFAULT_USER_AGENT
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)


DEFAULT_RANGE_CHUNK_SIZE = 1024 * 1024
"""HTTP Range 分片大小"""

STATE_VERSION = 1
"""HTTP Range 断点续传状态版本"""

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
"""分片下载时可重试的 HTTP 状态码"""


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class _RangeDownloadNotSupported(RuntimeError):
    """远端不支持可靠的 HTTP Range 下载"""


class _RangeDownloadTemporaryError(RuntimeError):
    """分片下载过程中的可重试错误"""

    def __init__(
        self,
        message: str,
        retry_delay: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_delay = retry_delay


@dataclass(frozen=True)
class _RemoteFileInfo:
    """远端文件元数据"""

    total_size: int
    supports_range: bool
    etag: str | None = None
    last_modified: str | None = None


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


def _parse_content_range_total(
    content_range: str | None,
) -> int:
    if not content_range:
        return 0

    match = re.match(r"bytes\s+\d+-\d+/(\d+|\*)", content_range.strip(), flags=re.IGNORECASE)
    if not match or match.group(1) == "*":
        return 0
    try:
        return int(match.group(1))
    except ValueError:
        return 0


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
        "Accept-Encoding": "identity",
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def _probe_remote_file(
    requests_module: object,
    url: str,
    timeout: int = 60,
) -> _RemoteFileInfo:
    """探测远端是否支持 HTTP Range 下载"""
    head_func = getattr(requests_module, "head", None)
    if not callable(head_func):
        return _RemoteFileInfo(total_size=0, supports_range=False)

    total_size = 0
    etag: str | None = None
    last_modified: str | None = None
    supports_range = False

    try:
        response = head_func(url, allow_redirects=True, timeout=timeout, headers=_request_headers())
        try:
            status_code = int(getattr(response, "status_code", 0) or 0)
            if 200 <= status_code < 400:
                headers = getattr(response, "headers", {})
                total_size = _parse_int_header(headers, "Content-Length")
                etag = _get_header(headers, "ETag")
                last_modified = _get_header(headers, "Last-Modified")
                supports_range = (_get_header(headers, "Accept-Ranges") or "").lower() == "bytes"
        finally:
            _close_response(response)
    except Exception as e:
        logger.debug("HEAD 探测失败, 尝试使用 Range 请求探测: %s", e)

    get_func = getattr(requests_module, "get", None)
    if not callable(get_func):
        return _RemoteFileInfo(total_size=total_size, supports_range=supports_range and total_size > 0, etag=etag, last_modified=last_modified)

    if not supports_range or total_size <= 0:
        try:
            response = get_func(url, stream=True, timeout=timeout, headers=_request_headers({"Range": "bytes=0-0"}))
            try:
                status_code = int(getattr(response, "status_code", 0) or 0)
                if status_code == 206:
                    headers = getattr(response, "headers", {})
                    content_range_total = _parse_content_range_total(_get_header(headers, "Content-Range"))
                    total_size = content_range_total or total_size
                    etag = etag or _get_header(headers, "ETag")
                    last_modified = last_modified or _get_header(headers, "Last-Modified")
                    supports_range = total_size > 0
            finally:
                _close_response(response)
        except Exception as e:
            logger.debug("Range 探测失败, 将使用单连接下载: %s", e)

    return _RemoteFileInfo(total_size=total_size, supports_range=supports_range and total_size > 0, etag=etag, last_modified=last_modified)


def _state_path_for(
    temp_file: Path,
) -> Path:
    return temp_file.with_name(f"{temp_file.name}.state.json")


def _cleanup_resume_files(
    temp_file: Path,
    state_file: Path,
) -> None:
    temp_file.unlink(missing_ok=True)
    state_file.unlink(missing_ok=True)


def _load_resume_state(
    state_file: Path,
) -> dict[str, object] | None:
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _state_matches_remote(
    state: dict[str, object] | None,
    *,
    url: str,
    remote_info: _RemoteFileInfo,
    chunk_size: int,
) -> bool:
    if not state:
        return False

    return (
        state.get("version") == STATE_VERSION
        and state.get("url") == url
        and state.get("total_size") == remote_info.total_size
        and state.get("etag") == remote_info.etag
        and state.get("last_modified") == remote_info.last_modified
        and state.get("chunk_size") == chunk_size
    )


def _normalize_completed_ranges(
    state: dict[str, object] | None,
    total_size: int,
) -> set[tuple[int, int]]:
    raw_ranges = state.get("completed_ranges", []) if state else []
    completed_ranges: set[tuple[int, int]] = set()
    if not isinstance(raw_ranges, list):
        return completed_ranges

    for raw_range in raw_ranges:
        if not isinstance(raw_range, list | tuple) or len(raw_range) != 2:
            continue
        start, end = raw_range
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if 0 <= start <= end < total_size:
            completed_ranges.add((start, end))
    return completed_ranges


def _save_resume_state(
    state_file: Path,
    *,
    url: str,
    remote_info: _RemoteFileInfo,
    chunk_size: int,
    completed_ranges: set[tuple[int, int]],
) -> None:
    state = {
        "version": STATE_VERSION,
        "url": url,
        "total_size": remote_info.total_size,
        "etag": remote_info.etag,
        "last_modified": remote_info.last_modified,
        "chunk_size": chunk_size,
        "completed_ranges": [list(item) for item in sorted(completed_ranges)],
    }
    tmp_state_file = state_file.with_name(f"{state_file.name}.tmp")
    tmp_state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_state_file.replace(state_file)


def _build_ranges(
    total_size: int,
    chunk_size: int,
) -> list[tuple[int, int]]:
    return [(start, min(start + chunk_size - 1, total_size - 1)) for start in range(0, total_size, chunk_size)]


def _retry_delay_for(
    headers: Any,
    attempt: int,
) -> float:
    retry_after = _get_header(headers, "Retry-After")
    if retry_after:
        try:
            return min(float(retry_after), 30.0)
        except ValueError:
            pass
    return min(0.5 * attempt, 5.0)


def _download_range_once(
    requests_module: Any,
    *,
    url: str,
    temp_file: Path,
    byte_range: tuple[int, int],
    timeout: int,
) -> int:
    start, end = byte_range
    response = requests_module.get(url, stream=True, timeout=timeout, headers=_request_headers({"Range": f"bytes={start}-{end}"}))
    try:
        status_code = int(getattr(response, "status_code", 0) or 0)
        headers = getattr(response, "headers", {})

        if status_code == 200:
            raise _RangeDownloadNotSupported("远端忽略 Range 请求")
        if status_code in {416}:
            raise _RangeDownloadNotSupported(f"远端拒绝 Range 请求: HTTP {status_code}")
        if status_code in RETRYABLE_STATUS_CODES:
            raise _RangeDownloadTemporaryError(f"HTTP {status_code}", retry_delay=_retry_delay_for(headers, 1))
        if status_code != 206:
            raise RuntimeError(f"Range 请求返回非预期状态码: HTTP {status_code}")

        expected_size = end - start + 1
        downloaded_size = 0
        offset = start
        with temp_file.open("r+b") as file:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                if downloaded_size + len(chunk) > expected_size:
                    chunk = chunk[: expected_size - downloaded_size]
                file.seek(offset)
                file.write(chunk)
                offset += len(chunk)
                downloaded_size += len(chunk)

        if downloaded_size != expected_size:
            raise IOError(f"分片大小不匹配: 期望 {expected_size}, 实际 {downloaded_size}")
        return downloaded_size
    finally:
        _close_response(response)


def _download_range_with_retries(
    requests_module: Any,
    *,
    url: str,
    temp_file: Path,
    byte_range: tuple[int, int],
    timeout: int,
    max_retries: int,
) -> int:
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return _download_range_once(
                requests_module,
                url=url,
                temp_file=temp_file,
                byte_range=byte_range,
                timeout=timeout,
            )
        except _RangeDownloadNotSupported:
            raise
        except Exception as e:
            last_error = e
            if attempt >= max_retries:
                break
            delay = e.retry_delay if isinstance(e, _RangeDownloadTemporaryError) and e.retry_delay is not None else min(0.5 * attempt, 5.0)
            logger.warning("分片 %s 下载失败 [%s/%s]: %s, %.1fs 后重试", byte_range, attempt, max_retries, e, delay)
            time.sleep(delay)
    raise IOError(f"分片 {byte_range} 下载失败: {last_error}") from last_error


def _download_file_with_ranges(
    requests_module: Any,
    *,
    url: str,
    temp_file: Path,
    state_file: Path,
    remote_info: _RemoteFileInfo,
    progress: bool,
    tqdm_class: Any,
    resume: bool,
    max_retries: int,
    num_threads: int,
    chunk_size: int,
    timeout: int = 60,
) -> None:
    if remote_info.total_size <= 0 or not remote_info.supports_range:
        raise _RangeDownloadNotSupported("远端未提供可分片下载的文件大小或 Range 支持")

    state = _load_resume_state(state_file) if resume else None
    if resume and temp_file.exists() and _state_matches_remote(state, url=url, remote_info=remote_info, chunk_size=chunk_size) and temp_file.stat().st_size == remote_info.total_size:
        completed_ranges = _normalize_completed_ranges(state, remote_info.total_size)
    else:
        _cleanup_resume_files(temp_file, state_file)
        completed_ranges = set()
        with temp_file.open("wb") as file:
            file.truncate(remote_info.total_size)

    all_ranges = _build_ranges(remote_info.total_size, chunk_size)
    completed_ranges &= set(all_ranges)
    pending_ranges = [item for item in all_ranges if item not in completed_ranges]
    completed_size = sum(end - start + 1 for start, end in completed_ranges)
    progress_lock = threading.Lock()
    state_lock = threading.Lock()

    with tqdm_class(
        total=remote_info.total_size,
        initial=completed_size,
        unit="B",
        unit_scale=True,
        desc=temp_file.name.removesuffix(".tmp"),
        disable=not progress,
    ) as progress_bar:
        if not pending_ranges:
            return

        worker_count = max(1, min(num_threads, len(pending_ranges)))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_range = {
                executor.submit(
                    _download_range_with_retries,
                    requests_module,
                    url=url,
                    temp_file=temp_file,
                    byte_range=byte_range,
                    timeout=timeout,
                    max_retries=max_retries,
                ): byte_range
                for byte_range in pending_ranges
            }

            for future in as_completed(future_to_range):
                byte_range = future_to_range[future]
                downloaded_size = future.result()
                with state_lock:
                    completed_ranges.add(byte_range)
                    _save_resume_state(
                        state_file,
                        url=url,
                        remote_info=remote_info,
                        chunk_size=chunk_size,
                        completed_ranges=completed_ranges,
                    )
                with progress_lock:
                    progress_bar.update(downloaded_size)

    if temp_file.stat().st_size != remote_info.total_size:
        raise IOError(f"下载文件大小不匹配: 期望 {remote_info.total_size}, 实际 {temp_file.stat().st_size}")


def _download_file_single_stream(
    requests_module: Any,
    *,
    url: str,
    temp_file: Path,
    file_name: str,
    progress: bool,
    tqdm_class: Any,
) -> None:
    response = requests_module.get(url, stream=True, timeout=60)
    try:
        response.raise_for_status()
        total_size = _parse_int_header(response.headers, "Content-Length")
        with tqdm_class(
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
    finally:
        _close_response(response)


def _finalize_download(
    *,
    temp_file: Path,
    state_file: Path,
    cached_file: Path,
    file_name: str,
    hash_prefix: str | None,
) -> None:
    if hash_prefix and not compare_sha256(temp_file, hash_prefix):
        logger.error("'%s' 的哈希值不匹配, 正在删除临时文件", temp_file)
        _cleanup_resume_files(temp_file, state_file)
        raise ValueError(f"文件哈希值与预期的哈希前缀不匹配: {hash_prefix}")

    temp_file.replace(cached_file)
    state_file.unlink(missing_ok=True)
    logger.info("'%s' 下载完成", file_name)


def download_file_from_url(
    url: str,
    save_path: Path | None = None,
    file_name: str | None = None,
    progress: bool | None = True,
    hash_prefix: str | None = None,
    re_download: bool | None = False,
    num_threads: int | None = 16,
    resume: bool | None = True,
    max_retries: int | None = 5,
    chunk_size: int | None = DEFAULT_RANGE_CHUNK_SIZE,
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
        re_download (bool | None):
            强制重新下载文件
        num_threads (int | None):
            单文件 HTTP Range 下载线程数
        resume (bool | None):
            是否启用断点续传
        max_retries (int | None):
            单个分片的最大重试次数
        chunk_size (int | None):
            HTTP Range 分片大小

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
        state_file = _state_path_for(temp_file)
        if re_download:
            _cleanup_resume_files(temp_file, state_file)

        logger.info("下载 '%s' 到 '%s' 中", file_name, cached_file)

        safe_num_threads = max(1, int(num_threads if num_threads is not None else 16))
        safe_max_retries = max(1, int(max_retries if max_retries is not None else 5))
        safe_chunk_size = max(1, int(chunk_size if chunk_size is not None else DEFAULT_RANGE_CHUNK_SIZE))
        remote_info = _probe_remote_file(requests, url) if safe_num_threads > 1 else _RemoteFileInfo(total_size=0, supports_range=False)

        if remote_info.supports_range:
            try:
                _download_file_with_ranges(
                    requests,
                    url=url,
                    temp_file=temp_file,
                    state_file=state_file,
                    remote_info=remote_info,
                    progress=bool(progress),
                    tqdm_class=tqdm,
                    resume=bool(resume),
                    max_retries=safe_max_retries,
                    num_threads=safe_num_threads,
                    chunk_size=safe_chunk_size,
                )
            except _RangeDownloadNotSupported as e:
                logger.warning("无法使用 HTTP Range 下载 '%s': %s, 切换到单连接下载", file_name, e)
                _cleanup_resume_files(temp_file, state_file)
                _download_file_single_stream(
                    requests,
                    url=url,
                    temp_file=temp_file,
                    file_name=file_name,
                    progress=bool(progress),
                    tqdm_class=tqdm,
                )
        else:
            _download_file_single_stream(
                requests,
                url=url,
                temp_file=temp_file,
                file_name=file_name,
                progress=bool(progress),
                tqdm_class=tqdm,
            )

        _finalize_download(
            temp_file=temp_file,
            state_file=state_file,
            cached_file=cached_file,
            file_name=file_name,
            hash_prefix=hash_prefix,
        )
    else:
        logger.info("'%s' 已存在于 '%s' 中", file_name, cached_file)
    return cached_file
