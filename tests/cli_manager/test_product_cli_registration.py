"""各 WebUI 命令行注册测试"""

import sys

import pytest

from sd_webui_all_in_one.cli_manager import comfyui_cli, fooocus_cli, invokeai_cli, mizuoto_tts_webui_cli, qwen_tts_webui_cli, rvc_next_webui_cli, sd_scripts_cli, sd_trainer_cli, sd_webui_cli
from tests.cli_manager.helpers import build_parser


@pytest.mark.parametrize(
    ("module", "product"),
    [
        (sd_webui_cli, "sd_webui"),
        (comfyui_cli, "comfyui"),
        (fooocus_cli, "fooocus"),
        (invokeai_cli, "invokeai"),
        (sd_trainer_cli, "sd_trainer"),
        (sd_scripts_cli, "sd_scripts"),
        (qwen_tts_webui_cli, "qwen_tts_webui"),
        (rvc_next_webui_cli, "rvc_next_webui"),
        (mizuoto_tts_webui_cli, "mizuoto_tts_webui"),
    ],
)
def test_env_check_choices_match_runtime_tasks(monkeypatch, tmp_path, capsys, module, product):
    check_env = getattr(module, f"check_{product}_env")
    implementation = sys.modules[check_env.__module__]
    tasks = []
    monkeypatch.setattr(implementation, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(implementation, "apply_git_config_global_to_process", lambda env: None)
    monkeypatch.setattr(implementation, "get_pypi_mirror_config", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(implementation, "run_env_check_tasks", lambda selected_tasks, **kwargs: tasks.extend(selected_tasks))
    (tmp_path / "requirements.txt").write_text("", encoding="utf-8")
    if product == "invokeai":
        check_env()
    else:
        check_env(tmp_path)

    task_names = [task.name.value for task in tasks]
    assert task_names
    parser = build_parser(getattr(module, f"register_{product}"))
    root = product.replace("_", "-")
    commands = ["check-env"] if product == "sd_scripts" else ["check-env", "launch"]
    foreign_name = "python-dependencies" if product == "invokeai" else "invokeai-package"
    for command in commands:
        args = parser.parse_args([root, command])
        assert args.include_checks is None
        assert args.exclude_checks is None
        with pytest.raises(SystemExit) as exc:
            parser.parse_args([root, command, "--help"])
        assert exc.value.code == 0
        help_text = capsys.readouterr().out
        choices_text = "{" + ",".join(task_names) + "}"
        assert f"--include-check {choices_text}" in help_text
        assert f"--exclude-check {choices_text}" in help_text

        for flag, dest in [("--include-check", "include_checks"), ("--exclude-check", "exclude_checks")]:
            arguments = [root, command]
            for name in task_names:
                arguments.extend([flag, name])
            args = parser.parse_args(arguments)
            assert getattr(args, dest) == task_names
            for invalid_name in ["unknown-check", foreign_name]:
                with pytest.raises(SystemExit) as exc:
                    parser.parse_args([root, command, flag, invalid_name])
                assert exc.value.code == 2
                assert "invalid choice" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("module", "register", "command", "path_arg", "checker_name"),
    [
        (sd_webui_cli, sd_webui_cli.register_sd_webui, "sd-webui", "--sd-webui-path", "check_sd_webui_updates"),
        (comfyui_cli, comfyui_cli.register_comfyui, "comfyui", "--comfyui-path", "check_comfyui_updates"),
        (fooocus_cli, fooocus_cli.register_fooocus, "fooocus", "--fooocus-path", "check_fooocus_updates"),
        (invokeai_cli, invokeai_cli.register_invokeai, "invokeai", "--invokeai-path", "check_invokeai_updates"),
        (
            qwen_tts_webui_cli,
            qwen_tts_webui_cli.register_qwen_tts_webui,
            "qwen-tts-webui",
            "--qwen-tts-webui-path",
            "check_qwen_tts_webui_updates",
        ),
        (
            rvc_next_webui_cli,
            rvc_next_webui_cli.register_rvc_next_webui,
            "rvc-next-webui",
            "--rvc-next-webui-path",
            "check_rvc_next_webui_updates",
        ),
        (
            mizuoto_tts_webui_cli,
            mizuoto_tts_webui_cli.register_mizuoto_tts_webui,
            "mizuoto-tts-webui",
            "--mizuoto-tts-webui-path",
            "check_mizuoto_tts_webui_updates",
        ),
        (sd_trainer_cli, sd_trainer_cli.register_sd_trainer, "sd-trainer", "--sd-trainer-path", "check_sd_trainer_updates"),
        (sd_scripts_cli, sd_scripts_cli.register_sd_scripts, "sd-scripts", "--sd-scripts-path", "check_sd_scripts_updates"),
    ],
)
def test_webui_cli_registers_product_update_checker(monkeypatch, tmp_path, module, register, command, path_arg, checker_name):
    parser = build_parser(register)
    calls = []
    result = object()
    outputs = []

    monkeypatch.setattr(module, checker_name, lambda path, options: calls.append((path, options)) or result)
    monkeypatch.setattr(module, "output_update_check_result", lambda status: outputs.append(status))

    args = parser.parse_args(
        [
            command,
            "check-update",
            path_arg,
            str(tmp_path),
            "--no-auto-mirror",
            "--no-github-mirror",
            "--custom-github-mirror",
            "https://github.example",
        ]
    )
    args.func(args)

    path, options = calls[-1]
    assert path == tmp_path
    assert options.use_github_mirror is False
    assert options.custom_github_mirror == "https://github.example"
    assert outputs == [result]


@pytest.mark.parametrize(
    ("module", "register", "command", "path_arg", "path_key"),
    [
        (sd_webui_cli, sd_webui_cli.register_sd_webui, "sd-webui", "--sd-webui-path", "sd_webui_path"),
        (comfyui_cli, comfyui_cli.register_comfyui, "comfyui", "--comfyui-path", "comfyui_path"),
        (fooocus_cli, fooocus_cli.register_fooocus, "fooocus", "--fooocus-path", "fooocus_path"),
        (invokeai_cli, invokeai_cli.register_invokeai, "invokeai", "--invokeai-path", "invokeai_path"),
        (sd_trainer_cli, sd_trainer_cli.register_sd_trainer, "sd-trainer", "--sd-trainer-path", "sd_trainer_path"),
        (sd_scripts_cli, sd_scripts_cli.register_sd_scripts, "sd-scripts", "--sd-scripts-path", "sd_scripts_path"),
        (
            qwen_tts_webui_cli,
            qwen_tts_webui_cli.register_qwen_tts_webui,
            "qwen-tts-webui",
            "--qwen-tts-webui-path",
            "qwen_tts_webui_path",
        ),
        (
            rvc_next_webui_cli,
            rvc_next_webui_cli.register_rvc_next_webui,
            "rvc-next-webui",
            "--rvc-next-webui-path",
            "rvc_next_webui_path",
        ),
        (
            mizuoto_tts_webui_cli,
            mizuoto_tts_webui_cli.register_mizuoto_tts_webui,
            "mizuoto-tts-webui",
            "--mizuoto-tts-webui-path",
            "mizuoto_tts_webui_path",
        ),
    ],
)
def test_webui_cli_exports_environment_info(monkeypatch, tmp_path, module, register, command, path_arg, path_key):
    parser = build_parser(register)
    calls = []
    output = tmp_path / "environment.json"
    monkeypatch.setattr(module, "export_environment", lambda **kwargs: calls.append(kwargs))

    args = parser.parse_args(
        [
            command,
            "export-environment",
            path_arg,
            str(tmp_path),
            "--output",
            str(output),
            "--no-packages",
            "--force",
        ]
    )
    args.func(args)

    assert calls == [
        {
            path_key: tmp_path,
            "output": output,
            "include_packages": False,
            "overwrite": True,
        }
    ]


@pytest.mark.parametrize(
    ("module", "register", "command", "group", "path_arg", "checker_name"),
    [
        (sd_webui_cli, sd_webui_cli.register_sd_webui, "sd-webui", "extension", "--sd-webui-path", "check_sd_webui_updates"),
        (comfyui_cli, comfyui_cli.register_comfyui, "comfyui", "custom-node", "--comfyui-path", "check_comfyui_updates"),
        (invokeai_cli, invokeai_cli.register_invokeai, "invokeai", "custom-node", "--invokeai-path", "check_invokeai_updates"),
    ],
)
def test_extension_cli_update_checker_excludes_kernel(monkeypatch, tmp_path, module, register, command, group, path_arg, checker_name):
    parser = build_parser(register)
    calls = []
    result = object()

    monkeypatch.setattr(module, checker_name, lambda path, options: calls.append((path, options)) or result)
    monkeypatch.setattr(module, "output_update_check_result", lambda status: status)

    args = parser.parse_args([command, group, "check-update", path_arg, str(tmp_path), "--no-auto-mirror"])
    args.func(args)

    path, options = calls[-1]
    assert path == tmp_path
    assert options.include_kernel is False


def test_all_product_roots_register_together():
    parser = build_parser(
        comfyui_cli.register_comfyui,
        fooocus_cli.register_fooocus,
        invokeai_cli.register_invokeai,
        qwen_tts_webui_cli.register_qwen_tts_webui,
        rvc_next_webui_cli.register_rvc_next_webui,
        mizuoto_tts_webui_cli.register_mizuoto_tts_webui,
        sd_scripts_cli.register_sd_scripts,
        sd_trainer_cli.register_sd_trainer,
    )

    assert parser.parse_args(["comfyui", "check-env"]).command == "comfyui"
    assert parser.parse_args(["fooocus", "check-env"]).command == "fooocus"
    assert parser.parse_args(["invokeai", "check-env"]).command == "invokeai"
    assert parser.parse_args(["qwen-tts-webui", "check-env"]).command == "qwen-tts-webui"
    assert parser.parse_args(["rvc-next-webui", "check-env"]).command == "rvc-next-webui"
    assert parser.parse_args(["mizuoto-tts-webui", "check-env"]).command == "mizuoto-tts-webui"
    assert parser.parse_args(["sd-scripts", "check-env"]).command == "sd-scripts"
    assert parser.parse_args(["sd-trainer", "check-env"]).command == "sd-trainer"
