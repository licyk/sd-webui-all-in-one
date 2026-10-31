"""环境快照 Git 仓库恢复测试"""

import pytest

from sd_webui_all_in_one.base_manager import snapshot as snapshot_utils
from sd_webui_all_in_one.base_manager import snapshot_restore as restore_utils
from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryProbe
from sd_webui_all_in_one.base_manager.snapshot_restore import extensions as restore_extensions
from tests.base_manager.snapshot.helpers import make_extension_snapshot, make_git_repo_snapshot, make_webui_snapshot, write_fake_git_dir


def test_restore_git_repository_refuses_reset_when_dirty_state_unknown(monkeypatch, tmp_path):
    repo = snapshot_utils.RepositorySnapshot(
        path=tmp_path / "demo",
        name="demo",
        is_git_repo=True,
        url="https://example.test/demo.git",
        commit="abcdef",
    )
    switched = []
    monkeypatch.setattr(restore_extensions, "_ensure_git_target", lambda _repo, _path: True)
    monkeypatch.setattr(restore_extensions, "probe_repository", lambda path: RepositoryProbe(path=path, is_git_repo=True, commit="123456", dirty=None))
    monkeypatch.setattr(restore_extensions, "repository_has_commit", lambda _path, _commit: False)
    monkeypatch.setattr(restore_extensions, "fetch_repository", lambda _path: None)
    monkeypatch.setattr(restore_extensions.git_warpper, "switch_commit", lambda path, commit: switched.append((path, commit)))

    with pytest.raises(RuntimeError, match="无法检查"):
        restore_extensions.restore_git_repository(repo, tmp_path / "demo", restore_utils.SnapshotRestoreOptions())
    assert switched == []

    assert restore_extensions.restore_git_repository(repo, tmp_path / "demo", restore_utils.SnapshotRestoreOptions(force_git_reset=True)) is True
    assert switched == [(tmp_path / "demo", "abcdef")]


def test_restore_git_repository_requires_clean_worktree_unless_forced(monkeypatch, tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    repo = snapshot_utils.RepositorySnapshot(
        path=target,
        name="repo",
        is_git_repo=True,
        url="https://example.test/repo.git",
        commit="abcdef",
    )

    monkeypatch.setattr(restore_extensions, "probe_repository", lambda path: RepositoryProbe(path=path, is_git_repo=True, commit="123456", dirty=True))
    monkeypatch.setattr(restore_extensions, "repository_has_commit", lambda _path, _commit: False)

    with pytest.raises(RuntimeError, match="存在未提交变更"):
        restore_utils.restore_git_repository(repo, target, restore_utils.SnapshotRestoreOptions())

    calls = []
    monkeypatch.setattr(restore_extensions, "fetch_repository", lambda path: calls.append(("fetch", path)))
    monkeypatch.setattr(restore_extensions.git_warpper, "switch_commit", lambda path, commit: calls.append(("switch", path, commit)))

    restored = restore_utils.restore_git_repository(
        repo,
        target,
        restore_utils.SnapshotRestoreOptions(force_git_reset=True),
    )

    assert restored is True
    assert calls == [("fetch", target), ("switch", target, "abcdef")]


def _track_git_restore_calls(monkeypatch, has_commit: bool) -> list[tuple]:
    calls: list[tuple] = []
    monkeypatch.setattr(restore_extensions, "repository_has_commit", lambda _path, _commit: has_commit)
    monkeypatch.setattr(restore_extensions, "fetch_repository", lambda path: calls.append(("fetch", path)))
    monkeypatch.setattr(restore_extensions.git_warpper, "switch_commit", lambda path, commit: calls.append(("switch", path, commit)))
    return calls


def test_restore_git_repository_skips_fetch_and_reset_when_already_at_snapshot_commit(monkeypatch, tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    full_commit = "abcdef" + "0" * 34
    monkeypatch.setattr(restore_extensions, "probe_repository", lambda path: RepositoryProbe(path=path, is_git_repo=True, commit=full_commit, dirty=False))
    calls = _track_git_restore_calls(monkeypatch, has_commit=True)

    assert restore_utils.restore_git_repository(make_git_repo_snapshot(target), target, restore_utils.SnapshotRestoreOptions()) is True
    assert calls == []


def test_restore_git_repository_resets_dirty_repo_at_snapshot_commit_when_forced(monkeypatch, tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    monkeypatch.setattr(restore_extensions, "probe_repository", lambda path: RepositoryProbe(path=path, is_git_repo=True, commit="abcdef", dirty=True))
    calls = _track_git_restore_calls(monkeypatch, has_commit=True)

    assert restore_utils.restore_git_repository(make_git_repo_snapshot(target), target, restore_utils.SnapshotRestoreOptions(force_git_reset=True)) is True
    # 强制恢复仍需重置工作区以丢弃未提交变更, 但 commit 已在本地无需拉取。
    assert calls == [("switch", target, "abcdef")]


@pytest.mark.parametrize(("has_commit", "expected_fetch"), [(True, False), (False, True)])
def test_restore_git_repository_fetches_only_when_snapshot_commit_missing_locally(monkeypatch, tmp_path, has_commit, expected_fetch):
    target = tmp_path / "repo"
    target.mkdir()
    monkeypatch.setattr(restore_extensions, "probe_repository", lambda path: RepositoryProbe(path=path, is_git_repo=True, commit="123456", dirty=False))
    calls = _track_git_restore_calls(monkeypatch, has_commit=has_commit)

    assert restore_utils.restore_git_repository(make_git_repo_snapshot(target), target, restore_utils.SnapshotRestoreOptions()) is True
    assert calls == ([("fetch", target)] if expected_fetch else []) + [("switch", target, "abcdef")]


def _fail_probe(_path):
    raise AssertionError("repository already at snapshot commit should not spawn git status")


def test_git_restore_skips_repo_at_snapshot_commit_without_git_status(monkeypatch, tmp_path):
    target = tmp_path / "repo"
    full_commit = "abcdef" + "0" * 34
    write_fake_git_dir(target, full_commit)
    monkeypatch.setattr(restore_extensions, "probe_repository", _fail_probe)
    calls = _track_git_restore_calls(monkeypatch, has_commit=True)
    repo = make_git_repo_snapshot(target)
    options = restore_utils.SnapshotRestoreOptions()

    plan = restore_extensions._build_git_restore_plan(repo, target, options)
    assert (plan.action, plan.current_commit, plan.dirty) == ("skip_same_commit", full_commit, None)
    assert restore_utils.restore_git_repository(repo, target, options) is True
    assert calls == []


def test_git_restore_does_not_block_dirty_repo_already_at_snapshot_commit(monkeypatch, tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    # HEAD 无法直接解析时回退到 git status; 已位于快照 commit 时未提交变更不会被修改, 不应阻断
    monkeypatch.setattr(restore_extensions, "probe_repository", lambda path: RepositoryProbe(path=path, is_git_repo=True, commit="abcdef", dirty=True))
    calls = _track_git_restore_calls(monkeypatch, has_commit=True)
    repo = make_git_repo_snapshot(target)
    options = restore_utils.SnapshotRestoreOptions()

    plan = restore_extensions._build_git_restore_plan(repo, target, options)
    assert (plan.action, plan.dirty) == ("skip_same_commit", True)
    assert restore_utils.restore_git_repository(repo, target, options) is True
    assert calls == []


def test_git_restore_plan_reports_reset_for_dirty_repo_at_snapshot_commit_when_forced(monkeypatch, tmp_path):
    target = tmp_path / "repo"
    write_fake_git_dir(target, "abcdef" + "0" * 34)
    monkeypatch.setattr(restore_extensions, "probe_repository", lambda path: RepositoryProbe(path=path, is_git_repo=True, commit="abcdef", dirty=True))

    plan = restore_extensions._build_git_restore_plan(make_git_repo_snapshot(target), target, restore_utils.SnapshotRestoreOptions(force_git_reset=True))

    # 强制恢复会重置工作区丢弃未提交变更, 预检查需如实报告而不是显示为跳过
    assert plan.action == "switch_commit"
    assert "重置" in plan.reason


def test_ensure_git_restore_targets_clean_only_checks_repos_that_need_switching(monkeypatch, tmp_path):
    webui_path = tmp_path / "ComfyUI"
    custom_nodes = webui_path / "custom_nodes"
    write_fake_git_dir(webui_path, "abcdef" + "0" * 34)
    write_fake_git_dir(custom_nodes / "SameNode", "abcdef" + "0" * 34)
    (custom_nodes / "DirtySameNode").mkdir(parents=True)
    (custom_nodes / "DirtyOtherNode").mkdir(parents=True)
    snapshot = make_webui_snapshot(webui_path)
    snapshot.webui.type = "comfyui"
    snapshot.kernel = make_git_repo_snapshot(webui_path)
    snapshot.extensions = [make_extension_snapshot(name, custom_nodes / name, True) for name in ("SameNode", "DirtySameNode", "DirtyOtherNode")]
    probed = []

    def fake_probe(path):
        probed.append(path.name)
        return RepositoryProbe(path=path, is_git_repo=True, commit="abcdef" if path.name == "DirtySameNode" else "123456", dirty=True)

    monkeypatch.setattr(restore_extensions, "probe_repository", fake_probe)

    with pytest.raises(RuntimeError, match="存在未提交变更") as exc_info:
        restore_extensions.ensure_git_restore_targets_clean(snapshot, webui_path, restore_utils.SnapshotRestoreOptions())

    assert sorted(probed) == ["DirtyOtherNode", "DirtySameNode"]
    assert "DirtyOtherNode" in str(exc_info.value)
    assert "DirtySameNode" not in str(exc_info.value)
