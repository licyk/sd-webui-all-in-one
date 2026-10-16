"""urllib 下载器测试"""

import hashlib
import sys
import types

from sd_webui_all_in_one.downloader import urllib_downloader
from tests.downloader.helpers import FakeTqdm


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
