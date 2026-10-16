"""requests 下载器下载选项, 文件名, 超时与进度测试"""

import json
import sys
import threading
import types
from email.utils import parsedate_to_datetime

import pytest

from sd_webui_all_in_one.downloader import requests_downloader
from sd_webui_all_in_one.downloader.requests_downloader import api as requests_api
from sd_webui_all_in_one.downloader.requests_downloader import models as requests_models
from sd_webui_all_in_one.downloader.requests_downloader import transfer as requests_transfer
from tests.downloader.helpers import FakeRangeResponse, FakeTqdm, range_response

pytestmark = pytest.mark.usefixtures("small_aria2_size_bounds")


def test_requests_downloader_uses_separate_timeouts_and_emits_progress_when_display_disabled(monkeypatch, tmp_path):
    payload = b"abcdefgh"
    timeouts = []
    events = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        timeouts.append(("head", timeout))
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        timeouts.append(("get", timeout))
        return range_response(payload, headers)[1]

    monkeypatch.setattr(requests_models, "STREAM_CHUNK_SIZE", 4)
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        connect_timeout=11,
        read_timeout=22,
        progress_callback=events.append,
        split=1,
        min_split_size=8,
        piece_length=8,
    )

    assert result.read_bytes() == payload
    assert timeouts == [("head", (11, 22)), ("get", (11, 22))]
    assert events
    assert events[-1].completed_size == len(payload)
    assert events[-1].total_size == len(payload)
    assert events[-1].current_url == "https://example.test/model.bin"
    assert events[-1].active_connections == 1


def test_requests_downloader_cancel_saves_resumable_state(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    cancel_event = threading.Event()
    ranges = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        ranges.append(headers["Range"])
        return range_response(payload, headers)[1]

    def cancel_after_first_event(_event):
        cancel_event.set()

    monkeypatch.setattr(requests_models, "STREAM_CHUNK_SIZE", 4)
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(requests_models.DownloadCancelledError):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            progress=False,
            cancel_event=cancel_event,
            progress_callback=cancel_after_first_event,
            split=1,
            min_split_size=12,
            piece_length=12,
        )

    assert (tmp_path / "model.bin.tmp").exists()
    assert (tmp_path / "model.bin.tmp.state.json").exists()

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=1,
        min_split_size=12,
        piece_length=12,
    )

    assert ranges == ["bytes=0-", "bytes=4-"]
    assert result.read_bytes() == payload


def test_requests_downloader_low_speed_error_preserves_in_flight_progress(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    clock_value = 0.0

    def fake_monotonic():
        nonlocal clock_value
        clock_value += 2.0
        return clock_value

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        return range_response(payload, headers)[1]

    monkeypatch.setattr(requests_models, "STREAM_CHUNK_SIZE", 4)
    monkeypatch.setattr(requests_transfer.time, "monotonic", fake_monotonic)
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(requests_models.DownloadTransientError, match="预算已耗尽") as exc:
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            progress=False,
            split=1,
            min_split_size=12,
            piece_length=12,
            max_tries=1,
            lowest_speed_limit=1_000_000,
            lowest_speed_time=1,
        )

    assert isinstance(exc.value.__cause__, requests_models.DownloadLowSpeedError)
    state = json.loads((tmp_path / "model.bin.tmp.state.json").read_text(encoding="utf-8"))
    assert state["in_flight_pieces"][0]["completed_length"] == 4


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
        return range_response(payload, headers)[1]

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


@pytest.mark.parametrize(
    "file_name",
    ["../escape.bin", "/tmp/escape.bin", "nested/file.bin", r"C:\escape.bin", r"\\server\share\file.bin", "NUL.txt", "..", "bad\0name"],
)
def test_requests_downloader_rejects_unsafe_explicit_file_name(file_name, tmp_path):
    with pytest.raises(ValueError, match="下载文件名"):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            file_name=file_name,
            progress=False,
        )


def test_requests_downloader_accepts_unicode_and_space_file_name(monkeypatch, tmp_path):
    payload = b"safe"

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        return range_response(payload, headers)[1]

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        file_name="模型 文件.bin",
        progress=False,
        split=1,
        min_split_size=4,
        piece_length=4,
    )

    assert result.name == "模型 文件.bin"
    assert result.read_bytes() == payload


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
        return range_response(payload, headers)[1]

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
        return range_response(payload, headers)[1]

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
        return range_response(payload, headers)[1]

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


def test_requests_downloader_normalizes_options_with_aria2_bounds(monkeypatch):
    monkeypatch.setattr(requests_models, "ARIA2_SIZE_OPTION_MIN", 1024 * 1024)
    monkeypatch.setattr(requests_models, "ARIA2_SIZE_OPTION_MAX", 1024 * 1024 * 1024)

    options = requests_api._normalize_options(
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
        always_resume=False,
        max_resume_failure_tries=2,
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
    assert options.always_resume is False
    assert options.max_resume_failure_tries == 2

    with pytest.raises(ValueError, match="max_connection_per_server"):
        requests_api._normalize_options(
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
        requests_api._normalize_options(
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
        requests_api._normalize_options(
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
        requests_api._normalize_options(
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
        requests_api._normalize_options(
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
    with pytest.raises(ValueError, match="max_resume_failure_tries"):
        requests_api._normalize_options(
            split=1,
            max_connection_per_server=1,
            min_split_size=1024 * 1024,
            piece_length=1024 * 1024,
            allow_piece_length_change=False,
            max_tries=1,
            retry_wait=0,
            continue_download=False,
            conditional_get=False,
            remote_time=True,
            max_resume_failure_tries=-1,
        )
