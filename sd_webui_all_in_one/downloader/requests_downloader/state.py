"""Requests 下载器断点状态、bitfield 和持久化。"""

import hashlib
import json
import math
import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger

from sd_webui_all_in_one.downloader.requests_downloader import models
from sd_webui_all_in_one.downloader.requests_downloader.models import _DownloadOptions, _PieceLengthChangedError, _RemoteFileInfo, _ResumeStateError

if TYPE_CHECKING:
    from sd_webui_all_in_one.downloader.requests_downloader.scheduler import _PieceStorage


logger = get_logger(name=LOGGER_NAME, level=LOGGER_LEVEL, color=LOGGER_COLOR)

_STATE_FILE_DIGESTS: dict[Path, str] = {}
_STATE_FILE_DIGEST_LOCK = threading.Lock()


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
    block_count = max(1, math.ceil(piece_size / models.IN_FLIGHT_BLOCK_LENGTH))
    data = bytearray(math.ceil(block_count / 8))
    completed_blocks = min(block_count, completed_length // models.IN_FLIGHT_BLOCK_LENGTH)
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
    block_count = max(1, math.ceil(piece_size / models.IN_FLIGHT_BLOCK_LENGTH))
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
    if version != models.STATE_VERSION:
        raise _ResumeStateError(f"断点续传状态版本不匹配: 期望 {models.STATE_VERSION}, 实际 {version}")
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
        "version": models.STATE_VERSION,
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
