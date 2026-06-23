"""CLI 快照输出工具"""

import argparse
from pathlib import Path
from typing import Callable

from sd_webui_all_in_one.base_manager.snapshot import WebUiSnapshot, resolve_snapshot_output, save_snapshot
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME, SD_WEBUI_ALL_IN_ONE_SNAPSHOT_DIR
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.utils import normalized_filepath


SnapshotFactory = Callable[[], WebUiSnapshot]
"""快照构建函数"""

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def output_snapshot(
    snapshot_factory: SnapshotFactory,
    output: Path | None = None,
) -> Path:
    """输出或保存快照

    Args:
        snapshot_factory (SnapshotFactory):
            创建快照对象的回调。
        output (Path | None):
            快照输出路径或目录。

    Returns:
        Path: 已写入的快照文件路径。
    """
    logger.info("开始创建 WebUI 环境快照")
    snapshot = snapshot_factory()
    output_path = resolve_snapshot_output(snapshot, output)
    save_snapshot(snapshot, output_path)
    logger.info("快照已保存: %s", output_path)
    return output_path


def add_pre_operation_snapshot_arguments(parser: argparse.ArgumentParser) -> None:
    """为会修改环境的 CLI 子命令添加操作前快照参数

    Args:
        parser (argparse.ArgumentParser):
            需要添加参数的命令行解析器。
    """
    parser.add_argument("--no-snapshot", action="store_false", dest="snapshot_enabled", help="禁用操作前自动快照")
    parser.add_argument("--snapshot-dir", type=normalized_filepath, default=SD_WEBUI_ALL_IN_ONE_SNAPSHOT_DIR, dest="snapshot_dir", help="操作前自动快照目录")


def create_pre_operation_snapshot(
    snapshot_factory: SnapshotFactory,
    operation_name: str,
    snapshot_enabled: bool = True,
    snapshot_dir: Path | None = None,
    show_gui_warning: bool = False,
) -> Path | None:
    """在 CLI 操作前创建快照, 失败时记录警告并继续执行原操作

    Args:
        snapshot_factory (SnapshotFactory):
            创建快照对象的回调。
        operation_name (str):
            正在执行的操作名称。
        snapshot_enabled (bool):
            是否启用操作前自动快照。
        snapshot_dir (Path | None):
            快照文件目录。
        show_gui_warning (bool):
            是否在 GUI 中显示快照失败提示。

    Returns:
        Path | None: 已创建的快照文件路径；禁用或创建失败时返回 None。
    """
    if not snapshot_enabled:
        logger.info("已禁用操作前自动快照: %s", operation_name)
        return None

    try:
        output_path = output_snapshot(snapshot_factory, output=snapshot_dir)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("操作前自动快照创建失败, 将继续执行 '%s': %s", operation_name, e, exc_info=True)
        if show_gui_warning:
            _show_pre_operation_snapshot_warning(operation_name, e)
        return None

    logger.info("操作前自动快照创建完成 (%s): %s", operation_name, output_path)
    return output_path


def _show_pre_operation_snapshot_warning(operation_name: str, error: Exception) -> None:
    """在 GUI 启动前显示自动快照失败提示"""
    root = None
    try:
        import tkinter as tk  # pylint: disable=import-outside-toplevel
        from tkinter import messagebox  # pylint: disable=import-outside-toplevel

        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "快照创建失败",
            f"'{operation_name}' 前自动快照创建失败, 将继续启动版本管理器。\n\n{error}",
            parent=root,
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.debug("显示自动快照失败提示时发生错误: %s", e, exc_info=True)
    finally:
        if root is not None:
            root.destroy()
