import os
import re
import subprocess
import sys
import tarfile
import types
from pathlib import Path

import pytest

from sd_webui_all_in_one.tunnel.tunnels import cloudflare
from sd_webui_all_in_one.tunnel.tunnels import gradio
from sd_webui_all_in_one.tunnel.tunnels import localhost_run
from sd_webui_all_in_one.tunnel.tunnels import ngrok
from sd_webui_all_in_one.tunnel.tunnels import pinggy_io
from sd_webui_all_in_one.tunnel.tunnels import remote_moe
from sd_webui_all_in_one.tunnel.tunnels import ssh_base
from sd_webui_all_in_one.tunnel.tunnels import zrok
from sd_webui_all_in_one.tunnel.utils import ssh_key


def test_gen_ssh_key_runs_keygen_and_chmods(monkeypatch, tmp_path):
    key_path = tmp_path / "id_rsa"
    calls = []

    def fake_run(args, check):
        calls.append((args, check))
        key_path.write_text("key", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(ssh_key.subprocess, "run", fake_run)

    assert ssh_key.gen_ssh_key(key_path) is True
    assert calls[0][0][:7] == ["ssh-keygen", "-t", "rsa", "-b", "4096", "-N", ""]
    if os.name != "nt":
        assert oct(key_path.stat().st_mode & 0o777) == "0o600"
    else:
        assert key_path.exists()

    monkeypatch.setattr(ssh_key.subprocess, "run", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("no ssh")))
    assert ssh_key.gen_ssh_key(tmp_path / "bad") is False


def test_ssh_tunnel_uses_workspace_key_and_extracts_url(monkeypatch, tmp_path, capsys):
    key_path = tmp_path / "id_rsa"
    key_path.write_text("key", encoding="utf-8")
    commands = []

    class FakeStdout:
        def __init__(self):
            self.lines = iter(["Warning: test\n", "ready https://demo.example.tunnel\n", ""])

        def readline(self):
            return next(self.lines)

        def close(self):
            pass

    class FakeProcess:
        pid = 123

        def __init__(self, command, **kwargs):
            commands.append((command, kwargs))
            self.stdout = FakeStdout()

        def poll(self):
            return None

        def terminate(self):
            pass

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(ssh_base.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(ssh_base, "preprocess_command", lambda command, shell=True: command)

    tunnel = ssh_base.SSHTunnel(
        port=7860,
        workspace=tmp_path,
        ssh_args=["-R", "80:127.0.0.1:7860", "example"],
        url_pattern=re.compile(r"(?P<url>https://\S+\.tunnel)"),
        line_limit=3,
    )

    assert tunnel.start() == "https://demo.example.tunnel"
    assert "Warning: test" in capsys.readouterr().out
    assert commands[0][0][:5] == ["ssh", "-T", "-o", "StrictHostKeyChecking=no", "-i"]
    assert commands[0][0][5] == key_path.as_posix()
    assert commands[0][0][6:] == ["-R", "80:127.0.0.1:7860", "example"]


def test_ssh_tunnel_falls_back_to_temp_key_and_times_out(monkeypatch, tmp_path):
    generated = []
    monkeypatch.setattr(ssh_base, "gen_ssh_key", lambda path: generated.append(path) or len(generated) == 2)

    class EmptyStdout:
        def __init__(self):
            self.lines = iter(["still starting\n", ""])

        def readline(self):
            return next(self.lines)

        def close(self):
            pass

    class FakeProcess:
        pid = 1

        def __init__(self, *_args, **_kwargs):
            self.stdout = EmptyStdout()

        def poll(self):
            return None

    monkeypatch.setattr(ssh_base.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(ssh_base, "preprocess_command", lambda command, shell=True: command)

    tunnel = ssh_base.SSHTunnel(7860, tmp_path, ["remote"], re.compile(r"(?P<url>https://\S+)"), line_limit=1)

    with pytest.raises(RuntimeError):
        tunnel.start()

    assert generated[0] == tmp_path / "id_rsa"
    assert generated[1].name == "id_rsa"
    tunnel.stop()


def test_ssh_based_tunnel_classes_configure_expected_arguments(tmp_path):
    assert remote_moe.RemoteMoeTunnel(7860, tmp_path).ssh_args == ["-R", "80:127.0.0.1:7860", "remote.moe"]
    assert localhost_run.LocalhostRunTunnel(7860, tmp_path).ssh_args == ["-R", "80:127.0.0.1:7860", "localhost.run"]
    assert pinggy_io.PinggyIoTunnel(7860, tmp_path).ssh_args == ["-p", "443", "-R0:127.0.0.1:7860", "free.pinggy.io"]


def test_cloudflare_tunnel_start_stop_and_install_failure(monkeypatch, tmp_path):
    class FakeProcess:
        def __init__(self):
            self.terminated = False

        def poll(self):
            return 0 if self.terminated else None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return 0

    class FakeCloudflareTunnel:
        tunnel = "https://cf.example"

        def __init__(self):
            self.process = FakeProcess()
            self.terminated = False

    class FakeCloudflareClient:
        def __init__(self, tunnel):
            self.tunnel = tunnel

        def __call__(self, port):
            return self.tunnel

        def terminate(self, port):
            self.tunnel.terminated = True
            self.tunnel.process.terminate()

    fake = FakeCloudflareTunnel()
    monkeypatch.setitem(sys.modules, "pycloudflared", types.SimpleNamespace(try_cloudflare=FakeCloudflareClient(fake)))

    tunnel = cloudflare.CloudflareTunnel(7860, tmp_path)
    assert tunnel.start() == "https://cf.example"
    assert tunnel.is_running is True
    tunnel.stop()
    assert fake.terminated is True

    monkeypatch.setitem(sys.modules, "pycloudflared", None)
    monkeypatch.setattr(cloudflare, "install_optional_dependency", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("install failed")))
    with pytest.raises(RuntimeError, match="安装 CloudFlare"):
        cloudflare.CloudflareTunnel(7860, tmp_path).start()


def test_gradio_tunnel_uses_api_payload_and_kills(monkeypatch, tmp_path):
    tunnel_instances = []

    class FakeTunnel:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.killed = False
            tunnel_instances.append(self)

        def start_tunnel(self):
            return "https://gradio.example"

        def kill(self):
            self.killed = True

    fake_main = types.ModuleType("gradio_tunneling.main")
    setattr(fake_main, "Tunnel", FakeTunnel)
    setattr(fake_main, "GRADIO_API_SERVER", "https://api.example")
    monkeypatch.setitem(sys.modules, "gradio_tunneling", types.ModuleType("gradio_tunneling"))
    monkeypatch.setitem(sys.modules, "gradio_tunneling.main", fake_main)
    monkeypatch.setitem(
        sys.modules,
        "requests",
        types.SimpleNamespace(get=lambda url: types.SimpleNamespace(status_code=200, json=lambda: [{"host": "remote", "port": "9000"}])),
    )

    tunnel = gradio.GradioTunnel(7860, tmp_path)
    assert tunnel.start() == "https://gradio.example"
    assert tunnel_instances[0].kwargs["remote_host"] == "remote"
    assert tunnel_instances[0].kwargs["local_port"] == 7860
    tunnel.stop()
    assert tunnel_instances[0].killed is True


def test_ngrok_tunnel_reuses_existing_or_connects_and_disconnects(monkeypatch, tmp_path):
    default_conf = types.SimpleNamespace(auth_token=None, monitor_thread=True)
    disconnected = []

    class PyngrokError(Exception):
        pass

    fake_ngrok = types.SimpleNamespace(
        get_tunnels=lambda _conf: [],
        connect=lambda port, bind_tls=True: types.SimpleNamespace(public_url=f"https://{port}.ngrok.example"),
        disconnect=lambda url: disconnected.append(url),
    )
    fake_conf = types.SimpleNamespace(get_default=lambda: default_conf)
    fake_pyngrok = types.ModuleType("pyngrok")
    setattr(fake_pyngrok, "conf", fake_conf)
    setattr(fake_pyngrok, "ngrok", fake_ngrok)
    fake_exception = types.ModuleType("pyngrok.exception")
    setattr(fake_exception, "PyngrokError", PyngrokError)
    monkeypatch.setitem(sys.modules, "pyngrok", fake_pyngrok)
    monkeypatch.setitem(sys.modules, "pyngrok.exception", fake_exception)

    tunnel = ngrok.NgrokTunnel(7860, tmp_path, ngrok_token="token")
    assert tunnel.start() == "https://7860.ngrok.example"
    assert default_conf.auth_token == "token"
    assert default_conf.monitor_thread is False
    tunnel.stop()
    assert disconnected == ["https://7860.ngrok.example"]


def test_zrok_package_selection_and_release_error(monkeypatch, tmp_path):
    tunnel = zrok.ZrokTunnel(7860, tmp_path, zrok_token="token")
    monkeypatch.setattr(zrok.sys, "platform", "linux")
    monkeypatch.setattr(zrok.platform, "machine", lambda: "x86_64")

    assert tunnel._get_appropriate_zrok_package(
        [
            ["zrok_1.0.0_darwin_amd64.tar.gz", "darwin-url"],
            ["zrok_1.0.0_linux_amd64.tar.gz", "linux-url"],
        ]
    ) == ("zrok_1.0.0_linux_amd64.tar.gz", "linux-url")

    fake_requests = types.SimpleNamespace(get=lambda **_kwargs: types.SimpleNamespace(status_code=500, json=lambda: {}))
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    with pytest.raises(FileNotFoundError):
        tunnel._get_latest_zrok_release()


def test_zrok_install_uses_existing_or_downloaded_binary(monkeypatch, tmp_path):
    tunnel = zrok.ZrokTunnel(7860, tmp_path, zrok_token="token")
    monkeypatch.setattr(zrok.shutil, "which", lambda name: "/usr/bin/zrok2" if name == "zrok2" else None)
    assert tunnel._install_zrok() == Path("/usr/bin/zrok2")

    monkeypatch.setattr(zrok.shutil, "which", lambda _name: None)
    monkeypatch.setattr(tunnel, "_get_latest_zrok_release", lambda: [["zrok_1.0.0_linux_amd64.tar.gz", "https://example.test/zrok.tar.gz"]])
    monkeypatch.setattr(tunnel, "_get_appropriate_zrok_package", lambda packages: packages[0])

    def fake_download_file(url, path, save_name):
        archive = path / save_name
        bin_name = "zrok2.exe" if zrok.sys.platform == "win32" else "zrok2"
        binary = path / bin_name
        binary.write_text("zrok", encoding="utf-8")
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(binary, arcname=bin_name)
        return archive

    monkeypatch.setattr(zrok, "download_file", fake_download_file)

    installed = tunnel._install_zrok()
    assert installed == tmp_path / ("zrok.exe" if zrok.sys.platform == "win32" else "zrok")
    assert installed.read_text(encoding="utf-8") == "zrok"


def test_zrok_start_parses_url_and_stop_disables(monkeypatch, tmp_path):
    zrok_bin = tmp_path / "zrok"
    zrok_bin.write_text("", encoding="utf-8")
    run_calls = []

    class FakeStdout:
        def __init__(self):
            self.lines = iter(["starting\n", "share ready rp123.shares.zrok.io\n", ""])

        def readline(self):
            return next(self.lines)

        def close(self):
            pass

    class FakeProcess:
        pid = 123

        def __init__(self, command, **kwargs):
            self.command = command
            self.kwargs = kwargs
            self.stdout = FakeStdout()
            self.terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(zrok, "run_cmd", lambda command, live=True: run_calls.append((command, live)))
    monkeypatch.setattr(zrok, "preprocess_command", lambda command, shell=True: command)
    monkeypatch.setattr(zrok.subprocess, "Popen", FakeProcess)

    tunnel = zrok.ZrokTunnel(7860, tmp_path, zrok_token="token")
    monkeypatch.setattr(tunnel, "_install_zrok", lambda: zrok_bin)

    assert tunnel.start() == "https://rp123.shares.zrok.io"
    assert run_calls == [([zrok_bin.as_posix(), "enable", "token"], True)]
    assert getattr(tunnel._process, "command") == [zrok_bin.as_posix(), "share", "public", "7860", "--headless"]

    tunnel.stop()
    assert run_calls[-1] == ([zrok_bin.as_posix(), "disable"], False)
    assert getattr(tunnel._process, "terminated") is True


def test_zrok_start_wraps_enable_failure(monkeypatch, tmp_path):
    tunnel = zrok.ZrokTunnel(7860, tmp_path, zrok_token="token")
    zrok_bin = tmp_path / "zrok"
    monkeypatch.setattr(tunnel, "_install_zrok", lambda: zrok_bin)
    monkeypatch.setattr(zrok, "run_cmd", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("enable bad")))

    with pytest.raises(RuntimeError, match="初始化 Zrok 配置失败"):
        tunnel.start()
