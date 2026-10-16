"""内网穿透基类测试"""

import subprocess

from sd_webui_all_in_one.tunnel.base import BaseTunnel


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
