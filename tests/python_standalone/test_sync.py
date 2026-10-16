"""Python Standalone 同步任务测试"""

import json
import logging
import shutil
import tarfile
import threading
import zipfile
from pathlib import Path

import pytest

from sd_webui_all_in_one.config import LOGGER_NAME
from sd_webui_all_in_one.python_standalone import sync
from sd_webui_all_in_one.python_standalone.types import SyncConfig, SyncPlan
from tests.python_standalone.helpers import HF, LINUX_312, MS, REPO_PATH_LINUX_312, WINDOWS_312, FakeRepoManager, make_asset


def _config(tmp_path, targets=(), **kwargs):
    return SyncConfig(targets=list(targets), output_dir=tmp_path / "out", work_dir=tmp_path / "work", **kwargs)


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

    tasks = sync.plan_tasks([("linux/amd64", make_asset(LINUX_312))], remote, config)

    assert len(tasks) == 1
    assert tasks[0].repo_path == REPO_PATH_LINUX_312
    assert tasks[0].action == action
    assert tasks[0].missing_targets == missing
    assert tasks[0].present_targets == [t for t, files in remote.items() if REPO_PATH_LINUX_312 in files]


def test_plan_tasks_uses_archive_format_and_path_in_repo(tmp_path):
    config = _config(tmp_path, archive_format=".tar.xz", path_in_repo="/runtime/py/")

    task = sync.plan_tasks([("linux/amd64", make_asset(LINUX_312))], {}, config)[0]

    assert task.repo_path == "runtime/py/linux/amd64/cpython-3.12.14+20260924-x86_64-unknown-linux-gnu-install_only.tar.xz"


def test_create_sync_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(sync, "fetch_release_assets", lambda **kwargs: ("20260924", [make_asset(LINUX_312), make_asset(WINDOWS_312)]))
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
    task = sync.plan_tasks([("linux/amd64", make_asset(LINUX_312, "sha"))], {HF: {REPO_PATH_LINUX_312}, MS: set()}, config)[0]
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
    task = sync.plan_tasks([("linux/amd64", make_asset(LINUX_312, "sha"))], {}, config)[0]

    result = sync.run_task(0, task, config, tmp_path / "work", None, {}, threading.Event())

    assert result.status == "success", result.error
    assert fake_download[0][1] is None


def test_run_task_continues_other_targets_when_upload_fails(tmp_path, monkeypatch):
    config = _config(tmp_path, [HF, MS])
    output = config.output_dir / REPO_PATH_LINUX_312
    output.parent.mkdir(parents=True)
    output.write_bytes(b"zip")
    monkeypatch.setattr(sync, "download_file", lambda **kwargs: pytest.fail("不应下载"))
    task = sync.plan_tasks([("linux/amd64", make_asset(LINUX_312))], {HF: set(), MS: set()}, config)[0]
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
    task = sync.plan_tasks([("linux/amd64", make_asset(LINUX_312))], {}, config)[0]

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
    tasks = sync.plan_tasks([("linux/amd64", make_asset(LINUX_312)), ("windows/amd64", make_asset(WINDOWS_312))], {HF: {windows}}, config)
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
    task = sync.plan_tasks([("linux/amd64", make_asset(LINUX_312))], {}, SyncConfig())[0]
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


# -- 临时输出模式 --------------------------------------------------------------
def test_plan_tasks_temp_output_ignores_local_archive(tmp_path):
    config = _config(tmp_path, [HF], temp_output=True)
    (config.output_dir / REPO_PATH_LINUX_312).parent.mkdir(parents=True)
    (config.output_dir / REPO_PATH_LINUX_312).write_bytes(b"zip")

    task = sync.plan_tasks([("linux/amd64", make_asset(LINUX_312))], {HF: set()}, config)[0]

    assert task.action == "build"


def test_validate_sync_config_temp_output_requires_target(tmp_path):
    with pytest.raises(ValueError):
        sync.validate_sync_config(_config(tmp_path, temp_output=True))
    sync.validate_sync_config(_config(tmp_path, [HF], temp_output=True))


def test_run_task_temp_output_deletes_archive_after_upload(tmp_path, fake_download):
    config = _config(tmp_path, [HF], temp_output=True)
    task = sync.plan_tasks([("linux/amd64", make_asset(LINUX_312))], {HF: set()}, config)[0]
    manager = FakeRepoManager()

    result = sync.run_task(0, task, config, tmp_path / "work", manager, {HF: threading.Lock()}, threading.Event())

    assert result.status == "success", result.error
    assert manager.uploads[0]["files"] == ["linux/amd64/" + task.archive_name]
    assert result.archive is None
    assert result.size is not None and result.size > 0
    assert result.sha256 is not None and len(result.sha256) == 64
    assert not config.output_dir.exists()
    assert not (tmp_path / "work" / task.slug).exists()

    plan = SyncPlan(release_tag="20260924", source_repo="r", targets=[HF], tasks=[task])
    resource = sync.build_sync_report(plan, [result], config)["resources"][0]
    assert (resource["size"], resource["sha256"]) == (result.size, result.sha256)
    assert "huggingface" in resource["urls"]


def test_run_task_temp_output_keeps_archive_with_keep_temp(tmp_path, fake_download):
    config = _config(tmp_path, [HF], temp_output=True, keep_temp=True)
    task = sync.plan_tasks([("linux/amd64", make_asset(LINUX_312))], {HF: set()}, config)[0]

    result = sync.run_task(0, task, config, tmp_path / "work", FakeRepoManager(), {HF: threading.Lock()}, threading.Event())

    assert result.archive == tmp_path / "work" / task.slug / "output" / task.archive_name
    assert result.archive.is_file()
