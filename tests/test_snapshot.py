import argparse
import json
from datetime import datetime
from pathlib import Path

import pytest

from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryState
from sd_webui_all_in_one.base_manager import (
    comfy_registry,
    comfyui_base,
    fooocus_base,
    invokeai_base,
    qwen_tts_webui_base,
    sd_scripts_base,
    sd_trainer_base,
    sd_webui_base,
)
from sd_webui_all_in_one.base_manager import snapshot as snapshot_utils
from sd_webui_all_in_one.base_manager import snapshot_restore as restore_utils
from sd_webui_all_in_one.cli_manager import (
    comfyui_cli,
    fooocus_cli,
    invokeai_cli,
    qwen_tts_webui_cli,
    sd_scripts_cli,
    sd_trainer_cli,
    sd_webui_cli,
)
from sd_webui_all_in_one.base_manager.gui.snapshot_gui import (
    build_restore_blocking_guidance,
    format_restore_blocking_message,
    format_snapshot_timestamp,
    list_snapshot_files,
)
from sd_webui_all_in_one.cli_manager.snapshot import create_pre_operation_snapshot, output_snapshot


class FakeDistribution:
    def __init__(self, name: str, version: str, files: dict[str, str | None]) -> None:
        self.metadata = {"Name": name}
        self.version = version
        self.files = files

    def read_text(self, filename: str) -> str | None:
        return self.files.get(filename)


def _parser(register_func):
    parser = argparse.ArgumentParser(prog="sd-webui-all-in-one")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_func(subparsers)
    return parser


def _extension_snapshot(name: str, path: Path, enabled: bool | None) -> snapshot_utils.ExtensionSnapshot:
    return snapshot_utils.ExtensionSnapshot(
        name=name,
        path=path,
        enabled=enabled,
        is_git_repo=True,
        url=f"https://example.test/{name}",
        branch="main",
        commit="abcdef",
        dirty=False,
    )


def _webui_snapshot(path: Path) -> snapshot_utils.WebUiSnapshot:
    return snapshot_utils.WebUiSnapshot(
        schema_version=snapshot_utils.SNAPSHOT_SCHEMA_VERSION,
        created_at="2026-06-18T00:00:00Z",
        webui=snapshot_utils.WebUiIdentitySnapshot(name="Demo", type="demo", path=path),
        python=snapshot_utils.PythonSnapshot(
            version="3.11.0",
            implementation="CPython",
            executable=Path("/usr/bin/python"),
            platform="linux",
        ),
        system=snapshot_utils.SystemSnapshot(
            system="Linux",
            architecture="x86_64",
        ),
        kernel=snapshot_utils.RepositorySnapshot(
            path=path,
            name=path.name,
            is_git_repo=False,
            dirty=None,
        ),
    )


def _package_snapshot(
    name: str,
    version: str,
    direct_url: snapshot_utils.DirectUrlSnapshot | None = None,
    editable: bool = False,
) -> snapshot_utils.PackageSnapshot:
    return snapshot_utils.PackageSnapshot(
        name=name,
        version=version,
        editable=editable,
        direct_url=direct_url,
    )


def test_collect_installed_packages_reads_standard_source_metadata(monkeypatch):
    direct_url = {
        "url": "file:///workspace/demo",
        "dir_info": {
            "editable": True,
        },
    }
    git_url = {
        "url": "https://github.com/example/repo.git",
        "vcs_info": {
            "vcs": "git",
            "commit_id": "abcdef",
        },
    }
    distributions = [
        FakeDistribution(
            "demo-editable",
            "1.2.3",
            {
                "INSTALLER": "pip\n",
                "REQUESTED": "",
                "direct_url.json": json.dumps(direct_url),
                "WHEEL": "Generator: bdist_wheel\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
            },
        ),
        FakeDistribution(
            "demo-git",
            "0.1.0",
            {
                "direct_url.json": json.dumps(git_url),
            },
        ),
    ]
    monkeypatch.setattr(snapshot_utils.metadata, "distributions", lambda: distributions)

    packages = snapshot_utils.collect_installed_packages()

    assert packages[0].name == "demo-editable"
    assert packages[0].installer == "pip"
    assert packages[0].requested is True
    assert packages[0].editable is True
    assert packages[0].source_type == "local-directory"
    assert snapshot_utils.snapshot_to_dict(packages[0].direct_url) == direct_url
    assert snapshot_utils.snapshot_to_dict(packages[0].wheel) == {
        "generator": "bdist_wheel",
        "root_is_purelib": True,
        "tags": ["py3-none-any"],
    }
    assert packages[1].source_type == "vcs"
    assert packages[1].editable is False


def test_collect_system_info_records_system_and_architecture(monkeypatch):
    monkeypatch.setattr(snapshot_utils.platform, "system", lambda: "TestOS")
    monkeypatch.setattr(snapshot_utils.platform, "machine", lambda: "arm64")

    system = snapshot_utils.collect_system_info()

    assert system.system == "TestOS"
    assert system.architecture == "arm64"


def test_collect_repository_snapshot_includes_dirty_flag(monkeypatch, tmp_path):
    state = RepositoryState(
        path=tmp_path,
        is_git_repo=True,
        name="repo",
        url="https://github.com/example/repo",
        branch="main",
        commit="abcdef",
        commit_date="2026-06-18 00:00:00 +0000",
        message="snapshot",
    )
    monkeypatch.setattr(snapshot_utils, "inspect_repository", lambda _path: state)
    monkeypatch.setattr(snapshot_utils, "run_git_output", lambda _path, *args: " M file.py\n")

    data = snapshot_utils.collect_repository_snapshot(tmp_path)

    assert data.is_git_repo is True
    assert data.url == "https://github.com/example/repo"
    assert data.dirty is True


def test_collect_git_extensions_filters_non_git_directories(monkeypatch, tmp_path):
    ext_root = tmp_path / "extensions"
    (ext_root / "git-ext").mkdir(parents=True)
    (ext_root / "plain-ext").mkdir()
    (ext_root / "__pycache__").mkdir()
    (ext_root / "file.py").write_text("", encoding="utf-8")

    def fake_collect(path: Path) -> snapshot_utils.RepositorySnapshot:
        return snapshot_utils.RepositorySnapshot(
            path=path,
            name=path.name,
            is_git_repo=path.name == "git-ext",
            url=f"https://example.test/{path.name}",
            branch="main",
            commit="abcdef",
            dirty=False,
        )

    monkeypatch.setattr(snapshot_utils, "collect_repository_snapshot", fake_collect)

    extensions = snapshot_utils.collect_git_extensions(ext_root, enabled_resolver=lambda name, _path: name == "git-ext")

    assert [item.name for item in extensions] == ["git-ext"]
    assert extensions[0].enabled is True
    assert extensions[0].commit == "abcdef"


def test_load_comfyui_manager_snapshot_imports_registry_and_git_nodes(tmp_path):
    snapshot_path = tmp_path / "manager.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "comfyui": "kernel-commit",
                "git_custom_nodes": {
                    "https://github.com/example/git-node": {
                        "hash": "git-commit",
                        "disabled": True,
                    }
                },
                "cnr_custom_nodes": {
                    "registry-node": "1.2.3",
                },
                "file_custom_nodes": [
                    {
                        "filename": "single.py",
                        "disabled": False,
                    }
                ],
                "pips": {
                    "demo": "0.1.0",
                },
            }
        ),
        encoding="utf-8",
    )

    snapshot = snapshot_utils.load_snapshot(snapshot_path)

    assert snapshot.webui.type == "comfyui"
    assert snapshot.kernel is not None
    assert snapshot.kernel.commit == "kernel-commit"
    assert [(item.name, item.source_type, item.enabled) for item in snapshot.extensions] == [
        ("git-node", "git", False),
        ("registry-node", "comfy-registry", True),
        ("single.py", "file", True),
    ]
    assert snapshot.extensions[1].registry_id == "registry-node"
    assert snapshot.extensions[1].registry_version == "1.2.3"
    assert snapshot.packages[0].name == "demo"


def test_product_snapshots_include_webui_identity_and_extension_state(monkeypatch, tmp_path):
    (tmp_path / "sd-webui" / "extensions").mkdir(parents=True)
    (tmp_path / "sd-webui" / "config.json").write_text(json.dumps({"disabled_extensions": ["disabled-ext"]}), encoding="utf-8")

    def fake_sd_extensions(_path, enabled_resolver=None, **_kwargs):
        return [
            _extension_snapshot("enabled-ext", _path / "enabled-ext", enabled_resolver("enabled-ext", _path / "enabled-ext")),
            _extension_snapshot("disabled-ext", _path / "disabled-ext", enabled_resolver("disabled-ext", _path / "disabled-ext")),
        ]

    monkeypatch.setattr(sd_webui_base, "collect_git_extensions", fake_sd_extensions)
    sd_snapshot = sd_webui_base.get_sd_webui_snapshot(tmp_path / "sd-webui", include_packages=False)
    assert snapshot_utils.snapshot_to_dict(sd_snapshot)["webui"] == {
        "name": "Stable Diffusion WebUI",
        "type": "sd_webui",
        "path": (tmp_path / "sd-webui").as_posix(),
    }
    assert snapshot_utils.snapshot_to_dict(sd_snapshot)["system"] == snapshot_utils.snapshot_to_dict(
        snapshot_utils.collect_system_info()
    )
    assert [item.enabled for item in sd_snapshot.extensions] == [True, False]

    monkeypatch.setattr(
        comfyui_base,
        "collect_comfyui_extensions",
        lambda _path: [_extension_snapshot("node.disabled", _path / "custom_nodes" / "node.disabled", False)],
    )
    comfy_snapshot = comfyui_base.get_comfyui_snapshot(tmp_path / "ComfyUI", include_packages=False)
    assert comfy_snapshot.webui.type == "comfyui"
    assert comfy_snapshot.extensions[0].enabled is False

    monkeypatch.setattr(
        invokeai_base,
        "collect_git_extensions",
        lambda _path, enabled_resolver=None, **_kwargs: [_extension_snapshot("node", _path / "node", enabled_resolver("node", _path / "node"))],
    )
    (tmp_path / "InvokeAI" / "nodes" / "node").mkdir(parents=True)
    (tmp_path / "InvokeAI" / "nodes" / "node" / "__init__.py").write_text("", encoding="utf-8")
    invoke_snapshot = invokeai_base.get_invokeai_snapshot(tmp_path / "InvokeAI", include_packages=False)
    assert invoke_snapshot.webui.type == "invokeai"
    assert invoke_snapshot.extensions[0].enabled is True

    assert fooocus_base.get_fooocus_snapshot(tmp_path / "Fooocus", include_packages=False).webui.type == "fooocus"
    assert qwen_tts_webui_base.get_qwen_tts_webui_snapshot(tmp_path / "qwen", include_packages=False).webui.type == "qwen_tts_webui"
    assert sd_trainer_base.get_sd_trainer_snapshot(tmp_path / "trainer", include_packages=False).webui.type == "sd_trainer"
    assert sd_scripts_base.get_sd_scripts_snapshot(tmp_path / "scripts", include_packages=False).webui.type == "sd_scripts"


def test_output_snapshot_writes_default_or_explicit_directory(monkeypatch, tmp_path):
    snapshot = _webui_snapshot(tmp_path / "demo")
    snapshot_json = snapshot_utils.snapshot_to_dict(snapshot)
    default_dir = tmp_path / "snapshots"
    default_file = default_dir / "demo-2026-06-18T000000Z.json"

    monkeypatch.setattr(snapshot_utils, "SD_WEBUI_ALL_IN_ONE_SNAPSHOT_DIR", default_dir)

    assert output_snapshot(lambda: snapshot) == default_file
    assert json.loads(default_file.read_text(encoding="utf-8")) == snapshot_json

    output_dir = tmp_path / "custom-snapshots"
    output_file = output_dir / "demo-2026-06-18T000000Z.json"
    assert output_snapshot(lambda: snapshot, output=output_dir) == output_file
    assert json.loads(output_file.read_text(encoding="utf-8")) == snapshot_json


def test_create_pre_operation_snapshot_writes_to_directory(tmp_path):
    snapshot = _webui_snapshot(tmp_path / "demo")
    output_dir = tmp_path / "pre-operation-snapshots"
    output_file = output_dir / "demo-2026-06-18T000000Z.json"

    assert create_pre_operation_snapshot(lambda: snapshot, "update demo", snapshot_dir=output_dir) == output_file
    assert json.loads(output_file.read_text(encoding="utf-8")) == snapshot_utils.snapshot_to_dict(snapshot)


def test_create_pre_operation_snapshot_failure_or_disabled_does_not_raise(tmp_path):
    called = False

    def disabled_factory():
        nonlocal called
        called = True
        raise AssertionError("disabled snapshot should not call factory")

    def failing_factory():
        raise RuntimeError("boom")

    assert create_pre_operation_snapshot(disabled_factory, "disabled demo", snapshot_enabled=False, snapshot_dir=tmp_path) is None
    assert called is False
    assert create_pre_operation_snapshot(failing_factory, "failing demo", snapshot_dir=tmp_path) is None


def test_format_snapshot_timestamp_uses_local_time_and_keeps_invalid_values():
    local_timestamp = datetime.fromisoformat("2026-06-18T00:00:00+00:00").astimezone()
    suffix = local_timestamp.strftime("%Z") or local_timestamp.strftime("%z")
    expected = f"{local_timestamp:%Y-%m-%d %H:%M:%S}{f' {suffix}' if suffix else ''}"

    assert format_snapshot_timestamp("2026-06-18T00:00:00Z") == expected
    assert format_snapshot_timestamp("not-a-timestamp") == "not-a-timestamp"


def test_list_snapshot_files_reads_valid_snapshots_sorted_by_created_at(tmp_path):
    old_snapshot = _webui_snapshot(tmp_path / "old")
    old_snapshot.created_at = "2026-06-17T00:00:00Z"
    old_snapshot.packages = [_package_snapshot("old", "1.0.0")]
    old_path = snapshot_utils.save_snapshot(old_snapshot, tmp_path / "old.json")

    new_snapshot = _webui_snapshot(tmp_path / "new")
    new_snapshot.created_at = "2026-06-18T00:00:00Z"
    new_snapshot.extensions = [_extension_snapshot("ext", tmp_path / "new" / "extensions" / "ext", True)]
    new_path = snapshot_utils.save_snapshot(new_snapshot, tmp_path / "new.json")
    (tmp_path / "invalid.json").write_text("{", encoding="utf-8")
    (tmp_path / "note.txt").write_text("not a snapshot", encoding="utf-8")

    items = list_snapshot_files(tmp_path)

    assert [item.path for item in items] == [new_path, old_path]
    assert items[0].filename == "new.json"
    assert items[0].created_at == "2026-06-18T00:00:00Z"
    assert items[0].created_at_display == format_snapshot_timestamp("2026-06-18T00:00:00Z")
    assert items[0].webui_name == "Demo"
    assert items[0].webui_type == "demo"
    assert items[0].package_count == 0
    assert items[0].extension_count == 1
    assert items[1].package_count == 1


def test_list_snapshot_files_keeps_invalid_timestamp_display(tmp_path):
    snapshot = _webui_snapshot(tmp_path / "invalid-time")
    snapshot.created_at = "invalid-time"
    path = snapshot_utils.save_snapshot(snapshot, tmp_path / "invalid-time.json")

    items = list_snapshot_files(tmp_path)

    assert len(items) == 1
    assert items[0].path == path
    assert items[0].created_at == "invalid-time"
    assert items[0].created_at_display == "invalid-time"


def test_list_snapshot_files_returns_empty_for_missing_directory(tmp_path):
    assert list_snapshot_files(tmp_path / "missing") == []


def test_load_snapshot_roundtrip_and_rejects_unsupported_schema(tmp_path):
    local_source = tmp_path / "local-package"
    local_source.mkdir()
    snapshot = _webui_snapshot(tmp_path / "demo")
    snapshot.packages = [
        snapshot_utils.PackageSnapshot(
            name="demo-editable",
            version="1.2.3",
            installer="pip",
            requested=True,
            editable=True,
            direct_url=snapshot_utils.DirectUrlSnapshot(
                url=local_source.as_uri(),
                dir_info=snapshot_utils.DirectUrlDirInfo(editable=True),
            ),
            source_type="local-directory",
            wheel=snapshot_utils.WheelSnapshot(generator="bdist_wheel", root_is_purelib=True, tags=["py3-none-any"]),
        )
    ]
    snapshot.extensions = [_extension_snapshot("ext", tmp_path / "demo" / "extensions" / "ext", True)]

    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    loaded = snapshot_utils.load_snapshot(output)

    assert snapshot_utils.snapshot_to_dict(loaded) == snapshot_utils.snapshot_to_dict(snapshot)

    unsupported = tmp_path / "unsupported.json"
    unsupported.write_text(json.dumps({"schema_version": 999}), encoding="utf-8")
    with pytest.raises(ValueError, match="不支持的快照结构版本"):
        snapshot_utils.load_snapshot(unsupported)


def test_load_legacy_snapshot_without_system_field_uses_current_system(monkeypatch, tmp_path):
    snapshot = _webui_snapshot(tmp_path / "demo")
    snapshot_data = snapshot_utils.snapshot_to_dict(snapshot)
    assert isinstance(snapshot_data, dict)
    snapshot_data.pop("system")
    output = tmp_path / "legacy.json"
    output.write_text(json.dumps(snapshot_data), encoding="utf-8")
    monkeypatch.setattr(snapshot_utils, "collect_system_info", lambda: snapshot_utils.SystemSnapshot(system="CurrentOS", architecture="riscv64"))

    loaded = snapshot_utils.load_snapshot(output)

    assert loaded.system == snapshot_utils.SystemSnapshot(system="CurrentOS", architecture="riscv64")


def test_restore_webui_snapshot_rejects_mismatched_webui_type(monkeypatch, tmp_path):
    snapshot = _webui_snapshot(tmp_path / "demo")
    snapshot.webui.type = "sd_webui"
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    def fail_restore(*_args, **_kwargs):
        raise AssertionError("restore should not run for mismatched snapshots")

    monkeypatch.setattr(restore_utils, "restore_python_packages", fail_restore)

    with pytest.raises(ValueError, match="快照 WebUI 类型不匹配"):
        restore_utils.restore_webui_snapshot(
            snapshot_path=output,
            webui_path=tmp_path / "ComfyUI",
            expected_webui_type="comfyui",
        )


def test_restore_webui_snapshot_rejects_missing_kernel_before_package_restore(monkeypatch, tmp_path):
    webui_path = tmp_path / "demo"
    snapshot = _webui_snapshot(webui_path)
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    def fail_restore(*_args, **_kwargs):
        raise AssertionError("package restore should not run when kernel directory is missing")

    monkeypatch.setattr(restore_utils, "restore_python_packages", fail_restore)

    with pytest.raises(FileNotFoundError, match="内核目录不存在"):
        restore_utils.restore_webui_snapshot(
            snapshot_path=output,
            webui_path=webui_path,
            expected_webui_type="demo",
        )


def test_restore_webui_snapshot_allows_missing_path_for_package_kernel_webui(monkeypatch, tmp_path):
    webui_path = tmp_path / "invokeai"
    snapshot = _webui_snapshot(webui_path)
    snapshot.webui.type = "invokeai"
    snapshot.webui.name = "InvokeAI"
    snapshot.kernel = snapshot_utils.RepositorySnapshot(
        path=webui_path,
        name="invokeai",
        is_git_repo=True,
        url="https://example.test/invokeai-root.git",
        commit="abcdef",
    )
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    events = []
    monkeypatch.setattr(restore_utils, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(restore_utils, "restore_python_packages", lambda snapshot, options: events.append(("packages", snapshot.webui.type)))
    monkeypatch.setattr(
        restore_utils,
        "restore_git_repository",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("package-kernel WebUI should not restore Git kernel")),
    )
    monkeypatch.setattr(restore_utils, "restore_extensions", lambda snapshot, webui_path, options: events.append(("extensions", webui_path)))

    restore_utils.restore_webui_snapshot(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="invokeai",
    )

    assert events == [("packages", "invokeai"), ("extensions", webui_path)]


def test_preview_restore_plan_reports_package_actions_and_pytorch_source(monkeypatch, tmp_path):
    missing_local = tmp_path / "missing-local"
    webui_path = tmp_path / "demo"
    webui_path.mkdir()
    snapshot = _webui_snapshot(webui_path)
    snapshot.packages = [
        _package_snapshot("sd-webui-all-in-one", "99.0.0"),
        _package_snapshot("Torch", "2.7.0+cu128"),
        _package_snapshot("demo-pkg", "2.0.0"),
        _package_snapshot(
            "editable-local",
            "1.0.0",
            direct_url=snapshot_utils.DirectUrlSnapshot(
                url=missing_local.as_uri(),
                dir_info=snapshot_utils.DirectUrlDirInfo(editable=True),
            ),
            editable=True,
        ),
        _package_snapshot("already", "1.0.0"),
    ]
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    monkeypatch.setattr(
        restore_utils,
        "collect_installed_packages",
        lambda: [
            _package_snapshot("demo_pkg", "1.0.0"),
            _package_snapshot("already", "1.0.0"),
            _package_snapshot("old-pkg", "0.1.0"),
            _package_snapshot("pip", "25.0"),
        ],
    )
    monkeypatch.setattr(restore_utils, "get_pytorch_mirror", lambda dtype, use_cn_mirror: ("https://torch.example/cu128", "index_url"))

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
    assert plan.errors == []


@pytest.mark.parametrize(
    ("platform_tag", "torch_version", "expected_dtype", "expected_url"),
    [
        ("win32", "2.9.0+rocm9.0", "rocm_win", "https://torch.example/rocm-win"),
        ("win32", "2.9.0+rocm6.4", "rocm_win", "https://torch.example/rocm-win"),
        ("linux", "2.9.0+rocm6.4", "rocm6.4", "https://torch.example/rocm64"),
        ("linux", "2.9.0+rocm9.0", None, None),
    ],
)
def test_preview_restore_plan_normalizes_rocm_pytorch_suffix(monkeypatch, tmp_path, platform_tag, torch_version, expected_dtype, expected_url):
    webui_path = tmp_path / "demo"
    webui_path.mkdir()
    snapshot = _webui_snapshot(webui_path)
    snapshot.packages = [_package_snapshot("Torch", torch_version)]
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    mirror_by_dtype = {
        "rocm_win": ("https://torch.example/rocm-win", "find_links"),
        "rocm6.4": ("https://torch.example/rocm64", "index_url"),
    }
    mirror_calls = []

    def fake_get_pytorch_mirror(dtype, use_cn_mirror):
        mirror_calls.append((dtype, use_cn_mirror))
        return mirror_by_dtype[dtype]

    monkeypatch.setattr(restore_utils.sys, "platform", platform_tag)
    monkeypatch.setattr(restore_utils, "collect_installed_packages", lambda: [])
    monkeypatch.setattr(restore_utils, "get_pytorch_mirror", fake_get_pytorch_mirror)

    plan = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="demo",
        options=restore_utils.SnapshotRestoreOptions(use_pypi_mirror=True),
    )

    assert plan.pytorch_device_type == expected_dtype
    assert plan.pytorch_mirror_url == expected_url
    if expected_dtype is None:
        assert mirror_calls == []
        assert plan.warnings == ["未从 PyTorch 包版本推断出特殊源, 将使用普通 PyPI 源"]
    else:
        assert mirror_calls == [(expected_dtype, True)]
        assert plan.warnings == []


def test_preview_restore_plan_blocks_dirty_kernel_without_force(monkeypatch, tmp_path):
    snapshot = _webui_snapshot(tmp_path / "demo")
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

    monkeypatch.setattr(restore_utils, "collect_installed_packages", lambda: [])
    monkeypatch.setattr(restore_utils.git_warpper, "is_git_repo", lambda _path: True)
    monkeypatch.setattr(restore_utils, "repository_dirty", lambda _path, _include_untracked: True)
    monkeypatch.setattr(restore_utils.git_warpper, "get_current_commit", lambda _path: "123456")

    blocked = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=tmp_path / "demo",
        expected_webui_type="demo",
    )

    assert blocked.kernel_change is not None
    assert blocked.kernel_change.action == "blocked_dirty"
    assert blocked.errors == ["内核仓库存在未提交变更"]
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
    assert forced.errors == []


def test_restore_blocking_guidance_explains_webui_type_mismatch(tmp_path):
    snapshot = _webui_snapshot(tmp_path / "demo")
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    plan = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=tmp_path / "demo",
        expected_webui_type="other_webui",
    )

    guidance = "\n".join(build_restore_blocking_guidance(plan))

    assert plan.errors == ["快照 WebUI 类型不匹配: 期望 'other_webui', 实际 'demo'"]
    assert "对应的快照管理器" in guidance
    assert "跨 WebUI 类型恢复会被终止" in guidance


def test_preview_restore_plan_blocks_missing_kernel_with_guidance(tmp_path):
    webui_path = tmp_path / "demo"
    snapshot = _webui_snapshot(webui_path)
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
    assert plan.errors == [f"内核目录不存在: {webui_path}"]
    assert "通过 installer 准备对应的 WebUI kernel" in guidance
    assert "不能通过强制恢复开关绕过" in guidance


def test_preview_restore_plan_allows_missing_path_for_package_kernel_webui(monkeypatch, tmp_path):
    webui_path = tmp_path / "invokeai"
    snapshot = _webui_snapshot(webui_path)
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
    monkeypatch.setattr(restore_utils, "collect_installed_packages", lambda: [])

    plan = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="invokeai",
    )

    assert plan.errors == []
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
    snapshot = _webui_snapshot(webui_path)
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

    monkeypatch.setattr(restore_utils, "collect_installed_packages", lambda: [])
    monkeypatch.setattr(restore_utils.git_warpper, "is_git_repo", lambda _path: True)
    monkeypatch.setattr(restore_utils, "repository_dirty", lambda _path, _include_untracked: False)
    monkeypatch.setattr(restore_utils.git_warpper, "get_current_commit", lambda _path: "123456")

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

    snapshot = _webui_snapshot(webui_path)
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

    monkeypatch.setattr(restore_utils, "collect_installed_packages", lambda: [])

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


def test_restore_python_packages_prioritizes_pytorch_skips_missing_local_and_prunes(monkeypatch, tmp_path):
    missing_local = tmp_path / "missing-local"
    existing_local = tmp_path / "existing-local"
    existing_local.mkdir()
    snapshot = _webui_snapshot(tmp_path / "demo")
    snapshot.packages = [
        _package_snapshot("sd-webui-all-in-one", "99.0.0"),
        _package_snapshot("Torch", "2.7.0+cu128"),
        _package_snapshot("torchvision", "0.22.0+cu128"),
        _package_snapshot("demo-pkg", "2.0.0"),
        _package_snapshot("other-pkg", "3.0.0"),
        _package_snapshot(
            "editable-existing",
            "1.0.0",
            direct_url=snapshot_utils.DirectUrlSnapshot(
                url=existing_local.as_uri(),
                dir_info=snapshot_utils.DirectUrlDirInfo(editable=True),
            ),
            editable=True,
        ),
        _package_snapshot(
            "editable-local",
            "1.0.0",
            direct_url=snapshot_utils.DirectUrlSnapshot(
                url=missing_local.as_uri(),
                dir_info=snapshot_utils.DirectUrlDirInfo(editable=True),
            ),
            editable=True,
        ),
        _package_snapshot("already", "1.0.0"),
    ]

    monkeypatch.setattr(
        restore_utils,
        "collect_installed_packages",
        lambda: [
            _package_snapshot("demo_pkg", "1.0.0"),
            _package_snapshot("already", "1.0.0"),
            _package_snapshot("old_pkg", "0.1.0"),
            _package_snapshot("pip", "25.0"),
            _package_snapshot("sd-webui-all-in-one", "1.0.0"),
        ],
    )
    monkeypatch.setattr(restore_utils, "get_pypi_mirror_config", lambda use_cn_mirror: {"PIP_INDEX_URL": "https://pypi.example"})

    mirror_calls = []
    env_calls = []
    events = []

    def fake_get_pytorch_mirror(dtype, use_cn_mirror):
        mirror_calls.append((dtype, use_cn_mirror))
        return "https://torch.example/cu128", "index_url"

    def fake_generate_env(index_url=None, extra_index_url=None, find_links=None):
        env_calls.append(
            {
                "index_url": index_url,
                "extra_index_url": extra_index_url,
                "find_links": find_links,
            }
        )
        return {"TORCH_INDEX": str(index_url)}

    def fake_install_pytorch_with_fallback(**kwargs):
        events.append(("pytorch", kwargs))

    def fake_pip_install(*args, **kwargs):
        events.append(("pip", args, kwargs))

    def fake_run_cmd(cmd, **_kwargs):
        events.append(("uninstall", cmd))

    monkeypatch.setattr(restore_utils, "get_pytorch_mirror", fake_get_pytorch_mirror)
    monkeypatch.setattr(restore_utils, "generate_uv_and_pip_env_mirror_config", fake_generate_env)
    monkeypatch.setattr(restore_utils, "install_pytorch_with_fallback", fake_install_pytorch_with_fallback)
    monkeypatch.setattr(restore_utils, "pip_install", fake_pip_install)
    monkeypatch.setattr(restore_utils, "run_cmd", fake_run_cmd)

    restore_utils.restore_python_packages(
        snapshot,
        restore_utils.SnapshotRestoreOptions(prune_packages=True, use_uv=False, use_pypi_mirror=True),
    )

    assert mirror_calls == [("cu128", True)]
    assert env_calls == [
        {
            "index_url": "https://torch.example/cu128",
            "extra_index_url": [],
            "find_links": [],
        }
    ]
    assert events[0][0] == "pytorch"
    assert events[0][1]["torch_package"] == ["Torch==2.7.0+cu128", "torchvision==0.22.0+cu128", "--no-deps"]
    assert events[0][1]["xformers_package"] is None
    assert events[0][1]["use_uv"] is False
    pip_events = [event for event in events if event[0] == "pip"]
    assert pip_events == [
        (
            "pip",
            (
                "demo-pkg==2.0.0",
                "other-pkg==3.0.0",
                "-e",
                existing_local.as_posix(),
                "--no-deps",
            ),
            {"use_uv": False, "custom_env": {"PIP_INDEX_URL": "https://pypi.example"}},
        )
    ]
    assert not any(event[0] == "pip" and "editable-local" in event[1][0] for event in events)
    assert not any(event[0] == "pip" and "sd-webui-all-in-one" in event[1][0] for event in events)
    assert events[-1][0] == "uninstall"
    uninstall_names = events[-1][1][4:-1]
    assert uninstall_names == ["old_pkg"]


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

    monkeypatch.setattr(restore_utils.git_warpper, "is_git_repo", lambda _path: True)
    monkeypatch.setattr(restore_utils, "repository_dirty", lambda _path, _include_untracked: True)

    with pytest.raises(RuntimeError, match="存在未提交变更"):
        restore_utils.restore_git_repository(repo, target, restore_utils.SnapshotRestoreOptions())

    calls = []
    monkeypatch.setattr(restore_utils, "fetch_repository", lambda path: calls.append(("fetch", path)))
    monkeypatch.setattr(restore_utils.git_warpper, "switch_commit", lambda path, commit: calls.append(("switch", path, commit)))

    restored = restore_utils.restore_git_repository(
        repo,
        target,
        restore_utils.SnapshotRestoreOptions(force_git_reset=True),
    )

    assert restored is True
    assert calls == [("fetch", target), ("switch", target, "abcdef")]


def test_restore_extensions_sets_status_and_prunes_with_comfyui_name_normalization(monkeypatch, tmp_path):
    webui_path = tmp_path / "ComfyUI"
    custom_nodes = webui_path / "custom_nodes"
    (custom_nodes / "KeepNode.disabled").mkdir(parents=True)
    (custom_nodes / "ExtraNode.disabled").mkdir()
    (custom_nodes / "__pycache__").mkdir()
    (custom_nodes / "README.md").write_text("", encoding="utf-8")

    snapshot = _webui_snapshot(webui_path)
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
        restore_utils,
        "_extension_tools",
        lambda _type: restore_utils.ExtensionRestoreTools(
            directory_name="custom_nodes",
            set_status=lambda path, name, enabled: statuses.append((path, name, enabled)),
            uninstall=lambda path, name: removed.append((path, name)),
            strip_disabled_suffix=True,
        ),
    )
    monkeypatch.setattr(
        restore_utils,
        "restore_git_repository",
        lambda repo, target_path, options: restored.append((repo.name, target_path, options.prune_extensions)) or True,
    )

    restore_utils.restore_extensions(
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
    snapshot = _webui_snapshot(webui_path)
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
        restore_utils,
        "_extension_tools",
        lambda _type: restore_utils.ExtensionRestoreTools(
            directory_name="custom_nodes",
            set_status=lambda path, name, enabled: statuses.append((path, name, enabled)),
            uninstall=lambda path, name: None,
            strip_disabled_suffix=True,
        ),
    )
    monkeypatch.setattr(
        restore_utils,
        "restore_comfy_registry_extension",
        lambda extension, webui_path, options: restored.append((extension.registry_id, extension.registry_version, webui_path, options.use_uv)) or True,
    )

    restore_utils.restore_extensions(snapshot, webui_path, restore_utils.SnapshotRestoreOptions(use_uv=False))

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


def test_product_snapshot_cli_parse_smoke(monkeypatch, tmp_path):
    cases = [
        (sd_webui_cli, sd_webui_cli.register_sd_webui, "sd-webui", "--sd-webui-path", "sd_webui_path"),
        (comfyui_cli, comfyui_cli.register_comfyui, "comfyui", "--comfyui-path", "comfyui_path"),
        (fooocus_cli, fooocus_cli.register_fooocus, "fooocus", "--fooocus-path", "fooocus_path"),
        (invokeai_cli, invokeai_cli.register_invokeai, "invokeai", "--invokeai-path", "invokeai_path"),
        (qwen_tts_webui_cli, qwen_tts_webui_cli.register_qwen_tts_webui, "qwen-tts-webui", "--qwen-tts-webui-path", "qwen_tts_webui_path"),
        (sd_trainer_cli, sd_trainer_cli.register_sd_trainer, "sd-trainer", "--sd-trainer-path", "sd_trainer_path"),
        (sd_scripts_cli, sd_scripts_cli.register_sd_scripts, "sd-scripts", "--sd-scripts-path", "sd_scripts_path"),
    ]

    for module, register, command, path_arg, path_key in cases:
        parser = _parser(register)
        calls = []
        monkeypatch.setattr(module, "snapshot", lambda **kwargs: calls.append(kwargs))

        args = parser.parse_args(
            [
                command,
                "snapshot",
                path_arg,
                str(tmp_path / command),
                "--output",
                str(tmp_path / f"{command}-snapshots"),
                "--no-packages",
            ]
        )
        args.func(args)

        assert calls == [
            {
                path_key: tmp_path / command,
                "output": tmp_path / f"{command}-snapshots",
                "include_packages": False,
            }
        ]

        restore_calls = []
        monkeypatch.setattr(module, "restore", lambda **kwargs: restore_calls.append(kwargs))
        args = parser.parse_args(
            [
                command,
                "restore",
                str(tmp_path / "snapshot.json"),
                path_arg,
                str(tmp_path / command),
                "--prune-packages",
                "--prune-extensions",
                "--force-git-reset",
                "--no-uv",
                "--no-pypi-mirror",
                "--no-github-mirror",
                "--custom-github-mirror",
                "https://mirror.example",
                "--no-auto-mirror",
            ]
        )
        args.func(args)

        assert restore_calls == [
            {
                "snapshot_path": tmp_path / "snapshot.json",
                path_key: tmp_path / command,
                "prune_packages": True,
                "prune_extensions": True,
                "force_git_reset": True,
                "use_uv": False,
                "use_pypi_mirror": False,
                "use_github_mirror": False,
                "custom_github_mirror": "https://mirror.example",
            }
        ]

        gui_calls = []
        monkeypatch.setattr(module, "launch_snapshot_gui", lambda **kwargs: gui_calls.append(kwargs))
        args = parser.parse_args(
            [
                command,
                "gui",
                "snapshot-manager",
                path_arg,
                str(tmp_path / command),
                "--snapshot-dir",
                str(tmp_path / "gui-snapshots"),
                "--no-uv",
                "--no-pypi-mirror",
                "--no-github-mirror",
                "--custom-github-mirror",
                "https://mirror.example",
                "--no-auto-mirror",
            ]
        )
        args.func(args)

        assert gui_calls == [
            {
                path_key: tmp_path / command,
                "snapshot_dir": tmp_path / "gui-snapshots",
                "use_uv": False,
                "use_pypi_mirror": False,
                "use_github_mirror": False,
                "custom_github_mirror": "https://mirror.example",
            }
        ]
