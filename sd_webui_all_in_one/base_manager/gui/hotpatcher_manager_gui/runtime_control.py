"""Hotpatcher 管理器的 "运行时控制" 标签页 (D3, 最小范围)。

``RuntimeControlController`` 不依赖 Tk, 只调用 ``HotpatcherRuntimeHost`` 的控制接口并把结果整理成表格行和文本;
``RuntimeControlTab`` 负责控件, 所有网络调用都通过应用的 ``run_background`` 放到后台线程执行。
"""

from __future__ import annotations

import json
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable, Protocol

from sd_webui_all_in_one.base_manager.hotpatcher_manager import HotpatcherRuntimeHost, RemoteServiceError
from sd_webui_all_in_one.base_manager.gui.version_gui import EnhancedEntry

EVENT_PAGE_SIZE = 200
"""每次读取的控制事件数量"""

PATCH_COLUMNS = (("id", "ID", 110), ("kind", "类型", 80), ("target", "目标", 260), ("owner", "所属", 160), ("stage", "阶段", 80), ("status", "状态", 80))
SET_COLUMNS = (("id", "ID", 110), ("name", "名称", 220), ("kind", "来源", 80), ("status", "状态", 80), ("handles", "补丁数", 70))
FEATURE_COLUMNS = (("key", "键", 220), ("title", "名称", 200), ("applied", "已应用", 70), ("active", "生效", 70))


class _BackgroundRunner(Protocol):
    def run_background(
        self,
        message: str,
        func: Callable[[], Any],
        callback: Callable[[Any], object] | None = None,
        error_callback: Callable[[BaseException], object] | None = None,
    ) -> None: ...

    def set_status(self, message: str) -> None: ...


def redact_token(token: str) -> str:
    """
    生成用于显示的 token 文本。

    Args:
        token (str):
            原始 token。

    Returns:
        str:
            非空时为 ``***``, 否则为 ``(未设置)``。
    """

    return "***" if token else "(未设置)"


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "是" if value else "否"
    return str(value)


def format_patch_rows(result: dict[str, Any]) -> list[tuple[str, tuple[str, ...]]]:
    """
    把 ``hotpatch.patches.list`` 结果整理成表格行。

    Args:
        result (dict[str, Any]):
            ``{patches, count, truncated}``。

    Returns:
        list[tuple[str, tuple[str, ...]]]:
            ``(补丁 id, 列值)`` 列表。
    """

    rows = []
    for item in result.get("patches") or []:
        if isinstance(item, dict):
            rows.append((str(item.get("id")), tuple(_text(item.get(key)) for key, _title, _width in PATCH_COLUMNS)))
    return rows


def format_set_rows(result: dict[str, Any]) -> list[tuple[str, tuple[str, ...]]]:
    """
    把 ``hotpatch.sets.list`` 结果整理成表格行。

    Args:
        result (dict[str, Any]):
            ``{sets, count, truncated}``。

    Returns:
        list[tuple[str, tuple[str, ...]]]:
            ``(补丁集 id, 列值)`` 列表。
    """

    rows = []
    for item in result.get("sets") or []:
        if isinstance(item, dict):
            values = (_text(item.get("id")), _text(item.get("name")), _text(item.get("kind")), _text(item.get("status")), _text(item.get("handle_count")))
            rows.append((str(item.get("id")), values))
    return rows


def format_feature_rows(result: dict[str, Any]) -> list[tuple[str, tuple[str, ...]]]:
    """
    把 ``hotpatch.features.list`` 结果整理成表格行。

    Args:
        result (dict[str, Any]):
            ``{features: [...]}``。

    Returns:
        list[tuple[str, tuple[str, ...]]]:
            ``(功能键, 列值)`` 列表。
    """

    rows = []
    for item in result.get("features") or []:
        if isinstance(item, dict):
            rows.append((str(item.get("key")), tuple(_text(item.get(key)) for key, _title, _width in FEATURE_COLUMNS)))
    return rows


def format_event_line(event: dict[str, Any]) -> str:
    """
    把一条控制事件整理成单行文本。

    Args:
        event (dict[str, Any]):
            ``{cursor, timestamp, type, payload}``。

    Returns:
        str:
            可显示的事件行。
    """

    timestamp = event.get("timestamp")
    clock = time.strftime("%H:%M:%S", time.localtime(timestamp)) if isinstance(timestamp, (int, float)) else "--:--:--"
    payload = json.dumps(event.get("payload"), ensure_ascii=False, separators=(",", ":"), default=str)
    return f"[{event.get('cursor')}] {clock} {event.get('type')} {payload}"


def parse_rebind_target(host_text: str, port_text: str, token_text: str, *, current: tuple[str, int, str]) -> dict[str, Any]:
    """
    把连接面板的输入解析为 ``rebind`` 参数, 与当前值相同的字段省略。

    Args:
        host_text (str):
            新监听地址, 空白表示不变。
        port_text (str):
            新端口, 空白表示不变。
        token_text (str):
            新 token, 空白表示不变。
        current (tuple[str, int, str]):
            当前 ``(host, port, token)``。

    Returns:
        dict[str, Any]:
            ``host`` / ``port`` / ``token`` 中发生变化的字段。

    Raises:
        ValueError:
            端口不是 0-65535 的整数, 或没有任何字段变化时抛出。
    """

    changes: dict[str, Any] = {}
    host = host_text.strip()
    if host and host != current[0]:
        changes["host"] = host
    port_raw = port_text.strip()
    if port_raw:
        try:
            port = int(port_raw)
        except ValueError as exc:
            raise ValueError("端口必须是整数") from exc
        if not 0 <= port <= 65535:
            raise ValueError("端口必须在 0-65535 之间")
        if port != current[1]:
            changes["port"] = port
    if token_text and token_text != current[2]:
        changes["token"] = token_text
    if not changes:
        raise ValueError("监听地址、端口和 token 均未变化")
    return changes


class RuntimeControlController:
    """
    运行时控制标签页的逻辑部分, 不依赖 Tk, 所有方法都可能阻塞 (网络请求), 需要在后台线程调用。

    Attributes:
        get_host (Callable[[], HotpatcherRuntimeHost | None]):
            返回当前 runtime host 的函数, 未监听时返回 None。
    """

    def __init__(self, get_host: Callable[[], HotpatcherRuntimeHost | None]) -> None:
        """
        创建控制器。

        Args:
            get_host (Callable[[], HotpatcherRuntimeHost | None]):
                返回当前 runtime host 的函数。
        """

        self.get_host = get_host

    def _host(self) -> HotpatcherRuntimeHost:
        host = self.get_host()
        if host is None:
            raise RemoteServiceError("channel_unavailable", "runtime host 未监听")
        return host

    def describe(self) -> dict[str, Any]:
        """
        获取连接与能力概要。

        Returns:
            dict[str, Any]:
                ``state`` 为 ``stopped``、``not_connected``、``legacy``、``error`` 或 ``control``, ``text`` 为显示文本;
                ``control`` 时还包含 ``capabilities`` 与 ``status``。
        """

        host = self.get_host()
        if host is None:
            return {"state": "stopped", "text": "runtime host 未监听"}
        if not host.service_channel_available:
            return {"state": "not_connected", "text": "补丁进程未连接 (没有 services 控制通道)"}
        try:
            capabilities = host.get_capabilities()
            status = host.get_status()
        except RemoteServiceError as exc:
            if exc.code == "unsupported":
                return {"state": "legacy", "text": "旧版补丁进程: 不支持运行时控制, 只能使用远程应用配置"}
            return {"state": "error", "text": f"获取能力失败: {exc}"}
        raw_version = status.get("version")
        version: dict[str, Any] = raw_version if isinstance(raw_version, dict) else {}
        text = (
            f"控制协议 v{capabilities.get('control_version')}, 传输 {capabilities.get('transport')}, "
            f"命令 {len(capabilities.get('commands') or [])} 个, 补丁进程 PID {status.get('pid')}, "
            f"hotpatcher {version.get('package', '?')} / Python {version.get('python', '?')}"
        )
        return {"state": "control", "text": text, "capabilities": capabilities, "status": status}

    def load_lists(self) -> dict[str, Any]:
        """
        读取补丁、补丁集与功能列表。

        Returns:
            dict[str, Any]:
                ``patches``、``sets``、``features`` 三组表格行, 以及 ``truncated`` 标记。
        """

        host = self._host()
        patches = host.list_patches()
        sets = host.list_sets()
        features = host.list_features()
        return {
            "patches": format_patch_rows(patches),
            "sets": format_set_rows(sets),
            "features": format_feature_rows(features),
            "truncated": bool(patches.get("truncated") or sets.get("truncated")),
        }

    def unload_patch(self, patch_id: str) -> dict[str, Any]:
        """
        卸载补丁句柄。

        Args:
            patch_id (str):
                补丁 id。

        Returns:
            dict[str, Any]:
                卸载结果。
        """

        return self._host().unload_patch(patch_id)

    def unload_set(self, key: str) -> dict[str, Any]:
        """
        卸载补丁集。

        Args:
            key (str):
                补丁集 id。

        Returns:
            dict[str, Any]:
                卸载报告。
        """

        return self._host().unload_patch_set(key)

    def set_feature(self, key: str, enabled: bool) -> dict[str, Any]:
        """
        启用或关闭功能。

        Args:
            key (str):
                功能键。
            enabled (bool):
                是否启用。

        Returns:
            dict[str, Any]:
                功能报告。
        """

        host = self._host()
        return host.enable_feature(key) if enabled else host.disable_feature(key)

    def read_events(self, since_cursor: int) -> dict[str, Any]:
        """
        按游标读取一页控制事件。

        Args:
            since_cursor (int):
                起始游标。

        Returns:
            dict[str, Any]:
                ``lines``、``next_cursor``、``has_more`` 与 ``truncated`` (起始游标之前的事件已被丢弃)。
        """

        result = self._host().read_patch_events(since_cursor, EVENT_PAGE_SIZE)
        events = [item for item in result.get("events") or [] if isinstance(item, dict)]
        return {
            "lines": [format_event_line(item) for item in events],
            "next_cursor": int(result.get("next_cursor", since_cursor)),
            "has_more": bool(result.get("has_more")),
            "truncated": bool(result.get("truncated")),
        }

    def get_debug(self) -> dict[str, Any]:
        """
        读取跟踪与严格模式设置。

        Returns:
            dict[str, Any]:
                ``trace`` (``{enabled, tags, file, available_tags}``) 与 ``strict``。
        """

        host = self._host()
        status = host.get_status()
        raw_debug = status.get("debug")
        debug: dict[str, Any] = raw_debug if isinstance(raw_debug, dict) else {}
        return {"trace": host.get_trace(), "strict": bool(debug.get("strict"))}

    def set_trace(self, tags_text: str) -> dict[str, Any]:
        """
        设置跟踪标签。

        Args:
            tags_text (str):
                逗号分隔的标签或 ``all``, 空白表示关闭跟踪。

        Returns:
            dict[str, Any]:
                新的跟踪设置。
        """

        tags = tags_text.strip()
        return self._host().set_trace(tags or None)

    def set_strict(self, enabled: bool) -> dict[str, Any]:
        """
        设置严格模式。

        Args:
            enabled (bool):
                是否开启。

        Returns:
            dict[str, Any]:
                ``{strict, previous}``。
        """

        return self._host().set_strict(enabled)

    def connection_view(self) -> dict[str, Any]:
        """
        获取当前监听参数, 不做网络请求。

        Returns:
            dict[str, Any]:
                ``host``、``port`` 与脱敏后的 ``token``; 未监听时为 None。
        """

        host = self.get_host()
        if host is None:
            return {"host": None, "port": None, "token": None}
        address = host.server_address
        return {"host": address[0], "port": address[1], "token": redact_token(host.token)}

    def test_connection(self) -> dict[str, Any]:
        """
        让补丁进程以当前参数试连本宿主 (``hotpatch.connection.test``), 并读取补丁进程侧的连接状态。

        Returns:
            dict[str, Any]:
                ``test`` 为试连报告, ``connection`` 为 ``hotpatch.connection.get`` 结果 (token 已脱敏)。
        """

        host = self._host()
        return {"test": host.test_connection({}), "connection": host.get_connection()}

    def apply_rebind(self, changes: dict[str, Any]) -> dict[str, Any]:
        """
        切换本宿主的监听地址 / 端口 / token, 并让已连接的补丁进程跟随切换。

        Args:
            changes (dict[str, Any]):
                ``parse_rebind_target`` 的结果。

        Returns:
            dict[str, Any]:
                ``HotpatcherRuntimeHost.rebind`` 的报告。
        """

        return self._host().rebind(**changes)


def _make_tree(parent: tk.Misc, columns: tuple[tuple[str, str, int], ...]) -> ttk.Treeview:
    frame = ttk.Frame(parent)
    frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
    tree = ttk.Treeview(frame, columns=[key for key, _title, _width in columns], show="headings", selectmode="browse")
    for key, title, width in columns:
        tree.heading(key, text=title)
        tree.column(key, width=width, stretch=True)
    scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    return tree


def _fill_tree(tree: ttk.Treeview, rows: list[tuple[str, tuple[str, ...]]]) -> None:
    tree.delete(*tree.get_children())
    for index, (item_id, values) in enumerate(rows):
        tree.insert("", tk.END, iid=f"{index}:{item_id}", values=values)


def _selected_key(tree: ttk.Treeview) -> str | None:
    selection = tree.selection()
    if not selection:
        return None
    return str(selection[0]).split(":", 1)[1]


class RuntimeControlTab:
    """
    运行时控制标签页控件。

    Attributes:
        controller (RuntimeControlController):
            标签页逻辑。
    """

    def __init__(self, app: _BackgroundRunner, parent: ttk.Frame, controller: RuntimeControlController) -> None:
        """
        创建标签页控件。

        Args:
            app (_BackgroundRunner):
                提供 ``run_background`` 与 ``set_status`` 的应用对象。
            parent (ttk.Frame):
                标签页容器。
            controller (RuntimeControlController):
                标签页逻辑。
        """

        self.app = app
        self.controller = controller
        self.event_cursor = 0
        self.summary_var = tk.StringVar(value="runtime host 未监听")
        self.trace_var = tk.StringVar(value="")
        self.trace_info_var = tk.StringVar(value="")
        self.strict_var = tk.BooleanVar(value=False)
        self.connection_var = tk.StringVar(value="")
        self.new_host_var = tk.StringVar(value="")
        self.new_port_var = tk.StringVar(value="")
        self.new_token_var = tk.StringVar(value="")
        self.on_rebind: Callable[[dict[str, Any], dict[str, Any]], None] | None = None

        header = ttk.Frame(parent)
        header.pack(fill=tk.X, padx=10, pady=8)
        ttk.Button(header, text="刷新", command=self.refresh).pack(side=tk.RIGHT)
        ttk.Label(header, textvariable=self.summary_var, wraplength=900, justify=tk.LEFT).pack(side=tk.LEFT, fill=tk.X, expand=True)

        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        patches_tab, sets_tab, features_tab, events_tab, debug_tab, connection_tab = (ttk.Frame(notebook) for _ in range(6))
        for frame, title in (
            (patches_tab, "补丁"),
            (sets_tab, "补丁集"),
            (features_tab, "功能"),
            (events_tab, "事件"),
            (debug_tab, "调试"),
            (connection_tab, "连接"),
        ):
            notebook.add(frame, text=title)

        self.patch_tree = self._list_tab(patches_tab, PATCH_COLUMNS, (("卸载所选", self.unload_selected_patch),))
        self.set_tree = self._list_tab(sets_tab, SET_COLUMNS, (("卸载所选", self.unload_selected_set),))
        self.feature_tree = self._list_tab(
            features_tab,
            FEATURE_COLUMNS,
            (("启用所选", lambda: self.toggle_selected_feature(True)), ("关闭所选", lambda: self.toggle_selected_feature(False))),
        )

        events_toolbar = ttk.Frame(events_tab)
        events_toolbar.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(events_toolbar, text="读取新事件", command=self.read_events).pack(side=tk.LEFT)
        ttk.Button(events_toolbar, text="从头读取", command=lambda: self.read_events(reset=True)).pack(side=tk.LEFT, padx=(8, 0))
        self.events_text = tk.Text(events_tab, wrap=tk.NONE, height=12, state=tk.DISABLED)
        self.events_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        debug_panel = ttk.Frame(debug_tab)
        debug_panel.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(debug_panel, text="跟踪标签:").grid(row=0, column=0, sticky=tk.W, padx=(0, 8), pady=4)
        EnhancedEntry(debug_panel, textvariable=self.trace_var).grid(row=0, column=1, sticky=tk.EW, pady=4)
        ttk.Button(debug_panel, text="应用", command=self.apply_trace).grid(row=0, column=2, padx=(8, 0), pady=4)
        ttk.Label(debug_panel, textvariable=self.trace_info_var, style="Help.TLabel").grid(row=1, column=1, columnspan=2, sticky=tk.W)
        ttk.Checkbutton(debug_panel, text="严格模式 (补丁失败时抛出异常)", variable=self.strict_var, command=self.apply_strict).grid(row=2, column=1, sticky=tk.W, pady=(8, 0))
        debug_panel.columnconfigure(1, weight=1)

        connection_panel = ttk.Frame(connection_tab)
        connection_panel.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(connection_panel, text="当前监听:").grid(row=0, column=0, sticky=tk.W, padx=(0, 8), pady=4)
        ttk.Label(connection_panel, textvariable=self.connection_var).grid(row=0, column=1, sticky=tk.W, pady=4)
        for row, (label, variable) in enumerate((("新地址:", self.new_host_var), ("新端口:", self.new_port_var), ("新 Token:", self.new_token_var)), start=1):
            ttk.Label(connection_panel, text=label).grid(row=row, column=0, sticky=tk.W, padx=(0, 8), pady=4)
            EnhancedEntry(connection_panel, textvariable=variable).grid(row=row, column=1, sticky=tk.EW, pady=4)
        ttk.Label(connection_panel, text="留空表示不变; 端口 0 表示由系统分配。", style="Help.TLabel").grid(row=4, column=1, sticky=tk.W)
        buttons = ttk.Frame(connection_panel)
        buttons.grid(row=5, column=1, sticky=tk.W, pady=(8, 0))
        ttk.Button(buttons, text="测试", command=self.test_connection).pack(side=tk.LEFT)
        ttk.Button(buttons, text="应用", command=self.apply_rebind).pack(side=tk.LEFT, padx=(8, 0))
        connection_panel.columnconfigure(1, weight=1)
        self.update_connection_view()

    def _list_tab(self, parent: ttk.Frame, columns: tuple[tuple[str, str, int], ...], actions: tuple[tuple[str, Callable[[], None]], ...]) -> ttk.Treeview:
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(toolbar, text="刷新", command=self.refresh_lists).pack(side=tk.LEFT)
        for title, command in actions:
            ttk.Button(toolbar, text=title, command=command).pack(side=tk.LEFT, padx=(8, 0))
        return _make_tree(parent, columns)

    def _error(self, title: str) -> Callable[[BaseException], None]:
        def show(error: BaseException) -> None:
            messagebox.showerror(title, str(error))

        return show

    def refresh(self) -> None:
        """刷新概要、列表与调试设置。"""
        self.update_connection_view()
        self.app.run_background("读取运行时控制状态中...", self.controller.describe, self._after_describe, self._error("读取失败"))

    def _after_describe(self, summary: dict[str, Any]) -> None:
        self.summary_var.set(summary["text"])
        if summary["state"] == "control":
            self.refresh_lists()
            self.app.run_background("读取调试设置中...", self.controller.get_debug, self._after_debug, self._error("读取失败"))

    def refresh_lists(self) -> None:
        """刷新补丁、补丁集与功能列表。"""
        self.app.run_background("读取补丁列表中...", self.controller.load_lists, self._after_lists, self._error("读取失败"))

    def _after_lists(self, lists: dict[str, Any]) -> None:
        _fill_tree(self.patch_tree, lists["patches"])
        _fill_tree(self.set_tree, lists["sets"])
        _fill_tree(self.feature_tree, lists["features"])
        self.app.set_status("补丁列表已刷新" + (" (结果已截断)" if lists["truncated"] else ""))

    def _after_debug(self, debug: dict[str, Any]) -> None:
        trace = debug["trace"]
        self.trace_var.set(",".join(trace.get("tags") or []))
        self.trace_info_var.set(f"可用标签: {', '.join(trace.get('available_tags') or [])}")
        self.strict_var.set(debug["strict"])

    def unload_selected_patch(self) -> None:
        """卸载所选补丁。"""
        key = _selected_key(self.patch_tree)
        if key is not None:
            self.app.run_background("卸载补丁中...", lambda: self.controller.unload_patch(key), lambda _result: self.refresh_lists(), self._error("卸载失败"))

    def unload_selected_set(self) -> None:
        """卸载所选补丁集。"""
        key = _selected_key(self.set_tree)
        if key is not None:
            self.app.run_background("卸载补丁集中...", lambda: self.controller.unload_set(key), lambda _result: self.refresh_lists(), self._error("卸载失败"))

    def toggle_selected_feature(self, enabled: bool) -> None:
        """启用或关闭所选功能。

        Args:
            enabled (bool):
                是否启用。
        """
        key = _selected_key(self.feature_tree)
        if key is not None:
            self.app.run_background("切换功能中...", lambda: self.controller.set_feature(key, enabled), lambda _result: self.refresh_lists(), self._error("切换失败"))

    def read_events(self, reset: bool = False) -> None:
        """按游标读取控制事件。

        Args:
            reset (bool):
                是否从头读取并清空显示。
        """
        if reset:
            self.event_cursor = 0
            self._set_events_text(None)
        cursor = self.event_cursor
        self.app.run_background("读取事件中...", lambda: self.controller.read_events(cursor), self._after_events, self._error("读取失败"))

    def _after_events(self, page: dict[str, Any]) -> None:
        self.event_cursor = page["next_cursor"]
        lines = list(page["lines"])
        if page["truncated"]:
            lines.insert(0, "[...] 部分较早的事件已被丢弃")
        if lines:
            self._set_events_text(lines)
        self.app.set_status(f"已读取 {len(page['lines'])} 条事件" + (", 还有更多" if page["has_more"] else ""))

    def _set_events_text(self, lines: list[str] | None) -> None:
        self.events_text.configure(state=tk.NORMAL)
        if lines is None:
            self.events_text.delete("1.0", tk.END)
        else:
            self.events_text.insert(tk.END, "\n".join(lines) + "\n")
            self.events_text.see(tk.END)
        self.events_text.configure(state=tk.DISABLED)

    def apply_trace(self) -> None:
        """应用跟踪标签。"""
        tags = self.trace_var.get()
        self.app.run_background("设置跟踪中...", lambda: self.controller.set_trace(tags), lambda trace: self._after_debug({"trace": trace, "strict": self.strict_var.get()}), self._error("设置失败"))

    def apply_strict(self) -> None:
        """应用严格模式开关。"""
        enabled = self.strict_var.get()
        self.app.run_background("设置严格模式中...", lambda: self.controller.set_strict(enabled), lambda result: self.strict_var.set(bool(result.get("strict"))), self._error("设置失败"))

    def update_connection_view(self) -> None:
        """刷新当前监听参数显示 (不做网络请求)。"""
        view = self.controller.connection_view()
        if view["host"] is None:
            self.connection_var.set("未监听")
        else:
            self.connection_var.set(f"{view['host']}:{view['port']}  token: {view['token']}")

    def test_connection(self) -> None:
        """让补丁进程以当前参数试连。"""
        self.app.run_background(
            "测试连接中...",
            self.controller.test_connection,
            lambda result: messagebox.showinfo("连接测试", json.dumps(result, ensure_ascii=False, indent=2)),
            self._error("连接测试失败"),
        )

    def apply_rebind(self) -> None:
        """切换监听参数, 已连接的补丁进程会跟随切换。"""
        host = self.controller.get_host()
        if host is None:
            messagebox.showwarning("未监听", "runtime host 未监听")
            return
        address = host.server_address
        try:
            changes = parse_rebind_target(self.new_host_var.get(), self.new_port_var.get(), self.new_token_var.get(), current=(address[0], address[1], host.token))
        except ValueError as exc:
            messagebox.showerror("参数无效", str(exc))
            return
        self.app.run_background("切换监听中...", lambda: self.controller.apply_rebind(changes), lambda report: self._after_rebind(changes, report), self._error("切换失败"))

    def _after_rebind(self, changes: dict[str, Any], report: dict[str, Any]) -> None:
        self.update_connection_view()
        if self.on_rebind is not None:
            self.on_rebind(changes, report)
        status = report.get("status")
        detail = report.get("error") or report.get("message") or report.get("reason") or ""
        text = f"监听切换结果: {status}" + (f"\n{json.dumps(detail, ensure_ascii=False)}" if detail else "")
        if status == "switched":
            self.new_host_var.set("")
            self.new_port_var.set("")
            self.new_token_var.set("")
            messagebox.showinfo("监听切换", text)
        else:
            messagebox.showwarning("监听切换", text)
