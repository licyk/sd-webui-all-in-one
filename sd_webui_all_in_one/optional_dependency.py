"""可选 Python 依赖安装工具"""

from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.mirror_manager import get_auto_pypi_mirror_config
from sd_webui_all_in_one.pkg_manager import pip_install

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def install_optional_dependency(
    package_name: str,
    display_name: str | None = None,
) -> None:
    """安装可选 Python 依赖

    Args:
        package_name (str):
            要安装的 Python 包名
        display_name (str | None):
            日志和异常中显示的模块名

    Raises:
        RuntimeError:
            安装可选依赖失败时
    """
    if display_name is None:
        display_name = package_name

    try:
        custom_env = get_auto_pypi_mirror_config()
        pip_install(
            package_name,
            custom_env=custom_env,
        )
    except RuntimeError as e:
        logger.error("安装 %s 模块失败: %s", display_name, e)
        raise RuntimeError(f"安装 {display_name} 模块失败: {e}") from e
