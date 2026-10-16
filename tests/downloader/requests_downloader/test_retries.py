"""requests 下载器重试, 镜像切换与会话管理测试"""

import json
import sys
import types

import pytest

from sd_webui_all_in_one.downloader import requests_downloader
from sd_webui_all_in_one.downloader.requests_downloader import models as requests_models
from sd_webui_all_in_one.downloader.requests_downloader import transfer as requests_transfer
from tests.downloader.helpers import FakeRangeResponse, FakeTqdm, range_response, request_state

pytestmark = pytest.mark.usefixtures("small_aria2_size_bounds")


def test_requests_downloader_retries_failed_ranges(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:4] + b"\0" * 8)
    state_file.write_text(
        json.dumps(
            request_state(
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
        _, response = range_response(payload, headers)
        return response

    sleep_calls = []
    monkeypatch.setattr(requests_transfer.time, "sleep", lambda seconds: sleep_calls.append(seconds))
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


def test_requests_downloader_does_not_retry_permanent_http_error(monkeypatch, tmp_path):
    calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": "8", "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        calls.append(headers["Range"])
        return FakeRangeResponse(status_code=404)

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(requests_models.DownloadPermanentHttpError) as exc:
        requests_downloader.download_file_from_url(
            "https://example.test/missing.bin",
            save_path=tmp_path,
            progress=False,
            split=1,
            min_split_size=4,
            piece_length=4,
            max_tries=5,
        )

    assert calls == ["bytes=0-"]
    assert exc.value.status_code == 404
    assert exc.value.url == "https://example.test/missing.bin"
    assert exc.value.segment == (0, 3)
    assert exc.value.attempt == 1


def test_requests_downloader_tries_good_mirror_after_bad_mirror_budget(monkeypatch, tmp_path):
    payload = b"abcdefgh"
    calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        calls.append(url)
        if "bad" in url:
            return FakeRangeResponse(status_code=503)
        return range_response(payload, headers)[1]

    monkeypatch.setattr(requests_transfer.time, "sleep", lambda _seconds: None)
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        ["https://bad.example.test/model.bin", "https://good.example.test/model.bin"],
        save_path=tmp_path,
        progress=False,
        split=1,
        min_split_size=8,
        piece_length=8,
        max_tries=1,
    )

    assert calls == ["https://bad.example.test/model.bin", "https://good.example.test/model.bin"]
    assert result.read_bytes() == payload


def test_requests_downloader_parses_retry_after_http_date(monkeypatch):
    monkeypatch.setattr(requests_transfer.time, "time", lambda: 1_700_000_000.0)
    retry_at = "Tue, 14 Nov 2023 22:13:25 GMT"

    delay = requests_transfer._retry_delay_for(
        {"Retry-After": retry_at},
        1,
        status_code=429,
        retry_wait=0,
    )

    assert delay == 5.0


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
        _, response = range_response(payload, headers)
        return response

    monkeypatch.setattr(requests_transfer.time, "sleep", lambda _seconds: None)
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
            range_header, response = range_response(payload, headers)
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
    monkeypatch.setattr(requests_transfer.time, "sleep", lambda _seconds: None)

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
