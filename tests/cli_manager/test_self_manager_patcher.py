"""Hotpatcher 命令行测试"""

import argparse
import os

import pytest

from sd_webui_all_in_one.base_manager.hotpatcher_manager import (
    DEFAULT_HOTPATCHER_CONFIG_PATH,
    DEFAULT_RUNTIME_PORT,
    HOTPATCHER_PATH,
)
from sd_webui_all_in_one.cli_manager.utils import register_manager


def test_self_manager_patcher_cli_parser(tmp_path):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="main_command", required=True)
    register_manager(subparsers)

    export_args = parser.parse_args(["self-manager", "patcher", "export-config", "--output", str(tmp_path / "config.json"), "--force"])
    assert export_args.patcher_action == "export-config"
    assert export_args.force is True
    assert callable(export_args.func)

    pythonpath_args = parser.parse_args(["self-manager", "patcher", "get-pythonpath"])
    assert pythonpath_args.patcher_action == "get-pythonpath"
    assert callable(pythonpath_args.func)

    check_pip_args = parser.parse_args(["self-manager", "check", "pip", "--no-pypi-mirror", "--no-auto-mirror"])
    assert check_pip_args.sd_webui_all_in_one_action == "check"
    assert check_pip_args.check_action == "pip"
    assert check_pip_args.use_pypi_mirror is False
    assert check_pip_args.auto_mirror is False
    assert callable(check_pip_args.func)

    check_uv_args = parser.parse_args(["self-manager", "check", "uv"])
    assert check_uv_args.sd_webui_all_in_one_action == "check"
    assert check_uv_args.check_action == "uv"
    assert callable(check_uv_args.func)

    check_aria2_args = parser.parse_args(["self-manager", "check", "aria2"])
    assert check_aria2_args.sd_webui_all_in_one_action == "check"
    assert check_aria2_args.check_action == "aria2"
    assert callable(check_aria2_args.func)

    proxy_args = parser.parse_args(["self-manager", "get", "proxy"])
    assert proxy_args.sd_webui_all_in_one_action == "get"
    assert proxy_args.get_action == "proxy"
    assert callable(proxy_args.func)

    env_config_args = parser.parse_args(["self-manager", "get", "env-config"])
    assert env_config_args.sd_webui_all_in_one_action == "get"
    assert env_config_args.get_action == "env-config"
    assert callable(env_config_args.func)

    tcmalloc_args = parser.parse_args(["self-manager", "get", "tcmalloc"])
    assert tcmalloc_args.sd_webui_all_in_one_action == "get"
    assert tcmalloc_args.get_action == "tcmalloc"
    assert tcmalloc_args.path is False
    assert callable(tcmalloc_args.func)

    tcmalloc_path_args = parser.parse_args(["self-manager", "get", "tcmalloc", "--path"])
    assert tcmalloc_path_args.sd_webui_all_in_one_action == "get"
    assert tcmalloc_path_args.get_action == "tcmalloc"
    assert tcmalloc_path_args.path is True
    assert callable(tcmalloc_path_args.func)

    api_serve_args = parser.parse_args(["self-manager", "api", "serve", "--host", "0.0.0.0", "--port", "9000", "--token", "secret"])
    assert api_serve_args.sd_webui_all_in_one_action == "api"
    assert api_serve_args.api_action == "serve"
    assert api_serve_args.host == "0.0.0.0"
    assert api_serve_args.port == 9000
    assert api_serve_args.token == "secret"
    assert callable(api_serve_args.func)

    pytorch_type_args = parser.parse_args(["self-manager", "get", "pytorch-device-type"])
    assert pytorch_type_args.sd_webui_all_in_one_action == "get"
    assert pytorch_type_args.get_action == "pytorch-device-type"
    assert pytorch_type_args.category is False
    assert callable(pytorch_type_args.func)

    pytorch_category_args = parser.parse_args(["self-manager", "get", "pytorch-device-type", "--category"])
    assert pytorch_category_args.sd_webui_all_in_one_action == "get"
    assert pytorch_category_args.get_action == "pytorch-device-type"
    assert pytorch_category_args.category is True
    assert callable(pytorch_category_args.func)

    extract_args = parser.parse_args(["self-manager", "archive", "extract", str(tmp_path / "archive.zip"), "--output", str(tmp_path / "out")])
    assert extract_args.sd_webui_all_in_one_action == "archive"
    assert extract_args.archive_action == "extract"
    assert extract_args.archive_path == tmp_path / "archive.zip"
    assert extract_args.output == tmp_path / "out"
    assert extract_args.progress is True
    assert callable(extract_args.func)

    compress_args = parser.parse_args(
        [
            "self-manager",
            "archive",
            "compress",
            str(tmp_path / "source-a"),
            str(tmp_path / "source-b.txt"),
            "--output",
            str(tmp_path / "created.tar.gz"),
            "--no-progress",
        ]
    )
    assert compress_args.sd_webui_all_in_one_action == "archive"
    assert compress_args.archive_action == "compress"
    assert compress_args.sources == [tmp_path / "source-a", tmp_path / "source-b.txt"]
    assert compress_args.output == tmp_path / "created.tar.gz"
    assert compress_args.progress is False
    assert callable(compress_args.func)

    gui_args = parser.parse_args(["self-manager", "patcher", "gui"])
    assert gui_args.patcher_action == "gui"
    assert gui_args.config == DEFAULT_HOTPATCHER_CONFIG_PATH
    assert gui_args.host == "127.0.0.1"
    assert gui_args.port == 8765
    assert callable(gui_args.func)


@pytest.mark.parametrize(
    "argv",
    [
        ["self-manager", "check-aria2"],
        ["self-manager", "check-pip"],
        ["self-manager", "check-uv"],
        ["self-manager", "get-proxy"],
        ["self-manager", "get-cuda-malloc"],
        ["self-manager", "get-tcmalloc"],
        ["self-manager", "get-env-config"],
    ],
)
def test_self_manager_legacy_check_and_get_paths_are_removed(argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="main_command", required=True)
    register_manager(subparsers)

    with pytest.raises(SystemExit):
        parser.parse_args(argv)


def test_self_manager_patcher_get_pythonpath_cli(monkeypatch, capsys):
    from sd_webui_all_in_one.cli_manager import utils as cli_utils

    monkeypatch.setenv("PYTHONPATH", "existing")

    cli_utils.get_hotpatcher_pythonpath_cli()

    pythonpath = capsys.readouterr().out.strip().split(os.pathsep)
    assert pythonpath[:2] == [HOTPATCHER_PATH.as_posix(), "existing"]


@pytest.mark.parametrize(
    ("register_name", "command"),
    (
        ("register_sd_webui", "sd-webui"),
        ("register_comfyui", "comfyui"),
        ("register_fooocus", "fooocus"),
        ("register_qwen_tts_webui", "qwen-tts-webui"),
        ("register_rvc_next_webui", "rvc-next-webui"),
        ("register_mizuoto_tts_webui", "mizuoto-tts-webui"),
        ("register_sd_trainer", "sd-trainer"),
        ("register_invokeai", "invokeai"),
    ),
)
def test_webui_launch_cli_hotpatcher_parser(register_name, command, tmp_path):
    modules = {
        "register_sd_webui": "sd_webui_all_in_one.cli_manager.sd_webui_cli",
        "register_comfyui": "sd_webui_all_in_one.cli_manager.comfyui_cli",
        "register_fooocus": "sd_webui_all_in_one.cli_manager.fooocus_cli",
        "register_qwen_tts_webui": "sd_webui_all_in_one.cli_manager.qwen_tts_webui_cli",
        "register_rvc_next_webui": "sd_webui_all_in_one.cli_manager.rvc_next_webui_cli",
        "register_mizuoto_tts_webui": "sd_webui_all_in_one.cli_manager.mizuoto_tts_webui_cli",
        "register_sd_trainer": "sd_webui_all_in_one.cli_manager.sd_trainer_cli",
        "register_invokeai": "sd_webui_all_in_one.cli_manager.invokeai_cli",
    }
    module = __import__(modules[register_name], fromlist=[register_name])
    register_func = getattr(module, register_name)
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="main_command", required=True)
    register_func(subparsers)

    default_args = parser.parse_args([command, "launch"])
    assert default_args.enable_hotpatcher is True
    assert default_args.enable_hotpatcher_runtime is False
    assert default_args.hotpatcher_config_path is None
    assert default_args.hotpatcher_port == DEFAULT_RUNTIME_PORT

    config_path = tmp_path / "patcher.json"
    custom_args = parser.parse_args(
        [
            command,
            "launch",
            "--no-hotpatcher",
            "--hotpatcher-runtime",
            "--hotpatcher-config",
            config_path.as_posix(),
            "--hotpatcher-port",
            "9901",
        ]
    )
    assert custom_args.enable_hotpatcher is False
    assert custom_args.enable_hotpatcher_runtime is True
    assert custom_args.hotpatcher_config_path == config_path
    assert custom_args.hotpatcher_port == 9901
