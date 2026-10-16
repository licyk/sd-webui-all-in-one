"""环境快照 Git 仓库恢复测试"""

import pytest

from sd_webui_all_in_one.base_manager import snapshot as snapshot_utils
from sd_webui_all_in_one.base_manager import snapshot_restore as restore_utils
from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryProbe
from sd_webui_all_in_one.base_manager.snapshot_restore import extensions as restore_extensions
from tests.base_manager.snapshot.helpers import make_git_repo_snapshot


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
