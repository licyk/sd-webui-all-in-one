"""分组镜像的磁盘空间规划工具"""

import shutil
from pathlib import Path

from sd_webui_all_in_one.repo_manager.types import MirrorGroupTask


def _format_size(size: int | None) -> str:
    if size is None:
        return "未知大小"
    value = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(value) < 1024:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024
    return f"{value:.2f} TB"


def _get_free_disk_space(path: Path) -> int:
    """获取路径所在磁盘的剩余空间 (字节), 路径不存在时使用最近的已存在父目录"""
    path = Path(path).absolute()
    while not path.exists() and path.parent != path:
        path = path.parent
    return shutil.disk_usage(path).free


def _plan_mirror_group(
    pending: list[MirrorGroupTask],
    group_size: int,
    budget: int,
) -> tuple[list[MirrorGroupTask], list[MirrorGroupTask]]:
    """根据可用磁盘空间规划下一组镜像任务

    按源仓库顺序进行首次适应 (first-fit) 选择, 放不下的文件保留到后续分组。
    大小未知的文件只会单独成组, 以便在大小估计失误时将影响限制在单个文件内。

    Args:
        pending (list[MirrorGroupTask]):
            待镜像的任务列表
        group_size (int):
            单组最大文件数量
        budget (int):
            本组可使用的磁盘空间 (字节)

    Returns:
        tuple[list[MirrorGroupTask], list[MirrorGroupTask]]:
            (本组任务, 单独占用空间也超过可用空间而无法调度的任务)
    """
    group: list[MirrorGroupTask] = []
    too_large: list[MirrorGroupTask] = []
    used = 0
    for task in pending:
        size = task[1]
        if size is None:
            if not group:
                return [task], too_large
            continue
        if size > budget:
            too_large.append(task)
            continue
        if len(group) >= group_size or used + size > budget:
            continue
        group.append(task)
        used += size
    return group, too_large
