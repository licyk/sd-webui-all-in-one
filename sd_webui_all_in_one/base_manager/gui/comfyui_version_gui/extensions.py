"""Extensions behavior for the product version window."""

from __future__ import annotations

import tkinter as tk
from tkinter import (
    messagebox,
    ttk,
)
from sd_webui_all_in_one.base_manager.comfy_registry import (
    fetch_comfy_registry_versions,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    BranchInfo,
    CommitInfo,
    ManagedExtension,
    list_branches,
    list_commits,
    update_repository,
)
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    BranchSwitchDialog,
    CommitSwitchDialog,
    SearchableTree,
)


from sd_webui_all_in_one.base_manager.gui.version_gui import GuiActionsMixinContext


class ExtensionActionsMixin(GuiActionsMixinContext):
    def _create_extensions_tab(
        self,
    ) -> None:
        toolbar = ttk.Frame(self.extensions_tab)
        toolbar.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(toolbar, text="刷新节点", command=self.refresh_extensions).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="更新选中", command=self.update_selected_extension).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(toolbar, text="切换版本", command=self.open_extension_commit_dialog).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(toolbar, text="切换分支", command=self.open_extension_branch_dialog).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(toolbar, text="启用/禁用", command=self.toggle_selected_extension).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(toolbar, text="卸载", command=self.uninstall_selected_extension).pack(side=tk.LEFT, padx=(8, 0))

        self.extension_tree = SearchableTree(
            self.extensions_tab,
            columns=("enabled", "source", "name", "version", "url", "branch", "commit", "date", "state"),
            headings={"enabled": "启用", "source": "来源", "name": "节点名", "version": "版本", "url": "远程地址", "branch": "当前分支", "commit": "版本 ID", "date": "更新日期", "state": "状态"},
            widths={"enabled": 60, "source": 110, "name": 230, "version": 100, "url": 380, "branch": 110, "commit": 90, "date": 160, "state": 130},
            search_placeholder="搜索已安装节点...",
        )
        self.extension_tree.pack(fill=tk.BOTH, expand=True)
        self.extension_tree.bind_search_change(self.render_extensions)

    def refresh_extensions(
        self,
    ) -> None:
        """
        刷新已安装自定义节点列表
        """
        self.run_background("刷新自定义节点中...", self.extension_manager.list_extensions, self._apply_extensions)

    def _apply_extensions(
        self,
        extensions: list[ManagedExtension],
    ) -> None:
        self.extensions = extensions
        self.render_extensions()

    def _extension_values(self, ext: ManagedExtension) -> tuple[str, str, str, str, str, str, str, str, str]:
        """
        生成自定义节点列表行数据

        Args:
            ext (ManagedExtension):
                自定义节点信息

        Returns:
            tuple[str, str, str, str, str, str, str, str, str]: 列表行数据
        """
        source_label = {
            "git": "Git",
            "comfy-registry": "Registry",
            "file": "文件",
            "unknown": "未知",
        }.get(ext.source_type, ext.source_type)
        version = ext.registry_version or ext.commit or "-"
        state = "Git 仓库" if ext.is_git_repo else ("Comfy Registry" if ext.source_type == "comfy-registry" else (ext.error or "非 Git/文件安装"))
        return (
            "✓" if ext.enabled else "",
            source_label,
            ext.name,
            version,
            ext.url or "-",
            ext.branch or "-",
            ext.commit or "-",
            ext.commit_date or "-",
            state,
        )

    def render_extensions(
        self,
    ) -> None:
        """
        渲染已安装自定义节点列表
        """
        keyword = self.extension_tree.search_keyword()
        self.extension_tree.clear()
        for ext in self.extensions:
            haystack = " ".join(str(x or "") for x in (ext.name, ext.url, ext.branch, ext.commit, ext.commit_date, ext.error, ext.source_type, ext.registry_id, ext.registry_version)).lower()
            if keyword and keyword not in haystack:
                continue
            self.extension_tree.tree.insert("", tk.END, iid=ext.name, values=self._extension_values(ext))

    def _selected_extension(self) -> ManagedExtension | None:
        selected_id = self.extension_tree.selected_item_id()
        if not selected_id:
            messagebox.showwarning("请选择节点", "请先选择一个自定义节点")
            return None
        return next((ext for ext in self.extensions if ext.name == selected_id), None)

    def update_all(
        self,
    ) -> None:
        """
        更新内核和所有 Git 自定义节点
        """

        def _update_all() -> None:
            if self.repository_state and self.repository_state.is_git_repo:
                update_repository(self.comfyui_path)
            self.extension_manager.update_all()

        self.run_background("一键更新中...", _update_all, lambda _value: self.refresh_all())

    def update_selected_extension(
        self,
    ) -> None:
        """
        更新当前选中的自定义节点
        """
        ext = self._selected_extension()
        if ext is None:
            return
        if not ext.is_git_repo and ext.source_type != "comfy-registry":
            messagebox.showwarning("无法更新", f"'{ext.name}' 不是 Git 仓库或 Comfy Registry 节点")
            return
        self.run_background("更新节点中...", lambda: self.extension_manager.update_extension(ext.name), lambda _value: self.refresh_extensions())

    def toggle_selected_extension(
        self,
    ) -> None:
        """
        切换当前选中自定义节点的启用状态
        """
        ext = self._selected_extension()
        if ext is None:
            return
        self.run_background(
            "修改节点状态中...",
            lambda: self.extension_manager.set_extension_enabled(ext.name, not ext.enabled),
            lambda _value: self.refresh_extensions(),
        )

    def _apply_extension_enabled(
        self,
        name: str,
        enabled: bool,
    ) -> None:
        """
        应用自定义节点启用状态到当前列表

        Args:
            name (str):
                自定义节点名称
            enabled (bool):
                是否启用
        """
        new_name = name.removesuffix(".disabled") if enabled else f"{name.removesuffix('.disabled')}.disabled"
        for ext in self.extensions:
            if ext.name == name:
                ext.name = new_name
                ext.path = self.custom_nodes_path / new_name
                ext.enabled = enabled
                break
        self.render_extensions()
        if self.extension_tree.tree.exists(new_name):
            self.extension_tree.tree.selection_set(new_name)
            self.extension_tree.tree.focus(new_name)

    def open_extension_commit_dialog(
        self,
    ) -> None:
        """
        打开自定义节点版本切换弹窗
        """
        ext = self._selected_extension()
        if ext is None:
            return
        if ext.source_type == "comfy-registry":
            node_id = ext.registry_id or ext.name
            current_version = ext.registry_version
            extension_name = ext.name

            def _versions() -> list[CommitInfo]:
                return [
                    CommitInfo(
                        commit=version.version,
                        message=version.status or "Comfy Registry",
                        date=version.created_at,
                        is_current=version.version == current_version,
                    )
                    for version in fetch_comfy_registry_versions(node_id)
                ]

            self.run_background(
                "读取 Registry 节点版本中...",
                _versions,
                lambda commits: CommitSwitchDialog(
                    self,
                    f"{extension_name} Registry 版本切换",
                    commits,
                    lambda commit: self._switch_registry_extension_version(extension_name, commit.commit),
                ),
            )
            return
        if not ext.is_git_repo:
            messagebox.showwarning("无法切换", f"'{ext.name}' 不是 Git 仓库")
            return
        dialog: CommitSwitchDialog | None = None

        def _open_or_refresh_dialog(commits: list[CommitInfo]) -> None:
            nonlocal dialog
            if dialog is None:
                dialog = CommitSwitchDialog(
                    self,
                    f"{ext.name} 版本切换",
                    commits,
                    lambda commit: self._switch_extension_commit(ext.name, commit.commit),
                )
            else:
                dialog.update_commits(commits)

        self.run_two_phase_refresh(
            "读取节点版本中...",
            lambda: list_commits(ext.path, None, fetch=False),
            lambda: list_commits(ext.path, None, fetch=True),
            _open_or_refresh_dialog,
        )

    def _switch_extension_commit(
        self,
        name: str,
        commit: str,
    ) -> None:
        self.run_background("切换节点版本中...", lambda: self.extension_manager.switch_extension_commit(name, commit), lambda _value: self.refresh_extensions())

    def open_extension_branch_dialog(
        self,
    ) -> None:
        """
        打开自定义节点分支切换弹窗
        """
        ext = self._selected_extension()
        if ext is None:
            return
        if ext.source_type == "comfy-registry":
            messagebox.showwarning("无法切换", f"'{ext.name}' 是 Comfy Registry 节点，请使用“切换版本”选择 Registry 版本")
            return
        if not ext.is_git_repo:
            messagebox.showwarning("无法切换", f"'{ext.name}' 不是 Git 仓库")
            return
        dialog: BranchSwitchDialog | None = None

        def _open_or_refresh_dialog(branches: list[BranchInfo]) -> None:
            nonlocal dialog
            if dialog is None:
                dialog = BranchSwitchDialog(
                    self,
                    f"{ext.name} 分支切换",
                    branches,
                    lambda branch: self._switch_extension_branch(ext.name, branch.name),
                )
            else:
                dialog.update_branches(branches)

        self.run_two_phase_refresh(
            "读取节点分支中...",
            lambda: list_branches(ext.path, fetch=False),
            lambda: list_branches(ext.path, fetch=True),
            _open_or_refresh_dialog,
        )

    def _switch_extension_branch(
        self,
        name: str,
        branch: str,
    ) -> None:
        self.run_background("切换节点分支中...", lambda: self.extension_manager.switch_extension_branch(name, branch), lambda _value: self.refresh_extensions())
