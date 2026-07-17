"""Hotpatcher 管理 API 适配器。"""

from __future__ import annotations

import ipaddress
from pathlib import Path
from threading import RLock
from typing import Any

from sd_webui_all_in_one.base_manager.hotpatcher_manager import (
    DEFAULT_RUNTIME_HOST,
    DEFAULT_RUNTIME_PORT,
    HotpatcherRuntimeHost,
    apply_hotpatcher_config,
    build_hotpatcher_runtime_env,
    export_hotpatcher_default_config,
    get_hotpatcher_catalog,
    get_hotpatcher_default_config,
    load_hotpatcher_config,
    normalize_hotpatcher_config,
    save_hotpatcher_config,
)


class HotpatcherApiAdapter:
    """Hotpatcher 管理 API 适配器。"""

    def __init__(self) -> None:
        self._runtime_host: HotpatcherRuntimeHost | None = None
        self._runtime_config: dict[str, Any] | None = None
        self._lock = RLock()

    def default_config(self) -> dict[str, Any]:
        """获取默认配置。

        Returns:
            dict[str, Any]: Hotpatcher 默认配置。
        """
        return {"config": get_hotpatcher_default_config()}

    def catalog(self) -> dict[str, Any]:
        """获取功能目录。

        Returns:
            dict[str, Any]: Hotpatcher 功能目录。
        """
        return {"catalog": get_hotpatcher_catalog()}

    def load_config(self, path: Path | None = None, normalize: bool = True) -> dict[str, Any]:
        """读取配置文件。

        Args:
            path (Path | None): 配置文件路径。
            normalize (bool): 是否补齐默认值。

        Returns:
            dict[str, Any]: 配置对象。
        """
        return {"config": load_hotpatcher_config(path, normalize=normalize)}

    def normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """规范化配置对象。

        Args:
            config (dict[str, Any]): 原始配置对象。

        Returns:
            dict[str, Any]: 规范化后的配置对象。
        """
        return {"config": normalize_hotpatcher_config(config)}

    def save_config(self, path: Path | None, config: dict[str, Any]) -> dict[str, Any]:
        """保存配置文件。

        Args:
            path (Path | None): 配置文件路径。
            config (dict[str, Any]): 配置对象。

        Returns:
            dict[str, Any]: 保存结果。
        """
        save_hotpatcher_config(path, normalize_hotpatcher_config(config))
        return {"saved": True, "path": path.as_posix() if path is not None else None}

    def export_default_config(self, path: Path | None = None, overwrite: bool = False) -> dict[str, Any]:
        """导出默认配置文件。

        Args:
            path (Path | None): 输出路径。
            overwrite (bool): 是否覆盖已有文件。

        Returns:
            dict[str, Any]: 导出结果。
        """
        output = export_hotpatcher_default_config(path, overwrite=overwrite)
        return {"path": output.as_posix()}

    def apply_config(self, config_or_path: dict[str, Any] | Path | None = None) -> dict[str, Any]:
        """应用配置到当前进程。

        Args:
            config_or_path (dict[str, Any] | Path | None): 配置对象或配置文件路径。

        Returns:
            dict[str, Any]: 应用结果。
        """
        return {"result": apply_hotpatcher_config(config_or_path)}

    def runtime_env(self, host: str = DEFAULT_RUNTIME_HOST, port: int = DEFAULT_RUNTIME_PORT, token: str = "", config_source: str = "remote") -> dict[str, Any]:
        """构建 runtime host 环境变量。

        Args:
            host (str): runtime host 地址。
            port (int): runtime host 端口。
            token (str): 连接 token。
            config_source (str): 配置来源。

        Returns:
            dict[str, Any]: 环境变量映射。
        """
        return {"env": build_hotpatcher_runtime_env(host, port, token=token, config_source=config_source)}

    def runtime_status(self) -> dict[str, Any]:
        """获取 runtime host 状态。

        Returns:
            dict[str, Any]: runtime host 状态。
        """
        with self._lock:
            host = self._runtime_host
            if host is None:
                return {"running": False, "service_channel_available": False, "address": None, "message_count": 0, "log_count": 0, "browser_event_count": 0, "browser_diagnostic_count": 0, "browser_next_cursor": 0, "runtime_identity": None}
            return {
                "running": True,
                "service_channel_available": host.service_channel_available,
                "address": {"host": host.server_address[0], "port": host.server_address[1]},
                "message_count": len(host.messages),
                "log_count": len(host.log_entries),
                "browser_event_count": len(host.browser_events),
                "browser_diagnostic_count": len(host.browser_diagnostics),
                "browser_next_cursor": host.browser_next_cursor,
                "runtime_identity": host.runtime_identity,
            }

    def runtime_browser_events(self, since_cursor: int = 0, limit: int = 100) -> dict[str, Any]:
        """读取独立的强类型浏览器事件流。

        Args:
            since_cursor (int): 起始游标。
            limit (int): 最多返回的事件数量。

        Returns:
            dict[str, Any]: 浏览器事件流及下一游标。

        Raises:
            ValueError: 游标或数量范围无效时抛出。
        """

        if isinstance(since_cursor, bool) or not isinstance(since_cursor, int) or not 0 <= since_cursor <= 2**63 - 1:
            raise ValueError("since_cursor must be an integer between 0 and 2^63-1")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
            raise ValueError("limit must be an integer between 1 and 200")
        with self._lock:
            host = self._runtime_host
            if host is None:
                return {
                    "runtime_identity": None,
                    "events": [],
                    "start_cursor": since_cursor,
                    "next_cursor": since_cursor,
                    "truncated": False,
                }
            return host.read_browser_events(since_cursor=since_cursor, limit=limit)

    def runtime_logs(self, limit: int | None = 200, since_cursor: int = 0) -> dict[str, Any]:
        """获取 runtime host 日志。

        Args:
            limit (int | None): 最多返回的日志数量。
            since_cursor (int): 起始游标。

        Returns:
            dict[str, Any]: runtime host 日志列表。
        """
        with self._lock:
            host = self._runtime_host
            if host is None:
                return {"logs": [], "start_cursor": max(0, since_cursor), "next_cursor": max(0, since_cursor), "truncated": False}
            effective_limit = 1000 if limit is None else limit
            return host.read_logs(since_cursor=since_cursor, limit=effective_limit)

    def start_runtime(self, host: str = DEFAULT_RUNTIME_HOST, port: int = DEFAULT_RUNTIME_PORT, token: str = "", config: dict[str, Any] | None = None) -> dict[str, Any]:
        """启动 runtime host。

        Args:
            host (str): 监听地址。
            port (int): 监听端口。
            token (str): 连接 token。
            config (dict[str, Any] | None): 远端请求配置时返回的配置对象。

        Returns:
            dict[str, Any]: runtime host 状态。
        """
        with self._lock:
            if self._runtime_host is not None:
                return self.runtime_status()
            self._runtime_config = normalize_hotpatcher_config(config or get_hotpatcher_default_config())
            runtime = HotpatcherRuntimeHost(host=host, port=port, token=token, get_config=lambda: self._runtime_config or {})
            runtime.start()
            self._runtime_host = runtime
            return self.runtime_status()

    def ensure_runtime(self, host: str = DEFAULT_RUNTIME_HOST, port: int = 0, token: str = "", config: dict[str, Any] | None = None) -> dict[str, Any]:
        """启动或复用运行时主机并返回其专用启动环境。

        Args:
            host (str): 运行时主机监听地址。
            port (int): 运行时主机监听端口，零表示自动分配。
            token (str): 运行时连接令牌。
            config (dict[str, Any] | None): 提供给运行时的配置。

        Returns:
            dict[str, Any]: 运行时状态及专用环境变量。

        Raises:
            ValueError: 主机不是回环地址或端口无效时抛出。
        """

        try:
            address = ipaddress.ip_address(host)
        except ValueError as exc:
            raise ValueError(f"runtime host must be a loopback IP address: {host}") from exc
        if not address.is_loopback:
            raise ValueError("runtime host must be loopback")
        if isinstance(port, bool) or not 0 <= int(port) <= 65535:
            raise ValueError("runtime port must be between 0 and 65535")
        with self._lock:
            normalized = normalize_hotpatcher_config(config or get_hotpatcher_default_config())
            runtime = self._runtime_host
            reused = runtime is not None
            if runtime is None:
                runtime = HotpatcherRuntimeHost(
                    host=host,
                    port=port,
                    token=token,
                    get_config=lambda: self._runtime_config or {},
                )
                self._runtime_config = normalized
                runtime.start()
                self._runtime_host = runtime
            else:
                self._runtime_config = normalized
                if not runtime.token:
                    runtime.token = token
            actual_host, actual_port = runtime.server_address
            result = self.runtime_status()
            result.update(
                {
                    "reused": reused,
                    "env": build_hotpatcher_runtime_env(
                        actual_host,
                        actual_port,
                        token=runtime.token,
                        config_source="remote",
                    ),
                }
            )
            return result

    def stop_runtime(self) -> dict[str, Any]:
        """停止 runtime host。

        Returns:
            dict[str, Any]: 停止结果。
        """
        with self._lock:
            host = self._runtime_host
            self._runtime_host = None
            self._runtime_config = None
        if host is not None:
            host.stop()
        return {"stopped": True}

    def apply_remote_config(self, config: dict[str, Any], timeout: float = 10.0) -> dict[str, Any]:
        """应用配置到已连接的远端 runtime。

        Args:
            config (dict[str, Any]): 配置对象。
            timeout (float): 请求超时时间。

        Returns:
            dict[str, Any]: 远端应用结果。

        Raises:
            RuntimeError: runtime host 未启动。
        """
        with self._lock:
            host = self._runtime_host
        if host is None:
            raise RuntimeError("runtime host is not running")
        return {"result": host.apply_remote_config(normalize_hotpatcher_config(config), timeout=timeout)}


HOTPATCHER_API_ADAPTER = HotpatcherApiAdapter()
