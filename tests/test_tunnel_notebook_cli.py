import argparse
import subprocess

import pytest

from sd_webui_all_in_one.cli_manager import sd_webui_cli
from sd_webui_all_in_one.cli_manager import utils as cli_utils
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.notebook_manager import base_manager as notebook_base
from sd_webui_all_in_one.tunnel import manager as tunnel_manager
from sd_webui_all_in_one.tunnel.base import BaseTunnel


def test_tunnel_manager_returns_local_url_when_no_services(tmp_path):
    manager = tunnel_manager.TunnelManager(tmp_path, 7860)

    assert manager.start_tunnel(check=True) == {"local_url": "http://127.0.0.1:7860"}
    assert manager.tunnel_url == {"local_url": "http://127.0.0.1:7860"}
    assert manager.running_tunnels_count == 0


def test_tunnel_manager_starts_registered_tunnels_and_context_stops(monkeypatch, tmp_path):
    instances = []

    class GoodTunnel:
        def __init__(self, port, workspace):
            self.port = port
            self.workspace = workspace
            self.stopped = False
            instances.append(self)

        def start(self):
            return f"https://cloudflare.example/{self.port}"

        def stop(self):
            self.stopped = True

        @property
        def is_running(self):
            return not self.stopped

    monkeypatch.setattr(tunnel_manager, "CloudflareTunnel", GoodTunnel)

    with tunnel_manager.TunnelManager(tmp_path, 7860) as manager:
        assert manager.start_tunnel(use_cloudflare=True) == {
            "local_url": "http://127.0.0.1:7860",
            "cloudflare": "https://cloudflare.example/7860",
        }
        assert manager.running_tunnels_count == 1

    assert instances[0].stopped is True


def test_tunnel_manager_aggregates_or_ignores_failures(monkeypatch, tmp_path):
    class GoodTunnel:
        def __init__(self, *_args):
            pass

        def start(self):
            return "https://ok.example"

        def stop(self):
            pass

        @property
        def is_running(self):
            return True

    class BadTunnel:
        def __init__(self, *_args):
            pass

        def start(self):
            raise RuntimeError("no tunnel")

    monkeypatch.setattr(tunnel_manager, "CloudflareTunnel", GoodTunnel)
    monkeypatch.setattr(tunnel_manager, "GradioTunnel", BadTunnel)

    manager = tunnel_manager.TunnelManager(tmp_path, 7860)
    with pytest.raises(AggregateError) as exc:
        manager.start_tunnel(use_cloudflare=True, use_gradio=True, check=True)
    assert len(exc.value.exceptions) == 1

    assert manager.start_tunnel(use_cloudflare=True, use_gradio=True, check=False) == {
        "local_url": "http://127.0.0.1:7860",
        "cloudflare": "https://ok.example",
    }


class DemoTunnel(BaseTunnel):
    def start(self):
        return "https://demo.example"


def test_base_tunnel_stop_terminates_or_kills_on_timeout(tmp_path):
    class CleanProcess:
        pid = 1

        def __init__(self):
            self.terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return 0

    tunnel = DemoTunnel(7860, tmp_path)
    process = CleanProcess()
    tunnel._process = process  # ty: ignore[invalid-assignment]
    tunnel.stop()
    assert process.terminated is True

    class SlowProcess:
        pid = 2

        def __init__(self):
            self.killed = False

        def poll(self):
            return None

        def terminate(self):
            pass

        def wait(self, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired("cmd", timeout)
            return 0

        def kill(self):
            self.killed = True

    slow_process = SlowProcess()
    tunnel._process = slow_process  # ty: ignore[invalid-assignment]
    tunnel.stop()
    assert slow_process.killed is True


class FakeRepoManager:
    def __init__(self, hf_token=None, ms_token=None):
        self.hf_token = hf_token
        self.ms_token = ms_token
        self.calls = []

    def upload_files_to_repo(self, **kwargs):
        self.calls.append(("upload", kwargs))

    def download_files_from_repo(self, **kwargs):
        self.calls.append(("download", kwargs))

    def get_repo_files_metadata(self, **kwargs):
        self.calls.append(("metadata", kwargs))
        return [{"path": "weights/a.bin"}]

    def get_repo_file_download_url(self, **kwargs):
        self.calls.append(("download_url", kwargs))
        return "https://example.test/download.bin"

    def mirror_repo_files(self, **kwargs):
        self.calls.append(("mirror", kwargs))


class FakeTunnelManager:
    def __init__(self, workspace, port):
        self.workspace = workspace
        self.port = port
        self.calls = []

    def start_tunnel(self, **kwargs):
        self.calls.append(kwargs)
        return {"local_url": "http://127.0.0.1:7860", "cloudflare": "https://cf.example"}

    def stop_all(self):
        self.calls.append(("stop_all", {}))


class FakeTCMalloc:
    def __init__(self, workspace):
        self.workspace = workspace


@pytest.fixture
def notebook_manager(monkeypatch, tmp_path):
    monkeypatch.setattr(notebook_base, "RepoManager", FakeRepoManager)
    monkeypatch.setattr(notebook_base, "TunnelManager", FakeTunnelManager)
    monkeypatch.setattr(notebook_base, "TCMalloc", FakeTCMalloc)
    return notebook_base.BaseManager(tmp_path / "workspace", "webui", hf_token="hf", ms_token="ms", port=9000)


def test_notebook_base_manager_initializes_and_parses_commands(notebook_manager, tmp_path):
    assert notebook_manager.workspace == tmp_path / "workspace"
    assert notebook_manager.workspace.is_dir()
    assert notebook_manager.repo_manager.hf_token == "hf"
    assert notebook_manager.tun_manager.port == 9000
    assert notebook_manager.parse_cmd_str_to_list('--theme "dark mode"') == ["--theme", "dark mode"]
    assert notebook_manager.parse_cmd_list_to_str(["--theme", "dark mode"]) == "--theme 'dark mode'"


def test_notebook_get_model_from_list_downloads_enabled_items(notebook_manager):
    calls = []

    def fake_get_model(url, path, filename=None, tool="aria2"):
        calls.append((url, path, filename, tool))

    notebook_manager.get_model = fake_get_model
    notebook_manager.get_model_from_list("/models", [["skip", 0], ["a", 1], ["b", 2, "b.bin"], ["bad"]])

    assert calls == [
        ("a", "/models", None, "aria2"),
        ("b", "/models", "b.bin", "aria2"),
    ]


def test_notebook_gpu_check_and_delegates(monkeypatch, notebook_manager, tmp_path):
    monkeypatch.setattr(notebook_base, "get_gpu_list", lambda: [])
    monkeypatch.setattr(notebook_base, "is_colab_environment", lambda: False)

    with pytest.raises(RuntimeError):
        notebook_manager.check_avaliable_gpu()

    download_calls = []
    monkeypatch.setattr(notebook_base, "download_archive_and_unpack", lambda **kwargs: download_calls.append(kwargs))
    notebook_manager.download_and_extract("https://example.test/a.zip", tmp_path / "out", name="a.zip")
    assert download_calls == [{"url": "https://example.test/a.zip", "local_dir": tmp_path / "out", "name": "a.zip"}]

    notebook_manager.upload_files_to_repo(
        "huggingface",
        "owner/repo",
        tmp_path / "upload",
        visibility=True,
        num_threads=2,
        revision="hf-rev",
    )
    notebook_manager.download_files_from_repo(
        "modelscope",
        "owner/repo",
        tmp_path / "download",
        folder="aa",
        num_threads=3,
        revision="ms-rev",
    )
    assert notebook_manager.repo_manager.calls[0][0] == "upload"
    assert notebook_manager.repo_manager.calls[1][0] == "download"
    assert notebook_manager.repo_manager.calls[0][1]["revision"] == "hf-rev"
    assert notebook_manager.repo_manager.calls[1][1]["revision"] == "ms-rev"
    url = notebook_manager.get_repo_file_download_url(
        "huggingface",
        "owner/repo",
        "weights/a.bin",
        revision="hf-rev",
    )
    assert url == "https://example.test/download.bin"
    assert notebook_manager.repo_manager.calls[2] == (
        "download_url",
        {
            "api_type": "huggingface",
            "repo_id": "owner/repo",
            "file_path": "weights/a.bin",
            "repo_type": "model",
            "revision": "hf-rev",
        },
    )
    metadata = notebook_manager.get_repo_files_metadata(
        "modelscope",
        "owner/repo",
        repo_type="dataset",
        include_dirs=True,
        include_raw=True,
    )
    assert metadata == [{"path": "weights/a.bin"}]
    assert notebook_manager.repo_manager.calls[3] == (
        "metadata",
        {
            "api_type": "modelscope",
            "repo_id": "owner/repo",
            "repo_type": "dataset",
            "include_dirs": True,
            "include_raw": True,
        },
    )
    notebook_manager.mirror_repo_files(
        "huggingface",
        "modelscope",
        "owner/src",
        "owner/dst",
        dst_repo_type="dataset",
        visibility=True,
        revision="mirror-rev",
        num_threads=4,
        retry_times=2,
        use_fast_download=True,
        download_tool="aria2",
        download_split=16,
        download_progress=False,
    )
    assert notebook_manager.repo_manager.calls[4] == (
        "mirror",
        {
            "src_api_type": "huggingface",
            "dst_api_type": "modelscope",
            "src_repo_id": "owner/src",
            "dst_repo_id": "owner/dst",
            "src_repo_type": "model",
            "dst_repo_type": "dataset",
            "visibility": True,
            "num_threads": 4,
            "use_fast_download": True,
            "download_tool": "aria2",
            "download_split": 16,
            "download_progress": False,
            "revision": "mirror-rev",
            "retry_times": 2,
        },
    )

    tunnel = notebook_manager.get_tunnel_url(use_cloudflare=True, webui_name="Demo")
    assert tunnel["cloudflare"] == "https://cf.example"
    assert notebook_manager.tun_manager.calls[0]["check"] is False


def _single_command_parser(register_func):
    parser = argparse.ArgumentParser(prog="test")
    subparsers = parser.add_subparsers(dest="main_command", required=True)
    register_func(subparsers)
    return parser


def test_sd_webui_cli_parse_smoke(monkeypatch, tmp_path):
    parser = _single_command_parser(sd_webui_cli.register_sd_webui)
    calls = []

    monkeypatch.setattr(sd_webui_cli, "install", lambda **kwargs: calls.append(("install", kwargs)))
    monkeypatch.setattr(sd_webui_cli, "launch", lambda **kwargs: calls.append(("launch", kwargs)))
    monkeypatch.setattr(sd_webui_cli, "install_extension", lambda **kwargs: calls.append(("extension", kwargs)))
    monkeypatch.setattr(sd_webui_cli, "install_model_from_library", lambda **kwargs: calls.append(("model", kwargs)))

    args = parser.parse_args(["sd-webui", "install", "--sd-webui-path", str(tmp_path), "--no-auto-mirror", "--no-uv", "--no-pre-download-extension"])
    args.func(args)
    assert calls[-1][0] == "install"
    assert calls[-1][1]["sd_webui_path"] == tmp_path
    assert calls[-1][1]["use_uv"] is False
    assert calls[-1][1]["no_pre_download_extension"] is True

    args = parser.parse_args(["sd-webui", "launch", "--sd-webui-path", str(tmp_path), "--no-auto-mirror", "--launch-args", "--api --listen", "--no-check-env"])
    args.func(args)
    assert calls[-1][0] == "launch"
    assert calls[-1][1]["launch_args"] == "--api --listen"
    assert calls[-1][1]["check_launch_env"] is False

    args = parser.parse_args(["sd-webui", "extension", "install", "--sd-webui-path", str(tmp_path), "--no-auto-mirror", "--url", "https://github.com/example/ext"])
    args.func(args)
    assert calls[-1][0] == "extension"
    assert calls[-1][1]["extension_url"] == "https://github.com/example/ext"

    args = parser.parse_args(["sd-webui", "model", "install-library", "--sd-webui-path", str(tmp_path), "--no-auto-mirror", "--index", "2", "--downloader", "urllib"])
    args.func(args)
    assert calls[-1][0] == "model"
    assert calls[-1][1]["model_index"] == 2
    assert calls[-1][1]["downloader"] == "urllib"


def test_self_manager_start_tunnel_cli_parse_smoke(monkeypatch, tmp_path):
    parser = _single_command_parser(cli_utils.register_manager)
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


def test_self_manager_download_file_cli_parse_smoke(monkeypatch, tmp_path):
    parser = _single_command_parser(cli_utils.register_manager)
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
        }
    ]


def test_self_manager_archive_cli_parse_smoke(monkeypatch, tmp_path):
    parser = _single_command_parser(cli_utils.register_manager)
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


def test_get_env_config_prints_resolved_config_values(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL", "999")
    monkeypatch.setenv("SD_WEBUI_ROOT", "/env/sd-webui")
    monkeypatch.setattr(cli_utils.app_config, "LOGGER_LEVEL", 42)
    monkeypatch.setattr(cli_utils.app_config, "SD_WEBUI_ROOT_PATH", tmp_path / "configured-webui")

    cli_utils.get_env_config()

    output = {name: value for name, value in (line.split(": ", 1) for line in capsys.readouterr().out.strip().splitlines())}
    assert output["SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL"] == "'42'"
    assert output["SD_WEBUI_ROOT"] == f"'{(tmp_path / 'configured-webui').as_posix()}'"
