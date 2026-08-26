"""Product version-manager application shell."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import (
    ttk,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    BranchInfo,
    CommitInfo,
    ExtensionIndexItem,
    ExtensionManager,
    ManagedExtension,
    RepositoryState,
    configure_git_env,
    list_branches,
)
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    BackgroundTaskMixin,
    apply_gui_theme,
    apply_window_icon,
    configure_gui_fonts,
)

from .helpers import _sd_webui_extension_enabled, _set_sd_webui_extension_enabled
from .extensions import ExtensionActionsMixin
from .install import InstallActionsMixin
from .kernel import KernelActionsMixin


class SDWebUiVersionManagerApp(tk.Tk, BackgroundTaskMixin, KernelActionsMixin, ExtensionActionsMixin, InstallActionsMixin):
    "Stable Diffusion WebUI 版本管理窗口\n\n提供内核版本管理、扩展启禁用、扩展更新、扩展卸载和扩展源安装功能。"

    def __init__(
        self,
        sd_webui_path: Path,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> None:
        """
        初始化 Stable Diffusion WebUI 版本管理窗口

        Args:
            sd_webui_path (Path):
                Stable Diffusion WebUI 根目录
            use_github_mirror (bool):
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
        self.kernel_commits: list[CommitInfo] = []
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

    def _list_branches_with_env(self, path: Path, fetch: bool) -> list[BranchInfo]:
        """
        读取分支列表

        Args:
            path (Path):
                Git 仓库路径
            fetch (bool):
                是否先拉取远程引用

        Returns:
            list[BranchInfo]: 分支列表
        """
        return list_branches(path, fetch=fetch)
