"""Shell 命令执行器

不同平台下 subprocess 的执行结果不一致, 以下为不同平台的测试结果:
```
Test Platform: linux
Case 1: {'cmd': ['/usr/bin/git', '--version'], 'shell': False} -> Success
Case 2: {'cmd': ['/usr/bin/git', '--version'], 'shell': True} -> Failed
Case 3: {'cmd': '"/usr/bin/git" --version', 'shell': False} -> Failed
Case 4: {'cmd': '"/usr/bin/git" --version', 'shell': True} -> Success
Case 5: {'cmd': ['/usr/bin/git', '--version'], 'shell': False} -> Success
Case 6: {'cmd': ['/usr/bin/git', '--version'], 'shell': True} -> Failed
Case 7: {'cmd': '"/usr/bin/git" --version', 'shell': False} -> Failed
Case 8: {'cmd': '"/usr/bin/git" --version', 'shell': True} -> Success

Test Platform: win32
Case 1: {'cmd': ['C:\\Program Files\\Git\\mingw64\\bin\\git.EXE', '--version'], 'shell': False} -> Success
Case 2: {'cmd': ['C:\\Program Files\\Git\\mingw64\\bin\\git.EXE', '--version'], 'shell': True} -> Success
Case 3: {'cmd': '"C:\\Program Files\\Git\\mingw64\\bin\\git.EXE" --version', 'shell': False} -> Success
Case 4: {'cmd': '"C:\\Program Files\\Git\\mingw64\\bin\\git.EXE" --version', 'shell': True} -> Success
Case 5: {'cmd': ['C:/Program Files/Git/mingw64/bin/git.EXE', '--version'], 'shell': False} -> Success
Case 6: {'cmd': ['C:/Program Files/Git/mingw64/bin/git.EXE', '--version'], 'shell': True} -> Success
Case 7: {'cmd': '"C:/Program Files/Git/mingw64/bin/git.EXE" --version', 'shell': False} -> Success
Case 8: {'cmd': '"C:/Program Files/Git/mingw64/bin/git.EXE" --version', 'shell': True} -> Success

Test Platform: darwin
Case 1: {'cmd': ['/opt/homebrew/bin/git', '--version'], 'shell': False} -> Success
Case 2: {'cmd': ['/opt/homebrew/bin/git', '--version'], 'shell': True} -> Failed
Case 3: {'cmd': '"/opt/homebrew/bin/git" --version', 'shell': False} -> Failed
Case 4: {'cmd': '"/opt/homebrew/bin/git" --version', 'shell': True} -> Success
Case 5: {'cmd': ['/opt/homebrew/bin/git', '--version'], 'shell': False} -> Success
Case 6: {'cmd': ['/opt/homebrew/bin/git', '--version'], 'shell': True} -> Failed
Case 7: {'cmd': '"/opt/homebrew/bin/git" --version', 'shell': False} -> Failed
Case 8: {'cmd': '"/opt/homebrew/bin/git" --version', 'shell': True} -> Success
```

- 对于 Linux 平台, 当使用 Shell=True 时, 应使用字符串命令; Shell=False 时, 使用列表命令
- 对于 Windows 平台, 当使用 Shell=True / Shell=False 时, 使用字符串命令和列表命令都可行
- 对于 MacOS 平台, 当使用 Shell=True 时, 应使用字符串命令; Shell=False 时, 使用列表命令 (行为和 Linux 中的一致)
"""

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


def preprocess_command(command: list[str] | str, shell: bool) -> list[str] | str:
    """针对不同平台对命令进行预处理

    Args:
        command (list[str] | str): 原始命令
        shell (bool): 是否调用 Shell
    Returns:
        (list[str] | str): 处理后的命令
    """
    if sys.platform == "win32":
        # Windows
        # 字符串命令和列表命令都可行
        return command
    else:
        # Linux / MacOS
        if shell:
            # 使用字符串命令
            if isinstance(command, list):
                return shlex.join(command)
            return command
        # 使用列表命令
        if isinstance(command, str):
            return shlex.split(command)
        return command


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

    command_to_exec = preprocess_command(command=command, shell=shell)

    if display_mode is None:
        if in_jupyter():
            display_mode = "jupyter"
        else:
            display_mode = "terminal"

    cwd = Path(cwd) if not isinstance(cwd, Path) and cwd is not None else cwd
    logger.debug("执行命令时使用的显示模式: %s", display_mode)
    logger.debug("使用的输出模式: %s", ("实时输出" if live else "非实时输出"))

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
            result: subprocess.CompletedProcess[str] = subprocess.run(
                command_to_exec,
                shell=shell,
                env=custom_env,
                cwd=cwd,
                bufsize=1,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
            if result.returncode != 0:
                raise RuntimeError(f"""{errdesc or "执行命令时发生错误"}
命令: {command_to_exec}
错误代码: {result.returncode}""")

            try:
                # 当 subprocess.run() 使用 PIPE 捕获输出时, result 才有输出内容
                return result.stdout
            except Exception:
                # 未使用 PIPE 时 subprocess.run() 可以实时输出内容, 但是 result 将为 None
                return None

        logger.warning("未知的显示模式: %s, 将切换到非实时输出模式", display_mode)

    # 非实时输出模式
    result: subprocess.CompletedProcess[bytes] = subprocess.run(
        command_to_exec,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=shell,
        env=custom_env,
        cwd=cwd,
        bufsize=1,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    if result.returncode != 0:
        message = f"""{errdesc or "执行命令时发生错误"}
命令: {command_to_exec}
错误代码: {result.returncode}
标准输出: {result.stdout if len(result.stdout) > 0 else ""}
错误输出: {result.stderr if len(result.stderr) > 0 else ""}
"""
        raise RuntimeError(message)

    return result.stdout
