"""Kaggle 工具集"""

from pathlib import Path

from sd_webui_all_in_one.file_operations.file_manager import copy_files
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR, LOGGER_NAME

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def get_kaggle_secret(key: str) -> str | None:
    """获取 Kaggle Secret

    Args:
        key (str):
            Kaggle Secret 名称
    Returns:
        (str | None):
            Kaggle Secret 名称对应的密钥
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
    output_path: Path,
) -> None:
    """从 Kaggle Input 文件夹中导入文件

    Args:
        output_path (Path):
            导出文件的路径
    """
    kaggle_input_path = Path("/kaggle/input")
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
