"""Install behavior for the product version window."""

from __future__ import annotations

import tkinter as tk
from tkinter import (
    messagebox,
    ttk,
)
from sd_webui_all_in_one.base_manager.base import get_repo_name_from_url
from sd_webui_all_in_one.base_manager.comfy_registry import (
    fetch_comfy_registry_extension_index,
)
from sd_webui_all_in_one.base_manager.comfyui_base import (
    set_comfyui_custom_node_list_mirror,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    ExtensionIndexItem,
    fetch_comfyui_custom_node_index,
    filter_extension_index,
)
from sd_webui_all_in_one.downloader import (
    download_archive_and_unpack,
    download_file,
)
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    AdaptiveIndexList,
    EnhancedEntry,
)

from .helpers import COMFYUI_CUSTOM_NODE_INDEX_URL, _download_name_from_url, _format_index_tags


from sd_webui_all_in_one.base_manager.gui.version_gui import GuiActionsMixinContext


class InstallActionsMixin(GuiActionsMixinContext):
    def _configure_extension_index_url(self) -> str:
        if not self.use_github_mirror:
            return COMFYUI_CUSTOM_NODE_INDEX_URL
        extension_index_url = set_comfyui_custom_node_list_mirror(
            custom_github_mirror=self.custom_github_mirror,
        )
        return extension_index_url or COMFYUI_CUSTOM_NODE_INDEX_URL

    def _create_install_tab(
        self,
    ) -> None:
        toolbar = ttk.Frame(self.install_tab)
        toolbar.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(toolbar, text="刷新节点源", command=lambda: self.refresh_extension_index(force_refresh=True)).pack(side=tk.LEFT)
        self.tag_var = tk.StringVar(value="全部分类")
        self.tag_combo = ttk.Combobox(toolbar, textvariable=self.tag_var, state="readonly", values=("全部分类",), width=18)
        self.tag_combo.pack(side=tk.LEFT, padx=(8, 0))
        self.tag_combo.bind("<<ComboboxSelected>>", lambda _event: self.render_extension_index())

        self.index_tree = AdaptiveIndexList(
            self.install_tab,
            columns=("name", "description", "source", "version", "type", "tags", "url"),
            headings={"name": "节点名", "description": "简介", "source": "来源", "version": "版本", "type": "安装方式", "tags": "分类/作者", "url": "地址"},
            widths={"name": 220, "description": 440, "source": 110, "version": 100, "type": 120, "tags": 170, "url": 360},
            search_placeholder="搜索新节点...",
        )
        self.index_tree.pack(fill=tk.BOTH, expand=True)
        self.index_tree.bind_search_change(self.render_extension_index)
        self.index_tree.bind_double_click(self.install_selected_index_extension)

        bottom = ttk.Frame(self.install_tab)
        bottom.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.install_url_var = tk.StringVar()
        self.install_url_placeholder = "输入自定义节点 Git URL，例如 https://github.com/user/ComfyUI-node"
        install_url_entry = EnhancedEntry(bottom, textvariable=self.install_url_var, placeholder=self.install_url_placeholder)
        install_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(bottom, text="安装 URL", command=self.install_from_url).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(bottom, text="安装选中", command=self.install_selected_index_extension).pack(side=tk.LEFT, padx=(8, 0))

    def refresh_extension_index(
        self,
        force_refresh: bool = False,
    ) -> None:
        """
        刷新自定义节点源列表

        Args:
            force_refresh (bool):
                是否强制忽略 Comfy Registry 内存缓存。
        """
        self._extension_index_generation += 1
        generation = self._extension_index_generation
        self._manager_extension_index = []
        self._registry_extension_index = []

        def _apply_manager_items(items: list[ExtensionIndexItem]) -> None:
            self._apply_manager_extension_index(generation, items, force_refresh)

        self.run_background("刷新 ComfyUI-Manager 节点源中...", lambda: fetch_comfyui_custom_node_index(self.extension_index_url), _apply_manager_items)

    def _apply_manager_extension_index(
        self,
        generation: int,
        items: list[ExtensionIndexItem],
        force_refresh: bool = False,
    ) -> None:
        if generation != self._extension_index_generation:
            return
        self._manager_extension_index = items
        self._apply_extension_index([*self._manager_extension_index])
        self._refresh_registry_extension_index(generation, force_refresh)

    def _refresh_registry_extension_index(
        self,
        generation: int,
        force_refresh: bool = False,
    ) -> None:
        def _progress(loaded: int, total: int | None) -> None:
            self.after(0, lambda loaded=loaded, total=total: self._apply_registry_extension_index_progress(generation, loaded, total))

        def _apply_registry_items(items: list[ExtensionIndexItem]) -> None:
            self._apply_registry_extension_index(generation, items)

        def _handle_registry_error(error: BaseException) -> None:
            self._handle_registry_extension_index_error(generation, error)

        self.run_background(
            "加载 Comfy Registry 节点源中...",
            lambda: fetch_comfy_registry_extension_index(limit=None, page_size=500, force_refresh=force_refresh, progress_callback=_progress),
            _apply_registry_items,
            _handle_registry_error,
        )

    def _apply_registry_extension_index_progress(
        self,
        generation: int,
        loaded: int,
        total: int | None,
    ) -> None:
        if generation != self._extension_index_generation:
            return
        total_text = str(total) if total is not None else "?"
        self.set_status(f"Comfy Registry 加载中: {loaded}/{total_text}")

    def _apply_registry_extension_index(
        self,
        generation: int,
        items: list[ExtensionIndexItem],
    ) -> None:
        if generation != self._extension_index_generation:
            return
        self._registry_extension_index = items
        self._apply_extension_index([*self._manager_extension_index, *self._registry_extension_index])

    def _handle_registry_extension_index_error(
        self,
        generation: int,
        error: BaseException,
    ) -> None:
        if generation != self._extension_index_generation:
            return
        self.set_status(f"Comfy Registry 刷新失败: {error}")

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
        渲染自定义节点源列表
        """
        keyword = self.index_tree.search_keyword()
        tag = self.tag_var.get()
        tags = [] if tag == "全部分类" else [tag]
        installed_names = {ext.name.removesuffix(".disabled") for ext in self.extensions}
        self.filtered_extension_index = filter_extension_index(self.extension_index, keyword, tags)
        self.index_tree.clear()
        for index, item in enumerate(self.filtered_extension_index):
            registry_id = item.registry_id or ""
            installed = item.name in installed_names or registry_id in installed_names or get_repo_name_from_url(item.reference or item.url) in installed_names
            if installed:
                status_url = "已装"
            elif not item.installable:
                status_url = item.install_status or "不可安装"
            else:
                status_url = item.reference or item.url
            source_label = "Registry" if item.source_type == "comfy-registry" else "Git/列表"
            install_type = item.install_type if item.installable else "不可安装"
            self.index_tree.insert(str(index), (item.name, item.description, source_label, item.registry_version or "-", install_type, _format_index_tags(item), status_url))

    def uninstall_selected_extension(
        self,
    ) -> None:
        """
        卸载当前选中的自定义节点
        """
        ext = self._selected_extension()
        if ext is None:
            return
        if not messagebox.askyesno("确认卸载", f"确认卸载自定义节点 '{ext.name}' 吗？"):
            return
        self.run_background("卸载节点中...", lambda: self.extension_manager.uninstall_extension(ext.name), lambda _value: self.refresh_extensions())

    def _switch_registry_extension_version(
        self,
        name: str,
        version: str,
    ) -> None:
        self.run_background("切换 Registry 节点版本中...", lambda: self.extension_manager.switch_registry_extension_version(name, version), lambda _value: self.refresh_extensions())

    def install_from_url(
        self,
    ) -> None:
        """
        从 Git URL 安装自定义节点
        """
        url = self.install_url_var.get().strip()
        if url == self.install_url_placeholder:
            url = ""
        if not url:
            messagebox.showwarning("请输入 URL", "请先输入自定义节点 Git URL")
            return
        self.run_background(
            "安装节点中...",
            lambda: self.extension_manager.install_extension(url, self.use_github_mirror, self.custom_github_mirror),
            lambda _value: (self.install_url_var.set(self.install_url_placeholder), self.refresh_extensions()),
        )

    def install_selected_index_extension(
        self,
    ) -> None:
        """
        安装当前选中的节点源条目
        """
        selected_id = self.index_tree.selected_item_id()
        if selected_id is None:
            messagebox.showwarning("请选择节点", "请先选择节点源中的条目")
            return
        item = self.filtered_extension_index[int(selected_id)]
        if not item.installable:
            node_id = item.registry_id or item.name
            detail = item.install_status or "当前条目不可安装"
            if item.source_type == "comfy-registry":
                detail = f"{detail}。Registry 中存在节点记录，但没有可安装 CNR 版本。节点 ID: {node_id}"
            messagebox.showwarning("无法安装", f"'{item.name}' {detail}")
            return
        self.run_background("安装节点中...", lambda: self._install_index_item(item), lambda _value: self.refresh_extensions())

    def _install_index_item(
        self,
        item: ExtensionIndexItem,
    ) -> None:
        """
        安装节点源条目

        Args:
            item (ExtensionIndexItem):
                节点源条目
        """
        install_type = item.install_type.lower()
        if not item.installable:
            raise ValueError(f"'{item.name}' 不可安装: {item.install_status or '当前条目不可安装'}")
        if item.source_type == "comfy-registry" or install_type == "comfy-registry":
            node_id = item.registry_id or item.name
            self.extension_manager.install_registry_extension(node_id, version=item.registry_version or None)
            return
        files = item.files or (item.url,)
        if install_type == "git-clone":
            repo = files[0] if files else item.reference or item.url
            self.extension_manager.install_extension(repo, self.use_github_mirror, self.custom_github_mirror)
            return
        if install_type == "copy":
            self.custom_nodes_path.mkdir(parents=True, exist_ok=True)
            for url in files:
                filename = _download_name_from_url(url)
                download_file(
                    url=url,
                    path=self.custom_nodes_path,
                    save_name=filename,
                    progress=False,
                )
            return
        if install_type in {"unzip", "zip"}:
            target_name = get_repo_name_from_url(item.reference or item.url or item.name).removesuffix(".zip")
            target_path = self.custom_nodes_path / target_name
            for url in files:
                filename = _download_name_from_url(url)
                download_archive_and_unpack(
                    url=url,
                    local_dir=target_path,
                    name=filename,
                )
            return
        raise ValueError(f"暂不支持安装方式: {item.install_type}")

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
