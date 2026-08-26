"""Extensions behavior for the product version window."""

from __future__ import annotations

import tkinter as tk
from tkinter import (
    messagebox,
    ttk,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    BranchInfo,
    CommitInfo,
    ManagedExtension,
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
        ttk.Button(toolbar, text="刷新扩展", command=self.refresh_extensions).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="更新选中", command=self.update_selected_extension).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(toolbar, text="切换版本", command=self.open_extension_commit_dialog).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(toolbar, text="切换分支", command=self.open_extension_branch_dialog).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(toolbar, text="启用/禁用", command=self.toggle_selected_extension).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(toolbar, text="卸载", command=self.uninstall_selected_extension).pack(side=tk.LEFT, padx=(8, 0))

        self.extension_tree = SearchableTree(
            self.extensions_tab,
            columns=("enabled", "name", "url", "branch", "commit", "date", "state"),
            headings={"enabled": "启用", "name": "插件名", "url": "远程地址", "branch": "当前分支", "commit": "版本 ID", "date": "更新日期", "state": "状态"},
            widths={"enabled": 60, "name": 250, "url": 420, "branch": 120, "commit": 90, "date": 170, "state": 120},
            search_placeholder="搜索已安装插件...",
        )
        self.extension_tree.pack(fill=tk.BOTH, expand=True)
        self.extension_tree.bind_search_change(self.render_extensions)

    def refresh_extensions(
        self,
    ) -> None:
        """
        刷新已安装扩展列表
        """
        self.run_background("刷新扩展列表中...", self.extension_manager.list_extensions, self._apply_extensions)

    def _apply_extensions(
        self,
        extensions: list[ManagedExtension],
    ) -> None:
        self.extensions = extensions
        self.render_extensions()

    def render_extensions(
        self,
    ) -> None:
        """
        渲染已安装扩展列表
        """
        keyword = self.extension_tree.search_keyword()
        self.extension_tree.clear()
        for ext in self.extensions:
            haystack = " ".join(str(x or "") for x in (ext.name, ext.url, ext.branch, ext.commit, ext.commit_date, ext.error)).lower()
            if keyword and keyword not in haystack:
                continue
            self.extension_tree.tree.insert(
                "",
                tk.END,
                iid=ext.name,
                values=self._extension_values(ext),
            )

    def _selected_extension(self) -> ManagedExtension | None:
        selected_id = self.extension_tree.selected_item_id()
        if not selected_id:
            messagebox.showwarning("请选择扩展", "请先选择一个扩展")
            return None
        return next((ext for ext in self.extensions if ext.name == selected_id), None)

    def update_all(
        self,
    ) -> None:
        """
        更新内核和所有 Git 扩展
        """

        def _update_all() -> None:
            if self.repository_state and self.repository_state.is_git_repo:
                update_repository(self.sd_webui_path)
            self.extension_manager.update_all()

        self.run_background("一键更新中...", _update_all, lambda _value: self.refresh_all())

    def update_selected_extension(
        self,
    ) -> None:
        """
        更新当前选中的扩展
        """
        ext = self._selected_extension()
        if ext is None:
            return
        if not ext.is_git_repo:
            messagebox.showwarning("无法更新", f"'{ext.name}' 不是 Git 仓库")
            return

        def _update() -> None:
            self.extension_manager.update_extension(ext.name)

        self.run_background("更新扩展中...", _update, lambda _value: self.refresh_extensions())

    def toggle_selected_extension(
        self,
    ) -> None:
        """
        切换当前选中扩展的启用状态
        """
        ext = self._selected_extension()
        if ext is None:
            return
        self.run_background(
            "修改扩展状态中...",
            lambda: self.extension_manager.set_extension_enabled(ext.name, not ext.enabled),
            lambda _value: self._apply_extension_enabled(ext.name, not ext.enabled),
        )

    def open_extension_commit_dialog(
        self,
    ) -> None:
        """
        打开扩展版本切换弹窗
        """
        ext = self._selected_extension()
        if ext is None:
            return
        if not ext.is_git_repo:
            messagebox.showwarning("无法切换", f"'{ext.name}' 不是 Git 仓库")
            return
        dialog: CommitSwitchDialog | None = None

        def _open_or_refresh_dialog(commits: list[CommitInfo]) -> None:
            nonlocal dialog
            if dialog is None:
                dialog = CommitSwitchDialog(self, f"{ext.name} 版本切换", commits, lambda commit: self._switch_extension_commit(ext.name, commit.commit))
            else:
                dialog.update_commits(commits)

        self.run_two_phase_refresh(
            "读取扩展版本中...",
            lambda: list_commits(ext.path, limit=None, fetch=False),
            lambda: list_commits(ext.path, limit=None, fetch=True),
            _open_or_refresh_dialog,
        )

    def _switch_extension_commit(
        self,
        name: str,
        commit: str,
    ) -> None:
        self.run_background("切换扩展版本中...", lambda: self.extension_manager.switch_extension_commit(name, commit), lambda _value: self.refresh_extensions())

    def open_extension_branch_dialog(
        self,
    ) -> None:
        """
        打开扩展分支切换弹窗
        """
        ext = self._selected_extension()
        if ext is None:
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
            "读取扩展分支中...",
            lambda: self._list_branches_with_env(ext.path, fetch=False),
            lambda: self._list_branches_with_env(ext.path, fetch=True),
            _open_or_refresh_dialog,
        )

    def _switch_extension_branch(
        self,
        name: str,
        branch: str,
    ) -> None:
        def _switch() -> None:
            self.extension_manager.switch_extension_branch(name, branch)

        self.run_background("切换扩展分支中...", _switch, lambda _value: self.refresh_extensions())

    def _extension_values(self, ext: ManagedExtension) -> tuple[str, str, str, str, str, str, str]:
        return (
            "✓" if ext.enabled else "",
            ext.name,
            ext.url or "-",
            ext.branch or "-",
            ext.commit or "-",
            ext.commit_date or "-",
            "Git 仓库" if ext.is_git_repo else (ext.error or "非 Git 仓库"),
        )

    def _apply_extension_enabled(
        self,
        name: str,
        enabled: bool,
    ) -> None:
        for ext in self.extensions:
            if ext.name == name:
                ext.enabled = enabled
                if self.extension_tree.tree.exists(name):
                    self.extension_tree.tree.item(name, values=self._extension_values(ext))
                    self.extension_tree.tree.selection_set(name)
                    self.extension_tree.tree.focus(name)
                return
