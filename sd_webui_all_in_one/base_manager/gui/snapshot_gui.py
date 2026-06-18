"""WebUI 环境快照管理 GUI"""

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import (
    filedialog,
    messagebox,
    ttk,
)

from sd_webui_all_in_one.base_manager.gui.version_gui import (
    BackgroundTaskMixin,
    apply_gui_theme,
    apply_window_icon,
    configure_gui_fonts,
    install_text_context_menu,
)
from sd_webui_all_in_one.base_manager.snapshot import WebUiSnapshot, resolve_snapshot_output, save_snapshot
from sd_webui_all_in_one.base_manager.snapshot_restore import (
    GitRestorePlanItem,
    PackageRestorePlanItem,
    SnapshotRestoreOptions,
    SnapshotRestorePlan,
    preview_webui_snapshot_restore,
    restore_webui_snapshot,
)
from sd_webui_all_in_one.config import SD_WEBUI_ALL_IN_ONE_SNAPSHOT_DIR


SnapshotFactory = Callable[[bool], WebUiSnapshot]


class SnapshotManagerApp(tk.Tk, BackgroundTaskMixin):
    """WebUI 快照创建与恢复窗口"""

    def __init__(
        self,
        title: str,
        webui_type: str,
        webui_path: Path,
        snapshot_factory: SnapshotFactory,
        use_uv: bool = True,
        use_pypi_mirror: bool = True,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> None:
        tk.Tk.__init__(self)
        BackgroundTaskMixin.__init__(self)
        self.app_title = title
        self.webui_type = webui_type
        self.webui_path = Path(webui_path)
        self.snapshot_factory = snapshot_factory
        self.use_pypi_mirror = use_pypi_mirror
        self.use_github_mirror = use_github_mirror
        self.custom_github_mirror = custom_github_mirror
        self.current_plan: SnapshotRestorePlan | None = None

        self.output_path_var = tk.StringVar(value=SD_WEBUI_ALL_IN_ONE_SNAPSHOT_DIR.as_posix())
        self.include_packages_var = tk.BooleanVar(value=True)
        self.snapshot_path_var = tk.StringVar(value="")
        self.use_uv_var = tk.BooleanVar(value=use_uv)
        self.prune_packages_var = tk.BooleanVar(value=False)
        self.prune_extensions_var = tk.BooleanVar(value=False)
        self.force_git_reset_var = tk.BooleanVar(value=False)

        self.title(f"{self.app_title} 快照管理")
        apply_window_icon(self)
        self.geometry("1120x720")
        self.minsize(900, 560)
        self._create_styles()
        self._create_widgets()
        self._install_task_poller(self)

    def _create_styles(self) -> None:
        theme_applied = apply_gui_theme(self)
        style = ttk.Style(self)
        if not theme_applied and "clam" in style.theme_names():
            style.theme_use("clam")
        configure_gui_fonts(self, style)
        style.configure("Status.TLabel", padding=(8, 4))

    def _create_widgets(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.X)
        ttk.Label(top, text=f"路径: {self.webui_path}").pack(side=tk.LEFT, padx=10, pady=8)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.create_tab = ttk.Frame(self.notebook)
        self.restore_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.create_tab, text="创建快照")
        self.notebook.add(self.restore_tab, text="恢复快照")
        self._create_snapshot_tab()
        self._create_restore_tab()

        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel", anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.busy_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.busy_var, width=10, anchor=tk.CENTER).pack(side=tk.RIGHT, padx=(0, 8))
        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=180)
        self.progress.pack(side=tk.RIGHT, padx=(0, 8), pady=4)

    def _create_snapshot_tab(self) -> None:
        form = ttk.Frame(self.create_tab)
        form.pack(fill=tk.X, padx=18, pady=16)
        ttk.Label(form, text="输出目录:").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=self.output_path_var).grid(row=0, column=1, sticky=tk.EW, padx=(12, 8), pady=4)
        ttk.Button(form, text="选择", command=self._choose_output_path).grid(row=0, column=2, pady=4)
        ttk.Checkbutton(form, text="记录 Python packages", variable=self.include_packages_var).grid(row=1, column=1, sticky=tk.W, padx=(12, 0), pady=4)
        form.columnconfigure(1, weight=1)

        buttons = ttk.Frame(self.create_tab)
        buttons.pack(fill=tk.X, padx=18, pady=(0, 8))
        ttk.Button(buttons, text="创建快照", command=self.create_snapshot).pack(side=tk.LEFT)

        self.create_result = tk.Text(self.create_tab, height=18, wrap=tk.WORD, state=tk.DISABLED)
        self.create_result.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))
        install_text_context_menu(self.create_result, editable=False)

    def _create_restore_tab(self) -> None:
        form = ttk.Frame(self.restore_tab)
        form.pack(fill=tk.X, padx=18, pady=16)
        ttk.Label(form, text="快照文件:").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=self.snapshot_path_var).grid(row=0, column=1, sticky=tk.EW, padx=(12, 8), pady=4)
        ttk.Button(form, text="选择", command=self._choose_snapshot_path).grid(row=0, column=2, pady=4)
        form.columnconfigure(1, weight=1)

        options = ttk.Frame(self.restore_tab)
        options.pack(fill=tk.X, padx=18, pady=(0, 8))
        ttk.Checkbutton(options, text="使用 uv", variable=self.use_uv_var).pack(side=tk.LEFT)
        ttk.Checkbutton(options, text="卸载快照外 Python 包", variable=self.prune_packages_var, command=self._invalidate_plan).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Checkbutton(options, text="删除快照外扩展", variable=self.prune_extensions_var, command=self._invalidate_plan).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Checkbutton(options, text="允许覆盖 Git 未提交变更", variable=self.force_git_reset_var, command=self._invalidate_plan).pack(side=tk.LEFT, padx=(12, 0))

        buttons = ttk.Frame(self.restore_tab)
        buttons.pack(fill=tk.X, padx=18, pady=(0, 8))
        ttk.Button(buttons, text="预检查", command=self.preview_restore).pack(side=tk.LEFT)
        self.restore_button = ttk.Button(buttons, text="恢复快照", command=self.restore_snapshot, state=tk.DISABLED)
        self.restore_button.pack(side=tk.LEFT, padx=(8, 0))

        self.restore_result = tk.Text(self.restore_tab, height=18, wrap=tk.WORD, state=tk.DISABLED)
        self.restore_result.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))
        install_text_context_menu(self.restore_result, editable=False)

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def set_busy_state(self, busy: bool) -> None:
        if busy:
            self.busy_var.set("执行中")
            self.progress.start(12)
        else:
            self.busy_var.set("")
            self.progress.stop()

    def _choose_output_path(self) -> None:
        current_output = Path(self.output_path_var.get())
        initial_dir = current_output if current_output.suffix == "" else current_output.parent
        path = filedialog.askdirectory(
            parent=self,
            title="选择快照输出目录",
            initialdir=initial_dir.as_posix(),
        )
        if path:
            self.output_path_var.set(path)

    def _choose_snapshot_path(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="选择快照文件",
            filetypes=(("JSON 文件", "*.json"), ("所有文件", "*.*")),
        )
        if path:
            self.snapshot_path_var.set(path)
            self._invalidate_plan()

    def _restore_options(self) -> SnapshotRestoreOptions:
        return SnapshotRestoreOptions(
            prune_packages=bool(self.prune_packages_var.get()),
            prune_extensions=bool(self.prune_extensions_var.get()),
            force_git_reset=bool(self.force_git_reset_var.get()),
            use_uv=bool(self.use_uv_var.get()),
            use_pypi_mirror=self.use_pypi_mirror,
            use_github_mirror=self.use_github_mirror,
            custom_github_mirror=self.custom_github_mirror,
        )

    def _snapshot_path(self) -> Path | None:
        value = self.snapshot_path_var.get().strip()
        if not value:
            messagebox.showwarning("缺少快照文件", "请选择要恢复的快照文件")
            return None
        path = Path(value)
        if not path.is_file():
            messagebox.showwarning("快照文件不存在", f"快照文件不存在: {path}")
            return None
        return path

    def _invalidate_plan(self) -> None:
        self.current_plan = None
        self.restore_button.configure(state=tk.DISABLED)

    def create_snapshot(self) -> None:
        output_text = self.output_path_var.get().strip()
        if not output_text:
            messagebox.showwarning("缺少输出目录", "请选择快照输出目录")
            return
        output_dir = Path(output_text)

        def _task() -> tuple[WebUiSnapshot, Path]:
            snapshot = self.snapshot_factory(bool(self.include_packages_var.get()))
            output_path = resolve_snapshot_output(snapshot, output_dir)
            save_snapshot(snapshot, output_path)
            return snapshot, output_path

        self.run_background(
            "创建快照中...",
            _task,
            lambda result: self._show_create_result(result[0], result[1]),
        )

    def _show_create_result(self, snapshot: WebUiSnapshot, output: Path) -> None:
        lines = [
            "快照创建完成",
            f"输出文件: {output}",
            f"WebUI: {snapshot.webui.name} ({snapshot.webui.type})",
            f"Python: {snapshot.python.version}",
            f"Python packages: {len(snapshot.packages)}",
            f"内核: {'Git 仓库' if snapshot.kernel and snapshot.kernel.is_git_repo else '非 Git 仓库'}",
            f"扩展: {len(snapshot.extensions)}",
        ]
        self._set_text(self.create_result, "\n".join(lines))
        messagebox.showinfo("创建完成", f"快照已保存到:\n{output}")

    def preview_restore(self) -> None:
        snapshot_path = self._snapshot_path()
        if snapshot_path is None:
            return
        self.run_background(
            "预检查快照恢复中...",
            lambda: preview_webui_snapshot_restore(
                snapshot_path=snapshot_path,
                webui_path=self.webui_path,
                expected_webui_type=self.webui_type,
                options=self._restore_options(),
            ),
            self._show_restore_plan,
        )

    def _show_restore_plan(self, plan: SnapshotRestorePlan) -> None:
        self.current_plan = plan
        self._set_text(self.restore_result, self._format_restore_plan(plan))
        self.restore_button.configure(state=tk.NORMAL if not plan.errors else tk.DISABLED)

    def restore_snapshot(self) -> None:
        snapshot_path = self._snapshot_path()
        if snapshot_path is None:
            return
        if self.current_plan is None:
            messagebox.showwarning("需要预检查", "请先执行预检查")
            return
        if self.current_plan.errors:
            messagebox.showwarning("无法恢复", "\n".join(self.current_plan.errors))
            return
        if (self.prune_packages_var.get() or self.prune_extensions_var.get() or self.force_git_reset_var.get()) and not messagebox.askyesno(
            "确认恢复",
            "当前恢复选项包含清理或强制覆盖操作, 是否继续?",
        ):
            return

        self.run_background(
            "恢复快照中...",
            lambda: restore_webui_snapshot(
                snapshot_path=snapshot_path,
                webui_path=self.webui_path,
                expected_webui_type=self.webui_type,
                options=self._restore_options(),
            ),
            lambda _value: self._restore_finished(),
        )

    def _restore_finished(self) -> None:
        messagebox.showinfo("恢复完成", "快照恢复完成")
        self.preview_restore()

    def _set_text(self, widget: tk.Text, text: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.configure(state=tk.DISABLED)

    def _format_restore_plan(self, plan: SnapshotRestorePlan) -> str:
        lines = [
            f"快照: {plan.snapshot_path}",
            f"WebUI: {plan.snapshot_webui_name} ({plan.snapshot_webui_type})",
            f"目标路径: {plan.webui_path}",
        ]
        if plan.python_version_note:
            lines.extend(("", "Python:", f"- {plan.python_version_note}"))
        if plan.pytorch_device_type:
            lines.extend(("", "PyTorch 源:", f"- 类型: {plan.pytorch_device_type}", f"- {plan.pytorch_mirror_kind or '普通 PyPI'}: {plan.pytorch_mirror_url or '-'}"))
        if plan.warnings:
            lines.append("")
            lines.append("警告:")
            lines.extend(f"- {item}" for item in plan.warnings)
        if plan.errors:
            lines.append("")
            lines.append("阻断:")
            lines.extend(f"- {item}" for item in plan.errors)

        if plan.package_changes:
            lines.append("")
            lines.append("Python packages:")
            lines.extend(self._format_package_item(item) for item in plan.package_changes)
        if plan.kernel_change is not None:
            lines.append("")
            lines.append("内核:")
            lines.append(self._format_git_item(plan.kernel_change))
        if plan.extension_changes:
            lines.append("")
            lines.append("扩展:")
            lines.extend(self._format_extension_item(item) for item in plan.extension_changes)
        return "\n".join(lines)

    def _format_package_item(self, item: PackageRestorePlanItem) -> str:
        current = item.current_version or "-"
        target = item.target_version or "-"
        suffix = f" ({item.reason})" if item.reason else ""
        return f"- [{item.action}] {item.name}: {current} -> {target}{suffix}"

    def _format_git_item(self, item: GitRestorePlanItem) -> str:
        current = item.current_commit or "-"
        target = item.target_commit or "-"
        dirty = " dirty" if item.dirty else ""
        return f"- [{item.action}] {item.name}: {current} -> {target}{dirty} ({item.reason})"

    def _format_extension_item(self, item) -> str:
        if item.cleanup_action == "uninstall":
            return f"- [uninstall] {item.name}: {item.reason}"
        git_text = self._format_git_item(item.git) if item.git is not None else "- [keep] -"
        enabled_text = ""
        if item.target_enabled is not None:
            enabled_text = f"; 启用状态: {item.current_enabled} -> {item.target_enabled}"
        return f"- {item.name}: {git_text}{enabled_text}"


def launch_snapshot_manager_gui(
    title: str,
    webui_type: str,
    webui_path: Path,
    snapshot_factory: SnapshotFactory,
    use_uv: bool = True,
    use_pypi_mirror: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """启动 WebUI 快照管理 GUI"""
    app = SnapshotManagerApp(
        title=title,
        webui_type=webui_type,
        webui_path=webui_path,
        snapshot_factory=snapshot_factory,
        use_uv=use_uv,
        use_pypi_mirror=use_pypi_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )
    app.mainloop()
