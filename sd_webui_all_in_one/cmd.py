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

from sd_webui_all_in_one.utils import in_jupyter
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def preprocess_command(
    command: list[str] | str,
    shell: bool,
) -> list[str] | str:
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
    custom_env: dict[str, str] | None = None,
    live: bool | None = True,
    shell: bool | None = None,
    cwd: Path | None = None,
    check: bool | None = True,
) -> str | None:
    """执行 Shell 命令

    Args:
        command (str | list[str]):
            要执行的命令
        custom_env (dict[str, str] | None):
            自定义环境变量
        live (bool | None):
            是否实时输出命令执行日志
        shell (bool | None):
            是否使用内置 Shell 执行命令
        cwd (Path | str | None):
            执行进程时的起始路径
        check (bool | None):
            检查进程退出状态, 当异常退出时引发 RuntimeError
    Returns:
        (str | None):
            命令执行时输出的内容, 当 live=True / 执行命令发生错误时输出内容为 None
    Raises:
        RuntimeError:
            当命令执行失败时
    """

    def _run_in_jupyter(
        command: str | list[str],
        custom_env: dict[str, str] | None = None,
        shell: bool | None = None,
        cwd: Path | None = None,
    ) -> subprocess.Popen:
        process = subprocess.Popen(
            command,
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
            print(line, end="", flush=True)
            if sys.stdout and hasattr(sys.stdout, "flush"):
                sys.stdout.flush()

        process.wait()
        return process

    if shell is None:
        shell = sys.platform != "win32"

    if custom_env is None:
        custom_env = os.environ.copy()

    command_to_exec = preprocess_command(command=command, shell=shell)

    kwargs = {
        "args": command_to_exec,
        "shell": shell,
        "env": custom_env,
        "cwd": cwd,
        "encoding": "utf-8",
        "errors": "ignore",
    }

    if not live:
        kwargs["stdout"] = kwargs["stderr"] = subprocess.PIPE

    logger.debug("执行命令的参数: %s", kwargs)

    if live and in_jupyter():
        logger.debug("使用 _run_in_jupyter() 执行命令")
        result = _run_in_jupyter(
            command=command_to_exec,
            custom_env=custom_env,
            shell=shell,
            cwd=cwd,
        )
    else:
        logger.debug("使用 subprocess.run() 执行命令")
        result: subprocess.CompletedProcess[str] = subprocess.run(**kwargs)  # pylint: disable=subprocess-run-check

    if check and result.returncode != 0:
        errors = [
            "执行命令时发生错误",
            f"命令: {command_to_exec}",
            f"错误代码: {result.returncode}",
        ]
        if result.stdout:
            errors.append(f"标准输出: {result.stdout}")
        if result.stderr:
            errors.append(f"错误输出: {result.stderr}")

        raise RuntimeError("\n".join(errors))

    return result.stdout
