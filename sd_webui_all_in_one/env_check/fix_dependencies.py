"""依赖检查与修复工具"""

from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR
from sd_webui_all_in_one.env_manager import install_requirements
from sd_webui_all_in_one.package_analyzer.pkg_check import validate_requirements


logger = get_logger(
    name="Deps Check",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def py_dependency_checker(
    requirement_path: Path | str,
    name: str | None = None,
    use_uv: bool | None = True,
) -> None:
    """检测依赖完整性并安装缺失依赖

    Args:
        requirement_path (Path | str): 依赖文件路径
        name (str | None): 显示的名称
        use_uv (bool | None): 是否使用 uv 安装依赖
    """
    requirement_path = Path(requirement_path) if not isinstance(requirement_path, Path) and requirement_path is not None else requirement_path
    if not requirement_path.exists():
        logger.error("未找到 %s 文件, 无法检查依赖完整性", requirement_path)
        return
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
            )
            logger.info("安装 %s 依赖完成", name)
        except Exception as e:
            logger.error("安装 %s 依赖出现错误: %s", name, e)
            return
    logger.info("%s 依赖完整性检查完成", name)
