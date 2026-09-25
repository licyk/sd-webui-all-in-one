"""Extension update-check display helpers for version-manager windows."""

from __future__ import annotations

import tkinter as tk
from tkinter import (
    messagebox,
    ttk,
)

from sd_webui_all_in_one.base_manager.version_manager import (
    ExtensionUpdateStatus,
    RepositoryUpdateStatus,
)
from sd_webui_all_in_one.base_manager.gui.version_gui.tasks import GuiActionsMixinContext

ExtensionCheckStatus = ExtensionUpdateStatus | RepositoryUpdateStatus
"""扩展管理器 `check_updates()` 返回的更新状态"""


def format_extension_update_state(status: ExtensionCheckStatus) -> str | None:
    """
    生成扩展更新检查结果的状态列文本。

    Args:
        status (ExtensionCheckStatus):
            扩展更新状态。

    Returns:
        str | None: 状态文本；扩展不支持更新检查时返回 None。
    """
    is_registry = isinstance(status, ExtensionUpdateStatus) and status.source_type == "comfy-registry"
    if (isinstance(status, ExtensionUpdateStatus) and status.skipped) or not (status.is_git_repo or is_registry):
        return None
    if status.error:
        return f"检查失败: {status.error.splitlines()[0]}"
    if not status.has_update:
        return "已是最新"
    if status.behind > 0:
        return f"有更新 (落后 {status.behind})"
    if is_registry and isinstance(status, ExtensionUpdateStatus) and status.current_version and status.latest_version:
        return f"有更新 ({status.current_version} → {status.latest_version})"
    return "有更新"


def summarize_extension_update_check(statuses: list[ExtensionCheckStatus]) -> str:
    """
    生成扩展更新检查结果摘要。

    Args:
        statuses (list[ExtensionCheckStatus]):
            扩展更新状态列表。

    Returns:
        str: 状态栏摘要文本。
    """
    checked = [status for status in statuses if format_extension_update_state(status) is not None]
    update_count = sum(status.has_update for status in checked)
    error_count = sum(bool(status.error) for status in checked)
    summary = f"检查更新完成: {update_count} 个有更新, 共检查 {len(checked)} 个"
    if error_count:
        summary += f", {error_count} 个检查失败"
    return summary


def summarize_updated_extensions(updated: list[str], kernel_updated: bool = False) -> str:
    """
    生成更新完成后的结果摘要。

    Args:
        updated (list[str]):
            实际发生更新的扩展名称列表。
        kernel_updated (bool):
            内核是否发生更新。

    Returns:
        str: 结果摘要文本。
    """
    lines: list[str] = []
    if kernel_updated:
        lines.append("内核已更新")
    if updated:
        lines.append(f"已更新 {len(updated)} 个扩展:")
        lines.extend(f"  • {name}" for name in updated)
    return "\n".join(lines) if lines else "所有项目均已是最新版本"


class ExtensionUpdateCheckMixin(GuiActionsMixinContext):
    """
    为扩展列表提供 "检查更新" 与 "更新可更新项" 两步更新流程

    使用方需要提供 `extension_manager` (含 `check_updates()` 与 `update_extensions(names, fetch)`),
    `extension_update_status` 字典, 以及 `render_extensions()` 和 `refresh_extensions()`。
    """

    def _create_update_check_buttons(
        self,
        toolbar: ttk.Frame,
    ) -> None:
        """
        在工具栏中添加检查更新相关按钮

        Args:
            toolbar (ttk.Frame):
                扩展工具栏
        """
        ttk.Button(toolbar, text="检查更新", command=self.check_extension_updates).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(toolbar, text="更新可更新项", command=self.update_available_extensions).pack(side=tk.LEFT, padx=(8, 0))

    def _extension_state_text(
        self,
        name: str,
        default: str,
    ) -> str:
        """
        获取扩展状态列文本, 存在更新检查结果时优先显示检查结果

        Args:
            name (str):
                扩展名称
            default (str):
                无检查结果时的状态文本

        Returns:
            str: 状态列文本
        """
        status = self.extension_update_status.get(name)
        return (format_extension_update_state(status) if status is not None else None) or default

    def check_extension_updates(
        self,
    ) -> None:
        """
        并行检查所有扩展的远程更新
        """
        self.run_background("检查扩展更新中...", self.extension_manager.check_updates, self._apply_extension_update_status)

    def _apply_extension_update_status(
        self,
        statuses: list[ExtensionCheckStatus],
    ) -> None:
        self.extension_update_status = {status.name: status for status in statuses}
        self.render_extensions()
        summary = summarize_extension_update_check(statuses)
        # 后台任务结束后状态栏会被重置为 "就绪", 延后设置以保留检查摘要
        self.after_idle(lambda: self.set_status(summary))

    def update_available_extensions(
        self,
    ) -> None:
        """
        仅更新上次检查中存在更新的扩展, 并复用检查时已拉取的远程引用
        """
        names = [name for name, status in self.extension_update_status.items() if status.has_update]
        if not names:
            messagebox.showinfo("没有可更新项", "没有检查到可更新的扩展, 请先点击 “检查更新”")
            return
        self.run_background(
            f"更新 {len(names)} 个扩展中...",
            lambda: self.extension_manager.update_extensions(names, fetch=False),
            self._on_extensions_updated,
        )

    def _on_extensions_updated(
        self,
        updated: list[str],
        kernel_updated: bool = False,
    ) -> None:
        self.extension_update_status = {}
        messagebox.showinfo("更新完成", summarize_updated_extensions(updated, kernel_updated=kernel_updated))
        self.refresh_extensions()

    def _forget_extension_update_status(
        self,
        name: str,
    ) -> None:
        self.extension_update_status.pop(name, None)
