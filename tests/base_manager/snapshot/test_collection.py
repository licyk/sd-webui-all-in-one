"""环境快照信息采集测试"""

import json
import sys
from pathlib import Path

from sd_webui_all_in_one.base_manager import (
    comfyui_base,
    fooocus_base,
    invokeai_base,
    mizuoto_tts_webui_base,
    qwen_tts_webui_base,
    rvc_next_webui_base,
    sd_scripts_base,
    sd_trainer_base,
    sd_webui_base,
)
from sd_webui_all_in_one.base_manager import snapshot as snapshot_utils
from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryState
from sd_webui_all_in_one.base_manager.snapshot import collection as snapshot_collection
from tests.base_manager.snapshot.helpers import make_extension_snapshot


class FakeDistribution:
    def __init__(self, name: str, version: str, files: dict[str, str | None]) -> None:
        self.metadata = {"Name": name}
        self.version = version
        self.files = files

    def read_text(self, filename: str) -> str | None:
        return self.files.get(filename)


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
    monkeypatch.setattr(snapshot_collection.metadata, "distributions", lambda: distributions)

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
    monkeypatch.setattr(snapshot_collection.platform, "system", lambda: "TestOS")
    monkeypatch.setattr(snapshot_collection.platform, "machine", lambda: "arm64")

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
    monkeypatch.setattr(snapshot_collection, "inspect_repository", lambda _path: state)
    monkeypatch.setattr(snapshot_collection, "run_git_output", lambda _path, *args: " M file.py\n")

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

    monkeypatch.setattr(snapshot_collection, "collect_repository_snapshot", fake_collect)

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
            make_extension_snapshot(
                "enabled-ext",
                _path / "enabled-ext",
                enabled_resolver("enabled-ext", _path / "enabled-ext"),
            ),
            make_extension_snapshot(
                "disabled-ext",
                _path / "disabled-ext",
                enabled_resolver("disabled-ext", _path / "disabled-ext"),
            ),
        ]

    monkeypatch.setattr(sys.modules[sd_webui_base.get_sd_webui_snapshot.__module__], "collect_git_extensions", fake_sd_extensions)
    sd_snapshot = sd_webui_base.get_sd_webui_snapshot(tmp_path / "sd-webui", include_packages=False)
    assert snapshot_utils.snapshot_to_dict(sd_snapshot)["webui"] == {
        "name": "Stable Diffusion WebUI",
        "type": "sd_webui",
        "path": (tmp_path / "sd-webui").as_posix(),
    }
    assert snapshot_utils.snapshot_to_dict(sd_snapshot)["system"] == snapshot_utils.snapshot_to_dict(snapshot_utils.collect_system_info())
    assert [item.enabled for item in sd_snapshot.extensions] == [True, False]

    monkeypatch.setattr(
        sys.modules[comfyui_base.get_comfyui_snapshot.__module__],
        "collect_comfyui_extensions",
        lambda _path: [make_extension_snapshot("node.disabled", _path / "custom_nodes" / "node.disabled", False)],
    )
    comfy_snapshot = comfyui_base.get_comfyui_snapshot(tmp_path / "ComfyUI", include_packages=False)
    assert comfy_snapshot.webui.type == "comfyui"
    assert comfy_snapshot.extensions[0].enabled is False

    monkeypatch.setattr(
        sys.modules[invokeai_base.get_invokeai_snapshot.__module__],
        "collect_git_extensions",
        lambda _path, enabled_resolver=None, **_kwargs: [make_extension_snapshot("node", _path / "node", enabled_resolver("node", _path / "node"))],
    )
    (tmp_path / "InvokeAI" / "nodes" / "node").mkdir(parents=True)
    (tmp_path / "InvokeAI" / "nodes" / "node" / "__init__.py").write_text("", encoding="utf-8")
    invoke_snapshot = invokeai_base.get_invokeai_snapshot(tmp_path / "InvokeAI", include_packages=False)
    assert invoke_snapshot.webui.type == "invokeai"
    assert invoke_snapshot.extensions[0].enabled is True

    assert fooocus_base.get_fooocus_snapshot(tmp_path / "Fooocus", include_packages=False).webui.type == "fooocus"
    assert qwen_tts_webui_base.get_qwen_tts_webui_snapshot(tmp_path / "qwen", include_packages=False).webui.type == "qwen_tts_webui"
    assert rvc_next_webui_base.get_rvc_next_webui_snapshot(tmp_path / "rvc", include_packages=False).webui.type == "rvc_next_webui"
    assert mizuoto_tts_webui_base.get_mizuoto_tts_webui_snapshot(tmp_path / "mizuoto", include_packages=False).webui.type == "mizuoto_tts_webui"
    assert sd_trainer_base.get_sd_trainer_snapshot(tmp_path / "trainer", include_packages=False).webui.type == "sd_trainer"
    assert sd_scripts_base.get_sd_scripts_snapshot(tmp_path / "scripts", include_packages=False).webui.type == "sd_scripts"


def test_distribution_name_version_fast_path_matches_importlib_metadata():
    from importlib import metadata

    distributions = list(metadata.distributions())
    assert distributions

    for dist in distributions:
        expected_name = dist.metadata["Name"]
        if not expected_name:
            continue
        assert snapshot_collection._distribution_name_version(dist) == (expected_name, dist.version)


def test_distribution_name_version_reads_only_metadata_header(tmp_path):
    from importlib import metadata

    dist_info = tmp_path / "demo-1.0.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: Demo.Pkg\nVersion: 1.0+local\nSummary: demo\n\nName: not-a-header\nVersion: 9.9\n",
        encoding="utf-8",
    )

    assert snapshot_collection._distribution_name_version(metadata.PathDistribution(dist_info)) == ("Demo.Pkg", "1.0+local")


def test_collect_repository_snapshots_preserves_input_order(monkeypatch, tmp_path):
    paths = [tmp_path / f"repo-{index}" for index in range(20)]
    monkeypatch.setattr(
        snapshot_collection,
        "collect_repository_snapshot",
        lambda path: snapshot_utils.RepositorySnapshot(path=path, name=path.name, is_git_repo=True),
    )

    assert [item.path for item in snapshot_utils.collect_repository_snapshots(paths)] == paths
