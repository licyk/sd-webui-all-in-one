import argparse
import json
from pathlib import Path

import pytest

from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryState
from sd_webui_all_in_one.base_manager import (
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
from sd_webui_all_in_one.cli_manager.snapshot import output_snapshot


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
    assert [item.enabled for item in sd_snapshot.extensions] == [True, False]

    monkeypatch.setattr(
        comfyui_base,
        "collect_git_extensions",
        lambda _path, enabled_resolver=None, **_kwargs: [
            _extension_snapshot("node.disabled", _path / "node.disabled", enabled_resolver("node.disabled", _path / "node.disabled"))
        ],
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


def test_preview_restore_plan_reports_package_actions_and_pytorch_source(monkeypatch, tmp_path):
    missing_local = tmp_path / "missing-local"
    snapshot = _webui_snapshot(tmp_path / "demo")
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
        webui_path=tmp_path / "demo",
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

    forced = restore_utils.preview_webui_snapshot_restore(
        snapshot_path=output,
        webui_path=tmp_path / "demo",
        expected_webui_type="demo",
        options=restore_utils.SnapshotRestoreOptions(force_git_reset=True),
    )

    assert forced.kernel_change is not None
    assert forced.kernel_change.action == "switch_commit"
    assert forced.errors == []


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


def test_restore_python_packages_prioritizes_pytorch_skips_missing_local_and_prunes(monkeypatch, tmp_path):
    missing_local = tmp_path / "missing-local"
    snapshot = _webui_snapshot(tmp_path / "demo")
    snapshot.packages = [
        _package_snapshot("sd-webui-all-in-one", "99.0.0"),
        _package_snapshot("Torch", "2.7.0+cu128"),
        _package_snapshot("torchvision", "0.22.0+cu128"),
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
    assert events[0][1]["torch_package"] == ["Torch==2.7.0+cu128", "torchvision==0.22.0+cu128"]
    assert events[0][1]["xformers_package"] is None
    assert events[0][1]["use_uv"] is False
    assert ("pip", ("demo-pkg==2.0.0",), {"use_uv": False, "custom_env": {"PIP_INDEX_URL": "https://pypi.example"}}) in events
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
                "use_uv": False,
                "use_pypi_mirror": False,
                "use_github_mirror": False,
                "custom_github_mirror": "https://mirror.example",
            }
        ]
