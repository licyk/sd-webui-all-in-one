"""跨平台进程树管理

启动 WebUI 时, WebUI 进程还可能继续创建子进程 (例如 Gradio 子进程, 训练进程, TensorBoard 等)。
当启动器被 Ctrl+C 中断, 收到终止信号或者直接崩溃时, 需要保证整个进程树都被清理, 避免残留进程占用端口和显存。

不同平台下的实现方式:
```
Linux / MacOS:
    - 子进程使用 start_new_session 运行在独立的会话和进程组中, 通过 os.killpg() 向整个进程组发送信号
    - 由于子进程不在终端的前台进程组中, 终端的 Ctrl+C 只会发送给启动器, 再由启动器转发 SIGINT 给子进程组
    - 启动器额外启动一个看门狗进程, 通过管道检测启动器是否存活
      当启动器崩溃或被 SIGKILL 杀死时, 管道被内核关闭, 看门狗收到 EOF 后负责结束子进程组

Windows:
    - 子进程被分配到设置了 JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE 的作业对象 (Job Object) 中
    - 子进程创建的所有后代进程会自动加入同一个作业对象
    - 启动器以任何方式退出 (包括崩溃和被强制结束) 时, 系统会关闭作业对象句柄并结束作业中的所有进程
    - 子进程与启动器共享控制台, 终端的 Ctrl+C 会同时发送给子进程, 启动器只需等待子进程退出
```

已知限制:
- Linux / MacOS 中, 后代进程如果主动调用 setsid() 脱离进程组, 将无法被追踪
- Windows 中, 子进程启动后到加入作业对象之间存在极短的时间窗口, 此时创建的后代进程无法被作业对象追踪
"""

import os
import sys
import time
import signal
import threading
import subprocess
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from types import FrameType
from typing import Any

from sd_webui_all_in_one.utils import in_jupyter
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.custom_exceptions import ProcessTreeTerminated


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

DEFAULT_GRACEFUL_TIMEOUT = 10.0
"""收到中断信号后, 等待进程树自行退出的时间 (秒)"""

TERMINATE_TIMEOUT = 5.0
"""发送终止信号后, 等待进程树退出的时间 (秒)"""

KILL_TIMEOUT = 3.0
"""强制结束后, 等待进程树退出的时间 (秒)"""

POLL_INTERVAL = 0.1
"""轮询进程状态的间隔 (秒)"""

WAIT_SLICE = 0.5
"""等待子进程退出时每次阻塞的时间 (秒), 保证主线程能及时处理信号"""

_WATCHDOG_EXIT_COMMAND = "exit"

# 看门狗进程脚本, 使用 `python -I -S -c` 运行, 只依赖标准库
# 第一行读取需要守护的进程组 ID, 之后阻塞读取直到启动器发送退出命令或管道关闭 (启动器已退出)
_POSIX_WATCHDOG_SCRIPT = f"""
import os, signal, sys, time

def alive(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True

def main():
    try:
        pgid = int(sys.stdin.readline())
    except ValueError:
        return
    if sys.stdin.readline().strip() == {_WATCHDOG_EXIT_COMMAND!r}:
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except OSError:
            return
        deadline = time.monotonic() + {TERMINATE_TIMEOUT!r}
        while time.monotonic() < deadline:
            if not alive(pgid):
                return
            time.sleep({POLL_INTERVAL!r})

main()
"""


def _wait_until(predicate: Callable[[], bool], timeout: float) -> bool:
    """轮询等待条件成立

    Args:
        predicate (Callable[[], bool]):
            等待的条件
        timeout (float):
            最长等待时间 (秒)

    Returns:
        bool:
            条件是否成立
    """
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            return False
        time.sleep(POLL_INTERVAL)
    return True


class _ProcessTree:
    """进程树管理器的基类, 定义各平台需要实现的操作"""

    def popen_kwargs(self) -> dict[str, Any]:
        """获取启动子进程时额外需要的参数

        Returns:
            dict[str, Any]:
                传递给 subprocess.Popen 的参数
        """
        return {}

    def prepare(self) -> None:
        """在启动子进程前准备清理机制"""

    def attach(self, process: subprocess.Popen[str]) -> None:
        """将已启动的子进程纳入管理

        Args:
            process (subprocess.Popen[str]):
                已启动的子进程
        """
        raise NotImplementedError

    def is_alive(self) -> bool:
        """检查进程树中是否还有存活的进程

        Returns:
            bool:
                是否还有存活的进程
        """
        raise NotImplementedError

    def interrupt(self) -> None:
        """请求进程树优雅退出"""

    def terminate(self) -> None:
        """请求进程树终止"""
        raise NotImplementedError

    def kill(self) -> None:
        """强制结束进程树"""
        raise NotImplementedError

    def close(self) -> None:
        """释放清理机制占用的资源"""

    def wait(self, timeout: float) -> bool:
        """等待进程树中的进程全部退出

        Args:
            timeout (float):
                最长等待时间 (秒)

        Returns:
            bool:
                进程树是否已全部退出
        """
        return _wait_until(lambda: not self.is_alive(), timeout)


class _PosixProcessTree(_ProcessTree):
    """基于进程组和看门狗进程的 Linux / MacOS 进程树管理器"""

    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._watchdog: subprocess.Popen[str] | None = None
        self._finished = False

    def popen_kwargs(self) -> dict[str, Any]:
        # 使用 setsid() 而不是 setpgid(), 子进程脱离控制终端后读写终端时不会因为处于后台进程组而被 SIGTTIN / SIGTTOU 挂起
        return {"start_new_session": True}

    def prepare(self) -> None:
        try:
            self._watchdog = subprocess.Popen(
                [sys.executable, "-I", "-S", "-c", _POSIX_WATCHDOG_SCRIPT],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                start_new_session=True,
            )
        except OSError as e:
            logger.warning("启动进程树看门狗失败, 启动器异常退出时可能无法清理子进程: %s", e)
            self._watchdog = None

    def attach(self, process: subprocess.Popen[str]) -> None:
        self._process = process
        self._send_watchdog(f"{process.pid}\n")

    def is_alive(self) -> bool:
        if self._process is None or self._finished:
            return False
        # 先通过 Popen 回收进程组组长, 避免僵尸进程被误判为存活
        self._process.poll()
        self._reap_orphans()
        # 信号 0 只检查进程组是否存在, 不会真正发送信号
        return self._signal(0)

    def interrupt(self) -> None:
        self._signal(signal.SIGINT)

    def terminate(self) -> None:
        self._signal(signal.SIGTERM)

    def kill(self) -> None:
        if sys.platform != "win32":
            self._signal(signal.SIGKILL)

    def close(self) -> None:
        if self._watchdog is None:
            return
        watchdog = self._watchdog
        self._watchdog = None
        try:
            # 进程树已全部退出时通知看门狗直接退出, 否则直接关闭管道, 由看门狗结束残留的进程组
            if self._process is not None and not self.is_alive():
                self._write_watchdog(watchdog, f"{_WATCHDOG_EXIT_COMMAND}\n")
            if watchdog.stdin is not None:
                watchdog.stdin.close()
        except OSError:
            pass
        try:
            watchdog.wait(timeout=KILL_TIMEOUT)
        except subprocess.TimeoutExpired:
            watchdog.kill()
            watchdog.wait()

    def _signal(self, sig: int) -> bool:
        """向子进程组发送信号

        Args:
            sig (int):
                信号值

        Returns:
            bool:
                子进程组是否仍然存在
        """
        if sys.platform == "win32" or self._process is None or self._finished:
            return False
        try:
            os.killpg(self._process.pid, sig)
        except ProcessLookupError:
            # 进程组已不存在, 之后不再向该进程组 ID 发送信号, 避免 ID 被复用后误杀其他进程
            self._finished = True
            return False
        except PermissionError as e:
            logger.debug("向进程组 %s 发送信号 %s 失败: %s", self._process.pid, sig, e)
        return True

    def _reap_orphans(self) -> None:
        """回收进程组中已退出的孤儿进程

        当启动器是子进程收割者 (例如容器中的 PID 1) 时, 进程组中的孤儿进程会被重新挂载到启动器下,
        如果不回收, 这些僵尸进程会让进程组一直处于存在状态。这里只回收属于该进程组的进程, 不影响其他子进程。
        """
        if sys.platform == "win32" or self._process is None or self._process.returncode is None:
            return
        while True:
            try:
                pid, _ = os.waitpid(-self._process.pid, os.WNOHANG)
            except ChildProcessError:
                return
            if pid == 0:
                return

    def _send_watchdog(self, message: str) -> None:
        if self._watchdog is None:
            return
        try:
            self._write_watchdog(self._watchdog, message)
        except OSError as e:
            logger.warning("与进程树看门狗通信失败, 启动器异常退出时可能无法清理子进程: %s", e)

    @staticmethod
    def _write_watchdog(watchdog: subprocess.Popen[str], message: str) -> None:
        if watchdog.stdin is None:
            return
        watchdog.stdin.write(message)
        watchdog.stdin.flush()


class _WindowsProcessTree(_ProcessTree):
    """基于作业对象 (Job Object) 的 Windows 进程树管理器"""

    _JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

    def __init__(self) -> None:
        self._process: subprocess.Popen[str] | None = None
        self._job: int | None = None
        self._assigned = False
        self._kernel32: Any = None
        self._win_error: Callable[[int], OSError] | None = None
        self._get_last_error: Callable[[], int] | None = None

    def prepare(self) -> None:
        try:
            self._job = self._create_job()
        except OSError as e:
            logger.warning("创建 Windows 作业对象失败, 将使用 taskkill 清理进程树: %s", e)
            self._job = None

    def attach(self, process: subprocess.Popen[str]) -> None:
        self._process = process
        if self._job is None:
            return
        handle = getattr(process, "_handle")
        if self._kernel32.AssignProcessToJobObject(self._job, int(handle)):
            self._assigned = True
            return
        error = self._win_error(self._get_last_error()) if self._win_error and self._get_last_error else None
        logger.warning("将进程加入 Windows 作业对象失败, 将使用 taskkill 清理进程树: %s", error)
        self._close_job()

    def is_alive(self) -> bool:
        if self._process is None:
            return False
        if not self._assigned:
            return self._process.poll() is None
        return self._active_processes() > 0 or self._process.poll() is None

    def terminate(self) -> None:
        # Windows 中无法向不同控制台进程组外的单个进程发送 Ctrl+C, 终止即为强制结束
        self.kill()

    def kill(self) -> None:
        if self._process is None:
            return
        if self._assigned:
            self._kernel32.TerminateJobObject(self._job, 1)
            return
        if self._process.poll() is None:
            subprocess.run(
                ["taskkill", "/PID", str(self._process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def close(self) -> None:
        self._close_job()

    def _create_job(self) -> int:
        import ctypes
        from ctypes import wintypes

        win_dll = getattr(ctypes, "WinDLL")
        win_error = getattr(ctypes, "WinError")
        get_last_error = getattr(ctypes, "get_last_error")
        kernel32 = win_dll("kernel32.dll", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.QueryInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p)
        kernel32.QueryInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
        kernel32.TerminateJobObject.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL

        # 句柄默认不可继承, 只有启动器持有作业对象句柄, 启动器退出时作业对象才会被关闭
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            raise win_error(get_last_error())

        info = _JobObjectExtendedLimitInformation()
        info.BasicLimitInformation.LimitFlags = self._JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(job, self._JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(info), ctypes.sizeof(info)):
            error = win_error(get_last_error())
            kernel32.CloseHandle(job)
            raise error

        self._kernel32 = kernel32
        self._win_error = win_error
        self._get_last_error = get_last_error
        return job

    def _active_processes(self) -> int:
        import ctypes

        info = _JobObjectBasicAccountingInformation()
        if not self._kernel32.QueryInformationJobObject(self._job, self._JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION, ctypes.byref(info), ctypes.sizeof(info), None):
            return 0
        return int(info.ActiveProcesses)

    def _close_job(self) -> None:
        if self._job is None:
            return
        self._kernel32.CloseHandle(self._job)
        self._job = None
        self._assigned = False


def _define_job_structures() -> tuple[type, type]:
    """定义 Windows 作业对象相关的结构体

    Returns:
        tuple[type, type]:
            JOBOBJECT_EXTENDED_LIMIT_INFORMATION 和 JOBOBJECT_BASIC_ACCOUNTING_INFORMATION 结构体类型
    """
    import ctypes

    class IoCounters(ctypes.Structure):
        """IO_COUNTERS"""

        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class JobObjectBasicLimitInformation(ctypes.Structure):
        """JOBOBJECT_BASIC_LIMIT_INFORMATION"""

        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", ctypes.c_uint32),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.c_uint32),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", ctypes.c_uint32),
            ("SchedulingClass", ctypes.c_uint32),
        ]

    class JobObjectExtendedLimitInformation(ctypes.Structure):
        """JOBOBJECT_EXTENDED_LIMIT_INFORMATION"""

        _fields_ = [
            ("BasicLimitInformation", JobObjectBasicLimitInformation),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    class JobObjectBasicAccountingInformation(ctypes.Structure):
        """JOBOBJECT_BASIC_ACCOUNTING_INFORMATION"""

        _fields_ = [
            ("TotalUserTime", ctypes.c_int64),
            ("TotalKernelTime", ctypes.c_int64),
            ("ThisPeriodTotalUserTime", ctypes.c_int64),
            ("ThisPeriodTotalKernelTime", ctypes.c_int64),
            ("TotalPageFaultCount", ctypes.c_uint32),
            ("TotalProcesses", ctypes.c_uint32),
            ("ActiveProcesses", ctypes.c_uint32),
            ("TotalTerminatedProcesses", ctypes.c_uint32),
        ]

    return JobObjectExtendedLimitInformation, JobObjectBasicAccountingInformation


_JobObjectExtendedLimitInformation, _JobObjectBasicAccountingInformation = _define_job_structures()


def _create_process_tree() -> _ProcessTree:
    """创建当前平台的进程树管理器

    Returns:
        _ProcessTree:
            进程树管理器
    """
    if sys.platform == "win32":
        return _WindowsProcessTree()
    return _PosixProcessTree()


@contextmanager
def _handle_termination_signals() -> Generator[None, None, None]:
    """将终止信号转换为 ProcessTreeTerminated 异常, 使启动器在被终止前能够清理进程树

    Python 只允许在主线程中设置信号处理函数, 在其他线程中运行时不做处理,
    此时启动器被终止后依赖看门狗进程 / 作业对象清理进程树。
    """
    if threading.current_thread() is not threading.main_thread():
        yield
        return

    signal_names = ("SIGBREAK",) if sys.platform == "win32" else ("SIGTERM", "SIGHUP")
    signals = [getattr(signal, name) for name in signal_names if hasattr(signal, name)]

    def _handler(signum: int, _frame: FrameType | None) -> None:
        raise ProcessTreeTerminated(signum)

    previous_handlers: dict[int, Callable[[int, FrameType | None], Any] | int | None] = {}
    try:
        for sig in signals:
            previous_handlers[sig] = signal.signal(sig, _handler)
        yield
    finally:
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler if handler is not None else signal.SIG_DFL)


def _wait_process(process: subprocess.Popen[str]) -> int:
    """等待子进程退出

    分段等待而不是无限期阻塞, 保证 Windows 中主线程也能及时响应 Ctrl+C。

    Args:
        process (subprocess.Popen[str]):
            子进程

    Returns:
        int:
            子进程的退出代码
    """
    while True:
        try:
            return process.wait(timeout=WAIT_SLICE)
        except subprocess.TimeoutExpired:
            continue


def _shutdown_process_tree(
    tree: _ProcessTree,
    process: subprocess.Popen[str],
    graceful: bool,
    graceful_timeout: float,
) -> None:
    """逐步升级结束进程树: 中断 -> 终止 -> 强制结束

    Args:
        tree (_ProcessTree):
            进程树管理器
        process (subprocess.Popen[str]):
            进程树的根进程
        graceful (bool):
            是否先请求进程树优雅退出
        graceful_timeout (float):
            请求优雅退出后等待根进程退出的时间 (秒)
    """
    steps: list[tuple[Callable[[], None], float]] = [
        (tree.terminate, TERMINATE_TIMEOUT),
        (tree.kill, KILL_TIMEOUT),
    ]

    try:
        if graceful and tree.is_alive():
            # 优雅退出阶段只等待根进程退出, 根进程退出后残留的后代进程直接进入终止阶段
            tree.interrupt()
            _wait_until(lambda: process.poll() is not None, graceful_timeout)
        for action, timeout in steps:
            if not tree.is_alive():
                return
            action()
            if tree.wait(timeout):
                return
        logger.warning("进程树在强制结束后仍有进程未退出")
    except (KeyboardInterrupt, ProcessTreeTerminated):
        logger.warning("再次收到中断信号, 强制结束进程树")
        tree.kill()
        tree.wait(KILL_TIMEOUT)


def _start_output_reader(process: subprocess.Popen[str]) -> threading.Thread | None:
    """在后台线程中转发子进程输出

    Args:
        process (subprocess.Popen[str]):
            子进程

    Returns:
        (threading.Thread | None):
            转发输出的线程
    """
    stream = process.stdout
    if stream is None:
        return None

    def _pump() -> None:
        for line in stream:
            print(line, end="", flush=True)

    thread = threading.Thread(target=_pump, name="process-tree-output", daemon=True)
    thread.start()
    return thread


def run_process_tree(
    command: list[str],
    custom_env: dict[str, str] | None = None,
    cwd: Path | None = None,
    check: bool = True,
    graceful_timeout: float = DEFAULT_GRACEFUL_TIMEOUT,
) -> int:
    """运行命令并在结束时清理整个进程树

    无论子进程正常退出, 启动器被 Ctrl+C 中断, 收到终止信号还是直接崩溃, 子进程及其所有后代进程都会被清理。
    在 Jupyter 中运行时, 子进程的输出会被转发到 Notebook 中。

    Args:
        command (list[str]):
            要执行的命令
        custom_env (dict[str, str] | None):
            自定义环境变量
        cwd (Path | None):
            执行进程时的起始路径
        check (bool):
            检查进程退出状态, 当异常退出时引发 RuntimeError
        graceful_timeout (float):
            收到中断信号后, 等待进程树自行退出的时间 (秒)

    Returns:
        int:
            子进程的退出代码

    Raises:
        RuntimeError:
            当命令执行失败时
        KeyboardInterrupt:
            启动器被 Ctrl+C 中断时, 在进程树清理完成后重新引发
        ProcessTreeTerminated:
            启动器收到终止信号时, 在进程树清理完成后引发
    """
    if custom_env is None:
        custom_env = os.environ.copy()

    tree = _create_process_tree()
    kwargs: dict[str, Any] = {
        "args": command,
        "env": custom_env,
        "cwd": cwd,
        "encoding": "utf-8",
        "errors": "ignore",
        **tree.popen_kwargs(),
    }
    if in_jupyter():
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)

    logger.debug("执行命令的参数: %s", kwargs)

    with _handle_termination_signals():
        tree.prepare()
        try:
            process = subprocess.Popen(**kwargs)
            reader: threading.Thread | None = None
            interrupted = False
            try:
                tree.attach(process)
                reader = _start_output_reader(process)
                returncode = _wait_process(process)
            except (KeyboardInterrupt, ProcessTreeTerminated):
                interrupted = True
                logger.info("正在结束进程树")
                raise
            finally:
                # 子进程退出后其后代进程可能仍在运行, 同样需要清理
                _shutdown_process_tree(tree, process, graceful=interrupted, graceful_timeout=graceful_timeout)
                if reader is not None:
                    reader.join(timeout=KILL_TIMEOUT)
        finally:
            tree.close()

    if check and returncode != 0:
        raise RuntimeError("\n".join(["执行命令时发生错误", f"命令: {command}", f"错误代码: {returncode}"]))

    return returncode
