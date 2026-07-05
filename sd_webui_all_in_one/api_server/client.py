"""标准库 API 客户端。"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class ApiClientError(RuntimeError):
    """API 客户端错误。"""

    def __init__(self, code: str, message: str, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.payload = payload or {}


class ApiClient:
    """SD WebUI All In One API 客户端。"""

    def __init__(self, base_url: str = "http://127.0.0.1:8765", token: str = "", timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        """检查 API 服务健康状态。"""
        return self.request("GET", "/health")

    def methods(self) -> dict[str, Any]:
        """获取 API 方法目录。"""
        return self.request("GET", "/api/v1/methods")

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        """调用同步 API 方法。"""
        return self.request("POST", "/api/v1/call", {"method": method, "params": params or {}})

    def create_task(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """创建后台任务。"""
        return self.request("POST", "/api/v1/tasks", {"method": method, "params": params or {}})

    def list_tasks(self) -> dict[str, Any]:
        """列出后台任务。"""
        return self.request("GET", "/api/v1/tasks")

    def get_task(self, task_id: str) -> dict[str, Any]:
        """获取任务状态。"""
        return self.request("GET", f"/api/v1/tasks/{task_id}")

    def get_task_logs(self, task_id: str) -> dict[str, Any]:
        """获取任务日志。"""
        return self.request("GET", f"/api/v1/tasks/{task_id}/logs")

    def cancel_task(self, task_id: str) -> dict[str, Any]:
        """请求取消任务。"""
        return self.request("POST", f"/api/v1/tasks/{task_id}/cancel")

    def request(self, http_method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        """发送原始 API 请求并返回 result。"""
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(f"{self.base_url}{path}", data=body, headers=headers, method=http_method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return self._decode_response(response.read())
        except urllib.error.HTTPError as exc:
            try:
                self._decode_response(exc.read())
            except ApiClientError as api_exc:
                raise api_exc from exc
            raise

    def _decode_response(self, body: bytes) -> Any:
        data = json.loads(body.decode("utf-8"))
        if not isinstance(data, dict):
            raise ApiClientError("invalid_response", "API response must be a JSON object", {"response": data})
        if data.get("ok") is True:
            return data.get("result")
        error = data.get("error")
        if not isinstance(error, dict):
            error = {}
        raise ApiClientError(
            str(error.get("code", "request_failed")),
            str(error.get("message", "API request failed")),
            data,
        )
