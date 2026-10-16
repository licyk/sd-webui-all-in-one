"""ComfyUI 管理器测试"""

import pytest

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager import comfyui_base
from sd_webui_all_in_one.base_manager.comfy_registry import ComfyRegistryNodeUpdateResult
from sd_webui_all_in_one.base_manager.version_manager import ManagedExtension
from sd_webui_all_in_one.custom_exceptions import AggregateError
from tests.base_manager.products.helpers import fail_old_git_info_reader, fake_repository_state, implementation_module, use_temp_git_config


def test_comfyui_config_installs_once(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(implementation_module(comfyui_base, "install_comfyui_config"), "copy_files", lambda src, dst: calls.append((src, dst)))

    comfyui_base.install_comfyui_config(tmp_path)
    assert calls == [(comfyui_base.COMFYUI_CONFIG_PATH, tmp_path / "user" / "default" / "comfy.settings.json")]

    (tmp_path / "user" / "default").mkdir(parents=True)
    (tmp_path / "user" / "default" / "comfy.settings.json").write_text("{}", encoding="utf-8")
    calls.clear()
    comfyui_base.install_comfyui_config(tmp_path)
    assert calls == []


def test_install_comfyui_orchestrates_extensions_models_and_missing_requirements(monkeypatch, tmp_path):
    calls = []
    git_config_path = use_temp_git_config(monkeypatch, tmp_path)
    implementation = implementation_module(comfyui_base, "install_comfyui")
    (tmp_path / "requirements.txt").write_text("demo\n", encoding="utf-8")

    monkeypatch.setattr(implementation, "COMFYUI_CUSTOM_NODES_INFO_DICT", [{"name": "Node", "url": "https://github.com/example/node", "save_dir": "custom_nodes/node"}])
    monkeypatch.setattr(implementation, "prepare_pytorch_install_info", lambda **kwargs: ("torch", None, {"TORCH": "env"}))
    monkeypatch.setattr(implementation, "get_pypi_mirror_config", lambda use_cn_mirror=True: {"PIP": str(use_cn_mirror)})
    monkeypatch.setattr(implementation, "apply_git_base_config_and_github_mirror", lambda **kwargs: {**kwargs["origin_env"], "GIT_CONFIG_GLOBAL": git_config_path})
    monkeypatch.setattr(implementation, "clone_repo", lambda **kwargs: calls.append(("clone", kwargs)))
    monkeypatch.setattr(implementation, "install_pytorch_for_webui", lambda **kwargs: calls.append(("pytorch", kwargs)))
    monkeypatch.setattr(implementation, "install_requirements", lambda **kwargs: calls.append(("requirements", kwargs)))
    monkeypatch.setattr(implementation, "pre_download_model_for_webui", lambda **kwargs: calls.append(("model", kwargs)))
    monkeypatch.setattr(implementation, "install_comfyui_config", lambda path: calls.append(("config", path)))

    comfyui_base.install_comfyui(tmp_path, no_pre_download_extension=False, no_pre_download_model=False, use_uv=False)

    assert calls[0] == ("clone", {"repo": comfyui_base.COMFYUI_REPO_URL, "path": tmp_path})
    assert calls[1] == ("clone", {"repo": "https://github.com/example/node", "path": tmp_path / "custom_nodes/node"})
    assert calls[3][0] == "requirements"
    assert calls[4][0] == "model"
    assert calls[4][1]["dtype"] == "comfyui"
    assert calls[-1] == ("config", tmp_path)

    with pytest.raises(FileNotFoundError):
        comfyui_base.install_comfyui(tmp_path / "missing", no_pre_download_extension=True)


def test_comfyui_custom_node_lifecycle(monkeypatch, tmp_path):
    implementation = implementation_module(comfyui_base, "list_comfyui_custom_nodes")
    custom_nodes = tmp_path / "custom_nodes"
    (custom_nodes / "installed" / ".git").mkdir(parents=True)
    (custom_nodes / "disabled.disabled").mkdir()
    (custom_nodes / ".disabled" / "registry-node").mkdir(parents=True)
    (custom_nodes / ".disabled" / "registry-node" / ".tracking").write_text("pyproject.toml\n", encoding="utf-8")
    (custom_nodes / ".disabled" / "registry-node" / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "registry-node"',
                'version = "1.0.0"',
            ]
        ),
        encoding="utf-8",
    )
    (custom_nodes / "file.py").write_text("pass", encoding="utf-8")

    monkeypatch.setattr(implementation, "inspect_repository", fake_repository_state)
    monkeypatch.setattr(git_warpper, "get_current_branch_remote_url", fail_old_git_info_reader)
    monkeypatch.setattr(git_warpper, "get_current_commit", fail_old_git_info_reader)
    monkeypatch.setattr(git_warpper, "get_current_branch", fail_old_git_info_reader)

    nodes = sorted(comfyui_base.list_comfyui_custom_nodes(tmp_path), key=lambda item: item["name"])
    assert [node["name"] for node in nodes] == ["disabled.disabled", "installed", "registry-node"]
    assert nodes[0]["status"] is False
    assert nodes[0]["url"] is None
    assert nodes[1]["url"] == "https://example.test/installed"
    assert nodes[1]["commit"] == "installed-full-commit"
    assert nodes[1]["branch"] == "main"
    assert nodes[2]["status"] is False
    assert nodes[2]["source_type"] == "comfy-registry"
    assert nodes[2]["registry_version"] == "1.0.0"

    moves = []
    monkeypatch.setattr(implementation, "move_files", lambda src, dst: moves.append((src, dst)))
    comfyui_base.set_comfyui_custom_node_status(tmp_path, "disabled", True)
    comfyui_base.set_comfyui_custom_node_status(tmp_path, "installed", False)
    comfyui_base.set_comfyui_custom_node_status(tmp_path, "registry-node", True)
    assert moves == [
        (custom_nodes / "disabled.disabled", custom_nodes / "disabled"),
        (custom_nodes / "installed", custom_nodes / "installed.disabled"),
        (custom_nodes / ".disabled" / "registry-node", custom_nodes / "registry-node"),
    ]

    removed = []
    monkeypatch.setattr(implementation, "remove_files", lambda path: removed.append(path))
    comfyui_base.uninstall_comfyui_custom_node(tmp_path, "installed")
    assert removed == [custom_nodes / "installed"]

    with pytest.raises(FileNotFoundError):
        comfyui_base.set_comfyui_custom_node_status(tmp_path, "missing", True)


def test_comfyui_custom_node_install_and_update_aggregate_errors(monkeypatch, tmp_path):
    use_temp_git_config(monkeypatch, tmp_path)
    install_implementation = implementation_module(comfyui_base, "install_comfyui_custom_node")
    custom_nodes = tmp_path / "custom_nodes"
    (custom_nodes / "ok" / ".git").mkdir(parents=True)
    (custom_nodes / "bad" / ".git").mkdir(parents=True)

    monkeypatch.setattr(install_implementation, "list_comfyui_custom_nodes", lambda _path: [{"name": "existing"}])
    monkeypatch.setattr(install_implementation, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])

    cloned = []

    def fake_clone(repo, path):
        cloned.append((repo, path))
        if "fail" in repo:
            raise RuntimeError("clone bad")

    monkeypatch.setattr(install_implementation, "clone_repo", fake_clone)

    with pytest.raises(AggregateError) as exc:
        comfyui_base.install_comfyui_custom_node(tmp_path, ["https://github.com/example/existing", "https://github.com/example/new", "https://github.com/example/fail"])

    assert cloned == [
        ("https://github.com/example/new", custom_nodes / "new"),
        ("https://github.com/example/fail", custom_nodes / "fail"),
    ]
    assert len(exc.value.exceptions) == 1

    updates = []

    def fake_update(path, live=True, fetch=True):
        updates.append(path.name)
        if path.name == "bad":
            raise RuntimeError("update bad")

    monkeypatch.setattr(git_warpper, "update", fake_update)
    with pytest.raises(AggregateError):
        comfyui_base.update_comfyui_custom_nodes(tmp_path)
    assert sorted(updates) == ["bad", "ok"]


def test_comfyui_extension_manager_update_all_reuses_extension_scan(monkeypatch, tmp_path):
    implementation = implementation_module(comfyui_base, "ComfyUiExtensionManager")
    manager = comfyui_base.ComfyUiExtensionManager(tmp_path)
    git_path = tmp_path / "custom_nodes" / "git-node"
    registry_path = tmp_path / "custom_nodes" / "registry-node"
    file_path = tmp_path / "custom_nodes" / "file.py"
    extensions = [
        ManagedExtension(
            name="git-node",
            path=git_path,
            enabled=True,
            is_git_repo=True,
            source_type="git",
        ),
        ManagedExtension(
            name="registry-node",
            path=registry_path,
            enabled=True,
            is_git_repo=False,
            source_type="comfy-registry",
            registry_id="registry-node",
        ),
        ManagedExtension(
            name="file.py",
            path=file_path,
            enabled=True,
            is_git_repo=False,
            source_type="file",
        ),
    ]
    scan_count = 0

    def fake_list_extensions():
        nonlocal scan_count
        scan_count += 1
        return extensions

    git_updates = []
    registry_updates = []

    def fake_registry_update(nodes):
        registry_updates.extend(nodes)
        return [ComfyRegistryNodeUpdateResult(node_id=node_id, path=path, updated=True) for node_id, path in nodes]

    def fake_git_update(path, live=True, fetch=True):
        git_updates.append((path, live, fetch))
        return False

    monkeypatch.setattr(manager, "list_extensions", fake_list_extensions)
    monkeypatch.setattr(git_warpper, "update", fake_git_update)
    monkeypatch.setattr(implementation, "update_comfy_registry_nodes", fake_registry_update)

    assert manager.update_all() == ["registry-node"]

    assert scan_count == 1
    assert git_updates == [(git_path, False, True)]
    assert registry_updates == [("registry-node", registry_path)]

    git_updates.clear()
    registry_updates.clear()
    with pytest.raises(AggregateError) as exc:
        manager.update_extensions(["registry-node", "file.py", "git-node"], fetch=False)
    assert git_updates == [(git_path, False, False)]
    assert registry_updates == [("registry-node", registry_path)]
    assert len(exc.value.exceptions) == 1
    with pytest.raises(FileNotFoundError):
        manager.update_extensions(["missing"])
