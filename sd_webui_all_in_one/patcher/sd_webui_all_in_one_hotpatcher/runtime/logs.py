"""运行时日志采集工具"""

from __future__ import annotations

import logging
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from locale import getpreferredencoding
from typing import Any, Iterable, TextIO, cast

from ..state import HotpatcherState, get_default_state
from .client import RuntimeClient

DEFAULT_MAX_CHARS = 8192
DEFAULT_QUEUE_SIZE = 1000
DEFAULT_STREAMS = ("stdout", "stderr")
DEFAULT_LOGGER_EXCLUDE = ("sd_webui_all_in_one_hotpatcher",)
DEFAULT_HOOK_POLICY = "cooperative"
DEFAULT_HOOK_CHECK_INTERVAL = 1
DEFAULT_FD_CAPTURE = "0"


def install_log_capture(
    client: RuntimeClient,
    *,
    capture_logging: bool = True,
    streams: Iterable[str] | None = DEFAULT_STREAMS,
    subprocess_mode: str | None = "safe",
    policy: str = "bounded",
    max_chars: int = DEFAULT_MAX_CHARS,
    queue_size: int = DEFAULT_QUEUE_SIZE,
    logger_include: Iterable[str] | None = None,
    logger_exclude: Iterable[str] | None = DEFAULT_LOGGER_EXCLUDE,
    hook_policy: str = DEFAULT_HOOK_POLICY,
    hook_check_interval: int | float = DEFAULT_HOOK_CHECK_INTERVAL,
    fd_capture: str | None = DEFAULT_FD_CAPTURE,
    state: HotpatcherState | None = None,
) -> "LogCapture":
    """
    安装进程级日志采集

    重复调用会返回当前已安装的采集器, 避免重复挂载 root logging handler、
    stdout/stderr tee 和 subprocess patch。

    Args:
        client (RuntimeClient):
            发送日志事件的运行时客户端
        capture_logging (bool):
            是否采集 Python logging
        streams (Iterable[str] | None):
            需要 tee 的标准流名称, 支持 stdout、stderr
        subprocess_mode (str | None):
            子进程采集模式, 支持 ``0``、``safe``、``force``
        policy (str):
            日志策略, 支持 ``bounded`` 和 ``raw``
        max_chars (int):
            bounded 模式下单个字符串最大长度
        queue_size (int):
            后台发送队列大小
        logger_include (Iterable[str] | None):
            允许采集的 logger 前缀
        logger_exclude (Iterable[str] | None):
            排除采集的 logger 前缀
        hook_policy (str):
            hook 冲突策略, 支持 ``cooperative``、``warn`` 和 ``reapply``
        hook_check_interval (int | float):
            warn/reapply 模式下检查 hook 状态的间隔秒数
        fd_capture (str | None):
            实验性 fd 级标准流采集模式, 支持 ``0``、``fallback`` 和 ``force``
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        LogCapture:
            已安装的日志采集器
    """

    active_state = state or get_default_state()
    if active_state.log_capture is not None and not active_state.log_capture.closed:
        return active_state.log_capture

    capture = LogCapture(
        client=client,
        capture_logging=capture_logging,
        streams=tuple(streams or ()),
        subprocess_mode=(subprocess_mode or "0").lower(),
        policy=policy,
        max_chars=max_chars,
        queue_size=queue_size,
        logger_include=tuple(logger_include or ()),
        logger_exclude=tuple(logger_exclude or ()),
        hook_policy=(hook_policy or DEFAULT_HOOK_POLICY).lower(),
        hook_check_interval=hook_check_interval,
        fd_capture=(fd_capture or DEFAULT_FD_CAPTURE).lower(),
        guard=active_state.log_guard,
    )
    capture.install()
    active_state.log_capture = capture
    return capture


def uninstall_log_capture(*, state: HotpatcherState | None = None) -> None:
    """卸载当前进程级日志采集器

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
    """

    active_state = state or get_default_state()
    capture = active_state.log_capture
    active_state.log_capture = None
    if capture is not None:
        capture.close()


def configure_log_capture_from_env(
    client: RuntimeClient,
    config: dict[str, Any] | None = None,
    *,
    state: HotpatcherState | None = None,
) -> "LogCapture | None":
    """
    根据环境变量和配置安装日志采集

    ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGS=1`` 或配置中的 ``logs`` 为真时启用。

    Args:
        client (RuntimeClient):
            发送日志事件的运行时客户端
        config (dict[str, Any] | None):
            已加载的运行时配置
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        LogCapture | None:
            已安装的日志采集器。未启用时返回 None。
    """

    active_state = state or get_default_state()
    config_logs = _config_logs(config)
    enabled = _env_bool("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGS", default=bool(config_logs))
    if not enabled:
        return None

    return install_log_capture(
        client,
        capture_logging=_env_bool(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGGING",
            default=bool(config_logs.get("logging", True)) if isinstance(config_logs, dict) else True,
        ),
        streams=_env_streams(config_logs),
        subprocess_mode=_env_value(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_SUBPROCESS",
            config_logs.get("subprocess", "safe") if isinstance(config_logs, dict) else "safe",
        ),
        policy=_env_value(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_POLICY",
            config_logs.get("policy", "bounded") if isinstance(config_logs, dict) else "bounded",
        ),
        max_chars=_env_int(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_MAX_CHARS",
            int(config_logs.get("max_chars", DEFAULT_MAX_CHARS)) if isinstance(config_logs, dict) else DEFAULT_MAX_CHARS,
        ),
        queue_size=_env_int(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_QUEUE_SIZE",
            int(config_logs.get("queue_size", DEFAULT_QUEUE_SIZE)) if isinstance(config_logs, dict) else DEFAULT_QUEUE_SIZE,
        ),
        logger_include=_env_list(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGGER_INCLUDE",
            config_logs.get("logger_include", ()) if isinstance(config_logs, dict) else (),
        ),
        logger_exclude=_env_list(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGGER_EXCLUDE",
            config_logs.get("logger_exclude", DEFAULT_LOGGER_EXCLUDE) if isinstance(config_logs, dict) else DEFAULT_LOGGER_EXCLUDE,
        ),
        hook_policy=_env_value(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_HOOK_POLICY",
            config_logs.get("hook_policy", DEFAULT_HOOK_POLICY) if isinstance(config_logs, dict) else DEFAULT_HOOK_POLICY,
        ),
        hook_check_interval=_env_int(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_HOOK_CHECK_INTERVAL",
            int(config_logs.get("hook_check_interval", DEFAULT_HOOK_CHECK_INTERVAL)) if isinstance(config_logs, dict) else DEFAULT_HOOK_CHECK_INTERVAL,
        ),
        fd_capture=_env_value(
            "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_FD_CAPTURE",
            config_logs.get("fd_capture", DEFAULT_FD_CAPTURE) if isinstance(config_logs, dict) else DEFAULT_FD_CAPTURE,
        ),
        state=active_state,
    )


@dataclass
class LogMessage:
    """
    待发送的日志消息

    Attributes:
        message_type (str):
            runtime 事件类型
        payload (dict[str, Any]):
            事件载荷
    """

    message_type: str
    payload: dict[str, Any]


class RuntimeLogHandler(logging.Handler):
    """
    转发 logging 记录的 handler

    Attributes:
        capture (LogCapture):
            接收结构化日志记录的采集器
    """

    def __init__(self, capture: "LogCapture"):
        super().__init__()
        self.capture = capture
        self._formatter = logging.Formatter()

    def emit(self, record: logging.LogRecord) -> None:
        if self.capture.should_skip_record(record):
            return
        try:
            payload: dict[str, Any] = {
                "logger": record.name,
                "level": record.levelname,
                "levelno": record.levelno,
                "message": record.getMessage(),
                "created": record.created,
                "pathname": record.pathname,
                "lineno": record.lineno,
                "function": record.funcName,
                "thread": record.thread,
                "thread_name": record.threadName,
                "process": record.process,
            }
            if record.exc_info:
                exc_type, exc_value, exc_tb = record.exc_info
                if exc_type is not None:
                    payload["exception"] = {
                        "type": f"{exc_type.__module__}.{exc_type.__qualname__}",
                        "message": str(exc_value),
                        "traceback": self._formatter.formatException(record.exc_info),
                    }
            self.capture.submit("log.record", payload)
        except Exception:
            return


class StreamTee:
    """
    标准流 tee 包装器

    写入时会先尽量写回原始 stream, 再把文本作为 ``log.stream`` 事件送入采集器。
    原始 stream 异常只上报状态, 不再抛回业务代码。

    Attributes:
        capture (LogCapture):
            接收 stream 事件的采集器
        stream_name (str):
            标准流名称, 通常为 stdout 或 stderr
        original (TextIO):
            原始标准流对象
    """

    def __init__(self, capture: "LogCapture", stream_name: str, original: TextIO):
        self.capture = capture
        self.stream_name = stream_name
        self.original = original
        self._sd_webui_all_in_one_hotpatcher_stream_tee = True

    def write(self, text: str) -> int:
        """
        写入文本并镜像为日志事件

        Args:
            text (str):
                待写入文本

        Returns:
            int:
                原始 stream 返回的写入结果
        """

        try:
            result = self.original.write(text)
        except Exception as exc:
            self.capture.report_stream_error_once(self.stream_name, "write", exc)
            result = len(text)
        if text and self.capture.should_capture():
            self.capture.submit_stream(self.stream_name, text, source="stream")
        return len(text) if result is None else result

    def flush(self) -> None:
        """刷新原始 stream"""

        try:
            self.original.flush()
        except Exception as exc:
            self.capture.report_stream_error_once(self.stream_name, "flush", exc)

    def isatty(self) -> bool:
        """
        判断原始 stream 是否连接到 TTY

        Returns:
            bool:
                原始 stream 的 isatty 结果
        """

        return self.original.isatty()

    def fileno(self) -> int:
        """
        获取原始 stream 的文件描述符

        Returns:
            int:
                文件描述符
        """

        return self.original.fileno()

    @property
    def encoding(self) -> str | None:
        """
        原始 stream 编码

        Returns:
            str | None:
                编码名称
        """

        return getattr(self.original, "encoding", None)

    @property
    def errors(self) -> str | None:
        """
        原始 stream 错误处理策略

        Returns:
            str | None:
                错误处理策略名称
        """

        return getattr(self.original, "errors", None)

    @property
    def closed(self) -> bool:
        """
        原始 stream 是否已关闭

        Returns:
            bool:
                原始 stream 的 closed 状态
        """

        return getattr(self.original, "closed", False)

    def __getattr__(self, name: str) -> Any:
        """
        代理访问原始 stream 属性

        Args:
            name (str):
                属性名

        Returns:
            Any:
                原始 stream 上的属性值
        """

        return getattr(self.original, name)


class FdWritebackStream:
    """
    写回 fd 捕获安装前的原始文件描述符。

    这个对象只用于 subprocess force 模式, 避免子进程输出写回时再次进入
    fd 捕获管道造成重复事件。

    Attributes:
        fd_capture (FdStreamCapture):
            fd 级标准流捕获器。
        fallback (TextIO):
            原始 fallback stream。
    """

    def __init__(self, fd_capture: "FdStreamCapture", fallback: TextIO):
        self.fd_capture = fd_capture
        self.fallback = fallback

    def write(self, text: str) -> int:
        """
        写入文本到安装 fd 捕获前的原始文件描述符

        Args:
            text (str):
                待写入文本。

        Returns:
            int:
                写入的字节数或 fallback stream 返回的写入结果。
        """

        data = text.encode(getattr(self.fallback, "encoding", None) or getpreferredencoding(False), errors="replace")
        try:
            return os.write(self.fd_capture.original_fd, data)
        except Exception:
            return self.fallback.write(text)

    def flush(self) -> None:
        """刷新 fallback stream"""

        try:
            self.fallback.flush()
        except Exception:
            return

    def __getattr__(self, name: str) -> Any:
        """
        代理访问 fallback stream 属性

        Args:
            name (str):
                属性名。

        Returns:
            Any:
                fallback stream 上的属性值。
        """

        return getattr(self.fallback, name)


class FdStreamCapture:
    """
    实验性 fd 级标准流捕获。

    通过 ``dup2`` 把 stdout/stderr fd 指向 pipe, 后台线程读取 pipe、
    写回安装前的原始 fd, 并发送 ``source=fd`` 的 ``log.stream``。

    Attributes:
        capture (LogCapture):
            接收 fd stream 事件的采集器。
        stream_name (str):
            标准流名称, 通常为 stdout 或 stderr。
        stream (TextIO):
            被捕获的标准流对象。
        installed (bool):
            fd 捕获是否已安装。
    """

    def __init__(self, capture: "LogCapture", stream_name: str, stream: TextIO):
        self.capture = capture
        self.stream_name = stream_name
        self.stream = stream
        self.fd: int | None = None
        self.original_fd: int = -1
        self.pipe_r: int = -1
        self.pipe_w: int = -1
        self.installed = False
        self._thread: threading.Thread | None = None

    def install(self) -> bool:
        """
        安装 fd 级标准流捕获

        Returns:
            bool:
                安装成功时返回 True。当前环境不支持或安装失败时返回 False。
        """

        try:
            flush = getattr(self.stream, "flush", None)
            if callable(flush):
                flush()
            self.fd = int(self.stream.fileno())
            self.original_fd = os.dup(self.fd)
            self.pipe_r, self.pipe_w = os.pipe()
            os.dup2(self.pipe_w, self.fd)
            self.installed = True
            self._thread = threading.Thread(
                target=self._reader,
                name=f"sd_webui_all_in_one_hotpatcher-fd-{self.stream_name}",
                daemon=True,
            )
            self._thread.start()
            return True
        except (AttributeError, OSError, ValueError) as exc:
            self.close()
            self.capture.submit_hook_status(
                f"fd.{self.stream_name}",
                "unsupported",
                f"{type(exc).__name__}: {exc}",
            )
            return False
        except Exception as exc:
            self.close()
            self.capture.submit_hook_status(
                f"fd.{self.stream_name}",
                "error",
                f"{type(exc).__name__}: {exc}",
            )
            return False

    def close(self) -> None:
        """关闭 fd 捕获并尽量恢复原始文件描述符"""

        if self.installed and self.fd is not None and self.original_fd >= 0:
            try:
                if self.pipe_w >= 0 and _same_fd_target(self.fd, self.pipe_w):
                    os.dup2(self.original_fd, self.fd)
            except Exception:
                pass
        self.installed = False
        for fd_name in ("pipe_w", "pipe_r", "original_fd"):
            fd = getattr(self, fd_name)
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass
                setattr(self, fd_name, -1)
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None

    def is_current(self) -> bool:
        """
        判断当前标准流 fd 是否仍指向捕获 pipe

        Returns:
            bool:
                当前 fd 仍由本捕获器接管时返回 True。
        """

        return self.installed and self.fd is not None and self.pipe_w >= 0 and _same_fd_target(self.fd, self.pipe_w)

    def writeback_stream(self, fallback: TextIO) -> FdWritebackStream:
        """
        构建写回原始 fd 的 stream 代理

        Args:
            fallback (TextIO):
                fd 写回失败时使用的 fallback stream。

        Returns:
            FdWritebackStream:
                写回原始 fd 的 stream 代理。
        """

        return FdWritebackStream(self, fallback)

    def _reader(self) -> None:
        while True:
            try:
                chunk = os.read(self.pipe_r, 4096)
            except OSError:
                return
            if not chunk:
                return
            try:
                os.write(self.original_fd, chunk)
            except OSError:
                pass
            self.capture.submit_stream(self.stream_name, chunk, source="fd")


class SubprocessCapture:
    """
    子进程输出采集器

    通过 patch ``subprocess.Popen`` 捕获 safe 或 force 模式下的子进程输出。

    Attributes:
        capture (LogCapture):
            接收子进程输出事件的采集器
        mode (str):
            子进程采集模式
        stdout_stream (TextIO):
            force 模式下写回父进程 stdout 的目标流
        stderr_stream (TextIO):
            force 模式下写回父进程 stderr 的目标流
    """

    def __init__(
        self,
        capture: "LogCapture",
        mode: str,
        stdout_stream: TextIO,
        stderr_stream: TextIO,
    ):
        self.capture = capture
        self.mode = mode
        self.stdout_stream = stdout_stream
        self.stderr_stream = stderr_stream
        self.original_popen = subprocess.Popen
        self.patched_popen: Any = None
        self.installed = False
        self._reader_threads: list[threading.Thread] = []

    def install(self) -> None:
        """安装 subprocess.Popen patch

        Raises:
            ValueError:
                subprocess 捕获模式不受支持时抛出。
        """

        if self.installed or self.mode in {"0", "false", "none", "off"}:
            return
        if self.mode not in {"safe", "force"}:
            raise ValueError("subprocess_mode must be 0, safe, or force")
        self.patched_popen = self._make_popen_class()
        subprocess.Popen = self.patched_popen  # type: ignore[assignment]
        self.installed = True

    def uninstall(self) -> None:
        """卸载 subprocess.Popen patch"""

        if not self.installed:
            return
        if subprocess.Popen is self.patched_popen:
            subprocess.Popen = cast(Any, self.original_popen)
        self.patched_popen = None
        self.installed = False

    def is_current(self) -> bool:
        """
        判断当前 subprocess.Popen 是否仍是本采集器安装的包装类

        Returns:
            bool:
                当前 subprocess.Popen 仍是本采集器安装的包装类时返回 True。
        """

        return self.installed and subprocess.Popen is self.patched_popen

    def reapply(self) -> bool:
        """
        重新包住当前 subprocess.Popen

        Returns:
            bool:
                重新包装成功时返回 True。
        """

        if not self.installed:
            return False
        self.original_popen = subprocess.Popen
        self.patched_popen = self._make_popen_class()
        subprocess.Popen = self.patched_popen  # type: ignore[assignment]
        return True

    def _make_popen_class(self) -> Any:
        """
        创建可继承的 Popen 包装类。

        Windows 标准库的 ``asyncio.windows_utils`` 会定义
        ``class Popen(subprocess.Popen)``。因此这里不能把
        ``subprocess.Popen`` 替换成函数或 bound method。
        """

        owner = self
        original_popen = cast(Any, self.original_popen)

        class CapturedPopen(original_popen):
            def __init__(captured_self: Any, *popenargs: Any, **kwargs: Any) -> None:  # pylint: disable=no-self-argument
                (
                    prepared_args,
                    prepared_kwargs,
                    args_value,
                    stdout_value,
                    stderr_value,
                    forced_stdout,
                    forced_stderr,
                ) = owner._prepare_popen(popenargs, kwargs)
                super().__init__(*prepared_args, **prepared_kwargs)
                owner._attach_process_capture(
                    captured_self,
                    args_value,
                    stdout_value,
                    stderr_value,
                    forced_stdout,
                    forced_stderr,
                )

        CapturedPopen.__name__ = getattr(original_popen, "__name__", "Popen")
        CapturedPopen.__qualname__ = getattr(original_popen, "__qualname__", "Popen")
        CapturedPopen.__module__ = getattr(original_popen, "__module__", "subprocess")
        CapturedPopen._sd_webui_all_in_one_hotpatcher_popen = True
        return CapturedPopen

    def _prepare_popen(
        self,
        popenargs: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> tuple[tuple[Any, ...], dict[str, Any], Any, Any, Any, bool, bool]:
        args_value = popenargs[0] if popenargs else kwargs.get("args")
        stdout_value = _get_popen_option(popenargs, kwargs, "stdout", 4)
        stderr_value = _get_popen_option(popenargs, kwargs, "stderr", 5)
        forced_stdout = False
        forced_stderr = False

        if self.mode == "force":
            if stdout_value is None:
                popenargs, kwargs = _set_popen_option(popenargs, kwargs, "stdout", 4, subprocess.PIPE)
                stdout_value = subprocess.PIPE
                forced_stdout = True
            if stderr_value is None:
                popenargs, kwargs = _set_popen_option(popenargs, kwargs, "stderr", 5, subprocess.PIPE)
                stderr_value = subprocess.PIPE
                forced_stderr = True

        return popenargs, kwargs, args_value, stdout_value, stderr_value, forced_stdout, forced_stderr

    def _attach_process_capture(
        self,
        process: subprocess.Popen,
        args_value: Any,
        stdout_value: Any,
        stderr_value: Any,
        forced_stdout: bool,
        forced_stderr: bool,
    ) -> None:
        communicate_stdout = None if forced_stdout else stdout_value
        communicate_stderr = None if forced_stderr else stderr_value
        reader_threads: list[threading.Thread] = []

        if forced_stdout and process.stdout is not None:
            reader_threads.append(self._start_reader(process, "stdout", process.stdout, self.stdout_stream, args_value))
        if forced_stderr and process.stderr is not None:
            reader_threads.append(self._start_reader(process, "stderr", process.stderr, self.stderr_stream, args_value))

        self._patch_communicate(
            process,
            args_value,
            communicate_stdout,
            communicate_stderr,
            forced_stdout=forced_stdout,
            forced_stderr=forced_stderr,
            reader_threads=reader_threads,
        )

    def _patch_communicate(
        self,
        process: subprocess.Popen,
        args_value: Any,
        stdout_value: Any,
        stderr_value: Any,
        *,
        forced_stdout: bool = False,
        forced_stderr: bool = False,
        reader_threads: list[threading.Thread] | None = None,
    ) -> None:
        original_communicate = process.communicate
        capture_stdout = stdout_value is subprocess.PIPE
        capture_stderr = stderr_value is subprocess.PIPE
        reader_threads = reader_threads or []

        if not capture_stdout and not capture_stderr and not (forced_stdout or forced_stderr):
            return

        def communicate(*args: Any, **kwargs: Any) -> tuple[Any, Any]:
            if (forced_stdout or forced_stderr) and not _communicate_has_input(args, kwargs):
                timeout = _communicate_timeout(args, kwargs)
                process.wait(timeout=timeout)
                for thread in reader_threads:
                    thread.join(timeout=1)
                return None, None

            stdout_data, stderr_data = original_communicate(*args, **kwargs)
            if capture_stdout and stdout_data:
                self.capture.submit_subprocess_stream("stdout", stdout_data, process, args_value)
            if capture_stderr and stderr_data:
                self.capture.submit_subprocess_stream("stderr", stderr_data, process, args_value)
            return stdout_data, stderr_data

        process.communicate = communicate  # ty: ignore[invalid-assignment]

    def _start_reader(
        self,
        process: subprocess.Popen,
        stream_name: str,
        pipe: Any,
        target: TextIO,
        args_value: Any,
    ) -> threading.Thread:
        thread = threading.Thread(
            target=self._reader,
            args=(process, stream_name, pipe, target, args_value),
            daemon=True,
        )
        self._reader_threads.append(thread)
        thread.start()
        return thread

    def _reader(
        self,
        process: subprocess.Popen,
        stream_name: str,
        pipe: Any,
        target: TextIO,
        args_value: Any,
    ) -> None:
        try:
            while True:
                chunk = pipe.readline()
                if not chunk:
                    break
                text = _to_text(chunk)
                try:
                    target.write(text)
                    target.flush()
                except Exception:
                    pass
                self.capture.submit_subprocess_stream(stream_name, text, process, args_value)
        except Exception:
            return


class LogCapture:
    """
    进程级日志采集器

    统一管理 logging handler、stdout/stderr tee、subprocess patch 和后台发送线程。

    Attributes:
        client (RuntimeClient):
            发送日志事件的运行时客户端
        capture_logging (bool):
            是否采集 Python logging
        streams (tuple[str, ...]):
            被 tee 的标准流名称
        subprocess_mode (str):
            子进程采集模式
        policy (str):
            日志策略, 支持 bounded 和 raw
        max_chars (int):
            bounded 模式下单个字符串最大长度
        logger_include (tuple[str, ...]):
            允许采集的 logger 前缀
        logger_exclude (tuple[str, ...]):
            排除采集的 logger 前缀
        closed (bool):
            采集器是否已关闭
    """

    def __init__(
        self,
        *,
        client: RuntimeClient,
        capture_logging: bool,
        streams: tuple[str, ...],
        subprocess_mode: str,
        policy: str,
        max_chars: int,
        queue_size: int,
        logger_include: tuple[str, ...],
        logger_exclude: tuple[str, ...],
        hook_policy: str,
        hook_check_interval: int | float,
        fd_capture: str,
        guard: Any | None = None,
    ):
        if policy not in {"bounded", "raw"}:
            raise ValueError("policy must be bounded or raw")
        if hook_policy not in {"cooperative", "warn", "reapply"}:
            raise ValueError("hook_policy must be cooperative, warn, or reapply")
        if fd_capture not in {"0", "false", "none", "off", "fallback", "force"}:
            raise ValueError("fd_capture must be 0, fallback, or force")
        self.client = client
        self._guard = guard or get_default_state().log_guard
        self.capture_logging = capture_logging
        self.streams = streams
        self.subprocess_mode = subprocess_mode
        self.policy = policy
        self.max_chars = max(0, max_chars)
        self.logger_include = logger_include
        self.logger_exclude = logger_exclude
        self.hook_policy = hook_policy
        self.hook_check_interval = max(0.05, float(hook_check_interval))
        self.fd_capture = "0" if fd_capture in {"false", "none", "off"} else fd_capture
        self.queue: queue.Queue[LogMessage] = queue.Queue(maxsize=max(0, queue_size))
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="sd_webui_all_in_one_hotpatcher-log-capture", daemon=True)
        self._dropped = 0
        self._dropped_lock = threading.Lock()
        self._root_handler: RuntimeLogHandler | None = None
        self._stream_originals: dict[str, TextIO] = {}
        self._stream_wrappers: dict[str, StreamTee] = {}
        self._fd_captures: dict[str, FdStreamCapture] = {}
        self._subprocess_capture: SubprocessCapture | None = None
        self._last_hook_check = time.monotonic()
        self._reported_lost: set[str] = set()
        self._reported_stream_errors: set[str] = set()
        self.closed = False

    def install(self) -> None:
        """安装日志采集 hook 并启动后台发送线程"""

        self._thread.start()
        self._install_fd_capture(force_only=True)
        self._install_streams()
        self._install_logging()
        self._install_subprocess()

    def close(self) -> None:
        """关闭日志采集并恢复所有进程级 patch"""

        if self.closed:
            return
        self.closed = True
        self._uninstall_subprocess()
        self._uninstall_logging()
        self._uninstall_streams()
        self._uninstall_fd_capture()
        self._stop.set()
        self._thread.join(timeout=2)

    def submit(self, message_type: str, payload: dict[str, Any]) -> None:
        """
        提交日志事件到后台队列

        Args:
            message_type (str):
                runtime 事件类型
            payload (dict[str, Any]):
                事件载荷
        """

        if self.closed or not self.should_capture():
            return
        message = LogMessage(message_type, self._apply_policy(dict(payload)))
        try:
            self.queue.put_nowait(message)
        except queue.Full:
            self._mark_dropped("queue_full")

    def submit_stream(self, stream: str, text: Any, *, source: str) -> None:
        """
        提交标准流日志事件

        Args:
            stream (str):
                流名称
            text (Any):
                输出文本
            source (str):
                日志来源
        """

        self.submit(
            "log.stream",
            {
                "stream": stream,
                "text": _to_text(text),
                "pid": os.getpid(),
                "source": source,
            },
        )

    def submit_subprocess_stream(
        self,
        stream: str,
        text: Any,
        process: subprocess.Popen,
        args_value: Any,
    ) -> None:
        """
        提交子进程标准流日志事件

        Args:
            stream (str):
                流名称
            text (Any):
                输出文本
            process (subprocess.Popen):
                子进程对象
            args_value (Any):
                子进程启动参数
        """

        payload = {
            "stream": stream,
            "text": _to_text(text),
            "pid": os.getpid(),
            "source": "subprocess",
            "subprocess": {
                "pid": process.pid,
                "args": _json_safe(args_value),
            },
        }
        self.submit("log.stream", payload)

    def submit_hook_status(self, component: str, status: str, detail: str = "") -> None:
        """
        提交日志 hook 健康状态事件

        Args:
            component (str):
                hook 组件名称
            status (str):
                状态, 例如 installed、lost、reapplied、unsupported、error
            detail (str):
                补充说明
        """

        self.submit(
            "log.hook_status",
            {
                "component": component,
                "status": status,
                "policy": self.hook_policy,
                "pid": os.getpid(),
                "detail": detail,
            },
        )

    def report_stream_error_once(self, stream_name: str, operation: str, exc: BaseException) -> None:
        """
        上报一次标准流下游异常

        标准流经常被 colorama、wandb、WebUI 自己的 logger 等多层包装。
        下游 write/flush 抛错时, 日志采集器保持 best-effort, 避免把异常抛回
        import/print 调用点导致业务模块加载失败。

        Args:
            stream_name (str):
                标准流名称。
            operation (str):
                发生异常的操作名称。
            exc (BaseException):
                下游 stream 抛出的异常。
        """

        key = f"{stream_name}.{operation}.{type(exc).__name__}.{exc}"
        if key in self._reported_stream_errors:
            return
        self._reported_stream_errors.add(key)
        self.submit_hook_status(
            f"stream.{stream_name}",
            "error",
            f"{operation} failed: {type(exc).__name__}: {exc}",
        )

    def should_capture(self) -> bool:
        """
        判断当前线程是否允许采集日志

        Returns:
            bool:
                未处于递归保护状态时返回 True
        """

        return not getattr(self._guard, "active", False)

    def should_skip_record(self, record: logging.LogRecord) -> bool:
        """
        判断 logging 记录是否应跳过

        Args:
            record (logging.LogRecord):
                logging 记录

        Returns:
            bool:
                需要跳过时返回 True
        """

        if not self.should_capture():
            return True
        name = record.name
        if self.logger_include and not _matches_prefix(name, self.logger_include):
            return True
        if self.logger_exclude and _matches_prefix(name, self.logger_exclude):
            return True
        return False

    def _install_logging(self) -> None:
        if not self.capture_logging:
            return
        handler = RuntimeLogHandler(self)
        logging.getLogger().addHandler(handler)
        self._root_handler = handler
        self.submit_hook_status("logging", "installed", "root handler installed")

    def _uninstall_logging(self) -> None:
        if self._root_handler is None:
            return
        try:
            if self._root_handler in logging.getLogger().handlers:
                logging.getLogger().removeHandler(self._root_handler)
        finally:
            self._root_handler = None

    def _install_streams(self) -> None:
        stream_names = {name.strip().lower() for name in self.streams}
        for stream_name in ("stdout", "stderr"):
            if stream_name not in stream_names or stream_name in self._fd_captures:
                continue
            self._install_stream(stream_name, status="installed")

    def _uninstall_streams(self) -> None:
        for stream_name in list(self._stream_wrappers):
            self._uninstall_stream(stream_name)

    def _install_stream(self, stream_name: str, *, status: str) -> None:
        stream = _get_std_stream(stream_name)
        wrapper = StreamTee(self, stream_name, stream)
        self._stream_originals[stream_name] = stream
        self._stream_wrappers[stream_name] = wrapper
        _set_std_stream(stream_name, wrapper)  # ty: ignore[invalid-argument-type]
        self._reported_lost.discard(f"stream.{stream_name}")
        self.submit_hook_status(f"stream.{stream_name}", status, "stream wrapper installed")

    def _uninstall_stream(self, stream_name: str) -> None:
        wrapper = self._stream_wrappers.pop(stream_name, None)
        original = self._stream_originals.pop(stream_name, None)
        if wrapper is not None and original is not None and _get_std_stream(stream_name) is wrapper:
            _set_std_stream(stream_name, original)

    def _install_subprocess(self) -> None:
        if self.subprocess_mode in {"0", "false", "none", "off"}:
            return
        stdout_stream = self._subprocess_writeback_stream("stdout")
        stderr_stream = self._subprocess_writeback_stream("stderr")
        capture = SubprocessCapture(self, self.subprocess_mode, stdout_stream, stderr_stream)
        capture.install()
        self._subprocess_capture = capture
        if capture.installed:
            self.submit_hook_status("subprocess", "installed", f"Popen wrapped in {self.subprocess_mode} mode")

    def _uninstall_subprocess(self) -> None:
        if self._subprocess_capture is None:
            return
        self._subprocess_capture.uninstall()
        self._subprocess_capture = None

    def _subprocess_writeback_stream(self, stream_name: str) -> TextIO:
        stream = self._stream_originals.get(stream_name) or _get_std_stream(stream_name)
        fd_capture = self._fd_captures.get(stream_name)
        if fd_capture is not None and fd_capture.installed:
            return fd_capture.writeback_stream(stream)  # ty: ignore[invalid-return-type]
        return stream

    def _install_fd_capture(self, *, force_only: bool = False, stream_name: str | None = None) -> bool:
        if self.fd_capture in {"0", "false", "none", "off"}:
            return False
        if force_only and self.fd_capture != "force":
            return False

        stream_names = {name.strip().lower() for name in self.streams}
        targets = (stream_name,) if stream_name is not None else ("stdout", "stderr")
        installed_any = False
        for target in targets:
            if target not in stream_names or target in self._fd_captures:
                continue
            fd_capture = FdStreamCapture(self, target, _get_std_stream(target))
            if fd_capture.install():
                self._fd_captures[target] = fd_capture
                self.submit_hook_status(f"fd.{target}", "installed", f"fd capture installed in {self.fd_capture} mode")
                installed_any = True
        return installed_any

    def _uninstall_fd_capture(self) -> None:
        for fd_capture in list(self._fd_captures.values()):
            fd_capture.close()
        self._fd_captures.clear()

    def _check_hooks(self) -> None:
        if self.hook_policy not in {"warn", "reapply"}:
            return
        now = time.monotonic()
        if now - self._last_hook_check < self.hook_check_interval:
            return
        self._last_hook_check = now
        self._check_stream_hooks()
        self._check_fd_hooks()
        self._check_logging_hook()
        self._check_subprocess_hook()

    def _check_stream_hooks(self) -> None:
        for stream_name, wrapper in list(self._stream_wrappers.items()):
            component = f"stream.{stream_name}"
            if _get_std_stream(stream_name) is wrapper:
                self._reported_lost.discard(component)
                continue
            self._report_lost_once(component, "stream wrapper was replaced")
            if self.fd_capture == "fallback" and self._install_fd_capture(stream_name=stream_name):
                self._stream_wrappers.pop(stream_name, None)
                self._stream_originals.pop(stream_name, None)
                continue
            if self.hook_policy == "reapply":
                self._install_stream(stream_name, status="reapplied")

    def _check_logging_hook(self) -> None:
        if self._root_handler is None:
            return
        component = "logging"
        root = logging.getLogger()
        if self._root_handler in root.handlers:
            self._reported_lost.discard(component)
            return
        self._report_lost_once(component, "root logging handler was removed")
        if self.hook_policy == "reapply":
            root.addHandler(self._root_handler)
            self._reported_lost.discard(component)
            self.submit_hook_status(component, "reapplied", "root handler re-added")

    def _check_fd_hooks(self) -> None:
        for stream_name, fd_capture in list(self._fd_captures.items()):
            component = f"fd.{stream_name}"
            if fd_capture.is_current():
                self._reported_lost.discard(component)
                continue
            self._report_lost_once(component, "fd capture was replaced")
            if self.hook_policy == "reapply":
                fd_capture.close()
                self._fd_captures.pop(stream_name, None)
                if self._install_fd_capture(stream_name=stream_name):
                    self._reported_lost.discard(component)
                    self.submit_hook_status(component, "reapplied", "fd capture reinstalled")

    def _check_subprocess_hook(self) -> None:
        if self._subprocess_capture is None or not self._subprocess_capture.installed:
            return
        component = "subprocess"
        if self._subprocess_capture.is_current():
            self._reported_lost.discard(component)
            return
        self._report_lost_once(component, "subprocess.Popen was replaced")
        if self.hook_policy == "reapply" and self._subprocess_capture.reapply():
            self._reported_lost.discard(component)
            self.submit_hook_status(component, "reapplied", "subprocess.Popen wrapped current object")

    def _report_lost_once(self, component: str, detail: str) -> None:
        if component in self._reported_lost:
            return
        self._reported_lost.add(component)
        self.submit_hook_status(component, "lost", detail)

    def _apply_policy(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.policy == "raw" or self.max_chars <= 0:
            return payload
        truncated = False

        def truncate_value(value: Any) -> Any:
            nonlocal truncated
            if isinstance(value, str) and len(value) > self.max_chars:
                truncated = True
                return value[: self.max_chars]
            if isinstance(value, dict):
                return {key: truncate_value(item) for key, item in value.items()}
            if isinstance(value, list):
                return [truncate_value(item) for item in value]
            return value

        payload = truncate_value(payload)
        if truncated and isinstance(payload, dict):
            payload["truncated"] = True
        return payload

    def _mark_dropped(self, reason: str) -> None:
        with self._dropped_lock:
            self._dropped += 1

    def _take_dropped(self) -> int:
        with self._dropped_lock:
            count = self._dropped
            self._dropped = 0
            return count

    def _run(self) -> None:
        while not self._stop.is_set() or not self.queue.empty():
            self._check_hooks()
            try:
                message = self.queue.get(timeout=0.05)
            except queue.Empty:
                self._flush_dropped()
                continue
            self._flush_dropped()
            self._send(message.message_type, message.payload)
            self.queue.task_done()
        self._flush_dropped()

    def _flush_dropped(self) -> None:
        count = self._take_dropped()
        if count <= 0:
            return
        self._send("log.dropped", {"count": count, "reason": "queue_full"})

    def _send(self, message_type: str, payload: dict[str, Any]) -> None:
        if getattr(self._guard, "active", False):
            return
        self._guard.active = True
        try:
            self.client.transport.event(message_type, payload)
        except Exception:
            return
        finally:
            self._guard.active = False


def _config_logs(config: dict[str, Any] | None) -> dict[str, Any] | bool:
    if not isinstance(config, dict):
        return False
    logs = config.get("logs", False)
    return logs if isinstance(logs, dict) else bool(logs)


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_value(name: str, default: Any) -> str:
    value = os.getenv(name)
    if value is None:
        return str(default)
    return value


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _env_list(name: str, default: Iterable[str]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None:
        return tuple(str(item).strip() for item in default if str(item).strip())
    if not value.strip():
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _env_streams(config_logs: dict[str, Any] | bool) -> tuple[str, ...]:
    default: Iterable[str] = DEFAULT_STREAMS
    if isinstance(config_logs, dict):
        default_value = config_logs.get("streams", DEFAULT_STREAMS)
        if isinstance(default_value, str):
            default = default_value.split(",")
        else:
            default = default_value
    streams = _env_list("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOG_STREAMS", default)
    if len(streams) == 1 and streams[0].lower() in {"0", "false", "none", "off"}:
        return ()
    return streams


def _get_std_stream(stream_name: str) -> TextIO:
    return sys.stderr if stream_name == "stderr" else sys.stdout


def _set_std_stream(stream_name: str, stream: TextIO) -> None:
    if stream_name == "stderr":
        sys.stderr = stream  # type: ignore[assignment]
    else:
        sys.stdout = stream  # type: ignore[assignment]


def _same_fd_target(left: int, right: int) -> bool:
    try:
        left_stat = os.fstat(left)
        right_stat = os.fstat(right)
    except OSError:
        return False
    return (left_stat.st_dev, left_stat.st_ino) == (right_stat.st_dev, right_stat.st_ino)


def _matches_prefix(name: str, prefixes: tuple[str, ...]) -> bool:
    for prefix in prefixes:
        if name == prefix or name.startswith(prefix + "."):
            return True
    return False


def _get_popen_option(popenargs: tuple[Any, ...], kwargs: dict[str, Any], name: str, index: int) -> Any:
    if name in kwargs:
        return kwargs[name]
    if len(popenargs) > index:
        return popenargs[index]
    return None


def _set_popen_option(
    popenargs: tuple[Any, ...],
    kwargs: dict[str, Any],
    name: str,
    index: int,
    value: Any,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    if len(popenargs) > index and name not in kwargs:
        args_list = list(popenargs)
        args_list[index] = value
        return tuple(args_list), kwargs
    kwargs[name] = value
    return popenargs, kwargs


def _communicate_has_input(args: tuple[Any, ...], kwargs: dict[str, Any]) -> bool:
    if "input" in kwargs and kwargs["input"] is not None:
        return True
    return bool(args and args[0] is not None)


def _communicate_timeout(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    if "timeout" in kwargs:
        return kwargs["timeout"]
    if len(args) > 1:
        return args[1]
    return None


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode(getpreferredencoding(False), errors="replace")
    return str(value)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return _to_text(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return repr(value)
