"""Python Standalone 资源路径与列表测试"""

import pytest

from sd_webui_all_in_one.python_standalone import resources
from sd_webui_all_in_one.python_standalone.types import RepoTarget
from tests.python_standalone.helpers import HF, MS, REPO_PATH_LINUX_312, FakeRepoManager, make_resource


# -- 资源解析与查询 -------------------------------------------------------------
@pytest.mark.parametrize(
    ("target", "revision", "expected"),
    [
        (RepoTarget("huggingface", "a/b"), None, "https://huggingface.co/a/b/resolve/main/python/x+1.zip"),
        (RepoTarget("huggingface", "a/b", "dataset"), "dev", "https://huggingface.co/datasets/a/b/resolve/dev/python/x+1.zip"),
        (RepoTarget("modelscope", "a/b"), None, "https://modelscope.cn/models/a/b/resolve/master/python/x+1.zip"),
        (RepoTarget("modelscope", "a/b", "dataset"), None, "https://modelscope.cn/datasets/a/b/resolve/master/python/x+1.zip"),
    ],
)
def test_build_download_url(monkeypatch, target, revision, expected):
    monkeypatch.delenv("HF_ENDPOINT", raising=False)
    assert resources.build_download_url(target, "python/x+1.zip", revision) == expected


def test_build_download_url_respects_hf_endpoint(monkeypatch):
    monkeypatch.setenv("HF_ENDPOINT", "https://hf-mirror.com/")
    assert resources.build_download_url(HF, "a.zip") == "https://hf-mirror.com/user/hf-repo/resolve/main/a.zip"


def test_parse_resource_path():
    resource = resources.parse_resource_path(REPO_PATH_LINUX_312)

    assert resource is not None
    assert resource["platform"] == "linux"
    assert resource["arch"] == "amd64"
    assert resource["triple"] == "x86_64-unknown-linux-gnu"
    assert resource["variant"] == "install_only"
    assert resource["version"] == "3.12.14"
    assert resource["archive_format"] == ".zip"


@pytest.mark.parametrize(
    ("path", "path_in_repo", "platforms", "triple", "variant", "archive_format"),
    [
        ("py/linux/amd64/cpython-3.13.1+20260924-x86_64-unknown-linux-gnu-freethreaded-install_only.tar.gz", "py", None, "x86_64-unknown-linux-gnu", "freethreaded-install_only", ".tar.gz"),
        ("linux/musl/cpython-3.13.1+20260924-x86_64-unknown-linux-musl-install_only.7z", "", {"linux/musl": "x86_64-unknown-linux-musl"}, "x86_64-unknown-linux-musl", "install_only", ".7z"),
        ("python/linux/musl/cpython-3.13.1+20260924-x86_64-unknown-linux-musl-install_only.zip", "python", None, None, "x86_64-unknown-linux-musl-install_only", ".zip"),
    ],
)
def test_parse_resource_path_variants(path, path_in_repo, platforms, triple, variant, archive_format):
    resource = resources.parse_resource_path(path, path_in_repo, platforms)

    assert resource is not None
    assert (resource["triple"], resource["variant"], resource["archive_format"]) == (triple, variant, archive_format)


@pytest.mark.parametrize(
    "path",
    [
        "portable/sd_webui_cuda-licyk-windows-v1.0.0.7z",
        "python/linux/amd64/readme.md",
        "python/linux/cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-install_only.zip",
        "other/linux/amd64/cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-install_only.zip",
    ],
)
def test_parse_resource_path_rejects_other_files(path):
    assert resources.parse_resource_path(path) is None


def test_normalize_path_in_repo_rejects_parent():
    assert resources.normalize_path_in_repo("/a//b/") == "a/b"
    with pytest.raises(ValueError):
        resources.normalize_path_in_repo("a/../b")


def test_filter_resources_latest_and_filters():
    items = [
        make_resource("3.12.12", "20260203"),
        make_resource("3.12.14", "20260924"),
        make_resource("3.11.16", "20260924"),
        make_resource("3.12.14", "20260924", "windows/amd64"),
        make_resource("3.12.14", "20260924", variant="install_only_stripped"),
    ]

    latest = resources.filter_resources(items)
    assert [(r["platform"], r["version"], r["variant"]) for r in latest] == [
        ("windows", "3.12.14", "install_only"),
        ("linux", "3.12.14", "install_only"),
        ("linux", "3.12.14", "install_only_stripped"),
        ("linux", "3.11.16", "install_only"),
    ]
    assert len(resources.filter_resources(items, latest_only=False)) == 5
    assert [r["version"] for r in resources.filter_resources(items, versions=["3.12"], platforms=["linux"], variants=["install_only"], latest_only=False)] == ["3.12.14", "3.12.12"]
    assert [r["build_date"] for r in resources.filter_resources(items, build_date="20260203")] == ["20260203"]
    assert resources.filter_resources(items, archive_formats=[".7z"]) == []


def test_collect_resources_merges_sources(monkeypatch):
    monkeypatch.delenv("HF_ENDPOINT", raising=False)
    manager = FakeRepoManager(
        {
            "huggingface": [{"path": REPO_PATH_LINUX_312, "size": 5, "sha256": "s"}, {"path": "README.md"}],
            "modelscope": [{"path": REPO_PATH_LINUX_312, "size": 5, "sha256": None}],
        }
    )

    items = resources.collect_resources(manager, [HF, MS])

    assert len(items) == 1
    assert items[0]["size"] == 5
    assert items[0]["sha256"] == "s"
    assert set(items[0]["urls"]) == {"huggingface", "modelscope"}


def test_render_resources():
    items = [make_resource("3.12.14", "20260924")]
    items[0]["urls"] = {"huggingface": "https://h/x.zip"}
    items[0]["size"] = 1024 * 1024 * 3

    assert "3.12.14  linux/amd64" in resources.render_resources_table(items)
    markdown = resources.render_resources_markdown(items)
    assert "### linux/amd64" in markdown
    assert "[HuggingFace](https://h/x.zip)" in markdown
    assert "3.0 MB" in markdown
    data = resources.build_resource_list_data(items, [HF], latest_only=True)
    assert data["sources"] == ["HuggingFace:user/hf-repo"]
    assert data["resources"] == items
