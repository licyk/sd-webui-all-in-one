"""标准库 HTTP JSON API 服务。"""

from __future__ import annotations

import inspect
import json
import re
import secrets
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, get_type_hints
from urllib.parse import unquote, urlparse

from sd_webui_all_in_one.api_server.introspection import CallablePlan, compile_callable, to_json_value
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

# 真实 callable 会在注册时编译成统一的内部作业处理器；公开参数始终来自
# callable 自身签名，内部处理器只负责接入任务上下文和执行流水线。
ApiJobHandler = Callable[[dict[str, Any], "ApiTaskContext"], Any]
MAX_REQUEST_BODY_SIZE = 1024 * 1024
SUPPORTED_HTTP_METHODS = "GET,HEAD,POST,OPTIONS"
API_METHOD_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
API_TASK_STATUSES = ("pending", "running", "succeeded", "failed", "canceled")
# How long a submit request waits for a job to finish before returning a pollable
# handle instead. Keeps fast reads to a single round-trip without capping slow work.
INLINE_WAIT_DEFAULT_MS = 500
# Bounded worker pool and retained-task cap so high-frequency jobs neither churn
# threads nor accumulate unbounded task records.
TASK_POOL_MAX_WORKERS = 8
TASK_RETENTION_LIMIT = 256
API_ERROR_CODES = (
    "invalid_request",
    "invalid_json",
    "method_failed",
    "method_not_allowed",
    "method_not_found",
    "not_found",
    "request_too_large",
    "task_canceled",
    "task_failed",
    "task_method_not_found",
    "task_not_found",
    "unauthorized",
)


@dataclass(frozen=True, slots=True)
class ApiMethodSpec:
    """真实 callable 的 API 注册信息，不保存重复参数 schema。"""

    handler: Callable[..., Any]
    description: str = ""
    bound_arguments: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RegisteredMethod:
    """已完成反射编译、可直接发现和调用的方法。"""

    name: str
    plan: CallablePlan

    def metadata(self) -> dict[str, Any]:
        """导出真实 callable 的方法和参数元数据。

        Returns:
            dict[str, Any]: 方法元数据字典。
        """
        return {
            "name": self.name,
            "kind": "job",
            "description": self.plan.description,
            "target": self.plan.target_name,
            "params_schema": self.plan.params_schema,
            "parameters": [parameter.metadata() for parameter in self.plan.parameters],
        }

    def invoke(self, params: Mapping[str, Any], context: ApiTaskContext) -> Any:
        """使用通用调用计划直接执行真实 callable。

        Args:
            params (Mapping[str, Any]): 调用参数映射。
            context (ApiTaskContext): 当前 API 任务上下文。

        Returns:
            Any: 目标 callable 的返回结果，原始 Python 对象。
        """
        return to_json_value(self.plan.invoke(params, {"context": context}))


ApiMethodRegistry = Mapping[str, Callable[..., Any] | ApiMethodSpec]


def validate_api_method_name(name: str) -> None:
    """校验 API 方法名。

    Args:
        name (str): API 方法名。

    Raises:
        ValueError: 方法名不符合 API 命名规则。
    """
    if not API_METHOD_NAME_PATTERN.match(name):
        raise ValueError(f"Invalid API method name: {name}")


def _normalize_method_registry(methods: ApiMethodRegistry | None) -> tuple[dict[str, ApiJobHandler], dict[str, RegisteredMethod]]:
    handlers: dict[str, ApiJobHandler] = {}
    registered: dict[str, RegisteredMethod] = {}
    for key, value in (methods or {}).items():
        if isinstance(value, ApiMethodSpec):
            name = key
            spec = value
        else:
            name = key
            spec = ApiMethodSpec(handler=value)
        validate_api_method_name(name)
        injected: set[str] = set()
        context_parameter = inspect.signature(spec.handler).parameters.get("context")
        if context_parameter is not None and "context" not in spec.bound_arguments:
            try:
                context_annotation = get_type_hints(spec.handler).get("context", context_parameter.annotation)
            except (NameError, TypeError):
                context_annotation = context_parameter.annotation
            if context_annotation is ApiTaskContext:
                injected.add("context")
        plan = compile_callable(
            spec.handler,
            bound_arguments=spec.bound_arguments,
            injected_parameters=frozenset(injected),
            description=spec.description,
        )
        method = RegisteredMethod(name=name, plan=plan)
        registered[name] = method
        handlers[name] = method.invoke
    return handlers, registered


class ApiTaskCanceled(RuntimeError):
    """API 任务被取消。"""


class ApiTaskContext:
    """API 后台任务上下文。"""

    def __init__(self, task: ApiTask) -> None:
        self._task = task

    @property
    def task_id(self) -> str:
        """任务 ID。

        Returns:
            str: 当前任务 ID。
        """
        return self._task.task_id

    def set_progress(self, value: float | None = None, message: str = "") -> None:
        """设置任务进度。

        Args:
            value (float | int | None): 任务进度值。
            message (str): 进度说明。
        """
        self._task.set_progress(value, message)

    def log(self, message: str, level: str = "info") -> None:
        """记录任务日志。

        Args:
            message (str): 日志内容。
            level (str): 日志级别。
        """
        self._task.add_log(message, level=level)

    def is_canceled(self) -> bool:
        """任务是否已收到取消请求。

        Returns:
            bool: 任务收到取消请求时返回 True。
        """
        return self._task.is_canceled

    def check_canceled(self) -> None:
        """任务已取消时抛出异常。

        Raises:
            ApiTaskCanceled: 当前任务已收到取消请求。
        """
        if self.is_canceled():
            raise ApiTaskCanceled("Task was canceled")


class ApiTask:
    """后台 API 任务状态。"""

    def __init__(self, task_id: str, method: str, params: dict[str, Any], handler: ApiJobHandler) -> None:
        self.task_id = task_id
        self.method = method
        self.params = params
        self.handler = handler
        self.status = "pending"
        self.created_at = time.time()
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self.progress: float | int | None = None
        self.progress_message = ""
        self.result: Any = None
        self.error: dict[str, str] | None = None
        self.logs: list[dict[str, Any]] = []
        self._cancel_event = threading.Event()
        self._done_event = threading.Event()
        self._lock = threading.RLock()

    @property
    def is_canceled(self) -> bool:
        """任务是否已收到取消请求。

        Returns:
            bool: 已收到取消请求时返回 True。
        """
        return self._cancel_event.is_set()

    @property
    def is_terminal(self) -> bool:
        """任务是否已进入终态。

        Returns:
            bool: 任务成功、失败或取消时返回 True。
        """
        return self.status in {"succeeded", "failed", "canceled"}

    def wait_terminal(self, timeout: float | None = None) -> bool:
        """等待任务进入终态。

        Args:
            timeout (float | None): 最长等待秒数，None 表示无限等待。

        Returns:
            bool: 在超时前进入终态时返回 True。
        """
        return self._done_event.wait(timeout)

    def cancel(self) -> bool:
        """请求取消任务。

        Returns:
            bool: 成功发出取消请求时返回 True，任务已结束时返回 False。
        """
        with self._lock:
            if self.status in {"succeeded", "failed", "canceled"}:
                return False
            self._cancel_event.set()
            self.add_log("Cancel requested", level="warning")
            return True

    def set_progress(self, value: float | None = None, message: str = "") -> None:
        """设置任务进度。

        Args:
            value (float | int | None): 任务进度值。
            message (str): 进度说明。
        """
        with self._lock:
            self.progress = value
            self.progress_message = message

    def add_log(self, message: str, level: str = "info") -> None:
        """添加任务日志。

        Args:
            message (str): 日志内容。
            level (str): 日志级别。
        """
        with self._lock:
            self.logs.append({"time": time.time(), "level": level, "message": message})

    def snapshot(self, include_result: bool = True) -> dict[str, Any]:
        """导出任务状态快照。

        Args:
            include_result (bool): 是否包含任务结果。

        Returns:
            dict[str, Any]: 任务状态快照。
        """
        with self._lock:
            data: dict[str, Any] = {
                "id": self.task_id,
                "method": self.method,
                "status": self.status,
                "created_at": self.created_at,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "progress": self.progress,
                "progress_message": self.progress_message,
                "canceled": self.is_canceled,
                "error": self.error,
            }
            if include_result:
                data["result"] = self.result
            return data

    def logs_snapshot(self) -> list[dict[str, Any]]:
        """导出任务日志。

        Returns:
            list[dict[str, Any]]: 任务日志快照。
        """
        with self._lock:
            return list(self.logs)

    def _run(self) -> None:
        with self._lock:
            self.status = "running"
            self.started_at = time.time()
        context = ApiTaskContext(self)
        try:
            context.check_canceled()
            result = self.handler(self.params, context)
            with self._lock:
                if self.is_canceled:
                    self.status = "canceled"
                else:
                    self.status = "succeeded"
                    self.result = result
        except ApiTaskCanceled as exc:
            with self._lock:
                self.status = "canceled"
                self.error = {"code": "task_canceled", "message": str(exc)}
        except Exception as exc:
            logger.exception("API task failed: %s", self.method)
            with self._lock:
                self.status = "failed"
                self.error = {"code": "task_failed", "message": str(exc)}
        finally:
            with self._lock:
                self.finished_at = time.time()
            self._done_event.set()


class ApiTaskManager:
    """后台 API 任务管理器。

    使用有界线程池执行任务，并对已完成任务做有界保留，避免高频任务导致线程抖动或
    任务记录无限增长。
    """

    def __init__(self, max_workers: int = TASK_POOL_MAX_WORKERS, max_retained: int = TASK_RETENTION_LIMIT) -> None:
        self._tasks: dict[str, ApiTask] = {}
        self._order: deque[str] = deque()
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="api-job")
        self._max_retained = max_retained

    def create_task(self, method: str, params: dict[str, Any], handler: ApiJobHandler) -> ApiTask:
        """创建并调度后台任务。

        Args:
            method (str): 任务方法名。
            params (dict[str, Any]): 任务参数。
            handler (ApiJobHandler): 任务处理器。

        Returns:
            ApiTask: 已创建的后台任务。
        """
        task = ApiTask(uuid.uuid4().hex, method, params, handler)
        with self._lock:
            self._tasks[task.task_id] = task
            self._order.append(task.task_id)
            self._evict_locked()
        self._executor.submit(task._run)
        return task

    def get(self, task_id: str) -> ApiTask | None:
        """获取任务。

        Args:
            task_id (str): 任务 ID。

        Returns:
            ApiTask | None: 找到时返回任务，否则返回 None。
        """
        with self._lock:
            return self._tasks.get(task_id)

    def remove(self, task_id: str) -> None:
        """移除任务记录（用于已内联返回终态结果、客户端不会再轮询的任务）。

        Args:
            task_id (str): 任务 ID。
        """
        with self._lock:
            self._tasks.pop(task_id, None)

    def snapshots(self) -> list[dict[str, Any]]:
        """列出任务快照。

        Returns:
            list[dict[str, Any]]: 后台任务状态快照列表。
        """
        with self._lock:
            return [task.snapshot(include_result=False) for task in self._tasks.values()]

    def shutdown(self) -> None:
        """停止线程池，取消尚未开始的任务。"""
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _evict_locked(self) -> None:
        """在持有锁时按创建顺序淘汰最旧的终态任务，保持记录数量有界。"""
        if len(self._tasks) <= self._max_retained:
            return
        excess = len(self._tasks) - self._max_retained
        for task_id in list(self._order):
            if excess <= 0:
                break
            task = self._tasks.get(task_id)
            if task is not None and task.is_terminal:
                del self._tasks[task_id]
                excess -= 1
        self._order = deque(task_id for task_id in self._order if task_id in self._tasks)


class ApiServer(ThreadingHTTPServer):
    """SD WebUI All In One API 服务。"""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        methods: ApiMethodRegistry | None = None,
        token: str = "",
        max_request_body_size: int = MAX_REQUEST_BODY_SIZE,
        task_manager: ApiTaskManager | None = None,
    ) -> None:
        normalized_methods, method_specs = _normalize_method_registry(methods)
        super().__init__(server_address, ApiRequestHandler)
        self.token = token
        self.methods = normalized_methods
        self.method_specs = method_specs
        self.task_manager = task_manager or ApiTaskManager()
        self.max_request_body_size = max_request_body_size

    def method_catalog(self) -> dict[str, Any]:
        """导出方法目录和 API 规范信息。

        Returns:
            dict[str, Any]: 方法名、元数据、命名规则、任务状态和错误码列表。
        """
        metadata = {name: spec.metadata() for name, spec in self.method_specs.items()}
        return {
            "methods": sorted(self.methods),
            # There is one registry; `tasks` is retained (empty) for client
            # catalogs that union method/task lists.
            "tasks": [],
            "metadata": metadata,
            "method_name_pattern": API_METHOD_NAME_PATTERN.pattern,
            "task_statuses": list(API_TASK_STATUSES),
            "error_codes": list(API_ERROR_CODES),
        }

    def method_details(self, name: str) -> dict[str, Any] | None:
        """导出单个方法的元数据及结构化参数说明。

        Args:
            name (str): API 方法名。

        Returns:
            dict[str, Any] | None: 方法元数据，若方法不存在则返回 None。
        """
        spec = self.method_specs.get(name)
        if spec is None:
            return None
        return spec.metadata()

    def server_close(self) -> None:
        """Close the listener, stop the task pool, and bind any in-flight discovery."""
        from sd_webui_all_in_one.launch_arguments import cancel_launch_argument_discovery

        cancel_launch_argument_discovery()
        self.task_manager.shutdown()
        super().server_close()


class ApiRequestHandler(BaseHTTPRequestHandler):
    """API HTTP 请求处理器。"""

    server: ApiServer

    def do_GET(self) -> None:
        """处理 GET 请求。"""
        path = self._path
        if path == "/health":
            self._send_success({"status": "ok"})
            return

        if not self._authorize():
            return

        if path == "/api/v2/methods":
            self._send_success(self.server.method_catalog())
            return

        method_prefix = "/api/v2/methods/"
        if path.startswith(method_prefix):
            method = unquote(path.removeprefix(method_prefix))
            details = self.server.method_details(method)
            if details is None:
                self._send_error(HTTPStatus.NOT_FOUND, "method_not_found", f"Method not found: {method}")
                return
            self._send_success(details)
            return

        if path == "/api/v2/tasks":
            self._send_success({"tasks": self.server.task_manager.snapshots()})
            return

        task_id, suffix = self._parse_task_path(path)
        if task_id is not None:
            task = self.server.task_manager.get(task_id)
            if task is None:
                self._send_error(HTTPStatus.NOT_FOUND, "task_not_found", f"Task not found: {task_id}")
                return
            if suffix == "":
                self._send_success(task.snapshot())
                return
            if suffix == "/logs":
                self._send_success({"logs": task.logs_snapshot()})
                return

        self._send_error(HTTPStatus.NOT_FOUND, "not_found", "Endpoint not found")

    def do_HEAD(self) -> None:
        """处理 HEAD 请求。"""
        if self._path == "/health":
            self._send_success({"status": "ok"}, write_body=False)
            return

        self._send_error(HTTPStatus.NOT_FOUND, "not_found", "Endpoint not found", write_body=False)

    def do_OPTIONS(self) -> None:
        """处理 OPTIONS 请求。"""
        self.send_response(HTTPStatus.NO_CONTENT.value)
        self._send_common_headers(0)
        self.end_headers()

    def do_PUT(self) -> None:
        """处理未支持的 PUT 请求。"""
        self._send_method_not_allowed()

    def do_PATCH(self) -> None:
        """处理未支持的 PATCH 请求。"""
        self._send_method_not_allowed()

    def do_DELETE(self) -> None:
        """处理未支持的 DELETE 请求。"""
        self._send_method_not_allowed()

    def do_POST(self) -> None:
        """处理 POST 请求。"""
        path = self._path
        if path not in {"/api/v2/call", "/api/v2/tasks"} and not path.endswith("/cancel"):
            self._send_error(HTTPStatus.NOT_FOUND, "not_found", "Endpoint not found")
            return

        if not self._authorize():
            return

        if path == "/api/v2/call":
            self._handle_submit(INLINE_WAIT_DEFAULT_MS)
            return

        if path == "/api/v2/tasks":
            # Async submit: never wait inline, always return a pollable handle.
            self._handle_submit(0)
            return

        task_id, suffix = self._parse_task_path(path)
        if task_id is not None and suffix == "/cancel":
            self._handle_cancel_task(task_id)
            return

        self._send_error(HTTPStatus.NOT_FOUND, "not_found", "Endpoint not found")

    @property
    def _path(self) -> str:
        return urlparse(self.path).path

    def _handle_submit(self, default_wait_ms: float) -> None:
        """Submit a method as a job, optionally waiting for it inline.

        Every method runs on the task pool. If it reaches a terminal state within
        `wait_ms`, the response is the same single-round-trip shape as before:
        `{ok:true, result:<value>}` (200) on success, or an error envelope on
        failure/cancellation; the record is evicted since the client has the
        result. Otherwise the response is a pollable handle snapshot (202). A slow
        job's duration is thus decoupled from any request timeout.
        """
        data = self._read_json_body()
        if data is None:
            return

        method = data.get("method")
        params = data.get("params", {})
        wait_ms = data.get("wait_ms", default_wait_ms)
        if not isinstance(method, str) or not method:
            self._send_error(HTTPStatus.BAD_REQUEST, "invalid_request", "Field 'method' must be a non-empty string")
            return
        if not isinstance(params, dict):
            self._send_error(HTTPStatus.BAD_REQUEST, "invalid_request", "Field 'params' must be an object")
            return
        if isinstance(wait_ms, bool) or not isinstance(wait_ms, (int, float)) or wait_ms < 0:
            self._send_error(HTTPStatus.BAD_REQUEST, "invalid_request", "Field 'wait_ms' must be a non-negative number")
            return

        handler = self.server.methods.get(method)
        if handler is None:
            self._send_error(HTTPStatus.NOT_FOUND, "method_not_found", f"Method not found: {method}")
            return
        try:
            self.server.method_specs[method].plan.prepare(params)
        except ValueError as exc:
            self._send_error(HTTPStatus.BAD_REQUEST, "invalid_request", str(exc))
            return

        task = self.server.task_manager.create_task(method, params, handler)
        if wait_ms > 0 and task.wait_terminal(wait_ms / 1000.0):
            self.server.task_manager.remove(task.task_id)
            snapshot = task.snapshot()
            if snapshot["status"] == "succeeded":
                self._send_success(snapshot["result"])
                return
            error = snapshot["error"] or {"code": "task_failed", "message": f"API job {snapshot['status']}"}
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(error["code"]), str(error["message"]))
            return
        self._send_success(task.snapshot(include_result=False), status=HTTPStatus.ACCEPTED)

    def _handle_cancel_task(self, task_id: str) -> None:
        task = self.server.task_manager.get(task_id)
        if task is None:
            self._send_error(HTTPStatus.NOT_FOUND, "task_not_found", f"Task not found: {task_id}")
            return
        self._send_success({"canceled": task.cancel(), "task": task.snapshot(include_result=False)})

    def _parse_task_path(self, path: str) -> tuple[str | None, str]:
        prefix = "/api/v2/tasks/"
        if not path.startswith(prefix):
            return None, ""
        rest = path.removeprefix(prefix)
        if not rest:
            return None, ""
        task_id, sep, suffix = rest.partition("/")
        return task_id, f"/{suffix}" if sep else ""

    def _authorize(self) -> bool:
        token = self.server.token
        if not token:
            return True

        auth_header = self.headers.get("Authorization", "")
        expected = f"Bearer {token}"
        if secrets.compare_digest(auth_header, expected):
            return True

        self._send_error(HTTPStatus.UNAUTHORIZED, "unauthorized", "Invalid or missing bearer token")
        return False

    def _read_json_body(self) -> dict[str, Any] | None:
        content_length_text = self.headers.get("Content-Length", "0")
        try:
            content_length = int(content_length_text)
        except ValueError:
            self._send_error(HTTPStatus.BAD_REQUEST, "invalid_request", "Invalid Content-Length")
            return None

        if content_length > self.server.max_request_body_size:
            self._send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request_too_large", "Request body is too large")
            return None

        body = self.rfile.read(content_length)
        if not body:
            return {}

        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_error(HTTPStatus.BAD_REQUEST, "invalid_json", "Request body must be valid JSON")
            return None

        if not isinstance(data, dict):
            self._send_error(HTTPStatus.BAD_REQUEST, "invalid_request", "Request body must be a JSON object")
            return None

        return data

    def _send_success(self, result: Any, status: HTTPStatus = HTTPStatus.OK, write_body: bool = True) -> None:
        self._send_json(status, {"ok": True, "result": result}, write_body=write_body)

    def _send_error(self, status: HTTPStatus, code: str, message: str, write_body: bool = True) -> None:
        self._send_json(status, {"ok": False, "error": {"code": code, "message": message}}, write_body=write_body)

    def _send_method_not_allowed(self) -> None:
        self._send_error(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed", f"HTTP method is not allowed: {self.command}")

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any], write_body: bool = True) -> None:
        data = json.dumps(to_json_value(payload), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status.value)
        self._send_common_headers(len(data))
        self.end_headers()
        if write_body:
            self.wfile.write(data)

    def _send_common_headers(self, content_length: int) -> None:
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(content_length))
        self.send_header("Allow", SUPPORTED_HTTP_METHODS)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", SUPPORTED_HTTP_METHODS)
        self.send_header("Access-Control-Allow-Headers", "Authorization,Content-Type")

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        """输出 API access log。

        Args:
            code (int | str): HTTP 响应状态码。
            size (int | str): 响应体大小。
        """
        host, port = self.client_address[:2]
        logger.info('API %s:%s - "%s %s %s" %s', host, port, self.command, self.path, self.request_version, code)

    def log_message(self, format: str, *args: Any) -> None:
        """输出 API debug log。

        Args:
            format (str): 日志格式字符串。
            *args (Any): 格式化参数。
        """
        logger.debug("API %s - " + format, self.address_string(), *args)


def create_api_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    token: str = "",
    methods: ApiMethodRegistry | None = None,
    task_manager: ApiTaskManager | None = None,
    include_default_methods: bool = True,
) -> ApiServer:
    """创建 API 服务实例。

    Args:
        host (str): API 服务监听地址。
        port (int): API 服务监听端口。
        token (str): Bearer token，空字符串表示不启用鉴权。
        methods (ApiMethodRegistry | None): 额外方法注册表。
        task_manager (ApiTaskManager | None): 自定义任务管理器。
        include_default_methods (bool): 是否加载默认业务方法。

    Returns:
        ApiServer: 已创建但尚未启动的 API 服务实例。
    """
    if include_default_methods:
        from sd_webui_all_in_one.api_server.registry import get_default_methods

        merged_methods = dict(get_default_methods())
        merged_methods.update(methods or {})
    else:
        merged_methods = methods

    return ApiServer((host, port), methods=merged_methods, token=token, task_manager=task_manager)


def serve_api(
    host: str = "127.0.0.1",
    port: int = 8765,
    token: str = "",
    methods: ApiMethodRegistry | None = None,
    include_default_methods: bool = True,
) -> None:
    """启动阻塞式 API 服务。

    Args:
        host (str): API 服务监听地址。
        port (int): API 服务监听端口。
        token (str): Bearer token，空字符串表示不启用鉴权。
        methods (ApiMethodRegistry | None): 额外方法注册表。
        include_default_methods (bool): 是否加载默认业务方法。
    """
    server = create_api_server(host=host, port=port, token=token, methods=methods, include_default_methods=include_default_methods)
    address_info = server.server_address
    address = str(address_info[0])
    actual_port = int(address_info[1])
    logger.info("API 服务已启动: http://%s:%s", address, actual_port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("正在停止 API 服务")
    finally:
        server.server_close()
