"""Numpy 版本检查与修复"""

import importlib.metadata
import sys

from sd_webui_all_in_one.pkg_manager import pip_install
from sd_webui_all_in_one.package_analyzer import Version
from sd_webui_all_in_one.env_check.shared import logger


def check_numpy(
    use_uv: bool = True,
    custom_env: dict[str, str] | None = None,
) -> None:
    """检查 Numpy 是否需要降级

    Args:
        use_uv (bool):
            是否使用 uv 安装依赖
        custom_env (dict[str, str] | None):
            环境变量字典

    Raises:
        RuntimeError:
            检查 Numpy 版本时出现错误
    """
    logger.info("检查 Numpy 是否需要降级")
    if sys.version_info >= (3, 12):
        logger.info("Python 版本大于等于 3.12, 跳过 Numpy 版本检查")
        return

    try:
        numpy_ver = importlib.metadata.version("numpy")
        if Version.parse(numpy_ver) >= Version.parse("2"):
            logger.info("降级 Numpy 中")
            pip_install("numpy<2", use_uv=use_uv, custom_env=custom_env)
            logger.info("Numpy 降级完成")
        else:
            logger.info("Numpy 无需降级")
    except Exception as e:
        logger.error("检查 Numpy 时出现错误: %s", e)
        raise RuntimeError(f"检查 Numpy 时出现错误: {e}") from e
