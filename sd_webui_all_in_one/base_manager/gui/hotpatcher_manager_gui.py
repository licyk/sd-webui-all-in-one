"""Hotpatcher 配置管理 GUI"""

# pylint: disable=too-many-instance-attributes,too-many-public-methods,too-many-lines

from __future__ import annotations

import json
import queue
import tkinter as tk
from pathlib import Path
from tkinter import (
    filedialog,
    messagebox,
    ttk,
)
from typing import Any

from sd_webui_all_in_one.base_manager.hotpatcher_manager import (
    DEFAULT_HOTPATCHER_CONFIG_PATH,
    DEFAULT_RUNTIME_HOST,
    DEFAULT_RUNTIME_PORT,
    HotpatcherRuntimeHost,
    RuntimeLogEntry,
    apply_hotpatcher_config,
    build_hotpatcher_runtime_env,
    export_hotpatcher_default_config,
    get_hotpatcher_catalog,
    get_hotpatcher_default_config,
    load_hotpatcher_config,
    normalize_hotpatcher_config,
    save_hotpatcher_config,
)
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    BackgroundTaskMixin,
    apply_gui_theme,
    apply_window_icon,
    configure_gui_fonts,
)


class HotpatcherManagerApp(tk.Tk, BackgroundTaskMixin):
    """Hotpatcher 配置管理窗口"""

    def __init__(
        self,
        config_path: str | Path | None = DEFAULT_HOTPATCHER_CONFIG_PATH,
        host: str = DEFAULT_RUNTIME_HOST,
        port: int = DEFAULT_RUNTIME_PORT,
        token: str = "",
    ) -> None:
        tk.Tk.__init__(self)
        BackgroundTaskMixin.__init__(self)

        self.config_path: Path | None = Path(config_path).expanduser() if config_path else DEFAULT_HOTPATCHER_CONFIG_PATH
        self.config_data: dict[str, Any] = {}
        self.runtime_host: HotpatcherRuntimeHost | None = None
        self._runtime_log_queue: queue.Queue[RuntimeLogEntry] = queue.Queue()
        self._json_dirty = False
        self._updating_form = False
        self._updating_json = False
        self._form_update_job: str | None = None
        self._form_mouse_over = False
        self._form_canvas_window: int | None = None
        self.catalog_data = get_hotpatcher_catalog()
        self._schema_field_vars: dict[tuple[str, str], tuple[tk.Variable, str, Any, dict[str, Any]]] = {}

        self.host_var = tk.StringVar(value=host)
        self.port_var = tk.StringVar(value=str(port))
        self.token_var = tk.StringVar(value=token)
        self.connection_status_var = tk.StringVar(value="未监听")
        self.config_path_var = tk.StringVar(value=self.config_path.as_posix() if self.config_path else "")
        self.status_var = tk.StringVar(value="就绪")
        self.busy_var = tk.StringVar(value="")
        self.log_autoscroll_var = tk.BooleanVar(value=True)
        self.log_level_filter_var = tk.StringVar(value="全部")
        self.log_source_filter_var = tk.StringVar(value="全部")

        self.title("Hotpatcher 配置管理器")
        self.geometry("1180x760")
        self.minsize(960, 620)
        apply_window_icon(self)
        self._create_styles()
        self._create_widgets()
        self._install_task_poller(self)
        self.after(100, self._poll_runtime_logs)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if self.config_path is not None and self.config_path.is_file():
            self._set_config(load_hotpatcher_config(self.config_path, normalize=True))
        else:
            self._set_config(get_hotpatcher_default_config())

    def _create_styles(self) -> None:
        theme_applied = apply_gui_theme(self)
        style = ttk.Style(self)
        if not theme_applied and "clam" in style.theme_names():
            style.theme_use("clam")
        configure_gui_fonts(self, style)
        style.configure("Status.TLabel", padding=(8, 4))
        style.configure("Panel.TLabelframe", padding=8)
        style.configure("Help.TLabel", foreground="#666666")

    def _create_widgets(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.config_tab = ttk.Frame(self.notebook)
        self.runtime_tab = ttk.Frame(self.notebook)
        self.logs_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.config_tab, text="配置")
        self.notebook.add(self.runtime_tab, text="运行时")
        self.notebook.add(self.logs_tab, text="日志")

        self._create_config_tab()
        self._create_runtime_tab()
        self._create_logs_tab()

        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel", anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(status_frame, textvariable=self.busy_var, width=10, anchor=tk.CENTER).pack(side=tk.RIGHT, padx=(0, 8))
        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=180)
        self.progress.pack(side=tk.RIGHT, padx=(0, 8), pady=4)

    def _create_config_tab(self) -> None:
        toolbar = ttk.Frame(self.config_tab)
        toolbar.pack(fill=tk.X, padx=10, pady=8)
        ttk.Label(toolbar, text="配置文件:").pack(side=tk.LEFT)
        ttk.Entry(toolbar, textvariable=self.config_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        ttk.Button(toolbar, text="浏览", command=self.browse_config_path).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="导出默认", command=self.export_default_config).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="打开", command=self.open_config).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="保存", command=self.save_config).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="规范化", command=self.normalize_config).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="本地应用", command=self.apply_config_local).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text="远程应用", command=self.apply_config_remote).pack(side=tk.LEFT)

        paned = ttk.PanedWindow(self.config_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        form_container = ttk.Frame(paned)
        json_container = ttk.Frame(paned)
        paned.add(form_container, weight=1)
        paned.add(json_container, weight=2)

        canvas_bg = self._frame_background()
        self.form_canvas = tk.Canvas(
            form_container,
            highlightthickness=0,
            borderwidth=0,
            bg=canvas_bg,
            takefocus=1,
        )
        form_canvas = self.form_canvas
        form_scroll = ttk.Scrollbar(form_container, orient=tk.VERTICAL, command=form_canvas.yview)
        self.form_frame = ttk.Frame(form_canvas)
        self._form_canvas_window = form_canvas.create_window((0, 0), window=self.form_frame, anchor=tk.NW)
        self.form_frame.bind("<Configure>", self._on_form_frame_configure)
        form_canvas.bind("<Configure>", self._on_form_canvas_configure)
        form_canvas.configure(yscrollcommand=form_scroll.set)
        form_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        form_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._create_form_fields(self.form_frame)
        self._bind_form_mousewheel()

        json_toolbar = ttk.Frame(json_container)
        json_toolbar.pack(fill=tk.X)
        ttk.Label(json_toolbar, text="完整 JSON").pack(side=tk.LEFT)
        json_frame = ttk.Frame(json_container)
        json_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.json_text = tk.Text(json_frame, wrap=tk.NONE, undo=True)
        json_y = ttk.Scrollbar(json_frame, orient=tk.VERTICAL, command=self.json_text.yview)
        json_x = ttk.Scrollbar(json_frame, orient=tk.HORIZONTAL, command=self.json_text.xview)
        self.json_text.configure(yscrollcommand=json_y.set, xscrollcommand=json_x.set)
        self.json_text.grid(row=0, column=0, sticky=tk.NSEW)
        json_y.grid(row=0, column=1, sticky=tk.NS)
        json_x.grid(row=1, column=0, sticky=tk.EW)
        json_frame.rowconfigure(0, weight=1)
        json_frame.columnconfigure(0, weight=1)
        self.json_text.bind("<<Modified>>", self._on_json_modified)
        self._install_form_traces()

    def _create_form_fields(self, parent: ttk.Frame) -> None:
        features = self.catalog_data.get("features", {})
        if not isinstance(features, dict):
            return
        for feature_name, feature_schema in features.items():
            if not isinstance(feature_schema, dict):
                continue
            settings = feature_schema.get("settings", {})
            if not isinstance(settings, dict):
                continue
            title = str(feature_schema.get("title") or _humanize_name(feature_name))
            description = str(feature_schema.get("description") or "")
            frame = ttk.LabelFrame(parent, text=title, style="Panel.TLabelframe")
            frame.pack(fill=tk.X, padx=4, pady=(0, 8))
            row = 0
            if description:
                ttk.Label(frame, text=description, style="Help.TLabel", wraplength=360).grid(
                    row=row,
                    column=0,
                    columnspan=2,
                    sticky=tk.EW,
                    pady=(0, 6),
                )
                row += 1
            for setting_name, metadata in settings.items():
                if not isinstance(metadata, dict):
                    metadata = {"type": str(metadata)}
                row = self._add_schema_setting_row(frame, row, feature_name, setting_name, metadata)

    def _add_schema_setting_row(
        self,
        parent: tk.Misc,
        row: int,
        feature_name: str,
        setting_name: str,
        metadata: dict[str, Any],
    ) -> int:
        default_value = metadata.get("default")
        kind = _metadata_field_kind(metadata, default_value)
        title = str(metadata.get("title") or _humanize_name(setting_name))
        description = str(metadata.get("description") or "")

        variable: tk.Variable
        if kind == "bool":
            variable = tk.BooleanVar(value=bool(default_value))
            ttk.Checkbutton(parent, text=title, variable=variable).grid(
                row=row,
                column=0,
                columnspan=2,
                sticky=tk.W,
                pady=(3, 0),
            )
        elif kind == "choice":
            variable = tk.StringVar(value=_value_to_text(default_value, kind))
            values = tuple(str(item) for item in metadata.get("choices", ()))
            self._combo_row(parent, row, f"{title}:", variable, values)
        else:
            variable = tk.StringVar(value=_value_to_text(default_value, kind))
            self._entry_row(parent, row, f"{title}:", variable)

        self._schema_field_vars[(feature_name, setting_name)] = (variable, kind, default_value, metadata)
        row += 1
        if description:
            ttk.Label(parent, text=description, style="Help.TLabel", wraplength=360).grid(
                row=row,
                column=1 if kind != "bool" else 0,
                columnspan=1 if kind != "bool" else 2,
                sticky=tk.EW,
                pady=(0, 5),
            )
            row += 1
        return row

    def _create_runtime_tab(self) -> None:
        panel = ttk.Frame(self.runtime_tab)
        panel.pack(fill=tk.X, padx=18, pady=16)
        self._entry_row(panel, 0, "Host:", self.host_var)
        self._entry_row(panel, 1, "Port:", self.port_var)
        self._entry_row(panel, 2, "Token:", self.token_var)
        ttk.Label(panel, text="状态:").grid(row=3, column=0, sticky=tk.W, pady=4)
        ttk.Label(panel, textvariable=self.connection_status_var).grid(row=3, column=1, sticky=tk.W, pady=4)
        button_frame = ttk.Frame(panel)
        button_frame.grid(row=4, column=1, sticky=tk.W, pady=(8, 0))
        ttk.Button(button_frame, text="开始监听", command=self.start_runtime_host).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="停止监听", command=self.stop_runtime_host).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(button_frame, text="刷新环境变量", command=self.update_env_preview).pack(side=tk.LEFT, padx=(8, 0))
        panel.columnconfigure(1, weight=1)

        env_frame = ttk.LabelFrame(self.runtime_tab, text="启动环境变量", style="Panel.TLabelframe")
        env_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 16))
        self.env_text = tk.Text(env_frame, height=12, wrap=tk.NONE)
        env_scroll = ttk.Scrollbar(env_frame, orient=tk.VERTICAL, command=self.env_text.yview)
        self.env_text.configure(yscrollcommand=env_scroll.set)
        self.env_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        env_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.update_env_preview()

    def _create_logs_tab(self) -> None:
        toolbar = ttk.Frame(self.logs_tab)
        toolbar.pack(fill=tk.X, padx=10, pady=8)
        ttk.Button(toolbar, text="清空", command=self.clear_logs).pack(side=tk.LEFT)
        ttk.Checkbutton(toolbar, text="自动滚动", variable=self.log_autoscroll_var).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(toolbar, text="等级:").pack(side=tk.LEFT, padx=(16, 4))
        ttk.Combobox(toolbar, textvariable=self.log_level_filter_var, state="readonly", values=("全部", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"), width=10).pack(side=tk.LEFT)
        ttk.Label(toolbar, text="来源:").pack(side=tk.LEFT, padx=(16, 4))
        ttk.Combobox(
            toolbar,
            textvariable=self.log_source_filter_var,
            state="readonly",
            values=("全部", "logging", "stdout", "stderr", "subprocess", "dropped", "fault"),
            width=12,
        ).pack(side=tk.LEFT)

        log_frame = ttk.Frame(self.logs_tab)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.log_text = tk.Text(log_frame, wrap=tk.NONE, state=tk.DISABLED)
        log_y = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_x = ttk.Scrollbar(log_frame, orient=tk.HORIZONTAL, command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=log_y.set, xscrollcommand=log_x.set)
        self.log_text.grid(row=0, column=0, sticky=tk.NSEW)
        log_y.grid(row=0, column=1, sticky=tk.NS)
        log_x.grid(row=1, column=0, sticky=tk.EW)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

    def _entry_row(self, parent: tk.Misc, row: int, label: str, variable: tk.Variable) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky=tk.EW, pady=4)
        parent.columnconfigure(1, weight=1)
        return entry

    def _combo_row(self, parent: tk.Misc, row: int, label: str, variable: tk.Variable, values: tuple[str, ...]) -> ttk.Combobox:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        combo = ttk.Combobox(parent, textvariable=variable, state="readonly", values=values)
        combo.grid(row=row, column=1, sticky=tk.EW, pady=4)
        parent.columnconfigure(1, weight=1)
        return combo

    def _frame_background(self) -> str:
        style = ttk.Style(self)
        background = style.lookup("TFrame", "background") or style.lookup(".", "background")
        return str(background or self.cget("background"))

    def _on_form_frame_configure(self, _event: tk.Event) -> None:
        try:
            self.form_canvas.configure(scrollregion=self.form_canvas.bbox("all"))
        except tk.TclError:
            return

    def _on_form_canvas_configure(self, event: tk.Event) -> None:
        if self._form_canvas_window is None:
            return
        try:
            self.form_canvas.itemconfigure(self._form_canvas_window, width=max(1, event.width))
            self.form_canvas.configure(scrollregion=self.form_canvas.bbox("all"))
        except tk.TclError:
            return

    def _bind_form_mousewheel(self) -> None:
        widgets = [self.form_canvas, self.form_frame, *self._form_descendants(self.form_frame)]
        for widget in widgets:
            widget.bind("<Enter>", self._on_form_mouse_enter, add="+")
            widget.bind("<Leave>", self._on_form_mouse_leave, add="+")
            widget.bind("<MouseWheel>", self._on_form_mousewheel, add="+")
            widget.bind("<Button-4>", self._on_form_mousewheel, add="+")
            widget.bind("<Button-5>", self._on_form_mousewheel, add="+")

    def _form_descendants(self, widget: tk.Misc) -> list[tk.Misc]:
        descendants: list[tk.Misc] = []
        for child in widget.winfo_children():
            descendants.append(child)
            descendants.extend(self._form_descendants(child))
        return descendants

    def _on_form_mouse_enter(self, _event: tk.Event) -> None:
        self._form_mouse_over = True
        try:
            self.form_canvas.focus_set()
        except tk.TclError:
            pass

    def _on_form_mouse_leave(self, event: tk.Event) -> None:
        x_root = getattr(event, "x_root", 0)
        y_root = getattr(event, "y_root", 0)
        try:
            target = self.winfo_containing(x_root, y_root)
        except tk.TclError:
            target = None
        if target is not None and self._is_form_widget(target):
            return
        self._form_mouse_over = False

    def _is_form_widget(self, widget: tk.Misc) -> bool:
        current: tk.Misc | None = widget
        while current is not None:
            if current is self.form_canvas or current is self.form_frame:
                return True
            try:
                current = current.master
            except tk.TclError:
                return False
        return False

    def _on_form_mousewheel(self, event: tk.Event) -> str | None:
        if not self._form_mouse_over:
            return None
        if getattr(event, "num", None) == 4:
            self.form_canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            self.form_canvas.yview_scroll(3, "units")
        else:
            delta = getattr(event, "delta", 0)
            if delta:
                self.form_canvas.yview_scroll(int(-1 * (delta / 120)), "units")
        return "break"

    def _install_form_traces(self) -> None:
        variables = [variable for variable, _kind, _default, _metadata in self._schema_field_vars.values()]
        for variable in variables:
            variable.trace_add("write", lambda *_args: self._schedule_form_json_update())

    def _schedule_form_json_update(self) -> None:
        if self._updating_form or self._updating_json:
            return
        if self._form_update_job is not None:
            self.after_cancel(self._form_update_job)
        self._form_update_job = self.after(120, self._sync_form_to_json)

    def _sync_form_to_json(self) -> None:
        self._form_update_job = None
        if self._updating_form or self._updating_json:
            return
        try:
            config = self._read_editor_config()
        except Exception:
            config = self.config_data
        try:
            config = self._apply_form_to_config(config)
        except Exception as exc:
            self.set_status(f"表单配置无效: {exc}")
            return
        self.config_data = config
        self._write_json_editor(config)

    def set_status(self, message: str) -> None:
        """设置状态栏消息。

        Args:
            message (str):
                状态栏消息
        """
        self.status_var.set(message)

    def set_busy_state(self, busy: bool) -> None:
        """设置忙碌状态显示。

        Args:
            busy (bool):
                是否处于忙碌状态
        """
        if busy:
            self.busy_var.set("执行中")
            self.progress.start(12)
        else:
            self.busy_var.set("")
            self.progress.stop()

    def browse_config_path(self) -> None:
        """选择配置文件保存路径。"""
        path = filedialog.asksaveasfilename(
            title="选择 Hotpatcher 配置文件",
            defaultextension=".json",
            filetypes=(("JSON", "*.json"), ("All files", "*.*")),
        )
        if path:
            self.config_path_var.set(path)
            self.config_path = Path(path).expanduser()

    def export_default_config(self) -> None:
        """导出默认配置文件。"""
        path = self._current_config_path_or_ask(save=True)
        if path is None:
            return
        overwrite = path.exists() and messagebox.askyesno("覆盖配置", f"配置文件已存在:\n{path}\n\n是否覆盖？")
        if path.exists() and not overwrite:
            return
        self.run_background(
            "导出默认配置中...",
            lambda: export_hotpatcher_default_config(path, overwrite=overwrite),
            lambda output: self._after_export_default(output),
        )

    def open_config(self) -> None:
        """打开并加载配置文件。"""
        path = self._current_config_path_or_ask(save=False)
        if path is None:
            return
        self.run_background(
            "读取配置中...",
            lambda: load_hotpatcher_config(path, normalize=True),
            lambda config: self._after_open_config(path, config),
        )

    def save_config(self) -> None:
        """保存当前配置文件。"""
        path = self._current_config_path_or_ask(save=True)
        if path is None:
            return
        try:
            config = self._read_editor_config()
            config = normalize_hotpatcher_config(config)
        except Exception as exc:
            messagebox.showerror("配置无效", str(exc))
            return
        self.run_background(
            "保存配置中...",
            lambda: save_hotpatcher_config(path, config),
            lambda _value: self._after_save_config(path, config),
        )

    def normalize_config(self) -> None:
        """规范化当前配置。"""
        try:
            config = normalize_hotpatcher_config(self._read_editor_config())
        except Exception as exc:
            messagebox.showerror("配置无效", str(exc))
            return
        self._set_config(config)
        self.set_status("配置已规范化")

    def apply_config_local(self) -> None:
        """将当前配置应用到本地进程。"""
        try:
            config = normalize_hotpatcher_config(self._read_editor_config())
        except Exception as exc:
            messagebox.showerror("配置无效", str(exc))
            return
        self.run_background(
            "应用本地配置中...",
            lambda: apply_hotpatcher_config(config),
            lambda result: messagebox.showinfo("应用结果", json.dumps(result, ensure_ascii=False, indent=2)),
        )

    def apply_config_remote(self) -> None:
        """将当前配置应用到远程 runtime。"""
        if self.runtime_host is None or not self.runtime_host.service_channel_available:
            messagebox.showwarning("未连接", "远程 services 控制通道未连接")
            return
        try:
            config = normalize_hotpatcher_config(self._read_editor_config())
        except Exception as exc:
            messagebox.showerror("配置无效", str(exc))
            return
        self.run_background(
            "应用远程配置中...",
            lambda: self.runtime_host.apply_remote_config(config) if self.runtime_host else {},
            lambda result: messagebox.showinfo("远程应用结果", json.dumps(result, ensure_ascii=False, indent=2)),
            lambda error: messagebox.showerror("远程应用失败", str(error)),
        )

    def start_runtime_host(self) -> None:
        """启动 runtime host。"""
        if self.runtime_host is not None:
            return
        try:
            port = int(self.port_var.get())
        except ValueError:
            messagebox.showerror("端口无效", "端口必须是整数")
            return
        self.runtime_host = HotpatcherRuntimeHost(
            self.host_var.get().strip() or DEFAULT_RUNTIME_HOST,
            port,
            token=self.token_var.get(),
            get_config=self._runtime_config_snapshot,
            on_log=self._runtime_log_queue.put,
            on_status=self._set_connection_status,
            confirm_file_operation=self._confirm_file_operation,
        )
        try:
            self.runtime_host.start()
        except Exception as exc:
            self.runtime_host = None
            messagebox.showerror("监听失败", str(exc))
            return
        actual_host, actual_port = self.runtime_host.server_address
        self.host_var.set(actual_host)
        self.port_var.set(str(actual_port))
        self.update_env_preview()

    def stop_runtime_host(self) -> None:
        """停止 runtime host。"""
        host = self.runtime_host
        self.runtime_host = None
        if host is not None:
            host.stop()
        self.connection_status_var.set("未监听")

    def update_env_preview(self) -> None:
        """更新 runtime 环境变量预览。"""
        try:
            port = int(self.port_var.get())
        except ValueError:
            port = DEFAULT_RUNTIME_PORT
        env = build_hotpatcher_runtime_env(
            self.host_var.get().strip() or DEFAULT_RUNTIME_HOST,
            port,
            token=self.token_var.get(),
            config_source="remote",
        )
        lines = [f"{key}={value}" for key, value in env.items()]
        self.env_text.configure(state=tk.NORMAL)
        self.env_text.delete("1.0", tk.END)
        self.env_text.insert(tk.END, "\n".join(lines) + "\n")
        self.env_text.configure(state=tk.NORMAL)

    def clear_logs(self) -> None:
        """清空日志窗口。"""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def form_to_json(self) -> None:
        """将表单内容同步到 JSON 配置。"""
        try:
            config = self._read_editor_config()
        except Exception:
            config = self.config_data
        try:
            config = self._apply_form_to_config(config)
        except Exception as exc:
            messagebox.showerror("表单配置无效", str(exc))
            return
        self._set_config(normalize_hotpatcher_config(config))

    def _after_export_default(self, output: Path) -> None:
        self.config_path = output
        self.config_path_var.set(output.as_posix())
        self._set_config(load_hotpatcher_config(output, normalize=True))
        self.set_status(f"默认配置已导出: {output}")

    def _after_open_config(self, path: Path, config: dict[str, Any]) -> None:
        self.config_path = path
        self.config_path_var.set(path.as_posix())
        self._set_config(config)
        self.set_status(f"已打开配置: {path}")

    def _after_save_config(self, path: Path, config: dict[str, Any]) -> None:
        self.config_path = path
        self.config_path_var.set(path.as_posix())
        self._set_config(config)
        self.set_status(f"配置已保存: {path}")

    def _current_config_path_or_ask(self, *, save: bool) -> Path | None:
        raw = self.config_path_var.get().strip()
        if raw:
            path = Path(raw).expanduser()
            self.config_path = path
            return path
        if save:
            selected = filedialog.asksaveasfilename(defaultextension=".json", filetypes=(("JSON", "*.json"), ("All files", "*.*")))
        else:
            selected = filedialog.askopenfilename(filetypes=(("JSON", "*.json"), ("All files", "*.*")))
        if not selected:
            return None
        path = Path(selected).expanduser()
        self.config_path = path
        self.config_path_var.set(path.as_posix())
        return path

    def _set_config(self, config: dict[str, Any]) -> None:
        self.config_data = config
        self._config_to_form(config)
        self._write_json_editor(config)

    def _write_json_editor(self, config: dict[str, Any]) -> None:
        self._updating_json = True
        try:
            self.json_text.configure(state=tk.NORMAL)
            self.json_text.delete("1.0", tk.END)
            self.json_text.insert(tk.END, json.dumps(config, ensure_ascii=False, indent=2) + "\n")
            self.json_text.edit_modified(False)
            self._json_dirty = False
        finally:
            self._updating_json = False

    def _read_editor_config(self) -> dict[str, Any]:
        raw = self.json_text.get("1.0", tk.END).strip()
        if not raw:
            return {}
        config = json.loads(raw)
        if not isinstance(config, dict):
            raise ValueError("配置 JSON 顶层必须是对象")
        return config

    def _runtime_config_snapshot(self) -> dict[str, Any]:
        try:
            return normalize_hotpatcher_config(self._read_editor_config())
        except Exception:
            return normalize_hotpatcher_config(self.config_data)

    def _config_to_form(self, config: dict[str, Any]) -> None:
        self._updating_form = True
        try:
            for (feature_name, setting_name), (variable, kind, default_value, _metadata) in self._schema_field_vars.items():
                feature_config = _section_by_path(config, feature_name)
                value = _value_by_path(feature_config, setting_name, default_value)
                if kind == "bool":
                    variable.set(bool(value))
                else:
                    variable.set(_value_to_text(value, kind))
        finally:
            self._updating_form = False

    def _apply_form_to_config(self, config: dict[str, Any]) -> dict[str, Any]:
        config = dict(config)
        for (feature_name, setting_name), (variable, kind, default_value, _metadata) in self._schema_field_vars.items():
            feature_config = _ensure_section_by_path(config, feature_name)
            _set_value_by_path(
                feature_config,
                setting_name,
                _variable_to_value(variable, kind, default_value),
            )
        return config

    def _on_json_modified(self, _event: tk.Event) -> None:
        if self._updating_json:
            self.json_text.edit_modified(False)
            return
        self._json_dirty = self.json_text.edit_modified()

    def _poll_runtime_logs(self) -> None:
        while True:
            try:
                entry = self._runtime_log_queue.get_nowait()
            except queue.Empty:
                break
            if self._log_entry_visible(entry):
                self._append_log(entry.format_line())
        self.after(100, self._poll_runtime_logs)

    def _log_entry_visible(self, entry: RuntimeLogEntry) -> bool:
        level_filter = self.log_level_filter_var.get()
        if level_filter != "全部" and entry.payload.get("level") != level_filter:
            return False
        source_filter = self.log_source_filter_var.get()
        if source_filter == "全部":
            return True
        if source_filter == "logging":
            return entry.message_type == "log.record"
        if source_filter == "dropped":
            return entry.message_type == "log.dropped"
        if source_filter == "fault":
            return entry.payload.get("source") == "fault"
        if source_filter == "subprocess":
            return entry.payload.get("source") == "subprocess"
        return entry.payload.get("stream") == source_filter

    def _append_log(self, line: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, line + "\n")
        if self.log_autoscroll_var.get():
            self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _set_connection_status(self, message: str) -> None:
        self.connection_status_var.set(message)

    def _confirm_file_operation(self, message_type: str, payload: dict[str, Any]) -> bool:
        return messagebox.askyesno("文件操作确认", f"{message_type}\n\n{json.dumps(payload, ensure_ascii=False, indent=2)}")

    def _on_close(self) -> None:
        self.stop_runtime_host()
        self.destroy()


def _section(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name, {})
    return value if isinstance(value, dict) else {}


def _ensure_section(config: dict[str, Any], name: str) -> dict[str, Any]:
    value = config.get(name)
    if not isinstance(value, dict):
        value = {}
        config[name] = value
    return value


def _section_by_path(config: dict[str, Any], path: str) -> dict[str, Any]:
    current = config
    for part in path.split("."):
        current = _section(current, part)
        if not current:
            return {}
    return current


def _ensure_section_by_path(config: dict[str, Any], path: str) -> dict[str, Any]:
    current = config
    for part in path.split("."):
        current = _ensure_section(current, part)
    return current


def _value_by_path(config: dict[str, Any], path: str, default: Any = None) -> Any:
    current: Any = config
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _set_value_by_path(config: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = config
    for part in parts[:-1]:
        current = _ensure_section(current, part)
    current[parts[-1]] = value


def _split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _join_list(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return ",".join(str(item) for item in value)
    return ""


def _field_kind(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, (list, tuple)):
        return "list"
    if isinstance(value, dict):
        return "object"
    return "str"


def _metadata_field_kind(metadata: dict[str, Any], default_value: Any = None) -> str:
    raw_type = str(metadata.get("type", "")).strip().lower()
    if raw_type == "choice":
        return "choice"
    if raw_type == "bool":
        return "bool"
    if raw_type == "int":
        return "int"
    if raw_type in {"list", "list[str]"} or raw_type.startswith("list["):
        return "list"
    if raw_type == "object" or "object" in raw_type:
        return "object"
    if raw_type == "str":
        return "str"
    return _field_kind(default_value)


def _value_to_text(value: Any, kind: str) -> str:
    if kind == "list":
        return _join_list(value)
    if kind in {"json", "object"}:
        if value is None:
            return ""
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return "" if value is None else str(value)


def _variable_to_value(variable: tk.Variable, kind: str, default_value: Any = None) -> Any:
    value = variable.get()
    if kind == "bool":
        return bool(value)
    if kind == "int":
        default_int = default_value if isinstance(default_value, int) and not isinstance(default_value, bool) else 0
        return _to_int(str(value), default_int)
    if kind == "list":
        return _split_list(str(value))
    if kind == "choice":
        return str(value)
    if kind in {"json", "object"}:
        text = str(value).strip()
        if not text:
            return {} if isinstance(default_value, dict) else default_value
        return json.loads(text)
    return str(value)


def _humanize_name(name: str) -> str:
    return name.replace("_", " ").replace(".", " ").title()


def _to_int(value: str, default: int) -> int:
    try:
        return int(value)
    except ValueError:
        return default


def launch_hotpatcher_manager_gui(
    config_path: str | Path | None = DEFAULT_HOTPATCHER_CONFIG_PATH,
    host: str = DEFAULT_RUNTIME_HOST,
    port: int = DEFAULT_RUNTIME_PORT,
    token: str = "",
) -> None:
    """启动 Hotpatcher 配置管理 GUI

    Args:
        config_path (str | Path | None):
            配置文件路径
        host (str):
            runtime host 监听地址
        port (int):
            runtime host 监听端口
        token (str):
            runtime host 访问令牌
    """

    app = HotpatcherManagerApp(config_path=config_path, host=host, port=port, token=token)
    app.mainloop()
