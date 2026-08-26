"""Implementation grouped from the former ``version_gui.py`` module."""

from __future__ import annotations

import tkinter as tk
from tkinter import (
    messagebox,
    ttk,
)
from typing import (
    Callable,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    BranchInfo,
    CommitInfo,
)

from .filters import commit_matches_keyword, normalize_search_keyword
from .index_list import AdaptiveIndexList
from .inputs import EnhancedEntry
from .theme import apply_window_icon


class CommitSwitchDialog(tk.Toplevel):
    """
    提交版本切换弹窗

    显示提交列表并允许用户切换到指定提交。
    """

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        commits: list[CommitInfo],
        on_switch: Callable[[CommitInfo], None],
    ) -> None:
        """
        初始化提交版本切换弹窗

        Args:
            master (tk.Misc):
                父窗口
            title (str):
                弹窗标题
            commits (list[CommitInfo]):
                提交列表
            on_switch (Callable[[CommitInfo], None]):
                切换回调
        """
        super().__init__(master)
        self.title(title)
        apply_window_icon(self)
        self.geometry("900x520")
        self.minsize(720, 360)
        self.on_switch = on_switch
        self.commits = commits
        self.filtered_commits = commits
        self.search_var = tk.StringVar()

        self.transient(master)  # ty: ignore[no-matching-overload]
        self.grab_set()

        entry = EnhancedEntry(self, textvariable=self.search_var)
        entry.pack(fill=tk.X, padx=10, pady=10)
        self.search_var.trace_add("write", lambda *_args: self._refresh())

        self.tree = AdaptiveIndexList(
            self,
            columns=("commit", "message", "date", "current"),
            headings={"commit": "版本 ID", "message": "更新内容", "date": "日期", "current": "当前"},
            widths={"commit": 110, "message": 520, "date": 180, "current": 70},
        )
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        self.tree.bind("<Double-1>", lambda _event: self._switch_selected())

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(button_frame, text="切换", command=self._switch_selected).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="关闭", command=self.destroy).pack(side=tk.RIGHT, padx=(0, 8))

        self._refresh()

    def update_commits(
        self,
        commits: list[CommitInfo],
    ) -> None:
        """
        更新弹窗中的提交列表

        用于两段式刷新: 弹窗先以本地已知引用渲染, 后台拉取远程引用完成后
        原地更新列表。

        Args:
            commits (list[CommitInfo]):
                新的提交列表
        """
        try:
            if not self.winfo_exists():
                return
            self.commits = commits
            self._refresh()
        except tk.TclError:
            pass

    def _refresh(
        self,
    ) -> None:
        keyword = normalize_search_keyword(self.search_var.get())
        self.tree.delete(*self.tree.get_children())
        self.filtered_commits = []
        for commit in self.commits:
            if not commit_matches_keyword(commit, keyword):
                continue
            self.filtered_commits.append(commit)
            self.tree.insert(
                "",
                tk.END,
                iid=commit.commit,
                values=(commit.commit, commit.message, commit.date, "✓" if commit.is_current else ""),
            )

    def _switch_selected(
        self,
    ) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("请选择版本", "请先选择要切换的版本")
            return
        commit_id = selection[0]
        commit = next(item for item in self.filtered_commits if item.commit == commit_id)
        if commit.is_current:
            self.destroy()
            return
        if not messagebox.askyesno("确认切换", f"确认切换到版本 {commit.commit} 吗？"):
            return
        self.on_switch(commit)
        self.destroy()


class BranchSwitchDialog(tk.Toplevel):
    """
    分支切换弹窗

    显示本地和远程分支并允许用户切换到指定分支。
    """

    def __init__(
        self,
        master: tk.Misc,
        title: str,
        branches: list[BranchInfo],
        on_switch: Callable[[BranchInfo], None],
    ) -> None:
        """
        初始化分支切换弹窗

        Args:
            master (tk.Misc):
                父窗口
            title (str):
                弹窗标题
            branches (list[BranchInfo]):
                分支列表
            on_switch (Callable[[BranchInfo], None]):
                切换回调
        """
        super().__init__(master)
        self.title(title)
        apply_window_icon(self)
        self.geometry("460x420")
        self.minsize(360, 300)
        self.branches = branches
        self.on_switch = on_switch
        self.transient(master)  # ty: ignore[no-matching-overload]
        self.grab_set()

        self.tree = AdaptiveIndexList(
            self,
            columns=("name", "kind", "current"),
            headings={"name": "分支", "kind": "类型", "current": "当前"},
            widths={"name": 260, "kind": 80, "current": 70},
        )
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.tree.bind("<Double-1>", lambda _event: self._switch_selected())

        self._refresh()

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(button_frame, text="切换", command=self._switch_selected).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="关闭", command=self.destroy).pack(side=tk.RIGHT, padx=(0, 8))

    def update_branches(
        self,
        branches: list[BranchInfo],
    ) -> None:
        """
        更新弹窗中的分支列表

        用于两段式刷新: 弹窗先以本地已知引用渲染, 后台拉取远程引用完成后
        原地更新列表。

        Args:
            branches (list[BranchInfo]):
                新的分支列表
        """
        try:
            if not self.winfo_exists():
                return
            self.branches = branches
            self._refresh()
        except tk.TclError:
            pass

    def _refresh(
        self,
    ) -> None:
        self.tree.delete(*self.tree.get_children())
        for branch in self.branches:
            self.tree.insert(
                "",
                tk.END,
                iid=branch.name,
                values=(branch.name, "远程" if branch.is_remote else "本地", "✓" if branch.is_current else ""),
            )

    def _switch_selected(
        self,
    ) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("请选择分支", "请先选择要切换的分支")
            return
        branch_name = selection[0]
        branch = next(item for item in self.branches if item.name == branch_name)
        if branch.is_current:
            self.destroy()
            return
        if not messagebox.askyesno("确认切换", f"确认切换到分支 {branch.name} 吗？"):
            return
        self.on_switch(branch)
        self.destroy()
