"""环境快照命令行解析测试"""

import argparse

from sd_webui_all_in_one.cli_manager import (
    comfyui_cli,
    fooocus_cli,
    invokeai_cli,
    mizuoto_tts_webui_cli,
    qwen_tts_webui_cli,
    rvc_next_webui_cli,
    sd_scripts_cli,
    sd_trainer_cli,
    sd_webui_cli,
)


def _parser(register_func):
    parser = argparse.ArgumentParser(prog="sd-webui-all-in-one")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_func(subparsers)
    return parser


def test_product_snapshot_cli_parse_smoke(monkeypatch, tmp_path):
    cases = [
        (sd_webui_cli, sd_webui_cli.register_sd_webui, "sd-webui", "--sd-webui-path", "sd_webui_path"),
        (comfyui_cli, comfyui_cli.register_comfyui, "comfyui", "--comfyui-path", "comfyui_path"),
        (fooocus_cli, fooocus_cli.register_fooocus, "fooocus", "--fooocus-path", "fooocus_path"),
        (invokeai_cli, invokeai_cli.register_invokeai, "invokeai", "--invokeai-path", "invokeai_path"),
        (qwen_tts_webui_cli, qwen_tts_webui_cli.register_qwen_tts_webui, "qwen-tts-webui", "--qwen-tts-webui-path", "qwen_tts_webui_path"),
        (rvc_next_webui_cli, rvc_next_webui_cli.register_rvc_next_webui, "rvc-next-webui", "--rvc-next-webui-path", "rvc_next_webui_path"),
        (mizuoto_tts_webui_cli, mizuoto_tts_webui_cli.register_mizuoto_tts_webui, "mizuoto-tts-webui", "--mizuoto-tts-webui-path", "mizuoto_tts_webui_path"),
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
