"""WebUI 启动与环境检查任务测试"""

import os

import pytest

from sd_webui_all_in_one.base_manager import base as base_module
from sd_webui_all_in_one.base_manager.base import environment as base_environment
from sd_webui_all_in_one.base_manager.base import runtime as base_runtime
from sd_webui_all_in_one.custom_exceptions import WebUiRuntimeError


def test_launch_webui_builds_command_env_and_wraps_runtime_errors(monkeypatch, tmp_path):
    webui = tmp_path / "webui"
    webui.mkdir()
    (webui / "launch.py").write_text("print('ok')", encoding="utf-8")
    captured = {}
    events = []

    def fake_run_process_tree(command, custom_env=None, cwd=None):
        events.append("run")
        captured["command"] = command
        captured["custom_env"] = custom_env
        captured["cwd"] = cwd

    def fake_print_divider(char=None):
        events.append(("divider", char))

    monkeypatch.setattr(base_runtime, "run_process_tree", fake_run_process_tree)
    monkeypatch.setattr(base_runtime, "print_divider", fake_print_divider)
    base_module.launch_webui(webui, "launch.py", launch_args=["--api"], custom_env={"PYTHONPATH": "existing"})

    assert captured["command"][-2:] == [(webui / "launch.py").as_posix(), "--api"]
    assert captured["cwd"] == webui
    assert captured["custom_env"]["PYTHONPATH"].split(os.pathsep)[:2] == [webui.as_posix(), "existing"]
    assert events == [("divider", "="), "run", ("divider", "=")]

    def fail_run_process_tree(*_args, **_kwargs):
        events.append("run_fail")
        raise RuntimeError("boom")

    monkeypatch.setattr(base_runtime, "run_process_tree", fail_run_process_tree)
    events.clear()

    with pytest.raises(WebUiRuntimeError) as exc:
        base_module.launch_webui(webui, "launch.py", webui_name="Demo")

    assert "Demo" in str(exc.value)
    assert "boom" in str(exc.value)
    assert events == [("divider", "="), "run_fail", ("divider", "=")]


def test_run_env_check_tasks_filters_and_aggregates_errors():
    class CheckName(base_module.EnvCheckName):
        ALPHA = "alpha"
        BETA = "beta"
        FAIL = "fail"

    calls = []

    def record(name):
        calls.append(name)

    def fail():
        calls.append("fail")
        raise RuntimeError("boom")

    tasks: list[base_module.EnvCheckTask[CheckName]] = [
        base_module.EnvCheckTask(CheckName.ALPHA, record, {"name": "alpha"}),
        base_module.EnvCheckTask(CheckName.BETA, record, {"name": "beta"}),
        base_module.EnvCheckTask(CheckName.FAIL, fail, {}),
    ]

    base_module.run_env_check_tasks(tasks, include_checks=["alpha", "fail"], exclude_checks=["fail"], error_message="failed")
    assert calls == ["alpha"]

    with pytest.raises(ValueError, match="missing"):
        base_module.run_env_check_tasks(tasks, include_checks=["missing"], error_message="failed")

    with pytest.raises(base_environment.AggregateError) as exc:
        base_module.run_env_check_tasks(tasks, include_checks=["fail"], error_message="failed")
    assert calls == ["alpha", "fail"]
    assert len(exc.value.exceptions) == 1
