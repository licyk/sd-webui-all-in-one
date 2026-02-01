"""Numpy 检查工具"""

import importlib.metadata

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.pkg_manager import pip_install
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR
from sd_webui_all_in_one.package_analyzer.py_ver_cmp import PyWhlVersionComparison


logger = get_logger(
    name="Numpy Check",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def check_numpy(
    use_uv: bool | None = True,
) -> None:
    """检查 Numpy 是否需要降级

    Args:
        use_uv (bool| None):
            是否使用 uv 安装依赖

    Raises:
        RuntimeError:
            检查 Numpy 版本时出现错误
    """
    logger.info("检查 Numpy 是否需要降级")
    try:
        numpy_ver = importlib.metadata.version("numpy")
        if PyWhlVersionComparison(numpy_ver) > PyWhlVersionComparison("1.26.4"):
            logger.info("降级 Numoy 中")
            pip_install("numpy==1.26.4", use_uv=use_uv)
            logger.info("Numpy 降级完成")
        else:
            logger.info("Numpy 无需降级")
    except Exception as e:
        logger.error("检查 Numpy 时出现错误: %s", e)
        raise RuntimeError(f"检查 Numpy 时出现错误: {e}") from e
