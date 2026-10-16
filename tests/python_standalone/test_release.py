"""Python Standalone 发布资源解析测试"""

import json

from sd_webui_all_in_one.python_standalone import release
from tests.python_standalone.helpers import LINUX_312, WINDOWS_312, make_asset


# -- Release -----------------------------------------------------------------
def test_parse_asset_name():
    asset = make_asset(LINUX_312, "abc")
    assert asset.version == "3.12.14"
    assert asset.minor == "3.12"
    assert asset.build_date == "20260924"
    assert asset.build_type == "x86_64-unknown-linux-gnu-install_only"
    assert asset.sha256 == "abc"
    assert asset.version_tuple == (3, 12, 14)
    assert release.parse_asset_name("SHA256SUMS", "u") is None
    assert release.parse_asset_name("pypy-3.10.1+20260924-x86_64-unknown-linux-gnu-install_only.tar.gz", "u") is None


def test_select_assets_picks_highest_patch_and_exact_variant():
    assets = [
        make_asset("cpython-3.12.9+20260924-x86_64-unknown-linux-gnu-install_only.tar.gz"),
        make_asset(LINUX_312),
        make_asset("cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-freethreaded-install_only.tar.gz"),
        make_asset("cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"),
        make_asset("cpython-3.1.5+20260924-x86_64-unknown-linux-gnu-install_only.tar.gz"),
        make_asset(WINDOWS_312),
    ]
    platforms = {"linux/amd64": "x86_64-unknown-linux-gnu", "windows/amd64": "x86_64-pc-windows-msvc", "macos/aarch64": "aarch64-apple-darwin"}

    selected = release.select_assets(assets, ["3.12", "3.10"], platforms, "install_only")

    assert [(platform, asset.name) for platform, asset in selected] == [("linux/amd64", LINUX_312), ("windows/amd64", WINDOWS_312)]


def test_fetch_release_assets_uses_digest_then_sha256sums(monkeypatch):
    release_data = {
        "tag_name": "20260924",
        "assets": [
            {"name": LINUX_312, "browser_download_url": "u1", "size": 10, "digest": "sha256:aaa"},
            {"name": WINDOWS_312, "browser_download_url": "u2", "size": 20},
            {"name": "SHA256SUMS", "browser_download_url": "sums"},
        ],
    }
    requested = []

    def fake_get(url, token=None, accept=""):
        requested.append((url, token))
        if url == "sums":
            return f"bbb  {WINDOWS_312}\n".encode()
        return json.dumps(release_data).encode()

    monkeypatch.setattr(release, "github_get", fake_get)

    tag, assets = release.fetch_release_assets("20260924", source_repo="owner/repo", token="t", api_url="https://api.example/")

    assert tag == "20260924"
    assert [(a.name, a.sha256, a.size) for a in assets] == [(LINUX_312, "aaa", 10), (WINDOWS_312, "bbb", 20)]
    assert requested == [("https://api.example/repos/owner/repo/releases/tags/20260924", "t"), ("sums", "t")]


def test_list_releases(monkeypatch):
    data = [{"tag_name": "20260924", "name": "n", "published_at": "p", "prerelease": False, "assets": [1, 2], "html_url": "h"}]
    monkeypatch.setattr(release, "github_get", lambda url, token=None: json.dumps(data).encode())

    assert release.list_releases(limit=5) == [{"tag": "20260924", "name": "n", "published_at": "p", "prerelease": False, "assets": 2, "url": "h"}]
