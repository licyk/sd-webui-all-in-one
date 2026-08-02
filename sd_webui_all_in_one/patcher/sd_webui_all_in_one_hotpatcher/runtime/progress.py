"""运行时进度上报工具"""

from __future__ import annotations

from typing import Any

from .client import RuntimeClient


class ProgressManager:
    """
    进度事件管理器

    Attributes:
        client (RuntimeClient):
            发送进度事件的运行时客户端
    """

    def __init__(self, client: RuntimeClient):
        self.client = client

    def create(self, progress_id: int, *, name: str, maximum: float, indeterminate: bool) -> None:
        """
        创建进度项

        Args:
            progress_id (int):
                进度项 ID
            name (str):
                进度名称
            maximum (float):
                最大值
            indeterminate (bool):
                是否为不确定进度
        """

        self.client.event(
            "progress.create",
            {
                "id": progress_id,
                "name": name,
                "max": maximum,
                "indeterminate": indeterminate,
            },
        )

    def update(self, progress_id: int, **payload: Any) -> None:
        """
        更新进度项

        Args:
            progress_id (int):
                进度项 ID
            **payload (Any):
                需要更新的字段
        """

        payload["id"] = progress_id
        self.client.event("progress.update", payload)

    def remove(self, progress_id: int) -> None:
        """
        移除进度项

        Args:
            progress_id (int):
                进度项 ID
        """

        self.client.event("progress.remove", {"id": progress_id})


class Progress:
    """
    上下文管理式进度对象

    进入上下文时发送 ``progress.create``, 属性变更时发送 ``progress.update``,
    退出上下文时发送 ``progress.remove``。

    Attributes:
        manager (ProgressManager | None):
            全局进度管理器。未设置时进度对象只维护本地状态。
    """

    manager: ProgressManager | None = None

    def __init__(self, name: str, max_value: float | None = 100, *, indeterminate: bool | None = None):
        """
        初始化进度对象

        Args:
            name (str):
                进度名称
            max_value (float | None):
                最大值。为 None 时默认不确定进度。
            indeterminate (bool | None):
                是否强制使用不确定进度模式
        """

        self._name = name
        self._max = max_value if max_value is not None else 0
        self._indeterminate = max_value is None if indeterminate is None else indeterminate
        self._left: str | None = None
        self._right: str | None = None
        self._value = 0.0

    def __enter__(self) -> "Progress":
        if self.manager is not None:
            self.manager.create(
                id(self),
                name=self._name,
                maximum=self._max,
                indeterminate=self._indeterminate,
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.manager is not None:
            self.manager.remove(id(self))

    @property
    def name(self) -> str:
        """
        进度名称

        Returns:
            str:
                当前进度名称
        """

        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        self._update(name=value)

    @property
    def max(self) -> float:
        """
        进度最大值

        Returns:
            float:
                当前进度最大值
        """

        return self._max

    @max.setter
    def max(self, value: float) -> None:
        self._max = value
        self._update(max=value)

    @property
    def indeterminate(self) -> bool:
        """
        是否为不确定进度

        Returns:
            bool:
                当前是否为不确定进度
        """

        return self._indeterminate

    @indeterminate.setter
    def indeterminate(self, value: bool) -> None:
        self._indeterminate = value
        self._update(indeterminate=value)

    @property
    def left(self) -> str | None:
        """
        左侧显示文本

        Returns:
            str | None:
                当前左侧文本
        """

        return self._left

    @left.setter
    def left(self, value: str | None) -> None:
        self._left = value
        self._update(left=value)

    @property
    def right(self) -> str | None:
        """
        右侧显示文本

        Returns:
            str | None:
                当前右侧文本
        """

        return self._right

    @right.setter
    def right(self, value: str | None) -> None:
        self._right = value
        self._update(right=value)

    @property
    def value(self) -> float:
        """
        当前进度值

        Returns:
            float:
                当前进度值
        """

        return self._value

    @value.setter
    def value(self, value: float) -> None:
        self._value = value
        self._update(value=value)

    def _update(self, **payload: Any) -> None:
        if self.manager is not None:
            self.manager.update(id(self), **payload)
