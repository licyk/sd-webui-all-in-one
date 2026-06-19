"""WebUI 环境快照管理 GUI"""

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import (
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
from sd_webui_all_in_one.base_manager.snapshot import WebUiSnapshot, load_snapshot, resolve_snapshot_output, save_snapshot
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


@dataclass(slots=True)
class SnapshotListItem:
    """快照列表项"""

    path: Path
    filename: str
    created_at: str
    created_at_display: str
    webui_name: str
    webui_type: str
    package_count: int
    extension_count: int


def format_snapshot_timestamp(value: str) -> str:
    """将快照 ISO 时间戳转换为当前系统本地时间显示

    Args:
        value (str):
            快照 ISO 时间戳字符串。

    Returns:
        str: 适合界面展示的时间字符串。
    """
    try:
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        timestamp = datetime.fromisoformat(normalized)
        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone()
        suffix = (timestamp.strftime("%Z") or timestamp.strftime("%z")) if timestamp.tzinfo is not None else ""
        return f"{timestamp:%Y-%m-%d %H:%M:%S}{f' {suffix}' if suffix else ''}"
    except (AttributeError, TypeError, ValueError, OSError):
        return value


def list_snapshot_files(snapshot_dir: Path) -> list[SnapshotListItem]:
    """读取目录中的有效快照文件列表

    Args:
        snapshot_dir (Path):
            快照文件目录。

    Returns:
        list[SnapshotListItem]: 快照文件列表。
    """
    if not snapshot_dir.is_dir():
        return []

    items: list[SnapshotListItem] = []
    for path in snapshot_dir.glob("*.json"):
        if not path.is_file():
            continue
        try:
            snapshot = load_snapshot(path)
        except (OSError, ValueError):
            continue
        items.append(
            SnapshotListItem(
                path=path,
                filename=path.name,
                created_at=snapshot.created_at,
                created_at_display=format_snapshot_timestamp(snapshot.created_at),
                webui_name=snapshot.webui.name,
                webui_type=snapshot.webui.type,
                package_count=len(snapshot.packages),
                extension_count=len(snapshot.extensions),
            )
        )
    return sorted(items, key=lambda item: (item.created_at, item.filename), reverse=True)


def format_snapshot_path(path: Path) -> str:
    """格式化快照 GUI 中展示的本地路径。

    Args:
        path (Path):
            需要展示的本地路径。

    Returns:
        str: POSIX 风格的路径字符串。
    """
    return path.as_posix()


def build_restore_blocking_guidance(plan: SnapshotRestorePlan) -> list[str]:
    """根据恢复阻断项生成处理建议

    Args:
        plan (SnapshotRestorePlan):
            快照恢复预检查结果。

    Returns:
        list[str]: 面向用户的恢复阻塞处理建议。
    """
    guidance: list[str] = []
    if not plan.webui_type_match:
        guidance.append(
            f"请使用 {plan.snapshot_webui_type} 对应的快照管理器恢复该快照, 或选择 {plan.expected_webui_type} 类型的快照。"
            "跨 WebUI 类型恢复会被终止, 避免写错内核和扩展目录。"
        )
    if plan.kernel_change is not None and plan.kernel_change.action == "blocked_missing_target":
        guidance.append(
            f"请先通过 installer 准备对应的 WebUI kernel, 确认内核目录存在后再恢复: {format_snapshot_path(plan.kernel_change.path)}。"
            "该问题不能通过强制恢复开关绕过, 因为扩展恢复依赖 kernel 目录。"
        )

    dirty_targets: list[str] = []
    if plan.kernel_change is not None and plan.kernel_change.action == "blocked_dirty":
        dirty_targets.append(f"内核: {format_snapshot_path(plan.kernel_change.path)}")
    for item in plan.extension_changes:
        if item.git is not None and item.git.action == "blocked_dirty":
            dirty_targets.append(f"扩展 {item.name}: {format_snapshot_path(item.path)}")
    if dirty_targets:
        guidance.append(f"存在 Git 未提交变更: {'; '.join(dirty_targets)}。建议先提交、stash 或备份这些变更后再恢复。")
        guidance.append(
            "如果确认要丢弃这些未提交变更, 可以勾选“允许覆盖 Git 未提交变更”后再次恢复。"
            "风险: 该开关会强制恢复上述 Git 仓库, 未提交的文件修改可能被永久覆盖。"
        )

    if plan.errors and not guidance:
        guidance.append("请根据阻断信息处理当前环境或更换快照文件后再次恢复。")
    return guidance


def format_restore_blocking_message(plan: SnapshotRestorePlan) -> str:
    """格式化无法恢复时展示给用户的提示

    Args:
        plan (SnapshotRestorePlan):
            快照恢复预检查结果。

    Returns:
        str: 恢复阻塞提示文本。
    """
    lines = [*plan.errors]
    guidance = build_restore_blocking_guidance(plan)
    if guidance:
        lines.extend(("", "处理建议:"))
        lines.extend(f"- {item}" for item in guidance)
    return "\n".join(lines)


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
        snapshot_dir: Path | None = None,
    ) -> None:
        tk.Tk.__init__(self)
        BackgroundTaskMixin.__init__(self)
        self.app_title = title
        self.webui_type = webui_type
        self.webui_path = Path(webui_path)
        self.snapshot_dir = Path(snapshot_dir or SD_WEBUI_ALL_IN_ONE_SNAPSHOT_DIR)
        self.snapshot_factory = snapshot_factory
        self.use_uv = use_uv
        self.use_pypi_mirror = use_pypi_mirror
        self.use_github_mirror = use_github_mirror
        self.custom_github_mirror = custom_github_mirror
        self.current_plan: SnapshotRestorePlan | None = None
        self.snapshot_list_items: dict[str, SnapshotListItem] = {}

        self.include_packages_var = tk.BooleanVar(value=True)
        self.snapshot_path_var = tk.StringVar(value="")
        self.prune_packages_var = tk.BooleanVar(value=True)
        self.prune_extensions_var = tk.BooleanVar(value=True)
        self.force_git_reset_var = tk.BooleanVar(value=True)

        self.title(f"{self.app_title} 快照管理")
        apply_window_icon(self)
        self.geometry("1120x720")
        self.minsize(900, 560)
        self._create_styles()
        self._create_widgets()
        self._install_task_poller(self)
        self.refresh_snapshot_list(show_message=False)

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
        ttk.Label(top, text=f"快照目录: {self.snapshot_dir}").pack(side=tk.LEFT, padx=(10, 0), pady=8)

        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel", anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.busy_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.busy_var, width=10, anchor=tk.CENTER).pack(side=tk.RIGHT, padx=(0, 8))
        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=180)
        self.progress.pack(side=tk.RIGHT, padx=(0, 8), pady=4)

        content = ttk.Frame(self)
        content.pack(fill=tk.BOTH, expand=True)
        self.create_tab = ttk.Frame(content)
        self.create_tab.pack(fill=tk.X)
        self.restore_tab = ttk.Frame(content)
        self.restore_tab.pack(fill=tk.BOTH, expand=True)
        self._create_snapshot_tab()
        self._create_restore_tab()

    def _create_snapshot_tab(self) -> None:
        form = ttk.Frame(self.create_tab)
        form.pack(fill=tk.X, padx=18, pady=(16, 8))
        ttk.Checkbutton(form, text="记录 Python packages", variable=self.include_packages_var).pack(side=tk.LEFT)
        ttk.Button(form, text="创建快照", command=self.create_snapshot).pack(side=tk.LEFT, padx=(12, 0))

    def _create_restore_tab(self) -> None:
        form = ttk.Frame(self.restore_tab)
        form.pack(fill=tk.X, padx=18, pady=(0, 8))
        ttk.Label(form, text="已选快照:").grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=self.snapshot_path_var, state="readonly").grid(row=0, column=1, sticky=tk.EW, padx=(12, 8), pady=4)
        ttk.Button(form, text="刷新列表", command=self.refresh_snapshot_list).grid(row=0, column=2, pady=4)
        form.columnconfigure(1, weight=1)

        list_frame = ttk.Frame(self.restore_tab)
        list_frame.pack(fill=tk.BOTH, padx=18, pady=(0, 8))
        self.snapshot_tree = ttk.Treeview(
            list_frame,
            columns=("created_at", "webui", "type", "packages", "extensions", "filename"),
            show="headings",
            height=8,
            selectmode="browse",
        )
        headings = {
            "created_at": "创建时间",
            "webui": "WebUI",
            "type": "类型",
            "packages": "包",
            "extensions": "扩展",
            "filename": "文件名",
        }
        widths = {
            "created_at": 220,
            "webui": 190,
            "type": 130,
            "packages": 70,
            "extensions": 70,
            "filename": 310,
        }
        for column, heading in headings.items():
            self.snapshot_tree.heading(column, text=heading)
            self.snapshot_tree.column(column, width=widths[column], minwidth=60, anchor=tk.W)
        self.snapshot_tree.column("packages", anchor=tk.CENTER)
        self.snapshot_tree.column("extensions", anchor=tk.CENTER)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.snapshot_tree.yview)
        self.snapshot_tree.configure(yscrollcommand=scrollbar.set)
        self.snapshot_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.snapshot_tree.bind("<<TreeviewSelect>>", self._on_snapshot_selected)

        options = ttk.Frame(self.restore_tab)
        options.pack(fill=tk.X, padx=18, pady=(0, 8))
        ttk.Checkbutton(options, text="卸载快照外 Python 包", variable=self.prune_packages_var, command=self._invalidate_plan).pack(side=tk.LEFT)
        ttk.Checkbutton(options, text="删除快照外扩展", variable=self.prune_extensions_var, command=self._invalidate_plan).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Checkbutton(options, text="允许覆盖 Git 未提交变更", variable=self.force_git_reset_var, command=self._invalidate_plan).pack(side=tk.LEFT, padx=(12, 0))

        buttons = ttk.Frame(self.restore_tab)
        buttons.pack(fill=tk.X, padx=18, pady=(0, 8))
        self.preview_button = ttk.Button(buttons, text="查看变更", command=self.preview_restore, state=tk.DISABLED)
        self.preview_button.pack(side=tk.LEFT)
        self.restore_button = ttk.Button(buttons, text="恢复快照", command=self.restore_snapshot, state=tk.DISABLED)
        self.restore_button.pack(side=tk.LEFT, padx=(8, 0))
        self.delete_button = ttk.Button(buttons, text="删除快照", command=self.delete_snapshot, state=tk.DISABLED)
        self.delete_button.pack(side=tk.LEFT, padx=(8, 0))

        result_frame = ttk.Frame(self.restore_tab)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 18))
        self.result_text = tk.Text(result_frame, height=18, wrap=tk.WORD, state=tk.DISABLED)
        result_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=result_scrollbar.set)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        result_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        install_text_context_menu(self.result_text, editable=False)

    def set_status(self, message: str) -> None:
        """更新状态栏文本。

        Args:
            message (str):
                状态栏消息文本。
        """
        self.status_var.set(message)

    def set_busy_state(self, busy: bool) -> None:
        """切换界面忙碌状态。

        Args:
            busy (bool):
                是否进入忙碌状态。
        """
        if busy:
            self.busy_var.set("执行中")
            self.progress.start(12)
        else:
            self.busy_var.set("")
            self.progress.stop()

    def refresh_snapshot_list(self, show_message: bool = True) -> None:
        """刷新快照目录列表

        Args:
            show_message (bool):
                刷新后是否显示提示消息。
        """
        if not self.snapshot_dir.is_dir():
            self._clear_snapshot_list()
            self.snapshot_path_var.set("")
            self._invalidate_plan()
            self._set_snapshot_action_state(False)
            if show_message:
                messagebox.showwarning("快照目录不存在", f"快照目录不存在: {self.snapshot_dir}")
            else:
                self.set_status(f"快照目录不存在: {self.snapshot_dir}")
            return

        current_selection = self.snapshot_path_var.get().strip()
        self._clear_snapshot_list()
        for item in list_snapshot_files(self.snapshot_dir):
            item_id = item.path.as_posix()
            self.snapshot_list_items[item_id] = item
            self.snapshot_tree.insert(
                "",
                tk.END,
                iid=item_id,
                values=(
                    item.created_at_display,
                    item.webui_name,
                    item.webui_type,
                    item.package_count,
                    item.extension_count,
                    item.filename,
                ),
            )

        if current_selection and current_selection in self.snapshot_list_items:
            self._select_snapshot(Path(current_selection))
        else:
            self.snapshot_path_var.set("")
            self._invalidate_plan()
            self._set_snapshot_action_state(False)
        if show_message:
            self.set_status(f"已加载 {len(self.snapshot_list_items)} 个快照")

    def _clear_snapshot_list(self) -> None:
        for item_id in self.snapshot_tree.get_children():
            self.snapshot_tree.delete(item_id)
        self.snapshot_list_items.clear()

    def _on_snapshot_selected(self, _event: tk.Event | None = None) -> None:
        selection = self.snapshot_tree.selection()
        if not selection:
            return
        item = self.snapshot_list_items.get(selection[0])
        if item is None:
            return
        self.snapshot_path_var.set(item.path.as_posix())
        self._invalidate_plan()
        self._set_snapshot_action_state(True)
        self.set_status(f"已选择快照: {item.filename}")

    def _select_snapshot(self, path: Path) -> None:
        item_id = path.as_posix()
        if item_id not in self.snapshot_list_items:
            return
        self.snapshot_tree.selection_set(item_id)
        self.snapshot_tree.focus(item_id)
        self.snapshot_tree.see(item_id)
        self.snapshot_path_var.set(item_id)
        self._invalidate_plan()
        self._set_snapshot_action_state(True)

    def _restore_options(self) -> SnapshotRestoreOptions:
        return SnapshotRestoreOptions(
            prune_packages=bool(self.prune_packages_var.get()),
            prune_extensions=bool(self.prune_extensions_var.get()),
            force_git_reset=bool(self.force_git_reset_var.get()),
            use_uv=self.use_uv,
            use_pypi_mirror=self.use_pypi_mirror,
            use_github_mirror=self.use_github_mirror,
            custom_github_mirror=self.custom_github_mirror,
        )

    def _snapshot_path(self) -> Path | None:
        value = self.snapshot_path_var.get().strip()
        if not value:
            messagebox.showwarning("缺少快照文件", "请从快照列表选择快照文件")
            return None
        path = Path(value)
        if not path.is_file():
            messagebox.showwarning("快照文件不存在", f"快照文件不存在: {path}")
            return None
        return path

    def _invalidate_plan(self) -> None:
        self.current_plan = None

    def _set_delete_state(self, enabled: bool) -> None:
        self.delete_button.configure(state=tk.NORMAL if enabled else tk.DISABLED)

    def _set_snapshot_action_state(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        self.preview_button.configure(state=state)
        self.restore_button.configure(state=state)
        self._set_delete_state(enabled)

    def create_snapshot(self) -> None:
        """创建新的 WebUI 环境快照。"""
        def _task() -> tuple[WebUiSnapshot, Path]:
            snapshot = self.snapshot_factory(bool(self.include_packages_var.get()))
            output_path = resolve_snapshot_output(snapshot, self.snapshot_dir)
            save_snapshot(snapshot, output_path)
            return snapshot, output_path

        self.run_background(
            "创建快照中...",
            _task,
            lambda result: self._show_create_result(result[0], result[1]),
        )

    def _show_create_result(self, snapshot: WebUiSnapshot, output: Path) -> None:
        self.refresh_snapshot_list(show_message=False)
        self._select_snapshot(output)
        lines = [
            "快照创建完成",
            f"输出文件: {output}",
            f"WebUI: {snapshot.webui.name} ({snapshot.webui.type})",
            f"Python: {snapshot.python.version}",
            f"Python packages: {len(snapshot.packages)}",
            f"内核: {'Git 仓库' if snapshot.kernel and snapshot.kernel.is_git_repo else '非 Git 仓库'}",
            f"扩展: {len(snapshot.extensions)}",
        ]
        self._set_result_text("\n".join(lines))
        messagebox.showinfo("创建完成", f"快照已保存到:\n{output}")

    def delete_snapshot(self) -> None:
        """删除当前选中的快照文件。"""
        snapshot_path = self._snapshot_path()
        if snapshot_path is None:
            return
        if not messagebox.askyesno("确认删除", f"是否删除快照文件?\n{snapshot_path}"):
            return
        try:
            snapshot_path.unlink()
        except OSError as exc:
            messagebox.showerror("删除失败", f"删除快照失败:\n{exc}")
            return
        self.snapshot_path_var.set("")
        self._invalidate_plan()
        self._set_snapshot_action_state(False)
        self.refresh_snapshot_list(show_message=False)
        self._set_result_text("")
        self.set_status(f"已删除快照: {snapshot_path.name}")

    def preview_restore(self) -> None:
        """预览当前选中快照的恢复计划。"""
        snapshot_path = self._snapshot_path()
        if snapshot_path is None:
            return
        options = self._restore_options()
        self.run_background(
            "检查快照变更中...",
            lambda: preview_webui_snapshot_restore(
                snapshot_path=snapshot_path,
                webui_path=self.webui_path,
                expected_webui_type=self.webui_type,
                options=options,
            ),
            self._show_restore_plan,
        )

    def _show_restore_plan(self, plan: SnapshotRestorePlan) -> None:
        self.current_plan = plan
        self._set_result_text(self._format_restore_plan(plan))

    def restore_snapshot(self) -> None:
        """恢复当前选中的快照。"""
        snapshot_path = self._snapshot_path()
        if snapshot_path is None:
            return
        options = self._restore_options()
        self.run_background(
            "检查快照恢复中...",
            lambda: preview_webui_snapshot_restore(
                snapshot_path=snapshot_path,
                webui_path=self.webui_path,
                expected_webui_type=self.webui_type,
                options=options,
            ),
            lambda plan: self._confirm_restore_plan(snapshot_path, options, plan),
        )

    def _confirm_restore_plan(self, snapshot_path: Path, options: SnapshotRestoreOptions, plan: SnapshotRestorePlan) -> None:
        self._show_restore_plan(plan)
        if plan.errors:
            messagebox.showwarning("无法恢复", format_restore_blocking_message(plan))
            return
        confirm_message = "将按结果框中的变更恢复快照, 是否继续?"
        if options.prune_packages or options.prune_extensions or options.force_git_reset:
            confirm_message = "当前恢复选项包含清理或强制覆盖操作, 将按结果框中的变更恢复快照, 是否继续?"
        if not messagebox.askyesno("确认恢复", confirm_message):
            return

        self.run_background(
            "恢复快照中...",
            lambda: restore_webui_snapshot(
                snapshot_path=snapshot_path,
                webui_path=self.webui_path,
                expected_webui_type=self.webui_type,
                options=options,
            ),
            lambda _value: self._restore_finished(),
        )

    def _restore_finished(self) -> None:
        messagebox.showinfo("恢复完成", "快照恢复完成")
        self.preview_restore()

    def _set_result_text(self, text: str) -> None:
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, text)
        self.result_text.configure(state=tk.DISABLED)

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
            guidance = build_restore_blocking_guidance(plan)
            if guidance:
                lines.append("")
                lines.append("处理建议:")
                lines.extend(f"- {item}" for item in guidance)

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
    snapshot_dir: Path | None = None,
) -> None:
    """启动 WebUI 快照管理 GUI

    Args:
        title (str):
            GUI 窗口标题。
        webui_type (str):
            WebUI 类型标识。
        webui_path (Path):
            WebUI 根目录。
        snapshot_factory (SnapshotFactory):
            创建快照对象的回调。
        use_uv (bool):
            是否使用 uv 执行 Python 包安装。
        use_pypi_mirror (bool):
            是否使用 PyPI 镜像源。
        use_github_mirror (bool):
            是否使用 GitHub 镜像源。
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源。
        snapshot_dir (Path | None):
            快照文件目录。
    """
    app = SnapshotManagerApp(
        title=title,
        webui_type=webui_type,
        webui_path=webui_path,
        snapshot_factory=snapshot_factory,
        use_uv=use_uv,
        use_pypi_mirror=use_pypi_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        snapshot_dir=snapshot_dir,
    )
    app.mainloop()
