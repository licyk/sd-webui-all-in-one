import argparse
import json
from pathlib import Path

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


def test_output_snapshot_prints_json_or_writes_file(tmp_path, capsys):
    snapshot = _webui_snapshot(tmp_path / "demo")
    snapshot_json = snapshot_utils.snapshot_to_dict(snapshot)

    output_snapshot(lambda: snapshot)
    assert json.loads(capsys.readouterr().out) == snapshot_json

    output = tmp_path / "snapshot.json"
    output_snapshot(lambda: snapshot, output=output)
    assert json.loads(output.read_text(encoding="utf-8")) == snapshot_json


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
                str(tmp_path / f"{command}.json"),
                "--no-packages",
            ]
        )
        args.func(args)

        assert calls == [
            {
                path_key: tmp_path / command,
                "output": tmp_path / f"{command}.json",
                "include_packages": False,
            }
        ]
