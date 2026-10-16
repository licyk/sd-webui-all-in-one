"""requests 下载器已有文件复用, 缓存与条件请求测试"""

import base64
import hashlib
import sys
import types

import pytest

from sd_webui_all_in_one.downloader import requests_downloader
from tests.downloader.helpers import FakeRangeResponse, FakeRequestsResponse, FakeTqdm, range_response

pytestmark = pytest.mark.usefixtures("small_aria2_size_bounds")


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


def test_requests_downloader_checks_hash_for_existing_reuse(tmp_path):
    cached_file = tmp_path / "model.bin"
    cached_file.write_bytes(b"cached")

    with pytest.raises(ValueError, match="已有文件哈希"):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            hash_prefix=hashlib.sha256(b"different").hexdigest(),
            existing_file_policy="reuse",
            progress=False,
        )


def test_requests_downloader_verifies_existing_file_size_without_get(monkeypatch, tmp_path):
    payload = b"already complete"
    cached_file = tmp_path / "model.bin"
    cached_file.write_bytes(payload)

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(*args, **kwargs):
        raise AssertionError("verify 策略不应下载完整文件")

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        existing_file_policy="verify",
        progress=False,
    )

    assert result == cached_file.resolve()


def test_requests_downloader_verifies_existing_file_with_server_sha512(monkeypatch, tmp_path):
    payload = b"same length bad"
    cached_file = tmp_path / "model.bin"
    cached_file.write_bytes(b"different data!")
    digest = base64.b64encode(hashlib.sha512(payload).digest()).decode("ascii")

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={
                "Content-Length": str(len(payload)),
                "Accept-Ranges": "bytes",
                "Digest": f"SHA-512={digest}",
            },
        )

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head))

    with pytest.raises(ValueError, match="sha512"):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            existing_file_policy="verify",
            progress=False,
        )


def test_requests_downloader_resumes_from_partial_final_file(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    cached_file = tmp_path / "model.bin"
    cached_file.write_bytes(payload[:4])
    calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        calls.append(headers["Range"])
        return range_response(payload, headers)[1]

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        existing_file_policy="resume",
        progress=False,
        split=1,
        min_split_size=4,
        piece_length=4,
    )

    assert calls == ["bytes=4-"]
    assert result.read_bytes() == payload


def test_requests_downloader_rejects_existing_file_larger_than_remote(monkeypatch, tmp_path):
    (tmp_path / "model.bin").write_bytes(b"too large")

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": "4", "Accept-Ranges": "bytes"})

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head))

    with pytest.raises(IOError, match="大于远端文件"):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            existing_file_policy="resume",
            progress=False,
        )


def test_requests_downloader_overwrite_failure_preserves_existing_file(monkeypatch, tmp_path):
    cached_file = tmp_path / "model.bin"
    cached_file.write_bytes(b"original")

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": "8", "Accept-Ranges": "bytes"})

    def fake_get(*args, **kwargs):
        raise OSError("network failed")

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    with pytest.raises(IOError):
        requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            existing_file_policy="overwrite",
            progress=False,
            split=1,
            min_split_size=4,
            piece_length=4,
            max_tries=1,
        )

    assert cached_file.read_bytes() == b"original"


def test_requests_downloader_rename_preserves_existing_file(monkeypatch, tmp_path):
    payload = b"replacement"
    cached_file = tmp_path / "model.bin"
    cached_file.write_bytes(b"original")

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        return range_response(payload, headers)[1]

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        existing_file_policy="rename",
        progress=False,
        split=1,
        min_split_size=4,
        piece_length=4,
    )

    assert result == tmp_path / "model (1).bin"
    assert cached_file.read_bytes() == b"original"
    assert result.read_bytes() == payload


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
        range_header, response = range_response(payload, headers)
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


def test_requests_downloader_does_not_trust_full_size_temp_without_state(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    (tmp_path / "model.bin.tmp").write_bytes(b"\0" * len(payload))
    calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        calls.append(headers["Range"])
        _, response = range_response(payload, headers)
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=1,
        min_split_size=4,
        piece_length=4,
        continue_download=True,
    )

    assert calls == ["bytes=0-"]
    assert result.read_bytes() == payload
