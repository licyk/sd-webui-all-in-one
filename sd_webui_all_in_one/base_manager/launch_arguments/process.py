"""启动参数帮助命令子进程的运行与取消"""

from __future__ import annotations

import atexit
import os
import signal
import subprocess
import threading

from sd_webui_all_in_one.base_manager.launch_arguments.models import (
    MAX_DIAGNOSTIC_OUTPUT,
    LaunchArgumentDiagnostic,
    LaunchArgumentDiscoveryContext,
    HelpCommand,
)


_ACTIVE_PROCESSES: set[subprocess.Popen[str]] = set()
_ACTIVE_PROCESSES_LOCK = threading.Lock()


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=1)
    except (OSError, subprocess.TimeoutExpired):
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            pass


def cancel_launch_argument_discovery() -> None:
    """在 API 或进程关闭时终止所有进行中的发现子进程。"""
    with _ACTIVE_PROCESSES_LOCK:
        processes = list(_ACTIVE_PROCESSES)
    for process in processes:
        _terminate_process(process)


atexit.register(cancel_launch_argument_discovery)


def _normalize_process_output(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def _run_help(
    command: HelpCommand,
    context: LaunchArgumentDiscoveryContext,
) -> tuple[str, str, LaunchArgumentDiagnostic | None]:
    try:
        process = subprocess.Popen(
            command.argv,
            cwd=context.webui_path,
            env=command.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=os.name == "posix",
        )
    except OSError as error:
        return "", "", LaunchArgumentDiagnostic("error", "discovery_unavailable", "Unable to start WebUI help discovery", str(error))
    with _ACTIVE_PROCESSES_LOCK:
        _ACTIVE_PROCESSES.add(process)
    try:
        try:
            stdout, stderr = process.communicate(timeout=context.timeout_seconds)
        except subprocess.TimeoutExpired:
            _terminate_process(process)
            stdout, stderr = process.communicate()
            detail = (stdout + "\n" + stderr).strip()[-MAX_DIAGNOSTIC_OUTPUT:] or None
            return (
                "",
                "",
                LaunchArgumentDiagnostic(
                    "error",
                    "discovery_timeout",
                    f"WebUI help discovery exceeded {context.timeout_seconds:g} seconds",
                    detail,
                ),
            )
    finally:
        with _ACTIVE_PROCESSES_LOCK:
            _ACTIVE_PROCESSES.discard(process)
    stdout = _normalize_process_output(stdout)
    stderr = _normalize_process_output(stderr)
    if process.returncode not in (0, None) and not stdout and not stderr:
        return "", "", LaunchArgumentDiagnostic("error", "discovery_failed", f"WebUI help discovery exited with code {process.returncode}")
    return stdout, stderr, None
