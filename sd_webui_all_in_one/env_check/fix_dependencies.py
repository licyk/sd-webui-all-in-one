"""依赖检查与修复工具"""

from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one.package_analyzer.pkg_check import validate_requirements


logger = get_logger(
    name="Deps Check",
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
