"""CLI 入口与子命令分发测试"""

import runpy
import sys

import pytest


def test_module_main_delegates_to_cli_main(monkeypatch):
    from sd_webui_all_in_one.cli_manager import cli

    calls = []
    monkeypatch.setattr(cli, "main", lambda: calls.append("main"))

    runpy.run_module("sd_webui_all_in_one.__main__", run_name="__main__")

    assert calls == ["main"]


def test_cli_main_dispatches_registered_callback(monkeypatch):
    from sd_webui_all_in_one.cli_manager import cli

    calls = []

    def register_demo(subparsers):
        parser = subparsers.add_parser("demo")
        parser.set_defaults(func=lambda args: calls.append(args.main_command))

    def noop_register(_subparsers):
        return None

    for name in [
        "register_sd_trainer",
        "register_sd_scripts",
        "register_invokeai",
        "register_fooocus",
        "register_comfyui",
        "register_qwen_tts_webui",
        "register_rvc_next_webui",
        "register_mizuoto_tts_webui",
        "register_manager",
    ]:
        monkeypatch.setattr(cli, name, noop_register)
    monkeypatch.setattr(cli, "register_sd_webui", register_demo)
    monkeypatch.setattr(sys, "argv", ["sd-webui-all-in-one", "demo"])

    cli.main()

    assert calls == ["demo"]


def test_cli_main_prints_help_without_subcommand(monkeypatch, capsys):
    from sd_webui_all_in_one.cli_manager import cli

    def noop_register(_subparsers):
        return None

    for name in [
        "register_sd_webui",
        "register_sd_trainer",
        "register_sd_scripts",
        "register_invokeai",
        "register_fooocus",
        "register_comfyui",
        "register_qwen_tts_webui",
        "register_rvc_next_webui",
        "register_mizuoto_tts_webui",
        "register_manager",
    ]:
        monkeypatch.setattr(cli, name, noop_register)
    monkeypatch.setattr(sys, "argv", ["sd-webui-all-in-one"])

    cli.main()

    output = capsys.readouterr().out
    assert "SD WebUI All In One" in output
    assert "usage:" in output


@pytest.mark.parametrize(
    ("arguments", "usage"),
    [
        (["sd-webui"], "usage: sd-webui-all-in-one sd-webui [-h]"),
        (["sd-trainer"], "usage: sd-webui-all-in-one sd-trainer [-h]"),
        (["sd-scripts"], "usage: sd-webui-all-in-one sd-scripts [-h]"),
        (["invokeai"], "usage: sd-webui-all-in-one invokeai [-h]"),
        (["fooocus"], "usage: sd-webui-all-in-one fooocus [-h]"),
        (["comfyui"], "usage: sd-webui-all-in-one comfyui [-h]"),
        (["qwen-tts-webui"], "usage: sd-webui-all-in-one qwen-tts-webui [-h]"),
        (["rvc-next-webui"], "usage: sd-webui-all-in-one rvc-next-webui [-h]"),
        (["mizuoto-tts-webui"], "usage: sd-webui-all-in-one mizuoto-tts-webui [-h]"),
        (["self-manager"], "usage: sd-webui-all-in-one self-manager [-h]"),
        (["sd-webui", "extension"], "usage: sd-webui-all-in-one sd-webui extension [-h]"),
        (["self-manager", "check"], "usage: sd-webui-all-in-one self-manager check [-h]"),
    ],
)
def test_cli_main_prints_current_help_without_nested_action(monkeypatch, capsys, arguments, usage):
    from sd_webui_all_in_one.cli_manager import cli

    monkeypatch.setattr(sys, "argv", ["sd-webui-all-in-one", *arguments])

    cli.main()

    captured = capsys.readouterr()
    assert usage in captured.out
    assert captured.err == ""
