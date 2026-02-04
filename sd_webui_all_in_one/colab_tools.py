"""Colab 工具集"""

from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR


logger = get_logger(
    name="Colab Tools",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def is_colab_environment() -> bool:
    """检测当前运行环境是否为 Colab

    参考: https://github.com/googlecolab/colabtools/blob/be426fedb0bf192ea3b4f208e2c8d956caf94d65/google/colab/drive.py#L114

    Returns:
        bool: 检测结果
    """
    return Path("/var/colab/hostname").exists()


def mount_google_drive(
    path: Path,
) -> bool:
    """挂载 Google Drive

    Args:
        path (Path):
            要挂在的路径

    Raises:
        RuntimeError:
            挂载 Google Drive 失败时
    """
    if not path.exists():
        logger.info("挂载 Google Drive 中, 请根据提示进行操作")
        try:
            from google.colab import drive

            drive.mount(path.as_posix())
            logger.info("Google Dirve 挂载完成")
        except Exception as e:
            logger.error("挂载 Google Drive 时出现问题: %e", e)
            raise RuntimeError(f"挂载 Google Drive 时出现问题: {e}") from e
    else:
        logger.info("Google Drive 已挂载")


def get_colab_secret(key: str) -> str | None:
    """获取 Colab 密钥

    Args:
        key (str): 密钥名称
    Returns:
        (str | None): 密钥名称对应的值
    """
    try:
        from google.colab import userdata
    except Exception as e:
        logger.error("导入 Colab 工具失败, 无法获取 Colab Secret: %s", e)
        return None

    try:
        return userdata.get(key)
    except Exception as e:
        logger.error("密钥 %s 不存在", e)
        return None
