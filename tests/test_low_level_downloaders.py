import base64
import hashlib
import json
import subprocess
import sys
import types
import urllib.error
from email.utils import parsedate_to_datetime
from pathlib import Path

import pytest

from sd_webui_all_in_one.downloader import aria2_downloader
from sd_webui_all_in_one.downloader import aria2_server
from sd_webui_all_in_one.downloader import requests_downloader
from sd_webui_all_in_one.downloader import urllib_downloader
from sd_webui_all_in_one.downloader.hash_utils import compare_sha256


@pytest.fixture(autouse=True)
def _small_aria2_size_bounds(monkeypatch):
    monkeypatch.setattr(requests_downloader, "ARIA2_SIZE_OPTION_MIN", 1)
    monkeypatch.setattr(requests_downloader, "ARIA2_SIZE_OPTION_MAX", 1024 * 1024 * 1024)


class FakeTqdm:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.n = kwargs.get("initial", 0)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def update(self, value):
        self.n += value

    def close(self):
        pass


class FakeRequestsResponse:
    def __init__(self, chunks, status_code=200):
        self._chunks = chunks
        self.status_code = status_code
        self.headers = {"content-length": str(sum(len(chunk) for chunk in chunks))}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("bad status")

    def iter_content(self, chunk_size=1024):
        yield from self._chunks


class FakeRangeResponse:
    def __init__(self, payload=b"", status_code=200, headers=None):
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"bad status: {self.status_code}")

    def iter_content(self, chunk_size=64 * 1024):
        for index in range(0, len(self.payload), chunk_size):
            yield self.payload[index : index + chunk_size]

    def close(self):
        pass


def _range_bytes(range_header):
    start, end = range_header.removeprefix("bytes=").split("-", maxsplit=1)
    return int(start), int(end)


def _response_range(headers, total_size):
    range_header = headers.get("Range") if headers else None
    if range_header is None:
        return range_header, 0, total_size - 1, 200
    start, end = range_header.removeprefix("bytes=").split("-", maxsplit=1)
    return range_header, int(start), total_size - 1 if end == "" else int(end), 206


def _range_response(payload, headers):
    range_header, start, end, status_code = _response_range(headers, len(payload))
    response_headers = {"Content-Length": str(end - start + 1)}
    if range_header is not None:
        response_headers["Content-Range"] = f"bytes {start}-{end}/{len(payload)}"
    return range_header, FakeRangeResponse(payload[start : end + 1], status_code=status_code, headers=response_headers)


def _request_state(
    *,
    url,
    total_size,
    completed,
    in_flight_lengths=None,
    etag=None,
    last_modified=None,
    piece_length=4,
):
    if in_flight_lengths is None:
        in_flight_lengths = [0] * len(completed)
    in_flight_pieces = []
    for index, completed_length in enumerate(in_flight_lengths):
        if completed_length <= 0:
            continue
        piece_size = min((index + 1) * piece_length, total_size) - index * piece_length
        in_flight_pieces.append(
            {
                "index": index,
                "length": piece_size,
                "completed_length": completed_length,
                "bitfield": requests_downloader._in_flight_bitfield_to_hex(
                    piece_size=piece_size,
                    completed_length=completed_length,
                ),
            }
        )
    state = {
        "version": requests_downloader.STATE_VERSION,
        "url": url,
        "total_size": total_size,
        "etag": etag,
        "last_modified": last_modified,
        "piece_length": piece_length,
        "piece_count": len(completed),
        "completed_bitfield": requests_downloader._bitfield_to_hex(completed),
        "in_flight_pieces": in_flight_pieces,
    }
    return state


def test_requests_downloader_default_headers_match_aria2_http_defaults():
    headers = requests_downloader._request_headers({"Range": "bytes=1-"})

    assert headers["User-Agent"]
    assert headers["Accept"] == "*/*"
    assert headers["Accept-Encoding"] == "identity"
    assert headers["Pragma"] == "no-cache"
    assert headers["Cache-Control"] == "no-cache"
    assert headers["Want-Digest"] == "SHA-512;q=1, SHA-256;q=1, SHA-1;q=1"
    assert headers["Range"] == "bytes=1-"


def test_requests_downloader_cache_redownload_and_hash(monkeypatch, tmp_path):
    calls = []
    payload = b"hello world"

    def fake_get(url, stream=True, timeout=60, headers=None):
        calls.append(headers.get("Range") if headers else None)
        if headers and "Range" in headers:
            return FakeRequestsResponse([payload], status_code=200)
        return FakeRequestsResponse([payload[:5], payload[5:]])

    fake_requests = types.SimpleNamespace(get=fake_get)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    expected_hash = hashlib.sha256(payload).hexdigest()
    result = requests_downloader.download_file_from_url(
        "https://example.test/files/model.bin",
        save_path=tmp_path / "downloads",
        progress=False,
        hash_prefix=expected_hash[:12],
    )

    assert result == (tmp_path / "downloads" / "model.bin").resolve()
    assert result.read_bytes() == payload
    assert calls == ["bytes=0-0", None]

    cached = requests_downloader.download_file_from_url(
        "https://example.test/files/model.bin",
        save_path=tmp_path / "downloads",
        progress=False,
    )
    assert cached == result
    assert len(calls) == 2

    with pytest.raises(ValueError):
        requests_downloader.download_file_from_url(
            "https://example.test/files/model.bin",
            save_path=tmp_path / "downloads",
            progress=False,
            hash_prefix="badbad",
            re_download=True,
        )
    assert not (tmp_path / "downloads" / "model.bin.tmp").exists()


def test_requests_downloader_conditional_get_reuses_cached_file_on_304(monkeypatch, tmp_path):
    cached_file = tmp_path / "model.bin"
    cached_file.write_bytes(b"cached")
    head_headers = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        head_headers.append(headers or {})
        return FakeRangeResponse(status_code=304, headers={})

    def fake_get(url, stream=True, timeout=60, headers=None):
        raise AssertionError("304 conditional-get should not download")

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        conditional_get=True,
    )

    assert result == cached_file.resolve()
    assert result.read_bytes() == b"cached"
    assert "If-Modified-Since" in head_headers[0]


def test_requests_downloader_conditional_get_redownloads_when_modified(monkeypatch, tmp_path):
    cached_file = tmp_path / "model.bin"
    cached_file.write_bytes(b"old")
    payload = b"new payload"
    head_headers = []
    range_calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        head_headers.append(headers or {})
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
            },
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        range_header, response = _range_response(payload, headers)
        range_calls.append(range_header)
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        conditional_get=True,
        split=1,
        min_split_size=4,
        piece_length=4,
    )

    assert result == cached_file.resolve()
    assert result.read_bytes() == payload
    assert "If-Modified-Since" in head_headers[0]
    assert "If-Modified-Since" not in head_headers[-1]
    assert range_calls


def test_requests_downloader_validates_sha256_digest_header(monkeypatch, tmp_path):
    payload = b"digest payload"
    digest = base64.b64encode(hashlib.sha256(payload).digest()).decode("ascii")

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
                "Digest": f"SHA-256={digest}",
            },
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        return _range_response(payload, headers)[1]

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/files/model.bin",
        save_path=tmp_path,
        progress=False,
        split=1,
        min_split_size=4,
        piece_length=4,
    )

    assert result.read_bytes() == payload


def test_requests_downloader_rejects_bad_sha256_digest_header(monkeypatch, tmp_path):
    payload = b"digest payload"
    bad_digest = base64.b64encode(hashlib.sha256(b"other payload").digest()).decode("ascii")

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
                "Digest": f"sha-256={bad_digest}",
            },
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        return _range_response(payload, headers)[1]

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(ValueError, match="哈希"):
        requests_downloader.download_file_from_url(
            "https://example.test/files/model.bin",
            save_path=tmp_path,
            progress=False,
            split=1,
            min_split_size=4,
            piece_length=4,
        )

    assert not (tmp_path / "model.bin.tmp").exists()


def test_requests_downloader_uses_content_disposition_filename(monkeypatch, tmp_path):
    payload = b"content disposition payload"

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
                "Content-Disposition": "attachment; filename*=UTF-8''served%20model.bin",
            },
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        return _range_response(payload, headers)[1]

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/files/url-name.bin",
        save_path=tmp_path,
        progress=False,
        split=1,
        min_split_size=4,
        piece_length=4,
    )

    assert result == (tmp_path / "served model.bin").resolve()
    assert result.read_bytes() == payload
    assert not (tmp_path / "url-name.bin").exists()


def test_requests_downloader_explicit_file_name_overrides_content_disposition(monkeypatch, tmp_path):
    payload = b"explicit payload"

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
                "Content-Disposition": 'attachment; filename="served.bin"',
            },
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        return _range_response(payload, headers)[1]

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/files/url-name.bin",
        save_path=tmp_path,
        file_name="explicit.bin",
        progress=False,
        split=1,
        min_split_size=4,
        piece_length=4,
    )

    assert result == (tmp_path / "explicit.bin").resolve()
    assert result.read_bytes() == payload
    assert not (tmp_path / "served.bin").exists()


def test_requests_downloader_truncates_single_stream_trailing_garbage_before_hash(monkeypatch, tmp_path):
    payload = b"hello world"
    extra_payload = payload + b"garbage"

    def fake_get(url, stream=True, timeout=60, headers=None):
        if headers and "Range" in headers:
            return FakeRangeResponse(status_code=200, headers={})
        response = FakeRequestsResponse([extra_payload], status_code=200)
        response.headers = {"content-length": str(len(payload))}
        return response

    fake_requests = types.SimpleNamespace(get=fake_get)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/files/model.bin",
        save_path=tmp_path,
        progress=False,
        hash_prefix=hashlib.sha256(payload).hexdigest(),
    )

    assert result.read_bytes() == payload


def test_requests_downloader_rejects_single_stream_short_write(monkeypatch, tmp_path):
    payload = b"short"

    def fake_get(url, stream=True, timeout=60, headers=None):
        if headers and "Range" in headers:
            return FakeRangeResponse(status_code=200, headers={})
        response = FakeRequestsResponse([payload], status_code=200)
        response.headers = {"content-length": str(len(payload) + 1)}
        return response

    fake_requests = types.SimpleNamespace(get=fake_get)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(IOError, match="大小不足"):
        requests_downloader.download_file_from_url(
            "https://example.test/files/model.bin",
            save_path=tmp_path,
            progress=False,
        )

    assert not (tmp_path / "model.bin.tmp").exists()


def test_requests_downloader_uses_single_stream_for_content_encoding(monkeypatch, tmp_path):
    payload = b"decoded payload is longer"
    calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": "4",
                "Accept-Ranges": "bytes",
                "Content-Encoding": "gzip",
            },
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        calls.append(headers.get("Range") if headers else None)
        response = FakeRequestsResponse([payload], status_code=200)
        response.headers = {
            "Content-Length": "4",
            "Content-Encoding": "gzip",
        }
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/files/model.bin",
        save_path=tmp_path,
        progress=False,
        split=4,
        max_connection_per_server=4,
        min_split_size=4,
        piece_length=4,
    )

    assert calls == [None]
    assert result.read_bytes() == payload


def test_requests_downloader_applies_remote_last_modified_by_default(monkeypatch, tmp_path):
    payload = b"remote time payload"
    last_modified = "Wed, 27 May 2026 00:00:00 GMT"
    expected_timestamp = parsedate_to_datetime(last_modified).timestamp()

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
                "Last-Modified": last_modified,
            },
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        return _range_response(payload, headers)[1]

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/files/model.bin",
        save_path=tmp_path,
        progress=False,
        split=1,
        min_split_size=4,
        piece_length=4,
    )

    assert result.read_bytes() == payload
    assert abs(result.stat().st_mtime - expected_timestamp) < 1


def test_requests_downloader_can_disable_remote_time(monkeypatch, tmp_path):
    payload = b"remote time payload"
    last_modified = "Wed, 27 May 2026 00:00:00 GMT"
    expected_timestamp = parsedate_to_datetime(last_modified).timestamp()

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
                "Last-Modified": last_modified,
            },
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        return _range_response(payload, headers)[1]

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/files/model.bin",
        save_path=tmp_path,
        progress=False,
        split=1,
        min_split_size=4,
        piece_length=4,
        remote_time=False,
    )

    assert result.read_bytes() == payload
    assert abs(result.stat().st_mtime - expected_timestamp) >= 1


def test_piece_storage_checks_out_dynamic_segments():
    storage = requests_downloader._PieceStorage(total_size=16, piece_length=4)

    first = storage.check_out_segment(min_split_size=8)
    second = storage.check_out_segment(min_split_size=8)
    third = storage.check_out_segment(min_split_size=8)

    assert first is not None
    assert second is not None
    assert third is None
    assert first.byte_range == (0, 3)
    assert second.byte_range == (8, 11)

    storage.release(first)
    replay = storage.check_out_segment(min_split_size=8)
    assert replay == first
    assert storage.mark_complete(replay) == 1
    assert storage.mark_complete(second) == 1
    assert not storage.is_complete()


def test_segment_manager_does_not_continue_stream_into_partial_piece():
    storage = requests_downloader._PieceStorage(total_size=12, piece_length=4, in_flight_lengths=[0, 2, 0])
    manager = requests_downloader._SegmentManager(storage, min_split_size=4)

    first = storage.check_out_piece(0)
    assert first is not None
    assert storage.mark_complete(first) == 1

    assert manager.get_next_segment(first) is None
    resumed = manager.get_segment()
    assert resumed is not None
    assert resumed.byte_range == (6, 7)


def test_segment_manager_steals_clean_segment_from_idle_owner():
    storage = requests_downloader._PieceStorage(total_size=12, piece_length=4)
    manager = requests_downloader._SegmentManager(storage, min_split_size=4)

    first = storage.check_out_piece(0, owner_id=1)
    idle_next = storage.check_out_piece(1, owner_id=2)
    assert first is not None
    assert idle_next is not None

    assert storage.mark_complete(first) == 1
    stolen = manager.get_next_segment(first)

    assert stolen is not None
    assert stolen.byte_range == (4, 7)
    assert stolen.owner_id == 1
    assert not manager.owns_segment(idle_next)

    manager.release(idle_next)
    assert manager.owns_segment(stolen)
    assert storage.mark_complete(stolen) == 1


def test_uri_pool_limits_connections_per_host():
    pool = requests_downloader._UriPool(
        [
            "https://a.example.test/one.bin",
            "https://a.example.test/two.bin",
            "https://b.example.test/three.bin",
        ],
        max_connection_per_server=1,
    )

    first = pool.acquire()
    second = pool.acquire()
    assert first == "https://a.example.test/one.bin"
    assert second == "https://b.example.test/three.bin"

    pool.release(first)
    third = pool.acquire()
    assert third == "https://a.example.test/one.bin"

    pool.release(second)
    pool.release(third)


def test_requests_downloader_uses_mirror_urls_for_range_workers(monkeypatch, tmp_path):
    payload = b"abcdefgh"
    data_urls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
            },
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        data_urls.append(url)
        range_header = headers.get("Range") if headers else None
        if range_header is None:
            start = 0
            end = 3
        else:
            start_text, end_text = range_header.removeprefix("bytes=").split("-", maxsplit=1)
            start = int(start_text)
            end = len(payload) - 1 if end_text == "" else int(end_text)
        response_headers = {
            "Content-Length": str(end - start + 1),
            "Content-Range": f"bytes {start}-{end}/{len(payload)}",
        }
        return FakeRangeResponse(payload[start : end + 1], status_code=206, headers=response_headers)

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        [
            "https://a.example.test/model.bin",
            "https://b.example.test/model.bin",
        ],
        save_path=tmp_path,
        progress=False,
        split=2,
        max_connection_per_server=1,
        min_split_size=4,
        piece_length=4,
    )

    assert result.read_bytes() == payload
    assert set(data_urls) == {
        "https://a.example.test/model.bin",
        "https://b.example.test/model.bin",
    }


def test_requests_downloader_http_range_download_uses_piece_segments(monkeypatch, tmp_path):
    payload = b"abcdefghijklmnop"
    range_calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        assert url == "https://example.test/model.bin"
        assert allow_redirects is True
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
                "ETag": "v1",
                "Last-Modified": "Wed, 27 May 2026 00:00:00 GMT",
            },
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        range_header, response = _range_response(payload, headers)
        range_calls.append(range_header)
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    sleep_calls = []
    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=3,
        max_connection_per_server=3,
        min_split_size=4,
        piece_length=4,
    )

    assert result.read_bytes() == payload
    assert "bytes=0-" in range_calls
    assert all(item.endswith("-") for item in range_calls)
    assert not (tmp_path / "model.bin.tmp").exists()
    assert not (tmp_path / "model.bin.tmp.state.json").exists()


def test_requests_downloader_default_min_split_size_avoids_small_file_oversplitting(monkeypatch, tmp_path):
    payload = b"small payload"
    range_calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        range_header, response = _range_response(payload, headers)
        range_calls.append(range_header)
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/small.bin",
        save_path=tmp_path,
        progress=False,
        split=8,
        max_connection_per_server=8,
    )

    assert result.read_bytes() == payload
    assert range_calls == ["bytes=0-"]


def test_requests_downloader_resumes_completed_pieces_from_state(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:8] + b"\0" * 4)
    state_file.write_text(
        json.dumps(
            _request_state(
                url="https://example.test/model.bin",
                total_size=len(payload),
                etag="v1",
                last_modified="Wed, 27 May 2026 00:00:00 GMT",
                completed=[True, True, False],
            )
        ),
        encoding="utf-8",
    )
    range_calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
                "ETag": "v1",
                "Last-Modified": "Wed, 27 May 2026 00:00:00 GMT",
            },
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        range_header, response = _range_response(payload, headers)
        range_calls.append(range_header)
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=2,
        max_connection_per_server=1,
        min_split_size=4,
        piece_length=4,
        continue_download=True,
    )

    assert range_calls == ["bytes=8-"]
    assert result.read_bytes() == payload


def test_requests_downloader_loads_matching_partial_state_without_continue_flag(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:6] + b"\0" * 6)
    state_file.write_text(
        json.dumps(
            _request_state(
                url="https://example.test/model.bin",
                total_size=len(payload),
                completed=[True, False, False],
                in_flight_lengths=[0, 2, 0],
            )
        ),
        encoding="utf-8",
    )
    range_calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        range_header, response = _range_response(payload, headers)
        range_calls.append(range_header)
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=2,
        max_connection_per_server=1,
        min_split_size=4,
        piece_length=4,
    )

    assert range_calls == ["bytes=6-"]
    assert result.read_bytes() == payload


def test_requests_downloader_continues_partial_temp_file_without_state(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    temp_file = tmp_path / "model.bin.tmp"
    temp_file.write_bytes(payload[:6])
    range_calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        range_header, response = _range_response(payload, headers)
        range_calls.append(range_header)
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=2,
        max_connection_per_server=1,
        min_split_size=4,
        piece_length=4,
        continue_download=True,
    )

    assert range_calls == ["bytes=6-"]
    assert result.read_bytes() == payload


def test_requests_downloader_rejects_unsupported_resume_state_version(monkeypatch, tmp_path):
    payload = b"abcdefghijklmnop"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload)
    state_file.write_text(
        json.dumps(
            {
                "version": 1,
                "url": "https://example.test/model.bin",
                "total_size": len(payload),
                "etag": "v1",
                "last_modified": "Wed, 27 May 2026 00:00:00 GMT",
                "range_plan": {"mode": "fixed", "chunk_size": 4, "num_threads": 4},
                "completed_ranges": [[0, len(payload) - 1]],
            }
        ),
        encoding="utf-8",
    )

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
                "ETag": "v1",
                "Last-Modified": "Wed, 27 May 2026 00:00:00 GMT",
            },
        )

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(RuntimeError, match="状态版本不匹配"):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            progress=False,
            split=4,
            max_connection_per_server=1,
            min_split_size=4,
            piece_length=4,
            continue_download=True,
        )


def test_requests_downloader_rejects_malformed_resume_state(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload)
    state_file.write_text("{", encoding="utf-8")

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(RuntimeError, match="有效 JSON"):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            progress=False,
            split=2,
            max_connection_per_server=1,
            min_split_size=4,
            piece_length=4,
        )


def test_requests_downloader_skips_unchanged_json_state_writes(monkeypatch, tmp_path):
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file = tmp_path / "model.bin.tmp"
    temp_file.write_bytes(b"\0" * 8)
    storage = requests_downloader._PieceStorage(total_size=8, piece_length=4)
    options = requests_downloader._DownloadOptions(
        split=1,
        max_connection_per_server=1,
        min_split_size=4,
        piece_length=4,
        allow_piece_length_change=False,
        max_tries=1,
        retry_wait=0,
        continue_download=False,
        conditional_get=False,
        remote_time=True,
    )
    write_calls = []
    replace_calls = []
    original_write_text = Path.write_text
    original_replace = Path.replace

    def spy_write_text(self, *args, **kwargs):
        if self.name.endswith("__temp"):
            write_calls.append(self.name)
        return original_write_text(self, *args, **kwargs)

    def spy_replace(self, target):
        replace_calls.append((self.name, Path(target).name))
        return original_replace(self, target)

    monkeypatch.setattr(Path, "write_text", spy_write_text)
    monkeypatch.setattr(Path, "replace", spy_replace)

    requests_downloader._save_resume_state(
        state_file,
        urls=["https://example.test/model.bin"],
        remote_info=requests_downloader._RemoteFileInfo(total_size=8, supports_range=True),
        options=options,
        piece_storage=storage,
    )
    requests_downloader._save_resume_state(
        state_file,
        urls=["https://example.test/model.bin"],
        remote_info=requests_downloader._RemoteFileInfo(total_size=8, supports_range=True),
        options=options,
        piece_storage=storage,
    )

    assert write_calls == ["model.bin.tmp.state.json__temp"]
    assert replace_calls == [("model.bin.tmp.state.json__temp", "model.bin.tmp.state.json")]
    assert json.loads(state_file.read_text(encoding="utf-8"))["version"] == requests_downloader.STATE_VERSION

    requests_downloader._state_temp_path_for(state_file).write_text("stale", encoding="utf-8")
    requests_downloader._cleanup_resume_files(temp_file, state_file)
    assert not state_file.exists()
    assert not requests_downloader._state_temp_path_for(state_file).exists()


def test_requests_downloader_normalizes_options_with_aria2_bounds(monkeypatch):
    monkeypatch.setattr(requests_downloader, "ARIA2_SIZE_OPTION_MIN", 1024 * 1024)
    monkeypatch.setattr(requests_downloader, "ARIA2_SIZE_OPTION_MAX", 1024 * 1024 * 1024)

    options = requests_downloader._normalize_options(
        split=5,
        max_connection_per_server=16,
        min_split_size=1024 * 1024,
        piece_length=1024 * 1024,
        allow_piece_length_change=True,
        max_tries=0,
        retry_wait=10,
        continue_download=True,
        conditional_get=True,
        remote_time=False,
    )

    assert options.max_connection_per_server == 16
    assert options.min_split_size == 1024 * 1024
    assert options.piece_length == 1024 * 1024
    assert options.allow_piece_length_change is True
    assert options.max_tries == 0
    assert options.retry_wait == 10
    assert options.continue_download is True
    assert options.conditional_get is True
    assert options.remote_time is False

    with pytest.raises(ValueError, match="max_connection_per_server"):
        requests_downloader._normalize_options(
            split=1,
            max_connection_per_server=17,
            min_split_size=1024 * 1024,
            piece_length=1024 * 1024,
            allow_piece_length_change=False,
            max_tries=1,
            retry_wait=0,
            continue_download=False,
            conditional_get=False,
            remote_time=True,
        )
    with pytest.raises(ValueError, match="min_split_size"):
        requests_downloader._normalize_options(
            split=1,
            max_connection_per_server=1,
            min_split_size=1024 * 1024 - 1,
            piece_length=1024 * 1024,
            allow_piece_length_change=False,
            max_tries=1,
            retry_wait=0,
            continue_download=False,
            conditional_get=False,
            remote_time=True,
        )
    with pytest.raises(ValueError, match="piece_length"):
        requests_downloader._normalize_options(
            split=1,
            max_connection_per_server=1,
            min_split_size=1024 * 1024,
            piece_length=1024 * 1024 * 1024 + 1,
            allow_piece_length_change=False,
            max_tries=1,
            retry_wait=0,
            continue_download=False,
            conditional_get=False,
            remote_time=True,
        )
    with pytest.raises(ValueError, match="max_tries"):
        requests_downloader._normalize_options(
            split=1,
            max_connection_per_server=1,
            min_split_size=1024 * 1024,
            piece_length=1024 * 1024,
            allow_piece_length_change=False,
            max_tries=-1,
            retry_wait=0,
            continue_download=False,
            conditional_get=False,
            remote_time=True,
        )
    with pytest.raises(ValueError, match="retry_wait"):
        requests_downloader._normalize_options(
            split=1,
            max_connection_per_server=1,
            min_split_size=1024 * 1024,
            piece_length=1024 * 1024,
            allow_piece_length_change=False,
            max_tries=1,
            retry_wait=601,
            continue_download=False,
            conditional_get=False,
            remote_time=True,
        )


def test_requests_downloader_resumes_state_when_scheduling_options_change(monkeypatch, tmp_path):
    payload = b"abcdefghijklmnop"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:4] + b"\0" * 12)
    state_file.write_text(
        json.dumps(
            _request_state(
                url="https://example.test/model.bin",
                total_size=len(payload),
                etag="v1",
                last_modified="Wed, 27 May 2026 00:00:00 GMT",
                completed=[True, False, False, False],
            )
        ),
        encoding="utf-8",
    )
    range_calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
                "ETag": "v1",
                "Last-Modified": "Wed, 27 May 2026 00:00:00 GMT",
            },
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        range_header, response = _range_response(payload, headers)
        range_calls.append(range_header)
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=8,
        max_connection_per_server=4,
        min_split_size=8,
        piece_length=4,
        continue_download=True,
    )

    assert result.read_bytes() == payload
    assert "bytes=4-" in range_calls


def test_requests_downloader_rejects_piece_length_change_with_progress(monkeypatch, tmp_path):
    payload = b"abcdefghijklmnop"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:4] + b"\0" * 12)
    state_file.write_text(
        json.dumps(
            _request_state(
                url="https://example.test/model.bin",
                total_size=len(payload),
                completed=[True, False, False, False],
                piece_length=4,
            )
        ),
        encoding="utf-8",
    )

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(RuntimeError, match="piece_length"):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            progress=False,
            split=2,
            max_connection_per_server=1,
            min_split_size=4,
            piece_length=8,
        )


def test_requests_downloader_converts_completed_bitfield_when_piece_length_change_is_allowed(monkeypatch, tmp_path):
    payload = b"abcdefghijklmnop"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:10] + b"\0" * 6)
    state_file.write_text(
        json.dumps(
            _request_state(
                url="https://example.test/model.bin",
                total_size=len(payload),
                completed=[True, True, False, False],
                in_flight_lengths=[0, 0, 2, 0],
                piece_length=4,
            )
        ),
        encoding="utf-8",
    )
    calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        calls.append(headers.get("Range") if headers else None)
        _, response = _range_response(payload, headers)
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=2,
        max_connection_per_server=1,
        min_split_size=4,
        piece_length=8,
        allow_piece_length_change=True,
    )

    assert calls == ["bytes=8-"]
    assert result.read_bytes() == payload


def test_requests_downloader_ignores_resume_state_url_and_validator_metadata(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:8] + b"\0" * 4)
    state_file.write_text(
        json.dumps(
            _request_state(
                url="https://old.example.test/old.bin",
                total_size=len(payload),
                etag="old",
                last_modified="old-date",
                completed=[True, True, False],
            )
        ),
        encoding="utf-8",
    )
    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
                "ETag": "new",
                "Last-Modified": "new-date",
            },
        )
    range_calls = []

    def fake_get(url, stream=True, timeout=60, headers=None):
        range_header, response = _range_response(payload, headers)
        range_calls.append(range_header)
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=2,
        max_connection_per_server=1,
        min_split_size=4,
        piece_length=4,
        continue_download=True,
    )

    assert range_calls == ["bytes=8-"]
    assert result.read_bytes() == payload


def test_requests_downloader_rejects_malformed_in_flight_piece(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:6] + b"\0" * 6)
    state = _request_state(
        url="https://example.test/model.bin",
        total_size=len(payload),
        completed=[True, False, False],
        in_flight_lengths=[0, 2, 0],
    )
    state["in_flight_pieces"][0]["bitfield"] = "ff"
    state_file.write_text(json.dumps(state), encoding="utf-8")

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(RuntimeError, match="bitfield"):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            progress=False,
            split=2,
            max_connection_per_server=1,
            min_split_size=4,
            piece_length=4,
        )


def test_requests_downloader_preserves_resume_state_when_range_probe_is_unsupported(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:4] + b"\0" * 8)
    state_file.write_text(
        json.dumps(
            _request_state(
                url="https://example.test/model.bin",
                total_size=len(payload),
                completed=[True, False, False],
            )
        ),
        encoding="utf-8",
    )
    calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload))})

    def fake_get(url, stream=True, timeout=60, headers=None):
        calls.append(headers.get("Range") if headers else None)
        if headers and "Range" in headers:
            return FakeRangeResponse(payload, status_code=200, headers={"Content-Length": str(len(payload))})
        return FakeRangeResponse(payload, status_code=200, headers={"content-length": str(len(payload))})

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(IOError, match="HTTP Range"):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            progress=False,
            split=4,
            max_connection_per_server=1,
            min_split_size=4,
            piece_length=4,
        )

    assert calls == ["bytes=0-0", "bytes=4-"]
    assert temp_file.exists()
    assert state_file.exists()


def test_requests_downloader_preserves_state_when_content_range_is_invalid(monkeypatch, tmp_path):
    payload = b"abcdefghijklmnop"
    calls = []
    range_failed = False

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        nonlocal range_failed
        calls.append(headers.get("Range") if headers else None)
        if not range_failed:
            range_failed = True
            return FakeRangeResponse(payload[:4], status_code=206, headers={"Content-Range": f"bytes 1-4/{len(payload)}"})
        return FakeRangeResponse(payload, status_code=200, headers={"Content-Length": str(len(payload))})

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(IOError, match="HTTP Range"):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            progress=False,
            split=1,
            min_split_size=4,
            piece_length=4,
        )

    assert calls == ["bytes=0-"]
    assert (tmp_path / "model.bin.tmp").exists()
    assert (tmp_path / "model.bin.tmp.state.json").exists()


def test_requests_downloader_skips_range_validation_for_transfer_encoding():
    # TE + 206 with start > 0: range is satisfied (server returned 206), skip further check
    response_206 = FakeRangeResponse(
        b"chunk",
        status_code=206,
        headers={"Transfer-Encoding": "chunked"},
    )
    segment_nonzero = requests_downloader._Segment(start_piece=1, end_piece=1, start=4, end=7, piece_start=4)
    requests_downloader._validate_range_response(response_206, segment=segment_nonzero, total_size=12, attempt=1, retry_wait=0)

    # TE + 200 with start == 0: server sending full body from byte 0, no corruption
    response_200_start0 = FakeRangeResponse(
        b"chunk",
        status_code=200,
        headers={"Transfer-Encoding": "chunked"},
    )
    segment_zero = requests_downloader._Segment(start_piece=0, end_piece=0, start=0, end=3, piece_start=0)
    requests_downloader._validate_range_response(response_200_start0, segment=segment_zero, total_size=12, attempt=1, retry_wait=0)


def test_requests_downloader_transfer_encoding_200_with_nonzero_start_raises():
    # TE + 200 with start > 0: server ignored Range, would corrupt the file
    response = FakeRangeResponse(
        b"chunk",
        status_code=200,
        headers={"Transfer-Encoding": "chunked"},
    )
    segment = requests_downloader._Segment(start_piece=1, end_piece=1, start=4, end=7, piece_start=4)

    with pytest.raises(requests_downloader._RangeRequestIgnored):
        requests_downloader._validate_range_response(response, segment=segment, total_size=12, attempt=1, retry_wait=0)


def test_requests_downloader_preserves_state_when_resume_range_is_ignored(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:4] + b"\0" * 8)
    state_file.write_text(
        json.dumps(
            _request_state(
                url="https://example.test/model.bin",
                total_size=len(payload),
                completed=[True, False, False],
            )
        ),
        encoding="utf-8",
    )
    calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        calls.append(headers.get("Range") if headers else None)
        return FakeRangeResponse(payload, status_code=200, headers={"Content-Length": str(len(payload))})

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(IOError, match="HTTP Range"):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            progress=False,
            split=2,
            max_connection_per_server=1,
            min_split_size=4,
            piece_length=4,
        )

    assert calls == ["bytes=4-"]
    assert temp_file.exists()
    assert state_file.exists()


def test_requests_downloader_retries_failed_ranges(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:4] + b"\0" * 8)
    state_file.write_text(
        json.dumps(
            _request_state(
                url="https://example.test/model.bin",
                total_size=len(payload),
                completed=[True, False, False],
            )
        ),
        encoding="utf-8",
    )
    attempts = {}

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        range_header = headers["Range"]
        attempts[range_header] = attempts.get(range_header, 0) + 1
        if range_header == "bytes=4-" and attempts[range_header] == 1:
            return FakeRangeResponse(status_code=503, headers={"Retry-After": "0"})
        _, response = _range_response(payload, headers)
        return response

    sleep_calls = []
    monkeypatch.setattr(requests_downloader.time, "sleep", lambda seconds: sleep_calls.append(seconds))
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=2,
        max_connection_per_server=1,
        min_split_size=4,
        piece_length=4,
        continue_download=True,
        max_tries=2,
        retry_wait=7,
    )

    assert result.read_bytes() == payload
    assert attempts["bytes=4-"] == 2
    assert sleep_calls == [7.0]


def test_requests_downloader_retries_from_partial_piece_offset(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        range_header = headers.get("Range") if headers else None
        calls.append(range_header)
        if len(calls) == 1:
            return FakeRangeResponse(payload[:6], status_code=200, headers={"Content-Length": str(len(payload))})
        _, response = _range_response(payload, headers)
        return response

    monkeypatch.setattr(requests_downloader.time, "sleep", lambda _seconds: None)
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=1,
        max_connection_per_server=1,
        min_split_size=4,
        piece_length=4,
        max_tries=2,
    )

    assert calls == ["bytes=0-", "bytes=6-"]
    assert result.read_bytes() == payload


def test_requests_downloader_uses_and_closes_thread_sessions(monkeypatch, tmp_path):
    payload = b"abcdefghijklmnop"
    sessions = []
    range_calls = []

    class FakeSession:
        def __init__(self):
            self.closed = False
            sessions.append(self)

        def mount(self, prefix, adapter):
            pass

        def get(self, url, stream=True, timeout=60, headers=None):
            range_header, response = _range_response(payload, headers)
            range_calls.append(range_header)
            return response

        def close(self):
            self.closed = True

    class FakeAdapter:
        def __init__(self, pool_connections, pool_maxsize):
            self.pool_connections = pool_connections
            self.pool_maxsize = pool_maxsize

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    fake_requests = types.SimpleNamespace(
        head=fake_head,
        get=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("range downloads should use sessions")),
        Session=FakeSession,
        adapters=types.SimpleNamespace(HTTPAdapter=FakeAdapter),
    )
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=2,
        max_connection_per_server=2,
        min_split_size=4,
        piece_length=4,
    )

    assert result.read_bytes() == payload
    assert "bytes=0-" in range_calls
    assert all(item.endswith("-") for item in range_calls)
    assert sessions
    assert all(session.closed for session in sessions)


def test_requests_downloader_closes_thread_sessions_after_range_failure(monkeypatch, tmp_path):
    payload = b"abcdefghijklmnop"
    sessions = []

    class FakeSession:
        def __init__(self):
            self.closed = False
            sessions.append(self)

        def get(self, url, stream=True, timeout=60, headers=None):
            return FakeRangeResponse(status_code=503, headers={"Retry-After": "0"})

        def close(self):
            self.closed = True

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, Session=FakeSession))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))
    monkeypatch.setattr(requests_downloader.time, "sleep", lambda _seconds: None)

    with pytest.raises(IOError):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            progress=False,
            split=2,
            max_connection_per_server=2,
            min_split_size=4,
            piece_length=4,
            max_tries=1,
        )

    assert sessions
    assert all(session.closed for session in sessions)


def test_requests_downloader_batches_state_writes_and_updates_streaming_progress(monkeypatch, tmp_path):
    payload = b"abcdefghijklmnop"
    save_state_calls = []
    progress_bars = []

    class TrackingTqdm(FakeTqdm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            progress_bars.append(self)

    original_save_state = requests_downloader._save_resume_state

    def fake_save_state(*args, **kwargs):
        save_state_calls.append(kwargs["piece_storage"].snapshot_completed())
        return original_save_state(*args, **kwargs)

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        _, response = _range_response(payload, headers)
        return response

    monkeypatch.setattr(requests_downloader, "_save_resume_state", fake_save_state)
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=TrackingTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=True,
        split=4,
        max_connection_per_server=1,
        min_split_size=1,
        piece_length=1,
        continue_download=True,
    )

    assert result.read_bytes() == payload
    assert 0 < len(save_state_calls) < len(payload)
    assert progress_bars[-1].n == len(payload)


def test_requests_downloader_range_hash_mismatch_cleans_temp_files(monkeypatch, tmp_path):
    payload = b"wrong hash payload"

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        _, response = _range_response(payload, headers)
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(ValueError):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            progress=False,
            hash_prefix="0" * 12,
            split=2,
            max_connection_per_server=1,
            min_split_size=4,
            piece_length=4,
        )

    assert not (tmp_path / "model.bin.tmp").exists()
    assert not (tmp_path / "model.bin.tmp.state.json").exists()


class FakeUrllibResponse:
    def __init__(self, payload):
        self.payload = payload
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def getheader(self, name, default=None):
        return str(len(self.payload)) if name == "Content-Length" else default

    def read(self, size):
        chunk = self.payload[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


def test_urllib_downloader_uses_user_agent_cache_and_hash(monkeypatch, tmp_path):
    payload = b"urllib payload"
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, request.headers.get("User-agent"), timeout))
        return FakeUrllibResponse(payload)

    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))
    monkeypatch.setattr(urllib_downloader.urllib.request, "urlopen", fake_urlopen)

    result = urllib_downloader.download_file_from_url_urllib(
        "https://example.test/archive.tar.gz",
        save_path=tmp_path,
        progress=False,
        hash_prefix=hashlib.sha256(payload).hexdigest()[:8],
    )

    assert result == (tmp_path / "archive.tar.gz").resolve()
    assert result.read_bytes() == payload
    assert calls == [("https://example.test/archive.tar.gz", "Mozilla/5.0", 60)]

    urllib_downloader.download_file_from_url_urllib("https://example.test/archive.tar.gz", save_path=tmp_path, progress=False)
    assert len(calls) == 1


def test_compare_sha256_strips_and_lowercases_prefix(tmp_path):
    file_path = tmp_path / "data.bin"
    file_path.write_bytes(b"abc")
    digest = hashlib.sha256(b"abc").hexdigest()

    assert compare_sha256(file_path, f"  {digest[:10].upper()}  ") is True
    assert compare_sha256(file_path, "0" * 10) is False


def test_aria2_server_pool_refcounts_and_aria2_wrapper(monkeypatch, tmp_path):
    events = []

    class FakeServer:
        def __enter__(self):
            events.append("enter")
            return self

        def __exit__(self, *_args):
            events.append("exit")

        def download(self, **kwargs):
            events.append(("download", kwargs))
            save_name = kwargs["save_name"] or requests_downloader._filename_from_url(kwargs["url"][0])
            return kwargs["save_path"] / save_name

    monkeypatch.setattr(aria2_downloader, "Aria2RpcServer", lambda use_external_server=False: FakeServer())

    pool = aria2_downloader._Aria2ServerPool()
    first = pool.acquire()
    second = pool.acquire()
    assert first is second
    assert events == ["enter"]
    pool.release()
    assert events == ["enter"]
    pool.release()
    assert events == ["enter", "exit"]

    monkeypatch.setattr(aria2_downloader, "_server_pool", aria2_downloader._Aria2ServerPool())
    result = aria2_downloader.aria2("https://example.test/asset.bin", path=tmp_path, progress=False)
    assert result == tmp_path / "asset.bin"
    assert events[-2][0] == "download"
    assert events[-2][1]["url"] == ["https://example.test/asset.bin"]
    assert events[-2][1]["save_path"] == tmp_path
    assert events[-2][1]["save_name"] is None
    assert events[-2][1]["options"]["allow-piece-length-change"] == "false"
    assert events[-2][1]["options"]["retry-wait"] == "0"
    assert events[-2][1]["options"]["conditional-get"] == "false"
    assert events[-2][1]["options"]["remote-time"] == "true"

    result = aria2_downloader.aria2(
        "https://example.test/asset.bin",
        path=tmp_path,
        save_name="renamed.bin",
        progress=False,
        allow_piece_length_change=True,
        max_tries=0,
        retry_wait=9,
        conditional_get=True,
        remote_time=False,
    )
    assert result == tmp_path / "renamed.bin"
    assert events[-2][1]["save_name"] == "renamed.bin"
    assert events[-2][1]["options"]["allow-piece-length-change"] == "true"
    assert events[-2][1]["options"]["max-tries"] == "0"
    assert events[-2][1]["options"]["retry-wait"] == "9"
    assert events[-2][1]["options"]["conditional-get"] == "true"
    assert events[-2][1]["options"]["remote-time"] == "false"

    result = aria2_downloader.aria2(
        ["https://mirror-a.example.test/multi.bin", "https://mirror-b.example.test/multi.bin"],
        path=tmp_path,
        progress=False,
    )
    assert result == tmp_path / "multi.bin"
    assert events[-2][1]["url"] == [
        "https://mirror-a.example.test/multi.bin",
        "https://mirror-b.example.test/multi.bin",
    ]
    assert events[-2][1]["save_name"] is None

    before_invalid_call = list(events)
    with pytest.raises(ValueError, match="max_connection_per_server"):
        aria2_downloader.aria2(
            "https://example.test/asset.bin",
            path=tmp_path,
            progress=False,
            max_connection_per_server=17,
        )
    assert events == before_invalid_call


def test_aria2_rpc_call_includes_token_and_retries(monkeypatch):
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"result": {"version": "1.37.0"}}).encode("utf-8")

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, json.loads(request.data.decode("utf-8")), timeout))
        if len(calls) == 1:
            raise urllib.error.URLError("not ready")
        return FakeResponse()

    monkeypatch.setattr(aria2_server.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(aria2_server.time, "sleep", lambda _seconds: None)

    server = aria2_server.Aria2RpcServer(port=6801, secret="secret")
    assert server._rpc_call("aria2.getVersion", ["x"], retry_count=2) == {"version": "1.37.0"}
    assert calls[1][1]["params"] == ["token:secret", "x"]


def test_aria2_rpc_call_errors_on_rpc_error_and_bad_json(monkeypatch):
    class ErrorResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"error": {"code": 1, "message": "boom"}}).encode("utf-8")

    monkeypatch.setattr(aria2_server.urllib.request, "urlopen", lambda *_args, **_kwargs: ErrorResponse())
    server = aria2_server.Aria2RpcServer(port=6801)
    with pytest.raises(RuntimeError, match="RPC Error 1"):
        server._rpc_call("aria2.tellStatus")

    class BadJsonResponse(ErrorResponse):
        def read(self):
            return b"{"

    monkeypatch.setattr(aria2_server.urllib.request, "urlopen", lambda *_args, **_kwargs: BadJsonResponse())
    with pytest.raises(RuntimeError, match="JSON"):
        server._rpc_call("aria2.tellStatus")


def test_aria2_download_and_batch_waiting(monkeypatch, tmp_path):
    server = aria2_server.Aria2RpcServer(download_dir=tmp_path)
    server.process = types.SimpleNamespace(poll=lambda: None)
    monkeypatch.setattr(aria2_server.time, "sleep", lambda _seconds: None)

    calls = []
    statuses = {
        "gid-1": {"status": "complete", "totalLength": "10", "completedLength": "10", "files": [{"path": (tmp_path / "one.bin").as_posix()}]},
        "gid-2": {"status": "error", "totalLength": "10", "completedLength": "1", "errorMessage": "network", "errorCode": "7"},
    }

    def fake_rpc(method, params=None, retry_count=3):
        calls.append((method, params, retry_count))
        if method == "aria2.addUri":
            return "gid-1"
        if method == "aria2.tellStatus":
            return statuses[params[0]]
        raise AssertionError(method)

    server._rpc_call = fake_rpc
    assert server.download("https://example.test/one.bin", save_path=tmp_path, show_progress=False) == tmp_path / "one.bin"
    assert calls[0] == ("aria2.addUri", [["https://example.test/one.bin"], {"dir": tmp_path.as_posix()}], 3)

    calls.clear()
    assert (
        server.download(
            ["https://mirror-a.example.test/one.bin", "https://mirror-b.example.test/one.bin"],
            save_path=tmp_path,
            show_progress=False,
        )
        == tmp_path / "one.bin"
    )
    assert calls[0] == (
        "aria2.addUri",
        [
            ["https://mirror-a.example.test/one.bin", "https://mirror-b.example.test/one.bin"],
            {"dir": tmp_path.as_posix()},
        ],
        3,
    )

    server._rpc_call = lambda method, params=None, retry_count=3: "gid-2" if method == "aria2.addUri" else statuses["gid-2"]
    with pytest.raises(RuntimeError, match="network"):
        server.download("https://example.test/two.bin", save_path=tmp_path, show_progress=False)


def test_aria2_start_reuses_external_server_and_stop_skips(monkeypatch, tmp_path):
    monkeypatch.setattr(aria2_server.shutil, "which", lambda name: "/bin/aria2c" if name == "aria2c" else None)
    monkeypatch.setattr(aria2_server, "is_port_in_use", lambda _port: True)

    server = aria2_server.Aria2RpcServer(port=6800, download_dir=tmp_path, use_external_server=True)
    monkeypatch.setattr(server, "_test_connection", lambda: True)
    monkeypatch.setattr(server, "_rpc_call", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not stop external")))

    server._start_server()
    assert server._is_external_server is True
    assert server.process is None
    server._stop_server()


def test_aria2_wait_download_detects_process_crash(tmp_path):
    server = aria2_server.Aria2RpcServer(download_dir=tmp_path, log_file=tmp_path / "aria2.log")
    server.process = types.SimpleNamespace(poll=lambda: 1, stderr=None)

    with pytest.raises(RuntimeError, match="aria2 进程已崩溃"):
        server._wait_download("gid", "file.bin", show_progress=False)


def test_aria2_start_uses_free_port_and_stop_cleans_session(monkeypatch, tmp_path):
    commands = []

    class FakeProcess:
        def __init__(self, command, **kwargs):
            commands.append((command, kwargs))
            self.stderr = None
            self.killed = False
            self.waits = []

        def poll(self):
            return None

        def wait(self, timeout=None):
            self.waits.append(timeout)
            return 0

        def kill(self):
            self.killed = True

    monkeypatch.setattr(aria2_server.shutil, "which", lambda name: "/bin/aria2c" if name == "aria2c" else None)
    monkeypatch.setattr(aria2_server, "is_port_in_use", lambda _port: True)
    monkeypatch.setattr(aria2_server, "find_port", lambda port: port + 1)
    monkeypatch.setattr(aria2_server.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(aria2_server.Aria2RpcServer, "_test_connection", lambda _self: True)

    server = aria2_server.Aria2RpcServer(port=6800, download_dir=tmp_path, use_config_file=False, use_external_server=False)
    server._start_server()

    assert server.port == 6801
    assert server.rpc_url == "http://localhost:6801/jsonrpc"
    assert commands[0][0][:3] == ["aria2c", "--enable-rpc=true", "--rpc-listen-port=6801"]
    session_path = Path(server._session_file.name)
    assert session_path.exists()

    rpc_calls = []
    server._rpc_call = lambda method, *args, **kwargs: rpc_calls.append((method, args, kwargs))
    server._stop_server()

    assert rpc_calls[0][0] == "aria2.shutdown"
    assert server.process.waits == [5]
    assert not session_path.exists()


def test_aria2_stop_kills_timeout_process_and_removes_session(tmp_path):
    events = []

    class FakeProcess:
        stderr = None

        def poll(self):
            return None

        def wait(self, timeout=None):
            events.append(("wait", timeout))
            if timeout == 5:
                raise subprocess.TimeoutExpired("aria2c", timeout)
            return 0

        def kill(self):
            events.append("kill")

    session_file = tmp_path / "session.aria2"
    session_file.write_text("", encoding="utf-8")

    server = aria2_server.Aria2RpcServer(download_dir=tmp_path)
    server.process = FakeProcess()
    server._session_file = types.SimpleNamespace(name=session_file.as_posix())
    server._rpc_call = lambda method, *args, **kwargs: events.append(method)

    server._stop_server()

    assert events == ["aria2.shutdown", ("wait", 5), "kill", ("wait", None)]
    assert not session_file.exists()


def test_aria2_download_batch_keeps_successful_downloads(monkeypatch, tmp_path):
    server = aria2_server.Aria2RpcServer(download_dir=tmp_path)
    add_calls = []

    def fake_rpc(method, params=None, retry_count=3):
        if method != "aria2.addUri":
            raise AssertionError(method)
        url = params[0][0]
        add_calls.append(params)
        if "bad-add" in url:
            raise RuntimeError("add bad")
        return "gid-fail" if "bad-wait" in url else f"gid-{len(add_calls)}"

    def fake_wait(gid, file_name, show_progress):
        if gid == "gid-fail":
            raise RuntimeError("download bad")
        return tmp_path / file_name

    server._rpc_call = fake_rpc
    server._wait_download = fake_wait

    result = server.download_batch(
        ["https://example.test/one.bin", "https://example.test/bad-add.bin", "https://example.test/bad-wait.bin"],
        save_path=tmp_path,
        options={"split": "8"},
        show_progress=False,
    )

    assert result == [tmp_path / "one.bin"]
    assert add_calls[0][1]["out"] == "one.bin"
    assert add_calls[0][1]["split"] == "8"
    assert add_calls[2][1]["out"] == "bad-wait.bin"

    server._rpc_call = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("all bad"))
    with pytest.raises(RuntimeError, match="没有成功添加任何下载任务"):
        server.download_batch(["https://example.test/fail.bin"], save_path=tmp_path, show_progress=False)


def test_aria2_wait_download_removed_and_repeated_query_failures(monkeypatch, tmp_path):
    server = aria2_server.Aria2RpcServer(download_dir=tmp_path)
    server.process = types.SimpleNamespace(poll=lambda: None, stderr=None)
    monkeypatch.setattr(aria2_server.time, "sleep", lambda _seconds: None)

    server._rpc_call = lambda method, params=None, retry_count=3: {"status": "removed", "totalLength": "0", "completedLength": "0"}
    with pytest.raises(RuntimeError, match="下载任务已被移除"):
        server._wait_download("gid", "removed.bin", show_progress=False)

    attempts = []

    def failing_rpc(method, params=None, retry_count=3):
        attempts.append((method, params, retry_count))
        raise ValueError("temporary rpc parse error")

    server._rpc_call = failing_rpc
    with pytest.raises(RuntimeError, match="连续 5 次查询下载状态失败"):
        server._wait_download("gid", "broken.bin", show_progress=False)

    assert len(attempts) == 5


def test_aria2_rpc_wrapper_methods_delegate_to_expected_methods():
    server = aria2_server.Aria2RpcServer()
    calls = []

    def fake_rpc(method, params=None, retry_count=3):
        calls.append((method, params, retry_count))
        return {"method": method, "params": params}

    server._rpc_call = fake_rpc

    assert server.get_version()["method"] == "aria2.getVersion"
    assert server.get_global_stat()["method"] == "aria2.getGlobalStat"
    assert server.pause("gid")["params"] == ["gid"]
    assert server.unpause("gid")["method"] == "aria2.unpause"
    assert server.remove("gid")["method"] == "aria2.remove"
    assert server.tell_status("gid", ["status"])["params"] == ["gid", ["status"]]
    assert server.tell_active()["method"] == "aria2.tellActive"
    assert server.tell_waiting(2, 3)["params"] == [2, 3]
    assert server.tell_stopped(4, 5)["params"] == [4, 5]

    assert calls == [
        ("aria2.getVersion", None, 3),
        ("aria2.getGlobalStat", None, 3),
        ("aria2.pause", ["gid"], 3),
        ("aria2.unpause", ["gid"], 3),
        ("aria2.remove", ["gid"], 3),
        ("aria2.tellStatus", ["gid", ["status"]], 3),
        ("aria2.tellActive", None, 3),
        ("aria2.tellWaiting", [2, 3], 3),
        ("aria2.tellStopped", [4, 5], 3),
    ]
