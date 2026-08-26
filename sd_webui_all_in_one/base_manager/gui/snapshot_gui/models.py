"""Implementation grouped from the former ``snapshot_gui.py`` module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SnapshotListItem:
    """快照列表项"""

    path: Path
    filename: str
    created_at: str
    created_at_display: str
    webui_name: str
    webui_type: str
    package_count: int
    extension_count: int
