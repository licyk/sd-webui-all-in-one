"""软件包元数据依赖检查与修复"""

from sd_webui_all_in_one.pkg_manager import pip_install
from sd_webui_all_in_one.package_analyzer import (
    get_missing_package_metadata_dependencies,
)
from sd_webui_all_in_one.env_check.shared import logger


def py_package_metadata_dependency_checker(
    package_name: str,
    name: str | None = None,
    use_uv: bool = True,
    custom_env: dict[str, str] | None = None,
) -> None:
    """检测 wheel metadata 依赖完整性并安装缺失依赖

    Args:
        package_name (str):
            要检查的软件包名, 支持 ``package`` 或 ``package[extra1,extra2]`` 格式
        name (str | None):
            显示的名称
        use_uv (bool):
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
