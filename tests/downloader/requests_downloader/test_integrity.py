"""requests 下载器完整性校验测试"""

import base64
import hashlib
import sys
import types

import pytest

from sd_webui_all_in_one.downloader import requests_downloader
from tests.downloader.helpers import FakeRangeResponse, FakeRequestsResponse, FakeTqdm, range_response

pytestmark = pytest.mark.usefixtures("small_aria2_size_bounds")


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
        return range_response(payload, headers)[1]

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


def test_requests_downloader_validates_digest_returned_only_by_actual_get(monkeypatch, tmp_path):
    payload = b"actual get digest"
    digest = base64.b64encode(hashlib.sha512(payload).digest()).decode("ascii")
    calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload))})

    def fake_get(url, stream=True, timeout=60, headers=None):
        calls.append(headers.get("Range") if headers else None)
        if headers and "Range" in headers:
            return FakeRangeResponse(payload, status_code=200, headers={"Content-Length": str(len(payload))})
        return FakeRangeResponse(
            payload,
            status_code=200,
            headers={"Content-Length": str(len(payload)), "Digest": f"SHA-512={digest}"},
        )

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
    )

    assert calls == ["bytes=0-0", None]
    assert result.read_bytes() == payload


def test_requests_downloader_explicit_sha512_overrides_weaker_server_digest(monkeypatch, tmp_path):
    payload = b"explicit stronger hash"
    server_sha1 = base64.b64encode(hashlib.sha1(payload).digest()).decode("ascii")

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes", "Digest": f"SHA-1={server_sha1}"},
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        return range_response(payload, headers)[1]

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        hash_value=hashlib.sha512(payload).hexdigest(),
        hash_algorithm="sha512",
        progress=False,
        split=1,
        min_split_size=4,
        piece_length=4,
    )

    assert result.read_bytes() == payload


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


def test_requests_downloader_range_hash_mismatch_cleans_temp_files(monkeypatch, tmp_path):
    payload = b"wrong hash payload"

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        _, response = range_response(payload, headers)
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
