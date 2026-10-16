"""自管理命令: 内网穿透, 下载, 压缩包, API 服务与环境信息测试"""

from sd_webui_all_in_one.cli_manager import utils as cli_utils
from tests.cli_manager.helpers import single_command_parser


def test_self_manager_start_tunnel_cli_parse_smoke(monkeypatch, tmp_path):
    parser = single_command_parser(cli_utils.register_manager)
    calls = []

    monkeypatch.setattr(cli_utils, "start_tunnel", lambda **kwargs: calls.append(kwargs))

    args = parser.parse_args(["self-manager", "start-tunnel", "7860", "--workspace", str(tmp_path), "--cloudflare"])
    args.func(args)

    assert calls == [
        {
            "port": 7860,
            "workspace": tmp_path,
            "use_ngrok": False,
            "ngrok_token": None,
            "use_cloudflare": True,
            "use_remote_moe": False,
            "use_localhost_run": False,
            "use_gradio": False,
            "use_pinggy_io": False,
            "use_zrok": False,
            "zrok_token": None,
        }
    ]

    default_args = parser.parse_args(["self-manager", "download-file", "https://example.test/defaults.bin"])
    assert default_args.split == 32
    assert default_args.max_connection_per_server == 16
    assert default_args.min_split_size == 20 * 1024 * 1024
    assert default_args.piece_length == 1024 * 1024
    assert default_args.always_resume is True
    assert default_args.max_resume_failure_tries == 0
    assert default_args.existing_file == "resume"


def test_self_manager_download_file_cli_parse_smoke(monkeypatch, tmp_path):
    parser = single_command_parser(cli_utils.register_manager)
    calls = []

    monkeypatch.setattr(cli_utils, "download_file_cli", lambda **kwargs: calls.append(kwargs))

    args = parser.parse_args(
        [
            "self-manager",
            "download-file",
            "https://example.test/model.bin",
            "--path",
            str(tmp_path),
            "--save-name",
            "asset.bin",
            "--downloader",
            "requests",
            "--no-progress",
            "--split",
            "8",
            "--max-connection-per-server",
            "2",
            "--min-split-size",
            "4096",
            "--piece-length",
            "4096",
            "--allow-piece-length-change",
            "--continue",
            "--max-tries",
            "3",
            "--retry-wait",
            "9",
            "--conditional-get",
            "--no-remote-time",
            "--no-always-resume",
            "--max-resume-failure-tries",
            "2",
            "--existing-file",
            "overwrite",
            "--hash",
            "abcd",
            "--hash-algorithm",
            "sha512",
            "--connect-timeout",
            "11",
            "--read-timeout",
            "22",
            "--lowest-speed-limit",
            "1024",
            "--lowest-speed-time",
            "5",
        ]
    )
    args.func(args)

    assert calls == [
        {
            "url": "https://example.test/model.bin",
            "path": tmp_path,
            "save_name": "asset.bin",
            "tool": "requests",
            "progress": False,
            "split": 8,
            "max_connection_per_server": 2,
            "min_split_size": 4096,
            "piece_length": 4096,
            "allow_piece_length_change": True,
            "continue_download": True,
            "max_tries": 3,
            "retry_wait": 9,
            "conditional_get": True,
            "remote_time": False,
            "always_resume": False,
            "max_resume_failure_tries": 2,
            "existing_file_policy": "overwrite",
            "hash_value": "abcd",
            "hash_algorithm": "sha512",
            "connect_timeout": 11,
            "read_timeout": 22,
            "lowest_speed_limit": 1024,
            "lowest_speed_time": 5,
        }
    ]


def test_self_manager_archive_cli_parse_smoke(monkeypatch, tmp_path):
    parser = single_command_parser(cli_utils.register_manager)
    calls = []

    monkeypatch.setattr(cli_utils, "extract_archive_cli", lambda **kwargs: calls.append(("extract", kwargs)))
    monkeypatch.setattr(cli_utils, "compress_archive_cli", lambda **kwargs: calls.append(("compress", kwargs)))

    args = parser.parse_args(["self-manager", "archive", "extract", str(tmp_path / "archive.zip"), "--output", str(tmp_path / "out")])
    args.func(args)

    args = parser.parse_args(
        [
            "self-manager",
            "archive",
            "compress",
            str(tmp_path / "source"),
            str(tmp_path / "file.txt"),
            "--output",
            str(tmp_path / "created.zip"),
            "--no-progress",
        ]
    )
    args.func(args)

    assert calls == [
        (
            "extract",
            {
                "archive_path": tmp_path / "archive.zip",
                "output": tmp_path / "out",
                "progress": True,
            },
        ),
        (
            "compress",
            {
                "sources": [tmp_path / "source", tmp_path / "file.txt"],
                "output": tmp_path / "created.zip",
                "progress": False,
            },
        ),
    ]


def test_serve_api_cli_delegates_to_api_server(monkeypatch):
    calls = []
    monkeypatch.setattr(cli_utils, "serve_api", lambda **kwargs: calls.append(kwargs))

    cli_utils.serve_api_cli(host="0.0.0.0", port=9000, token="secret")

    assert calls == [{"host": "0.0.0.0", "port": 9000, "token": "secret"}]


def test_get_pytorch_device_type_prints_comma_separated_types(monkeypatch, capsys):
    monkeypatch.setattr(cli_utils, "get_available_pytorch_device_type", lambda: ["all", "cpu", "cu128"])
    monkeypatch.setattr(cli_utils, "auto_detect_pytorch_device_category", lambda: "cuda")

    cli_utils.get_pytorch_device_type()
    assert capsys.readouterr().out.strip() == "all,cpu,cu128"

    cli_utils.get_pytorch_device_type(output_category=True)
    assert capsys.readouterr().out.strip() == "cuda"


def test_get_env_config_prints_resolved_config_values(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL", "999")
    monkeypatch.setenv("SD_WEBUI_ROOT", "/env/sd-webui")
    monkeypatch.setattr(cli_utils.app_config, "LOGGER_LEVEL", 42)
    monkeypatch.setattr(cli_utils.app_config, "SD_WEBUI_ROOT_PATH", tmp_path / "configured-webui")

    cli_utils.get_env_config()

    output = {name: value for name, value in (line.split(": ", 1) for line in capsys.readouterr().out.strip().splitlines())}
    assert output["SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL"] == "'42'"
    assert output["SD_WEBUI_ROOT"] == f"'{(tmp_path / 'configured-webui').as_posix()}'"
