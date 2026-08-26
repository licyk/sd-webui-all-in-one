"""Kernel behavior for the product version window."""

from __future__ import annotations

import tkinter as tk
from tkinter import (
    messagebox,
    ttk,
)
from sd_webui_all_in_one.base_manager.invokeai_base import install_invokeai_component
from sd_webui_all_in_one.base_manager.version_manager import (
    CommitInfo,
    PackageVersionInfo,
    fetch_pypi_versions,
)
from sd_webui_all_in_one.base_manager.gui.version_gui import (
    CommitSwitchDialog,
    SearchableTree,
    package_version_matches_keyword,
)

from sd_webui_all_in_one.base_manager.gui.invokeai_version_gui.helpers import _get_invokeai_version


from sd_webui_all_in_one.base_manager.gui.version_gui import GuiActionsMixinContext


class KernelActionsMixin(GuiActionsMixinContext):
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
        self.kernel_version_tree.bind_search_change(self.render_kernel_versions)

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
        self.render_kernel_versions()

    def render_kernel_versions(
        self,
    ) -> None:
        """
        根据搜索条件渲染 InvokeAI 内核版本列表
        """
        keyword = self.kernel_version_tree.search_keyword()
        self.kernel_version_tree.clear()
        for version in self.package_versions:
            if not package_version_matches_keyword(version, keyword):
                continue
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
