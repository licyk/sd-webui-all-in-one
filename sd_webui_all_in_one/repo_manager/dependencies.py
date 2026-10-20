"""仓库管理可选依赖加载工具"""

import importlib

from sd_webui_all_in_one.optional_dependency import install_optional_dependency
from sd_webui_all_in_one.repo_manager.shared import logger


def _ensure_optional_dependency(
    module_name: str,
    package_name: str,
    display_name: str | None = None,
) -> None:
    """确保可选依赖可导入, 导入失败时先安装依赖后再重试"""
    display_name = display_name or module_name
    try:
        importlib.import_module(module_name)
        return
    except ImportError as import_error:
        logger.warning("%s 模块导入失败, 尝试自动安装依赖: %s", display_name, import_error)

    try:
        install_optional_dependency(package_name, display_name=display_name)
        importlib.invalidate_caches()
        importlib.import_module(module_name)
    except (RuntimeError, ImportError) as e:
        logger.error("导入 %s 模块失败: %s", display_name, e)
        raise RuntimeError(f"导入 {display_name} 模块失败: {e}") from e


def _ensure_huggingface_hub(
    module_name: str = "huggingface_hub",
) -> None:
    """确保 huggingface_hub 相关模块可导入, 缺失时自动安装 huggingface_hub"""
    _ensure_optional_dependency(module_name, "huggingface_hub", display_name=module_name)


def _ensure_modelscope(
    module_name: str = "modelscope",
) -> None:
    """确保 modelscope 相关模块可导入, 缺失时自动安装 modelscope"""
    _ensure_optional_dependency(module_name, "modelscope", display_name=module_name)
