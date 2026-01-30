"""Kaggle 工具集"""

from pathlib import Path

from sd_webui_all_in_one.file_operations.file_manager import copy_files, generate_dir_tree
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR

logger = get_logger(
    name="Kaggle Tools",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def get_kaggle_secret(key: str) -> str | None:
    """获取 Kaggle Secret

    Args:
        key (str): Kaggle Secret 名称
    Returns:
        (str | None): Kaggle Secret 名称对应的密钥
    """
    try:
        from kaggle_secrets import UserSecretsClient  # pylint: disable=import-error  # type: ignore
    except Exception as e:
        logger.error("无法导入 Kaggle 工具, 获取 Kaggle Secret 失败: %s", e)
        return None

    try:
        return UserSecretsClient().get_secret(key)
    except Exception:
        logger.error("密钥 %s 不存在")
        return None


def import_kaggle_input(
    output_path: Path | str,
) -> None:
    """从 Kaggle Input 文件夹中导入文件

    Args:
        output_path (Path|str): 导出文件的路径
    """
    kaggle_input_path = Path("/kaggle/input")
    output_path = Path(output_path) if not isinstance(output_path, Path) and output_path is not None else output_path
    logger.info("从 Kaggle Input 导入文件: %s -> %s", kaggle_input_path, output_path)
    if kaggle_input_path.is_dir() and any(kaggle_input_path.iterdir()):
        count = 0
        task_sum = sum(1 for _ in kaggle_input_path.iterdir())
        for i in kaggle_input_path.iterdir():
            count += 1
            logger.info("[%s/%s] 导入 %s", count, task_sum, i.name)
            copy_files(i, output_path)
        logger.info("Kaggle Input 导入完成")
        return
    logger.info("Kaggle Input 无可导入的文件")


def display_model_and_dataset_dir(
    model_path: Path | str = None,
    dataset_path: Path | str = None,
    recursive: bool | None = False,
    show_hidden: bool | None = True,
) -> None:
    """列出模型文件夹和数据集文件夹的文件列表

    Args:
        model_path (Path | str | None): 要展示的路径
        dataset_path (Path | str | None): 要展示的路径
        recursive (bool | None): 递归显示子目录的内容
        show_hidden (bool | None)`: 显示隐藏文件
    """
    model_path = Path(model_path) if not isinstance(model_path, Path) and model_path is not None else model_path
    dataset_path = Path(dataset_path) if not isinstance(dataset_path, Path) and dataset_path is not None else dataset_path
    if model_path is not None and model_path.is_dir():
        logger.info("模型目录中的文件列表")
        generate_dir_tree(
            start_path=model_path,
            max_depth=None if recursive else 1,
            show_hidden=show_hidden,
        )
    else:
        logger.info("模型目录不存在")

    if dataset_path is not None and dataset_path.is_dir():
        logger.info("数据集目录中的文件列表")
        generate_dir_tree(
            start_path=dataset_path,
            max_depth=None if recursive else 1,
            show_hidden=show_hidden,
        )
    else:
        logger.info("数据集目录不存在")
