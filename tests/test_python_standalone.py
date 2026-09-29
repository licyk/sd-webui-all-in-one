import argparse
import json
import logging
import shutil
import tarfile
import threading
import zipfile
from pathlib import Path

import pytest

from sd_webui_all_in_one.cli_manager import python_standalone_cli
from sd_webui_all_in_one.config import LOGGER_NAME
from sd_webui_all_in_one.python_standalone import release, resources, sync
from sd_webui_all_in_one.python_standalone.types import RepoTarget, SyncConfig, SyncPlan

LINUX_312 = "cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-install_only.tar.gz"
WINDOWS_312 = "cpython-3.12.14+20260924-x86_64-pc-windows-msvc-install_only.tar.gz"
REPO_PATH_LINUX_312 = "python/linux/amd64/cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-install_only.zip"
HF = RepoTarget("huggingface", "user/hf-repo")
MS = RepoTarget("modelscope", "user/ms-repo")


def _asset(name, sha256=None):
    asset = release.parse_asset_name(name, f"https://example.com/{name}", sha256=sha256)
    assert asset is not None
    return asset


def _config(tmp_path, targets=(), **kwargs):
    return SyncConfig(targets=list(targets), output_dir=tmp_path / "out", work_dir=tmp_path / "work", **kwargs)


# -- Release -----------------------------------------------------------------


def test_parse_asset_name():
    asset = _asset(LINUX_312, "abc")
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
        _asset("cpython-3.12.9+20260924-x86_64-unknown-linux-gnu-install_only.tar.gz"),
        _asset(LINUX_312),
        _asset("cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-freethreaded-install_only.tar.gz"),
        _asset("cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"),
        _asset("cpython-3.1.5+20260924-x86_64-unknown-linux-gnu-install_only.tar.gz"),
        _asset(WINDOWS_312),
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


def _resource(version, build_date, platform="linux/amd64", variant="install_only"):
    system, arch = platform.split("/")
    triple = {"linux/amd64": "x86_64-unknown-linux-gnu", "windows/amd64": "x86_64-pc-windows-msvc"}[platform]
    path = f"python/{platform}/cpython-{version}+{build_date}-{triple}-{variant}.zip"
    resource = resources.parse_resource_path(path)
    assert resource is not None
    return resource


def test_filter_resources_latest_and_filters():
    items = [
        _resource("3.12.12", "20260203"),
        _resource("3.12.14", "20260924"),
        _resource("3.11.16", "20260924"),
        _resource("3.12.14", "20260924", "windows/amd64"),
        _resource("3.12.14", "20260924", variant="install_only_stripped"),
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


class FakeRepoManager:
    def __init__(self, files=None):
        self.files = files or {}
        self.uploads = []

    def get_repo_files_metadata(self, api_type, repo_id, repo_type="model", revision=None):
        return self.files.get(api_type, [])

    def upload_files_to_repo(self, api_type, repo_id, upload_path, repo_type, path_in_repo, visibility, num_threads, revision):
        files = sorted(p.relative_to(upload_path).as_posix() for p in upload_path.rglob("*") if p.is_file())
        self.uploads.append({"api_type": api_type, "repo_id": repo_id, "path_in_repo": path_in_repo, "files": files, "visibility": visibility, "num_threads": num_threads})


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
    items = [_resource("3.12.14", "20260924")]
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


# -- 同步 --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("remote", "local_exists", "force", "action", "missing"),
    [
        ({HF: set(), MS: set()}, False, False, "build", [HF, MS]),
        ({HF: {REPO_PATH_LINUX_312}, MS: set()}, False, False, "build", [MS]),
        ({HF: {REPO_PATH_LINUX_312}, MS: {REPO_PATH_LINUX_312}}, False, False, "skip", []),
        ({HF: {REPO_PATH_LINUX_312}, MS: set()}, True, False, "upload-only", [MS]),
        ({HF: {REPO_PATH_LINUX_312}, MS: {REPO_PATH_LINUX_312}}, True, True, "build", [HF, MS]),
        ({}, False, False, "build", []),
        ({}, True, False, "skip", []),
        ({}, True, True, "build", []),
    ],
)
def test_plan_tasks(tmp_path, remote, local_exists, force, action, missing):
    config = _config(tmp_path, force=force)
    if local_exists:
        (config.output_dir / REPO_PATH_LINUX_312).parent.mkdir(parents=True)
        (config.output_dir / REPO_PATH_LINUX_312).write_bytes(b"zip")

    tasks = sync.plan_tasks([("linux/amd64", _asset(LINUX_312))], remote, config)

    assert len(tasks) == 1
    assert tasks[0].repo_path == REPO_PATH_LINUX_312
    assert tasks[0].action == action
    assert tasks[0].missing_targets == missing
    assert tasks[0].present_targets == [t for t, files in remote.items() if REPO_PATH_LINUX_312 in files]


def test_plan_tasks_uses_archive_format_and_path_in_repo(tmp_path):
    config = _config(tmp_path, archive_format=".tar.xz", path_in_repo="/runtime/py/")

    task = sync.plan_tasks([("linux/amd64", _asset(LINUX_312))], {}, config)[0]

    assert task.repo_path == "runtime/py/linux/amd64/cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-install_only.tar.xz"


def test_create_sync_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(sync, "fetch_release_assets", lambda **kwargs: ("20260924", [_asset(LINUX_312), _asset(WINDOWS_312)]))
    manager = FakeRepoManager({"huggingface": [{"path": REPO_PATH_LINUX_312}]})
    config = _config(tmp_path, [HF], versions=["3.12"], platforms={"linux/amd64": "x86_64-unknown-linux-gnu", "windows/amd64": "x86_64-pc-windows-msvc"})

    plan = sync.create_sync_plan(config, manager)

    assert plan.release_tag == "20260924"
    assert [t.action for t in plan.tasks] == ["skip", "build"]
    text = sync.render_sync_plan(plan)
    assert "HF" in text
    assert "build -> HF" in text
    assert "共 2 个任务: 构建 1, 仅上传 0, 跳过 1" in text


@pytest.mark.parametrize(
    "changes",
    [
        {"versions": []},
        {"platforms": {}},
        {"platforms": {"linux": "x"}},
        {"workers": 0},
        {"upload_threads": 0},
        {"targets": [HF, HF]},
        {"path_in_repo": "../x"},
    ],
)
def test_validate_sync_config_rejects_bad_values(tmp_path, changes):
    config = _config(tmp_path)
    for key, value in changes.items():
        setattr(config, key, value)
    with pytest.raises(ValueError):
        sync.validate_sync_config(config)


def _make_tarball(path: Path) -> Path:
    root = path / "src"
    (root / "python" / "bin").mkdir(parents=True)
    (root / "python" / "bin" / "python3.12").write_bytes(b"binary")
    (root / "python" / "lib").mkdir()
    (root / "python" / "lib" / "os.py").write_text("print('os')\n")
    tarball = path / LINUX_312
    with tarfile.open(tarball, "w:gz") as tar:
        tar.add(root / "python", arcname="python")
    return tarball


@pytest.fixture
def fake_download(tmp_path, monkeypatch):
    tarball = _make_tarball(tmp_path)
    calls = []

    def fake_download_file(url, path, save_name, **kwargs):
        calls.append((url, kwargs["hash_value"], kwargs["split"]))
        path.mkdir(parents=True, exist_ok=True)
        return Path(shutil.copy(tarball, path / save_name))

    monkeypatch.setattr(sync, "download_file", fake_download_file)
    return calls


def test_run_task_builds_archive_and_uploads_only_missing_targets(tmp_path, fake_download):
    config = _config(tmp_path, [HF, MS], public=True, upload_threads=3)
    task = sync.plan_tasks([("linux/amd64", _asset(LINUX_312, "sha"))], {HF: {REPO_PATH_LINUX_312}, MS: set()}, config)[0]
    manager = FakeRepoManager()

    result = sync.run_task(0, task, config, tmp_path / "work", manager, {HF: threading.Lock(), MS: threading.Lock()}, threading.Event())

    assert result.status == "success", result.error
    assert result.uploaded == [MS]
    assert fake_download == [(f"https://example.com/{LINUX_312}", "sha", 5)]
    output = config.output_dir / REPO_PATH_LINUX_312
    with zipfile.ZipFile(output) as zf:
        assert sorted(zf.namelist()) == ["python/bin/python3.12", "python/lib/os.py"]
    assert manager.uploads == [{"api_type": "modelscope", "repo_id": "user/ms-repo", "path_in_repo": "python", "files": ["linux/amd64/" + output.name], "visibility": True, "num_threads": 3}]
    assert not (tmp_path / "work" / task.slug).exists()


def test_run_task_skips_hash_check_when_disabled(tmp_path, fake_download):
    config = _config(tmp_path, verify_hash=False)
    task = sync.plan_tasks([("linux/amd64", _asset(LINUX_312, "sha"))], {}, config)[0]

    result = sync.run_task(0, task, config, tmp_path / "work", None, {}, threading.Event())

    assert result.status == "success", result.error
    assert fake_download[0][1] is None


def test_run_task_continues_other_targets_when_upload_fails(tmp_path, monkeypatch):
    config = _config(tmp_path, [HF, MS])
    output = config.output_dir / REPO_PATH_LINUX_312
    output.parent.mkdir(parents=True)
    output.write_bytes(b"zip")
    monkeypatch.setattr(sync, "download_file", lambda **kwargs: pytest.fail("不应下载"))
    task = sync.plan_tasks([("linux/amd64", _asset(LINUX_312))], {HF: set(), MS: set()}, config)[0]
    assert task.action == "upload-only"

    class FlakyRepoManager(FakeRepoManager):
        def upload_files_to_repo(self, api_type, **kwargs):
            if api_type == "huggingface":
                raise RuntimeError("hf down")
            super().upload_files_to_repo(api_type, **kwargs)

    manager = FlakyRepoManager()
    result = sync.run_task(0, task, config, tmp_path / "work", manager, {HF: threading.Lock(), MS: threading.Lock()}, threading.Event())

    assert result.status == "failed"
    assert result.uploaded == [MS]
    assert "hf down" in (result.error or "")
    assert [u["api_type"] for u in manager.uploads] == ["modelscope"]


def test_run_task_reports_failure_and_cancel(tmp_path, monkeypatch):
    def failing_download(**kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(sync, "download_file", failing_download)
    config = _config(tmp_path)
    task = sync.plan_tasks([("linux/amd64", _asset(LINUX_312))], {}, config)[0]

    result = sync.run_task(0, task, config, tmp_path / "work", None, {}, threading.Event())
    assert (result.status, result.error) == ("failed", "network down")

    cancel = threading.Event()
    cancel.set()
    result = sync.run_task(0, task, config, tmp_path / "work", None, {}, cancel)
    assert result.status == "cancelled"
    assert not (tmp_path / "work" / task.slug).exists()


def test_run_sync_and_report(tmp_path, fake_download, monkeypatch):
    monkeypatch.delenv("HF_ENDPOINT", raising=False)
    config = _config(tmp_path, [HF], workers=2)
    windows = "python/windows/amd64/cpython-3.12.14+20260924-x86_64-pc-windows-msvc-install_only.zip"
    tasks = sync.plan_tasks([("linux/amd64", _asset(LINUX_312)), ("windows/amd64", _asset(WINDOWS_312))], {HF: {windows}}, config)
    plan = SyncPlan(release_tag="20260924", source_repo="owner/repo", targets=[HF], tasks=tasks)
    manager = FakeRepoManager()

    results = sync.run_sync(plan, config, manager, color=False)

    assert [(r.task.platform, r.status) for r in results] == [("linux/amd64", "success"), ("windows/amd64", "skipped")]
    assert sync.sync_exit_code(results) == 0
    report = sync.build_sync_report(plan, results, config)
    assert report["summary"] == {"total": 2, "success": 1, "failed": 0, "skipped": 1, "cancelled": 0}
    linux, win = report["resources"]
    assert linux["uploaded_to"] == ["huggingface"]
    assert linux["urls"] == {"huggingface": f"https://huggingface.co/user/hf-repo/resolve/main/{REPO_PATH_LINUX_312}"}
    assert linux["size"] == (config.output_dir / REPO_PATH_LINUX_312).stat().st_size
    assert linux["sha256"] is not None
    assert win["status"] == "skipped"
    assert win["urls"] == {"huggingface": f"https://huggingface.co/user/hf-repo/resolve/main/{windows}"}
    assert win["size"] is None
    markdown = sync.render_sync_report_markdown(report)
    assert "Python Standalone 同步报告 (20260924)" in markdown
    assert f"[HuggingFace](https://huggingface.co/user/hf-repo/resolve/main/{REPO_PATH_LINUX_312})" in markdown
    json.dumps(report)


def test_sync_exit_code():
    task = sync.plan_tasks([("linux/amd64", _asset(LINUX_312))], {}, SyncConfig())[0]
    assert sync.sync_exit_code([sync.SyncTaskResult(task=task, status="failed")]) == 1
    assert sync.sync_exit_code([sync.SyncTaskResult(task=task, status="cancelled")]) == 130
    assert sync.sync_exit_code([sync.SyncTaskResult(task=task, status="skipped")]) == 0


def test_task_log_tags_prefixes_and_restores():
    target = logging.getLogger(LOGGER_NAME)
    original = [h.formatter for h in target.handlers]
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "hello\nworld", None, None)
    out = []

    def worker():
        token = sync.set_log_tag("3.12 linux/amd64", 0)
        out.append(target.handlers[0].format(record))
        sync._log_tag.reset(token)

    with sync.task_log_tags(color=False, tag_width=18):
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        untagged = target.handlers[0].format(record)

    assert out[0].splitlines()[0].startswith("3.12 linux/amd64   │ ")
    assert out[0].splitlines()[1].startswith("3.12 linux/amd64   │ ")
    assert "│" not in untagged
    assert [h.formatter for h in target.handlers] == original


# -- 命令行 ------------------------------------------------------------------


def _parse(argv):
    parser = argparse.ArgumentParser()
    python_standalone_cli.register_python_standalone(parser.add_subparsers())
    return parser.parse_args(argv)


def test_parse_platform_map_and_select_platforms():
    mapping = python_standalone_cli.parse_platform_map(["linux/musl=x86_64-unknown-linux-musl"])
    assert mapping["linux/musl"] == "x86_64-unknown-linux-musl"
    assert python_standalone_cli.select_platforms(mapping, ["linux/musl"]) == {"linux/musl": "x86_64-unknown-linux-musl"}
    with pytest.raises(ValueError):
        python_standalone_cli.parse_platform_map(["linux/musl"])
    with pytest.raises(ValueError):
        python_standalone_cli.select_platforms(mapping, ["linux/riscv64"])


def test_sync_cli_builds_config_and_writes_reports(tmp_path, monkeypatch):
    captured = {}

    def fake_create_sync_plan(config, manager):
        captured["config"] = config
        return SyncPlan(release_tag="20260901", source_repo=config.source_repo, targets=config.targets, tasks=[])

    monkeypatch.setattr(python_standalone_cli, "create_repo_manager", lambda hf_token, ms_token: object())
    monkeypatch.setattr(python_standalone_cli, "create_sync_plan", fake_create_sync_plan)
    args = _parse(
        [
            "python-standalone",
            "sync",
            "--release-tag",
            "20260901",
            "--versions",
            "3.11, 3.12",
            "--platforms",
            "linux/amd64",
            "--archive-format",
            ".tar.gz",
            "--no-ms",
            "--hf-repo-id",
            "me/repo",
            "--hf-repo-type",
            "dataset",
            "--report-json",
            str(tmp_path / "r.json"),
            "--report-markdown",
            str(tmp_path / "r.md"),
        ]
    )

    args.func(args)

    config = captured["config"]
    assert config.release_tag == "20260901"
    assert config.versions == ["3.11", "3.12"]
    assert config.platforms == {"linux/amd64": "x86_64-unknown-linux-gnu"}
    assert config.archive_format == ".tar.gz"
    assert config.targets == [RepoTarget("huggingface", "me/repo", "dataset")]
    assert json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))["release_tag"] == "20260901"
    assert "同步报告 (20260901)" in (tmp_path / "r.md").read_text(encoding="utf-8")


def test_sync_cli_dry_run_and_failure_exit(tmp_path, monkeypatch):
    task = sync.plan_tasks([("linux/amd64", _asset(LINUX_312))], {}, SyncConfig())[0]
    plan = SyncPlan(release_tag="t", source_repo="r", targets=[], tasks=[task])
    monkeypatch.setattr(python_standalone_cli, "create_sync_plan", lambda config, manager: plan)
    monkeypatch.setattr(python_standalone_cli, "run_sync", lambda *args, **kwargs: [sync.SyncTaskResult(task=task, status="failed", error="x")])

    args = _parse(["python-standalone", "sync", "--no-upload", "--dry-run"])
    args.func(args)

    args = _parse(["python-standalone", "sync", "--no-upload"])
    with pytest.raises(SystemExit) as exc:
        args.func(args)
    assert exc.value.code == 1


def test_list_cli_outputs_latest_json(tmp_path, monkeypatch):
    items = [_resource("3.12.12", "20260203"), _resource("3.12.14", "20260924")]
    captured = {}

    def fake_collect(manager, targets, path_in_repo, revision, platforms):
        captured["targets"] = targets
        return items

    monkeypatch.setattr(python_standalone_cli, "create_repo_manager", lambda hf_token, ms_token: object())
    monkeypatch.setattr(python_standalone_cli, "collect_resources", fake_collect)
    monkeypatch.setattr(python_standalone_cli, "silence_logger_output", lambda: None)
    output = tmp_path / "list.json"

    args = _parse(["python-standalone", "list", "--no-hf", "--format", "json", "--output", str(output)])
    args.func(args)

    data = json.loads(output.read_text(encoding="utf-8"))
    assert captured["targets"] == [RepoTarget("modelscope", "licyks/sd-webui-all-in-one")]
    assert data["latest_only"] is True
    assert [r["version"] for r in data["resources"]] == ["3.12.14"]

    args = _parse(["python-standalone", "list", "--all", "--format", "markdown", "--output", str(output)])
    args.func(args)
    assert "3.12.12" in output.read_text(encoding="utf-8")


def test_list_cli_requires_a_repo():
    args = _parse(["python-standalone", "list", "--no-hf", "--no-ms"])
    with pytest.raises(ValueError):
        args.func(args)
