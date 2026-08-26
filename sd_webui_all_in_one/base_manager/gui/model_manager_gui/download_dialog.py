"""Implementation grouped from the former ``model_manager_gui.py`` module."""

from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import TypedDict, cast
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    apply_window_icon,
)
from sd_webui_all_in_one.base_manager.model_manager import (
    FileModelManager,
)
from sd_webui_all_in_one.downloader import DOWNLOAD_TOOL_TYPE_LIST, DownloadToolType


class DownloadDialogResult(TypedDict):
    """模型下载弹窗返回的参数"""

    url: str
    target: str
    save_name: str | None
    downloader: DownloadToolType | None


def _download_tool_from_value(value: str) -> DownloadToolType | None:
    if value not in DOWNLOAD_TOOL_TYPE_LIST:
        return None
    return cast(DownloadToolType, value)


def _format_size(size: int) -> str:
    if size <= 0:
        return "-"
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size)
    unit = units[0]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            break
        value /= 1024
    if unit == "B":
        return f"{int(value)} {unit}"
    return f"{value:.2f} {unit}"


def _format_time(timestamp: float) -> str:
    if timestamp <= 0:
        return "-"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


class DownloadModelDialog(tk.Toplevel):
    """模型下载参数弹窗"""

    def __init__(
        self,
        master: tk.Misc,
        manager: FileModelManager,
        webui_path: Path,
        target_dir: str,
    ) -> None:
        super().__init__(master)
        self.manager = manager
        self.webui_path = webui_path
        self.result: DownloadDialogResult | None = None
        self.title("下载模型")
        apply_window_icon(self)
        self.resizable(False, False)
        if isinstance(master, (tk.Tk, tk.Toplevel)):
            self.transient(master)
        self.grab_set()

        self.url_var = tk.StringVar()
        self.target_var = tk.StringVar(value=target_dir)
        self.save_name_var = tk.StringVar()
        self.downloader_var = tk.StringVar(value="requests")

        body = ttk.Frame(self, padding=14)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="下载链接").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(body, textvariable=self.url_var, width=70).grid(row=0, column=1, sticky=tk.EW, pady=5)

        ttk.Label(body, text="目标文件夹").grid(row=1, column=0, sticky=tk.W, pady=5)
        target_frame = ttk.Frame(body)
        target_frame.grid(row=1, column=1, sticky=tk.EW, pady=5)
        target_frame.columnconfigure(0, weight=1)
        ttk.Entry(target_frame, textvariable=self.target_var).grid(row=0, column=0, sticky=tk.EW)
        ttk.Button(target_frame, text="选择", command=self._browse_target).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(body, text="保存文件名").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(body, textvariable=self.save_name_var).grid(row=2, column=1, sticky=tk.EW, pady=5)

        ttk.Label(body, text="下载器").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Combobox(
            body,
            textvariable=self.downloader_var,
            values=DOWNLOAD_TOOL_TYPE_LIST,
            state="readonly",
            width=18,
        ).grid(row=3, column=1, sticky=tk.W, pady=5)

        buttons = ttk.Frame(body)
        buttons.grid(row=4, column=0, columnspan=2, sticky=tk.E, pady=(12, 0))
        ttk.Button(buttons, text="取消", command=self.destroy).pack(side=tk.RIGHT)
        ttk.Button(buttons, text="下载", command=self._accept).pack(side=tk.RIGHT, padx=(0, 8))

        self.bind("<Return>", lambda _event: self._accept())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.wait_visibility()
        self.focus_force()

    def _browse_target(self) -> None:
        selected = filedialog.askdirectory(
            title="选择模型保存文件夹",
            initialdir=self.manager.resolve_path(self.webui_path, self.target_var.get()).as_posix(),
            parent=self,
        )
        if not selected:
            return
        try:
            self.target_var.set(self.manager.relative_to_root(self.webui_path, selected))
        except Exception as exc:
            messagebox.showerror("路径无效", str(exc), parent=self)

    def _accept(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("请输入链接", "请先输入模型下载链接", parent=self)
            return
        try:
            self.manager.resolve_path(self.webui_path, self.target_var.get())
            save_name = self.save_name_var.get().strip() or None
            if save_name is not None:
                self.manager.validate_name(save_name)
        except Exception as exc:
            messagebox.showerror("参数无效", str(exc), parent=self)
            return

        self.result = {
            "url": url,
            "target": self.target_var.get().strip() or ".",
            "save_name": save_name,
            "downloader": _download_tool_from_value(self.downloader_var.get()),
        }
        self.destroy()
