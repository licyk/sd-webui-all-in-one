"""Hotpatcher runtime host control command wrappers."""

from __future__ import annotations

from typing import Any

CONNECTION_UPDATE_COMMAND = "hotpatch.connection.update"
"""补丁进程切换连接参数的控制命令"""


def _compact(payload: dict[str, Any]) -> dict[str, Any]:
    # 省略值为 None 的可选字段, 由补丁进程使用默认值。
    return {key: value for key, value in payload.items() if value is not None}


class RuntimeControlMixin:
    """
    ``hotpatch.*`` 控制命令的便捷方法, 全部经由 ``request_control`` 发送。

    对端为旧版补丁进程时, 每个方法都抛出 ``RemoteServiceError("unsupported", ...)``; 补丁进程返回的错误以其错误码
    (例如 ``invalid_payload``、``forbidden``、``not_found``、``busy``、``remote_load_disabled``) 抛出。
    """

    def request_control(self, message_type: str, payload: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
        """
        发送控制命令, 由 ``HotpatcherRuntimeHost`` 实现。

        Args:
            message_type (str):
                控制命令名。
            payload (dict[str, Any] | None):
                命令载荷。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                命令结果载荷。

        Raises:
            NotImplementedError:
                子类未实现时抛出。
        """

        raise NotImplementedError

    def get_status(self, *, timeout: float = 10.0) -> dict[str, Any]:
        """
        获取补丁进程的状态快照 (``hotpatch.status``)。

        Args:
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                状态快照。
        """

        return self.request_control("hotpatch.status", timeout=timeout)

    def list_patches(self, owner: str | None = None, limit: int | None = None, *, timeout: float = 10.0) -> dict[str, Any]:
        """
        列出补丁句柄 (``hotpatch.patches.list``)。

        Args:
            owner (str | None):
                只列出该所有者 (补丁集) 的补丁。
            limit (int | None):
                最多返回的条目数, None 时使用补丁进程的默认值。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                ``{patches, count, truncated}``。
        """

        return self.request_control("hotpatch.patches.list", _compact({"owner": owner, "limit": limit}), timeout=timeout)

    def unload_patch(self, patch_id: str, *, timeout: float = 10.0) -> dict[str, Any]:
        """
        卸载单个补丁句柄 (``hotpatch.patches.unload``)。

        Args:
            patch_id (str):
                补丁句柄 id。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                ``{id, status}``。
        """

        return self.request_control("hotpatch.patches.unload", {"id": patch_id}, timeout=timeout)

    def list_sets(self, limit: int | None = None, *, timeout: float = 10.0) -> dict[str, Any]:
        """
        列出补丁集 (``hotpatch.sets.list``)。

        Args:
            limit (int | None):
                最多返回的条目数, None 时使用补丁进程的默认值。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                ``{sets, count, truncated}``。
        """

        return self.request_control("hotpatch.sets.list", _compact({"limit": limit}), timeout=timeout)

    def load_patch(self, source: str, name: str | None = None, config: dict[str, Any] | None = None, *, timeout: float = 30.0) -> dict[str, Any]:
        """
        在补丁进程中加载补丁模块或文件 (``hotpatch.sets.load``)。

        远程加载默认关闭 (``control.allow_remote_load``), 且需要非空 token; 未开启时补丁进程返回
        ``remote_load_disabled``。

        Args:
            source (str):
                模块名或补丁文件路径 (补丁进程所在机器上的路径)。
            name (str | None):
                补丁集名称。
            config (dict[str, Any] | None):
                传给补丁模块的配置。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                加载报告。
        """

        return self.request_control("hotpatch.sets.load", _compact({"source": source, "name": name, "config": config}), timeout=timeout)

    def unload_patch_set(self, key: str, *, timeout: float = 10.0) -> dict[str, Any]:
        """
        卸载补丁集 (``hotpatch.sets.unload``)。功能所属的补丁集需要用 ``disable_feature`` 关闭。

        Args:
            key (str):
                补丁集 id 或名称。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                卸载报告。
        """

        return self.request_control("hotpatch.sets.unload", {"key": key}, timeout=timeout)

    def reload_patch_set(self, key: str, config: dict[str, Any] | None = None, *, timeout: float = 30.0) -> dict[str, Any]:
        """
        重新加载已加载的补丁集 (``hotpatch.sets.reload``), 失败时补丁进程会回滚到旧版本。

        Args:
            key (str):
                补丁集 id 或名称。
            config (dict[str, Any] | None):
                新配置, None 时沿用原配置。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                重新加载报告。
        """

        return self.request_control("hotpatch.sets.reload", _compact({"key": key, "config": config}), timeout=timeout)

    def list_features(self, *, timeout: float = 10.0) -> dict[str, Any]:
        """
        列出功能及其状态 (``hotpatch.features.list``)。

        Args:
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                功能报告。
        """

        return self.request_control("hotpatch.features.list", timeout=timeout)

    def enable_feature(self, key: str, config: dict[str, Any] | None = None, *, timeout: float = 30.0) -> dict[str, Any]:
        """
        启用功能 (``hotpatch.features.enable``)。

        Args:
            key (str):
                功能键, 例如 ``extensions.uv_pip``。
            config (dict[str, Any] | None):
                功能配置, None 时使用当前配置。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                功能报告。
        """

        return self.request_control("hotpatch.features.enable", _compact({"key": key, "config": config}), timeout=timeout)

    def disable_feature(self, key: str, *, timeout: float = 30.0) -> dict[str, Any]:
        """
        关闭功能并撤销其补丁 (``hotpatch.features.disable``)。

        Args:
            key (str):
                功能键。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                功能报告。
        """

        return self.request_control("hotpatch.features.disable", {"key": key}, timeout=timeout)

    def read_patch_events(self, since_cursor: int = 0, limit: int | None = None, *, timeout: float = 10.0) -> dict[str, Any]:
        """
        按游标读取补丁进程的控制事件日志 (``hotpatch.debug.events.read``)。

        Args:
            since_cursor (int):
                起始游标, 传入上一次结果的 ``next_cursor`` 继续读取。
            limit (int | None):
                最多返回的事件数, None 时使用补丁进程的默认值。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                ``{events, start_cursor, next_cursor, truncated, has_more}``。
        """

        return self.request_control("hotpatch.debug.events.read", _compact({"since_cursor": int(since_cursor), "limit": limit}), timeout=timeout)

    def get_trace(self, *, timeout: float = 10.0) -> dict[str, Any]:
        """
        获取补丁跟踪设置 (``hotpatch.debug.trace.get``)。

        Args:
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                ``{enabled, tags, file, available_tags}``。
        """

        return self.request_control("hotpatch.debug.trace.get", timeout=timeout)

    def set_trace(self, tags: str | list[str] | None, *, timeout: float = 10.0) -> dict[str, Any]:
        """
        设置补丁跟踪标签 (``hotpatch.debug.trace.set``)。远程调用不能修改跟踪输出文件。

        Args:
            tags (str | list[str] | None):
                逗号分隔的标签、标签列表或 ``all``; 空值关闭跟踪。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                ``{enabled, tags, file, available_tags}``。
        """

        return self.request_control("hotpatch.debug.trace.set", {"tags": tags}, timeout=timeout)

    def set_strict(self, enabled: bool, *, timeout: float = 10.0) -> dict[str, Any]:
        """
        设置严格模式 (``hotpatch.debug.strict.set``)。

        Args:
            enabled (bool):
                是否开启严格模式。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                ``{strict, previous}``。
        """

        return self.request_control("hotpatch.debug.strict.set", {"enabled": bool(enabled)}, timeout=timeout)

    def explain_module(self, module: str, *, timeout: float = 10.0) -> dict[str, Any]:
        """
        解释某个模块上登记的补丁计划与结果 (``hotpatch.inspect.explain``)。

        Args:
            module (str):
                模块名。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                模块补丁说明。
        """

        return self.request_control("hotpatch.inspect.explain", {"module": module}, timeout=timeout)

    def get_connection(self, *, timeout: float = 10.0) -> dict[str, Any]:
        """
        获取补丁进程侧的连接参数与状态 (``hotpatch.connection.get``), token 已脱敏。

        Args:
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                ``{mode, connected, settings, status, editable, manager}``。
        """

        return self.request_control("hotpatch.connection.get", timeout=timeout)

    def test_connection(self, changes: dict[str, Any], *, timeout: float = 10.0) -> dict[str, Any]:
        """
        让补丁进程试连新的连接参数 (``hotpatch.connection.test``), 不做切换。需要补丁进程使用非空 token。

        Args:
            changes (dict[str, Any]):
                要试连的连接参数, 例如 ``{"host": ..., "port": ..., "token": ...}``。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                试连报告。
        """

        return self.request_control("hotpatch.connection.test", dict(changes), timeout=timeout)

    def update_connection(self, changes: dict[str, Any], *, timeout: float = 10.0) -> dict[str, Any]:
        """
        让补丁进程切换连接参数 (``hotpatch.connection.update``)。需要补丁进程使用非空 token。

        这是底层命令: 目标监听与 token 必须已经可用。要同时修改本宿主的监听地址或 token, 请使用 ``rebind``。

        Args:
            changes (dict[str, Any]):
                要修改的连接参数。
            timeout (float):
                等待响应的超时时间。

        Returns:
            dict[str, Any]:
                通常为 ``{"status": "scheduled", ...}``, 切换在响应写出后进行。
        """

        return self.request_control(CONNECTION_UPDATE_COMMAND, dict(changes), timeout=timeout)
