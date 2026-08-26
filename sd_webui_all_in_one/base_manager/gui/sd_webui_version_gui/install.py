"""Install behavior for the product version window."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import (
    messagebox,
    ttk,
)
from sd_webui_all_in_one.base_manager.sd_webui_base import (
    set_sd_webui_extension_download_list_mirror,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    DEFAULT_EXTENSION_INDEX_URL,
    ExtensionIndexItem,
    fetch_extension_index,
    filter_extension_index,
)
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    AdaptiveIndexList,
    EnhancedEntry,
)


from sd_webui_all_in_one.base_manager.gui.version_gui import GuiActionsMixinContext


class InstallActionsMixin(GuiActionsMixinContext):
    def _create_install_tab(
        self,
    ) -> None:
        toolbar = ttk.Frame(self.install_tab)
        toolbar.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(toolbar, text="刷新扩展源", command=self.refresh_extension_index).pack(side=tk.LEFT)
        self.tag_var = tk.StringVar(value="全部分类")
        self.tag_combo = ttk.Combobox(toolbar, textvariable=self.tag_var, state="readonly", values=("全部分类",), width=18)
        self.tag_combo.pack(side=tk.LEFT, padx=(8, 0))
        self.tag_combo.bind("<<ComboboxSelected>>", lambda _event: self.render_extension_index())

        self.index_tree = AdaptiveIndexList(
            self.install_tab,
            columns=("name", "description", "tags", "url"),
            headings={"name": "插件名", "description": "简介", "tags": "分类", "url": "地址"},
            widths={"name": 240, "description": 560, "tags": 180, "url": 420},
            search_placeholder="搜索新插件...",
        )
        self.index_tree.pack(fill=tk.BOTH, expand=True)
        self.index_tree.bind_search_change(self.render_extension_index)
        self.index_tree.bind_double_click(self.install_selected_index_extension)

        bottom = ttk.Frame(self.install_tab)
        bottom.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.install_url_var = tk.StringVar()
        self.install_url_placeholder = "输入扩展 Git URL，例如 https://github.com/user/extension"
        install_url_entry = EnhancedEntry(bottom, textvariable=self.install_url_var, placeholder=self.install_url_placeholder)
        install_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(bottom, text="安装 URL", command=self.install_from_url).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(bottom, text="安装选中", command=self.install_selected_index_extension).pack(side=tk.LEFT, padx=(8, 0))

    def _configure_extension_index_url(self) -> str:
        if not self.use_github_mirror:
            return DEFAULT_EXTENSION_INDEX_URL
        env = set_sd_webui_extension_download_list_mirror(
            custom_github_mirror=self.custom_github_mirror,
            origin_env=self.git_env,
        )
        self.git_env = env
        extension_index_url = env.get("WEBUI_EXTENSIONS_INDEX", DEFAULT_EXTENSION_INDEX_URL)
        os.environ["WEBUI_EXTENSIONS_INDEX"] = extension_index_url
        return extension_index_url

    def refresh_extension_index(
        self,
    ) -> None:
        """
        刷新扩展源列表
        """
        self.run_background("刷新扩展源中...", lambda: fetch_extension_index(self.extension_index_url), self._apply_extension_index)

    def _apply_extension_index(
        self,
        items: list[ExtensionIndexItem],
    ) -> None:
        self.extension_index = items
        tags = sorted({tag for item in items for tag in item.tags})
        self.tag_combo.configure(values=("全部分类", *tags))
        if self.tag_var.get() not in ("全部分类", *tags):
            self.tag_var.set("全部分类")
        self.render_extension_index()

    def render_extension_index(
        self,
    ) -> None:
        """
        渲染扩展源列表
        """
        keyword = self.index_tree.search_keyword()
        tag = self.tag_var.get()
        tags = [] if tag == "全部分类" else [tag]
        installed_names = {ext.name for ext in self.extensions}
        self.filtered_extension_index = filter_extension_index(self.extension_index, keyword, tags)
        self.index_tree.clear()
        for item in self.filtered_extension_index:
            status = "已装" if item.name in installed_names else item.url
            self.index_tree.insert(item.url, (item.name, item.description, ", ".join(item.tags), status))

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
        从 Git URL 安装扩展
        """
        url = self.install_url_var.get().strip()
        if url == self.install_url_placeholder:
            url = ""
        if not url:
            messagebox.showwarning("请输入 URL", "请先输入扩展 Git URL")
            return
        self._install_extension_url(url)

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

    def install_selected_index_extension(
        self,
    ) -> None:
        """
        安装当前选中的扩展源条目
        """
        selected_id = self.index_tree.selected_item_id()
        if not selected_id:
            messagebox.showwarning("请选择扩展", "请先选择扩展源中的插件")
            return
        self._install_extension_url(selected_id)

    def _install_extension_url(
        self,
        url: str,
    ) -> None:
        """
        安装指定 Git URL 的扩展

        Args:
            url (str):
                Git 仓库地址
        """
        self.run_background(
            "安装扩展中...",
            lambda: self.extension_manager.install_extension(url, self.use_github_mirror, self.custom_github_mirror),
            lambda _value: (self.install_url_var.set(self.install_url_placeholder), self.refresh_extensions()),
        )
