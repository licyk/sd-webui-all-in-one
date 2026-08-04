"""CLI 环境信息报告输出工具。"""

from pathlib import Path
from typing import Callable

from sd_webui_all_in_one.base_manager.environment_info import WebUiEnvironmentInfo, save_webui_environment_info
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger


EnvironmentInfoFactory = Callable[[], WebUiEnvironmentInfo]
"""环境信息报告构建函数。"""

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def output_environment_info(
    info_factory: EnvironmentInfoFactory,
    output: Path,
    overwrite: bool = False,
) -> Path:
    """构建并保存环境信息报告。

    Args:
        info_factory (EnvironmentInfoFactory): 环境信息报告构建函数。
        output (Path): 精确输出文件路径。
        overwrite (bool): 是否允许覆盖已有文件。

    Returns:
        Path: 已写入的文件路径。
    """
    logger.info("开始导出 WebUI 环境信息")
    output_path = save_webui_environment_info(info_factory(), output, overwrite=overwrite)
    logger.info("环境信息已保存: %s", output_path)
    return output_path
