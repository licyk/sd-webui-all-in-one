"""扩展索引与扩展管理测试"""

import json

import pytest

import sd_webui_all_in_one.base_manager.repository_inspector as repository_inspector
import sd_webui_all_in_one.base_manager.version_manager as version_manager
from sd_webui_all_in_one.base_manager.sd_webui_base import (
    list_sd_webui_extensions,
    set_sd_webui_extensions_status,
)
from sd_webui_all_in_one.base_manager.version_manager import checks as version_checks
from sd_webui_all_in_one.base_manager.version_manager import extensions as version_extensions
from sd_webui_all_in_one.base_manager.version_manager import (
    filter_extension_index,
    parse_comfyui_custom_node_index,
    parse_extension_index,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError


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
                {"name": "ControlNet", "url": "https://github.com/licyk/sd-webui-controlnet", "tags": ["script", "models"]},
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

    registry_items = [
        version_manager.ExtensionIndexItem(
            name="Registry Node",
            url="https://github.com/example/registry-node",
            source_type="comfy-registry",
            author="Registry Author",
            tags=("Comfy Registry",),
        )
    ]
    assert [item.name for item in filter_extension_index(registry_items, "registry author")] == ["Registry Node"]


def test_extension_manager_check_updates_keeps_non_git_entries(monkeypatch, tmp_path):
    manager = version_manager.ExtensionManager(
        tmp_path,
        "extensions",
        is_enabled=lambda _name, _path: True,
        set_enabled=lambda _name, _enabled: None,
    )
    git_ext = version_manager.ManagedExtension("git-ext", tmp_path / "extensions" / "git-ext", True, True)
    file_ext = version_manager.ManagedExtension("file-ext", tmp_path / "extensions" / "file-ext.py", True, False, error="非 Git 仓库")

    monkeypatch.setattr(manager, "list_extensions", lambda: [git_ext, file_ext])
    monkeypatch.setattr(
        version_extensions,
        "check_repository_update",
        lambda path, **_kwargs: version_manager.RepositoryUpdateStatus(name=path.name, path=path, is_git_repo=True, has_update=True, behind=2),
    )

    result = manager.check_updates()

    assert [item.name for item in result] == ["git-ext", "file-ext"]
    assert result[0].has_update is True
    assert result[0].behind == 2
    assert result[1].is_git_repo is False
    assert result[1].error == "非 Git 仓库"


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
    assert [item.author for item in items] == ["Comfy-Org", "time-river"]
    assert items[0].install_type == "git-clone"
    assert items[1].install_type == "copy"
    assert items[1].files == ("https://raw.githubusercontent.com/time-river/ComfyUI-CLIPSeg/main/custom_nodes/clipseg.py",)


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
        return repository_inspector.RepositoryState(
            path=path,
            is_git_repo=path.name == "git-ext",
            name=path.name,
            url=f"https://example.test/{path.name}",
            branch="main",
            commit="abc",
        )

    monkeypatch.setattr(version_extensions, "inspect_repository", fake_inspect)

    extensions = manager.list_extensions()
    assert [item.name for item in extensions] == ["git-ext", "plain-ext"]
    assert extensions[0].is_git_repo is True
    assert extensions[1].enabled is False

    manager.set_extension_enabled("plain-ext", True)
    assert enabled_changes == [("plain-ext", True)]

    clones = []
    monkeypatch.setattr(version_extensions, "clone_repo", lambda repo, path: clones.append((repo, path)))
    assert manager.install_extension("https://github.com/example/new-ext.git") == ext_root / "new-ext"
    assert clones == [("https://github.com/example/new-ext.git", ext_root / "new-ext")]
    with pytest.raises(FileExistsError):
        manager.install_extension("https://github.com/example/git-ext.git")

    monkeypatch.setattr(version_extensions.git_warpper, "is_git_repo", lambda path: path.name == "git-ext")
    updates = []
    monkeypatch.setattr(version_extensions, "update_repository", lambda path: updates.append(path))
    manager.update_extension("git-ext")
    with pytest.raises(ValueError):
        manager.update_extension("plain-ext")
    assert updates == [git_ext]

    def update_or_fail(path, live=True, fetch=True):
        assert live is False
        raise RuntimeError("bad update")

    monkeypatch.setattr(version_extensions.git_warpper, "update", update_or_fail)
    with pytest.raises(AggregateError) as exc:
        manager.update_all()
    assert len(exc.value.exceptions) == 1

    batch_updates = []
    monkeypatch.setattr(version_extensions.git_warpper, "update", lambda path, live=True, fetch=True: batch_updates.append((path, fetch)) or True)
    with pytest.raises(AggregateError) as exc:
        manager.update_extensions(["git-ext", "plain-ext", "git-ext"], fetch=False)
    assert batch_updates == [(git_ext, False)]
    assert len(exc.value.exceptions) == 1
    batch_updates.clear()
    assert manager.update_extensions(["git-ext"]) == ["git-ext"]
    assert batch_updates == [(git_ext, True)]

    removed = []
    monkeypatch.setattr(version_extensions, "remove_files", lambda path: removed.append(path))
    manager.uninstall_extension("plain-ext")
    assert removed == [plain_ext]
    with pytest.raises(FileNotFoundError):
        manager.uninstall_extension("missing")


def test_check_extension_updates_resolves_registry_versions(tmp_path):
    extension = version_manager.ManagedExtension(
        "registry-node",
        tmp_path / "registry-node",
        True,
        False,
        source_type="comfy-registry",
        registry_id="registry-node",
        registry_version="1.0.0",
    )

    result = version_manager.check_extension_updates([extension], registry_version_resolver=lambda _extension: "1.1.0")

    assert result[0].current_version == "1.0.0"
    assert result[0].latest_version == "1.1.0"
    assert result[0].has_update is True
    assert result[0].skipped is False


def test_check_extension_updates_runs_in_parallel_and_configures_mirror_once(monkeypatch, tmp_path):
    import threading

    extensions = [version_manager.ManagedExtension(name=f"ext-{index}", path=tmp_path / f"ext-{index}", enabled=True, is_git_repo=True, source_type="git") for index in range(4)]
    barrier = threading.Barrier(len(extensions), timeout=5)
    mirror_calls = []
    fetch_flags = []

    def fake_check(path, fetch=True, **kwargs):
        assert not kwargs, "mirror must be configured once before the parallel checks"
        fetch_flags.append(fetch)
        barrier.wait()
        behind = int(path.name.rsplit("-", 1)[1])
        return version_manager.RepositoryUpdateStatus(name=path.name, path=path, is_git_repo=True, has_update=behind > 0, behind=behind)

    monkeypatch.setattr(version_checks, "configure_git_env", lambda **kwargs: mirror_calls.append(kwargs) or {})
    monkeypatch.setattr(version_checks, "check_repository_update", fake_check)

    result = version_manager.check_extension_updates(extensions, use_github_mirror=True, custom_github_mirror="https://mirror.example", max_workers=4)

    assert [item.name for item in result] == [ext.name for ext in extensions]
    assert [item.behind for item in result] == [0, 1, 2, 3]
    assert [item.has_update for item in result] == [False, True, True, True]
    assert mirror_calls == [{"use_github_mirror": True, "custom_github_mirror": "https://mirror.example"}]
    assert fetch_flags == [True] * 4


def test_extension_manager_check_updates_parallel_preserves_order(monkeypatch, tmp_path):
    import threading

    manager = version_manager.ExtensionManager(tmp_path, "extensions", lambda _name, _path: True, lambda _name, _enabled: None, use_github_mirror=True)
    extensions = [
        version_manager.ManagedExtension(name="a", path=tmp_path / "a", enabled=True, is_git_repo=True, source_type="git"),
        version_manager.ManagedExtension(name="plain", path=tmp_path / "plain", enabled=True, is_git_repo=False, source_type="unknown"),
        version_manager.ManagedExtension(name="b", path=tmp_path / "b", enabled=True, is_git_repo=True, source_type="git"),
    ]
    barrier = threading.Barrier(2, timeout=5)

    def fake_check(path, fetch=True):
        barrier.wait()
        return version_manager.RepositoryUpdateStatus(name="", path=path, is_git_repo=True, has_update=path.name == "b", behind=int(path.name == "b"))

    monkeypatch.setattr(manager, "list_extensions", lambda: extensions)
    monkeypatch.setattr(version_extensions, "check_repository_update", fake_check)

    result = manager.check_updates()

    assert [item.name for item in result] == ["a", "plain", "b"]
    assert [item.has_update for item in result] == [False, False, True]
    assert result[1].is_git_repo is False
