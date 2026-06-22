"""ComfyUI 版本管理 GUI"""

# pylint: disable=too-many-instance-attributes,attribute-defined-outside-init

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import (
    messagebox,
    ttk,
)
from urllib.parse import urlparse

from sd_webui_all_in_one.base_manager.base import get_repo_name_from_url
from sd_webui_all_in_one.base_manager.comfy_registry import (
    fetch_comfy_registry_extension_index,
    fetch_comfy_registry_versions,
)
from sd_webui_all_in_one.base_manager.comfyui_base import (
    ComfyUiExtensionManager,
    set_comfyui_custom_node_list_mirror,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    BranchInfo,
    CommitInfo,
    ExtensionIndexItem,
    ManagedExtension,
    RepositoryState,
    configure_git_env,
    fetch_comfyui_custom_node_index,
    filter_extension_index,
    inspect_repository,
    list_branches,
    list_commits,
    switch_repository_branch,
    switch_repository_commit,
    update_repository,
)
from sd_webui_all_in_one.downloader import (
    download_archive_and_unpack,
    download_file,
)
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    AdaptiveIndexList,
    BackgroundTaskMixin,
    BranchSwitchDialog,
    CommitSwitchDialog,
    EnhancedEntry,
    SearchableTree,
    apply_gui_theme,
    apply_window_icon,
    commit_matches_keyword,
    configure_gui_fonts,
)
from sd_webui_all_in_one.file_manager import move_files


COMFYUI_CUSTOM_NODE_INDEX_URL = "https://raw.githubusercontent.com/Comfy-Org/ComfyUI-Manager/refs/heads/main/custom-node-list.json"


def _comfyui_custom_node_enabled(name: str, _path: Path) -> bool:
    return not name.endswith(".disabled")


def _set_comfyui_custom_node_enabled(
    custom_nodes_path: Path,
    name: str,
    enabled: bool,
) -> None:
    name = name.removesuffix(".disabled")
    enabled_path = custom_nodes_path / name
    disabled_path = custom_nodes_path / f"{name}.disabled"
    if enabled:
        if disabled_path.exists() and not enabled_path.exists():
            move_files(disabled_path, enabled_path)
    else:
        if enabled_path.exists() and not disabled_path.exists():
            move_files(enabled_path, disabled_path)


def _download_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    return name or get_repo_name_from_url(url)


class ComfyUiVersionManagerApp(tk.Tk, BackgroundTaskMixin):
    """
    ComfyUI 版本管理窗口

    提供内核版本管理、自定义节点启禁用、自定义节点更新、卸载和安装功能。
    """

    def __init__(
        self,
        comfyui_path: Path,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> None:
        """
        初始化 ComfyUI 版本管理窗口

        Args:
            comfyui_path (Path):
                ComfyUI 根目录
            use_github_mirror (bool):
                是否启用 GitHub 镜像源
            custom_github_mirror (str | list[str] | None):
                自定义 GitHub 镜像源
        """
        tk.Tk.__init__(self)
        BackgroundTaskMixin.__init__(self)
        self.comfyui_path = Path(comfyui_path)
        self.custom_nodes_path = self.comfyui_path / "custom_nodes"
        self.use_github_mirror = use_github_mirror
        self.custom_github_mirror = custom_github_mirror
        self.git_env = configure_git_env(use_github_mirror=self.use_github_mirror, custom_github_mirror=self.custom_github_mirror)
        self.extension_index_url = self._configure_extension_index_url()
        self.repository_state: RepositoryState | None = None
        self.kernel_commits: list[CommitInfo] = []
        self.extensions: list[ManagedExtension] = []
        self.extension_index: list[ExtensionIndexItem] = []
        self.filtered_extension_index: list[ExtensionIndexItem] = []
        self.extension_manager = ComfyUiExtensionManager(self.comfyui_path, include_files=True)

        self.title("ComfyUI 版本管理")
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

    def _configure_extension_index_url(self) -> str:
        if not self.use_github_mirror:
            return COMFYUI_CUSTOM_NODE_INDEX_URL
        extension_index_url = set_comfyui_custom_node_list_mirror(
            custom_github_mirror=self.custom_github_mirror,
        )
        return extension_index_url or COMFYUI_CUSTOM_NODE_INDEX_URL

    def _create_widgets(
        self,
    ) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.X)
        ttk.Label(top, text=f"路径: {self.comfyui_path}").pack(side=tk.LEFT, padx=10, pady=8)
        ttk.Button(top, text="刷新列表", command=self.refresh_all).pack(side=tk.RIGHT, padx=(0, 10), pady=8)
        ttk.Button(top, text="一键更新", command=self.update_all).pack(side=tk.RIGHT, padx=(0, 8), pady=8)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.kernel_tab = ttk.Frame(self.notebook)
        self.extensions_tab = ttk.Frame(self.notebook)
        self.install_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.kernel_tab, text="内核")
        self.notebook.add(self.extensions_tab, text="自定义节点")
        self.notebook.add(self.install_tab, text="安装新节点")

        self._create_kernel_tab()
        self._create_extensions_tab()
        self._create_install_tab()

        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel", anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.busy_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.busy_var, width=10, anchor=tk.CENTER).pack(side=tk.RIGHT, padx=(0, 8))
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
        for row, (label, var) in enumerate((("远程地址:", self.kernel_url_var), ("当前分支:", self.kernel_branch_var), ("当前版本:", self.kernel_commit_var), ("状态:", self.kernel_status_var))):
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

    def _create_install_tab(
        self,
    ) -> None:
        toolbar = ttk.Frame(self.install_tab)
        toolbar.pack(fill=tk.X, padx=8, pady=8)
        ttk.Button(toolbar, text="刷新节点源", command=self.refresh_extension_index).pack(side=tk.LEFT)
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
        刷新内核、自定义节点和节点源列表
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
            lambda: (inspect_repository(self.comfyui_path), list_commits(self.comfyui_path, None)),
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

    def refresh_extension_index(
        self,
    ) -> None:
        """
        刷新自定义节点源列表
        """
        def _fetch_index() -> list[ExtensionIndexItem]:
            manager_items = fetch_comfyui_custom_node_index(self.extension_index_url)
            try:
                registry_items = fetch_comfy_registry_extension_index(limit=200)
            except Exception as e:
                error_message = str(e)
                self.after(0, lambda: self.set_status(f"Comfy Registry 刷新失败: {error_message}"))
                registry_items = []
            return [*manager_items, *registry_items]

        self.run_background("刷新节点源中...", _fetch_index, self._apply_extension_index)

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
            self.index_tree.insert(str(index), (item.name, item.description, source_label, item.registry_version or "-", install_type, ", ".join(item.tags), status_url))

    def _selected_extension(self) -> ManagedExtension | None:
        selected_id = self.extension_tree.selected_item_id()
        if not selected_id:
            messagebox.showwarning("请选择节点", "请先选择一个自定义节点")
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
        self.run_background("更新内核中...", lambda: update_repository(self.comfyui_path), lambda _value: self.refresh_kernel())

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
            lambda: list_commits(self.comfyui_path, None),
            lambda commits: CommitSwitchDialog(self, "内核版本切换", commits, lambda commit: self._switch_kernel_commit(commit.commit)),
        )

    def _switch_kernel_commit(
        self,
        commit: str,
    ) -> None:
        self.run_background("切换内核版本中...", lambda: switch_repository_commit(self.comfyui_path, commit), lambda _value: self.refresh_kernel())

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
            lambda: list_branches(self.comfyui_path),
            lambda branches: BranchSwitchDialog(self, "内核分支切换", branches, self._switch_kernel_branch),
        )

    def _switch_kernel_branch(
        self,
        branch: BranchInfo,
    ) -> None:
        self.run_background("切换内核分支中...", lambda: switch_repository_branch(self.comfyui_path, branch.name), lambda _value: self.refresh_kernel())

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
        self.run_background(
            "读取节点版本中...",
            lambda: list_commits(ext.path, None),
            lambda commits: CommitSwitchDialog(
                self,
                f"{ext.name} 版本切换",
                commits,
                lambda commit: self._switch_extension_commit(ext.name, commit.commit),
            ),
        )

    def _switch_extension_commit(
        self,
        name: str,
        commit: str,
    ) -> None:
        self.run_background("切换节点版本中...", lambda: self.extension_manager.switch_extension_commit(name, commit), lambda _value: self.refresh_extensions())

    def _switch_registry_extension_version(
        self,
        name: str,
        version: str,
    ) -> None:
        self.run_background("切换 Registry 节点版本中...", lambda: self.extension_manager.switch_registry_extension_version(name, version), lambda _value: self.refresh_extensions())

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
        self.run_background(
            "读取节点分支中...",
            lambda: list_branches(ext.path),
            lambda branches: BranchSwitchDialog(
                self,
                f"{ext.name} 分支切换",
                branches,
                lambda branch: self._switch_extension_branch(ext.name, branch.name),
            ),
        )

    def _switch_extension_branch(
        self,
        name: str,
        branch: str,
    ) -> None:
        self.run_background("切换节点分支中...", lambda: self.extension_manager.switch_extension_branch(name, branch), lambda _value: self.refresh_extensions())

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


def launch_comfyui_version_gui(
    comfyui_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """
    启动 ComfyUI 版本管理 GUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        use_github_mirror (bool):
            是否启用 GitHub 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源
    """
    app = ComfyUiVersionManagerApp(
        comfyui_path=comfyui_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )
    app.mainloop()
