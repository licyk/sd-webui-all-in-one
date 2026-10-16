"""requests 下载器断点续传状态测试"""

import base64
import hashlib
import json
import sys
import types

import pytest

from sd_webui_all_in_one.downloader import requests_downloader
from tests.downloader.helpers import FakeRangeResponse, FakeTqdm, range_response, request_state

pytestmark = pytest.mark.usefixtures("small_aria2_size_bounds")


def test_requests_downloader_resumes_completed_pieces_from_state(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:8] + b"\0" * 4)
    state_file.write_text(
        json.dumps(
            request_state(
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
        range_header, response = range_response(payload, headers)
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
            request_state(
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
        range_header, response = range_response(payload, headers)
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
        range_header, response = range_response(payload, headers)
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


def test_requests_downloader_resumes_state_when_scheduling_options_change(monkeypatch, tmp_path):
    payload = b"abcdefghijklmnop"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:4] + b"\0" * 12)
    state_file.write_text(
        json.dumps(
            request_state(
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
        range_header, response = range_response(payload, headers)
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
            request_state(
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
            request_state(
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
        _, response = range_response(payload, headers)
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


def test_requests_downloader_rejects_changed_resume_state_validator_but_ignores_url(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:8] + b"\0" * 4)
    state_file.write_text(
        json.dumps(
            request_state(
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
        range_header, response = range_response(payload, headers)
        range_calls.append(range_header)
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(RuntimeError, match="强 ETag 已变化"):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            progress=False,
            split=2,
            max_connection_per_server=1,
            min_split_size=4,
            piece_length=4,
            continue_download=True,
        )

    assert range_calls == []
    assert temp_file.exists()
    assert state_file.exists()


def test_requests_downloader_resumes_changed_mirror_when_strong_digest_matches(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    digest = hashlib.sha256(payload).hexdigest()
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:4] + b"\0" * 8)
    state_file.write_text(
        json.dumps(
            request_state(
                url="https://old.example.test/model.bin",
                total_size=len(payload),
                completed=[True, False, False],
                etag='"old"',
                digest_sha256=digest,
            )
        ),
        encoding="utf-8",
    )
    request_headers = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        encoded_digest = base64.b64encode(bytes.fromhex(digest)).decode("ascii")
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
                "ETag": '"new"',
                "Digest": f"SHA-256={encoded_digest}",
            },
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        request_headers.append(headers)
        return range_response(payload, headers)[1]

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://new.example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=1,
        min_split_size=4,
        piece_length=4,
    )

    assert result.read_bytes() == payload
    assert request_headers[0]["Range"] == "bytes=4-"
    assert request_headers[0]["If-Range"] == '"new"'


def test_requests_downloader_rejects_malformed_in_flight_piece(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:6] + b"\0" * 6)
    state = request_state(
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
            request_state(
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

    assert calls == ["bytes=0-0"]
    assert temp_file.exists()
    assert state_file.exists()


def test_requests_downloader_restarts_fresh_download_when_content_range_is_invalid(monkeypatch, tmp_path):
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

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=1,
        min_split_size=4,
        piece_length=4,
    )

    assert calls == ["bytes=0-", None]
    assert result.read_bytes() == payload
    assert not (tmp_path / "model.bin.tmp.state.json").exists()


def test_requests_downloader_restarts_resume_when_always_resume_is_disabled(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    temp_file = tmp_path / "model.bin.tmp"
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file.write_bytes(payload[:4] + b"\0" * 8)
    state_file.write_text(
        json.dumps(request_state(url="https://example.test/model.bin", total_size=len(payload), completed=[True, False, False])),
        encoding="utf-8",
    )
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
        min_split_size=4,
        piece_length=4,
        always_resume=False,
    )

    assert calls == ["bytes=0-0", None]
    assert result.read_bytes() == payload
    assert not temp_file.exists()
    assert not state_file.exists()


def test_requests_downloader_preserves_state_when_resume_range_is_ignored(monkeypatch, tmp_path):
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
