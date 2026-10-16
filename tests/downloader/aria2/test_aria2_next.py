"""aria2-next 后端测试"""

import subprocess
import sys
import types

import pytest

from sd_webui_all_in_one.downloader import aria2_server


def test_aria2_next_find_executable_uses_package_finder(monkeypatch):
    monkeypatch.setattr(aria2_server.shutil, "which", lambda _name: None)
    monkeypatch.setattr(aria2_server, "get_aria2_next_version", lambda _exe: "3.0.4")
    fake_module = types.ModuleType("aria2_next")
    fake_module.find_aria2_next_bin = lambda: "/venv/bin/aria2-next"
    monkeypatch.setitem(sys.modules, "aria2_next", fake_module)

    assert aria2_server.Aria2NextRpcServer.find_executable() == "/venv/bin/aria2-next"

    def raise_not_found():
        raise FileNotFoundError("missing")

    fake_module.find_aria2_next_bin = raise_not_found
    assert aria2_server.Aria2NextRpcServer.find_executable() is None

    monkeypatch.setattr(aria2_server.shutil, "which", lambda name: "/usr/bin/aria2-next" if name == "aria2-next" else None)
    assert aria2_server.Aria2NextRpcServer.find_executable() == "/usr/bin/aria2-next"


def test_aria2_next_find_executable_skips_outdated_versions(monkeypatch):
    versions = {"/usr/bin/aria2-next": "2.8.6", "/venv/bin/aria2-next": "3.1.0"}
    monkeypatch.setattr(aria2_server.shutil, "which", lambda name: "/usr/bin/aria2-next" if name == "aria2-next" else None)
    monkeypatch.setattr(aria2_server, "get_aria2_next_version", versions.get)
    fake_module = types.ModuleType("aria2_next")
    fake_module.find_aria2_next_bin = lambda: "/venv/bin/aria2-next"
    monkeypatch.setitem(sys.modules, "aria2_next", fake_module)

    assert aria2_server.Aria2NextRpcServer.find_executable() == "/venv/bin/aria2-next"

    versions["/venv/bin/aria2-next"] = "3.0.3"
    assert aria2_server.Aria2NextRpcServer.find_executable() is None

    versions["/venv/bin/aria2-next"] = None
    assert aria2_server.Aria2NextRpcServer.find_executable() is None


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        ("aria2-next version 3.0.4\nCopyright\n", "3.0.4"),
        ("Aria2 Next version 2.8.6\nMaintained since 2026\n", "2.8.6"),
        ("aria2 version 1.37.0\n", None),
    ],
)
def test_get_aria2_next_version_parses_output(monkeypatch, stdout, expected):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(aria2_server.subprocess, "run", fake_run)

    assert aria2_server.get_aria2_next_version("/bin/aria2-next") == expected
    assert calls == [["/bin/aria2-next", "--version"]]


def test_get_aria2_next_version_handles_launch_error(monkeypatch):
    def fake_run(*_args, **_kwargs):
        raise OSError("exec format error")

    monkeypatch.setattr(aria2_server.subprocess, "run", fake_run)

    assert aria2_server.get_aria2_next_version("/bin/aria2-next") is None


def test_make_download_gid_is_stable_per_path(tmp_path):
    gid = aria2_server.make_download_gid(tmp_path / "model.safetensors")

    assert gid == aria2_server.make_download_gid(tmp_path / "model.safetensors")
    assert gid != aria2_server.make_download_gid(tmp_path / "other.safetensors")
    assert len(gid) == 16
    int(gid, 16)


def test_aria2_next_prepares_download_options(tmp_path):
    server = aria2_server.Aria2NextRpcServer(download_dir=tmp_path)
    rpc_calls = []

    def fake_rpc(method, params=None, retry_count=3):
        rpc_calls.append((method, params, retry_count))
        raise RuntimeError("GID is not found")

    server._rpc_call = fake_rpc
    options = {
        "dir": tmp_path.as_posix(),
        "out": "a.bin",
        "split": "32",
        "max-connection-per-server": "16",
        "min-split-size": "1048576",
        "piece-length": "1048576",
        "allow-piece-length-change": "false",
        "always-resume": "true",
        "conditional-get": "false",
        "max-resume-failure-tries": "0",
        "continue": "true",
    }

    prepared = server._prepare_download_options(["https://example.test/a.bin"], options)

    gid = aria2_server.make_download_gid(tmp_path / "a.bin")
    assert prepared == {
        "dir": tmp_path.as_posix(),
        "out": "a.bin",
        "split": "32",
        "max-connection-per-server": "16",
        "min-split-size": "1048576",
        "continue": "true",
        "gid": gid,
    }
    assert "piece-length" in options
    assert rpc_calls == [("aria2.removeDownloadResult", [gid], 1)]

    without_out = server._prepare_download_options(["https://example.test/files/b.bin?x=1"], {"dir": tmp_path.as_posix()})
    assert without_out["gid"] == aria2_server.make_download_gid(tmp_path / "b.bin")

    rpc_calls.clear()
    explicit = server._prepare_download_options(["https://example.test/a.bin"], {"dir": tmp_path.as_posix(), "gid": "0123456789abcdef"})
    assert explicit["gid"] == "0123456789abcdef"
    assert rpc_calls == []

    aria2c_server = aria2_server.Aria2cRpcServer(download_dir=tmp_path)
    assert aria2c_server._prepare_download_options(["https://example.test/a.bin"], options) == options


def test_aria2_next_download_sends_prepared_options(tmp_path):
    server = aria2_server.Aria2NextRpcServer(download_dir=tmp_path)
    calls = []

    def fake_rpc(method, params=None, retry_count=3):
        calls.append((method, params))
        return "OK" if method == "aria2.removeDownloadResult" else "gid-1"

    server._rpc_call = fake_rpc
    server.download("https://example.test/a.bin", save_path=tmp_path, options={"split": "4", "always-resume": "true"}, wait_complete=False)

    gid = aria2_server.make_download_gid(tmp_path / "a.bin")
    assert calls == [
        ("aria2.removeDownloadResult", [gid]),
        ("aria2.addUri", [["https://example.test/a.bin"], {"dir": tmp_path.as_posix(), "split": "4", "gid": gid}]),
    ]


@pytest.mark.parametrize("use_config_file", [True, False])
def test_aria2_next_start_uses_own_config_and_persistent_state_dir(monkeypatch, tmp_path, use_config_file):
    commands = []

    class FakeProcess:
        stderr = None

        def __init__(self, command, **_kwargs):
            commands.append(command)

        def poll(self):
            return None

        def wait(self, timeout=None):
            return 0

    state_dir = tmp_path / "cache" / "aria2-next"
    monkeypatch.setattr(aria2_server, "ARIA2_NEXT_STATE_PATH", state_dir)
    monkeypatch.setattr(aria2_server.Aria2NextRpcServer, "find_executable", classmethod(lambda _cls: "/venv/bin/aria2-next"))
    monkeypatch.setattr(aria2_server, "is_port_in_use", lambda _port: False)
    monkeypatch.setattr(aria2_server.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(aria2_server.Aria2RpcServer, "_test_connection", lambda _self: True)

    server = aria2_server.Aria2NextRpcServer(port=6800, download_dir=tmp_path, use_config_file=use_config_file, use_external_server=False)
    server._start_server()

    command = commands[0]
    assert command[0] == "/venv/bin/aria2-next"
    if use_config_file:
        assert f"--conf-path={aria2_server.ARIA2_NEXT_CONFIG_PATH.as_posix()}" in command
    else:
        assert "--split=32" in command
        assert not any(arg.startswith("--piece-length=") for arg in command)
    assert f"--state-dir={state_dir.as_posix()}" in command
    assert state_dir.is_dir()

    server._rpc_call = lambda *_args, **_kwargs: None
    server._stop_server()

    assert state_dir.is_dir()


def test_aria2_next_config_uses_only_native_options():
    config_keys = {line.split("=", 1)[0].strip() for line in aria2_server.ARIA2_NEXT_CONFIG_PATH.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")}
    unsupported_keys = {
        "stream-max-connections",
        "piece-length",
        "disk-cache",
        "no-file-allocation-limit",
        "auto-save-interval",
        "bt-detach-seed-only",
        "bt-tracker-connect-timeout",
        "bt-tracker-timeout",
        "dht-entry-point",
        "dht-entry-point6",
        "enable-dht6",
        "peer-agent",
        "peer-id-prefix",
    }

    assert {"split", "max-connection-per-server", "min-split-size", "state-save-interval"} <= config_keys
    assert not config_keys & unsupported_keys
