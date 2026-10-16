"""环境快照扩展恢复测试"""

import pytest

from sd_webui_all_in_one.base_manager import (
    comfy_registry,
    comfyui_base,
)
from sd_webui_all_in_one.base_manager import snapshot as snapshot_utils
from sd_webui_all_in_one.base_manager import snapshot_restore as restore_utils
from sd_webui_all_in_one.base_manager.snapshot_restore import extensions as restore_extensions
from tests.base_manager.snapshot.helpers import make_extension_snapshot, make_webui_snapshot


def test_restore_extensions_sets_status_and_prunes_with_comfyui_name_normalization(monkeypatch, tmp_path):
    webui_path = tmp_path / "ComfyUI"
    custom_nodes = webui_path / "custom_nodes"
    (custom_nodes / "KeepNode.disabled").mkdir(parents=True)
    (custom_nodes / "ExtraNode.disabled").mkdir()
    (custom_nodes / "__pycache__").mkdir()
    (custom_nodes / "README.md").write_text("", encoding="utf-8")

    snapshot = make_webui_snapshot(webui_path)
    snapshot.webui.type = "comfyui"
    snapshot.extensions = [
        snapshot_utils.ExtensionSnapshot(
            name="KeepNode",
            path=custom_nodes / "KeepNode",
            enabled=False,
            is_git_repo=True,
            url="https://example.test/keep",
            commit="abcdef",
        )
    ]

    restored = []
    statuses = []
    removed = []

    monkeypatch.setattr(
        restore_extensions,
        "_extension_tools",
        lambda _type: restore_utils.ExtensionRestoreTools(
            directory_name="custom_nodes",
            set_status=lambda path, name, enabled: statuses.append((path, name, enabled)),
            uninstall=lambda path, name: removed.append((path, name)),
            strip_disabled_suffix=True,
        ),
    )
    monkeypatch.setattr(
        restore_extensions,
        "restore_git_repository",
        lambda repo, target_path, options: restored.append((repo.name, target_path, options.prune_extensions)) or True,
    )

    restore_extensions.restore_extensions(
        snapshot,
        webui_path,
        restore_utils.SnapshotRestoreOptions(prune_extensions=True),
    )

    assert restore_utils.normalize_extension_name("KeepNode.disabled", strip_disabled_suffix=True) == "keepnode"
    assert restored == [("KeepNode", custom_nodes / "KeepNode", True)]
    assert statuses == [(webui_path, "KeepNode", False)]
    assert removed == [(webui_path, "ExtraNode.disabled")]


def test_restore_extensions_restores_comfyui_registry_node(monkeypatch, tmp_path):
    webui_path = tmp_path / "ComfyUI"
    snapshot = make_webui_snapshot(webui_path)
    snapshot.webui.type = "comfyui"
    snapshot.extensions = [
        snapshot_utils.ExtensionSnapshot(
            name="registry-node",
            path=webui_path / "custom_nodes" / "registry-node",
            enabled=True,
            is_git_repo=False,
            source_type="comfy-registry",
            registry_id="registry-node",
            registry_version="1.2.3",
        )
    ]

    statuses = []
    restored = []
    monkeypatch.setattr(
        restore_extensions,
        "_extension_tools",
        lambda _type: restore_utils.ExtensionRestoreTools(
            directory_name="custom_nodes",
            set_status=lambda path, name, enabled: statuses.append((path, name, enabled)),
            uninstall=lambda path, name: None,
            strip_disabled_suffix=True,
        ),
    )
    monkeypatch.setattr(
        restore_extensions,
        "restore_comfy_registry_extension",
        lambda extension, webui_path, options: restored.append((extension.registry_id, extension.registry_version, webui_path, options.use_uv)) or True,
    )

    restore_extensions.restore_extensions(snapshot, webui_path, restore_utils.SnapshotRestoreOptions(use_uv=False))

    assert restored == [("registry-node", "1.2.3", webui_path, False)]
    assert statuses == [(webui_path, "registry-node", True)]


def test_restore_comfy_registry_extension_skips_unavailable_node(monkeypatch, tmp_path):
    webui_path = tmp_path / "ComfyUI"
    extension = snapshot_utils.ExtensionSnapshot(
        name="ComfyUI for CosyVoice",
        path=webui_path / "custom_nodes" / "ComfyUI_CosyVoice",
        enabled=True,
        is_git_repo=False,
        source_type="comfy-registry",
        registry_id="ComfyUI_CosyVoice",
        registry_version="1.0.0",
    )

    def fail_switch(**kwargs):
        raise comfy_registry.ComfyRegistryInstallUnavailableError(
            node_id=kwargs["node_id"],
            version=kwargs["version"],
            reason="请求 install 返回 404",
            http_status=404,
        )

    monkeypatch.setattr(comfy_registry, "switch_comfy_registry_node_version", fail_switch)
    monkeypatch.setattr(comfyui_base, "resolve_comfyui_custom_node_path", lambda *_args: None)

    restored = restore_utils.restore_comfy_registry_extension(
        extension,
        webui_path,
        restore_utils.SnapshotRestoreOptions(),
    )

    assert restored is False


def test_restore_extensions_continues_after_failure_and_reports_all_errors(monkeypatch, tmp_path):
    from sd_webui_all_in_one.custom_exceptions import AggregateError

    webui_path = tmp_path / "ComfyUI"
    custom_nodes = webui_path / "custom_nodes"
    custom_nodes.mkdir(parents=True)
    names = [f"Node{index:02d}" for index in range(12)]
    snapshot = make_webui_snapshot(webui_path)
    snapshot.webui.type = "comfyui"
    snapshot.extensions = [make_extension_snapshot(name, custom_nodes / name, True) for name in names]

    statuses = []
    removed = []
    monkeypatch.setattr(
        restore_extensions,
        "_extension_tools",
        lambda _type: restore_utils.ExtensionRestoreTools(
            directory_name="custom_nodes",
            set_status=lambda path, name, enabled: statuses.append(name),
            uninstall=lambda path, name: removed.append(name),
            strip_disabled_suffix=True,
        ),
    )
    failing = {"Node03", "Node07"}

    def fake_restore(repo, target_path, options):
        if repo.name in failing:
            raise RuntimeError(f"failed {repo.name}")
        return True

    monkeypatch.setattr(restore_extensions, "restore_git_repository", fake_restore)

    with pytest.raises(AggregateError) as exc_info:
        restore_extensions.restore_extensions(snapshot, webui_path, restore_utils.SnapshotRestoreOptions(prune_extensions=True))

    assert sorted(str(error) for error in exc_info.value.exceptions) == ["failed Node03", "failed Node07"]
    # 其余扩展照常恢复并按快照顺序设置启用状态, 失败时不执行清理。
    assert statuses == [name for name in names if name not in failing]
    assert removed == []

    failing.discard("Node07")
    with pytest.raises(RuntimeError, match="failed Node03"):
        restore_extensions.restore_extensions(snapshot, webui_path, restore_utils.SnapshotRestoreOptions())
