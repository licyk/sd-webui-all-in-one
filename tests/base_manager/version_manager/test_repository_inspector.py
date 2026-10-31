"""Git 仓库信息读取测试"""

import zlib

import pytest

import sd_webui_all_in_one.base_manager.repository_inspector as repository_inspector
from sd_webui_all_in_one.base_manager.repository_inspector import inspect_repository


def test_inspect_non_git_directory(tmp_path):
    repo_path = tmp_path / "plain-extension"
    repo_path.mkdir()

    state = inspect_repository(repo_path)

    assert state.is_git_repo is False
    assert state.name == "plain-extension"
    assert state.error


def test_inspect_repository_reads_git_info_with_single_git_command(tmp_path, monkeypatch):
    repo_path = tmp_path / "repo"
    git_path = repo_path / ".git"
    git_path.mkdir(parents=True)
    (git_path / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_path / "config").write_text(
        "\n".join(
            [
                '[remote "origin"]',
                "    url = https://github.com/example/repo.git",
                '[branch "main"]',
                "    remote = origin",
                "    merge = refs/heads/main",
            ]
        ),
        encoding="utf-8",
    )
    calls = []

    def _fake_git_output(path, *args):
        calls.append((path, args))
        return "abcdef123456\x1f2026-05-02 12:00:00 +0000\x1fInitial commit"

    monkeypatch.setattr(repository_inspector, "run_git_output", _fake_git_output)

    state = inspect_repository(repo_path)

    assert state.is_git_repo is True
    assert state.branch == "main"
    assert state.url == "https://github.com/example/repo.git"
    assert state.commit == "abcdef123456"
    assert state.commit_date == "2026-05-02 12:00:00 +0000"
    assert state.message == "Initial commit"
    assert calls == [(repo_path, ("show", "-s", "--format=%H%x1f%ci%x1f%s", "HEAD"))]


def test_inspect_repository_reads_remote_url_from_git_config_with_duplicate_keys(tmp_path, monkeypatch):
    repo_path = tmp_path / "repo"
    git_path = repo_path / ".git"
    git_path.mkdir(parents=True)
    (git_path / "HEAD").write_text("ref: refs/heads/pixeloe\n", encoding="utf-8")
    (git_path / "config").write_text(
        """
[core]
    repositoryformatversion = 0
    filemode = false
    bare = false
[remote "origin"]
    url = https://github.com/KohakuBlueleaf/a1111-sd-webui-haku-img
    fetch = +refs/heads/*:refs/remotes/origin/*
[branch "main"]
    remote = origin
    merge = refs/heads/main
    vscode-merge-base = origin/main
    vscode-merge-base = origin/main
[remote "upstream"]
    url = git@github.com:KohakuBlueleaf/a1111-sd-webui-haku-img.git
    fetch = +refs/heads/*:refs/remotes/upstream/*
[branch "pixeloe"]
    github-pr-base-branch = "KohakuBlueleaf#a1111-sd-webui-haku-img#main"
    vscode-merge-base = origin/main
    vscode-merge-base = origin/main
    remote = origin
    merge = refs/heads/pixeloe
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(repository_inspector, "run_git_output", lambda *_args: "abcdef\x1f2026-05-02 12:00:00 +0000\x1fFix")

    state = inspect_repository(repo_path)

    assert state.branch == "pixeloe"
    assert state.url == "https://github.com/KohakuBlueleaf/a1111-sd-webui-haku-img"


def test_inspect_repository_falls_back_to_git_files_when_git_command_fails(tmp_path, monkeypatch):
    repo_path = tmp_path / "repo"
    git_path = repo_path / ".git"
    git_path.mkdir(parents=True)
    commit = "a" * 40
    (git_path / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_path / "refs" / "heads").mkdir(parents=True)
    (git_path / "refs" / "heads" / "main").write_text(f"{commit}\n", encoding="utf-8")
    (git_path / "config").write_text(
        "\n".join(
            [
                '[remote "origin"]',
                "    url = https://github.com/example/invoke-node",
                '[branch "main"]',
                "    remote = origin",
                "    merge = refs/heads/main",
            ]
        ),
        encoding="utf-8",
    )
    body = "\n".join(
        [
            f"tree {'b' * 40}",
            "author Demo <demo@example.com> 0 +0000",
            "committer Demo <demo@example.com> 0 +0000",
            "",
            "Fix InvokeAI node snapshot",
            "",
        ]
    ).encode("utf-8")
    object_path = git_path / "objects" / commit[:2] / commit[2:]
    object_path.parent.mkdir(parents=True)
    object_path.write_bytes(zlib.compress(b"commit " + str(len(body)).encode("ascii") + b"\x00" + body))

    def fail_git_output(*_args):
        raise RuntimeError("git failed")

    monkeypatch.setattr(repository_inspector, "run_git_output", fail_git_output)

    state = inspect_repository(repo_path)

    assert state.is_git_repo is True
    assert state.url == "https://github.com/example/invoke-node"
    assert state.branch == "main"
    assert state.commit == commit
    assert state.commit_date == "1970-01-01 00:00:00 +0000"
    assert state.message == "Fix InvokeAI node snapshot"


def test_inspect_repository_falls_back_to_packed_refs_when_git_command_fails(tmp_path, monkeypatch):
    repo_path = tmp_path / "repo"
    git_path = repo_path / ".git"
    git_path.mkdir(parents=True)
    commit = "b" * 40
    (git_path / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_path / "packed-refs").write_text(
        "\n".join(
            [
                "# pack-refs with: peeled fully-peeled sorted",
                f"{commit} refs/heads/main",
            ]
        ),
        encoding="utf-8",
    )
    (git_path / "config").write_text(
        "\n".join(
            [
                '[remote "origin"]',
                "    url = https://github.com/example/packed-node",
                '[branch "main"]',
                "    remote = origin",
            ]
        ),
        encoding="utf-8",
    )

    def fail_git_output(*_args):
        raise RuntimeError("git failed")

    monkeypatch.setattr(repository_inspector, "run_git_output", fail_git_output)

    state = inspect_repository(repo_path)

    assert state.is_git_repo is True
    assert state.url == "https://github.com/example/packed-node"
    assert state.branch == "main"
    assert state.commit == commit


def test_parse_porcelain_v2_tracking_reads_upstream_and_ahead_behind():
    output = "\n".join(
        [
            "# branch.oid " + "a" * 40,
            "# branch.head main",
            "# branch.upstream origin/main",
            "# branch.ab +2 -5",
            "1 .M N... 100644 100644 100644 abc abc file.py",
        ]
    )

    state = repository_inspector._parse_porcelain_v2_tracking(output)

    assert (state.commit, state.branch, state.upstream) == ("a" * 40, "main", "origin/main")
    assert (state.upstream_exists, state.ahead, state.behind, state.dirty) == (True, 2, 5, True)

    gone = repository_inspector._parse_porcelain_v2_tracking("# branch.oid (initial)\n# branch.head (detached)\n# branch.upstream origin/gone\n")
    assert (gone.commit, gone.branch, gone.upstream, gone.upstream_exists) == (None, None, "origin/gone", False)


def _write_fake_git_dir(repo_path, commit):
    git_path = repo_path / ".git"
    (git_path / "refs" / "heads").mkdir(parents=True)
    (git_path / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_path / "refs" / "heads" / "main").write_text(f"{commit}\n", encoding="utf-8")
    (git_path / "config").write_text('[remote "origin"]\n    url = https://github.com/example/repo.git\n', encoding="utf-8")


def test_inspect_repository_without_details_reads_git_dir_without_git_command(tmp_path, monkeypatch):
    repo_path = tmp_path / "repo"
    commit = "a" * 40
    _write_fake_git_dir(repo_path, commit)

    def fail_git_output(*_args):
        raise AssertionError("details=False should not spawn git when HEAD is readable")

    monkeypatch.setattr(repository_inspector, "run_git_output", fail_git_output)

    state = inspect_repository(repo_path, details=False)

    assert state.is_git_repo is True
    assert state.commit == commit
    assert state.branch == "main"
    assert state.url == "https://github.com/example/repo.git"
    assert state.commit_date is None
    assert state.message is None


def test_inspect_repository_without_details_falls_back_to_git_when_head_unreadable(tmp_path, monkeypatch):
    repo_path = tmp_path / "repo"
    _write_fake_git_dir(repo_path, "a" * 40)
    # 引用不在 loose refs 或 packed-refs 中时(例如 reftable 存储)只能交给 Git 解析。
    (repo_path / ".git" / "refs" / "heads" / "main").unlink()
    monkeypatch.setattr(repository_inspector, "run_git_output", lambda *_args: "abcdef\x1f2026-05-02 12:00:00 +0000\x1fFix")

    state = inspect_repository(repo_path, details=False)

    assert state.commit == "abcdef"
    assert state.message == "Fix"


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (f"# branch.oid {'b' * 40}\n# branch.head main\n# branch.upstream origin/main\n# branch.ab +0 -0", ("b" * 40, "main", False)),
        (f"# branch.oid {'b' * 40}\n# branch.head (detached)", ("b" * 40, None, False)),
        ("# branch.oid (initial)\n# branch.head main\n? new.txt", (None, "main", True)),
        (f"# branch.oid {'b' * 40}\n# branch.head main\n1 .M N... 100644 100644 100644 abc abc file.py", ("b" * 40, "main", True)),
    ],
)
def test_probe_repository_parses_status_with_single_git_command(tmp_path, monkeypatch, output, expected):
    calls = []

    def fake_git_output(path, *args):
        calls.append(args)
        return output

    monkeypatch.setattr(repository_inspector, "run_git_output", fake_git_output)

    probe = repository_inspector.probe_repository(tmp_path)

    assert calls == [("status", "--porcelain=v2", "--branch", "--untracked-files=no")]
    assert probe.is_git_repo is True
    assert (probe.commit, probe.branch, probe.dirty) == expected


def test_probe_repository_distinguishes_non_repo_from_unreadable_worktree(tmp_path, monkeypatch):
    repo_path = tmp_path / "repo"
    commit = "c" * 40
    _write_fake_git_dir(repo_path, commit)

    def fail_git_output(*_args):
        raise RuntimeError("status failed")

    monkeypatch.setattr(repository_inspector, "run_git_output", fail_git_output)
    monkeypatch.setattr(repository_inspector.git_warpper, "is_git_repo", lambda _path: False)

    assert repository_inspector.probe_repository(repo_path).is_git_repo is False

    monkeypatch.setattr(repository_inspector.git_warpper, "is_git_repo", lambda _path: True)
    probe = repository_inspector.probe_repository(repo_path)

    # 仓库有效但无法读取工作区状态时 dirty 必须保持未知, 不能当作干净。
    assert probe.is_git_repo is True
    assert probe.dirty is None
    assert probe.commit == commit
    assert probe.branch == "main"


def test_repository_has_commit_uses_cat_file(tmp_path, monkeypatch):
    calls = []

    def fake_git_output(path, *args):
        calls.append(args)
        if args[-1].startswith("missing"):
            raise RuntimeError("bad object")
        return ""

    monkeypatch.setattr(repository_inspector, "run_git_output", fake_git_output)

    assert repository_inspector.repository_has_commit(tmp_path, "abcdef") is True
    assert repository_inspector.repository_has_commit(tmp_path, "missing") is False
    assert calls[0] == ("cat-file", "-e", "abcdef^{commit}")


def test_read_head_commit_parses_git_dir_without_git_command(tmp_path, monkeypatch):
    repo_path = tmp_path / "repo"
    commit = "d" * 40
    _write_fake_git_dir(repo_path, commit)

    def fail_git_output(*_args):
        raise AssertionError("read_head_commit should not spawn git")

    monkeypatch.setattr(repository_inspector, "run_git_output", fail_git_output)

    assert repository_inspector.read_head_commit(repo_path) == commit
    assert repository_inspector.read_head_commit(tmp_path / "missing") is None
