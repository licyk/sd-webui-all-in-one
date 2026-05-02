"""InvokeAI 版本管理 GUI"""

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments
# pylint: disable=attribute-defined-outside-init

from __future__ import annotations

import importlib.metadata
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from sd_webui_all_in_one.base_manager.invokeai_base import install_invokeai_component
from sd_webui_all_in_one.base_manager.version_manager import (
    CommitInfo,
    ExtensionManager,
    ManagedExtension,
    PackageVersionInfo,
    configure_git_env,
    fetch_pypi_versions,
    list_branches,
    list_commits,
    switch_repository_branch,
    switch_repository_commit,
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
from sd_webui_all_in_one.file_operations import move_files
from sd_webui_all_in_one.mirror_manager import get_pypi_mirror_config


def _get_invokeai_version() -> str | None:
    try:
        return importlib.metadata.version("invokeai")
    except Exception:
        return None


def _invokeai_node_enabled(_name: str, path: Path) -> bool:
    return (path / "__init__.py").is_file()


def _set_invokeai_node_enabled(
    nodes_path: Path,
    name: str,
    enabled: bool,
) -> None:
    init_py = nodes_path / name / "__init__.py"
    init_bak_py = nodes_path / name / "__init__.py.bak"
    if enabled:
        if init_bak_py.is_file() and not init_py.is_file():
            move_files(init_bak_py, init_py)
    else:
        if init_py.is_file():
            move_files(init_py, init_bak_py)


class InvokeAiVersionManagerApp(tk.Tk, BackgroundTaskMixin):
    """
    InvokeAI 版本管理窗口

    使用 PyPI 版本列表管理 InvokeAI 内核版本, 并提供本地节点的 Git URL 安装和管理功能。
    """

    def __init__(
        self,
        invokeai_path: Path,
        use_pypi_mirror: bool | None = False,
        use_uv: bool | None = True,
        use_github_mirror: bool | None = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> None:
        """
        初始化 InvokeAI 版本管理窗口

        Args:
            invokeai_path (Path):
                InvokeAI 根目录
            use_pypi_mirror (bool | None):
                是否启用 PyPI 镜像源
            use_uv (bool | None):
                是否使用 uv 安装软件包
            use_github_mirror (bool | None):
                是否启用 GitHub 镜像源
            custom_github_mirror (str | list[str] | None):
                自定义 GitHub 镜像源
        """
        tk.Tk.__init__(self)
        BackgroundTaskMixin.__init__(self)
        self.invokeai_path = Path(invokeai_path)
        self.nodes_path = self.invokeai_path / "nodes"
        self.use_pypi_mirror = use_pypi_mirror
        self.use_uv = use_uv
        self.use_github_mirror = use_github_mirror
        self.custom_github_mirror = custom_github_mirror
        self.git_env = configure_git_env(use_github_mirror=self.use_github_mirror, custom_github_mirror=self.custom_github_mirror)
        self.pypi_env = get_pypi_mirror_config(use_cn_mirror=self.use_pypi_mirror)
        self.pypi_index_url = self.pypi_env.get("PIP_INDEX_URL", "https://pypi.org/pypi")
        self.current_version: str | None = None
        self.package_versions: list[PackageVersionInfo] = []
        self.extensions: list[ManagedExtension] = []
        self.extension_manager = ExtensionManager(
            root_path=self.invokeai_path,
            extension_dir_name="nodes",
            is_enabled=_invokeai_node_enabled,
            set_enabled=lambda name, enabled: _set_invokeai_node_enabled(self.nodes_path, name, enabled),
        )

        self.title("InvokeAI 版本管理")
        apply_window_icon(self)
        self.geometry("1180x720")
        self.minsize(940, 560)
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
        ttk.Label(top, text=f"路径: {self.invokeai_path}").pack(side=tk.LEFT, padx=10, pady=8)
        ttk.Button(top, text="刷新列表", command=self.refresh_all).pack(side=tk.RIGHT, padx=(0, 10), pady=8)
        ttk.Button(top, text="更新到最新版", command=self.update_kernel).pack(side=tk.RIGHT, padx=(0, 8), pady=8)

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
        self.package_name_var = tk.StringVar(value="invokeai")
        self.kernel_version_var = tk.StringVar(value="-")
        self.kernel_status_var = tk.StringVar(value="-")
        for row, (label, var) in enumerate((("PyPI 包:", self.package_name_var), ("当前版本:", self.kernel_version_var), ("状态:", self.kernel_status_var))):
            ttk.Label(info_frame, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
            ttk.Label(info_frame, textvariable=var).grid(row=row, column=1, sticky=tk.W, padx=(16, 0), pady=4)
        info_frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(self.kernel_tab)
        button_frame.pack(fill=tk.X, padx=18, pady=(0, 8))
        ttk.Button(button_frame, text="更新到最新版", command=self.update_kernel).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="切换版本", command=self.open_kernel_version_dialog).pack(side=tk.LEFT, padx=(8, 0))

        self.kernel_version_tree = SearchableTree(
            self.kernel_tab,
            columns=("version", "summary", "date", "current"),
            headings={"version": "版本", "summary": "说明", "date": "发布时间", "current": "当前"},
            widths={"version": 150, "summary": 600, "date": 220, "current": 80},
            search_placeholder="搜索 InvokeAI 版本...",
        )
        self.kernel_version_tree.pack(fill=tk.BOTH, expand=True)

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
            headings={"enabled": "启用", "name": "扩展名", "url": "远程地址", "branch": "当前分支", "commit": "版本 ID", "date": "更新日期", "state": "状态"},
            widths={"enabled": 60, "name": 250, "url": 420, "branch": 120, "commit": 90, "date": 170, "state": 120},
            search_placeholder="搜索已安装扩展...",
        )
        self.extension_tree.pack(fill=tk.BOTH, expand=True)
        self.extension_tree.search_var.trace_add("write", lambda *_args: self.render_extensions())

    def _create_install_tab(
        self,
    ) -> None:
        panel = ttk.Frame(self.install_tab)
        panel.pack(fill=tk.X, padx=18, pady=18)
        ttk.Label(panel, text="扩展 Git URL:").pack(side=tk.LEFT)
        self.install_url_var = tk.StringVar()
        self.install_url_placeholder = "输入 InvokeAI 扩展 Git URL，例如 https://github.com/user/invokeai-node"
        entry = ttk.Entry(panel, textvariable=self.install_url_var)
        entry.insert(0, self.install_url_placeholder)
        entry.bind("<FocusIn>", self._clear_install_url_placeholder)
        entry.bind("<FocusOut>", self._restore_install_url_placeholder)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        ttk.Button(panel, text="安装", command=self.install_from_url).pack(side=tk.LEFT)

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

    def refresh_all(
        self,
    ) -> None:
        """
        刷新内核版本和扩展列表
        """
        self.refresh_kernel()
        self.refresh_extensions()

    def refresh_kernel(
        self,
    ) -> None:
        """
        刷新 InvokeAI 内核版本列表
        """
        self.run_background("刷新 InvokeAI 版本中...", self._load_kernel_versions, self._apply_kernel_versions)

    def _load_kernel_versions(self) -> list[PackageVersionInfo]:
        self.current_version = _get_invokeai_version()
        return fetch_pypi_versions("invokeai", current_version=self.current_version, index_url=self.pypi_index_url)

    def _apply_kernel_versions(
        self,
        versions: list[PackageVersionInfo],
    ) -> None:
        self.package_versions = versions
        self.kernel_version_var.set(self.current_version or "未安装")
        self.kernel_status_var.set("已安装" if self.current_version else "未安装 invokeai 包")
        self.kernel_version_tree.clear()
        for version in versions:
            self.kernel_version_tree.tree.insert(
                "",
                tk.END,
                iid=version.version,
                values=(version.version, version.summary, version.upload_time, "✓" if version.is_current else ""),
            )

    def update_kernel(
        self,
    ) -> None:
        """
        更新 InvokeAI 内核包
        """
        self.run_background(
            "更新 InvokeAI 中...",
            lambda: install_invokeai_component(upgrade=True, use_pypi_mirror=self.use_pypi_mirror, use_uv=self.use_uv),
            lambda _value: self.refresh_kernel(),
        )

    def open_kernel_version_dialog(
        self,
    ) -> None:
        """
        打开 InvokeAI 版本切换弹窗
        """
        if not self.package_versions:
            messagebox.showwarning("无版本列表", "请先刷新版本列表")
            return
        commits = [CommitInfo(commit=item.version, message=item.summary, date=item.upload_time, is_current=item.is_current) for item in self.package_versions]
        CommitSwitchDialog(self, "InvokeAI 版本切换", commits, lambda item: self._switch_kernel_version(item.commit))

    def _switch_kernel_version(
        self,
        version: str,
    ) -> None:
        """
        切换 InvokeAI 内核版本

        Args:
            version (str):
                目标版本号
        """
        self.run_background(
            "切换 InvokeAI 版本中...",
            lambda: install_invokeai_component(invokeai_version=version, use_pypi_mirror=self.use_pypi_mirror, use_uv=self.use_uv),
            lambda _value: self.refresh_kernel(),
        )

    def refresh_extensions(
        self,
    ) -> None:
        """
        刷新 InvokeAI 扩展列表
        """
        self.run_background("刷新扩展列表中...", self.extension_manager.list_extensions, self._apply_extensions)

    def _apply_extensions(
        self,
        extensions: list[ManagedExtension],
    ) -> None:
        self.extensions = extensions
        self.render_extensions()

    def _extension_values(self, ext: ManagedExtension) -> tuple[str, str, str, str, str, str, str]:
        return ("✓" if ext.enabled else "", ext.name, ext.url or "-", ext.branch or "-", ext.commit or "-", ext.commit_date or "-", "Git 仓库" if ext.is_git_repo else (ext.error or "非 Git 仓库"))

    def render_extensions(
        self,
    ) -> None:
        """
        渲染 InvokeAI 扩展列表
        """
        keyword = self.extension_tree.search_var.get().strip().lower()
        if keyword == "搜索已安装扩展...":
            keyword = ""
        self.extension_tree.clear()
        for ext in self.extensions:
            haystack = " ".join(str(x or "") for x in (ext.name, ext.url, ext.branch, ext.commit, ext.commit_date, ext.error)).lower()
            if keyword and keyword not in haystack:
                continue
            self.extension_tree.tree.insert("", tk.END, iid=ext.name, values=self._extension_values(ext))

    def _selected_extension(self) -> ManagedExtension | None:
        selected_id = self.extension_tree.selected_item_id()
        if not selected_id:
            messagebox.showwarning("请选择扩展", "请先选择一个扩展")
            return None
        return next((ext for ext in self.extensions if ext.name == selected_id), None)

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
        self.run_background("更新扩展中...", lambda: self.extension_manager.update_extension(ext.name), lambda _value: self.refresh_extensions())

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
            "修改扩展状态中...", lambda: self.extension_manager.set_extension_enabled(ext.name, not ext.enabled), lambda _value: self._apply_extension_enabled(ext.name, not ext.enabled)
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
        self.run_background("切换扩展版本中...", lambda: switch_repository_commit(self.nodes_path / name, commit), lambda _value: self.refresh_extensions())

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
        self.run_background("切换扩展分支中...", lambda: switch_repository_branch(self.nodes_path / name, branch), lambda _value: self.refresh_extensions())

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


def launch_invokeai_version_gui(
    invokeai_path: Path,
    use_pypi_mirror: bool | None = False,
    use_uv: bool | None = True,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """
    启动 InvokeAI 版本管理 GUI

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        use_pypi_mirror (bool | None):
            是否启用 PyPI 镜像源
        use_uv (bool | None):
            是否使用 uv 安装软件包
        use_github_mirror (bool | None):
            是否启用 GitHub 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源
    """
    app = InvokeAiVersionManagerApp(
        invokeai_path=invokeai_path,
        use_pypi_mirror=use_pypi_mirror,
        use_uv=use_uv,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )
    app.mainloop()
