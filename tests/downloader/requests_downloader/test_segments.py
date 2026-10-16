"""requests 下载器分片调度与 Range 下载测试"""

import sys
import types

import pytest

from sd_webui_all_in_one.downloader import requests_downloader
from sd_webui_all_in_one.downloader.requests_downloader import models as requests_models
from sd_webui_all_in_one.downloader.requests_downloader import scheduler as requests_scheduler
from sd_webui_all_in_one.downloader.requests_downloader import transfer as requests_transfer
from tests.downloader.helpers import FakeRangeResponse, FakeRequestsResponse, FakeTqdm, range_response

pytestmark = pytest.mark.usefixtures("small_aria2_size_bounds")


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


def test_piece_storage_checks_out_dynamic_segments():
    storage = requests_scheduler._PieceStorage(total_size=16, piece_length=4)

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
    storage = requests_scheduler._PieceStorage(total_size=12, piece_length=4, in_flight_lengths=[0, 2, 0])
    manager = requests_scheduler._SegmentManager(storage, min_split_size=4)

    first = storage.check_out_piece(0)
    assert first is not None
    assert storage.mark_complete(first) == 1

    assert manager.get_next_segment(first) is None
    resumed = manager.get_segment()
    assert resumed is not None
    assert resumed.byte_range == (6, 7)


def test_segment_manager_steals_clean_segment_from_idle_owner():
    storage = requests_scheduler._PieceStorage(total_size=12, piece_length=4)
    manager = requests_scheduler._SegmentManager(storage, min_split_size=4)

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
    pool = requests_scheduler._UriPool(
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
    piece_length = 4
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
            end = piece_length - 1
        else:
            start_text, end_text = range_header.removeprefix("bytes=").split("-", maxsplit=1)
            start = int(start_text)
            # Cap at one piece so each response never spills into a neighbouring
            # piece — otherwise a fast Worker 1 can claim piece 1 via stream
            # continuation before Worker 2 starts (timing-dependent race).
            end = min(start + piece_length - 1, len(payload) - 1) if end_text == "" else int(end_text)
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
        range_header, response = range_response(payload, headers)
        range_calls.append(range_header)
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

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
        range_header, response = range_response(payload, headers)
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


def test_requests_downloader_falls_back_to_single_stream_without_range(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload))})

    def fake_get(url, stream=True, timeout=60, headers=None):
        calls.append(headers.get("Range") if headers else None)
        return FakeRangeResponse(payload, status_code=200, headers={"Content-Length": str(len(payload))})

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=4,
        min_split_size=4,
        piece_length=4,
    )

    assert calls == ["bytes=0-0", None]
    assert result.read_bytes() == payload


def test_requests_downloader_skips_range_validation_for_transfer_encoding():
    # TE + 206 with start > 0: range is satisfied (server returned 206), skip further check
    response_206 = FakeRangeResponse(
        b"chunk",
        status_code=206,
        headers={"Transfer-Encoding": "chunked"},
    )
    segment_nonzero = requests_models._Segment(start_piece=1, end_piece=1, start=4, end=7, piece_start=4)
    requests_transfer._validate_range_response(response_206, segment=segment_nonzero, total_size=12, attempt=1, retry_wait=0)

    # TE + 200 with start == 0: server sending full body from byte 0, no corruption
    response_200_start0 = FakeRangeResponse(
        b"chunk",
        status_code=200,
        headers={"Transfer-Encoding": "chunked"},
    )
    segment_zero = requests_models._Segment(start_piece=0, end_piece=0, start=0, end=3, piece_start=0)
    requests_transfer._validate_range_response(response_200_start0, segment=segment_zero, total_size=12, attempt=1, retry_wait=0)


def test_requests_downloader_transfer_encoding_200_with_nonzero_start_raises():
    # TE + 200 with start > 0: server ignored Range, would corrupt the file
    response = FakeRangeResponse(
        b"chunk",
        status_code=200,
        headers={"Transfer-Encoding": "chunked"},
    )
    segment = requests_models._Segment(start_piece=1, end_piece=1, start=4, end=7, piece_start=4)

    with pytest.raises(requests_models._RangeRequestIgnored):
        requests_transfer._validate_range_response(response, segment=segment, total_size=12, attempt=1, retry_wait=0)


def test_requests_downloader_uri_pool_fairly_probes_then_prefers_healthy_fast_mirror():
    first_url = "https://first.example.test/model.bin"
    second_url = "https://second.example.test/model.bin"
    pool = requests_scheduler._UriPool([first_url, second_url], max_connection_per_server=1)

    first = pool.acquire()
    assert first == first_url
    pool.release(first)
    pool.report_success(first_url, byte_count=10, elapsed=10.0)

    second = pool.acquire()
    assert second == second_url
    pool.release(second)
    pool.report_success(second_url, byte_count=100, elapsed=1.0)

    preferred = pool.acquire()
    assert preferred == second_url
    pool.release(preferred)
    assert pool.health[second_url].average_speed > pool.health[first_url].average_speed


def test_requests_downloader_uri_pool_temporarily_skips_failed_mirror():
    bad_url = "https://bad.example.test/model.bin"
    good_url = "https://good.example.test/model.bin"
    pool = requests_scheduler._UriPool([bad_url, good_url], max_connection_per_server=1)
    pool.report_failure(bad_url, OSError("temporary"), cooldown=30.0)

    selected = pool.acquire()

    assert selected == good_url
    pool.release(selected)
    assert pool.health[bad_url].failures == 1
    assert pool.health[bad_url].last_error == "temporary"


def test_requests_downloader_uri_pool_uses_redirected_host_for_connection_capacity():
    first_url = "https://mirror-a.example.test/model.bin"
    second_url = "https://mirror-b.example.test/model.bin"
    cdn_key = ("https", "cdn.example.test", 443)
    pool = requests_scheduler._UriPool(
        [first_url, second_url],
        max_connection_per_server=1,
        host_keys={first_url: cdn_key, second_url: cdn_key},
    )

    assert pool.capacity == 1
    selected = pool.acquire()
    assert selected == first_url
    assert pool.in_flight[cdn_key] == 1
    pool.release(selected)
    assert not pool.in_flight
