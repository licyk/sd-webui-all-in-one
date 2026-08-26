"""Product-specific version GUI helpers."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path
from sd_webui_all_in_one.file_manager import move_files


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
