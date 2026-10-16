"""各 WebUI 命令行子命令测试"""

import pytest

from sd_webui_all_in_one.cli_manager import comfyui_cli, fooocus_cli, invokeai_cli, mizuoto_tts_webui_cli, qwen_tts_webui_cli, rvc_next_webui_cli, sd_scripts_cli, sd_trainer_cli, sd_webui_cli
from tests.cli_manager.helpers import build_parser


@pytest.mark.parametrize(
    ("module", "register", "root", "path_arg", "path_key"),
    [
        (comfyui_cli, comfyui_cli.register_comfyui, "comfyui", "--comfyui-path", "comfyui_path"),
        (fooocus_cli, fooocus_cli.register_fooocus, "fooocus", "--fooocus-path", "fooocus_path"),
        (sd_scripts_cli, sd_scripts_cli.register_sd_scripts, "sd-scripts", "--sd-scripts-path", "sd_scripts_path"),
        (sd_trainer_cli, sd_trainer_cli.register_sd_trainer, "sd-trainer", "--sd-trainer-path", "sd_trainer_path"),
    ],
)
def test_product_cli_install_update_check_reinstall_and_model_smoke(monkeypatch, tmp_path, module, register, root, path_arg, path_key):
    parser = build_parser(register)
    calls = []

    monkeypatch.setattr(module, "install", lambda **kwargs: calls.append(("install", kwargs)))
    monkeypatch.setattr(module, "update", lambda **kwargs: calls.append(("update", kwargs)))
    monkeypatch.setattr(module, "check_env", lambda **kwargs: calls.append(("check", kwargs)))
    monkeypatch.setattr(module, "reinstall_pytorch", lambda **kwargs: calls.append(("reinstall", kwargs)))
    monkeypatch.setattr(module, "install_model_from_library", lambda **kwargs: calls.append(("model-library", kwargs)))
    monkeypatch.setattr(module, "install_model_from_url", lambda **kwargs: calls.append(("model-url", kwargs)))
    monkeypatch.setattr(module, "list_models", lambda **kwargs: calls.append(("model-list", kwargs)))
    monkeypatch.setattr(module, "uninstall_model", lambda **kwargs: calls.append(("model-uninstall", kwargs)))

    args = parser.parse_args([root, "install", path_arg, str(tmp_path), "--no-auto-mirror", "--no-uv", "--no-pypi-mirror"])
    args.func(args)
    assert calls[-1][0] == "install"
    assert calls[-1][1][path_key] == tmp_path
    assert calls[-1][1]["use_uv"] is False
    assert calls[-1][1]["use_pypi_mirror"] is False

    snapshot_dir = tmp_path / "pre-operation-snapshots"

    args = parser.parse_args(
        [
            root,
            "update",
            path_arg,
            str(tmp_path),
            "--no-auto-mirror",
            "--custom-github-mirror",
            "https://mirror.example",
            "--no-snapshot",
            "--snapshot-dir",
            str(snapshot_dir),
        ]
    )
    args.func(args)
    assert calls[-1][0] == "update"
    assert calls[-1][1][path_key] == tmp_path
    assert calls[-1][1]["custom_github_mirror"] == "https://mirror.example"
    assert calls[-1][1]["snapshot_enabled"] is False
    assert calls[-1][1]["snapshot_dir"] == snapshot_dir

    args = parser.parse_args([root, "check-env", path_arg, str(tmp_path), "--no-auto-mirror", "--no-uv"])
    args.func(args)
    assert calls[-1][0] == "check"
    assert calls[-1][1]["use_uv"] is False

    args = parser.parse_args(
        [
            root,
            "reinstall-pytorch",
            path_arg,
            str(tmp_path),
            "--no-auto-mirror",
            "--name",
            "torch-demo",
            "--no-uv",
            "--force-reinstall",
            "--no-snapshot",
            "--snapshot-dir",
            str(snapshot_dir),
        ]
    )
    args.func(args)
    assert calls[-1][0] == "reinstall"
    assert calls[-1][1][path_key] == tmp_path
    assert calls[-1][1]["pytorch_name"] == "torch-demo"
    assert calls[-1][1]["force_reinstall"] is True
    assert calls[-1][1]["snapshot_enabled"] is False
    assert calls[-1][1]["snapshot_dir"] == snapshot_dir

    args = parser.parse_args([root, "model", "install-library", path_arg, str(tmp_path), "--no-auto-mirror", "--name", "alpha", "--downloader", "urllib"])
    args.func(args)
    assert calls[-1][0] == "model-library"
    assert calls[-1][1][path_key] == tmp_path
    assert calls[-1][1]["model_name"] == "alpha"
    assert calls[-1][1]["downloader"] == "urllib"

    args = parser.parse_args([root, "model", "install-url", path_arg, str(tmp_path), "--url", "https://example.test/model.bin", "--type", "checkpoint"])
    args.func(args)
    assert calls[-1][0] == "model-url"
    assert calls[-1][1]["model_url"] == "https://example.test/model.bin"

    args = parser.parse_args([root, "model", "list", path_arg, str(tmp_path)])
    args.func(args)
    assert calls[-1][0] == "model-list"

    args = parser.parse_args([root, "model", "uninstall", path_arg, str(tmp_path), "--name", "alpha"])
    args.func(args)
    assert calls[-1][0] == "model-uninstall"
    assert calls[-1][1]["model_name"] == "alpha"


def test_sd_trainer_cli_accepts_next_branch(monkeypatch, tmp_path):
    parser = build_parser(sd_trainer_cli.register_sd_trainer)
    calls = []
    snapshot_dir = tmp_path / "switch-snapshots"

    monkeypatch.setattr(sd_trainer_cli, "install", lambda **kwargs: calls.append(("install", kwargs)))
    monkeypatch.setattr(sd_trainer_cli, "switch", lambda **kwargs: calls.append(("switch", kwargs)))

    args = parser.parse_args(
        [
            "sd-trainer",
            "install",
            "--sd-trainer-path",
            str(tmp_path),
            "--no-auto-mirror",
            "--install-branch",
            "sd_trainer_next_main",
        ]
    )
    args.func(args)

    assert calls[-1] == (
        "install",
        {
            "sd_trainer_path": tmp_path,
            "pytorch_mirror_type": None,
            "custom_pytorch_package": None,
            "custom_xformers_package": None,
            "use_pypi_mirror": True,
            "use_uv": True,
            "use_github_mirror": True,
            "custom_github_mirror": None,
            "install_branch": "sd_trainer_next_main",
            "no_pre_download_model": False,
            "model_download_resource_type": "modelscope",
        },
    )

    args = parser.parse_args(
        [
            "sd-trainer",
            "switch",
            "--sd-trainer-path",
            str(tmp_path),
            "--no-auto-mirror",
            "--branch",
            "sd_trainer_next_main",
            "--no-snapshot",
            "--snapshot-dir",
            str(snapshot_dir),
        ]
    )
    args.func(args)

    assert calls[-1] == (
        "switch",
        {
            "sd_trainer_path": tmp_path,
            "branch": "sd_trainer_next_main",
            "use_github_mirror": True,
            "custom_github_mirror": None,
            "interactive_mode": False,
            "list_only": False,
            "snapshot_enabled": False,
            "snapshot_dir": snapshot_dir,
        },
    )


def test_qwen_tts_webui_cli_install_uses_standard_model_options(monkeypatch, tmp_path):
    parser = build_parser(qwen_tts_webui_cli.register_qwen_tts_webui)
    calls = []

    monkeypatch.setattr(qwen_tts_webui_cli, "install", lambda **kwargs: calls.append(kwargs))

    args = parser.parse_args(
        [
            "qwen-tts-webui",
            "install",
            "--qwen-tts-webui-path",
            str(tmp_path),
            "--no-auto-mirror",
            "--no-pre-download-model",
            "--model-resource",
            "huggingface",
        ]
    )
    args.func(args)

    assert calls[-1]["qwen_tts_webui_path"] == tmp_path
    assert calls[-1]["no_pre_download_model"] is True
    assert calls[-1]["model_download_resource_type"] == "huggingface"


@pytest.mark.parametrize(
    ("module", "register", "root", "path_arg", "path_key"),
    [
        (comfyui_cli, comfyui_cli.register_comfyui, "comfyui", "--comfyui-path", "comfyui_path"),
        (fooocus_cli, fooocus_cli.register_fooocus, "fooocus", "--fooocus-path", "fooocus_path"),
        (qwen_tts_webui_cli, qwen_tts_webui_cli.register_qwen_tts_webui, "qwen-tts-webui", "--qwen-tts-webui-path", "qwen_tts_webui_path"),
        (rvc_next_webui_cli, rvc_next_webui_cli.register_rvc_next_webui, "rvc-next-webui", "--rvc-next-webui-path", "rvc_next_webui_path"),
        (mizuoto_tts_webui_cli, mizuoto_tts_webui_cli.register_mizuoto_tts_webui, "mizuoto-tts-webui", "--mizuoto-tts-webui-path", "mizuoto_tts_webui_path"),
        (sd_trainer_cli, sd_trainer_cli.register_sd_trainer, "sd-trainer", "--sd-trainer-path", "sd_trainer_path"),
        (invokeai_cli, invokeai_cli.register_invokeai, "invokeai", "--invokeai-path", "invokeai_path"),
    ],
)
def test_product_cli_launch_and_gui_smoke(monkeypatch, tmp_path, module, register, root, path_arg, path_key):
    parser = build_parser(register)
    calls = []

    monkeypatch.setattr(module, "launch", lambda **kwargs: calls.append(("launch", kwargs)))
    monkeypatch.setattr(module, "launch_version_gui", lambda **kwargs: calls.append(("gui", kwargs)))
    if hasattr(module, "launch_model_gui"):
        monkeypatch.setattr(module, "launch_model_gui", lambda **kwargs: calls.append(("model-gui", kwargs)))

    args = parser.parse_args(
        [
            root,
            "launch",
            path_arg,
            str(tmp_path),
            "--no-auto-mirror",
            "--launch-args",
            "--listen --port 7861",
            "--no-uv",
            "--include-check",
            "torch-version",
            "--exclude-check",
            "torch-libomp",
            "--no-check-env",
            "--no-hotpatcher",
        ]
    )
    args.func(args)
    assert calls[-1][0] == "launch"
    assert calls[-1][1][path_key] == tmp_path
    assert calls[-1][1]["launch_args"] == "--listen --port 7861"
    assert calls[-1][1]["use_uv"] is False
    assert calls[-1][1]["include_checks"] == ["torch-version"]
    assert calls[-1][1]["exclude_checks"] == ["torch-libomp"]
    assert calls[-1][1]["check_launch_env"] is False
    assert calls[-1][1]["enable_hotpatcher"] is False

    snapshot_dir = tmp_path / "version-gui-snapshots"
    args = parser.parse_args(
        [
            root,
            "gui",
            "version-manager",
            path_arg,
            str(tmp_path),
            "--no-auto-mirror",
            "--no-snapshot",
            "--snapshot-dir",
            str(snapshot_dir),
        ]
    )
    args.func(args)
    assert calls[-1][0] == "gui"
    assert calls[-1][1][path_key] == tmp_path
    assert calls[-1][1]["snapshot_enabled"] is False
    assert calls[-1][1]["snapshot_dir"] == snapshot_dir

    if hasattr(module, "launch_model_gui"):
        args = parser.parse_args([root, "gui", "model-manager", path_arg, str(tmp_path)])
        args.func(args)
        assert calls[-1][0] == "model-gui"
        assert calls[-1][1][path_key] == tmp_path


@pytest.mark.parametrize(
    ("module", "register", "root", "path_arg", "path_key"),
    [
        (sd_webui_cli, sd_webui_cli.register_sd_webui, "sd-webui", "--sd-webui-path", "sd_webui_path"),
        (comfyui_cli, comfyui_cli.register_comfyui, "comfyui", "--comfyui-path", "comfyui_path"),
        (fooocus_cli, fooocus_cli.register_fooocus, "fooocus", "--fooocus-path", "fooocus_path"),
        (sd_trainer_cli, sd_trainer_cli.register_sd_trainer, "sd-trainer", "--sd-trainer-path", "sd_trainer_path"),
        (sd_scripts_cli, sd_scripts_cli.register_sd_scripts, "sd-scripts", "--sd-scripts-path", "sd_scripts_path"),
        (invokeai_cli, invokeai_cli.register_invokeai, "invokeai", "--invokeai-path", "invokeai_path"),
    ],
)
def test_product_cli_model_gui_smoke(monkeypatch, tmp_path, module, register, root, path_arg, path_key):
    parser = build_parser(register)
    calls = []

    monkeypatch.setattr(module, "launch_model_gui", lambda **kwargs: calls.append(kwargs))

    args = parser.parse_args([root, "gui", "model-manager", path_arg, str(tmp_path)])
    args.func(args)

    assert calls == [{path_key: tmp_path}]


@pytest.mark.parametrize(
    ("module", "register", "root", "path_arg", "path_key"),
    [
        (comfyui_cli, comfyui_cli.register_comfyui, "comfyui", "--comfyui-path", "comfyui_path"),
        (invokeai_cli, invokeai_cli.register_invokeai, "invokeai", "--invokeai-path", "invokeai_path"),
    ],
)
def test_custom_node_cli_smoke(monkeypatch, tmp_path, module, register, root, path_arg, path_key):
    parser = build_parser(register)
    calls = []

    install_name = "install_custom_node" if module is comfyui_cli else "install_custom_nodes"
    status_name = "set_custom_node_status"
    list_name = "list_custom_nodes"
    update_name = "update_custom_nodes"
    uninstall_name = "uninstall_custom_node"

    monkeypatch.setattr(module, install_name, lambda **kwargs: calls.append(("install", kwargs)))
    monkeypatch.setattr(module, status_name, lambda **kwargs: calls.append(("status", kwargs)))
    monkeypatch.setattr(module, list_name, lambda **kwargs: calls.append(("list", kwargs)))
    monkeypatch.setattr(module, update_name, lambda **kwargs: calls.append(("update", kwargs)))
    monkeypatch.setattr(module, uninstall_name, lambda **kwargs: calls.append(("uninstall", kwargs)))

    args = parser.parse_args([root, "custom-node", "install", path_arg, str(tmp_path), "--no-auto-mirror", "--url", "https://github.com/example/node"])
    args.func(args)
    assert calls[-1] == ("install", {path_key: tmp_path, "custom_node_url": "https://github.com/example/node", "use_github_mirror": True, "custom_github_mirror": None})

    args = parser.parse_args([root, "custom-node", "status", path_arg, str(tmp_path), "--name", "node", "--disable"])
    args.func(args)
    assert calls[-1] == ("status", {path_key: tmp_path, "custom_node_name": "node", "status": False})

    args = parser.parse_args([root, "custom-node", "list", path_arg, str(tmp_path)])
    args.func(args)
    assert calls[-1] == ("list", {path_key: tmp_path})

    snapshot_dir = tmp_path / "custom-node-snapshots"
    args = parser.parse_args(
        [
            root,
            "custom-node",
            "update",
            path_arg,
            str(tmp_path),
            "--no-auto-mirror",
            "--no-github-mirror",
            "--no-snapshot",
            "--snapshot-dir",
            str(snapshot_dir),
        ]
    )
    args.func(args)
    assert calls[-1] == (
        "update",
        {
            path_key: tmp_path,
            "use_github_mirror": False,
            "custom_github_mirror": None,
            "snapshot_enabled": False,
            "snapshot_dir": snapshot_dir,
        },
    )

    args = parser.parse_args([root, "custom-node", "uninstall", path_arg, str(tmp_path), "--name", "node"])
    args.func(args)
    assert calls[-1] == ("uninstall", {path_key: tmp_path, "custom_node_name": "node"})
