"""CLI 快照输出工具"""

from pathlib import Path
from typing import Callable

from sd_webui_all_in_one.base_manager.snapshot import WebUiSnapshot, resolve_snapshot_output, save_snapshot
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger


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
    """输出或保存快照"""
    snapshot = snapshot_factory()
    output_path = resolve_snapshot_output(snapshot, output)
    save_snapshot(snapshot, output_path)
    logger.info("快照已保存: %s", output_path)
    return output_path
