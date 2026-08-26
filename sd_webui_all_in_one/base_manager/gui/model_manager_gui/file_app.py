"""Implementation grouped from the former ``model_manager_gui.py`` module."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    BackgroundTaskMixin,
    apply_gui_theme,
    apply_window_icon,
    configure_gui_fonts,
)
from sd_webui_all_in_one.base_manager.model_manager import (
    FileModelManager,
    FileWebUiModelType,
    ModelEntry,
)

from .download_dialog import DownloadModelDialog, _format_size, _format_time


class FileModelManagerApp(tk.Tk, BackgroundTaskMixin):
    """按文件夹管理模型的 GUI"""

    def __init__(
        self,
        webui_type: FileWebUiModelType,
        webui_path: Path,
        title: str,
    ) -> None:
        tk.Tk.__init__(self)
        BackgroundTaskMixin.__init__(self)
        self.manager = FileModelManager(webui_type=webui_type)
        self.webui_path = webui_path
        self.current_dir = "."
        self.dir_items: dict[str, str] = {}
        self.entry_items: dict[str, ModelEntry] = {}

        self.title(f"{title} 模型管理")
        apply_window_icon(self)
        self.geometry("1180x720")
        self.minsize(900, 560)
        self._create_styles()
        self._create_widgets()
        self._install_task_poller(self)
        self.refresh_all()

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
        ttk.Label(top, text=f"模型目录: {self.manager.root_path(self.webui_path)}").pack(side=tk.LEFT, padx=10, pady=8)
        ttk.Button(top, text="刷新", command=self.refresh_all).pack(side=tk.RIGHT, padx=(0, 10), pady=8)

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=10, pady=(0, 8))
        for text, command in (
            ("新建文件夹", self.create_folder),
            ("复制", self.copy_selected),
            ("移动", self.move_selected),
            ("删除", self.delete_selected),
            ("导入文件", self.import_files),
            ("导入文件夹", self.import_folder),
            ("下载", self.download_model),
        ):
            ttk.Button(toolbar, text=text, command=command).pack(side=tk.LEFT, padx=(0, 8))

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10)

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=3)

        self.dir_tree = ttk.Treeview(left, show="tree", selectmode="browse")
        dir_scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.dir_tree.yview)
        self.dir_tree.configure(yscrollcommand=dir_scroll.set)
        self.dir_tree.grid(row=0, column=0, sticky="nsew")
        dir_scroll.grid(row=0, column=1, sticky="ns")
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)
        self.dir_tree.bind("<<TreeviewSelect>>", self._on_directory_selected)

        columns = ("type", "size", "modified", "path")
        self.entry_tree = ttk.Treeview(right, columns=columns, show="tree headings", selectmode="browse")
        self.entry_tree.heading("#0", text="名称")
        self.entry_tree.heading("type", text="类型")
        self.entry_tree.heading("size", text="大小")
        self.entry_tree.heading("modified", text="修改时间")
        self.entry_tree.heading("path", text="相对路径")
        self.entry_tree.column("#0", width=260, stretch=True)
        self.entry_tree.column("type", width=90, anchor=tk.CENTER, stretch=False)
        self.entry_tree.column("size", width=110, anchor=tk.E, stretch=False)
        self.entry_tree.column("modified", width=170, stretch=False)
        self.entry_tree.column("path", width=360, stretch=True)
        entry_scroll = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.entry_tree.yview)
        self.entry_tree.configure(yscrollcommand=entry_scroll.set)
        self.entry_tree.grid(row=0, column=0, sticky="nsew")
        entry_scroll.grid(row=0, column=1, sticky="ns")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)
        self.entry_tree.bind("<Double-1>", self._open_selected_directory)

        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel", anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.busy_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.busy_var, width=10, anchor=tk.CENTER).pack(side=tk.RIGHT, padx=(0, 8))
        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=180)
        self.progress.pack(side=tk.RIGHT, padx=(0, 8), pady=4)

    def set_status(self, message: str) -> None:
        """设置底部状态栏文本

        Args:
            message (str):
                要显示的状态消息。
        """
        self.status_var.set(message)

    def set_busy_state(self, busy: bool) -> None:
        """切换耗时任务状态展示

        Args:
            busy (bool):
                是否正在执行后台任务。
        """
        if busy:
            self.busy_var.set("执行中")
            self.progress.start(12)
        else:
            self.busy_var.set("")
            self.progress.stop()

    def refresh_all(self) -> None:
        """刷新模型目录树和当前目录条目"""

        def _load() -> tuple[list[str], list[ModelEntry]]:
            return self.manager.list_directories(self.webui_path), self.manager.list_entries(self.webui_path, self.current_dir)

        self.run_background("刷新模型列表中...", _load, self._apply_state)

    def refresh_entries(self) -> None:
        """刷新当前模型目录条目"""

        self.run_background("刷新当前目录中...", lambda: self.manager.list_entries(self.webui_path, self.current_dir), self._apply_entries)

    def _apply_state(self, state: tuple[list[str], list[ModelEntry]]) -> None:
        directories, entries = state
        self.dir_tree.delete(*self.dir_tree.get_children(""))
        self.dir_items.clear()
        for directory in directories:
            item_id = f"dir:{directory}"
            parent = "" if directory == "." else f"dir:{Path(directory).parent.as_posix() if Path(directory).parent.as_posix() != '.' else '.'}"
            text = "/" if directory == "." else Path(directory).name
            try:
                self.dir_tree.insert(parent, tk.END, iid=item_id, text=text, open=directory in {".", self.current_dir})
            except tk.TclError:
                continue
            self.dir_items[item_id] = directory
        if f"dir:{self.current_dir}" in self.dir_items:
            self.dir_tree.selection_set(f"dir:{self.current_dir}")
            self.dir_tree.see(f"dir:{self.current_dir}")
        self._apply_entries(entries)

    def _apply_entries(self, entries: list[ModelEntry]) -> None:
        self.entry_tree.delete(*self.entry_tree.get_children(""))
        self.entry_items.clear()
        for entry in entries:
            item_id = f"entry:{entry.relative_path}"
            self.entry_tree.insert(
                "",
                tk.END,
                iid=item_id,
                text=entry.name,
                values=(
                    "文件夹" if entry.is_dir else "文件",
                    _format_size(entry.size),
                    _format_time(entry.modified_time),
                    entry.relative_path,
                ),
            )
            self.entry_items[item_id] = entry
        self.set_status(f"当前目录: {self.current_dir}")

    def _on_directory_selected(self, _event: tk.Event) -> None:
        selection = self.dir_tree.selection()
        if not selection:
            return
        relative_path = self.dir_items.get(selection[0])
        if relative_path is None or relative_path == self.current_dir:
            return
        self.current_dir = relative_path
        self.refresh_entries()

    def _selected_entry(self) -> ModelEntry | None:
        selection = self.entry_tree.selection()
        if not selection:
            messagebox.showwarning("请选择条目", "请先选择一个模型文件或文件夹", parent=self)
            return None
        return self.entry_items.get(selection[0])

    def _open_selected_directory(self, _event: tk.Event) -> None:
        entry = self._selected_entry()
        if entry is None or not entry.is_dir:
            return
        self.current_dir = entry.relative_path
        self.refresh_all()

    def _ask_target_directory(self) -> str | None:
        selected = filedialog.askdirectory(
            title="选择目标模型文件夹",
            initialdir=self.manager.resolve_path(self.webui_path, self.current_dir).as_posix(),
            parent=self,
        )
        if not selected:
            return None
        try:
            return self.manager.relative_to_root(self.webui_path, selected)
        except Exception as exc:
            messagebox.showerror("目标无效", str(exc), parent=self)
            return None

    def _ask_overwrite(self, target_dir: str, names: list[str]) -> bool | None:
        collisions = [name for name in names if (self.manager.resolve_path(self.webui_path, target_dir) / name).exists()]
        if not collisions:
            return False
        preview = "\n".join(collisions[:8])
        if len(collisions) > 8:
            preview += f"\n... 共 {len(collisions)} 项"
        if messagebox.askyesno("目标已存在", f"以下目标已存在，是否覆盖或合并？\n\n{preview}", parent=self):
            return True
        return None

    def create_folder(self) -> None:
        """在当前模型目录中新建文件夹"""

        name = simpledialog.askstring("新建文件夹", "文件夹名称", parent=self)
        if not name:
            return
        self.run_background(
            "创建文件夹中...",
            lambda: self.manager.create_folder(self.webui_path, self.current_dir, name),
            lambda _value: self.refresh_all(),
        )

    def copy_selected(self) -> None:
        """复制当前选中的模型文件或文件夹"""

        entry = self._selected_entry()
        if entry is None:
            return
        target_dir = self._ask_target_directory()
        if target_dir is None:
            return
        overwrite = self._ask_overwrite(target_dir, [entry.name])
        if overwrite is None:
            return
        self.run_background(
            "复制模型中...",
            lambda: self.manager.copy_entry(self.webui_path, entry.relative_path, target_dir, overwrite=overwrite),
            lambda _value: self.refresh_all(),
        )

    def move_selected(self) -> None:
        """移动当前选中的模型文件或文件夹"""

        entry = self._selected_entry()
        if entry is None:
            return
        target_dir = self._ask_target_directory()
        if target_dir is None:
            return
        overwrite = self._ask_overwrite(target_dir, [entry.name])
        if overwrite is None:
            return
        self.run_background(
            "移动模型中...",
            lambda: self.manager.move_entry(self.webui_path, entry.relative_path, target_dir, overwrite=overwrite),
            lambda _value: self.refresh_all(),
        )

    def delete_selected(self) -> None:
        """永久删除当前选中的模型文件或文件夹"""

        entry = self._selected_entry()
        if entry is None:
            return
        if not messagebox.askyesno("确认永久删除", f"将永久删除以下路径:\n{entry.path}\n\n是否继续？", parent=self):
            return
        self.run_background(
            "删除模型中...",
            lambda: self.manager.delete_entry(self.webui_path, entry.relative_path),
            lambda _value: self.refresh_all(),
        )

    def import_files(self) -> None:
        """复制导入一个或多个本地模型文件"""

        selected = filedialog.askopenfilenames(title="选择要导入的模型文件", parent=self)
        if not selected:
            return
        paths = [Path(item) for item in selected]
        overwrite = self._ask_overwrite(self.current_dir, [path.name for path in paths])
        if overwrite is None:
            return
        self.run_background(
            "导入模型文件中...",
            lambda: self.manager.import_paths(self.webui_path, paths, self.current_dir, overwrite=overwrite),
            lambda _value: self.refresh_all(),
        )

    def import_folder(self) -> None:
        """复制导入一个本地模型文件夹"""

        selected = filedialog.askdirectory(title="选择要导入的模型文件夹", parent=self)
        if not selected:
            return
        path = Path(selected)
        overwrite = self._ask_overwrite(self.current_dir, [path.name])
        if overwrite is None:
            return
        self.run_background(
            "导入模型文件夹中...",
            lambda: self.manager.import_paths(self.webui_path, [path], self.current_dir, overwrite=overwrite),
            lambda _value: self.refresh_all(),
        )

    def download_model(self) -> None:
        """下载模型到当前选择的模型目录"""

        dialog = DownloadModelDialog(self, self.manager, self.webui_path, self.current_dir)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        data = dialog.result
        self.run_background(
            "下载模型中...",
            lambda: self.manager.download_url(
                webui_path=self.webui_path,
                url=str(data["url"]),
                target_dir_relative_path=str(data["target"] or "."),
                save_name=str(data["save_name"]) if data["save_name"] else None,
                downloader=data["downloader"],
            ),
            lambda _value: self.refresh_all(),
        )
