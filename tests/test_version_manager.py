import json

import pytest

from sd_webui_all_in_one.custom_exceptions import AggregateError
import sd_webui_all_in_one.base_manager.version_manager as version_manager
from sd_webui_all_in_one.base_manager.base import apply_github_raw_file_mirror
from sd_webui_all_in_one.base_manager.sd_webui_base import (
    list_sd_webui_extensions,
    set_sd_webui_extensions_status,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    filter_extension_index,
    inspect_repository,
    parse_comfyui_custom_node_index,
    parse_extension_index,
)


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

    monkeypatch.setattr(version_manager, "_git_output", _fake_git_output)

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

    monkeypatch.setattr(version_manager, "_git_output", lambda *_args: "abcdef\x1f2026-05-02 12:00:00 +0000\x1fFix")

    state = inspect_repository(repo_path)

    assert state.branch == "pixeloe"
    assert state.url == "https://github.com/KohakuBlueleaf/a1111-sd-webui-haku-img"


def test_sd_webui_extension_status_config(tmp_path):
    sd_webui_path = tmp_path / "webui"
    extension_path = sd_webui_path / "extensions" / "demo-extension"
    extension_path.mkdir(parents=True)
    (sd_webui_path / "config.json").write_text(json.dumps({"disabled_extensions": ["demo-extension"]}), encoding="utf-8")

    assert list_sd_webui_extensions(sd_webui_path)[0]["status"] is False

    set_sd_webui_extensions_status(sd_webui_path, "demo-extension", True)
    assert list_sd_webui_extensions(sd_webui_path)[0]["status"] is True

    set_sd_webui_extensions_status(sd_webui_path, "demo-extension", False)
    assert list_sd_webui_extensions(sd_webui_path)[0]["status"] is False


def test_parse_extension_index_tolerates_missing_fields():
    items = parse_extension_index(
        {
            "extensions": [
                {"name": "ControlNet", "url": "https://github.com/Mikubill/sd-webui-controlnet", "tags": ["script", "models"]},
                {"description": "missing url"},
                {"url": "https://github.com/example/example-extension"},
            ]
        }
    )

    assert [item.name for item in items] == ["ControlNet", "example-extension"]
    assert items[0].tags == ("script", "models")


def test_filter_extension_index_by_keyword_and_tag():
    items = parse_extension_index(
        [
            {"name": "Agent Scheduler", "url": "https://github.com/example/agent", "description": "Queue task history", "tags": ["script"]},
            {"name": "ua_UA Localization", "url": "https://github.com/example/ua", "description": "Ukrainian localization", "tags": ["localization"]},
        ]
    )

    assert [item.name for item in filter_extension_index(items, "queue")] == ["Agent Scheduler"]
    assert [item.name for item in filter_extension_index(items, "", ["localization"])] == ["ua_UA Localization"]


def test_parse_comfyui_custom_node_index_git_and_copy():
    items = parse_comfyui_custom_node_index(
        {
            "custom_nodes": [
                {
                    "author": "Comfy-Org",
                    "title": "ComfyUI-Manager",
                    "reference": "https://github.com/Comfy-Org/ComfyUI-Manager",
                    "files": ["https://github.com/Comfy-Org/ComfyUI-Manager"],
                    "install_type": "git-clone",
                    "description": "Manager",
                },
                {
                    "author": "time-river",
                    "title": "CLIPSeg",
                    "reference": "https://github.com/time-river/ComfyUI-CLIPSeg",
                    "files": ["https://raw.githubusercontent.com/time-river/ComfyUI-CLIPSeg/main/custom_nodes/clipseg.py"],
                    "install_type": "copy",
                    "description": "Single file node",
                },
            ]
        }
    )

    assert [item.name for item in items] == ["ComfyUI-Manager", "CLIPSeg"]
    assert items[0].install_type == "git-clone"
    assert items[1].install_type == "copy"
    assert items[1].files == ("https://raw.githubusercontent.com/time-river/ComfyUI-CLIPSeg/main/custom_nodes/clipseg.py",)


def test_apply_github_raw_file_mirror_with_direct_json_url():
    url = apply_github_raw_file_mirror(
        raw_file_path="owner/repo/main/index.json",
        custom_github_mirror="https://example.com/index.json",
    )

    assert url == "https://example.com/index.json"


def test_apply_github_raw_file_mirror_with_prefix_url():
    url = apply_github_raw_file_mirror(
        raw_file_path="owner/repo/main/index.json",
        custom_github_mirror="https://mirror.example.com/github.com",
    )

    assert url == "https://mirror.example.com/raw.githubusercontent.com/owner/repo/main/index.json"


def test_list_commits_and_branches_parse_git_output(monkeypatch, tmp_path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    fetch_calls = []

    monkeypatch.setattr(version_manager.git_warpper, "is_git_repo", lambda _path: True)
    monkeypatch.setattr(version_manager.git_warpper, "get_current_commit", lambda _path: "abc123")
    monkeypatch.setattr(version_manager.git_warpper, "get_current_branch", lambda _path: "main")
    monkeypatch.setattr(version_manager, "fetch_repository", lambda path: fetch_calls.append(path))

    def fake_git_output(_path, *args):
        if args[:1] == ("log",):
            return "\n".join(
                [
                    "abc123\x1f2026-05-01\x1fcurrent",
                    "def456\x1f2026-04-30\x1folder",
                    "malformed",
                ]
            )
        if args == ("branch", "--all", "--format=%(refname:short)"):
            return "\n".join(["origin/HEAD -> origin/main", "origin/dev", "main", "origin/main"])
        raise AssertionError(args)

    monkeypatch.setattr(version_manager, "_git_output", fake_git_output)

    commits = version_manager.list_commits(repo_path, limit=2)
    assert [(item.commit, item.is_current) for item in commits] == [("abc123", True), ("def456", False)]

    branches = version_manager.list_branches(repo_path, fetch=True)
    assert fetch_calls == [repo_path]
    assert [(item.name, item.is_current, item.is_remote) for item in branches] == [
        ("main", True, False),
        ("dev", False, True),
    ]

    monkeypatch.setattr(version_manager.git_warpper, "is_git_repo", lambda _path: False)
    assert version_manager.list_commits(repo_path) == []
    assert version_manager.list_branches(repo_path) == []


def test_extension_manager_lifecycle_delegates_and_aggregates(monkeypatch, tmp_path):
    root = tmp_path / "webui"
    ext_root = root / "extensions"
    git_ext = ext_root / "git-ext"
    plain_ext = ext_root / "plain-ext"
    ignored_ext = ext_root / "__pycache__"
    git_ext.mkdir(parents=True)
    plain_ext.mkdir()
    ignored_ext.mkdir()

    enabled_changes = []

    manager = version_manager.ExtensionManager(
        root_path=root,
        extension_dir_name="extensions",
        is_enabled=lambda name, _path: name != "plain-ext",
        set_enabled=lambda name, enabled: enabled_changes.append((name, enabled)),
    )

    def fake_inspect(path):
        return version_manager.RepositoryState(
            path=path,
            is_git_repo=path.name == "git-ext",
            name=path.name,
            url=f"https://example.test/{path.name}",
            branch="main",
            commit="abc",
        )

    monkeypatch.setattr(version_manager, "inspect_repository", fake_inspect)

    extensions = manager.list_extensions()
    assert [item.name for item in extensions] == ["git-ext", "plain-ext"]
    assert extensions[0].is_git_repo is True
    assert extensions[1].enabled is False

    manager.set_extension_enabled("plain-ext", True)
    assert enabled_changes == [("plain-ext", True)]

    clones = []
    monkeypatch.setattr(version_manager, "clone_repo", lambda repo, path: clones.append((repo, path)))
    assert manager.install_extension("https://github.com/example/new-ext.git") == ext_root / "new-ext"
    assert clones == [("https://github.com/example/new-ext.git", ext_root / "new-ext")]
    with pytest.raises(FileExistsError):
        manager.install_extension("https://github.com/example/git-ext.git")

    monkeypatch.setattr(version_manager.git_warpper, "is_git_repo", lambda path: path.name == "git-ext")
    updates = []
    monkeypatch.setattr(version_manager, "update_repository", lambda path: updates.append(path))
    manager.update_extension("git-ext")
    with pytest.raises(ValueError):
        manager.update_extension("plain-ext")
    assert updates == [git_ext]

    def update_or_fail(path):
        raise RuntimeError("bad update")

    monkeypatch.setattr(version_manager, "update_repository", update_or_fail)
    with pytest.raises(AggregateError) as exc:
        manager.update_all()
    assert len(exc.value.exceptions) == 1

    removed = []
    monkeypatch.setattr(version_manager, "remove_files", lambda path: removed.append(path))
    manager.uninstall_extension("plain-ext")
    assert removed == [plain_ext]
    with pytest.raises(FileNotFoundError):
        manager.uninstall_extension("missing")
