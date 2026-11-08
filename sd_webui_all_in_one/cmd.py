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
from typing import Any, Literal, overload

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

DEFAULT_SUBPROCESS_SHELL = sys.platform != "win32"

CREATE_NO_WINDOW = 0x08000000
"""Windows 进程创建标志: 为控制台程序创建不显示窗口的控制台"""


def _windows_console_attached() -> bool:
    """检查当前 Windows 进程是否附加了控制台

    Returns:
        bool: 已附加控制台或无法判断时返回 True
    """
    try:
        import ctypes

        return bool(getattr(ctypes, "windll").kernel32.GetConsoleWindow())
    except (AttributeError, OSError):
        return True


def captured_process_kwargs() -> dict[str, Any]:
    """生成捕获输出 (不实时显示) 的子进程额外参数

    捕获输出的命令无法向用户显示提示, 因此不继承标准输入, 避免子进程等待输入而挂起。
    Windows 上当前进程未附加控制台 (如 GUI 程序) 时, 每个控制台子进程都会新建可见的控制台窗口,
    此时使用 ``CREATE_NO_WINDOW`` 隐藏窗口; 已附加控制台时子进程直接共享该控制台, 不额外设置。

    Returns:
        dict[str, Any]: ``subprocess`` 参数
    """
    kwargs: dict[str, Any] = {"stdin": subprocess.DEVNULL}
    if sys.platform == "win32" and not _windows_console_attached():
        kwargs["creationflags"] = CREATE_NO_WINDOW
    return kwargs


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


@overload
def run_cmd(
    command: str | list[str],
    custom_env: dict[str, str] | None = None,
    *,
    live: Literal[False],
    shell: bool = DEFAULT_SUBPROCESS_SHELL,
    cwd: Path | None = None,
    check: bool = True,
    timeout: float | None = None,
) -> str:
    """执行 Shell 命令并返回标准输出。

    Args:
        command (str | list[str]):
            要执行的命令
        custom_env (dict[str, str] | None):
            自定义环境变量
        live (Literal[False]):
            是否实时输出命令执行日志
        shell (bool):
            是否使用内置 Shell 执行命令
        cwd (Path | None):
            执行进程时的起始路径
        check (bool):
            检查进程退出状态
        timeout (float | None):
            子进程执行超时时间（秒）

    Returns:
        str:
            捕获的标准输出, 不实时输出子进程日志
    """
    ...


@overload
def run_cmd(
    command: str | list[str],
    custom_env: dict[str, str] | None = None,
    live: Literal[True] = True,
    shell: bool = DEFAULT_SUBPROCESS_SHELL,
    cwd: Path | None = None,
    check: bool = True,
    timeout: float | None = None,
) -> None:
    """执行 Shell 命令并实时输出日志。

    Args:
        command (str | list[str]):
            要执行的命令
        custom_env (dict[str, str] | None):
            自定义环境变量
        live (Literal[True]):
            是否实时输出命令执行日志
        shell (bool):
            是否使用内置 Shell 执行命令
        cwd (Path | None):
            执行进程时的起始路径
        check (bool):
            检查进程退出状态
        timeout (float | None):
            子进程执行超时时间（秒）

    Returns:
        None:
            日志已实时输出, 不返回日志内容
    """
    ...


def run_cmd(
    command: str | list[str],
    custom_env: dict[str, str] | None = None,
    live: bool = True,
    shell: bool = DEFAULT_SUBPROCESS_SHELL,
    cwd: Path | None = None,
    check: bool = True,
    timeout: float | None = None,
) -> str | None:
    """执行 Shell 命令

    Args:
        command (str | list[str]):
            要执行的命令
        custom_env (dict[str, str] | None):
            自定义环境变量
        live (bool):
            是否实时输出命令执行日志
        shell (bool):
            是否使用内置 Shell 执行命令
        cwd (Path | None):
            执行进程时的起始路径
        check (bool):
            检查进程退出状态, 当异常退出时引发 RuntimeError
        timeout (float | None):
            子进程执行超时时间（秒）
    Returns:
        (str | None):
            live=True 时实时输出日志并返回 None; live=False 时返回捕获的标准输出, 不实时输出子进程日志
    Raises:
        RuntimeError:
            当命令执行失败时
    """

    def _run_in_jupyter(
        command: str | list[str],
        custom_env: dict[str, str] | None = None,
        shell: bool = DEFAULT_SUBPROCESS_SHELL,
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

        if process.stdout is None:
            return process

        for line in process.stdout:
            print(line, end="", flush=True)
            if sys.stdout and hasattr(sys.stdout, "flush"):
                sys.stdout.flush()

        process.wait()
        return process

    if custom_env is None:
        custom_env = os.environ.copy()

    command_to_exec = preprocess_command(command=command, shell=shell)

    kwargs: dict[str, Any] = {
        "args": command_to_exec,
        "shell": shell,
        "env": custom_env,
        "cwd": cwd,
        "encoding": "utf-8",
        "errors": "ignore",
    }

    if not live:
        kwargs["stdout"] = kwargs["stderr"] = subprocess.PIPE
        kwargs.update(captured_process_kwargs())
    if timeout is not None:
        kwargs["timeout"] = timeout

    logger.debug("执行命令的参数: %s", kwargs)

    if live and in_jupyter() and timeout is None:
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

    return result.stdout if isinstance(result.stdout, str) else None
