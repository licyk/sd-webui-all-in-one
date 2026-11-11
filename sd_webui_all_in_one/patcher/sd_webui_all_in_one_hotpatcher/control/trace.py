"""TagTracer 风格的分层跟踪输出。

借鉴 pluggy ``TagTracer``: 标签分层 (``patch`` 启用后 ``patch.failed`` 也会输出), 关闭时调用点只需一次属性检查。
调用点约定先读取 ``state.tracer`` (可能为 None), 再检查 ``tracer.active`` / ``tracer.enabled_for(tag)``,
只有启用时才格式化消息, 因此关闭跟踪时不会产生任何字符串格式化开销::

    tracer = state.tracer
    if tracer is not None and tracer.active and tracer.enabled_for("set"):
        tracer.trace("set", "set loaded", {"name": name})

输出格式与 pluggy 相同: ``<缩进><消息> [hotpatch:<标签>]``, 每个附加字段单独一行 ``<缩进>    <键>: <值>``。
``section`` 上下文管理器在块内增加缩进 (按线程独立)。字段值会经过 ``redact_mapping`` 处理,
键名包含 ``token``、``secret``、``password`` 等的值被替换为 ``***``, 跟踪输出中永远不会出现 token。

环境变量 ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TRACE`` 为逗号分隔的标签或 ``all``;
``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TRACE_FILE`` 指定输出文件 (追加写入), 未设置时写入 stderr。
"""

from __future__ import annotations

import os
import sys
import threading
import time
from collections.abc import Callable, Generator, Iterable, Mapping
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, TextIO
from urllib.parse import urlsplit, urlunsplit

from ..state import TRACE_ENV, TRACE_FILE_ENV, get_default_state

if TYPE_CHECKING:
    from ..state import HotpatcherState

__all__ = [
    "MAX_TRACE_VALUE_CHARS",
    "REDACTED",
    "TRACE_ALL",
    "TRACE_ENV",
    "TRACE_FILE_ENV",
    "TRACE_TAGS",
    "HotpatchTracer",
    "configure_tracer_from_env",
    "get_trace",
    "get_tracer",
    "is_secret_key",
    "parse_trace_tags",
    "redact_mapping",
    "redact_url",
    "redact_value",
    "set_trace",
]

TRACE_TAGS: tuple[str, ...] = ("import", "patch", "control", "conn", "set", "feature")
"""顶层跟踪标签: import (finder 命中与跳过)、patch (补丁执行与结果)、control (命令分发)、conn (连接变化)、
set (补丁集加载/卸载/重新加载)、feature (功能启用/禁用/修改)"""

TRACE_ALL = "all"
"""启用全部标签的取值"""

REDACTED = "***"
"""敏感值的替代文本"""

MAX_TRACE_VALUE_CHARS = 500
"""单个跟踪字段值的最大字符数"""

_SECRET_KEY_PARTS = ("token", "secret", "password", "passwd", "authorization", "cookie", "credential", "api_key", "apikey", "sessionid", "session_id")
_ROOT_TAG = "hotpatch"
_UNCHANGED: Any = object()


def is_secret_key(key: Any) -> bool:
    """
    判断字段名是否表示敏感值。

    Args:
        key (Any):
            字段名, 非字符串时返回 False。

    Returns:
        bool:
            小写字段名包含 ``token``、``secret``、``password`` 等片段时返回 True。
    """

    if not isinstance(key, str):
        return False
    lowered = key.lower()
    return any(part in lowered for part in _SECRET_KEY_PARTS)


def redact_value(key: Any, value: Any) -> Any:
    """
    按字段名脱敏单个值。

    Args:
        key (Any):
            字段名。
        value (Any):
            字段值。

    Returns:
        Any:
            敏感且非空的值返回 ``***``; 空字符串、None 和布尔值 (例如 ``token_set``) 原样返回, 以便区分"未设置"。其他值原样返回。
    """

    if is_secret_key(key) and _is_secret_value(value):
        return REDACTED
    return value


def _is_secret_value(value: Any) -> bool:
    return value is not None and value != "" and not isinstance(value, bool)


def redact_url(url: Any) -> Any:
    """
    去除 URL 中的用户信息和查询参数。

    Args:
        url (Any):
            URL 字符串, 非字符串原样返回。

    Returns:
        Any:
            脱敏后的 URL: 用户信息替换为 ``***``, 查询串和片段替换为 ``***``。
    """

    if not isinstance(url, str) or not url:
        return url
    try:
        parts = urlsplit(url)
    except ValueError:
        return REDACTED
    netloc = parts.netloc
    if "@" in netloc:
        netloc = f"{REDACTED}@{netloc.rsplit('@', 1)[1]}"
    query = REDACTED if parts.query else ""
    fragment = REDACTED if parts.fragment else ""
    return urlunsplit((parts.scheme, netloc, parts.path, query, fragment))


def redact_mapping(value: Any) -> Any:
    """
    递归脱敏映射和列表中的敏感字段。

    Args:
        value (Any):
            任意值。映射按键名脱敏, 列表和元组逐项处理, 深度超过 8 层的部分原样返回。

    Returns:
        Any:
            脱敏后的副本 (映射变为 dict, 元组变为 list); 其他值原样返回。
    """

    return _redact(value, 0)


def _redact(value: Any, depth: int) -> Any:
    if depth > 8:
        return value
    if isinstance(value, Mapping):
        result: dict[Any, Any] = {}
        for key, item in value.items():
            if is_secret_key(key) and _is_secret_value(item):
                result[key] = REDACTED
            elif isinstance(key, str) and key.lower().endswith("url"):
                result[key] = redact_url(item)
            else:
                result[key] = _redact(item, depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [_redact(item, depth + 1) for item in value]
    return value


def parse_trace_tags(value: str | Iterable[str] | None, *, strict: bool = False) -> frozenset[str]:
    """
    规范化跟踪标签。

    Args:
        value (str | Iterable[str] | None):
            逗号分隔的字符串或标签序列; ``all`` (或 ``1``、``*``) 表示全部顶层标签; None 或空表示关闭。
            标签可以是顶层标签或其子标签 (例如 ``patch.failed``)。
        strict (bool):
            为 True 时未知标签抛出 ``ValueError``; 否则忽略未知标签 (用于解析环境变量)。

    Returns:
        frozenset[str]:
            规范化后的标签集合。

    Raises:
        ValueError:
            ``strict`` 为 True 且存在未知标签时抛出。
        TypeError:
            ``value`` 类型不受支持时抛出。
    """

    if value is None:
        return frozenset()
    if isinstance(value, str):
        items = value.split(",")
    elif isinstance(value, Iterable):
        items = list(value)
    else:
        raise TypeError(f"trace tags must be a string or a list of strings, got {type(value).__name__}")
    tags: set[str] = set()
    unknown: list[str] = []
    for item in items:
        if not isinstance(item, str):
            raise TypeError(f"trace tag must be a string, got {type(item).__name__}")
        tag = item.strip().lower()
        if not tag:
            continue
        if tag in (TRACE_ALL, "1", "*"):
            tags.update(TRACE_TAGS)
            continue
        if tag.split(".", 1)[0] not in TRACE_TAGS:
            unknown.append(tag)
            continue
        tags.add(tag)
    if unknown and strict:
        raise ValueError(f"unknown trace tags: {', '.join(sorted(unknown))}; available: {', '.join(TRACE_TAGS)}")
    return frozenset(tags)


class HotpatchTracer:
    """
    分层标签跟踪输出器。

    ``active`` 为 False 时 ``trace`` 直接返回; 调用点应先检查 ``active`` 再构造消息。写入失败会被忽略。

    Attributes:
        active (bool):
            是否启用了任何标签。
    """

    def __init__(
        self,
        tags: str | Iterable[str] | None = None,
        *,
        file: str | os.PathLike[str] | None = None,
        writer: Callable[[str], Any] | None = None,
    ) -> None:
        """
        创建跟踪输出器。

        Args:
            tags (str | Iterable[str] | None):
                启用的标签, 见 ``parse_trace_tags`` (严格校验)。
            file (str | os.PathLike[str] | None):
                输出文件路径 (追加写入)。为 None 时写入 stderr。
            writer (Callable[[str], Any] | None):
                自定义写入函数, 接收完整的一行或多行文本; 提供时忽略 ``file``。主要用于测试。
        """

        self.active = False
        self._tags: frozenset[str] = frozenset()
        self._decisions: dict[str, bool] = {}
        self._file: str | None = None
        self._stream: TextIO | None = None
        self._writer = writer
        self._lock = threading.Lock()
        self._local = threading.local()
        self.configure(tags, file=file)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> HotpatchTracer:
        """
        根据环境变量创建跟踪输出器, 忽略未知标签。

        Args:
            environ (Mapping[str, str] | None):
                环境变量映射。为 None 时使用 ``os.environ``。

        Returns:
            HotpatchTracer:
                新跟踪输出器; 未设置 ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_TRACE`` 时为关闭状态。
        """

        source = os.environ if environ is None else environ
        tags = parse_trace_tags(source.get(TRACE_ENV, ""))
        file = source.get(TRACE_FILE_ENV) or None
        tracer = cls()
        tracer._tags = tags
        tracer._file = file
        tracer._reset_decisions()
        return tracer

    @property
    def tags(self) -> list[str]:
        """
        已启用的标签。

        Returns:
            list[str]:
                排序后的标签列表。
        """

        return sorted(self._tags)

    @property
    def file(self) -> str | None:
        """
        输出文件路径。

        Returns:
            str | None:
                文件路径, 写入 stderr 或自定义写入函数时为 None。
        """

        return self._file

    def enabled_for(self, tag: str) -> bool:
        """
        判断标签是否启用, 子标签继承父标签。

        Args:
            tag (str):
                标签, 例如 ``patch`` 或 ``patch.failed``。

        Returns:
            bool:
                标签本身或其任一父标签启用时返回 True。
        """

        if not self.active:
            return False
        # 读取本地引用: configure 并发替换字典时, 旧决策只会写入旧字典, 不会污染新配置。
        decisions = self._decisions
        tags = self._tags
        decision = decisions.get(tag)
        if decision is None:
            decision = False
            candidate = tag
            while True:
                if candidate in tags:
                    decision = True
                    break
                if "." not in candidate:
                    break
                candidate = candidate.rsplit(".", 1)[0]
            decisions[tag] = decision
        return decision

    def configure(self, tags: str | Iterable[str] | None, *, file: Any = _UNCHANGED) -> None:
        """
        修改启用的标签和输出目标。

        Args:
            tags (str | Iterable[str] | None):
                新标签集合 (严格校验), 空表示关闭。
            file (Any):
                新输出文件路径; 不传时保持当前目标, None 或空字符串表示改为 stderr。

        Raises:
            ValueError:
                存在未知标签时抛出。
            TypeError:
                标签或文件参数类型不受支持时抛出。
        """

        parsed = parse_trace_tags(tags, strict=True)
        if file is not _UNCHANGED:
            if file is not None and not isinstance(file, (str, os.PathLike)):
                raise TypeError(f"trace file must be a path string, got {type(file).__name__}")
            new_file = os.fspath(file) if file else None
            if isinstance(new_file, bytes):
                raise TypeError("trace file must be a text path")
            with self._lock:
                if new_file != self._file:
                    self._close_stream_locked()
                    self._file = new_file
        self._tags = parsed
        self._reset_decisions()

    def trace(self, tag: str, message: str, fields: Mapping[str, Any] | None = None) -> None:
        """
        输出一条跟踪消息。

        Args:
            tag (str):
                标签。
            message (str):
                消息正文。
            fields (Mapping[str, Any] | None):
                附加字段, 敏感字段会被脱敏, 每个值最多 ``MAX_TRACE_VALUE_CHARS`` 字符。
        """

        if not self.enabled_for(tag):
            return
        self._write(self._format(tag, message, fields))

    @contextmanager
    def section(self, tag: str, message: str, fields: Mapping[str, Any] | None = None) -> Generator[None, None, None]:
        """
        输出一条消息并在块内增加缩进; 标签未启用时不输出也不缩进。

        Args:
            tag (str):
                标签。
            message (str):
                消息正文。
            fields (Mapping[str, Any] | None):
                附加字段。

        Yields:
            None: 块执行期间。
        """

        if not self.enabled_for(tag):
            yield
            return
        started = time.perf_counter()
        self._write(self._format(tag, message, fields))
        self._local.indent = getattr(self._local, "indent", 0) + 1
        try:
            yield
        finally:
            self._local.indent = max(0, getattr(self._local, "indent", 1) - 1)
            self._write(self._format(tag, f"{message} done", {"elapsed_ms": round((time.perf_counter() - started) * 1000, 3)}))

    def close(self) -> None:
        """关闭输出文件。之后写入会重新打开文件。"""

        with self._lock:
            self._close_stream_locked()

    def to_dict(self) -> dict[str, Any]:
        """
        生成可序列化的状态描述。

        Returns:
            dict[str, Any]:
                ``enabled``、``tags``、``file``、``available_tags``。
        """

        return {
            "enabled": self.active,
            "tags": self.tags,
            "file": self._file,
            "available_tags": list(TRACE_TAGS),
        }

    def _reset_decisions(self) -> None:
        self._decisions = {}
        self.active = bool(self._tags)

    def _format(self, tag: str, message: str, fields: Mapping[str, Any] | None) -> str:
        indent = "  " * getattr(self._local, "indent", 0)
        lines = [f"{indent}{message} [{_ROOT_TAG}:{tag}]\n"]
        if fields:
            for key, value in redact_mapping(fields).items():
                text = str(value)
                if len(text) > MAX_TRACE_VALUE_CHARS:
                    text = text[: MAX_TRACE_VALUE_CHARS - 3] + "..."
                lines.append(f"{indent}    {key}: {text}\n")
        return "".join(lines)

    def _write(self, text: str) -> None:
        writer = self._writer
        try:
            if writer is not None:
                writer(text)
                return
            with self._lock:
                if self._file is None:
                    stream = sys.stderr
                    if stream is not None:
                        stream.write(text)
                    return
                if self._stream is None:
                    self._stream = open(self._file, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
                self._stream.write(text)
        except Exception:
            # 跟踪输出是尽力而为的诊断信息, 写入失败不能影响被跟踪的代码。
            return

    def _close_stream_locked(self) -> None:
        stream = self._stream
        self._stream = None
        if stream is not None:
            try:
                stream.close()
            except Exception:
                return


def get_tracer(*, state: HotpatcherState | None = None) -> HotpatchTracer:
    """
    获取状态对象的跟踪输出器, 首次访问时根据环境变量创建。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        HotpatchTracer:
            跟踪输出器。
    """

    active_state = state or get_default_state()
    tracer = active_state.tracer
    if tracer is not None:
        return tracer
    created = HotpatchTracer.from_env()
    with active_state.control_lock:
        if active_state.tracer is None:
            active_state.tracer = created
        return active_state.tracer


def configure_tracer_from_env(*, state: HotpatcherState | None = None) -> HotpatchTracer:
    """
    根据环境变量 (重新) 配置跟踪输出器, 供 bootstrap 调用。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        HotpatchTracer:
            跟踪输出器。
    """

    active_state = state or get_default_state()
    fresh = HotpatchTracer.from_env()
    tracer = get_tracer(state=active_state)
    if tracer is not fresh:
        tracer.configure(fresh.tags, file=fresh.file)
    return tracer


def set_trace(
    tags: str | Iterable[str] | None,
    *,
    file: str | os.PathLike[str] | None = None,
    state: HotpatcherState | None = None,
) -> dict[str, Any]:
    """
    在运行时修改跟踪标签和输出目标, 并记录 ``debug.trace.changed`` 事件。

    Args:
        tags (str | Iterable[str] | None):
            新标签集合, ``all`` 表示全部, 空或 None 表示关闭。未知标签抛出 ``ValueError``。
        file (str | os.PathLike[str] | None):
            新输出文件路径。为 None 时保持当前目标, 空字符串表示改为 stderr。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            修改后的状态, 同 ``get_trace``。
    """

    active_state = state or get_default_state()
    tracer = get_tracer(state=active_state)
    previous = tracer.tags
    if file is None:
        tracer.configure(tags)
    else:
        tracer.configure(tags, file=file)
    result = tracer.to_dict()

    from .events import record_event

    record_event("debug.trace.changed", {"tags": result["tags"], "previous": previous, "file": result["file"]}, state=active_state, tag="control")
    return result


def get_trace(*, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    查询跟踪状态。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            ``enabled``、``tags``、``file``、``available_tags``。
    """

    return get_tracer(state=state).to_dict()
