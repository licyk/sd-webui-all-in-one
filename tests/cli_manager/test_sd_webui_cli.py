"""SD WebUI 命令行解析测试"""

from sd_webui_all_in_one.cli_manager import sd_webui_cli
from tests.cli_manager.helpers import single_command_parser


def test_sd_webui_cli_parse_smoke(monkeypatch, tmp_path):
    parser = single_command_parser(sd_webui_cli.register_sd_webui)
    calls = []

    monkeypatch.setattr(sd_webui_cli, "install", lambda **kwargs: calls.append(("install", kwargs)))
    monkeypatch.setattr(sd_webui_cli, "update", lambda **kwargs: calls.append(("update", kwargs)))
    monkeypatch.setattr(sd_webui_cli, "launch", lambda **kwargs: calls.append(("launch", kwargs)))
    monkeypatch.setattr(sd_webui_cli, "install_extension", lambda **kwargs: calls.append(("extension", kwargs)))
    monkeypatch.setattr(sd_webui_cli, "update_extensions", lambda **kwargs: calls.append(("extension-update", kwargs)))
    monkeypatch.setattr(sd_webui_cli, "launch_version_gui", lambda **kwargs: calls.append(("version-gui", kwargs)))
    monkeypatch.setattr(sd_webui_cli, "reinstall_pytorch", lambda **kwargs: calls.append(("reinstall-pytorch", kwargs)))
    monkeypatch.setattr(sd_webui_cli, "install_model_from_library", lambda **kwargs: calls.append(("model", kwargs)))

    args = parser.parse_args(["sd-webui", "install", "--sd-webui-path", str(tmp_path), "--no-auto-mirror", "--no-uv", "--no-pre-download-extension"])
    args.func(args)
    assert calls[-1][0] == "install"
    assert calls[-1][1]["sd_webui_path"] == tmp_path
    assert calls[-1][1]["use_uv"] is False
    assert calls[-1][1]["no_pre_download_extension"] is True

    snapshot_dir = tmp_path / "pre-operation-snapshots"

    args = parser.parse_args(
        [
            "sd-webui",
            "update",
            "--sd-webui-path",
            str(tmp_path),
            "--no-auto-mirror",
            "--no-snapshot",
            "--snapshot-dir",
            str(snapshot_dir),
        ]
    )
    args.func(args)
    assert calls[-1][0] == "update"
    assert calls[-1][1]["sd_webui_path"] == tmp_path
    assert calls[-1][1]["snapshot_enabled"] is False
    assert calls[-1][1]["snapshot_dir"] == snapshot_dir

    args = parser.parse_args(["sd-webui", "launch", "--sd-webui-path", str(tmp_path), "--no-auto-mirror", "--launch-args", "--api --listen", "--no-check-env"])
    args.func(args)
    assert calls[-1][0] == "launch"
    assert calls[-1][1]["launch_args"] == "--api --listen"
    assert calls[-1][1]["check_launch_env"] is False

    args = parser.parse_args(["sd-webui", "extension", "install", "--sd-webui-path", str(tmp_path), "--no-auto-mirror", "--url", "https://github.com/example/ext"])
    args.func(args)
    assert calls[-1][0] == "extension"
    assert calls[-1][1]["extension_url"] == "https://github.com/example/ext"

    args = parser.parse_args(
        [
            "sd-webui",
            "extension",
            "update",
            "--sd-webui-path",
            str(tmp_path),
            "--no-auto-mirror",
            "--no-snapshot",
            "--snapshot-dir",
            str(snapshot_dir),
        ]
    )
    args.func(args)
    assert calls[-1][0] == "extension-update"
    assert calls[-1][1]["sd_webui_path"] == tmp_path
    assert calls[-1][1]["snapshot_enabled"] is False
    assert calls[-1][1]["snapshot_dir"] == snapshot_dir

    args = parser.parse_args(
        [
            "sd-webui",
            "gui",
            "version-manager",
            "--sd-webui-path",
            str(tmp_path),
            "--no-auto-mirror",
            "--no-snapshot",
            "--snapshot-dir",
            str(snapshot_dir),
        ]
    )
    args.func(args)
    assert calls[-1][0] == "version-gui"
    assert calls[-1][1]["sd_webui_path"] == tmp_path
    assert calls[-1][1]["snapshot_enabled"] is False
    assert calls[-1][1]["snapshot_dir"] == snapshot_dir

    args = parser.parse_args(
        [
            "sd-webui",
            "reinstall-pytorch",
            "--sd-webui-path",
            str(tmp_path),
            "--no-auto-mirror",
            "--name",
            "torch-demo",
            "--no-snapshot",
            "--snapshot-dir",
            str(snapshot_dir),
        ]
    )
    args.func(args)
    assert calls[-1][0] == "reinstall-pytorch"
    assert calls[-1][1]["sd_webui_path"] == tmp_path
    assert calls[-1][1]["pytorch_name"] == "torch-demo"
    assert calls[-1][1]["snapshot_enabled"] is False
    assert calls[-1][1]["snapshot_dir"] == snapshot_dir

    args = parser.parse_args(["sd-webui", "model", "install-library", "--sd-webui-path", str(tmp_path), "--no-auto-mirror", "--index", "2", "--downloader", "urllib"])
    args.func(args)
    assert calls[-1][0] == "model"
    assert calls[-1][1]["model_index"] == 2
    assert calls[-1][1]["downloader"] == "urllib"
