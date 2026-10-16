"""命令预处理与执行测试"""

import shlex
import subprocess
import sys

import pytest

from sd_webui_all_in_one import cmd as cmd_module


def test_preprocess_command_platform_rules(monkeypatch):
    monkeypatch.setattr(cmd_module.sys, "platform", "linux")
    assert cmd_module.preprocess_command(["python", "-c", "print(1)"], shell=True) == shlex.join(["python", "-c", "print(1)"])
    assert cmd_module.preprocess_command("python -V", shell=False) == ["python", "-V"]

    monkeypatch.setattr(cmd_module.sys, "platform", "darwin")
    assert cmd_module.preprocess_command(["python", "-V"], shell=False) == ["python", "-V"]

    command = ["python", "-V"]
    monkeypatch.setattr(cmd_module.sys, "platform", "win32")
    assert cmd_module.preprocess_command(command, shell=True) is command


def test_run_cmd_returns_output_and_raises_on_nonzero(monkeypatch):
    monkeypatch.setattr(cmd_module, "in_jupyter", lambda: False)
    calls = []

    def fake_run(**kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(args=kwargs["args"], returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(cmd_module.subprocess, "run", fake_run)

    assert cmd_module.run_cmd(["python", "-V"], live=False, shell=False, timeout=4.0) == "ok\n"
    assert calls[0]["stdout"] == subprocess.PIPE
    assert calls[0]["stderr"] == subprocess.PIPE
    assert calls[0]["timeout"] == 4.0

    def fake_fail(**kwargs):
        return subprocess.CompletedProcess(args=kwargs["args"], returncode=7, stdout="bad out", stderr="bad err")

    monkeypatch.setattr(cmd_module.subprocess, "run", fake_fail)

    with pytest.raises(RuntimeError) as exc:
        cmd_module.run_cmd("python -V", live=False, shell=False)

    assert "bad out" in str(exc.value)
    assert "bad err" in str(exc.value)


def test_run_cmd_enforces_subprocess_timeout():
    with pytest.raises(subprocess.TimeoutExpired):
        cmd_module.run_cmd(
            [sys.executable, "-c", "import time; time.sleep(1)"],
            live=False,
            shell=False,
            timeout=0.05,
        )
