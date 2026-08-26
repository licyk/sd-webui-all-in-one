"""Kernel behavior for the product version window."""

from __future__ import annotations

import tkinter as tk
from tkinter import (
    messagebox,
    ttk,
)
from sd_webui_all_in_one.base_manager.sd_webui_base import (
    SD_WEBUI_BRANCH_INFO_DICT,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    BranchInfo,
    CommitInfo,
    inspect_repository,
    list_commits,
    switch_repository_branch,
    switch_repository_commit,
    update_repository,
)
from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryState
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    BranchSwitchDialog,
    CommitSwitchDialog,
    SearchableTree,
    commit_matches_keyword,
)


from sd_webui_all_in_one.base_manager.gui.version_gui import GuiActionsMixinContext


class KernelActionsMixin(GuiActionsMixinContext):
    def _create_kernel_tab(
        self,
    ) -> None:
        info_frame = ttk.Frame(self.kernel_tab)
        info_frame.pack(fill=tk.X, padx=18, pady=16)
        self.kernel_url_var = tk.StringVar(value="-")
        self.kernel_branch_var = tk.StringVar(value="-")
        self.kernel_commit_var = tk.StringVar(value="-")
        self.kernel_status_var = tk.StringVar(value="-")
        for row, (label, var) in enumerate(
            (
                ("远程地址:", self.kernel_url_var),
                ("当前分支:", self.kernel_branch_var),
                ("当前版本:", self.kernel_commit_var),
                ("状态:", self.kernel_status_var),
            )
        ):
            ttk.Label(info_frame, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
            ttk.Label(info_frame, textvariable=var).grid(row=row, column=1, sticky=tk.W, padx=(16, 0), pady=4)
        info_frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(self.kernel_tab)
        button_frame.pack(fill=tk.X, padx=18, pady=(0, 8))
        ttk.Button(button_frame, text="更新内核", command=self.update_kernel).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="切换分支", command=self.open_kernel_branch_dialog).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(button_frame, text="切换版本", command=self.open_kernel_commit_dialog).pack(side=tk.LEFT, padx=(8, 0))

        self.kernel_commit_tree = SearchableTree(
            self.kernel_tab,
            columns=("commit", "message", "date", "current"),
            headings={"commit": "版本 ID", "message": "更新内容", "date": "日期", "current": "当前"},
            widths={"commit": 120, "message": 700, "date": 210, "current": 80},
            search_placeholder="搜索内核版本...",
        )
        self.kernel_commit_tree.pack(fill=tk.BOTH, expand=True)
        self.kernel_commit_tree.bind_search_change(self.render_kernel_commits)

    def refresh_kernel(
        self,
    ) -> None:
        """
        刷新内核仓库信息和版本列表
        """
        self.run_two_phase_refresh(
            "刷新内核信息中...",
            lambda: (inspect_repository(self.sd_webui_path), list_commits(self.sd_webui_path, limit=None, fetch=False)),
            lambda: (inspect_repository(self.sd_webui_path), list_commits(self.sd_webui_path, limit=None, fetch=True)),
            self._apply_kernel_info,
        )

    def _apply_kernel_info(
        self,
        result: tuple[RepositoryState, list[CommitInfo]],
    ) -> None:
        state, commits = result
        self.repository_state = state
        self.kernel_commits = commits
        self.kernel_url_var.set(state.url or "-")
        self.kernel_branch_var.set(state.branch or "-")
        commit_text = state.commit or "-"
        if state.commit_date:
            commit_text = f"{commit_text} ({state.commit_date})"
        self.kernel_commit_var.set(commit_text)
        self.kernel_status_var.set("Git 仓库" if state.is_git_repo else (state.error or "非 Git 仓库"))
        self.render_kernel_commits()

    def render_kernel_commits(
        self,
    ) -> None:
        """
        根据搜索条件渲染内核版本列表
        """
        keyword = self.kernel_commit_tree.search_keyword()
        self.kernel_commit_tree.clear()
        for commit in self.kernel_commits:
            if not commit_matches_keyword(commit, keyword):
                continue
            self.kernel_commit_tree.tree.insert(
                "",
                tk.END,
                iid=commit.commit,
                values=(commit.commit, commit.message, commit.date, "✓" if commit.is_current else ""),
            )

    def update_kernel(
        self,
    ) -> None:
        """
        更新内核仓库
        """
        if not self.repository_state or not self.repository_state.is_git_repo:
            messagebox.showwarning("无法更新", "当前内核不是 Git 仓库")
            return
        self.run_background("更新内核中...", lambda: update_repository(self.sd_webui_path), lambda _value: self.refresh_kernel())

    def open_kernel_commit_dialog(
        self,
    ) -> None:
        """
        打开内核版本切换弹窗
        """
        if not self.repository_state or not self.repository_state.is_git_repo:
            messagebox.showwarning("无法切换", "当前内核不是 Git 仓库")
            return
        dialog: CommitSwitchDialog | None = None

        def _open_or_refresh_dialog(commits: list[CommitInfo]) -> None:
            nonlocal dialog
            if dialog is None:
                dialog = CommitSwitchDialog(self, "内核版本切换", commits, lambda commit: self._switch_kernel_commit(commit.commit))
            else:
                dialog.update_commits(commits)

        self.run_two_phase_refresh(
            "读取内核版本中...",
            lambda: list_commits(self.sd_webui_path, limit=None, fetch=False),
            lambda: list_commits(self.sd_webui_path, limit=None, fetch=True),
            _open_or_refresh_dialog,
        )

    def _switch_kernel_commit(
        self,
        commit: str,
    ) -> None:
        self.run_background("切换内核版本中...", lambda: switch_repository_commit(self.sd_webui_path, commit), lambda _value: self.refresh_kernel())

    def open_kernel_branch_dialog(
        self,
    ) -> None:
        """
        打开内核分支切换弹窗
        """
        if not self.repository_state or not self.repository_state.is_git_repo:
            messagebox.showwarning("无法切换", "当前内核不是 Git 仓库")
            return
        dialog: BranchSwitchDialog | None = None

        def _open_or_refresh_dialog(branches: list[BranchInfo]) -> None:
            nonlocal dialog
            if dialog is None:
                dialog = BranchSwitchDialog(self, "内核分支切换", branches, lambda branch: self._switch_kernel_branch(branch.name))
            else:
                dialog.update_branches(branches)

        self.run_two_phase_refresh(
            "读取内核分支中...",
            lambda: self._list_branches_with_env(self.sd_webui_path, fetch=False),
            lambda: self._list_branches_with_env(self.sd_webui_path, fetch=True),
            _open_or_refresh_dialog,
        )

    def _switch_kernel_branch(
        self,
        branch: str,
    ) -> None:
        branch_info = next((item for item in SD_WEBUI_BRANCH_INFO_DICT if item["branch"] == branch), None)

        def _switch() -> None:
            switch_repository_branch(
                self.sd_webui_path,
                branch=branch,
                new_url=branch_info["url"] if branch_info else None,
                recurse_submodules=branch_info["use_submodule"] if branch_info else False,
            )

        self.run_background("切换内核分支中...", _switch, lambda _value: self.refresh_kernel())
