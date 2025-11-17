"""文件操作工具"""

import os
import uuid
import stat
import shutil
import traceback
from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR

logger = get_logger(
    name="File Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def remove_files(path: str | Path) -> bool:
    """文件删除工具

    Args:
        path (str | Path): 要删除的文件路径
    Returns:
        bool: 删除结果
    """

    def _handle_remove_readonly(_func, _path, _):
        """处理只读文件的错误处理函数"""
        if os.path.exists(_path):
            os.chmod(_path, stat.S_IWRITE)
            _func(_path)

    try:
        path_obj = Path(path)
        if path_obj.is_file():
            os.chmod(path_obj, stat.S_IWRITE)
            path_obj.unlink()
            return True
        if path_obj.is_dir():
            shutil.rmtree(path_obj, onerror=_handle_remove_readonly)
            return True

        logger.error("路径不存在: %s", path)
        return False
    except Exception as e:
        logger.error("删除失败: %s", e)
        return False


def copy_files(src: Path | str, dst: Path | str) -> bool:
    """复制文件或目录

    Args:
        src (Path | str): 源文件路径
        dst (Path | str): 复制文件到指定的路径
    Returns:
        bool: 复制结果
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)

        # 检查源是否存在
        if not src_path.exists():
            logger.error("源路径不存在: %s", src)
            return False

        # 如果目标是目录, 创建完整路径
        if dst_path.is_dir():
            dst_file = dst_path / src_path.name
        else:
            dst_file = dst_path

        # 确保目标目录存在
        dst_file.parent.mkdir(parents=True, exist_ok=True)

        # 复制文件
        if src_path.is_file():
            shutil.copy2(src, dst_file)
        else:
            # 如果是目录, 使用 copytree
            if dst_file.exists():
                shutil.rmtree(dst_file)
            shutil.copytree(src, dst_file)

        return True
    except PermissionError as e:
        logger.error("权限错误, 请检查文件权限或以管理员身份运行: %s", e)
        return False
    except Exception as e:
        logger.error("复制失败: %s", e)
        return False


def generate_dir_tree(
    start_path: str | Path,
    max_depth: int | None = None,
    show_hidden: bool | None = False,
) -> None:
    """生成并打印目录树

    Args:
        start_path (str | Path): 要开始遍历的根目录路径
        max_depth (int | None): 要遍历的最大深度
        show_hidden (bool | None): 是否显示隐藏文件
    """
    start_path = Path(start_path) if not isinstance(start_path, Path) and start_path is not None else start_path
    if not start_path.is_dir():
        logger.error("目录 %s 不存在", start_path)
        return

    print(start_path)
    # 使用一个列表来传递计数, 因为列表是可变对象, 可以在递归中被修改
    counts = [0, 0]  # [目录数, 文件数]
    recursive_tree_builder(start_path, "", counts, 0, max_depth, show_hidden)
    print(f"\n{counts[0]} 个目录, {counts[1]} 个文件")


def recursive_tree_builder(
    dir_path: Path,
    prefix: str,
    counts: list[int],
    current_depth: int,
    max_depth: int | None,
    show_hidden: bool | None,
) -> None:
    """递归地构建和打印目录树

    Args:
        dir_path (Path): 当前正在遍历的目录路径
        prefix (str): 用于当前行打印的前缀字符串 (包含树状连接符)
        counts (list[int]): 包含目录和文件计数的列表
        current_depth (int): 当前的递归深度
        max_depth (int | None): 允许的最大递归深度
        show_hidden (bool | None): 是否显示隐藏文件
    """
    connectors_dict = {
        "T": "├── ",
        "L": "└── ",
        "I": "│   ",
        "S": "    ",
    }
    if max_depth is not None and current_depth >= max_depth:
        return

    try:
        # 获取目录下所有条目
        all_entries = dir_path.iterdir()

        # 如果不显示隐藏文件, 则过滤掉它们
        if not show_hidden:
            entries_to_process = [e for e in all_entries if not e.name.startswith(".")]
        else:
            entries_to_process = list(all_entries)

        # 按名称排序
        entries = sorted(entries_to_process, key=lambda p: p.name)

    except PermissionError:
        print(f"{prefix}└── [权限错误, 无法访问]")
        return

    num_entries = len(entries)

    for i, entry in enumerate(entries):
        is_last = i == num_entries - 1
        connector = connectors_dict["L"] if is_last else connectors_dict["T"]

        print(f"{prefix}{connector}{entry.name}")

        if entry.is_dir():
            counts[0] += 1
            # 递归调用的前缀: 如果当前是最后一个条目, 则下一级不再需要垂直线
            new_prefix = prefix + (connectors_dict["S"] if is_last else connectors_dict["I"])
            recursive_tree_builder(entry, new_prefix, counts, current_depth + 1, max_depth, show_hidden)
        else:
            counts[1] += 1


def get_file_list(path: Path | str, resolve: bool | None = False) -> list[Path]:
    """获取当前路径下的所有文件的绝对路径

    Args:
        path (Path | str): 要获取文件列表的目录
        resolve (bool | None): 将路径进行完全解析, 包括链接路径
    Returns:
        list[Path]: 文件列表的绝对路径
    """
    path = Path(path) if not isinstance(path, Path) and path is not None else path

    if not path.exists():
        return []

    if path.is_file():
        return [path.resolve() if resolve else path.absolute()]

    file_list: list[Path] = []
    for root, _, files in os.walk(path):
        for file in files:
            file_path = Path(root) / file
            file_list.append(file_path.resolve() if resolve else file_path.absolute())

    return file_list


def get_sync_files(src_path: Path | str, dst_path: Path | str) -> list[Path]:
    """获取需要进行同步的文件列表 (增量同步)

    Args:
        src_path (Path | str): 同步文件的源路径
        dst_path (Path | str): 同步文件到的路径
    Returns:
        list[Path]: 要进行同步的文件
    """
    from tqdm import tqdm

    if not isinstance(src_path, Path) and src_path is not None:
        src_path = Path(src_path)

    if not isinstance(dst_path, Path) and dst_path is not None:
        dst_path = Path(dst_path)

    src_is_file = src_path.is_file()
    src_files = get_file_list(src_path)
    logger.info("%s 中的文件数量: %s", src_path, len(src_files))
    dst_files = get_file_list(dst_path)
    logger.info("%s 中的文件数量: %s", dst_path, len(dst_files))
    if src_path.is_dir() and dst_path.is_file():
        logger.warning("%s 为目录, 而 %s 为文件, 无法进行复制", src_path, dst_path)
        sync_file_list = []
    else:
        dst_files_set = set(dst_files)  # 加快统计速度
        sync_file_list = [
            x for x in tqdm(src_files, desc="计算需要同步的文件") if (dst_path / x.relative_to(src_path if not src_is_file else src_path.parent)) not in dst_files_set
        ]
    logger.info("要进行同步的文件数量: %s", len(sync_file_list))
    return sync_file_list


def sync_files(src_path: Path, dst_path: Path) -> None:
    """同步文件 (增量同步)

    Args:
        src_path (Path): 同步文件的源路径
        dst_path (Path): 同步文件到的路径
    """
    from tqdm import tqdm

    logger.info("增量同步文件: %s -> %s", src_path, dst_path)
    file_list = get_sync_files(src_path, dst_path)
    if len(file_list) == 0:
        logger.info("没有需要同步的文件")
        return
    for file in tqdm(file_list, desc="同步文件"):
        dst = dst_path / file.relative_to(src_path)
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(file, dst)
        except Exception as e:
            traceback.print_exc()
            logger.error("同步 %s 到 %s 时发生错误: %s", file, dst, e)
            if dst.exists():
                logger.warning("删除未复制完成的文件: %s", dst)
                try:
                    os.remove(dst)
                except Exception as e1:
                    logger.error("删除未复制完成的文件失败: %s", e1)

    logger.info("同步文件完成")


def sync_files_and_create_symlink(
    src_path: Path | str,
    link_path: Path | str,
    src_is_file: bool | None = False,
) -> None:
    """同步文件并创建软链接

    当源路径不存在时, 则尝试创建源路径, 并检查链接路径状态

    链接路径若已存在, 并且存在文件, 将检查链接路径中的文件是否存在于源路径中

    在链接路径存在但在源路径不存在的文件将被复制 (增量同步)

    完成增量同步后将链接路径属性, 若为实际路径则对该路径进行重命名; 如果为链接路径则删除链接

    链接路径清理完成后, 在链接路径为源路径创建软链接

    Args:
        src_path (Path | str): 源路径
        link_path (Path | str): 软链接路径
        src_is_file (bool | None): 源路径是否为文件
    """
    src_path = Path(src_path) if not isinstance(src_path, Path) and src_path is not None else src_path
    link_path = Path(link_path) if not isinstance(link_path, Path) and link_path is not None else link_path
    logger.info("链接路径: %s -> %s", src_path, link_path)
    try:
        if src_is_file:
            src_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            src_path.mkdir(parents=True, exist_ok=True)
        if link_path.exists():
            sync_files(
                src_path=link_path,
                dst_path=src_path if not src_is_file else src_path.parent,
            )
            if link_path.is_symlink():
                link_path.unlink()
            else:
                shutil.move(
                    link_path,
                    link_path.parent / str(uuid.uuid4()),
                )
        link_path.symlink_to(src_path)
    except Exception as e:
        logger.error("创建 %s -> %s 的路径链接失败: %s", src_path, link_path, e)
