"""CLI 快照输出工具"""

import json
from pathlib import Path
from typing import Callable

from sd_webui_all_in_one.base_manager.snapshot import WebUiSnapshot, save_snapshot, snapshot_to_dict
from sd_webui_all_in_one.logger import silence_logger_output


SnapshotFactory = Callable[[], WebUiSnapshot]
"""快照构建函数"""


def output_snapshot(
    snapshot_factory: SnapshotFactory,
    output: Path | None = None,
) -> None:
    """输出或保存快照"""
    if output is None:
        silence_logger_output()

    snapshot = snapshot_factory()
    if output is None:
        print(json.dumps(snapshot_to_dict(snapshot), ensure_ascii=False, indent=2))
    else:
        save_snapshot(snapshot, output)
