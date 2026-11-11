"""统一控制命令注册表。

所有控制入口 (进程内 Python API、旧版 services 通道、桌面代理命令) 都经由 ``CommandRegistry.dispatch``
这一个分发点: 解析名称 (含别名) → 传输策略 → 载荷校验 → 调用处理函数 → 生成 envelope → 跟踪计时。
``dispatch`` 从不抛出异常, 任何失败都以错误 envelope 返回。

Envelope 结构与 services v1 一致::

    {"ok": true, "payload": {...}}
    {"ok": false, "error": {"code": "...", "message": "..."}}

``hotpatch.*`` 命令的错误对象可以额外带 ``details`` (例如加载补丁失败时的完整报告); ``services.*`` 命令的
错误对象永远只有 ``code`` 与 ``message``。

传输策略:

- ``remote=False``: 只允许 ``inprocess`` 传输, 其他传输返回 ``forbidden``;
- ``blocking=True``: 桌面传输返回 ``unsupported_transport`` 且不调用处理函数 (桌面命令运行在唯一的代理
  工作线程上, 该线程同时负责心跳与事件上传);
- ``requires_token=True``: 旧版传输的 token 为空时返回 ``forbidden``。
"""

from __future__ import annotations

import copy
import json
import logging
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..state import HotpatcherState

__all__ = [
    "CONTROL_VERSION",
    "ERROR_CODES",
    "MAX_DESKTOP_RESULT_BYTES",
    "PAYLOAD_TYPES",
    "TRANSPORTS",
    "CommandContext",
    "CommandError",
    "CommandHandler",
    "CommandRegistry",
    "CommandSpec",
    "PayloadField",
    "error_envelope",
    "run_after_send",
    "success_envelope",
    "unwrap_envelope",
    "validate_payload",
]

_LOGGER = logging.getLogger(__name__)

CONTROL_VERSION = 1
"""控制命令集版本, 由 ``hotpatch.capabilities`` 报告; 与运行时协议版本 ``PROTOCOL_VERSION`` 相互独立"""

TRANSPORTS: tuple[str, ...] = ("inprocess", "legacy", "desktop")
"""命令来源传输: 进程内 Python API、旧版 TCP JSONL services 通道、桌面 HTTP 代理"""

ERROR_CODES: tuple[str, ...] = (
    "invalid_request",
    "invalid_json",
    "unknown_request",
    "request_failed",
    "invalid_payload",
    "forbidden",
    "not_found",
    "unsupported_transport",
    "connection_failed",
    "remote_load_disabled",
    "busy",
    "conflict",
)
"""envelope 错误码。前四个沿用 services v1, 其余为控制命令新增"""

PAYLOAD_TYPES: tuple[str, ...] = ("str", "int", "float", "bool", "dict", "list", "any")
"""``PayloadField.type`` 支持的类型名"""

MAX_DESKTOP_RESULT_BYTES = 63 * 1024
"""桌面传输成功结果载荷 JSON 编码后的字节上限; 低于代理的 64 KiB 上限, 为 ``config.apply`` 的结果重命名留出余量"""

MAX_COMMAND_NAME_CHARS = 128
"""命令名与别名的最大长度, 与桌面代理的 ``commandType`` 上限一致"""

UNKNOWN_REQUEST_MESSAGE = "unknown services request: {name}"
"""未知命令的错误信息模板, 与 services v1 一致"""

_PYTHON_TYPES: dict[str, tuple[type, ...]] = {
    "str": (str,),
    "int": (int,),
    "float": (int, float),
    "bool": (bool,),
    "dict": (dict,),
    "list": (list,),
}


class _Missing:
    """表示字段没有默认值的哨兵类型。"""

    _instance: _Missing | None = None

    def __new__(cls) -> _Missing:
        """
        返回唯一实例。

        Returns:
            _Missing:
                哨兵实例。
        """

        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        """
        返回调试表示。

        Returns:
            str:
                ``MISSING``。
        """

        return "MISSING"


MISSING = _Missing()
"""``PayloadField.default`` 的默认值, 表示缺省时不填充"""


class CommandError(Exception):
    """
    命令处理函数抛出的强类型错误, ``dispatch`` 会把它转换为错误 envelope。

    Attributes:
        code (str):
            错误码, 通常取自 ``ERROR_CODES``。
        message (str):
            错误描述。
        details (dict[str, Any] | None):
            附加信息 (例如失败的加载报告), 只出现在 ``hotpatch.*`` 命令的错误 envelope 中。
    """

    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        """
        创建错误。

        Args:
            code (str):
                错误码。
            message (str):
                错误描述。
            details (dict[str, Any] | None):
                附加信息。
        """

        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


@dataclass(frozen=True)
class PayloadField:
    """
    命令载荷字段的轻量声明。

    Attributes:
        type (str):
            类型名, 取值见 ``PAYLOAD_TYPES``。``int`` 不接受 bool; ``float`` 接受 int 并转换为 float。
        required (bool):
            是否必须提供。
        choices (tuple[Any, ...] | None):
            允许的取值。
        max_len (int | None):
            ``str`` / ``list`` / ``dict`` 的最大长度。
        default (Any):
            缺省时填充的默认值 (深拷贝), 为 ``MISSING`` 时不填充。
        nullable (bool):
            是否接受 None (视为未提供)。
        description (str):
            字段说明。
    """

    type: str = "any"
    required: bool = False
    choices: tuple[Any, ...] | None = None
    max_len: int | None = None
    default: Any = MISSING
    nullable: bool = False
    description: str = ""

    def __post_init__(self) -> None:
        """
        校验字段声明。

        Raises:
            ValueError:
                类型名未知或 ``max_len`` 不是正整数时抛出。
        """

        if self.type not in PAYLOAD_TYPES:
            raise ValueError(f"unknown payload field type {self.type!r}; expected one of {', '.join(PAYLOAD_TYPES)}")
        if self.max_len is not None and (not isinstance(self.max_len, int) or isinstance(self.max_len, bool) or self.max_len < 0):
            raise ValueError(f"max_len must be a non-negative integer, got {self.max_len!r}")

    def to_dict(self) -> dict[str, Any]:
        """
        生成可序列化的字段描述。

        Returns:
            dict[str, Any]:
                ``type``、``required``、``choices``、``max_len``、``nullable``。
        """

        return {
            "type": self.type,
            "required": self.required,
            "choices": list(self.choices) if self.choices is not None else None,
            "max_len": self.max_len,
            "nullable": self.nullable,
        }


@dataclass
class CommandContext:
    """
    单次命令调用的上下文。

    Attributes:
        state (HotpatcherState):
            目标状态对象。
        transport (str):
            命令来源传输: ``inprocess`` / ``legacy`` / ``desktop``。
        token (str | None):
            旧版通道使用的 token; 进程内与桌面传输为 None。
        runtime_client (Any):
            运行时客户端, 传给需要事件接收端的处理函数 (例如启用日志采集)。
        after_send (list[Callable[[], Any]]):
            响应发出之后执行的回调, 只对成功的命令保留 (命令失败时 ``dispatch`` 丢弃本次登记的回调)。
            旧版通道在写出响应后执行; 进程内调用和桌面命令在分发返回后立即执行。回调之间相互隔离, 失败只记录诊断。
        command (str | None):
            已解析的规范命令名, 由 ``dispatch`` 填写。
    """

    state: HotpatcherState
    transport: str = "inprocess"
    token: str | None = None
    runtime_client: Any = None
    after_send: list[Callable[[], Any]] = field(default_factory=list)
    command: str | None = None

    @property
    def remote(self) -> bool:
        """
        是否来自进程外。

        Returns:
            bool:
                传输不是 ``inprocess`` 时返回 True。
        """

        return self.transport != "inprocess"


CommandHandler = Callable[[CommandContext, dict[str, Any]], dict[str, Any]]
"""命令处理函数: ``handler(ctx, payload) -> dict``, 返回值作为成功 envelope 的 ``payload``"""


@dataclass(frozen=True)
class CommandSpec:
    """
    控制命令声明。

    Attributes:
        name (str):
            规范命令名, 例如 ``hotpatch.patches.list``。
        handler (CommandHandler):
            处理函数, 返回 JSON 安全的 dict; 预期失败抛出 ``CommandError``, 其他异常转换为 ``request_failed``。
        payload (Mapping[str, PayloadField]):
            载荷字段声明。只校验声明过的字段, 未声明的字段原样传给处理函数。
        mutating (bool):
            是否修改进程状态。
        requires_token (bool):
            旧版传输的 token 为空时拒绝 (``forbidden``)。
        remote (bool):
            为 False 时只允许进程内调用。
        blocking (bool):
            是否可能导入模块或执行用户代码; 桌面传输返回 ``unsupported_transport``。
        since (int):
            引入该命令的 ``CONTROL_VERSION``。
        aliases (tuple[str, ...]):
            别名, 例如 ``config.apply``。
        description (str):
            命令说明。
        conditional_blocking (bool):
            是否只在特定载荷下阻塞 (由处理函数在桌面传输上自行拒绝), 仅用于能力报告。
    """

    name: str
    handler: CommandHandler
    payload: Mapping[str, PayloadField] = field(default_factory=dict)
    mutating: bool = False
    requires_token: bool = False
    remote: bool = True
    blocking: bool = False
    since: int = 1
    aliases: tuple[str, ...] = ()
    description: str = ""
    conditional_blocking: bool = False

    def __post_init__(self) -> None:
        """
        校验命令声明。

        Raises:
            ValueError:
                名称或别名为空、过长, 或载荷字段声明类型错误时抛出。
            TypeError:
                ``handler`` 不可调用时抛出。
        """

        for value in (self.name, *self.aliases):
            _validate_command_name(value)
        if not callable(self.handler):
            raise TypeError(f"command {self.name!r} handler must be callable")
        for key, spec in self.payload.items():
            if not isinstance(key, str) or not key:
                raise ValueError(f"command {self.name!r} payload field names must be non-empty strings")
            if not isinstance(spec, PayloadField):
                raise ValueError(f"command {self.name!r} payload field {key!r} must be a PayloadField")

    def flags(self) -> dict[str, Any]:
        """
        生成可序列化的命令标记。

        Returns:
            dict[str, Any]:
                ``mutating``、``blocking``、``conditional_blocking``、``remote``、``requires_token``、``since``、``aliases``。
        """

        return {
            "mutating": self.mutating,
            "blocking": self.blocking,
            "conditional_blocking": self.conditional_blocking,
            "remote": self.remote,
            "requires_token": self.requires_token,
            "since": self.since,
            "aliases": list(self.aliases),
        }


def success_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    """
    构造成功 envelope。

    Args:
        payload (dict[str, Any]):
            结果载荷。

    Returns:
        dict[str, Any]:
            ``{"ok": True, "payload": payload}``。
    """

    return {"ok": True, "payload": payload}


def error_envelope(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    构造错误 envelope。

    Args:
        code (str):
            错误码。
        message (str):
            错误描述。
        details (dict[str, Any] | None):
            附加信息, 为 None 时不出现 ``details`` 键。

    Returns:
        dict[str, Any]:
            ``{"ok": False, "error": {"code", "message"[, "details"]}}``。
    """

    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"ok": False, "error": error}


def unwrap_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """
    取出成功 envelope 的载荷, 错误 envelope 转换为 ``CommandError``。

    Args:
        envelope (Mapping[str, Any]):
            ``dispatch`` 返回的 envelope。

    Returns:
        dict[str, Any]:
            成功载荷。

    Raises:
        CommandError:
            envelope 表示失败时抛出, 保留错误码、信息与 ``details``。
    """

    if envelope.get("ok") is True:
        payload = envelope.get("payload")
        return payload if isinstance(payload, dict) else {}
    error = envelope.get("error")
    error = error if isinstance(error, Mapping) else {}
    details = error.get("details")
    raise CommandError(str(error.get("code") or "request_failed"), str(error.get("message") or ""), details=details if isinstance(details, dict) else None)


def run_after_send(callbacks: list[Callable[[], Any]], *, on_error: Callable[[BaseException], Any] | None = None) -> None:
    """
    依次执行响应后回调并清空列表, 每个回调的异常相互隔离。

    Args:
        callbacks (list[Callable[[], Any]]):
            回调列表, 执行后被清空。
        on_error (Callable[[BaseException], Any] | None):
            回调抛出 ``Exception`` 时调用, 用于记录诊断; 为 None 时写入日志。
    """

    pending = list(callbacks)
    callbacks.clear()
    for callback in pending:
        try:
            callback()
        except Exception as exc:
            if on_error is None:
                _LOGGER.warning("hotpatch control after_send callback failed: %s: %s", type(exc).__name__, exc)
                continue
            try:
                on_error(exc)
            except Exception:
                _LOGGER.warning("hotpatch control after_send diagnostic failed", exc_info=True)


def validate_payload(spec: CommandSpec, payload: dict[str, Any]) -> dict[str, Any]:
    """
    按命令声明校验载荷并填充默认值。

    Args:
        spec (CommandSpec):
            命令声明。
        payload (dict[str, Any]):
            原始载荷。

    Returns:
        dict[str, Any]:
            新的载荷字典: 未声明的字段原样保留, 声明的字段经过校验, ``float`` 字段转换为 float,
            缺省字段按 ``default`` 填充。

    Raises:
        CommandError:
            校验失败时抛出, 错误码为 ``invalid_payload``。
    """

    result = dict(payload)
    for key, declared in spec.payload.items():
        present = key in payload and not (declared.nullable and payload[key] is None)
        if not present:
            if declared.required:
                raise CommandError("invalid_payload", f"payload.{key} is required")
            result.pop(key, None)
            if declared.default is not MISSING:
                result[key] = copy.deepcopy(declared.default)
            continue
        value = payload[key]
        if declared.type != "any":
            expected = _PYTHON_TYPES[declared.type]
            if not isinstance(value, expected) or (declared.type in {"int", "float"} and isinstance(value, bool)):
                raise CommandError("invalid_payload", f"payload.{key} must be of type {declared.type}, got {type(value).__name__}")
            if declared.type == "float":
                value = float(value)
        if declared.choices is not None and value not in declared.choices:
            choices = ", ".join(repr(choice) for choice in declared.choices)
            raise CommandError("invalid_payload", f"payload.{key} must be one of {choices}, got {value!r}")
        if declared.max_len is not None and isinstance(value, (str, list, dict)) and len(value) > declared.max_len:
            raise CommandError("invalid_payload", f"payload.{key} exceeds the maximum length of {declared.max_len}")
        if declared.type == "str" and declared.required and isinstance(value, str) and not value.strip():
            raise CommandError("invalid_payload", f"payload.{key} must be a non-empty string")
        result[key] = value
    return result


class CommandRegistry:
    """
    命令注册表与唯一分发点。

    注册表自身的读写使用内部叶子锁; 处理函数总在锁外调用。
    """

    def __init__(self) -> None:
        """创建空注册表。"""

        self._specs: dict[str, CommandSpec] = {}
        self._aliases: dict[str, str] = {}
        self._lock = threading.Lock()

    def register(self, spec: CommandSpec, *, replace: bool = False) -> CommandSpec:
        """
        注册命令。

        Args:
            spec (CommandSpec):
                命令声明。
            replace (bool):
                是否替换同名命令 (连同其别名)。

        Returns:
            CommandSpec:
                同一个命令声明。

        Raises:
            ValueError:
                名称或别名已被其他命令占用且未指定 ``replace`` 时抛出。
        """

        with self._lock:
            existing = self._specs.get(spec.name)
            if existing is not None and not replace:
                raise ValueError(f"command {spec.name!r} is already registered")
            if spec.name in self._aliases:
                raise ValueError(f"command name {spec.name!r} is already registered as an alias of {self._aliases[spec.name]!r}")
            for alias in spec.aliases:
                if alias in self._specs and alias != spec.name:
                    raise ValueError(f"alias {alias!r} collides with a registered command")
                owner = self._aliases.get(alias)
                if owner is not None and owner != spec.name:
                    raise ValueError(f"alias {alias!r} is already registered for {owner!r}")
            if existing is not None:
                for alias in existing.aliases:
                    self._aliases.pop(alias, None)
            self._specs[spec.name] = spec
            for alias in spec.aliases:
                self._aliases[alias] = spec.name
        return spec

    def unregister(self, name: str) -> CommandSpec | None:
        """
        注销命令及其别名。

        Args:
            name (str):
                规范命令名或别名。

        Returns:
            CommandSpec | None:
                被注销的命令, 不存在时为 None。
        """

        with self._lock:
            canonical = self._aliases.get(name, name)
            spec = self._specs.pop(canonical, None)
            if spec is not None:
                for alias in spec.aliases:
                    self._aliases.pop(alias, None)
            return spec

    def names(self, *, include_aliases: bool = False) -> list[str]:
        """
        列出已注册命令名。

        Args:
            include_aliases (bool):
                是否同时列出别名。

        Returns:
            list[str]:
                排序后的名称列表。
        """

        with self._lock:
            names = list(self._specs)
            if include_aliases:
                names.extend(self._aliases)
        return sorted(names)

    def specs(self) -> list[CommandSpec]:
        """
        列出已注册命令声明。

        Returns:
            list[CommandSpec]:
                按名称排序的命令声明列表。
        """

        with self._lock:
            specs = list(self._specs.values())
        return sorted(specs, key=lambda item: item.name)

    def aliases(self) -> dict[str, str]:
        """
        列出别名映射。

        Returns:
            dict[str, str]:
                别名到规范命令名的映射, 按别名排序。
        """

        with self._lock:
            return dict(sorted(self._aliases.items()))

    def get(self, name: str) -> CommandSpec | None:
        """
        按名称或别名查找命令。

        Args:
            name (str):
                规范命令名或别名。

        Returns:
            CommandSpec | None:
                命令声明, 不存在时为 None。
        """

        if not isinstance(name, str):
            return None
        with self._lock:
            spec = self._specs.get(name)
            if spec is None:
                canonical = self._aliases.get(name)
                spec = self._specs.get(canonical) if canonical is not None else None
            return spec

    def __contains__(self, name: object) -> bool:
        """
        判断名称或别名是否已注册。

        Args:
            name (object):
                名称。

        Returns:
            bool:
                已注册时返回 True。
        """

        return isinstance(name, str) and self.get(name) is not None

    def dispatch(self, name: str, payload: Any, ctx: CommandContext) -> dict[str, Any]:
        """
        分发命令, 从不抛出 ``Exception``。

        顺序: 解析名称与别名 → 传输策略 (``remote`` / ``blocking`` / ``requires_token``) → 载荷校验 →
        调用处理函数 → 桌面结果大小检查 → envelope。``control`` 标签启用时输出包含耗时的跟踪。

        Args:
            name (str):
                命令名或别名。
            payload (Any):
                载荷, None 视为空对象。
            ctx (CommandContext):
                调用上下文, ``ctx.command`` 会被设为规范命令名。

        Returns:
            dict[str, Any]:
                成功或错误 envelope。
        """

        started = time.perf_counter()
        pending = len(ctx.after_send)
        envelope: dict[str, Any]
        try:
            envelope = self._dispatch(name, payload, ctx)
        except CommandError as exc:
            envelope = error_envelope(exc.code, exc.message, exc.details)
        except Exception as exc:
            envelope = error_envelope("request_failed", str(exc))
        if envelope.get("ok") is not True:
            # 失败的命令不执行其登记的响应后动作。
            del ctx.after_send[pending:]
        _trace_dispatch(ctx, name, envelope, time.perf_counter() - started)
        return envelope

    def _dispatch(self, name: str, payload: Any, ctx: CommandContext) -> dict[str, Any]:
        spec = self.get(name)
        if spec is None:
            return error_envelope("unknown_request", UNKNOWN_REQUEST_MESSAGE.format(name=name))
        ctx.command = spec.name
        if ctx.transport not in TRANSPORTS:
            raise CommandError("unsupported_transport", f"unknown transport {ctx.transport!r}")
        if ctx.transport != "inprocess" and not spec.remote:
            raise CommandError("forbidden", f"command {spec.name} is only available in-process")
        if ctx.transport == "desktop" and spec.blocking:
            raise CommandError("unsupported_transport", f"command {spec.name} may import modules or run patch code and is not available on the desktop transport")
        if ctx.transport == "legacy" and spec.requires_token and not (isinstance(ctx.token, str) and ctx.token.strip()):
            raise CommandError("forbidden", f"command {spec.name} requires a non-empty runtime token on the legacy transport")
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise CommandError("invalid_payload", "payload must be an object")
        validated = validate_payload(spec, payload)
        result = spec.handler(ctx, validated)
        if not isinstance(result, dict):
            raise TypeError(f"command {spec.name} handler returned {type(result).__name__}, expected an object")
        if ctx.transport == "desktop":
            size = len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            if size > MAX_DESKTOP_RESULT_BYTES:
                raise CommandError("request_failed", f"result_too_large: command {spec.name} result is {size} bytes, exceeding the desktop limit of {MAX_DESKTOP_RESULT_BYTES} bytes")
        return success_envelope(result)


def _validate_command_name(value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"command names must be non-empty strings, got {value!r}")
    if len(value) > MAX_COMMAND_NAME_CHARS:
        raise ValueError(f"command name {value[:32]!r}... exceeds {MAX_COMMAND_NAME_CHARS} characters")


def _trace_dispatch(ctx: CommandContext, name: Any, envelope: Mapping[str, Any], elapsed: float) -> None:
    # 热路径: 未启用跟踪时只读取一个属性。
    try:
        tracer = ctx.state.tracer
        if tracer is None or not tracer.active:
            return
        error = envelope.get("error") if envelope.get("ok") is not True else None
        fields: dict[str, Any] = {
            "transport": ctx.transport,
            "command": ctx.command or name,
            "ok": envelope.get("ok") is True,
            "elapsed_ms": round(elapsed * 1000, 3),
        }
        if isinstance(error, Mapping):
            fields["code"] = error.get("code")
        tracer.trace("control", f"dispatch {name}", fields)
    except Exception:
        return
