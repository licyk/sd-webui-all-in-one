"""Tests for the CI bounded-process runner."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).parents[1] / ".github" / "run_bounded_process.py"
SPEC = importlib.util.spec_from_file_location("run_bounded_process", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class FakeProcess:
    """Minimal process double with configurable wait results."""

    def __init__(self, waits: list[int | BaseException], pid: int = 4321):
        self.pid = pid
        self.waits = waits
        self.wait_timeouts: list[float | None] = []
        self.returncode: int | None = None
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        self.wait_timeouts.append(timeout)
        result = self.waits.pop(0)
        if isinstance(result, BaseException):
            raise result
        self.returncode = result
        return result

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9


def test_main_returns_child_exit_code_and_uses_requested_cwd(monkeypatch):
    process = FakeProcess([7])
    calls = []
    cwd = Path.cwd()
    monkeypatch.setattr(
        runner.subprocess,
        "Popen",
        lambda command, **kwargs: calls.append((command, kwargs)) or process,
    )

    result = runner.main(
        ["--timeout", "60", "--cwd", str(cwd), "--", "python", "-V"]
    )

    assert result == 7
    assert calls[0][0] == ["python", "-V"]
    assert calls[0][1]["cwd"] == cwd.resolve()
    assert process.wait_timeouts == [60.0]


def test_main_returns_timeout_exit_code_after_forced_termination(monkeypatch):
    process = FakeProcess(
        [
            subprocess.TimeoutExpired(["python", "-c", "pass"], 1),
            0,
        ]
    )
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(runner, "stop_process_tree", lambda target: setattr(target, "killed", True))

    result = runner.main(
        ["--timeout", "1", "--cwd", str(Path.cwd()), "--", "python", "-c", "pass"]
    )

    assert result == runner.TIMEOUT_EXIT_CODE
    assert process.killed is True
    assert process.wait_timeouts == [1.0, runner.STOP_WAIT_SECONDS]


def test_stop_process_tree_uses_taskkill_on_windows(monkeypatch):
    process = FakeProcess([0], pid=9876)
    calls = []
    monkeypatch.setattr(runner.os, "name", "nt")
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda command, **kwargs: calls.append((command, kwargs))
        or subprocess.CompletedProcess(command, 0, stdout=""),
    )

    runner.stop_process_tree(process)

    assert calls == [
        (
            ["taskkill", "/PID", "9876", "/T", "/F"],
            {
                "check": False,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "text": True,
                "encoding": "utf-8",
                "errors": "replace",
            },
        )
    ]
    assert process.killed is True


@pytest.mark.parametrize(
    "argv",
    [
        ["--timeout", "0", "--", "python", "-V"],
        ["--timeout", "1"],
    ],
)
def test_main_rejects_invalid_invocation(argv):
    with pytest.raises(SystemExit):
        runner.main(argv)
