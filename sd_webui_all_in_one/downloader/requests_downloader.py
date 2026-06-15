"""Requests 下载器"""

import json
import math
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
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)


DEFAULT_SPLIT = 5
"""aria2 风格的单文件最大分割数"""

DEFAULT_MAX_CONNECTION_PER_SERVER = 1
"""aria2 风格的单服务器最大连接数"""

DEFAULT_MIN_SPLIT_SIZE = 20 * 1024 * 1024
"""aria2 风格的最小切分大小"""

DEFAULT_PIECE_LENGTH = 1024 * 1024
"""aria2 风格的 piece 大小"""

STREAM_CHUNK_SIZE = 1024 * 1024
"""HTTP 响应读取块大小"""

STATE_SAVE_COMPLETED_PIECE_INTERVAL = 8
"""断点续传状态写入间隔"""

STATE_VERSION = 4
"""HTTP Range 断点续传状态版本"""

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


class _RangeDownloadNotSupported(RuntimeError):
    """远端不支持可靠的 HTTP Range 下载"""


class _ResumeStateError(RuntimeError):
    """断点续传状态文件不可恢复"""


class _PieceLengthChangedError(_ResumeStateError):
    """控制文件中的 piece length 与当前配置不同"""


class _RangeRequestIgnored(_RangeDownloadNotSupported):
    """远端忽略了非零起点的 Range 请求"""


class _RangeDownloadTemporaryError(RuntimeError):
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


@dataclass(frozen=True)
class _RemoteFileInfo:
    """远端文件元数据"""

    total_size: int
    supports_range: bool
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True)
class _DownloadOptions:
    """aria2 风格下载选项"""

    split: int
    max_connection_per_server: int
    min_split_size: int
    piece_length: int
    max_tries: int
    continue_download: bool


@dataclass(frozen=True)
class _Segment:
    """连续 piece 组成的下载段"""

    start_piece: int
    end_piece: int
    start: int
    end: int
    piece_start: int

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


def _parse_content_range(
    content_range: str | None,
) -> tuple[int, int, int | None] | None:
    if not content_range:
        return None

    match = _CONTENT_RANGE_RE.match(content_range.strip())
    if not match:
        return None

    start = int(match.group(1))
    end = int(match.group(2))
    total = None if match.group(3) == "*" else int(match.group(3))
    return start, end, total


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
    """探测远端是否支持可靠的 HTTP Range 下载"""
    total_size = 0
    etag: str | None = None
    last_modified: str | None = None
    supports_range = False

    head_func = getattr(requests_module, "head", None)
    if callable(head_func):
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
                headers = getattr(response, "headers", {})
                if status_code == 206:
                    parsed = _parse_content_range(_get_header(headers, "Content-Range"))
                    if parsed is not None:
                        start, end, content_total = parsed
                        if start == 0 and end == 0 and content_total:
                            total_size = content_total
                            etag = etag or _get_header(headers, "ETag")
                            last_modified = last_modified or _get_header(headers, "Last-Modified")
                            supports_range = True
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
) -> dict[str, object]:
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except OSError as e:
        raise _ResumeStateError(f"无法读取断点续传状态文件: {state_file}") from e
    except json.JSONDecodeError as e:
        raise _ResumeStateError(f"断点续传状态文件不是有效 JSON: {state_file}") from e
    if not isinstance(state, dict):
        raise _ResumeStateError("断点续传状态文件根节点必须是对象")
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
        raise _ResumeStateError(
            f"断点续传状态 bitfield 长度不匹配: 期望 {expected_bytes} 字节, 实际 {len(data)} 字节"
        )

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
        raise _ResumeStateError(
            f"in-flight piece bitfield 长度不匹配: 期望 {expected_bytes} 字节, 实际 {len(data)} 字节"
        )
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
    for item in in_flight_pieces:
        if not isinstance(item, dict):
            raise _ResumeStateError("in-flight piece 必须是对象")
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
    url: str,
    remote_info: _RemoteFileInfo,
    piece_length: int,
) -> tuple[list[bool], list[int]] | None:
    version = _require_state_int(state, "version")
    if version != STATE_VERSION:
        raise _ResumeStateError(f"断点续传状态版本不匹配: 期望 {STATE_VERSION}, 实际 {version}")
    if state.get("url") != url:
        raise _ResumeStateError("断点续传状态 URL 与当前下载不匹配")
    total_size = _require_state_int(state, "total_size")
    if total_size != remote_info.total_size:
        raise _ResumeStateError(f"断点续传状态文件大小不匹配: 期望 {remote_info.total_size}, 实际 {total_size}")
    if _require_state_optional_str(state, "etag") != remote_info.etag:
        raise _ResumeStateError("断点续传状态 ETag 与当前下载不匹配")
    if _require_state_optional_str(state, "last_modified") != remote_info.last_modified:
        raise _ResumeStateError("断点续传状态 Last-Modified 与当前下载不匹配")

    saved_piece_length = _require_state_int(state, "piece_length")
    if saved_piece_length <= 0:
        raise _ResumeStateError("断点续传状态 piece_length 必须大于 0")
    saved_piece_count = _require_state_int(state, "piece_count")
    expected_saved_piece_count = _piece_count_for(remote_info.total_size, saved_piece_length)
    if saved_piece_count != expected_saved_piece_count:
        raise _ResumeStateError(
            f"断点续传状态 piece_count 不匹配: 期望 {expected_saved_piece_count}, 实际 {saved_piece_count}"
        )

    completed = _bitfield_from_hex(state.get("completed_bitfield"), saved_piece_count)
    in_flight_lengths = _in_flight_lengths_from_state(
        state.get("in_flight_pieces"),
        piece_count=saved_piece_count,
        piece_length=saved_piece_length,
        total_size=remote_info.total_size,
        completed=completed,
    )
    if saved_piece_length != piece_length:
        if any(completed) or any(in_flight_lengths):
            raise _PieceLengthChangedError(
                f"检测到 piece_length 变化: 状态文件 {saved_piece_length}, 当前配置 {piece_length}"
            )
        return None
    return completed, in_flight_lengths


def _save_resume_state(
    state_file: Path,
    *,
    url: str,
    remote_info: _RemoteFileInfo,
    options: _DownloadOptions,
    piece_storage: "_PieceStorage",
) -> None:
    completed = piece_storage.snapshot_completed()
    in_flight_pieces = piece_storage.snapshot_in_flight_pieces()
    state = {
        "version": STATE_VERSION,
        "url": url,
        "total_size": remote_info.total_size,
        "etag": remote_info.etag,
        "last_modified": remote_info.last_modified,
        "piece_length": options.piece_length,
        "piece_count": len(completed),
        "completed_bitfield": _bitfield_to_hex(completed),
        "in_flight_pieces": in_flight_pieces,
    }
    tmp_state_file = state_file.with_name(f"{state_file.name}.tmp")
    tmp_state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_state_file.replace(state_file)


class _ThreadLocalSessionPool:
    """为每个下载线程复用一个 requests Session"""

    def __init__(
        self,
        requests_module: Any,
        pool_size: int,
    ) -> None:
        self.requests_module = requests_module
        self.pool_size = max(1, pool_size)
        self.local = threading.local()
        self.lock = threading.Lock()
        self.sessions: list[Any] = []

    def get(self) -> Any:
        session = getattr(self.local, "session", None)
        if session is not None:
            return session

        session_factory = getattr(self.requests_module, "Session", None)
        session = session_factory() if callable(session_factory) else self.requests_module
        if session is not self.requests_module:
            self._configure_session(session)
            with self.lock:
                self.sessions.append(session)
        self.local.session = session
        return session

    def close_all(self) -> None:
        with self.lock:
            sessions = list(self.sessions)
            self.sessions.clear()
        for session in sessions:
            closer = getattr(session, "close", None)
            if callable(closer):
                closer()

    def _configure_session(
        self,
        session: Any,
    ) -> None:
        adapters_module = getattr(self.requests_module, "adapters", None)
        adapter_factory = getattr(adapters_module, "HTTPAdapter", None)
        mount = getattr(session, "mount", None)
        if not callable(adapter_factory) or not callable(mount):
            return
        for prefix in ("http://", "https://"):
            mount(prefix, adapter_factory(pool_connections=self.pool_size, pool_maxsize=self.pool_size))


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
            return sum(
                self._piece_size_unlocked(index) if done else self.in_flight_lengths[index]
                for index, done in enumerate(self.completed)
            )

    def is_complete(self) -> bool:
        with self.lock:
            return all(self.completed)

    def check_out_segment(
        self,
        min_split_size: int,
    ) -> _Segment | None:
        with self.lock:
            index = self._select_sparse_missing_unused_piece_unlocked(min_split_size)
            if index is None:
                return None

            return self._check_out_piece_unlocked(index)

    def check_out_piece(
        self,
        index: int,
    ) -> _Segment | None:
        with self.lock:
            if index < 0 or index >= self.piece_count or self.completed[index] or self.in_use[index]:
                return None
            return self._check_out_piece_unlocked(index)

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
                self.in_use[index] = False
            return newly_completed

    def record_progress(
        self,
        segment: _Segment,
        next_offset: int,
    ) -> None:
        with self.lock:
            index = segment.start_piece
            if index < 0 or index >= self.piece_count or self.completed[index]:
                return
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
            return self._segment_for_piece_unlocked(index)

    def release(
        self,
        segment: _Segment,
    ) -> None:
        with self.lock:
            for index in range(segment.start_piece, segment.end_piece + 1):
                self.in_use[index] = False

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
    ) -> _Segment:
        self.in_use[index] = True
        return self._segment_for_piece_unlocked(index)

    def _segment_for_piece_unlocked(
        self,
        index: int,
    ) -> _Segment:
        piece_start = self._piece_start_unlocked(index)
        start = min(piece_start + self.in_flight_lengths[index], self._piece_end_unlocked(index))
        return _Segment(
            start_piece=index,
            end_piece=index,
            start=start,
            end=self._piece_end_unlocked(index),
            piece_start=piece_start,
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

    def get_segment(self) -> _Segment | None:
        return self.piece_storage.check_out_segment(self.min_split_size)

    def get_next_segment(
        self,
        segment: _Segment,
    ) -> _Segment | None:
        return self.piece_storage.check_out_piece(segment.end_piece + 1)

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


def _validate_range_response(
    response: Any,
    *,
    segment: _Segment,
    total_size: int,
    attempt: int,
) -> None:
    status_code = int(getattr(response, "status_code", 0) or 0)
    headers = getattr(response, "headers", {})

    if status_code == 200 and segment.start > 0:
        raise _RangeRequestIgnored("远端忽略 Range 请求")
    if status_code == 416:
        raise _RangeDownloadNotSupported("远端拒绝 Range 请求: HTTP 416")
    if status_code in RETRYABLE_STATUS_CODES:
        raise _RangeDownloadTemporaryError(f"HTTP {status_code}", retry_delay=_retry_delay_for(headers, attempt))
    if status_code not in {200, 206}:
        raise RuntimeError(f"Range 请求返回非预期状态码: HTTP {status_code}")

    parsed_range = _parse_content_range(_get_header(headers, "Content-Range"))
    if parsed_range is None and status_code == 206:
        raise _RangeDownloadNotSupported("Range 响应缺少有效 Content-Range")
    if parsed_range is None:
        content_length = _parse_int_header(headers, "Content-Length")
        if content_length and content_length != total_size:
            raise _RangeDownloadNotSupported(f"Content-Length 不匹配: 期望 {total_size}, 实际 {content_length}")
        return

    start, end, content_total = parsed_range
    if start != segment.start or end < segment.end or content_total != total_size:
        raise _RangeDownloadNotSupported(
            f"Range 响应不匹配: 期望 bytes {segment.start}-/{total_size}, 实际 {_get_header(headers, 'Content-Range')}"
        )


def _stream_request_headers(
    segment: _Segment,
) -> dict[str, str]:
    if segment.start == 0:
        return _request_headers()
    return _request_headers({"Range": f"bytes={segment.start}-"})


def _download_stream_once(
    request_client: Any,
    *,
    url: str,
    temp_file: Path,
    segment: _Segment,
    total_size: int,
    timeout: int,
    attempt: int,
    segment_manager: _SegmentManager,
    mark_complete_callback: Any,
    progress_callback: Any | None = None,
) -> None:
    response = request_client.get(url, stream=True, timeout=timeout, headers=_stream_request_headers(segment))
    current_segment: _Segment | None = segment
    last_complete_segment: _Segment | None = None
    partial_reported_size = 0
    try:
        _validate_range_response(response, segment=segment, total_size=total_size, attempt=attempt)

        offset = segment.start
        with temp_file.open("r+b") as file:
            for chunk in response.iter_content(chunk_size=STREAM_CHUNK_SIZE):
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

                    file.seek(offset)
                    file.write(chunk[chunk_offset : chunk_offset + writable_size])
                    offset += writable_size
                    chunk_offset += writable_size
                    partial_reported_size += writable_size
                    segment_manager.record_progress(current_segment, offset)
                    if progress_callback is not None:
                        progress_callback(writable_size)

                    if offset > current_segment.end:
                        mark_complete_callback(current_segment)
                        last_complete_segment = current_segment
                        current_segment = None
                        partial_reported_size = 0

        if current_segment is not None:
            raise IOError(f"分片大小不匹配: 期望 {current_segment.size}, 实际 {partial_reported_size}")
    except _RangeDownloadNotSupported:
        raise
    except Exception as e:
        raise _SegmentDownloadError(current_segment or segment, e) from e
    finally:
        _close_response(response)


def _download_stream_with_retries(
    session_pool: _ThreadLocalSessionPool,
    *,
    url: str,
    temp_file: Path,
    segment: _Segment,
    total_size: int,
    timeout: int,
    max_tries: int,
    segment_manager: _SegmentManager,
    mark_complete_callback: Any,
    progress_callback: Any | None = None,
) -> None:
    last_error: Exception | None = None
    for attempt in range(1, max_tries + 1):
        try:
            return _download_stream_once(
                session_pool.get(),
                url=url,
                temp_file=temp_file,
                segment=segment,
                total_size=total_size,
                timeout=timeout,
                attempt=attempt,
                segment_manager=segment_manager,
                mark_complete_callback=mark_complete_callback,
                progress_callback=progress_callback,
            )
        except _RangeDownloadNotSupported:
            raise
        except _SegmentDownloadError as e:
            refreshed_segment = segment_manager.refresh_segment(e.segment)
            if refreshed_segment is None:
                return
            segment = refreshed_segment
            last_error = e.error
            if attempt >= max_tries:
                break
            delay = e.error.retry_delay if isinstance(e.error, _RangeDownloadTemporaryError) and e.error.retry_delay is not None else min(0.5 * attempt, 5.0)
            logger.warning("分片 %s 下载失败 [%s/%s]: %s, %.1fs 后重试", segment.byte_range, attempt, max_tries, e.error, delay)
            time.sleep(delay)
        except Exception as e:
            last_error = e
            if attempt >= max_tries:
                break
            delay = e.retry_delay if isinstance(e, _RangeDownloadTemporaryError) and e.retry_delay is not None else min(0.5 * attempt, 5.0)
            logger.warning("分片 %s 下载失败 [%s/%s]: %s, %.1fs 后重试", segment.byte_range, attempt, max_tries, e, delay)
            time.sleep(delay)
    segment_manager.release(segment)
    raise IOError(f"分片 {segment.byte_range} 下载失败: {last_error}") from last_error


def _download_file_with_ranges(
    requests_module: Any,
    *,
    url: str,
    temp_file: Path,
    state_file: Path,
    remote_info: _RemoteFileInfo,
    progress: bool,
    tqdm_class: Any,
    options: _DownloadOptions,
    timeout: int = 60,
) -> None:
    if remote_info.total_size <= 0 or not remote_info.supports_range:
        raise _RangeDownloadNotSupported("远端未提供可分片下载的文件大小或 Range 支持")

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
            raise _ResumeStateError(
                f"临时文件大小与断点续传状态不匹配: 期望 {remote_info.total_size}, 实际 {temp_size}"
            )
        parsed_state = _parse_resume_state(
            state or {},
            url=url,
            remote_info=remote_info,
            piece_length=options.piece_length,
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
    elif options.continue_download and not state_exists and temp_exists and 0 < temp_size <= remote_info.total_size:
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
    stop_event = threading.Event()
    range_ignored_event = threading.Event()
    completed_since_state_save = 0
    worker_count = max(1, min(options.split, options.max_connection_per_server, piece_storage.piece_count))
    session_pool = _ThreadLocalSessionPool(requests_module, pool_size=worker_count)

    def _update_progress(delta: int) -> None:
        with progress_lock:
            progress_bar.update(delta)

    def _flush_state() -> None:
        _save_resume_state(
            state_file,
            url=url,
            remote_info=remote_info,
            options=options,
            piece_storage=piece_storage,
        )

    def _mark_segment_complete(segment: _Segment) -> None:
        nonlocal completed_since_state_save
        newly_completed = segment_manager.mark_complete(segment)
        with state_lock:
            completed_since_state_save += newly_completed
            if (
                completed_since_state_save >= STATE_SAVE_COMPLETED_PIECE_INTERVAL
                or piece_storage.is_complete()
            ):
                _flush_state()
                completed_since_state_save = 0

    def _worker() -> None:
        while not stop_event.is_set():
            segment = segment_manager.get_segment()
            if segment is None:
                return
            try:
                _download_stream_with_retries(
                    session_pool,
                    url=url,
                    temp_file=temp_file,
                    segment=segment,
                    total_size=remote_info.total_size,
                    timeout=timeout,
                    max_tries=options.max_tries,
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

    with tqdm_class(
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
            with state_lock:
                _flush_state()
            raise
        finally:
            session_pool.close_all()

    if not piece_storage.is_complete():
        with state_lock:
            _flush_state()
        if range_ignored_event.is_set():
            raise _RangeDownloadNotSupported("远端忽略 Range 请求")
        raise IOError("分片下载未完成")
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
    response = requests_module.get(url, stream=True, timeout=60, headers=_request_headers())
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
                for chunk in response.iter_content(chunk_size=STREAM_CHUNK_SIZE):
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


def _normalize_options(
    *,
    split: int,
    max_connection_per_server: int,
    min_split_size: int,
    piece_length: int,
    max_tries: int,
    continue_download: bool,
) -> _DownloadOptions:
    return _DownloadOptions(
        split=max(1, int(split)),
        max_connection_per_server=max(1, int(max_connection_per_server)),
        min_split_size=max(1, int(min_split_size)),
        piece_length=max(1, int(piece_length)),
        max_tries=max(1, int(max_tries)),
        continue_download=bool(continue_download),
    )


def download_file_from_url(
    url: str,
    save_path: Path | None = None,
    file_name: str | None = None,
    progress: bool = True,
    hash_prefix: str | None = None,
    re_download: bool = False,
    split: int = DEFAULT_SPLIT,
    max_connection_per_server: int = DEFAULT_MAX_CONNECTION_PER_SERVER,
    min_split_size: int = DEFAULT_MIN_SPLIT_SIZE,
    piece_length: int = DEFAULT_PIECE_LENGTH,
    continue_download: bool = False,
    max_tries: int = 5,
) -> Path:
    """使用 requests 库下载文件

    Args:
        url (str):
            下载链接
        save_path (Path | None):
            下载路径
        file_name (str | None):
            保存的文件名, 如果为`None`则从`url`中提取文件
        progress (bool):
            是否启用下载进度条
        hash_prefix (str | None):
            sha256 十六进制字符串, 如果提供, 将检查下载文件的哈希值是否与此前缀匹配, 当不匹配时引发`ValueError`
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
        continue_download (bool):
            没有匹配 state 文件时, 是否从已有临时文件推断断点续传进度
        max_tries (int):
            单个分片的最大尝试次数

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
        file_name = Path(parts.path).name or "download"

    cached_file = save_path.resolve() / file_name

    if re_download or not cached_file.exists():
        save_path.mkdir(parents=True, exist_ok=True)
        temp_file = save_path / f"{file_name}.tmp"
        state_file = _state_path_for(temp_file)
        if re_download:
            _cleanup_resume_files(temp_file, state_file)

        logger.info("下载 '%s' 到 '%s' 中", file_name, cached_file)

        options = _normalize_options(
            split=split,
            max_connection_per_server=max_connection_per_server,
            min_split_size=min_split_size,
            piece_length=piece_length,
            max_tries=max_tries,
            continue_download=continue_download,
        )
        remote_info = _probe_remote_file(requests, url)

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
                    options=options,
                )
            except _RangeDownloadNotSupported as e:
                logger.error("无法使用 HTTP Range 继续下载 '%s': %s, 已保留临时文件和断点状态", file_name, e)
                raise IOError(f"无法使用 HTTP Range 继续下载 '{file_name}': {e}") from e
        else:
            _cleanup_resume_files(temp_file, state_file)
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
