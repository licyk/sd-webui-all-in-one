"""requests 下载器 HTTP 请求头, 摘要头与镜像探测测试"""

import base64
import hashlib
import sys
import types

import pytest

from sd_webui_all_in_one.downloader.requests_downloader import http as requests_http
from sd_webui_all_in_one.downloader.requests_downloader import models as requests_models
from tests.downloader.helpers import FakeRangeResponse

pytestmark = pytest.mark.usefixtures("small_aria2_size_bounds")


def test_requests_downloader_default_headers_match_aria2_http_defaults():
    headers = requests_http._request_headers({"Range": "bytes=1-"})

    assert headers["User-Agent"]
    assert headers["Accept"] == "*/*"
    assert headers["Accept-Encoding"] == "identity"
    assert headers["Pragma"] == "no-cache"
    assert headers["Cache-Control"] == "no-cache"
    assert headers["Want-Digest"] == "SHA-512;q=1, SHA-256;q=1, SHA-1;q=1"
    assert headers["Range"] == "bytes=1-"


def test_requests_downloader_digest_prefers_sha512_and_rejects_conflicts():
    payload = b"digest algorithms"
    sha1 = base64.b64encode(hashlib.sha1(payload).digest()).decode("ascii")
    sha256 = base64.b64encode(hashlib.sha256(payload).digest()).decode("ascii")
    sha512 = base64.b64encode(hashlib.sha512(payload).digest()).decode("ascii")

    assert requests_http._digest_from_header(f"SHA-1={sha1}, SHA-256={sha256}, SHA-512=:{sha512}:") == (
        "sha512",
        hashlib.sha512(payload).hexdigest(),
    )

    conflicting = base64.b64encode(hashlib.sha256(b"different").digest()).decode("ascii")
    with pytest.raises(ValueError, match="冲突"):
        requests_http._digest_from_header(f"SHA-256={sha256}, sha256={conflicting}")


def test_requests_downloader_rejects_head_and_range_digest_conflict(monkeypatch):
    head_digest = base64.b64encode(hashlib.sha256(b"head").digest()).decode("ascii")
    range_digest = base64.b64encode(hashlib.sha256(b"range").digest()).decode("ascii")

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=200,
            headers={"Content-Length": "10", "Digest": f"SHA-256={head_digest}"},
        )

    def fake_get(url, stream=True, timeout=60, headers=None):
        return FakeRangeResponse(
            status_code=206,
            headers={"Content-Range": "bytes 0-0/10", "Digest": f"SHA-256={range_digest}"},
        )

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))

    with pytest.raises(ValueError, match="HEAD 冲突"):
        requests_http._probe_remote_file("https://example.test/model.bin")


def test_requests_downloader_isolates_mirror_with_conflicting_digest_header(monkeypatch):
    first = base64.b64encode(hashlib.sha256(b"first").digest()).decode("ascii")
    second = base64.b64encode(hashlib.sha256(b"second").digest()).decode("ascii")

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        digest = f"SHA-256={first}, SHA-256={second}" if "bad" in url else f"SHA-256={first}"
        return FakeRangeResponse(
            status_code=200,
            headers={"Content-Length": "10", "Accept-Ranges": "bytes", "Digest": digest},
        )

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head))

    result = requests_http._probe_remote_files(["https://bad.example.test/model.bin", "https://good.example.test/model.bin"])

    assert result.primary_url == "https://good.example.test/model.bin"
    assert result.range_urls == ["https://good.example.test/model.bin"]


def test_requests_downloader_probe_excludes_inconsistent_mirrors(monkeypatch):
    first_url = "https://first.example.test/model.bin"
    wrong_size_url = "https://wrong-size.example.test/model.bin"
    wrong_etag_url = "https://wrong-etag.example.test/model.bin"
    infos = {
        first_url: requests_models._RemoteFileInfo(total_size=8, supports_range=True, etag='"entity-a"'),
        wrong_size_url: requests_models._RemoteFileInfo(total_size=9, supports_range=True, etag='"entity-a"'),
        wrong_etag_url: requests_models._RemoteFileInfo(total_size=8, supports_range=True, etag='"entity-b"'),
    }
    monkeypatch.setattr(requests_http, "_probe_remote_file", lambda url, timeout=60: infos[url])

    result = requests_http._probe_remote_files([first_url, wrong_size_url, wrong_etag_url])

    assert result.primary_url == first_url
    assert result.range_urls == [first_url]
    assert result.resume_failure_count == 2
