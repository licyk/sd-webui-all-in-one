"""Shell 命令执行器"""

import os
import sys
import shlex
import subprocess
from pathlib import Path
from typing import Literal

from sd_webui_all_in_one.utils import in_jupyter
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL


logger = get_logger(
    name="CMD Runner",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def run_cmd(
    command: str | list[str],
    desc: str | None = None,
    errdesc: str | None = None,
    custom_env: dict[str, str] | None = None,
    live: bool | None = True,
    shell: bool | None = None,
    cwd: Path | str | None = None,
    display_mode: Literal["terminal", "jupyter"] | None = None,
) -> str | None:
    """执行 Shell 命令

    Args:
        command (str | list[str]): 要执行的命令
        desc (str | None): 执行命令的描述
        errdesc (str | None): 执行命令报错时的描述
        custom_env (dict[str, str] | None): 自定义环境变量
        live (bool | None): 是否实时输出命令执行日志
        shell (bool | None): 是否使用内置 Shell 执行命令
        cwd (Path | str | None): 执行进程时的起始路径
        display_mode (Literal["terminal", "jupyter"] | None): 执行子进程时使用的输出模式
    Returns:
        (str | None): 命令执行时输出的内容
    Raises:
        RuntimeError: 当命令执行失败时
    """

    if shell is None:
        shell = sys.platform != "win32"

    if desc is not None:
        logger.info(desc)

    if custom_env is None:
        custom_env = os.environ

    if sys.platform == "win32":
        # 在 Windows 平台上不使用 shlex 处理成字符串
        command_to_exec = command
    else:
        # 把列表转换为字符串, 避免 subprocss 只把使用列表第一个元素作为命令
        command_to_exec = shlex.join(command) if isinstance(command, list) else command

    if display_mode is None:
        if in_jupyter():
            display_mode = "jupyter"
        else:
            display_mode = "terminal"

    cwd = Path(cwd) if not isinstance(cwd, Path) and cwd is not None else cwd

    if live:
        if display_mode == "jupyter":
            process_output = []
            process = subprocess.Popen(
                command_to_exec,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                encoding="utf-8",
                env=custom_env,
                cwd=cwd,
            )

            for line in process.stdout:
                process_output.append(line)
                print(line, end="", flush=True)
                if sys.stdout and hasattr(sys.stdout, "flush"):
                    sys.stdout.flush()

            process.wait()
            if process.returncode != 0:
                raise RuntimeError(f"""{errdesc or "执行命令时发生错误"}
命令: {command_to_exec}
错误代码: {process.returncode}""")

            return "".join(process_output)

        if display_mode == "terminal":
            result: subprocess.CompletedProcess[bytes] = subprocess.run(
                command_to_exec,
                shell=shell,
                env=custom_env,
                cwd=cwd,
            )
            if result.returncode != 0:
                raise RuntimeError(f"""{errdesc or "执行命令时发生错误"}
命令: {command_to_exec}
错误代码: {result.returncode}""")

            return result.stdout.decode(encoding="utf8", errors="ignore")

        logger.warning("未知的显示模式: %s, 将切换到非实时输出模式", display_mode)

    # 非实时输出模式
    result: subprocess.CompletedProcess[bytes] = subprocess.run(
        command_to_exec,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=shell,
        env=custom_env,
        cwd=cwd,
    )

    if result.returncode != 0:
        message = f"""{errdesc or "执行命令时发生错误"}
命令: {command_to_exec}
错误代码: {result.returncode}
标准输出: {result.stdout.decode(encoding="utf8", errors="ignore") if len(result.stdout) > 0 else ""}
错误输出: {result.stderr.decode(encoding="utf8", errors="ignore") if len(result.stderr) > 0 else ""}
"""
        raise RuntimeError(message)

    return result.stdout.decode(encoding="utf8", errors="ignore")
