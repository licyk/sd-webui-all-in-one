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


def _get_display_name(
    package_name: str,
    display_name: str | None = None,
) -> str:
    """获取用于日志和异常的依赖名称"""
    return display_name or package_name


def _install_optional_dependency_package(
    package_name: str,
) -> None:
    """使用自动 PyPI 镜像安装可选 Python 依赖"""
    custom_env = get_auto_pypi_mirror_config()
    pip_install(
        package_name,
        custom_env=custom_env,
    )


def install_optional_dependency(
    package_name: str,
    display_name: str | None = None,
) -> None:
    """安装可选 Python 依赖, 安装失败时抛出异常

    Args:
        package_name (str):
            要安装的 Python 包名
        display_name (str | None):
            日志和异常中显示的模块名

    Raises:
        RuntimeError:
            安装可选依赖失败时
    """
    display_name = _get_display_name(package_name, display_name)

    try:
        _install_optional_dependency_package(package_name)
    except RuntimeError as e:
        logger.error("安装 %s 模块失败: %s", display_name, e)
        raise RuntimeError(f"安装 {display_name} 模块失败: {e}") from e


def try_install_optional_dependency(
    package_name: str,
    display_name: str | None = None,
) -> bool:
    """尝试安装可选 Python 依赖, 安装失败时返回 False

    Args:
        package_name (str):
            要安装的 Python 包名
        display_name (str | None):
            日志中显示的模块名

    Returns:
        bool:
            安装是否成功
    """
    display_name = _get_display_name(package_name, display_name)

    try:
        _install_optional_dependency_package(package_name)
        return True
    except RuntimeError as e:
        logger.warning("安装 %s 模块失败: %s", display_name, e)
        return False
