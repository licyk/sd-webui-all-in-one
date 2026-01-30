"""文件操作工具"""

import os
import uuid
import stat
import shutil
from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR

logger = get_logger(
    name="File Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def remove_files(
    path: Path,
) -> None:
    """文件删除工具, 支持删除只读文件和非空文件夹

    Args:
        path (str):
            要删除的文件或目录路径

    Raises:
        ValueError:
            路径不存在时
        OSError:
            删除过程中的系统错误
    """

    if not path.exists():
        logger.error("路径不存在: '%s'", path)
        raise ValueError(f"要删除的 {path} 路径不存在")

    def _handle_remove_readonly(
        func,
        path_str,
        _,
    ) -> None:
        """处理只读文件的错误处理函数"""
        if os.path.exists(path_str):
            os.chmod(path_str, stat.S_IWRITE)
            func(path_str)

    try:
        if path.is_file() or path.is_symlink():
            # 处理文件或符号链接
            os.chmod(path, stat.S_IWRITE)
            path.unlink()

        elif path.is_dir():
            # 处理文件夹
            shutil.rmtree(path, onerror=_handle_remove_readonly)

    except OSError as e:
        logger.error("删除失败: '%s' - 原因: %s", path, e)
        raise e


def copy_files(
    src: Path,
    dst: Path,
) -> None:
    """复制文件或目录

    Args:
        src (Path):
            源文件路径
        dst (Path):
            复制文件到指定的路径

    Raises:
        PermissionError:
            没有权限复制文件时
        OSError:
            复制文件失败时
        FileNotFoundError:
            源文件未找到时
        ValueError:
            路径逻辑错误（如循环复制）时
    """
    try:
        # 转换为绝对路径以进行准确的路径比对
        src_path = src.resolve()
        dst_path = dst.resolve()

        # 检查源是否存在
        if not src_path.exists():
            logger.error("源路径不存在: '%s'", src)
            raise FileNotFoundError(f"源路径不存在: {src}")

        # 防止递归复制（例如将目录复制到其自身的子目录中）
        if src_path.is_dir() and dst_path.is_relative_to(src_path):
            logger.error("不能将目录复制到自身或其子目录中: '%s'", src)
            raise ValueError(f"不能将目录复制到自身或其子目录中: {src}")

        # 如果目标是已存在的目录, 则在其下创建同名项
        if dst_path.exists() and dst_path.is_dir():
            dst_file = dst_path / src_path.name
        else:
            dst_file = dst_path

        # 确保目标父目录存在
        dst_file.parent.mkdir(parents=True, exist_ok=True)

        # 复制操作
        if src_path.is_file():
            # copy2 会尽量保留文件元数据
            shutil.copy2(src_path, dst_file)
        else:
            # symlinks=True: 保留软链接本身而非复制指向的内容
            # dirs_exist_ok=True: 实现合并逻辑，如果目标目录已存在则覆盖同名文件
            try:
                shutil.copytree(src_path, dst_file, symlinks=True, dirs_exist_ok=True)
            except shutil.Error:
                # Linux 中遇到已存在的软链接会导致失败, 则使用 symlinks=False 重试
                shutil.copytree(src_path, dst_file, symlinks=False, dirs_exist_ok=True)

    except PermissionError as e:
        logger.error("权限错误, 请检查文件权限或以管理员身份运行: %s", e)
        raise e
    except OSError as e:
        logger.error("复制失败: %s", e)
        raise e


def move_files(
    src: Path,
    dst: Path,
) -> None:
    """移动文件或目录

    Args:
        src (Path):
            源路径
        dst (Path):
            目标路径

    Raises:
        FileNotFoundError:
            源路径不存在时
        PermissionError:
            权限不足以移动文件时
        OSError:
            移动文件失败时
    """
    try:
        src_path = src.resolve()
        dst_path = dst.resolve()

        if not src_path.exists():
            logger.error("源路径不存在: '%s'", src)
            raise FileNotFoundError(f"源路径不存在: {src}")

        if src_path == dst_path:
            return

        # 确定目的路径
        if dst_path.exists() and dst_path.is_dir():
            final_dst = dst_path / src_path.name
        else:
            final_dst = dst_path

        if src_path.is_file() or src_path.is_symlink():
            if final_dst.is_file():
                remove_files(final_dst)

            final_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(final_dst))
            return

        if src_path.is_dir():
            if not final_dst.exists():
                final_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src_path), str(final_dst))
            elif not final_dst.is_dir():
                remove_files(final_dst)
                shutil.move(str(src_path), str(final_dst))
            else:
                logger.debug("目标目录已存在，执行合并操作: '%s' -> '%s'", src_path, final_dst)
                for item in src_path.iterdir():
                    move_files(item, final_dst / item.name)

                if src_path.exists():
                    src_path.rmdir()

    except PermissionError as e:
        logger.error("权限错误, 请检查文件权限或以管理员身份运行: %s", e)
        raise e
    except OSError as e:
        logger.error("移动失败: %s", e)
        raise e


def get_file_list(
    path: Path,
    resolve: bool | None = False,
    max_depth: int | None = -1,
    show_progress: bool | None = True,
    include_dirs: bool | None = False,
) -> list[Path]:
    """获取当前路径下的所有文件（和可选的目录）的绝对路径

    Args:
        path (Path): 要获取列表的目录
        resolve (bool | None): 将路径进行完全解析, 包括链接路径
        max_depth (int | None): 最大遍历深度, -1 表示不限制深度, 0 表示只遍历当前目录
        show_progress (bool | None): 是否显示 tqdm 进度条
        include_dirs (bool | None): 是否在结果中包含目录路径
    Returns:
        (list[Path]): 路径列表的绝对路径
    """
    from tqdm import tqdm

    if not path or not path.exists():
        return []

    if path.is_file():
        return [path.resolve() if resolve else path.absolute()]

    base_depth = len(path.resolve().parts)

    file_list: list[Path] = []
    with tqdm(desc=f"扫描目录 {path}", position=0, leave=True, disable=not show_progress) as dir_pbar:
        with tqdm(desc="发现条目数", position=1, leave=True, disable=not show_progress) as file_pbar:
            for root, dirs, files in os.walk(path):
                root_path = Path(root)
                current_depth = len(root_path.resolve().parts) - base_depth

                # 超过最大深度则阻止继续向下遍历
                if max_depth != -1 and current_depth >= max_depth:
                    # 如果需要包含目录, 虽然停止深挖, 但当前层的目录仍可加入
                    if include_dirs:
                        for d in dirs:
                            dir_path = root_path / d
                            file_list.append(dir_path.resolve() if resolve else dir_path.absolute())
                            file_pbar.update(1)
                    dirs.clear()
                else:
                    # 如果启用，将当前层级的目录加入列表
                    if include_dirs:
                        for d in dirs:
                            dir_path = root_path / d
                            file_list.append(dir_path.resolve() if resolve else dir_path.absolute())
                            file_pbar.update(1)

                for file in files:
                    file_path = root_path / file
                    file_list.append(file_path.resolve() if resolve else file_path.absolute())
                    file_pbar.update(1)

                dir_pbar.update(1)

    return file_list


def generate_dir_tree(
    start_path: Path,
    max_depth: int | None = None,
    show_hidden: bool | None = False,
) -> None:
    """生成并打印目录树

    Args:
        start_path (Path): 要开始遍历的根目录路径
        max_depth (int | None): 要遍历的最大深度
        show_hidden (bool | None): 是否显示隐藏文件
    """
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


def get_sync_files(
    src_path: Path,
    dst_path: Path,
) -> list[Path]:
    """获取需要进行同步的文件列表 (增量同步)

    Args:
        src_path (Path): 同步文件的源路径
        dst_path (Path): 同步文件到的路径

    Returns:
        list[Path]: 要进行同步的文件
    """
    from tqdm import tqdm

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
        src_path (Path):
            同步文件的源路径
        dst_path (Path):
            同步文件到的路径

    Raises:
        RuntimeError:
            同步文件发生错误时
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
        except (shutil.Error, PermissionError, IsADirectoryError, OSError) as e:
            logger.error("同步 %s 到 %s 时发生错误: %s", file, dst, e)
            if dst.exists():
                logger.warning("删除未复制完成的文件: %s", dst)
                try:
                    os.remove(dst)
                except Exception as e1:
                    logger.error("删除未复制完成的文件失败: %s", e1)
            raise RuntimeError(f"同步 '{src_path}' 到 '{dst_path}' 时发生错误: {e}") from e

    logger.info("同步文件完成")


def sync_files_and_create_symlink(
    src_path: Path,
    link_path: Path,
    src_is_file: bool | None = False,
) -> None:
    """同步文件并创建软链接

    当源路径不存在时, 则尝试创建源路径, 并检查链接路径状态

    链接路径若已存在, 并且存在文件, 将检查链接路径中的文件是否存在于源路径中

    在链接路径存在但在源路径不存在的文件将被复制 (增量同步)

    完成增量同步后将链接路径属性, 若为实际路径则对该路径进行重命名; 如果为链接路径则删除链接

    链接路径清理完成后, 在链接路径为源路径创建软链接

    Args:
        src_path (Path):
            源路径
        link_path (Path):
            软链接路径
        src_is_file (bool | None):
            源路径是否为文件

    Raises:
        RuntimeError:
            链接文件发生错误时
    """
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
    except (shutil.Error, PermissionError, IsADirectoryError, OSError, RuntimeError) as e:
        logger.error("创建 %s -> %s 的路径链接失败: %s", src_path, link_path, e)
        raise RuntimeError(f"创建 '{src_path}' -> '{link_path}' 的路径链接时发生错误: {e}") from e


def is_folder_empty(path: Path) -> None:
    """
    判断给定路径的文件夹是否为空

    Args:
        path (Path):
            文件夹路径

    Returns:
        bool:
            如果文件夹为空返回 True, 否则返回 False

    Raises:
        ValueError: 当目录不存在或者不是有效目录时
    """

    if not path.is_dir():
        raise ValueError(f"路径 '{path}' 不是有效的目录或不存在")

    return next(path.iterdir(), None) is None
