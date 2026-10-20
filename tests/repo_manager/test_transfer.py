"""仓库管理器上传, 下载与镜像同步测试"""

import hashlib
import sys
import types
from pathlib import Path

import pytest

from sd_webui_all_in_one import repo_manager as repo_module
from sd_webui_all_in_one.custom_exceptions import AggregateError
from tests.repo_manager.helpers import repo_manager_with_apis


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_repo_manager_upload_skips_matching_hash_and_aggregates_failures(monkeypatch, tmp_path):
    monkeypatch.setattr(repo_module, "RETRY_TIMES", 1)
    upload_root = tmp_path / "upload"
    upload_root.mkdir()
    (upload_root / "existing.txt").write_text("old", encoding="utf-8")
    (upload_root / "changed.txt").write_text("changed-local", encoding="utf-8")
    (upload_root / "new.txt").write_text("new", encoding="utf-8")
    nested_dir = upload_root / "nested"
    nested_dir.mkdir()
    (nested_dir / "keep.txt").write_text("nested", encoding="utf-8")

    manager = repo_manager_with_apis()
    uploaded = []
    list_calls = []
    upload_log_indexes = []

    def fake_log_info(message, *args, **_kwargs):
        if message == "[%s/%s] 上传 %s 到 %s (类型: %s) 仓库中":
            upload_log_indexes.append(args[:2])

    monkeypatch.setattr(repo_module.logger, "info", fake_log_info)

    class FakeHfApi:
        def upload_file(self, **kwargs):
            uploaded.append(kwargs)

    manager.hf_api = FakeHfApi()
    manager.get_repo_files_metadata = lambda **kwargs: (
        list_calls.append(kwargs)
        or [
            {"path": "remote/existing.txt", "type": "file", "sha256": _sha256("old")},
            {"path": "remote/changed.txt", "type": "file", "sha256": _sha256("changed-remote")},
            {"path": "remote/nested/keep.txt", "type": "file", "sha256": _sha256("nested")},
        ]
    )

    manager.upload_files_to_huggingface("owner/repo", upload_root, path_in_repo="/remote/", num_threads=1, revision="upload-branch")

    assert list_calls[0]["revision"] == "upload-branch"
    assert {kwargs["path_in_repo"] for kwargs in uploaded} == {"remote/changed.txt", "remote/new.txt"}
    assert {kwargs["revision"] for kwargs in uploaded} == {"upload-branch"}
    assert upload_log_indexes == [(1, 2), (2, 2)]

    ms_uploaded = []
    upload_log_indexes.clear()

    class FakeMsApi:
        def upload_file(self, **kwargs):
            ms_uploaded.append(kwargs)

    manager.ms_api = FakeMsApi()
    manager.get_repo_files_metadata = lambda **_kwargs: [
        {"path": "ms-root/existing.txt", "type": "file", "sha256": _sha256("old")},
        {"path": "ms-root/changed.txt", "type": "file", "sha256": _sha256("changed-remote")},
        {"path": "ms-root/nested/keep.txt", "type": "file", "sha256": _sha256("nested")},
    ]

    manager.upload_files_to_modelscope("owner/repo", upload_root, path_in_repo="ms-root", num_threads=1, revision="ms-branch")

    assert {kwargs["path_in_repo"] for kwargs in ms_uploaded} == {"ms-root/changed.txt", "ms-root/new.txt"}
    assert {kwargs["revision"] for kwargs in ms_uploaded} == {"ms-branch"}
    assert upload_log_indexes == [(1, 2), (2, 2)]

    class FailingHfApi:
        def upload_file(self, **_kwargs):
            raise ValueError("boom")

    manager.hf_api = FailingHfApi()
    manager.get_repo_files_metadata = lambda **_kwargs: []
    upload_log_indexes.clear()

    with pytest.raises(AggregateError) as exc:
        manager.upload_files_to_huggingface("owner/repo", upload_root, num_threads=1)

    assert len(exc.value.exceptions) == 4
    assert upload_log_indexes == [(1, 4), (2, 4), (3, 4), (4, 4)]


def test_repo_manager_upload_rejects_parent_path_in_repo(tmp_path):
    upload_root = tmp_path / "upload"
    upload_root.mkdir()

    manager = repo_manager_with_apis()

    with pytest.raises(ValueError, match="仓库路径不能包含"):
        manager.upload_files_to_repo(
            api_type="huggingface",
            repo_id="owner/repo",
            upload_path=upload_root,
            path_in_repo="../bad",
        )


def test_repo_manager_download_filters_huggingface_and_modelscope(monkeypatch, tmp_path):
    captured = []

    class FakeDownloader:
        def __init__(self, download_func, download_kwargs_list):
            captured.append((download_func, download_kwargs_list))

        def start(self, num_threads):
            captured.append(("start", num_threads))

    monkeypatch.setattr(repo_module, "MultiThreadDownloader", FakeDownloader)
    monkeypatch.setitem(sys.modules, "huggingface_hub", types.SimpleNamespace(hf_hub_download="hf-download"))
    monkeypatch.setitem(sys.modules, "modelscope", types.SimpleNamespace(snapshot_download="ms-download"))

    manager = repo_manager_with_apis()
    manager.hf_api = types.SimpleNamespace(hf_hub_download="hf-download")
    manager.get_repo_file = lambda **_kwargs: ["aa/a.txt", "bb/b.txt", "aa/nested/c.txt"]

    manager.download_files_from_huggingface(
        "owner/repo",
        tmp_path,
        folder="aa/",
        num_threads=3,
        revision="hf-rev",
    )
    assert captured[0] == (
        "hf-download",
        [
            {
                "repo_id": "owner/repo",
                "repo_type": "model",
                "local_dir": tmp_path,
                "filename": "aa/a.txt",
                "revision": "hf-rev",
            },
            {
                "repo_id": "owner/repo",
                "repo_type": "model",
                "local_dir": tmp_path,
                "filename": "aa/nested/c.txt",
                "revision": "hf-rev",
            },
        ],
    )
    assert captured[1] == ("start", 3)

    captured.clear()
    manager.download_files_from_modelscope(
        "owner/repo",
        tmp_path,
        repo_type="dataset",
        folder="bb/",
        num_threads=2,
        revision="ms-rev",
    )
    assert captured[0] == (
        "ms-download",
        [
            {
                "repo_id": "owner/repo",
                "repo_type": "dataset",
                "local_dir": tmp_path,
                "allow_patterns": "bb/b.txt",
                "revision": "ms-rev",
            }
        ],
    )
    assert captured[1] == ("start", 2)


def test_repo_manager_mirror_repo_files_uses_metadata_and_revision(monkeypatch):
    manager = repo_manager_with_apis()
    check_calls = []
    metadata_calls = []
    download_calls = []
    uploaded = []
    mirror_log_indexes = []

    def fake_log_info(message, *args, **_kwargs):
        if message == "[%s/%s] 镜像 %s":
            mirror_log_indexes.append(args[:2])

    monkeypatch.setattr(repo_module.logger, "info", fake_log_info)

    def fake_check_repo(**kwargs):
        check_calls.append(kwargs)
        return True

    def fake_get_repo_files_metadata(**kwargs):
        metadata_calls.append(kwargs)
        if kwargs["api_type"] == "huggingface":
            return [
                {"path": "same.bin", "type": "file", "sha256": _sha256("same")},
                {"path": "changed.bin", "type": "file", "sha256": _sha256("changed-local")},
                {"path": "missing.bin", "type": "file", "sha256": _sha256("missing")},
                {"path": "folder", "type": "directory", "sha256": None},
            ]
        return [
            {"path": "same.bin", "type": "file", "sha256": _sha256("same")},
            {"path": "changed.bin", "type": "file", "sha256": _sha256("changed-remote")},
        ]

    def fake_hf_hub_download(**kwargs):
        download_calls.append(kwargs)
        file_path = Path(kwargs["local_dir"]) / kwargs["filename"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(kwargs["filename"], encoding="utf-8")
        return file_path

    class FakeMsApi:
        def upload_file(self, **kwargs):
            assert kwargs["path_or_fileobj"].exists()
            uploaded.append(kwargs)

    manager.check_repo = fake_check_repo
    manager.get_repo_files_metadata = fake_get_repo_files_metadata
    manager.hf_api = types.SimpleNamespace(hf_hub_download=fake_hf_hub_download)
    manager.ms_api = FakeMsApi()
    monkeypatch.setitem(sys.modules, "huggingface_hub", types.SimpleNamespace(hf_hub_download=fake_hf_hub_download))

    manager.mirror_repo_files(
        src_api_type="huggingface",
        dst_api_type="modelscope",
        src_repo_id="owner/src",
        dst_repo_id="owner/dst",
        src_repo_type="model",
        dst_repo_type="dataset",
        visibility=True,
        revision="mirror-rev",
        num_threads=1,
        retry_times=1,
    )

    assert check_calls == [
        {
            "api_type": "modelscope",
            "repo_id": "owner/dst",
            "repo_type": "dataset",
            "visibility": True,
        }
    ]
    assert metadata_calls == [
        {
            "api_type": "huggingface",
            "repo_id": "owner/src",
            "repo_type": "model",
            "revision": "mirror-rev",
        },
        {
            "api_type": "modelscope",
            "repo_id": "owner/dst",
            "repo_type": "dataset",
            "revision": "mirror-rev",
        },
    ]
    assert {kwargs["filename"] for kwargs in download_calls} == {"changed.bin", "missing.bin"}
    assert {kwargs["revision"] for kwargs in download_calls} == {"mirror-rev"}
    assert {kwargs["path_in_repo"] for kwargs in uploaded} == {"changed.bin", "missing.bin"}
    assert {kwargs["repo_type"] for kwargs in uploaded} == {"dataset"}
    assert {kwargs["revision"] for kwargs in uploaded} == {"mirror-rev"}
    assert {kwargs["token"] for kwargs in uploaded} == {"ms-token"}
    assert mirror_log_indexes == [(1, 2), (2, 2)]


def test_repo_manager_mirror_repo_files_can_use_fast_download(monkeypatch):
    manager = repo_manager_with_apis()
    download_url_calls = []
    download_calls = []
    uploaded = []

    class FakeHfApi:
        def upload_file(self, **kwargs):
            assert kwargs["path_or_fileobj"].exists()
            uploaded.append(kwargs)

    manager.hf_api = FakeHfApi()
    manager.check_repo = lambda **_kwargs: True
    manager.get_repo_files_metadata = lambda **kwargs: [{"path": "nested/file.bin", "type": "file", "sha256": _sha256("src")}] if kwargs["api_type"] == "modelscope" else []

    def fake_get_repo_file_download_url(**kwargs):
        download_url_calls.append(kwargs)
        return "https://example.test/nested/file.bin"

    def fake_download_file(**kwargs):
        download_calls.append(kwargs)
        file_path = Path(kwargs["path"]) / kwargs["save_name"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("downloaded", encoding="utf-8")
        return file_path

    manager.get_repo_file_download_url = fake_get_repo_file_download_url
    monkeypatch.setattr(repo_module, "download_file", fake_download_file)

    manager.mirror_repo_files(
        src_api_type="modelscope",
        dst_api_type="huggingface",
        src_repo_id="owner/src",
        dst_repo_id="owner/dst",
        revision="fast-rev",
        use_fast_download=True,
        download_tool="aria2",
        download_split=16,
        download_progress=False,
        num_threads=1,
        retry_times=1,
    )

    assert download_url_calls == [
        {
            "api_type": "modelscope",
            "repo_id": "owner/src",
            "file_path": "nested/file.bin",
            "repo_type": "model",
            "revision": "fast-rev",
        }
    ]
    assert len(download_calls) == 1
    assert download_calls[0]["url"] == "https://example.test/nested/file.bin"
    assert download_calls[0]["path"].name == "nested"
    assert download_calls[0]["save_name"] == "file.bin"
    assert download_calls[0]["tool"] == "aria2"
    assert download_calls[0]["split"] == 16
    assert download_calls[0]["progress"] is False
    assert uploaded[0]["path_in_repo"] == "nested/file.bin"
    assert uploaded[0]["revision"] == "fast-rev"


def test_plan_mirror_group_respects_group_size_budget_and_unknown_sizes():
    pending = [("a.bin", 40), ("b.bin", 70), ("c.bin", 20), ("d.bin", 10), ("e.bin", 5)]

    group, too_large = repo_module._plan_mirror_group(pending, group_size=3, budget=100)
    assert group == [("a.bin", 40), ("c.bin", 20), ("d.bin", 10)]
    assert too_large == []

    group, too_large = repo_module._plan_mirror_group([("huge.bin", 101), ("a.bin", 40)], group_size=3, budget=100)
    assert group == [("a.bin", 40)]
    assert too_large == [("huge.bin", 101)]

    group, too_large = repo_module._plan_mirror_group([("unknown.bin", None), ("a.bin", 40)], group_size=3, budget=100)
    assert group == [("unknown.bin", None)]

    group, too_large = repo_module._plan_mirror_group([("a.bin", 40), ("unknown.bin", None), ("b.bin", 10)], group_size=3, budget=100)
    assert group == [("a.bin", 40), ("b.bin", 10)]


def _grouped_mirror_manager(monkeypatch, tmp_path, src_files, free_space, fail_files=()):
    manager = repo_manager_with_apis()
    commits = []
    download_calls = []
    group_dirs = []

    def fake_hf_hub_download(**kwargs):
        download_calls.append(kwargs["filename"])
        if kwargs["filename"] in fail_files:
            raise OSError("No space left on device")
        local_dir = Path(kwargs["local_dir"])
        group_dirs.append(local_dir.parents[1])
        file_path = local_dir / kwargs["filename"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(kwargs["filename"], encoding="utf-8")
        # 模拟 huggingface_hub 在 local_dir 中留下的缓存目录, 不应进入提交
        (local_dir / ".cache" / "huggingface").mkdir(parents=True, exist_ok=True)
        return file_path

    class FakeMsApi:
        def upload_folder(self, **kwargs):
            folder = Path(kwargs["folder_path"])
            files = sorted(path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file())
            commits.append({**kwargs, "files": files})

    manager.check_repo = lambda **_kwargs: True
    manager.get_repo_files_metadata = lambda **kwargs: src_files if kwargs["api_type"] == "huggingface" else []
    manager.hf_api = types.SimpleNamespace(hf_hub_download=fake_hf_hub_download)
    manager.ms_api = FakeMsApi()
    monkeypatch.setattr(repo_module, "_get_free_disk_space", lambda _path: free_space)
    return manager, commits, download_calls, group_dirs


def test_repo_manager_mirror_repo_files_grouped_commits_each_group(monkeypatch, tmp_path):
    gb = 1024**3
    src_files = [
        {"path": "a.bin", "type": "file", "size": 3 * gb, "sha256": _sha256("a")},
        {"path": "nested/b.bin", "type": "file", "size": 3 * gb, "sha256": _sha256("b")},
        {"path": "c.bin", "type": "file", "size": 1 * gb, "sha256": _sha256("c")},
        {"path": "d.bin", "type": "file", "size": 1, "sha256": _sha256("d")},
    ]
    manager, commits, download_calls, group_dirs = _grouped_mirror_manager(monkeypatch, tmp_path, src_files, free_space=10 * gb)
    work_dir = tmp_path / "work"

    manager.mirror_repo_files(
        src_api_type="huggingface",
        dst_api_type="modelscope",
        src_repo_id="owner/src",
        dst_repo_id="owner/dst",
        dst_repo_type="dataset",
        revision="group-rev",
        num_threads=2,
        retry_times=1,
        use_group_mirror=True,
        group_size=3,
        reserved_disk_space_gb=4,
        work_dir=work_dir,
    )

    # 可用空间为 10 - 4 = 6 GB, 每组最多 3 个文件
    assert [commit["files"] for commit in commits] == [["a.bin", "nested/b.bin"], ["c.bin", "d.bin"]]
    assert {commit["repo_id"] for commit in commits} == {"owner/dst"}
    assert {commit["repo_type"] for commit in commits} == {"dataset"}
    assert {commit["revision"] for commit in commits} == {"group-rev"}
    assert {commit["token"] for commit in commits} == {"ms-token"}
    assert [commit["commit_message"] for commit in commits] == ["Mirror 2 files (group 1)", "Mirror 2 files (group 2)"]
    assert sorted(download_calls) == ["a.bin", "c.bin", "d.bin", "nested/b.bin"]
    assert {path.parent for path in group_dirs} == {work_dir}
    assert not any(path.exists() for path in group_dirs)
    assert list(work_dir.iterdir()) == []


def test_repo_manager_mirror_repo_files_grouped_commits_partial_group_and_reports_errors(monkeypatch, tmp_path):
    gb = 1024**3
    src_files = [
        {"path": "ok.bin", "type": "file", "size": 1, "sha256": _sha256("ok")},
        {"path": "broken.bin", "type": "file", "size": 1, "sha256": _sha256("broken")},
        {"path": "huge.bin", "type": "file", "size": 20 * gb, "sha256": _sha256("huge")},
    ]
    manager, commits, download_calls, _group_dirs = _grouped_mirror_manager(
        monkeypatch,
        tmp_path,
        src_files,
        free_space=10 * gb,
        fail_files={"broken.bin"},
    )

    with pytest.raises(AggregateError) as exc_info:
        manager.mirror_repo_files(
            src_api_type="huggingface",
            dst_api_type="modelscope",
            src_repo_id="owner/src",
            dst_repo_id="owner/dst",
            retry_times=1,
            use_group_mirror=True,
            group_size=10,
            reserved_disk_space_gb=1,
            work_dir=tmp_path / "work",
        )

    assert [commit["files"] for commit in commits] == [["ok.bin"]]
    assert "huge.bin" not in download_calls
    messages = [str(error) for error in exc_info.value.exceptions]
    assert len(messages) == 2
    assert any("huge.bin" in message for message in messages)


def test_repo_manager_mirror_repo_files_grouped_stops_when_reserve_exceeds_free_space(monkeypatch, tmp_path):
    src_files = [{"path": "a.bin", "type": "file", "size": 1, "sha256": _sha256("a")}]
    manager, commits, download_calls, _group_dirs = _grouped_mirror_manager(monkeypatch, tmp_path, src_files, free_space=1024**3)

    with pytest.raises(AggregateError):
        manager.mirror_repo_files(
            src_api_type="huggingface",
            dst_api_type="modelscope",
            src_repo_id="owner/src",
            dst_repo_id="owner/dst",
            retry_times=1,
            use_group_mirror=True,
            reserved_disk_space_gb=2,
            work_dir=tmp_path / "work",
        )

    assert commits == []
    assert download_calls == []


@pytest.mark.parametrize(
    ("group_size", "reserved_disk_space_gb"),
    [(0, 1.0), (1, -1.0)],
)
def test_repo_manager_mirror_repo_files_grouped_rejects_invalid_arguments(group_size, reserved_disk_space_gb):
    manager = repo_manager_with_apis()

    with pytest.raises(ValueError):
        manager.mirror_repo_files(
            src_api_type="huggingface",
            dst_api_type="modelscope",
            src_repo_id="owner/src",
            dst_repo_id="owner/dst",
            use_group_mirror=True,
            group_size=group_size,
            reserved_disk_space_gb=reserved_disk_space_gb,
        )
