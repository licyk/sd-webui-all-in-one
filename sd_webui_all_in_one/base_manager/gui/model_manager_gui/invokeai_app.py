"""Implementation grouped from the former ``model_manager_gui.py`` module."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    AdaptiveIndexList,
    BackgroundTaskMixin,
    apply_gui_theme,
    apply_window_icon,
    configure_gui_fonts,
)
from sd_webui_all_in_one.base_manager.model_manager import (
    InvokeAIModelManager,
)


class InvokeAIModelManagerApp(tk.Tk, BackgroundTaskMixin):
    """InvokeAI 专用模型管理 GUI"""

    def __init__(
        self,
        invokeai_path: Path,
        title: str,
    ) -> None:
        tk.Tk.__init__(self)
        BackgroundTaskMixin.__init__(self)
        self.manager = InvokeAIModelManager(invokeai_path=invokeai_path)
        self.model_items: dict[str, dict[str, Any]] = {}

        self.title(f"{title} 模型管理")
        apply_window_icon(self)
        self.geometry("1180x720")
        self.minsize(900, 560)
        self._create_styles()
        self._create_widgets()
        self._install_task_poller(self)
        self.refresh_models()

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
        ttk.Label(top, text=f"InvokeAI 根目录: {self.manager.invokeai_path}").pack(side=tk.LEFT, padx=10, pady=8)
        ttk.Button(top, text="刷新", command=self.refresh_models).pack(side=tk.RIGHT, padx=(0, 10), pady=8)

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=10, pady=(0, 8))
        for text, command in (
            ("从 URL 安装", self.install_from_url),
            ("导入文件", self.import_files),
            ("导入文件夹", self.import_folder),
            ("删除/注销", self.unregister_selected),
        ):
            ttk.Button(toolbar, text=text, command=command).pack(side=tk.LEFT, padx=(0, 8))

        loading_frame = ttk.Frame(self)
        loading_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.loading_status_var = tk.StringVar(value="模型列表就绪")
        ttk.Label(loading_frame, textvariable=self.loading_status_var, anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.loading_progress = ttk.Progressbar(loading_frame, mode="indeterminate", length=220)
        self.loading_progress.pack(side=tk.RIGHT)

        columns = ("name", "type", "base", "path", "id", "description")
        self.model_tree = AdaptiveIndexList(
            self,
            columns=columns,
            headings={"name": "名称", "type": "类型", "base": "基底", "path": "路径", "id": "ID", "description": "描述"},
            widths={"name": 220, "type": 130, "base": 120, "path": 360, "id": 220, "description": 260},
        )
        self.model_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

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
        self.loading_status_var.set(message)

    def set_busy_state(self, busy: bool) -> None:
        """切换耗时任务状态展示

        Args:
            busy (bool):
                是否正在执行后台任务。
        """
        if busy:
            self.busy_var.set("执行中")
            self.progress.start(12)
            self.loading_progress.start(12)
            self.update_idletasks()
        else:
            self.busy_var.set("")
            self.progress.stop()
            self.loading_progress.stop()
            self.loading_status_var.set("模型列表就绪")

    def refresh_models(self) -> None:
        """刷新 InvokeAI 已注册模型列表"""

        self.run_background("正在导入 InvokeAI 模块并读取模型列表...", self.manager.list_models, self._apply_models)

    def _apply_models(self, models: list[dict[str, Any]]) -> None:
        self.model_tree.clear()
        self.model_items.clear()
        for index, model in enumerate(models):
            item_id = f"model:{index}"
            self.model_tree.insert(
                item_id,
                (
                    str(model.get("name", "")),
                    str(model.get("type", "")),
                    str(model.get("base", "")),
                    str(model.get("path", "")),
                    str(model.get("id", "")),
                    str(model.get("description") or ""),
                ),
            )
            self.model_items[item_id] = model
        self.set_status(f"已加载 {len(models)} 个 InvokeAI 模型")

    def _selected_model(self) -> dict[str, Any] | None:
        selection = self.model_tree.selection()
        if not selection:
            messagebox.showwarning("请选择模型", "请先选择一个 InvokeAI 模型", parent=self)
            return None
        return self.model_items.get(selection[0])

    def _selected_model_id(self) -> str | None:
        model = self._selected_model()
        if model is None:
            return None
        model_id = str(model.get("id") or "")
        if not model_id:
            messagebox.showerror("模型无效", "选中的模型缺少 ID，无法操作", parent=self)
            return None
        return model_id

    def _after_operation(self, success: bool) -> None:
        if not success:
            messagebox.showerror("操作失败", "InvokeAI 模型操作失败", parent=self)
            return
        self.refresh_models()

    def install_from_url(self) -> None:
        """通过 InvokeAI 模型管理器从 URL 安装模型"""

        url = simpledialog.askstring("从 URL 安装", "模型下载链接", parent=self)
        if not url:
            return
        self.run_background(
            "通过 InvokeAI 安装模型中...",
            lambda: self.manager.install_from_url(url.strip()),
            self._after_operation,
        )

    def import_files(self) -> None:
        """复制并导入一个或多个本地模型文件到 InvokeAI"""

        selected = filedialog.askopenfilenames(title="选择要导入的模型文件", parent=self)
        if not selected:
            return
        paths = [Path(item) for item in selected]
        self.run_background(
            "复制并导入 InvokeAI 模型中...",
            lambda: self.manager.import_local_paths(paths),
            self._after_operation,
        )

    def import_folder(self) -> None:
        """复制并导入一个本地模型文件夹到 InvokeAI"""

        selected = filedialog.askdirectory(title="选择要导入的模型文件夹", parent=self)
        if not selected:
            return
        self.run_background(
            "复制并导入 InvokeAI 模型中...",
            lambda: self.manager.import_local_paths([Path(selected)]),
            self._after_operation,
        )

    def unregister_selected(self) -> None:
        """注销当前选中的 InvokeAI 模型并保留文件"""

        model_id = self._selected_model_id()
        if model_id is None:
            return
        if not messagebox.askyesno(
            "确认注销",
            (f"将通过 InvokeAI 移除模型记录并保留模型文件。\n\n模型 ID: {model_id}\n\n是否继续？"),
            parent=self,
        ):
            return
        self.run_background(
            "注销 InvokeAI 模型中...",
            lambda: self.manager.unregister(model_id),
            self._after_operation,
        )

    def delete_selected(self) -> None:
        """删除当前选中的 InvokeAI 模型记录和文件"""

        model_id = self._selected_model_id()
        if model_id is None:
            return
        if not messagebox.askyesno("确认永久删除", f"将通过 InvokeAI 删除模型记录，并在允许时删除模型文件。\n\n模型 ID: {model_id}\n\n是否继续？", parent=self):
            return
        self.run_background(
            "删除 InvokeAI 模型中...",
            lambda: self.manager.delete(model_id),
            self._after_operation,
        )
