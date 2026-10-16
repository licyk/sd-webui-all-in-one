"""各 WebUI 命令行操作前快照测试"""

import pytest

from sd_webui_all_in_one.cli_manager import fooocus_cli, invokeai_cli, mizuoto_tts_webui_cli, qwen_tts_webui_cli, rvc_next_webui_cli, sd_scripts_cli, sd_trainer_cli, sd_webui_cli
from tests.cli_manager.helpers import build_parser


@pytest.mark.parametrize(
    ("module", "register", "root", "path_arg", "path_key", "branch"),
    [
        (sd_webui_cli, sd_webui_cli.register_sd_webui, "sd-webui", "--sd-webui-path", "sd_webui_path", sd_webui_cli.SD_WEBUI_BRANCH_LIST[0]),
        (fooocus_cli, fooocus_cli.register_fooocus, "fooocus", "--fooocus-path", "fooocus_path", fooocus_cli.FOOOCUS_BRANCH_LIST[0]),
        (sd_trainer_cli, sd_trainer_cli.register_sd_trainer, "sd-trainer", "--sd-trainer-path", "sd_trainer_path", sd_trainer_cli.SD_TRAINER_BRANCH_LIST[0]),
        (sd_scripts_cli, sd_scripts_cli.register_sd_scripts, "sd-scripts", "--sd-scripts-path", "sd_scripts_path", sd_scripts_cli.SD_SCRIPTS_BRANCH_LIST[0]),
    ],
)
def test_product_cli_switch_snapshot_smoke(monkeypatch, tmp_path, module, register, root, path_arg, path_key, branch):
    parser = build_parser(register)
    calls = []
    snapshot_dir = tmp_path / "switch-snapshots"

    monkeypatch.setattr(module, "switch", lambda **kwargs: calls.append(("switch", kwargs)))

    args = parser.parse_args(
        [
            root,
            "switch",
            path_arg,
            str(tmp_path),
            "--no-auto-mirror",
            "--branch",
            branch,
            "--no-snapshot",
            "--snapshot-dir",
            str(snapshot_dir),
        ]
    )
    args.func(args)

    assert calls[-1][0] == "switch"
    assert calls[-1][1][path_key] == tmp_path
    assert calls[-1][1]["branch"] == branch
    assert calls[-1][1]["snapshot_enabled"] is False
    assert calls[-1][1]["snapshot_dir"] == snapshot_dir


@pytest.mark.parametrize(
    ("module", "path_key", "base_switch_name", "branch", "operation_name"),
    [
        (sd_webui_cli, "sd_webui_path", "switch_sd_webui_branch", sd_webui_cli.SD_WEBUI_BRANCH_LIST[0], "切换 Stable Diffusion WebUI 分支"),
        (fooocus_cli, "fooocus_path", "switch_fooocus_branch", fooocus_cli.FOOOCUS_BRANCH_LIST[0], "切换 Fooocus 分支"),
        (sd_trainer_cli, "sd_trainer_path", "switch_sd_trainer_branch", sd_trainer_cli.SD_TRAINER_BRANCH_LIST[0], "切换 SD Trainer 分支"),
        (sd_scripts_cli, "sd_scripts_path", "switch_sd_scripts_branch", sd_scripts_cli.SD_SCRIPTS_BRANCH_LIST[0], "切换 SD Scripts 分支"),
    ],
)
def test_product_switch_creates_pre_operation_snapshot(monkeypatch, tmp_path, module, path_key, base_switch_name, branch, operation_name):
    calls = []
    snapshot_dir = tmp_path / "switch-snapshots"

    monkeypatch.setattr(module, "_create_pre_operation_snapshot", lambda **kwargs: calls.append(("snapshot", kwargs)))
    monkeypatch.setattr(module, base_switch_name, lambda **kwargs: calls.append(("switch", kwargs)))

    module.switch(
        **{
            path_key: tmp_path,
            "branch": branch,
            "snapshot_enabled": False,
            "snapshot_dir": snapshot_dir,
        }
    )

    assert calls[0] == (
        "snapshot",
        {
            path_key: tmp_path,
            "operation_name": operation_name,
            "snapshot_enabled": False,
            "snapshot_dir": snapshot_dir,
        },
    )
    assert calls[1][0] == "switch"
    assert calls[1][1][path_key] == tmp_path
    assert calls[1][1]["branch"] == branch

    calls.clear()
    module.switch(
        **{
            path_key: tmp_path,
            "list_only": True,
            "snapshot_enabled": True,
            "snapshot_dir": snapshot_dir,
        }
    )

    assert calls[0][0] == "switch"


@pytest.mark.parametrize(
    ("module", "register", "root", "path_arg", "path_key", "reinstall_func_name", "reinstall_args", "reinstall_expected"),
    [
        (
            qwen_tts_webui_cli,
            qwen_tts_webui_cli.register_qwen_tts_webui,
            "qwen-tts-webui",
            "--qwen-tts-webui-path",
            "qwen_tts_webui_path",
            "reinstall_pytorch",
            ["--name", "torch-demo", "--force-reinstall"],
            {"pytorch_name": "torch-demo", "force_reinstall": True},
        ),
        (
            rvc_next_webui_cli,
            rvc_next_webui_cli.register_rvc_next_webui,
            "rvc-next-webui",
            "--rvc-next-webui-path",
            "rvc_next_webui_path",
            "reinstall_pytorch",
            ["--name", "torch-demo", "--force-reinstall"],
            {"pytorch_name": "torch-demo", "force_reinstall": True},
        ),
        (
            mizuoto_tts_webui_cli,
            mizuoto_tts_webui_cli.register_mizuoto_tts_webui,
            "mizuoto-tts-webui",
            "--mizuoto-tts-webui-path",
            "mizuoto_tts_webui_path",
            "reinstall_pytorch",
            ["--name", "torch-demo", "--force-reinstall"],
            {"pytorch_name": "torch-demo", "force_reinstall": True},
        ),
        (
            invokeai_cli,
            invokeai_cli.register_invokeai,
            "invokeai",
            "--invokeai-path",
            "invokeai_path",
            "reinstall_invokeai_pytorch",
            ["--device-type", "cuda"],
            {"device_type": "cuda"},
        ),
    ],
)
def test_product_cli_update_and_reinstall_snapshot_smoke(
    monkeypatch,
    tmp_path,
    module,
    register,
    root,
    path_arg,
    path_key,
    reinstall_func_name,
    reinstall_args,
    reinstall_expected,
):
    parser = build_parser(register)
    calls = []
    snapshot_dir = tmp_path / "pre-operation-snapshots"

    monkeypatch.setattr(module, "update", lambda **kwargs: calls.append(("update", kwargs)))
    monkeypatch.setattr(module, reinstall_func_name, lambda **kwargs: calls.append(("reinstall", kwargs)))

    args = parser.parse_args(
        [
            root,
            "update",
            path_arg,
            str(tmp_path),
            "--no-auto-mirror",
            "--no-snapshot",
            "--snapshot-dir",
            str(snapshot_dir),
        ]
    )
    args.func(args)
    assert calls[-1][0] == "update"
    assert calls[-1][1][path_key] == tmp_path
    assert calls[-1][1]["snapshot_enabled"] is False
    assert calls[-1][1]["snapshot_dir"] == snapshot_dir

    args = parser.parse_args(
        [
            root,
            "reinstall-pytorch",
            path_arg,
            str(tmp_path),
            "--no-auto-mirror",
            *reinstall_args,
            "--no-snapshot",
            "--snapshot-dir",
            str(snapshot_dir),
        ]
    )
    args.func(args)
    assert calls[-1][0] == "reinstall"
    assert calls[-1][1][path_key] == tmp_path
    assert calls[-1][1]["snapshot_enabled"] is False
    assert calls[-1][1]["snapshot_dir"] == snapshot_dir
    for key, value in reinstall_expected.items():
        assert calls[-1][1][key] == value
