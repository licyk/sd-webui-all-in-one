"""环境快照恢复计划预览测试"""

import pytest

from sd_webui_all_in_one.base_manager import snapshot as snapshot_utils
from sd_webui_all_in_one.base_manager import snapshot_restore as restore_utils
from sd_webui_all_in_one.base_manager.gui.snapshot_gui import (
    build_restore_blocking_guidance,
    format_restore_blocking_message,
)
from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryProbe
from sd_webui_all_in_one.base_manager.snapshot_restore import extensions as restore_extensions
from sd_webui_all_in_one.base_manager.snapshot_restore import packages as restore_packages
from sd_webui_all_in_one.pytorch_manager import mirror_selector
from tests.base_manager.snapshot.helpers import make_package_snapshot, make_webui_snapshot


def test_preview_restore_plan_reports_package_actions_and_pytorch_source(monkeypatch, tmp_path):
    missing_local = tmp_path / "missing-local"
    webui_path = tmp_path / "demo"
    webui_path.mkdir()
    snapshot = make_webui_snapshot(webui_path)
    snapshot.packages = [
        make_package_snapshot("sd-webui-all-in-one", "99.0.0"),
        make_package_snapshot("Torch", "2.7.0+cu128"),
        make_package_snapshot("demo-pkg", "2.0.0"),
        make_package_snapshot(
            "editable-local",
            "1.0.0",
            direct_url=snapshot_utils.DirectUrlSnapshot(
                url=missing_local.as_uri(),
                dir_info=snapshot_utils.DirectUrlDirInfo(editable=True),
            ),
            editable=True,
        ),
        make_package_snapshot("already", "1.0.0"),
    ]
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    monkeypatch.setattr(
        restore_packages,
        "collect_installed_packages",
        lambda: [
            make_package_snapshot("demo_pkg", "1.0.0"),
            make_package_snapshot("already", "1.0.0"),
            make_package_snapshot("old-pkg", "0.1.0"),
            make_package_snapshot("pip", "25.0"),
        ],
    )
    monkeypatch.setattr(restore_packages, "get_pytorch_mirror", lambda dtype, use_cn_mirror: ("https://torch.example/cu128", "index_url"))

    plan = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="demo",
        options=restore_utils.SnapshotRestoreOptions(prune_packages=True, use_pypi_mirror=True),
    )

    actions = {(item.name, item.action) for item in plan.package_changes}
    assert ("sd-webui-all-in-one", "skip_protected") in actions
    assert ("Torch", "install_pytorch_special") in actions
    assert ("demo-pkg", "update") in actions
    assert ("editable-local", "skip_missing_local_path") in actions
    assert ("already", "skip_same_version") in actions
    assert ("old-pkg", "uninstall") in actions
    assert ("pip", "uninstall") not in actions
    assert plan.pytorch_device_type == "cu128"
    assert plan.pytorch_mirror_url == "https://torch.example/cu128"
    assert plan.pytorch_mirror_kind == "index_url"
    assert plan.blockers == []
    assert plan.restorable is True

    diffs = {item.name: item.diff for item in plan.package_changes}
    assert diffs["sd-webui-all-in-one"].status == "skipped"
    assert diffs["Torch"].status == "added"
    assert diffs["demo-pkg"].status == "modified"
    assert diffs["editable-local"].status == "skipped"
    assert diffs["already"].status == "unchanged"
    assert diffs["old-pkg"].status == "removed"
    assert diffs["demo-pkg"].fields == [restore_utils.DiffField(key="version", current="1.0.0", target="2.0.0")]
    assert diffs["old-pkg"].fields == [restore_utils.DiffField(key="version", current="0.1.0", target=None)]
    assert plan.diff_summary.packages.added == 1
    assert plan.diff_summary.packages.modified == 1
    assert plan.diff_summary.packages.removed == 1
    assert plan.diff_summary.packages.unchanged == 1
    assert plan.diff_summary.packages.skipped == 2
    assert plan.diff_summary.total_changes == 3


def test_preview_restore_plan_reports_pytorch_upgrade_as_modified(monkeypatch, tmp_path):
    webui_path = tmp_path / "demo"
    webui_path.mkdir()
    snapshot = make_webui_snapshot(webui_path)
    snapshot.packages = [make_package_snapshot("Torch", "2.7.0+cu128")]
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    monkeypatch.setattr(restore_packages, "collect_installed_packages", lambda: [make_package_snapshot("torch", "2.5.0+cu124")])
    monkeypatch.setattr(restore_packages, "get_pytorch_mirror", lambda dtype, use_cn_mirror: ("https://torch.example/cu128", "index_url"))

    plan = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="demo",
    )

    item = plan.package_changes[0]
    assert item.action == "install_pytorch_special"
    # 同一个 PyTorch 动作同时覆盖新装和升级, 差异状态由当前版本是否存在决定。
    assert item.diff.status == "modified"
    assert item.diff.fields == [restore_utils.DiffField(key="version", current="2.5.0+cu124", target="2.7.0+cu128")]


@pytest.mark.parametrize(
    ("platform_tag", "torch_version", "expected_dtype", "expected_url"),
    [
        ("win32", "2.9.0+rocm9.0", "rocm7", "https://torch.example/rocm7"),
        ("win32", "2.9.0+rocm6.4", "rocm7", "https://torch.example/rocm7"),
        ("win32", "2.13.0+rocm10.0.0", "rocm10", "https://torch.example/rocm10"),
        ("linux", "2.9.0+rocm6.4", "rocm6.4", "https://torch.example/rocm64"),
        ("linux", "2.9.0+rocm9.0", "rocm7", "https://torch.example/rocm7"),
        ("linux", "2.12.0+rocm7.14.1", "rocm7", "https://torch.example/rocm7"),
        ("linux", "2.13.0+rocm10.0.0", "rocm10", "https://torch.example/rocm10"),
        ("linux", "2.9.0+git7bcf7da", "all", "https://torch.example/all"),
    ],
)
def test_preview_restore_plan_normalizes_rocm_pytorch_suffix(monkeypatch, tmp_path, platform_tag, torch_version, expected_dtype, expected_url):
    webui_path = tmp_path / "demo"
    webui_path.mkdir()
    snapshot = make_webui_snapshot(webui_path)
    snapshot.packages = [make_package_snapshot("Torch", torch_version)]
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    mirror_by_dtype = {
        "all": ("https://torch.example/all", "index_url"),
        "rocm7": ("https://torch.example/rocm7", "index_url"),
        "rocm10": ("https://torch.example/rocm10", "index_url"),
        "rocm6.4": ("https://torch.example/rocm64", "index_url"),
    }
    mirror_calls = []

    def fake_get_pytorch_mirror(dtype, use_cn_mirror):
        mirror_calls.append((dtype, use_cn_mirror))
        return mirror_by_dtype[dtype]

    monkeypatch.setattr(mirror_selector.sys, "platform", platform_tag)
    monkeypatch.setattr(restore_packages, "collect_installed_packages", lambda: [])
    monkeypatch.setattr(restore_packages, "get_pytorch_mirror", fake_get_pytorch_mirror)

    plan = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="demo",
        options=restore_utils.SnapshotRestoreOptions(use_pypi_mirror=True),
    )

    assert plan.pytorch_device_type == expected_dtype
    assert plan.pytorch_mirror_url == expected_url
    assert mirror_calls == [(expected_dtype, True)]
    assert plan.warnings == []


def test_preview_restore_plan_blocks_dirty_kernel_without_force(monkeypatch, tmp_path):
    snapshot = make_webui_snapshot(tmp_path / "demo")
    snapshot.kernel = snapshot_utils.RepositorySnapshot(
        path=tmp_path / "demo",
        name="demo",
        is_git_repo=True,
        url="https://example.test/demo.git",
        commit="abcdef",
    )
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)
    (tmp_path / "demo").mkdir()

    monkeypatch.setattr(restore_packages, "collect_installed_packages", lambda: [])
    monkeypatch.setattr(restore_extensions, "probe_repository", lambda path: RepositoryProbe(path=path, is_git_repo=True, commit="123456", dirty=True))

    blocked = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=tmp_path / "demo",
        expected_webui_type="demo",
    )

    assert blocked.kernel_change is not None
    assert blocked.kernel_change.action == "blocked_dirty"
    assert [blocker.message for blocker in blocked.blockers] == ["内核仓库存在未提交变更"]
    assert blocked.blockers[0].code == "kernel_dirty"
    assert blocked.blockers[0].scope == "kernel"
    assert blocked.blockers[0].required_options == ["force_git_reset"]
    assert blocked.required_options == ["force_git_reset"]
    assert blocked.restorable is False
    assert blocked.kernel_change.diff.status == "blocked"
    blocking_message = format_restore_blocking_message(blocked)
    assert "允许覆盖 Git 未提交变更" in blocking_message
    assert "风险" in blocking_message
    assert (tmp_path / "demo").as_posix() in blocking_message

    forced = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=tmp_path / "demo",
        expected_webui_type="demo",
        options=restore_utils.SnapshotRestoreOptions(force_git_reset=True),
    )

    assert forced.kernel_change is not None
    assert forced.kernel_change.action == "switch_commit"
    assert forced.blockers == []
    assert forced.required_options == []
    assert forced.restorable is True
    assert forced.kernel_change.diff.status == "modified"
    assert forced.diff_summary.kernel.modified == 1
    assert forced.diff_summary.total_changes == 1


def test_preview_restore_plan_blocks_kernel_when_dirty_state_unknown(monkeypatch, tmp_path):
    snapshot = make_webui_snapshot(tmp_path / "demo")
    snapshot.kernel = snapshot_utils.RepositorySnapshot(
        path=tmp_path / "demo",
        name="demo",
        is_git_repo=True,
        url="https://example.test/demo.git",
        commit="abcdef",
    )
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)
    (tmp_path / "demo").mkdir()

    monkeypatch.setattr(restore_packages, "collect_installed_packages", lambda: [])
    monkeypatch.setattr(restore_extensions, "probe_repository", lambda path: RepositoryProbe(path=path, is_git_repo=True, commit="123456", dirty=None))

    blocked = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=tmp_path / "demo",
        expected_webui_type="demo",
    )

    assert blocked.kernel_change is not None
    assert blocked.kernel_change.action == "blocked_dirty"
    assert blocked.restorable is False


def test_restore_blocking_guidance_explains_webui_type_mismatch(tmp_path):
    snapshot = make_webui_snapshot(tmp_path / "demo")
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    plan = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=tmp_path / "demo",
        expected_webui_type="other_webui",
    )

    guidance = "\n".join(build_restore_blocking_guidance(plan))

    assert [blocker.message for blocker in plan.blockers] == ["快照 WebUI 类型不匹配: 期望 'other_webui', 实际 'demo'"]
    assert plan.blockers[0].code == "webui_type_mismatch"
    # 类型不匹配无法通过任何恢复选项开关绕过。
    assert plan.blockers[0].required_options == []
    assert plan.required_options == []
    assert plan.restorable is False
    assert "对应的快照管理器" in guidance
    assert "跨 WebUI 类型恢复会被终止" in guidance


def test_preview_restore_plan_blocks_missing_kernel_with_guidance(tmp_path):
    webui_path = tmp_path / "demo"
    snapshot = make_webui_snapshot(webui_path)
    snapshot.kernel = snapshot_utils.RepositorySnapshot(
        path=webui_path,
        name="demo",
        is_git_repo=True,
        url="https://example.test/demo.git",
        commit="abcdef",
    )
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    plan = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="demo",
    )
    guidance = "\n".join(build_restore_blocking_guidance(plan))

    assert plan.kernel_change is not None
    assert plan.kernel_change.action == "blocked_missing_target"
    assert [blocker.message for blocker in plan.blockers] == [f"内核目录不存在: {webui_path}"]
    assert plan.blockers[0].code == "kernel_missing"
    # 缺少内核目录必须先安装 kernel, 没有可以绕过的开关。
    assert plan.required_options == []
    assert plan.restorable is False
    assert "通过 installer 准备对应的 WebUI kernel" in guidance
    assert "不能通过强制恢复开关绕过" in guidance


def test_preview_restore_plan_allows_missing_path_for_package_kernel_webui(monkeypatch, tmp_path):
    webui_path = tmp_path / "invokeai"
    snapshot = make_webui_snapshot(webui_path)
    snapshot.webui.type = "invokeai"
    snapshot.webui.name = "InvokeAI"
    snapshot.kernel = snapshot_utils.RepositorySnapshot(
        path=webui_path,
        name="invokeai",
        is_git_repo=True,
        url="https://example.test/invokeai-root.git",
        commit="abcdef",
    )
    snapshot.extensions = [
        snapshot_utils.ExtensionSnapshot(
            name="DemoNode",
            path=webui_path / "nodes" / "DemoNode",
            enabled=True,
            is_git_repo=True,
            url="https://example.test/demo-node.git",
            commit="123456",
        )
    ]
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)
    monkeypatch.setattr(restore_packages, "collect_installed_packages", lambda: [])

    plan = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="invokeai",
    )

    assert plan.blockers == []
    assert plan.restorable is True
    assert plan.kernel_change is None
    assert len(plan.extension_changes) == 1
    assert plan.extension_changes[0].git is not None
    assert plan.extension_changes[0].git.action == "clone"
    assert plan.extension_changes[0].git.path == webui_path / "nodes" / "DemoNode"


def test_preview_restore_plan_prunes_comfyui_extensions_with_disabled_name(monkeypatch, tmp_path):
    webui_path = tmp_path / "ComfyUI"
    custom_nodes = webui_path / "custom_nodes"
    (custom_nodes / "KeepNode.disabled").mkdir(parents=True)
    (custom_nodes / "ExtraNode.disabled").mkdir()
    snapshot = make_webui_snapshot(webui_path)
    snapshot.webui.type = "comfyui"
    snapshot.extensions = [
        snapshot_utils.ExtensionSnapshot(
            name="KeepNode.disabled",
            path=custom_nodes / "KeepNode.disabled",
            enabled=False,
            is_git_repo=True,
            url="https://example.test/keep",
            commit="abcdef",
        )
    ]
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    monkeypatch.setattr(restore_packages, "collect_installed_packages", lambda: [])
    monkeypatch.setattr(restore_extensions, "probe_repository", lambda path: RepositoryProbe(path=path, is_git_repo=True, commit="123456", dirty=False))

    plan = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="comfyui",
        options=restore_utils.SnapshotRestoreOptions(prune_extensions=True),
    )

    keep = next(item for item in plan.extension_changes if item.name == "KeepNode.disabled")
    extra = next(item for item in plan.extension_changes if item.name == "ExtraNode.disabled")
    assert keep.normalized_name == "keepnode"
    assert keep.current_enabled is False
    assert keep.target_enabled is False
    assert keep.git is not None
    assert keep.git.action == "switch_commit"
    assert extra.cleanup_action == "uninstall"
    assert keep.diff.status == "modified"
    assert extra.diff.status == "removed"
    assert plan.diff_summary.extensions.modified == 1
    assert plan.diff_summary.extensions.removed == 1


def test_preview_restore_plan_marks_enabled_only_extension_change_as_modified(monkeypatch, tmp_path):
    webui_path = tmp_path / "ComfyUI"
    custom_nodes = webui_path / "custom_nodes"
    (custom_nodes / "DemoNode").mkdir(parents=True)
    snapshot = make_webui_snapshot(webui_path)
    snapshot.webui.type = "comfyui"
    snapshot.extensions = [
        snapshot_utils.ExtensionSnapshot(
            name="DemoNode",
            path=custom_nodes / "DemoNode",
            enabled=False,
            is_git_repo=True,
            url="https://example.test/demo",
            commit="abcdef",
        )
    ]
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    monkeypatch.setattr(restore_packages, "collect_installed_packages", lambda: [])
    monkeypatch.setattr(restore_extensions, "probe_repository", lambda path: RepositoryProbe(path=path, is_git_repo=True, commit="abcdef", dirty=False))

    plan = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="comfyui",
    )

    item = plan.extension_changes[0]
    assert item.git is not None
    # 仓库 commit 已一致, 只有启用状态需要切换。
    assert item.git.action == "skip_same_commit"
    assert item.current_enabled is True
    assert item.target_enabled is False
    assert item.diff.status == "modified"
    assert restore_utils.DiffField(key="enabled", current="true", target="false") in item.diff.fields
    assert plan.diff_summary.total_changes == 1


def test_preview_restore_plan_reports_dirty_extension_blocker(monkeypatch, tmp_path):
    webui_path = tmp_path / "ComfyUI"
    custom_nodes = webui_path / "custom_nodes"
    (custom_nodes / "DemoNode").mkdir(parents=True)
    snapshot = make_webui_snapshot(webui_path)
    snapshot.webui.type = "comfyui"
    snapshot.extensions = [
        snapshot_utils.ExtensionSnapshot(
            name="DemoNode",
            path=custom_nodes / "DemoNode",
            enabled=True,
            is_git_repo=True,
            url="https://example.test/demo",
            commit="abcdef",
        )
    ]
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    monkeypatch.setattr(restore_packages, "collect_installed_packages", lambda: [])
    monkeypatch.setattr(restore_extensions, "probe_repository", lambda path: RepositoryProbe(path=path, is_git_repo=True, commit="123456", dirty=True))

    blocked = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="comfyui",
    )

    assert [blocker.code for blocker in blocked.blockers] == ["extension_dirty"]
    assert blocked.blockers[0].scope == "extension"
    assert blocked.blockers[0].target == "DemoNode"
    assert blocked.blockers[0].required_options == ["force_git_reset"]
    assert blocked.required_options == ["force_git_reset"]
    assert blocked.restorable is False
    assert blocked.extension_changes[0].diff.status == "blocked"
    assert blocked.diff_summary.extensions.blocked == 1

    forced = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="comfyui",
        options=restore_utils.SnapshotRestoreOptions(force_git_reset=True),
    )

    # 启用 required_options 指出的开关后, 同一份快照不再有阻断项。
    assert forced.blockers == []
    assert forced.required_options == []
    assert forced.restorable is True
    assert forced.extension_changes[0].diff.status == "modified"


def test_preview_restore_plan_keeps_comfyui_registry_extensions_when_pruning(monkeypatch, tmp_path):
    webui_path = tmp_path / "ComfyUI"
    custom_nodes = webui_path / "custom_nodes"
    registry_path = custom_nodes / ".disabled" / "registry-node"
    registry_path.mkdir(parents=True)
    (registry_path / ".tracking").write_text("pyproject.toml\n", encoding="utf-8")
    (registry_path / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "registry-node"',
                'version = "1.2.3"',
            ]
        ),
        encoding="utf-8",
    )
    (custom_nodes / "ExtraNode").mkdir()

    snapshot = make_webui_snapshot(webui_path)
    snapshot.webui.type = "comfyui"
    snapshot.extensions = [
        snapshot_utils.ExtensionSnapshot(
            name="registry-node",
            path=custom_nodes / "registry-node",
            enabled=False,
            is_git_repo=False,
            source_type="comfy-registry",
            registry_id="registry-node",
            registry_version="1.2.3",
        )
    ]
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    monkeypatch.setattr(restore_packages, "collect_installed_packages", lambda: [])

    plan = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="comfyui",
        options=restore_utils.SnapshotRestoreOptions(prune_extensions=True),
    )

    registry = next(item for item in plan.extension_changes if item.name == "registry-node")
    extra = next(item for item in plan.extension_changes if item.name == "ExtraNode")
    assert registry.registry_action == "skip_same_registry_version"
    assert registry.current_enabled is False
    assert registry.target_enabled is False
    assert extra.cleanup_action == "uninstall"
