import argparse
from pathlib import Path

import pytest

from sd_webui_all_in_one.cli_manager import comfyui_cli
from sd_webui_all_in_one.cli_manager import fooocus_cli
from sd_webui_all_in_one.cli_manager import invokeai_cli
from sd_webui_all_in_one.cli_manager import qwen_tts_webui_cli
from sd_webui_all_in_one.cli_manager import sd_scripts_cli
from sd_webui_all_in_one.cli_manager import sd_trainer_cli


def _parser(*register_funcs):
    parser = argparse.ArgumentParser(prog="sd-webui-all-in-one")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for register in register_funcs:
        register(subparsers)
    return parser


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
    parser = _parser(register)
    calls = []

    monkeypatch.setattr(module, "install", lambda **kwargs: calls.append(("install", kwargs)))
    monkeypatch.setattr(module, "update", lambda **kwargs: calls.append(("update", kwargs)))
    monkeypatch.setattr(module, "check_env", lambda **kwargs: calls.append(("check", kwargs)))
    monkeypatch.setattr(module, "reinstall_pytorch", lambda **kwargs: calls.append(("reinstall", kwargs)))
    monkeypatch.setattr(module, "install_model_from_library", lambda **kwargs: calls.append(("model-library", kwargs)))
    monkeypatch.setattr(module, "install_model_from_url", lambda **kwargs: calls.append(("model-url", kwargs)))
    monkeypatch.setattr(module, "list_models", lambda **kwargs: calls.append(("model-list", kwargs)))
    monkeypatch.setattr(module, "uninstall_model", lambda **kwargs: calls.append(("model-uninstall", kwargs)))

    args = parser.parse_args([root, "install", path_arg, str(tmp_path), "--no-uv", "--no-pypi-mirror"])
    args.func(args)
    assert calls[-1][0] == "install"
    assert calls[-1][1][path_key] == tmp_path
    assert calls[-1][1]["use_uv"] is False
    assert calls[-1][1]["use_pypi_mirror"] is False

    args = parser.parse_args([root, "update", path_arg, str(tmp_path), "--custom-github-mirror", "https://mirror.example"])
    args.func(args)
    assert calls[-1][0] == "update"
    assert calls[-1][1][path_key] == tmp_path
    assert calls[-1][1]["custom_github_mirror"] == "https://mirror.example"

    args = parser.parse_args([root, "check-env", path_arg, str(tmp_path), "--no-uv"])
    args.func(args)
    assert calls[-1][0] == "check"
    assert calls[-1][1]["use_uv"] is False

    args = parser.parse_args([root, "reinstall-pytorch", "--name", "torch-demo", "--no-uv", "--force-reinstall"])
    args.func(args)
    assert calls[-1][0] == "reinstall"
    assert calls[-1][1]["pytorch_name"] == "torch-demo"
    assert calls[-1][1]["force_reinstall"] is True

    args = parser.parse_args([root, "model", "install-library", path_arg, str(tmp_path), "--name", "alpha", "--downloader", "urllib"])
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


@pytest.mark.parametrize(
    ("module", "register", "root", "path_arg", "path_key"),
    [
        (comfyui_cli, comfyui_cli.register_comfyui, "comfyui", "--comfyui-path", "comfyui_path"),
        (fooocus_cli, fooocus_cli.register_fooocus, "fooocus", "--fooocus-path", "fooocus_path"),
        (qwen_tts_webui_cli, qwen_tts_webui_cli.register_qwen_tts_webui, "qwen-tts-webui", "--qwen-tts-webui-path", "qwen_tts_webui_path"),
        (sd_trainer_cli, sd_trainer_cli.register_sd_trainer, "sd-trainer", "--sd-trainer-path", "sd_trainer_path"),
        (invokeai_cli, invokeai_cli.register_invokeai, "invokeai", "--invokeai-path", "invokeai_path"),
    ],
)
def test_product_cli_launch_and_gui_smoke(monkeypatch, tmp_path, module, register, root, path_arg, path_key):
    parser = _parser(register)
    calls = []

    monkeypatch.setattr(module, "launch", lambda **kwargs: calls.append(("launch", kwargs)))
    monkeypatch.setattr(module, "launch_version_gui", lambda **kwargs: calls.append(("gui", kwargs)))

    args = parser.parse_args([root, "launch", path_arg, str(tmp_path), "--launch-args", "--listen --port 7861", "--no-check-env", "--no-hotpatcher"])
    args.func(args)
    assert calls[-1][0] == "launch"
    assert calls[-1][1][path_key] == tmp_path
    assert calls[-1][1]["launch_args"] == "--listen --port 7861"
    assert calls[-1][1]["check_launch_env"] is False
    assert calls[-1][1]["enable_hotpatcher"] is False

    args = parser.parse_args([root, "gui", "version-manager", path_arg, str(tmp_path)])
    args.func(args)
    assert calls[-1][0] == "gui"
    assert calls[-1][1][path_key] == tmp_path


@pytest.mark.parametrize(
    ("module", "register", "root", "path_arg", "path_key"),
    [
        (comfyui_cli, comfyui_cli.register_comfyui, "comfyui", "--comfyui-path", "comfyui_path"),
        (invokeai_cli, invokeai_cli.register_invokeai, "invokeai", "--invokeai-path", "invokeai_path"),
    ],
)
def test_custom_node_cli_smoke(monkeypatch, tmp_path, module, register, root, path_arg, path_key):
    parser = _parser(register)
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

    args = parser.parse_args([root, "custom-node", "install", path_arg, str(tmp_path), "--url", "https://github.com/example/node"])
    args.func(args)
    assert calls[-1] == ("install", {path_key: tmp_path, "custom_node_url": "https://github.com/example/node", "use_github_mirror": True, "custom_github_mirror": None})

    args = parser.parse_args([root, "custom-node", "status", path_arg, str(tmp_path), "--name", "node", "--disable"])
    args.func(args)
    assert calls[-1] == ("status", {path_key: tmp_path, "custom_node_name": "node", "status": False})

    args = parser.parse_args([root, "custom-node", "list", path_arg, str(tmp_path)])
    args.func(args)
    assert calls[-1] == ("list", {path_key: tmp_path})

    args = parser.parse_args([root, "custom-node", "update", path_arg, str(tmp_path), "--no-github-mirror"])
    args.func(args)
    assert calls[-1] == ("update", {path_key: tmp_path, "use_github_mirror": False, "custom_github_mirror": None})

    args = parser.parse_args([root, "custom-node", "uninstall", path_arg, str(tmp_path), "--name", "node"])
    args.func(args)
    assert calls[-1] == ("uninstall", {path_key: tmp_path, "custom_node_name": "node"})


def test_all_product_roots_register_together():
    parser = _parser(
        comfyui_cli.register_comfyui,
        fooocus_cli.register_fooocus,
        invokeai_cli.register_invokeai,
        qwen_tts_webui_cli.register_qwen_tts_webui,
        sd_scripts_cli.register_sd_scripts,
        sd_trainer_cli.register_sd_trainer,
    )

    assert parser.parse_args(["comfyui", "check-env"]).command == "comfyui"
    assert parser.parse_args(["fooocus", "check-env"]).command == "fooocus"
    assert parser.parse_args(["invokeai", "check-env"]).command == "invokeai"
    assert parser.parse_args(["qwen-tts-webui", "check-env"]).command == "qwen-tts-webui"
    assert parser.parse_args(["sd-scripts", "check-env"]).command == "sd-scripts"
    assert parser.parse_args(["sd-trainer", "check-env"]).command == "sd-trainer"
