import json

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
