"""依赖检查与修复工具"""

from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.pkg_manager import install_requirements, pip_install
from sd_webui_all_in_one.package_analyzer import (
    get_missing_package_metadata_dependencies,
    validate_requirements,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def py_dependency_checker(
    requirement_path: Path,
    name: str | None = None,
    use_uv: bool | None = True,
    custom_env: dict[str, str] | None = None,
) -> None:
    """检测依赖完整性并安装缺失依赖

    Args:
        requirement_path (Path):
            依赖文件路径
        name (str | None):
            显示的名称
        use_uv (bool | None):
            是否使用 uv 安装依赖
        custom_env (dict[str, str] | None):
            环境变量字典

    Raises:
        FileNotFoundError:
            未找到依赖记录文件时
        RuntimeError:
            安装依赖发生错误时
    """
    if not requirement_path.exists():
        logger.error("未找到 %s 文件, 无法检查依赖完整性", requirement_path)
        raise FileNotFoundError(f"未在 '{requirement_path}' 找到依赖文件, 无法检查依赖完整性")

    if name is None:
        name = requirement_path.parent.name

    logger.info("检查 %s 依赖完整性中", name)
    if not validate_requirements(requirement_path):
        logger.info("安装 %s 依赖中", name)
        try:
            install_requirements(
                path=requirement_path,
                use_uv=use_uv,
                cwd=requirement_path.parent,
                custom_env=custom_env,
            )
            logger.info("安装 %s 依赖完成", name)
        except RuntimeError as e:
            logger.error("安装 %s 依赖出现错误: %s", name, e)
            raise RuntimeError(f"从 '{requirement_path}' 安装 '{name}' 缺失依赖时出现错误: {e}") from e

    logger.info("%s 依赖完整性检查完成", name)


def py_package_metadata_dependency_checker(
    package_name: str,
    name: str | None = None,
    use_uv: bool | None = True,
    custom_env: dict[str, str] | None = None,
) -> None:
    """检测 wheel metadata 依赖完整性并安装缺失依赖

    Args:
        package_name (str):
            要检查的软件包名, 支持 ``package`` 或 ``package[extra1,extra2]`` 格式
        name (str | None):
            显示的名称
        use_uv (bool | None):
            是否使用 uv 安装依赖
        custom_env (dict[str, str] | None):
            环境变量字典

    Raises:
        RuntimeError:
            安装依赖发生错误时
        ValueError:
            请求的 optional extra 不存在时
    """
    if name is None:
        name = package_name

    logger.info("检查 %s wheel metadata 依赖完整性中", name)
    missing_packages = get_missing_package_metadata_dependencies(package_name)
    if missing_packages:
        logger.info("安装 %s 缺失依赖中: %s", name, " ".join(missing_packages))
        try:
            pip_install(
                *missing_packages,
                use_uv=use_uv,
                custom_env=custom_env,
            )
            logger.info("安装 %s 缺失依赖完成", name)
        except RuntimeError as e:
            logger.error("安装 %s 缺失依赖出现错误: %s", name, e)
            raise RuntimeError(f"从 '{package_name}' 的 wheel metadata 安装 '{name}' 缺失依赖时出现错误: {e}") from e

    logger.info("%s wheel metadata 依赖完整性检查完成", name)
