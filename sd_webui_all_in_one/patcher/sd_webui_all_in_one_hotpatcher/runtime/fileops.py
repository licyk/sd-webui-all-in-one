"""宿主确认式文件操作工具"""

from __future__ import annotations

import uuid
from pathlib import Path

from .client import RuntimeClient
from .protocol import RuntimeRequestError


class UserCanceledException(Exception):
    """用户取消文件操作"""

    pass


class FileOperation:
    """
    宿主确认式文件操作上下文

    文件操作会先发送给宿主确认, 只有宿主响应成功后才认为操作可执行。

    Attributes:
        client (RuntimeClient):
            发送文件操作请求的运行时客户端
        operation_id (str):
            当前文件操作事务 ID
    """

    def __init__(self, client: RuntimeClient):
        self.client = client
        self.operation_id = uuid.uuid4().hex
        self._active = False

    def __enter__(self) -> "FileOperation":
        """
        开始文件操作事务

        Returns:
            FileOperation:
                当前文件操作对象
        """

        self.client.request("file.operation.begin", {"operation_id": self.operation_id})
        self._active = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        结束文件操作事务

        Args:
            exc_type (type[BaseException] | None):
                异常类型
            exc_val (BaseException | None):
                异常值
            exc_tb (Any | None):
                异常追踪信息
        """

        if self._active:
            self.client.request("file.operation.end", {"operation_id": self.operation_id})
            self._active = False

    def delete(self, path: str | Path) -> None:
        """
        请求删除文件或目录

        Args:
            path (str | Path):
                需要删除的路径

        Raises:
            UserCanceledException:
                宿主返回 cancelled
        """

        self._request_fileop(
            "file.delete",
            {
                "operation_id": self.operation_id,
                "path": str(path),
            },
        )

    def perform(self) -> None:
        """
        请求宿主执行已登记的文件操作

        Raises:
            UserCanceledException:
                宿主返回 cancelled
        """

        self._request_fileop("file.operation.perform", {"operation_id": self.operation_id})

    def _request_fileop(self, message_type: str, payload: dict[str, str]) -> None:
        try:
            self.client.request(message_type, payload)
        except RuntimeRequestError as exc:
            if exc.code == "cancelled":
                raise UserCanceledException(exc.message) from exc
            raise
