"""代理配置测试"""

import os
import socket
import sys
import types
from pathlib import Path

from sd_webui_all_in_one import proxy


def test_proxy_platform_parsers_and_env(monkeypatch, tmp_path):
    class FakeReg:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    fake_winreg = types.SimpleNamespace(
        HKEY_CURRENT_USER=1,
        KEY_READ=2,
        OpenKey=lambda *_args: FakeReg(),
        QueryValueEx=lambda _reg, name: (1, None) if name == "ProxyEnable" else ("http=127.0.0.1:7890;socks=127.0.0.1:1080", None),
    )
    monkeypatch.setitem(sys.modules, "winreg", fake_winreg)
    assert proxy.get_windows_proxy_address() == "http://127.0.0.1:7890"

    gsettings = {
        ("gsettings", "get", "org.gnome.system.proxy", "mode"): "'manual'\n",
        ("gsettings", "get", "org.gnome.system.proxy.http", "host"): "'localhost'\n",
        ("gsettings", "get", "org.gnome.system.proxy.http", "port"): "8080\n",
    }
    monkeypatch.setattr(proxy, "run_cmd", lambda command, live=False: gsettings[tuple(command)])
    assert proxy.get_linux_proxy_address() == "http://localhost:8080"

    monkeypatch.setattr(proxy, "run_cmd", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("no gsettings")))
    kde_config = tmp_path / ".config" / "kioslaverc"
    kde_config.parent.mkdir()
    kde_config.write_text("[Proxy Settings]\nProxyType=1\nsocksProxy=socks://127.0.0.1 1080\n", encoding="utf-8")
    monkeypatch.setattr(proxy, "Path", lambda value: kde_config if value == "~/.config/kioslaverc" else Path(value))
    assert proxy.get_linux_proxy_address() == "socks://127.0.0.1:1080"

    mac_output = "HTTPSEnable : 1\nHTTPSProxy : proxy.local\nHTTPSPort : 4443\n"
    monkeypatch.setattr(proxy, "run_cmd", lambda *_args, **_kwargs: mac_output)
    assert proxy.get_macos_proxy_address() == "http://proxy.local:4443"

    monkeypatch.setattr(proxy.sys, "platform", "darwin")
    assert proxy.get_system_proxy_address() == "http://proxy.local:4443"

    proxy.set_proxy("http://proxy.local:8080")
    assert os.environ["HTTP_PROXY"] == "http://proxy.local:8080"
    assert os.environ["HTTPS_PROXY"] == "http://proxy.local:8080"
    proxy.clean_proxy()
    assert "HTTP_PROXY" not in os.environ
    assert "HTTPS_PROXY" not in os.environ

    proxy.clean_proxy()
    proxy.set_proxy("https://proxy.local:8443")
    proxy.set_proxy("https://proxy.local:8443")
    assert os.environ["HTTP_PROXY"] == "https://proxy.local:8443"
    assert os.environ["HTTPS_PROXY"] == "https://proxy.local:8443"
    proxy.clean_proxy()
    proxy.clean_proxy()
    assert "HTTP_PROXY" not in os.environ
    assert "HTTPS_PROXY" not in os.environ


def test_proxy_connectivity_uses_tcp_socket(monkeypatch):
    events = []

    class FakeSocket:
        def settimeout(self, timeout):
            events.append(("timeout", timeout))

        def connect(self, address):
            events.append(("connect", address))

        def close(self):
            events.append("close")

    monkeypatch.setattr(proxy.socket, "socket", lambda *_args: FakeSocket())
    assert proxy.test_proxy_connectivity("http://127.0.0.1:7890", timeout=2) is True
    assert ("connect", ("127.0.0.1", 7890)) in events

    assert proxy.test_proxy_connectivity("not-a-proxy") is False

    class BadSocket(FakeSocket):
        def connect(self, address):
            raise socket.error("closed")

    monkeypatch.setattr(proxy.socket, "socket", lambda *_args: BadSocket())
    assert proxy.test_proxy_connectivity("socks://127.0.0.1:1080") is False
