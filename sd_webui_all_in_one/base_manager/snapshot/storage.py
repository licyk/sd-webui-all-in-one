"""Snapshot naming, persistence, listing, and deletion."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

from sd_webui_all_in_one.config import SD_WEBUI_ALL_IN_ONE_SNAPSHOT_DIR

from sd_webui_all_in_one.base_manager.snapshot.io import load_snapshot
from sd_webui_all_in_one.base_manager.snapshot.models import SavedSnapshot, SnapshotSummary, WebUiSnapshot, logger, snapshot_to_dict


def save_snapshot(snapshot: WebUiSnapshot, output: Path) -> Path:
    """保存快照 JSON 文件

    Args:
        snapshot (WebUiSnapshot):
            WebUI 环境快照。
        output (Path):
            快照输出路径或目录。

    Returns:
        Path: 已写入的快照文件路径。
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot_to_dict(snapshot), ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("快照已保存: %s", output)
    return output


def _safe_filename_part(value: str) -> str:
    part = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return part.strip("-._") or "snapshot"


def _snapshot_timestamp(snapshot: WebUiSnapshot) -> str:
    return _safe_filename_part(snapshot.created_at.replace(":", "").replace("+", ""))


def default_snapshot_output(snapshot: WebUiSnapshot, output_dir: Path | None = None) -> Path:
    """生成默认快照输出文件路径

    Args:
        snapshot (WebUiSnapshot):
            WebUI 环境快照。
        output_dir (Path | None):
            快照输出目录。

    Returns:
        Path: 默认快照输出路径。
    """
    if output_dir is None:
        output_dir = SD_WEBUI_ALL_IN_ONE_SNAPSHOT_DIR
    filename = f"{_safe_filename_part(snapshot.webui.type)}-{_snapshot_timestamp(snapshot)}.json"
    return output_dir / filename


def resolve_snapshot_output(snapshot: WebUiSnapshot, output_dir: Path | None = None) -> Path:
    """解析快照输出文件路径

    Args:
        snapshot (WebUiSnapshot):
            WebUI 环境快照。
        output_dir (Path | None):
            快照输出目录。

    Returns:
        Path: 最终快照输出路径。
    """
    if output_dir is None:
        return default_snapshot_output(snapshot)
    return default_snapshot_output(snapshot, output_dir=output_dir)


def list_webui_snapshots(
    webui_path: Path,
    snapshot_dir: Path | None = None,
) -> list[SnapshotSummary]:
    """列出 WebUI 的本地快照。

    Args:
        webui_path (Path): WebUI 根目录。
        snapshot_dir (Path | None): 快照目录，默认使用 ``<webui_path>/snapshots``。

    Returns:
        list[SnapshotSummary]: 按修改时间倒序排列的快照摘要。
    """
    directory = snapshot_dir or webui_path / "snapshots"
    if not directory.exists():
        logger.warning("快照目录不存在: %s", directory)
        return []

    logger.info("开始列出快照: %s", directory)
    summaries: list[SnapshotSummary] = []
    for item in sorted(directory.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True):
        logger.debug("读取快照文件: %s", item)
        try:
            snapshot = load_snapshot(item)
        except Exception as exc:
            logger.warning("无法解析快照文件: %s (%s)", item, exc)
            summaries.append(SnapshotSummary(path=item, filename=item.name, error=str(exc)))
            continue
        summaries.append(
            SnapshotSummary(
                path=item,
                filename=item.name,
                created_at=snapshot.created_at,
                webui_type=snapshot.webui.type,
                webui_name=snapshot.webui.name,
                package_count=len(snapshot.packages),
                extension_count=len(snapshot.extensions),
            )
        )
    logger.info("共找到 %s 个快照", len(summaries))
    return summaries


def create_webui_snapshot(
    webui_path: Path,
    snapshot_factory: Callable[[Path, bool], WebUiSnapshot],
    include_packages: bool = True,
    snapshot_dir: Path | None = None,
) -> SavedSnapshot:
    """采集并保存 WebUI 快照。

    ``snapshot_factory`` 由具体 WebUI 命名空间在注册时绑定，不对 API
    调用方公开。

    Args:
        webui_path (Path): WebUI 根目录。
        snapshot_factory (Callable[[Path, bool], WebUiSnapshot]): 对应 WebUI 的真实快照采集函数。
        include_packages (bool): 是否采集 Python 包。
        snapshot_dir (Path | None): 快照目录，默认使用 ``<webui_path>/snapshots``。

    Returns:
        SavedSnapshot: 保存路径和完整快照。
    """
    logger.info("开始创建 WebUI 快照: %s", webui_path)
    snapshot = snapshot_factory(webui_path, include_packages)
    output = default_snapshot_output(snapshot, output_dir=snapshot_dir or webui_path / "snapshots")
    save_snapshot(snapshot, output)
    logger.info("WebUI 快照创建完成: %s (包 %s 个, 扩展 %s 个)", output, len(snapshot.packages), len(snapshot.extensions))
    return SavedSnapshot(path=output, snapshot=snapshot)


def delete_snapshot(snapshot_path: Path) -> Path:
    """删除一个快照文件。

    Args:
        snapshot_path (Path): 快照文件路径。

    Returns:
        Path: 已删除的快照路径。

    Raises:
        FileNotFoundError: 快照文件不存在。
    """
    if not snapshot_path.is_file():
        logger.warning("快照文件不存在, 无法删除: %s", snapshot_path)
        raise FileNotFoundError(f"Snapshot not found: {snapshot_path}")
    snapshot_path.unlink()
    logger.info("快照已删除: %s", snapshot_path)
    return snapshot_path
