"""内网穿透管理器测试"""

import pytest

from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.tunnel import manager as tunnel_manager


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
