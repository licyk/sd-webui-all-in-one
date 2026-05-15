"""Stable Diffusion WebUI 版本管理 GUI"""

# pylint: disable=too-many-instance-attributes,attribute-defined-outside-init

from __future__ import annotations

import json
import os
import tkinter as tk
from pathlib import Path
from tkinter import (
    messagebox,
    ttk,
)

from sd_webui_all_in_one.base_manager.sd_webui_base import (
    SD_WEBUI_BRANCH_INFO_DICT,
    set_sd_webui_extension_download_list_mirror,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    BranchInfo,
    DEFAULT_EXTENSION_INDEX_URL,
    ExtensionIndexItem,
    ExtensionManager,
    ManagedExtension,
    RepositoryState,
    configure_git_env,
    fetch_extension_index,
    filter_extension_index,
    inspect_repository,
    list_branches,
    list_commits,
    switch_repository_branch,
    switch_repository_commit,
    update_repository,
)
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    AdaptiveIndexList,
    BackgroundTaskMixin,
    BranchSwitchDialog,
    CommitSwitchDialog,
    SearchableTree,
    apply_gui_theme,
    apply_window_icon,
    configure_gui_fonts,
)


def _load_sd_webui_config(sd_webui_path: Path) -> dict:
    config_path = sd_webui_path / "config.json"
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _save_sd_webui_config(
    sd_webui_path: Path,
    data: dict,
) -> None:
    config_path = sd_webui_path / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def _sd_webui_extension_enabled(sd_webui_path: Path, name: str, _path: Path) -> bool:
    settings = _load_sd_webui_config(sd_webui_path)
    disabled_extensions = set(settings.get("disabled_extensions", []))
    disable_all_extensions = settings.get("disable_all_extensions", "none")
    if disable_all_extensions == "all":
        return False
    if disable_all_extensions == "extra":
        return True
    return name not in disabled_extensions


def _set_sd_webui_extension_enabled(
    sd_webui_path: Path,
    name: str,
    enabled: bool,
) -> None:
    settings = _load_sd_webui_config(sd_webui_path)
    disabled_extensions = settings.setdefault("disabled_extensions", [])
    if not isinstance(disabled_extensions, list):
        disabled_extensions = []
        settings["disabled_extensions"] = disabled_extensions
    if enabled and name in disabled_extensions:
        disabled_extensions.remove(name)
    elif not enabled and name not in disabled_extensions:
        disabled_extensions.append(name)
    _save_sd_webui_config(sd_webui_path, settings)


class SDWebUiVersionManagerApp(tk.Tk, BackgroundTaskMixin):
    """
    Stable Diffusion WebUI 版本管理窗口

    提供内核版本管理、扩展启禁用、扩展更新、扩展卸载和扩展源安装功能。
    """

    def __init__(
        self,
        sd_webui_path: Path,
        use_github_mirror: bool | None = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> None:
        """
        初始化 Stable Diffusion WebUI 版本管理窗口

        Args:
            sd_webui_path (Path):
                Stable Diffusion WebUI 根目录
            use_github_mirror (bool | None):
                是否启用 GitHub 镜像源
            custom_github_mirror (str | list[str] | None):
                自定义 GitHub 镜像源
        """
        tk.Tk.__init__(self)
        BackgroundTaskMixin.__init__(self)
        self.sd_webui_path = Path(sd_webui_path)
        self.use_github_mirror = use_github_mirror
        self.custom_github_mirror = custom_github_mirror
        self.git_env = configure_git_env(
            use_github_mirror=self.use_github_mirror,
            custom_github_mirror=self.custom_github_mirror,
        )
        self.extension_index_url = self._configure_extension_index_url()
        self.repository_state: RepositoryState | None = None
        self.extensions: list[ManagedExtension] = []
        self.extension_index: list[ExtensionIndexItem] = []
        self.filtered_extension_index: list[ExtensionIndexItem] = []
        self.extension_manager = ExtensionManager(
            root_path=self.sd_webui_path,
            extension_dir_name="extensions",
            is_enabled=lambda name, path: _sd_webui_extension_enabled(self.sd_webui_path, name, path),
            set_enabled=lambda name, enabled: _set_sd_webui_extension_enabled(self.sd_webui_path, name, enabled),
        )

        self.title("Stable Diffusion WebUI 版本管理")
        apply_window_icon(self)
        self.geometry("1280x760")
        self.minsize(980, 580)
        self._create_styles()
        self._create_widgets()
        self._install_task_poller(self)
        self.refresh_all()

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
        path_label = ttk.Label(top, text=f"路径: {self.sd_webui_path}")
        path_label.pack(side=tk.LEFT, padx=10, pady=8)
        ttk.Button(top, text="刷新列表", command=self.refresh_all).pack(side=tk.RIGHT, padx=(0, 10), pady=8)
        ttk.Button(top, text="一键更新", command=self.update_all).pack(side=tk.RIGHT, padx=(0, 8), pady=8)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.kernel_tab = ttk.Frame(self.notebook)
        self.extensions_tab = ttk.Frame(self.notebook)
        self.install_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.kernel_tab, text="内核")
        self.notebook.add(self.extensions_tab, text="扩展")
        self.notebook.add(self.install_tab, text="安装新扩展")

        self._create_kernel_tab()
        self._create_extensions_tab()
        self._create_install_tab()

        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.busy_var = tk.StringVar(value="")
        self.busy_label = ttk.Label(status_frame, textvariable=self.busy_var, width=10, anchor=tk.CENTER)
        self.busy_label.pack(side=tk.RIGHT, padx=(0, 8))
        self.progress = ttk.Progressbar(status_frame, mode="indeterminate", length=180)
        self.progress.pack(side=tk.RIGHT, padx=(0, 8), pady=4)

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
        self.extension_tree.search_var.trace_add("write", lambda *_args: self.render_extensions())

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
        self.index_tree.search_var.trace_add("write", lambda *_args: self.render_extension_index())
        self.index_tree.bind_double_click(self.install_selected_index_extension)

        bottom = ttk.Frame(self.install_tab)
        bottom.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.install_url_var = tk.StringVar()
        self.install_url_placeholder = "输入扩展 Git URL，例如 https://github.com/user/extension"
        install_url_entry = ttk.Entry(bottom, textvariable=self.install_url_var)
        install_url_entry.insert(0, self.install_url_placeholder)
        install_url_entry.bind("<FocusIn>", self._clear_install_url_placeholder)
        install_url_entry.bind("<FocusOut>", self._restore_install_url_placeholder)
        install_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(bottom, text="安装 URL", command=self.install_from_url).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(bottom, text="安装选中", command=self.install_selected_index_extension).pack(side=tk.LEFT, padx=(8, 0))

    def set_status(
        self,
        message: str,
    ) -> None:
        """设置状态栏消息。

        Args:
            message (str):
                状态栏消息
        """
        self.status_var.set(message)

    def set_busy_state(
        self,
        busy: bool,
    ) -> None:
        """设置忙碌状态显示。

        Args:
            busy (bool):
                是否处于忙碌状态
        """
        if busy:
            self.busy_var.set("执行中")
            self.progress.start(12)
        else:
            self.busy_var.set("")
            self.progress.stop()

    def refresh_all(
        self,
    ) -> None:
        """
        刷新内核、扩展和扩展源列表
        """
        self.refresh_kernel()
        self.refresh_extensions()
        if not self.extension_index:
            self.refresh_extension_index()

    def refresh_kernel(
        self,
    ) -> None:
        """
        刷新内核仓库信息和版本列表
        """
        self.run_background(
            "刷新内核信息中...",
            lambda: (inspect_repository(self.sd_webui_path), list_commits(self.sd_webui_path, limit=None)),
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
        self.kernel_commit_tree.clear()
        for commit in commits:
            self.kernel_commit_tree.tree.insert(
                "",
                tk.END,
                iid=commit.commit,
                values=(commit.commit, commit.message, commit.date, "✓" if commit.is_current else ""),
            )

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
        keyword = self.extension_tree.search_var.get().strip().lower()
        if keyword == "搜索已安装插件...":
            keyword = ""
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
        keyword = self.index_tree.search_var.get().strip()
        if keyword == "搜索新插件...":
            keyword = ""
        tag = self.tag_var.get()
        tags = [] if tag == "全部分类" else [tag]
        installed_names = {ext.name for ext in self.extensions}
        self.filtered_extension_index = filter_extension_index(self.extension_index, keyword, tags)
        self.index_tree.clear()
        for item in self.filtered_extension_index:
            status = "已装" if item.name in installed_names else item.url
            self.index_tree.insert(item.url, (item.name, item.description, ", ".join(item.tags), status))

    def _selected_extension(self) -> ManagedExtension | None:
        selected_id = self.extension_tree.selected_item_id()
        if not selected_id:
            messagebox.showwarning("请选择扩展", "请先选择一个扩展")
            return None
        return next((ext for ext in self.extensions if ext.name == selected_id), None)

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

    def open_kernel_commit_dialog(
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
            lambda: list_commits(self.sd_webui_path, limit=None),
            lambda commits: CommitSwitchDialog(self, "内核版本切换", commits, lambda commit: self._switch_kernel_commit(commit.commit)),
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
        self.run_background(
            "读取内核分支中...",
            lambda: self._list_branches_with_env(self.sd_webui_path),
            lambda branches: BranchSwitchDialog(self, "内核分支切换", branches, lambda branch: self._switch_kernel_branch(branch.name)),
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
        self.run_background(
            "读取扩展版本中...",
            lambda: list_commits(ext.path, limit=None),
            lambda commits: CommitSwitchDialog(self, f"{ext.name} 版本切换", commits, lambda commit: self._switch_extension_commit(ext.name, commit.commit)),
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
        self.run_background(
            "读取扩展分支中...",
            lambda: self._list_branches_with_env(ext.path),
            lambda branches: BranchSwitchDialog(self, f"{ext.name} 分支切换", branches, lambda branch: self._switch_extension_branch(ext.name, branch.name)),
        )

    def _switch_extension_branch(
        self,
        name: str,
        branch: str,
    ) -> None:
        def _switch() -> None:
            self.extension_manager.switch_extension_branch(name, branch)

        self.run_background("切换扩展分支中...", _switch, lambda _value: self.refresh_extensions())

    def _list_branches_with_env(self, path: Path) -> list[BranchInfo]:
        """
        读取分支列表

        Args:
            path (Path):
                Git 仓库路径

        Returns:
            list[BranchInfo]: 分支列表
        """
        return list_branches(path)

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


def launch_sd_webui_version_gui(
    sd_webui_path: Path,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """
    启动 Stable Diffusion WebUI 版本管理 GUI

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        use_github_mirror (bool | None):
            是否启用 GitHub 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源
    """
    app = SDWebUiVersionManagerApp(
        sd_webui_path=sd_webui_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )
    app.mainloop()
