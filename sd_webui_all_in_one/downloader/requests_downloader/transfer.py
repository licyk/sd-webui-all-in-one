"""Requests 下载器的 Range 与单流传输实现。"""

import random
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.downloader.hash_utils import compare_hash
from sd_webui_all_in_one.logger import get_logger

from sd_webui_all_in_one.downloader.requests_downloader import http, models, state as state_io
from sd_webui_all_in_one.downloader.requests_downloader.http import _DigestTracker
from sd_webui_all_in_one.downloader.requests_downloader.models import (
    DownloadCancelledError,
    DownloadIntegrityError,
    DownloadLowSpeedError,
    DownloadPermanentHttpError,
    DownloadProgressEvent,
    DownloadSizeIntegrityError,
    DownloadTransientError,
    _DownloadOptions,
    _RangeDownloadNotSupported,
    _RangeDownloadTemporaryError,
    _RangeRequestIgnored,
    _RemoteFileInfo,
    _ResumeStateError,
    _Segment,
    _SegmentDownloadError,
    _SegmentOwnershipLost,
    _classify_network_error,
)
from sd_webui_all_in_one.downloader.requests_downloader.scheduler import _PieceStorage, _SegmentManager, _ThreadLocalSessionPool, _UriPool


logger = get_logger(name=LOGGER_NAME, level=LOGGER_LEVEL, color=LOGGER_COLOR)


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
    retry_after = http._get_header(headers, "Retry-After")
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
    if status_code in models.RETRYABLE_STATUS_CODES:
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

    if http._get_header(headers, "Transfer-Encoding") is not None:
        if status_code == 200 and segment.start > 0:
            raise _RangeRequestIgnored("服务器返回 HTTP 200 (含 Transfer-Encoding), 疑似忽略 Range 请求")
        return

    parsed_range = http._response_range_from_headers(headers)
    if parsed_range is None:
        raise _RangeDownloadNotSupported("响应缺少可验证的 Content-Range 或 Content-Length")

    start, end, content_total = parsed_range
    expected_end = 0
    range_satisfied = start == segment.start and (expected_end == 0 or expected_end == end) and (total_size == 0 or content_total == total_size)
    if not range_satisfied:
        message = f"Range 响应不匹配: 期望 bytes {segment.start}-/{total_size}, 实际 {http._get_header(headers, 'Content-Range') or http._get_header(headers, 'Content-Length')}"
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
    return http._request_headers(headers)


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
        digest_tracker.observe(http._get_header(response.headers, "Digest"))
        if not segment_manager.owns_segment(segment):
            raise _SegmentOwnershipLost()
        _validate_range_response(response, url=url, segment=segment, total_size=total_size, attempt=attempt, retry_wait=retry_wait)

        offset = segment.start
        with temp_file.open("r+b") as file:
            for chunk in response.iter_content(chunk_size=models.STREAM_CHUNK_SIZE):
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
        http._close_response(response)


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
        state = state_io._load_resume_state(state_file)
        validation_info = remote_info
        if remote_info.total_size <= 0:
            saved_total_size = state_io._require_state_int(state, "total_size")
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
        parsed_state = state_io._parse_resume_state(
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
            state_io._piece_size_for(
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
    state = state_io._load_resume_state(state_file) if state_exists else None

    if state_exists and temp_exists:
        if temp_size != remote_info.total_size:
            raise _ResumeStateError(f"临时文件大小与断点续传状态不匹配: 期望 {remote_info.total_size}, 实际 {temp_size}")
        parsed_state = state_io._parse_resume_state(
            state or {},
            remote_info=remote_info,
            piece_length=options.piece_length,
            allow_piece_length_change=options.allow_piece_length_change,
            allow_validator_change=allow_validator_change,
        )
        if parsed_state is None:
            state_io._cleanup_resume_files(temp_file, state_file)
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
        state_io._cleanup_resume_files(temp_file, state_file)
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
        state_io._flush_download_data(temp_file)
        state_io._save_resume_state(
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
            save_due_to_piece_count = completed_since_state_save >= models.STATE_SAVE_COMPLETED_PIECE_INTERVAL
            save_due_to_time = time.monotonic() - last_state_save >= models.STATE_SAVE_INTERVAL_SECONDS
            if force or save_due_to_piece_count or save_due_to_time:
                _flush_state()
                completed_since_state_save = 0

    def _mark_segment_complete(segment: _Segment) -> None:
        nonlocal completed_since_state_save
        newly_completed = segment_manager.mark_complete(segment)
        with state_lock:
            completed_since_state_save += newly_completed
            if completed_since_state_save >= models.STATE_SAVE_COMPLETED_PIECE_INTERVAL or piece_storage.is_complete():
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

    response = requests.get(url, stream=True, timeout=timeout, headers=http._request_headers())
    try:
        digest_tracker.observe(http._get_header(response.headers, "Digest"))
        status_code = int(response.status_code or 0)
        if status_code in models.RETRYABLE_STATUS_CODES:
            raise _RangeDownloadTemporaryError(
                f"HTTP {status_code}",
                retry_delay=_retry_delay_for(response.headers, attempt, status_code=status_code, retry_wait=retry_wait),
            )
        if status_code >= 400:
            raise DownloadPermanentHttpError(url=url, status_code=status_code, segment=None, attempt=attempt)
        response.raise_for_status()
        if http._get_header(response.headers, "Transfer-Encoding") is not None or http._content_encoding_requires_single_stream(http._get_header(response.headers, "Content-Encoding")):
            total_size = 0
        else:
            total_size = http._parse_int_header(response.headers, "Content-Length")
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
                for chunk in response.iter_content(chunk_size=models.STREAM_CHUNK_SIZE):
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
        http._close_response(response)


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
            state_io._cleanup_resume_files(temp_file, state_file)
            raise DownloadSizeIntegrityError(f"下载文件大小不足: 期望 {expected_size}, 实际 {actual_size}")
        if actual_size > expected_size:
            logger.warning("'%s' 包含多余尾部数据, 将截断到 %s 字节", temp_file, expected_size)
            with temp_file.open("r+b") as file:
                file.truncate(expected_size)

    if hash_prefix and not compare_hash(temp_file, hash_prefix, hash_algorithm):
        logger.error("'%s' 的哈希值不匹配, 正在删除临时文件", temp_file)
        state_io._cleanup_resume_files(temp_file, state_file)
        raise DownloadIntegrityError(f"文件 {hash_algorithm} 哈希值与预期值不匹配: {hash_prefix}")

    temp_file.replace(cached_file)
    if remote_time:
        _apply_remote_time(cached_file, last_modified)
    state_file.unlink(missing_ok=True)
    logger.info("'%s' 下载完成", file_name)
