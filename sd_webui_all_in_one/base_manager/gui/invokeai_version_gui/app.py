"""Product version-manager application shell."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import (
    ttk,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    ExtensionManager,
    ManagedExtension,
    PackageVersionInfo,
    configure_git_env,
)
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    BackgroundTaskMixin,
    apply_gui_theme,
    apply_window_icon,
    configure_gui_fonts,
)
from sd_webui_all_in_one.mirror_manager import get_pypi_mirror_config

from .helpers import _invokeai_node_enabled, _set_invokeai_node_enabled
from .extensions import ExtensionActionsMixin
from .install import InstallActionsMixin
from .kernel import KernelActionsMixin


class InvokeAiVersionManagerApp(tk.Tk, BackgroundTaskMixin, KernelActionsMixin, ExtensionActionsMixin, InstallActionsMixin):
    "InvokeAI 版本管理窗口\n\n使用 PyPI 版本列表管理 InvokeAI 内核版本, 并提供本地节点的 Git URL 安装和管理功能。"

    def __init__(
        self,
        invokeai_path: Path,
        use_pypi_mirror: bool = False,
        use_uv: bool = True,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> None:
        """
        初始化 InvokeAI 版本管理窗口

        Args:
            invokeai_path (Path):
                InvokeAI 根目录
            use_pypi_mirror (bool):
                是否启用 PyPI 镜像源
            use_uv (bool):
                是否使用 uv 安装软件包
            use_github_mirror (bool):
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
        刷新内核版本和扩展列表
        """
        self.refresh_kernel()
        self.refresh_extensions()
