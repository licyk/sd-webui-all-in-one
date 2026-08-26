"""Requests 下载器的 HTTP 元数据、Header 和远端探测。"""

import base64
import binascii
import hashlib
import re
import threading
from collections.abc import Sequence
from email.utils import formatdate
from pathlib import Path
from typing import Any
from urllib.parse import unquote, unquote_to_bytes, urlparse

from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.downloader.types import DEFAULT_USER_AGENT, validate_download_file_name
from sd_webui_all_in_one.logger import get_logger

from .models import DownloadIntegrityError, _RemoteFileInfo, _RemoteProbeResult, _UrlInput


logger = get_logger(name=LOGGER_NAME, level=LOGGER_LEVEL, color=LOGGER_COLOR)

_CONTENT_RANGE_RE = re.compile(r"(?:bytes\s+|bytes=)?(\d+)-(\d+)/(\d+|\*)", flags=re.IGNORECASE)
_UNSATISFIED_CONTENT_RANGE_RE = re.compile(r"(?:bytes\s+|bytes=)?\*/(\d+|\*)", flags=re.IGNORECASE)


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
