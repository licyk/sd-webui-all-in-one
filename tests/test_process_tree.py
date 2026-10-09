"""Integration tests for cross-platform process tree cleanup."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from sd_webui_all_in_one import process_tree
from sd_webui_all_in_one.custom_exceptions import ProcessTreeTerminated


REPO_ROOT = Path(__file__).parents[1]

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal based integration tests")

# Simulated WebUI: spawns a grandchild that ignores SIGINT, then either exits
# immediately or waits for Ctrl+C. Both paths deliberately leave the grandchild running.
CHILD_SCRIPT = textwrap.dedent(
    """
    import os, signal, subprocess, sys, time
    from pathlib import Path

    out = Path(sys.argv[1])
    mode = sys.argv[2]
    grandchild_code = (
        "import signal, time\\n"
        "signal.signal(signal.SIGINT, signal.SIG_IGN)\\n"
        + ("signal.signal(signal.SIGTERM, signal.SIG_IGN)\\n" if "stubborn" in mode else "")
        + "while True: time.sleep(0.1)\\n"
    )
    grandchild = subprocess.Popen([sys.executable, "-c", grandchild_code])
    (out / "grandchild.pid").write_text(str(grandchild.pid))
    if mode.startswith("exit"):
        sys.exit(int(sys.argv[3]) if len(sys.argv) > 3 else 0)
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        (out / "child.interrupted").write_text("1")
    """
)

# Launcher process that runs the simulated WebUI through run_process_tree().
HARNESS_SCRIPT = textwrap.dedent(
    """
    import sys
    from sd_webui_all_in_one.process_tree import run_process_tree

    child, out, mode, graceful = sys.argv[1:5]
    try:
        run_process_tree([sys.executable, child, out, mode], graceful_timeout=float(graceful))
    except KeyboardInterrupt:
        sys.exit(42)
    """
)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    stat = Path(f"/proc/{pid}/stat")
    if stat.exists():
        try:
            return stat.read_text().rsplit(")", 1)[1].split()[0] != "Z"
        except OSError:
            return False
    return True


def _wait_for(predicate, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


def _read_pid(path: Path) -> int:
    assert _wait_for(lambda: path.exists() and path.read_text().strip() != ""), f"{path} was not written"
    return int(path.read_text())


@pytest.fixture
def child_script(tmp_path: Path) -> Path:
    script = tmp_path / "child.py"
    script.write_text(CHILD_SCRIPT, encoding="utf-8")
    return script


def _start_harness(child_script: Path, out: Path, mode: str, graceful: float = 5.0) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [REPO_ROOT.as_posix(), env.get("PYTHONPATH")]))
    return subprocess.Popen(
        [sys.executable, "-c", HARNESS_SCRIPT, str(child_script), str(out), mode, str(graceful)],
        cwd=REPO_ROOT,
        env=env,
        start_new_session=True,
    )


def test_cleans_up_descendants_after_child_exits(child_script: Path, tmp_path: Path):
    returncode = process_tree.run_process_tree([sys.executable, str(child_script), str(tmp_path), "exit", "0"])

    assert returncode == 0
    grandchild = _read_pid(tmp_path / "grandchild.pid")
    assert _wait_for(lambda: not _pid_alive(grandchild), timeout=5)


def test_non_zero_exit_raises_runtime_error_after_cleanup(child_script: Path, tmp_path: Path):
    with pytest.raises(RuntimeError, match="错误代码: 3"):
        process_tree.run_process_tree([sys.executable, str(child_script), str(tmp_path), "exit", "3"])

    assert _wait_for(lambda: not _pid_alive(_read_pid(tmp_path / "grandchild.pid")), timeout=5)
    assert process_tree.run_process_tree([sys.executable, str(child_script), str(tmp_path), "exit", "3"], check=False) == 3


def test_ctrl_c_forwards_sigint_then_cleans_up_tree(child_script: Path, tmp_path: Path):
    harness = _start_harness(child_script, tmp_path, "wait")
    grandchild = _read_pid(tmp_path / "grandchild.pid")

    harness.send_signal(signal.SIGINT)

    assert harness.wait(timeout=20) == 42
    assert (tmp_path / "child.interrupted").exists(), "child should receive the forwarded SIGINT"
    assert _wait_for(lambda: not _pid_alive(grandchild), timeout=5)


def test_sigterm_cleans_up_tree_and_exits_with_signal_code(child_script: Path, tmp_path: Path):
    harness = _start_harness(child_script, tmp_path, "wait")
    grandchild = _read_pid(tmp_path / "grandchild.pid")

    harness.send_signal(signal.SIGTERM)

    assert harness.wait(timeout=20) == 128 + signal.SIGTERM
    assert _wait_for(lambda: not _pid_alive(grandchild), timeout=5)


def test_watchdog_cleans_up_tree_when_launcher_is_killed(child_script: Path, tmp_path: Path):
    harness = _start_harness(child_script, tmp_path, "wait")
    grandchild = _read_pid(tmp_path / "grandchild.pid")

    harness.kill()
    harness.wait(timeout=5)

    assert _wait_for(lambda: not _pid_alive(grandchild), timeout=10)


def test_escalates_to_sigkill_for_processes_ignoring_signals(child_script: Path, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(process_tree, "TERMINATE_TIMEOUT", 0.5)
    started = time.monotonic()

    process_tree.run_process_tree([sys.executable, str(child_script), str(tmp_path), "exit-stubborn"])

    grandchild = _read_pid(tmp_path / "grandchild.pid")
    assert _wait_for(lambda: not _pid_alive(grandchild), timeout=5)
    assert time.monotonic() - started < 10


def test_stubborn_tree_is_killed_after_ctrl_c(child_script: Path, tmp_path: Path):
    harness = _start_harness(child_script, tmp_path, "stubborn", graceful=0.5)
    grandchild = _read_pid(tmp_path / "grandchild.pid")

    harness.send_signal(signal.SIGINT)

    assert harness.wait(timeout=20) == 42
    assert _wait_for(lambda: not _pid_alive(grandchild), timeout=5)


def test_process_tree_terminated_is_system_exit_with_signal_code():
    error = ProcessTreeTerminated(signal.SIGTERM)

    assert isinstance(error, SystemExit)
    assert not isinstance(error, Exception)
    assert error.code == 128 + signal.SIGTERM
    assert error.signum == signal.SIGTERM


def test_streams_output_in_jupyter_and_restores_signal_handlers(monkeypatch, capsys):
    monkeypatch.setattr(process_tree, "in_jupyter", lambda: True)
    previous = signal.getsignal(signal.SIGTERM)

    returncode = process_tree.run_process_tree([sys.executable, "-c", "print('hello from webui')"])

    assert returncode == 0
    assert "hello from webui" in capsys.readouterr().out
    assert signal.getsignal(signal.SIGTERM) is previous
