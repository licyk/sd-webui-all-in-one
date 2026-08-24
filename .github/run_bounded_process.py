"""Run a command with a bounded lifetime for CI initialization steps."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
from pathlib import Path


TIMEOUT_EXIT_CODE = 124
LAUNCH_ERROR_EXIT_CODE = 125
STOP_WAIT_SECONDS = 15


def stop_process_tree(process: subprocess.Popen[object]) -> None:
    """Force-stop the launched process and every process below it."""
    if process.poll() is not None:
        return

    if os.name == "nt":
        result = subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            detail = result.stdout.strip()
            print(
                "::warning::taskkill could not fully terminate the process "
                f"tree rooted at PID {process.pid}: {detail}",
                flush=True,
            )
        try:
            process.kill()
        except OSError:
            pass
        return

    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def main(argv: list[str] | None = None) -> int:
    """Run the requested command and return its exit status."""
    parser = argparse.ArgumentParser(
        description="Run a command and terminate its process tree after a timeout."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        required=True,
        help="Maximum command runtime in seconds.",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="Working directory for the command.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("command is required; put it after --")

    cwd = args.cwd.resolve()
    if not cwd.is_dir():
        parser.error(f"working directory does not exist: {cwd}")

    popen_kwargs: dict[str, object] = {"cwd": cwd}
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    print(
        f"::notice::Launching bounded process; timeout={args.timeout}s; "
        f"cwd={cwd}; command={command}",
        flush=True,
    )

    try:
        process = subprocess.Popen(command, **popen_kwargs)
    except OSError as error:
        print(f"::error::Unable to launch command: {error}", flush=True)
        return

    try:
        return process.wait(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        print(
            f"::warning::Timed out after {args.timeout}s; stopping process "
            f"tree rooted at PID {process.pid}.",
            flush=True,
        )
        try:
            stop_process_tree(process)
        except OSError as error:
            print(f"::error::Unable to stop process tree: {error}", flush=True)

        try:
            process.wait(timeout=STOP_WAIT_SECONDS)
        except subprocess.TimeoutExpired:
            print(
                f"::error::Process PID {process.pid} still did not exit after "
                "forced tree termination.",
                flush=True,
            )


if __name__ == "__main__":
    main()
