"""Product version-manager application shell."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import (
    ttk,
)
from sd_webui_all_in_one.base_manager.comfyui_base import (
    ComfyUiExtensionManager,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    CommitInfo,
    ExtensionIndexItem,
    ManagedExtension,
    configure_git_env,
)
from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryState
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    BackgroundTaskMixin,
    apply_gui_theme,
    apply_window_icon,
    configure_gui_fonts,
)

from sd_webui_all_in_one.base_manager.gui.comfyui_version_gui.extensions import ExtensionActionsMixin
from sd_webui_all_in_one.base_manager.gui.comfyui_version_gui.install import InstallActionsMixin
from sd_webui_all_in_one.base_manager.gui.comfyui_version_gui.kernel import KernelActionsMixin


class ComfyUiVersionManagerApp(tk.Tk, BackgroundTaskMixin, KernelActionsMixin, ExtensionActionsMixin, InstallActionsMixin):
    "ComfyUI 版本管理窗口\n\n提供内核版本管理、自定义节点启禁用、自定义节点更新、卸载和安装功能。"

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
        self._manager_extension_index: list[ExtensionIndexItem] = []
        self._registry_extension_index: list[ExtensionIndexItem] = []
        self._extension_index_generation = 0
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
