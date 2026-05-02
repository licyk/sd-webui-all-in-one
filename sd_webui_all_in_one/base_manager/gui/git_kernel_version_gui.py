"""纯 Git 内核版本管理 GUI"""

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from sd_webui_all_in_one.base_manager.version_manager import (
    BranchInfo,
    RepositoryState,
    configure_git_env,
    inspect_repository,
    list_branches,
    list_commits,
    switch_repository_branch,
    switch_repository_commit,
    update_repository,
)
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    BackgroundTaskMixin,
    BranchSwitchDialog,
    CommitSwitchDialog,
    SearchableTree,
    apply_gui_theme,
    apply_window_icon,
    configure_gui_fonts,
)


class GitKernelVersionManagerApp(tk.Tk, BackgroundTaskMixin):
    """
    Git 内核版本管理窗口

    用于 Fooocus、SD-Trainer、Qwen TTS WebUI 等只有内核仓库版本管理需求的应用。
    """

    def __init__(
        self,
        title: str,
        root_path: Path,
        branch_presets: list[dict[str, Any]] | None = None,
        use_github_mirror: bool | None = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> None:
        """
        初始化 Git 内核版本管理窗口

        Args:
            title (str):
                应用名称
            root_path (Path):
                Git 仓库根目录
            branch_presets (list[dict[str, Any]] | None):
                预设分支信息
            use_github_mirror (bool | None):
                是否启用 GitHub 镜像源
            custom_github_mirror (str | list[str] | None):
                自定义 GitHub 镜像源
        """
        tk.Tk.__init__(self)
        BackgroundTaskMixin.__init__(self)
        self.app_title = title
        self.root_path = Path(root_path)
        self.branch_presets = branch_presets or []
        self.use_github_mirror = use_github_mirror
        self.custom_github_mirror = custom_github_mirror
        self.git_env = configure_git_env(
            use_github_mirror=self.use_github_mirror,
            custom_github_mirror=self.custom_github_mirror,
        )
        self.repository_state: RepositoryState | None = None

        self.title(f"{self.app_title} 版本管理")
        apply_window_icon(self)
        self.geometry("1120x700")
        self.minsize(880, 520)
        self._create_styles()
        self._create_widgets()
        self._install_task_poller(self)
        self.refresh_kernel()

    def _create_styles(
        self,
    ) -> None:
        theme_applied = apply_gui_theme(self)
        style = ttk.Style(self)
        if not theme_applied and "clam" in style.theme_names():
            style.theme_use("clam")
        configure_gui_fonts(self, style)
        style.configure("Status.TLabel", padding=(8, 4))

    def _create_widgets(
        self,
    ) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.X)
        ttk.Label(top, text=f"路径: {self.root_path}").pack(side=tk.LEFT, padx=10, pady=8)
        ttk.Button(top, text="刷新列表", command=self.refresh_kernel).pack(side=tk.RIGHT, padx=(0, 10), pady=8)
        ttk.Button(top, text="一键更新", command=self.update_kernel).pack(side=tk.RIGHT, padx=(0, 8), pady=8)

        main = ttk.Frame(self)
        main.pack(fill=tk.BOTH, expand=True)

        info_frame = ttk.Frame(main)
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

        button_frame = ttk.Frame(main)
        button_frame.pack(fill=tk.X, padx=18, pady=(0, 8))
        ttk.Button(button_frame, text="更新内核", command=self.update_kernel).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="切换分支", command=self.open_branch_dialog).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(button_frame, text="切换版本", command=self.open_commit_dialog).pack(side=tk.LEFT, padx=(8, 0))

        self.commit_tree = SearchableTree(
            main,
            columns=("commit", "message", "date", "current"),
            headings={"commit": "版本 ID", "message": "更新内容", "date": "日期", "current": "当前"},
            widths={"commit": 120, "message": 700, "date": 210, "current": 80},
            search_placeholder=f"搜索 {self.app_title} 版本...",
        )
        self.commit_tree.pack(fill=tk.BOTH, expand=True)

        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel", anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.busy_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.busy_var, width=10, anchor=tk.CENTER).pack(side=tk.RIGHT, padx=(0, 8))
        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=180)
        self.progress.pack(side=tk.RIGHT, padx=(0, 8), pady=4)

    def set_status(
        self,
        message: str,
    ) -> None:
        self.status_var.set(message)

    def set_busy_state(
        self,
        busy: bool,
    ) -> None:
        if busy:
            self.busy_var.set("执行中")
            self.progress.start(12)
        else:
            self.busy_var.set("")
            self.progress.stop()

    def refresh_kernel(
        self,
    ) -> None:
        """
        刷新内核仓库信息和版本列表
        """
        self.run_background(
            "刷新内核信息中...",
            lambda: (inspect_repository(self.root_path), list_commits(self.root_path, limit=None)),
            self._apply_kernel_info,
        )

    def _apply_kernel_info(
        self,
        result: tuple[RepositoryState, list],
    ) -> None:
        state, commits = result
        self.repository_state = state
        self.kernel_url_var.set(state.url or "-")
        self.kernel_branch_var.set(state.branch or "-")
        commit_text = state.commit or "-"
        if state.commit_date:
            commit_text = f"{commit_text} ({state.commit_date})"
        self.kernel_commit_var.set(commit_text)
        self.kernel_status_var.set("Git 仓库" if state.is_git_repo else (state.error or "非 Git 仓库"))
        self.commit_tree.clear()
        for commit in commits:
            self.commit_tree.tree.insert(
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
        self.run_background("更新内核中...", lambda: update_repository(self.root_path), lambda _value: self.refresh_kernel())

    def open_commit_dialog(
        self,
    ) -> None:
        """
        打开内核版本切换弹窗
        """
        if not self.repository_state or not self.repository_state.is_git_repo:
            messagebox.showwarning("无法切换", "当前内核不是 Git 仓库")
            return
        self.run_background(
            "读取内核版本中...",
            lambda: list_commits(self.root_path, limit=None),
            lambda commits: CommitSwitchDialog(self, f"{self.app_title} 版本切换", commits, lambda commit: self._switch_commit(commit.commit)),
        )

    def _switch_commit(
        self,
        commit: str,
    ) -> None:
        self.run_background("切换内核版本中...", lambda: switch_repository_commit(self.root_path, commit), lambda _value: self.refresh_kernel())

    def open_branch_dialog(
        self,
    ) -> None:
        """
        打开内核分支切换弹窗
        """
        if not self.repository_state or not self.repository_state.is_git_repo:
            messagebox.showwarning("无法切换", "当前内核不是 Git 仓库")
            return
        self.run_background(
            "读取内核分支中...",
            lambda: list_branches(self.root_path),
            lambda branches: BranchSwitchDialog(self, f"{self.app_title} 分支切换", branches, self._switch_branch),
        )

    def _switch_branch(
        self,
        branch: BranchInfo,
    ) -> None:
        preset = self._find_branch_preset(branch.name)

        def _task() -> None:
            switch_repository_branch(
                self.root_path,
                branch=branch.name,
                new_url=preset.get("url") if preset else None,
                recurse_submodules=preset.get("use_submodule", False) if preset else False,
            )

        self.run_background("切换内核分支中...", _task, lambda _value: self.refresh_kernel())

    def _find_branch_preset(self, branch_name: str) -> dict[str, Any] | None:
        current_url = self.repository_state.url if self.repository_state else None
        for preset in self.branch_presets:
            if preset.get("branch") != branch_name:
                continue
            if current_url is None or preset.get("url") == current_url:
                return preset
        for preset in self.branch_presets:
            if preset.get("branch") == branch_name:
                return preset
        return None


def launch_git_kernel_version_gui(
    title: str,
    root_path: Path,
    branch_presets: list[dict[str, Any]] | None = None,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """
    启动 Git 内核版本管理 GUI

    Args:
        title (str):
            应用名称
        root_path (Path):
            Git 仓库根目录
        branch_presets (list[dict[str, Any]] | None):
            预设分支信息
        use_github_mirror (bool | None):
            是否启用 GitHub 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源
    """
    app = GitKernelVersionManagerApp(
        title=title,
        root_path=root_path,
        branch_presets=branch_presets,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )
    app.mainloop()
