"""Requests 下载器公共入口和任务编排。"""

import shutil
import threading
from dataclasses import replace
from pathlib import Path
from typing import Any

from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.downloader.hash_utils import compare_hash, normalize_hash_algorithm
from sd_webui_all_in_one.downloader.types import ExistingFilePolicy, validate_download_file_name
from sd_webui_all_in_one.logger import get_logger

from sd_webui_all_in_one.downloader.requests_downloader import http, models, state, transfer
from sd_webui_all_in_one.downloader.requests_downloader.http import _DigestTracker
from sd_webui_all_in_one.downloader.requests_downloader.models import (
    DEFAULT_MAX_CONNECTION_PER_SERVER,
    DEFAULT_MIN_SPLIT_SIZE,
    DEFAULT_PIECE_LENGTH,
    DEFAULT_SPLIT,
    DownloadConfigurationError,
    DownloadIntegrityError,
    _DownloadOptions,
    _RangeDownloadNotSupported,
    _UrlInput,
)


logger = get_logger(name=LOGGER_NAME, level=LOGGER_LEVEL, color=LOGGER_COLOR)


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
            maximum=models.MAX_CONNECTION_PER_SERVER_MAX,
        ),
        min_split_size=_normalize_int_option(
            "min_split_size",
            min_split_size,
            minimum=models.ARIA2_SIZE_OPTION_MIN,
            maximum=models.ARIA2_SIZE_OPTION_MAX,
        ),
        piece_length=_normalize_int_option(
            "piece_length",
            piece_length,
            minimum=models.ARIA2_SIZE_OPTION_MIN,
            maximum=models.ARIA2_SIZE_OPTION_MAX,
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

    urls = http._normalize_urls(url)
    normalized_hash_algorithm = normalize_hash_algorithm(hash_algorithm)
    explicit_hash_value = hash_value or hash_prefix
    explicit_hash_algorithm = normalized_hash_algorithm if hash_value else "sha256"
    explicit_hash_is_strong = models._is_full_hash(explicit_hash_value, explicit_hash_algorithm)
    explicit_file_name = file_name is not None
    if file_name is None:
        file_name = http._filename_from_url(urls[0])
    else:
        file_name = validate_download_file_name(file_name)
    cached_file = save_path.resolve() / file_name
    cached_file_exists = cached_file.exists()
    effective_existing_policy = models._resolve_existing_file_policy(
        existing_file_policy,
        re_download=re_download,
        continue_download=continue_download,
    )

    if cached_file_exists and effective_existing_policy == "reuse" and not conditional_get:
        if explicit_hash_value and not compare_hash(cached_file, explicit_hash_value, explicit_hash_algorithm):
            raise DownloadIntegrityError(f"已有文件哈希值 ({explicit_hash_algorithm}) 与预期值不匹配: {explicit_hash_value}")
        logger.info("'%s' 已存在于 '%s' 中", file_name, cached_file)
        return cached_file

    if cached_file_exists and not re_download and conditional_get and http._cached_file_not_modified(urls, cached_file):
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
        probe_result = http._probe_remote_files(urls, timeout=(options.connect_timeout, options.read_timeout))
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
            cached_file = models._renamed_file_path(cached_file)
            file_name = cached_file.name
            cached_file_exists = False

        with models._target_download_lock(cached_file):
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
                    models._verify_existing_file(cached_file, remote_info=remote_info, hash_prefix=None)
                logger.info("'%s' 已通过大小或哈希校验, 复用 '%s'", file_name, cached_file)
                return cached_file

            temp_file = save_path / f"{file_name}.tmp"
            state_file = state._state_path_for(temp_file)
            if effective_existing_policy == "overwrite":
                state._cleanup_resume_files(temp_file, state_file)
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
                state._cleanup_resume_files(temp_file, state_file)
                shutil.copyfile(cached_file, temp_file)
                options = replace(options, continue_download=True)

            logger.info("下载 '%s' 到 '%s' 中", file_name, cached_file)
            expected_size = remote_info.total_size
            resume_progress_size = transfer._resume_progress_size(
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
                state._cleanup_resume_files(temp_file, state_file)
                stream_size = transfer._download_file_single_stream(
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
                    transfer._download_file_with_ranges(
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
                    if resume_progress_size == 0 or transfer._resume_policy_allows_restart(
                        options,
                        failure_count=failure_count,
                        total_url_count=len(urls),
                    ):
                        expected_size = _restart_with_single_stream(str(e))
                    else:
                        logger.error("无法使用 HTTP Range 继续下载 '%s': %s, 已保留临时文件和断点状态", file_name, e)
                        raise IOError(f"无法使用 HTTP Range 继续下载 '{file_name}': {e}") from e
            elif remote_info.total_size > 0:
                if resume_progress_size > 0 and not transfer._resume_policy_allows_restart(
                    options,
                    failure_count=probe_result.resume_failure_count,
                    total_url_count=len(urls),
                ):
                    logger.error("远端不支持 HTTP Range, 无法继续下载 '%s', 已保留临时文件和断点状态", file_name)
                    raise IOError(f"远端不支持 HTTP Range, 无法继续下载 '{file_name}'")
                expected_size = _restart_with_single_stream("远端不支持 HTTP Range")
            else:
                if resume_progress_size > 0 and not transfer._resume_policy_allows_restart(
                    options,
                    failure_count=probe_result.resume_failure_count,
                    total_url_count=len(urls),
                ):
                    logger.error("远端未提供可靠的 Range 元数据, 无法继续下载 '%s', 已保留临时文件和断点状态", file_name)
                    raise IOError(f"远端未提供可靠的 Range 元数据, 无法继续下载 '{file_name}'")
                expected_size = _restart_with_single_stream("远端未提供可靠的 Range 元数据")

            tracker_hash = digest_tracker.expected()
            final_hash = (explicit_hash_algorithm, explicit_hash_value) if explicit_hash_value else tracker_hash
            transfer._finalize_download(
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
