"""运行时日志采集工具"""

from __future__ import annotations

import logging
import os
import queue
import subprocess
import sys
import threading
from dataclasses import dataclass
from locale import getpreferredencoding
from typing import Any, Iterable, TextIO

from .client import RuntimeClient

DEFAULT_MAX_CHARS = 8192
DEFAULT_QUEUE_SIZE = 1000
DEFAULT_STREAMS = ("stdout", "stderr")
DEFAULT_LOGGER_EXCLUDE = ("sd_webui_all_in_one_hotpatcher",)

_current_capture: LogCapture | None = None
_guard = threading.local()


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

    Returns:
        LogCapture:
            已安装的日志采集器
    """

    global _current_capture

    if _current_capture is not None and not _current_capture.closed:
        return _current_capture

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
    )
    capture.install()
    _current_capture = capture
    return capture


def uninstall_log_capture() -> None:
    """卸载当前进程级日志采集器"""

    global _current_capture

    capture = _current_capture
    _current_capture = None
    if capture is not None:
        capture.close()


def configure_log_capture_from_env(
    client: RuntimeClient,
    config: dict[str, Any] | None = None,
) -> "LogCapture | None":
    """
    根据环境变量和配置安装日志采集

    ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_LOGS=1`` 或配置中的 ``logs`` 为真时启用。

    Args:
        client (RuntimeClient):
            发送日志事件的运行时客户端
        config (dict[str, Any] | None):
            已加载的运行时配置

    Returns:
        LogCapture | None:
            已安装的日志采集器。未启用时返回 None。
    """

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
            config_logs.get("logger_exclude", DEFAULT_LOGGER_EXCLUDE)
            if isinstance(config_logs, dict)
            else DEFAULT_LOGGER_EXCLUDE,
        ),
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

    写入时会先写回原始 stream, 再把文本作为 ``log.stream`` 事件送入采集器。

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

        result = self.original.write(text)
        if text and self.capture.should_capture():
            self.capture.submit_stream(self.stream_name, text, source="stream")
        return result

    def flush(self) -> None:
        """刷新原始 stream"""

        return self.original.flush()

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
        self.installed = False
        self._reader_threads: list[threading.Thread] = []

    def install(self) -> None:
        """安装 subprocess.Popen patch"""

        if self.installed or self.mode in {"0", "false", "none", "off"}:
            return
        if self.mode not in {"safe", "force"}:
            raise ValueError("subprocess_mode must be 0, safe, or force")
        subprocess.Popen = self._popen  # type: ignore[assignment]
        self.installed = True

    def uninstall(self) -> None:
        """卸载 subprocess.Popen patch"""

        if not self.installed:
            return
        subprocess.Popen = self.original_popen  # type: ignore[assignment]
        self.installed = False

    def _popen(self, *popenargs: Any, **kwargs: Any) -> subprocess.Popen:
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

        process = self.original_popen(*popenargs, **kwargs)
        communicate_stdout = None if forced_stdout else stdout_value
        communicate_stderr = None if forced_stderr else stderr_value
        self._patch_communicate(process, args_value, communicate_stdout, communicate_stderr)

        if forced_stdout and process.stdout is not None:
            self._start_reader(process, "stdout", process.stdout, self.stdout_stream, args_value)
        if forced_stderr and process.stderr is not None:
            self._start_reader(process, "stderr", process.stderr, self.stderr_stream, args_value)

        return process

    def _patch_communicate(
        self,
        process: subprocess.Popen,
        args_value: Any,
        stdout_value: Any,
        stderr_value: Any,
    ) -> None:
        original_communicate = process.communicate
        capture_stdout = stdout_value is subprocess.PIPE
        capture_stderr = stderr_value is subprocess.PIPE

        if not capture_stdout and not capture_stderr:
            return

        def communicate(*args: Any, **kwargs: Any) -> tuple[Any, Any]:
            stdout_data, stderr_data = original_communicate(*args, **kwargs)
            if capture_stdout and stdout_data:
                self.capture.submit_subprocess_stream("stdout", stdout_data, process, args_value)
            if capture_stderr and stderr_data:
                self.capture.submit_subprocess_stream("stderr", stderr_data, process, args_value)
            return stdout_data, stderr_data

        process.communicate = communicate  # type: ignore[method-assign]

    def _start_reader(
        self,
        process: subprocess.Popen,
        stream_name: str,
        pipe: Any,
        target: TextIO,
        args_value: Any,
    ) -> None:
        thread = threading.Thread(
            target=self._reader,
            args=(process, stream_name, pipe, target, args_value),
            daemon=True,
        )
        self._reader_threads.append(thread)
        thread.start()

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
    ):
        if policy not in {"bounded", "raw"}:
            raise ValueError("policy must be bounded or raw")
        self.client = client
        self.capture_logging = capture_logging
        self.streams = streams
        self.subprocess_mode = subprocess_mode
        self.policy = policy
        self.max_chars = max(0, max_chars)
        self.logger_include = logger_include
        self.logger_exclude = logger_exclude
        self.queue: queue.Queue[LogMessage] = queue.Queue(maxsize=max(0, queue_size))
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="sd_webui_all_in_one_hotpatcher-log-capture", daemon=True)
        self._dropped = 0
        self._dropped_lock = threading.Lock()
        self._root_handler: RuntimeLogHandler | None = None
        self._original_stdout: TextIO | None = None
        self._original_stderr: TextIO | None = None
        self._subprocess_capture: SubprocessCapture | None = None
        self.closed = False

    def install(self) -> None:
        """安装日志采集 hook 并启动后台发送线程"""

        self._thread.start()
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

    def should_capture(self) -> bool:
        """
        判断当前线程是否允许采集日志

        Returns:
            bool:
                未处于递归保护状态时返回 True
        """

        return not getattr(_guard, "active", False)

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

    def _uninstall_logging(self) -> None:
        if self._root_handler is None:
            return
        try:
            logging.getLogger().removeHandler(self._root_handler)
        finally:
            self._root_handler = None

    def _install_streams(self) -> None:
        stream_names = {name.strip().lower() for name in self.streams}
        if "stdout" in stream_names:
            self._original_stdout = sys.stdout
            sys.stdout = StreamTee(self, "stdout", sys.stdout)  # type: ignore[assignment]
        if "stderr" in stream_names:
            self._original_stderr = sys.stderr
            sys.stderr = StreamTee(self, "stderr", sys.stderr)  # type: ignore[assignment]

    def _uninstall_streams(self) -> None:
        if self._original_stdout is not None:
            sys.stdout = self._original_stdout
            self._original_stdout = None
        if self._original_stderr is not None:
            sys.stderr = self._original_stderr
            self._original_stderr = None

    def _install_subprocess(self) -> None:
        if self.subprocess_mode in {"0", "false", "none", "off"}:
            return
        stdout_stream = self._original_stdout or sys.stdout
        stderr_stream = self._original_stderr or sys.stderr
        capture = SubprocessCapture(self, self.subprocess_mode, stdout_stream, stderr_stream)
        capture.install()
        self._subprocess_capture = capture

    def _uninstall_subprocess(self) -> None:
        if self._subprocess_capture is None:
            return
        self._subprocess_capture.uninstall()
        self._subprocess_capture = None

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
        if getattr(_guard, "active", False):
            return
        _guard.active = True
        try:
            self.client.transport.event(message_type, payload)
        except Exception:
            return
        finally:
            _guard.active = False


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
