"""Install behavior for the product version window."""

from __future__ import annotations

import tkinter as tk
from tkinter import (
    messagebox,
    ttk,
)
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    EnhancedEntry,
)


from sd_webui_all_in_one.base_manager.gui.version_gui import GuiActionsMixinContext


class InstallActionsMixin(GuiActionsMixinContext):
    def _create_install_tab(
        self,
    ) -> None:
        panel = ttk.Frame(self.install_tab)
        panel.pack(fill=tk.X, padx=18, pady=18)
        ttk.Label(panel, text="扩展 Git URL:").pack(side=tk.LEFT)
        self.install_url_var = tk.StringVar()
        self.install_url_placeholder = "输入 InvokeAI 扩展 Git URL，例如 https://github.com/user/invokeai-node"
        entry = EnhancedEntry(panel, textvariable=self.install_url_var, placeholder=self.install_url_placeholder)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        ttk.Button(panel, text="安装", command=self.install_from_url).pack(side=tk.LEFT)

    def uninstall_selected_extension(
        self,
    ) -> None:
        """
        卸载当前选中的扩展
        """
        ext = self._selected_extension()
        if ext is None:
            return
        if not messagebox.askyesno("确认卸载", f"确认卸载扩展 '{ext.name}' 吗？"):
            return
        self.run_background("卸载扩展中...", lambda: self.extension_manager.uninstall_extension(ext.name), lambda _value: self.refresh_extensions())

    def install_from_url(
        self,
    ) -> None:
        """
        从 Git URL 安装 InvokeAI 扩展
        """
        url = self.install_url_var.get().strip()
        if url == self.install_url_placeholder:
            url = ""
        if not url:
            messagebox.showwarning("请输入 URL", "请先输入 InvokeAI 扩展 Git URL")
            return
        self.run_background(
            "安装扩展中...",
            lambda: self.extension_manager.install_extension(url, self.use_github_mirror, self.custom_github_mirror),
            lambda _value: (self.install_url_var.set(self.install_url_placeholder), self.refresh_extensions()),
        )

    def _clear_install_url_placeholder(
        self,
        _event,
    ) -> None:
        if self.install_url_var.get() == self.install_url_placeholder:
            self.install_url_var.set("")

    def _restore_install_url_placeholder(
        self,
        _event,
    ) -> None:
        if not self.install_url_var.get().strip():
            self.install_url_var.set(self.install_url_placeholder)
