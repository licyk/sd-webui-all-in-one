"""标准库 HTTP JSON API 服务。"""

from __future__ import annotations

import json
import re
import secrets
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Literal
from urllib.parse import urlparse

from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

ApiMethod = Callable[[dict[str, Any]], Any]
ApiTaskHandler = Callable[[dict[str, Any], "ApiTaskContext"], Any]
ApiMethodKind = Literal["sync", "task"]
MAX_REQUEST_BODY_SIZE = 1024 * 1024
SUPPORTED_HTTP_METHODS = "GET,HEAD,POST,OPTIONS"
API_METHOD_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
API_TASK_STATUSES = ("pending", "running", "succeeded", "failed", "canceled")
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
DEFAULT_OBJECT_SCHEMA: dict[str, Any] = {"type": "object"}


@dataclass(frozen=True, slots=True)
class ApiMethodSpec:
    """API 方法元数据和处理器。"""

    name: str
    handler: Callable[..., Any]
    kind: ApiMethodKind
    description: str = ""
    params_schema: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_OBJECT_SCHEMA))
    result_schema: dict[str, Any] | None = None

    def metadata(self) -> dict[str, Any]:
        """导出给客户端消费的方法元数据。"""
        data: dict[str, Any] = {
            "name": self.name,
            "kind": self.kind,
            "description": self.description,
            "params_schema": self.params_schema,
        }
        if self.result_schema is not None:
            data["result_schema"] = self.result_schema
        return data


ApiMethodRegistry = Mapping[str, ApiMethod | ApiMethodSpec]
ApiTaskRegistry = Mapping[str, ApiTaskHandler | ApiMethodSpec]


def validate_api_method_name(name: str) -> None:
    """校验 API 方法名。"""
    if not API_METHOD_NAME_PATTERN.match(name):
        raise ValueError(f"Invalid API method name: {name}")


def _normalize_method_registry(methods: ApiMethodRegistry | None) -> tuple[dict[str, ApiMethod], dict[str, ApiMethodSpec]]:
    handlers: dict[str, ApiMethod] = {}
    specs: dict[str, ApiMethodSpec] = {}
    for key, value in (methods or {}).items():
        if isinstance(value, ApiMethodSpec):
            name = value.name or key
            if value.kind != "sync":
                raise ValueError(f"API method spec kind mismatch for {name}: {value.kind}")
            handler = value.handler
            spec = value
        else:
            name = key
            handler = value
            spec = ApiMethodSpec(name=name, handler=handler, kind="sync")
        validate_api_method_name(name)
        handlers[name] = handler  # type: ignore[assignment]
        specs[name] = spec
    return handlers, specs


def _normalize_task_registry(task_methods: ApiTaskRegistry | None) -> tuple[dict[str, ApiTaskHandler], dict[str, ApiMethodSpec]]:
    handlers: dict[str, ApiTaskHandler] = {}
    specs: dict[str, ApiMethodSpec] = {}
    for key, value in (task_methods or {}).items():
        if isinstance(value, ApiMethodSpec):
            name = value.name or key
            if value.kind != "task":
                raise ValueError(f"API task spec kind mismatch for {name}: {value.kind}")
            handler = value.handler
            spec = value
        else:
            name = key
            handler = value
            spec = ApiMethodSpec(name=name, handler=handler, kind="task")
        validate_api_method_name(name)
        handlers[name] = handler  # type: ignore[assignment]
        specs[name] = spec
    return handlers, specs


class ApiTaskCanceled(RuntimeError):
    """API 任务被取消。"""


class ApiTaskContext:
    """API 后台任务上下文。"""

    def __init__(self, task: "ApiTask") -> None:
        self._task = task

    @property
    def task_id(self) -> str:
        """任务 ID。"""
        return self._task.task_id

    def set_progress(self, value: float | int | None = None, message: str = "") -> None:
        """设置任务进度。"""
        self._task.set_progress(value, message)

    def log(self, message: str, level: str = "info") -> None:
        """记录任务日志。"""
        self._task.add_log(message, level=level)

    def is_canceled(self) -> bool:
        """任务是否已收到取消请求。"""
        return self._task.is_canceled

    def check_canceled(self) -> None:
        """任务已取消时抛出异常。"""
        if self.is_canceled():
            raise ApiTaskCanceled("Task was canceled")


class ApiTask:
    """后台 API 任务状态。"""

    def __init__(self, task_id: str, method: str, params: dict[str, Any], handler: ApiTaskHandler) -> None:
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
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None

    @property
    def is_canceled(self) -> bool:
        return self._cancel_event.is_set()

    def start(self) -> None:
        """启动任务线程。"""
        self._thread = threading.Thread(target=self._run, name=f"api-task-{self.task_id}", daemon=True)
        self._thread.start()

    def cancel(self) -> bool:
        """请求取消任务。"""
        with self._lock:
            if self.status in {"succeeded", "failed", "canceled"}:
                return False
            self._cancel_event.set()
            self.add_log("Cancel requested", level="warning")
            return True

    def set_progress(self, value: float | int | None = None, message: str = "") -> None:
        """设置任务进度。"""
        with self._lock:
            self.progress = value
            self.progress_message = message

    def add_log(self, message: str, level: str = "info") -> None:
        """添加任务日志。"""
        with self._lock:
            self.logs.append({"time": time.time(), "level": level, "message": message})

    def snapshot(self, include_result: bool = True) -> dict[str, Any]:
        """导出任务状态快照。"""
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
        """导出任务日志。"""
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


class ApiTaskManager:
    """后台 API 任务管理器。"""

    def __init__(self) -> None:
        self._tasks: dict[str, ApiTask] = {}
        self._lock = threading.RLock()

    def create_task(self, method: str, params: dict[str, Any], handler: ApiTaskHandler) -> ApiTask:
        """创建并启动后台任务。"""
        task = ApiTask(uuid.uuid4().hex, method, params, handler)
        with self._lock:
            self._tasks[task.task_id] = task
        task.start()
        return task

    def get(self, task_id: str) -> ApiTask | None:
        """获取任务。"""
        with self._lock:
            return self._tasks.get(task_id)

    def list(self) -> list[dict[str, Any]]:
        """列出任务快照。"""
        with self._lock:
            return [task.snapshot(include_result=False) for task in self._tasks.values()]


class ApiServer(ThreadingHTTPServer):
    """SD WebUI All In One API 服务。"""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        methods: ApiMethodRegistry | None = None,
        task_methods: ApiTaskRegistry | None = None,
        token: str = "",
        max_request_body_size: int = MAX_REQUEST_BODY_SIZE,
        task_manager: ApiTaskManager | None = None,
    ) -> None:
        super().__init__(server_address, ApiRequestHandler)
        self.token = token
        self.methods, self.method_specs = _normalize_method_registry(methods)
        self.task_methods, self.task_method_specs = _normalize_task_registry(task_methods)
        self.task_manager = task_manager or ApiTaskManager()
        self.max_request_body_size = max_request_body_size

    def method_catalog(self) -> dict[str, Any]:
        """导出方法目录和 API 规范信息。"""
        metadata = {name: spec.metadata() for name, spec in {**self.method_specs, **self.task_method_specs}.items()}
        return {
            "methods": sorted(self.methods),
            "tasks": sorted(self.task_methods),
            "metadata": metadata,
            "method_name_pattern": API_METHOD_NAME_PATTERN.pattern,
            "task_statuses": list(API_TASK_STATUSES),
            "error_codes": list(API_ERROR_CODES),
        }


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

        if path == "/api/v1/methods":
            self._send_success(self.server.method_catalog())
            return

        if path == "/api/v1/tasks":
            self._send_success({"tasks": self.server.task_manager.list()})
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
        if path not in {"/api/v1/call", "/api/v1/tasks"} and not path.endswith("/cancel"):
            self._send_error(HTTPStatus.NOT_FOUND, "not_found", "Endpoint not found")
            return

        if not self._authorize():
            return

        if path == "/api/v1/call":
            self._handle_call()
            return

        if path == "/api/v1/tasks":
            self._handle_create_task()
            return

        task_id, suffix = self._parse_task_path(path)
        if task_id is not None and suffix == "/cancel":
            self._handle_cancel_task(task_id)
            return

        self._send_error(HTTPStatus.NOT_FOUND, "not_found", "Endpoint not found")

    @property
    def _path(self) -> str:
        return urlparse(self.path).path

    def _handle_call(self) -> None:
        data = self._read_method_request()
        if data is None:
            return
        method, params = data

        handler = self.server.methods.get(method)
        if handler is None:
            self._send_error(HTTPStatus.NOT_FOUND, "method_not_found", f"Method not found: {method}")
            return

        try:
            result = handler(params)
        except Exception as exc:
            logger.exception("API method failed: %s", method)
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "method_failed", str(exc))
            return

        self._send_success(result)

    def _handle_create_task(self) -> None:
        data = self._read_method_request()
        if data is None:
            return
        method, params = data

        handler = self.server.task_methods.get(method)
        if handler is None:
            self._send_error(HTTPStatus.NOT_FOUND, "task_method_not_found", f"Task method not found: {method}")
            return

        task = self.server.task_manager.create_task(method, params, handler)
        self._send_success(task.snapshot(include_result=False), status=HTTPStatus.ACCEPTED)

    def _handle_cancel_task(self, task_id: str) -> None:
        task = self.server.task_manager.get(task_id)
        if task is None:
            self._send_error(HTTPStatus.NOT_FOUND, "task_not_found", f"Task not found: {task_id}")
            return
        self._send_success({"canceled": task.cancel(), "task": task.snapshot(include_result=False)})

    def _read_method_request(self) -> tuple[str, dict[str, Any]] | None:
        data = self._read_json_body()
        if data is None:
            return None

        method = data.get("method")
        params = data.get("params", {})
        if not isinstance(method, str) or not method:
            self._send_error(HTTPStatus.BAD_REQUEST, "invalid_request", "Field 'method' must be a non-empty string")
            return None
        if not isinstance(params, dict):
            self._send_error(HTTPStatus.BAD_REQUEST, "invalid_request", "Field 'params' must be an object")
            return None

        return method, params

    def _parse_task_path(self, path: str) -> tuple[str | None, str]:
        prefix = "/api/v1/tasks/"
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
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
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
        """输出 API access log。"""
        host, port = self.client_address[:2]
        logger.info('API %s:%s - "%s %s %s" %s', host, port, self.command, self.path, self.request_version, code)

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug("API %s - " + format, self.address_string(), *args)


def create_api_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    token: str = "",
    methods: ApiMethodRegistry | None = None,
    task_methods: ApiTaskRegistry | None = None,
    task_manager: ApiTaskManager | None = None,
    include_default_methods: bool = True,
) -> ApiServer:
    """创建 API 服务实例。"""
    if include_default_methods:
        from sd_webui_all_in_one.api_server.registry import get_default_methods, get_default_task_methods

        merged_methods = dict(get_default_methods())
        merged_methods.update(methods or {})
        merged_task_methods = dict(get_default_task_methods())
        merged_task_methods.update(task_methods or {})
    else:
        merged_methods = methods
        merged_task_methods = task_methods

    return ApiServer((host, port), methods=merged_methods, task_methods=merged_task_methods, token=token, task_manager=task_manager)


def serve_api(
    host: str = "127.0.0.1",
    port: int = 8765,
    token: str = "",
    methods: ApiMethodRegistry | None = None,
    task_methods: ApiTaskRegistry | None = None,
    include_default_methods: bool = True,
) -> None:
    """启动阻塞式 API 服务。"""
    server = create_api_server(host=host, port=port, token=token, methods=methods, task_methods=task_methods, include_default_methods=include_default_methods)
    address, actual_port = server.server_address
    logger.info("API 服务已启动: http://%s:%s", address, actual_port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("正在停止 API 服务")
    finally:
        server.server_close()
