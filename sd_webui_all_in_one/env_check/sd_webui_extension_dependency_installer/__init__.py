"""Stable Diffusion WebUI 扩展依赖安装工具"""

from sd_webui_all_in_one.env_check.shared import logger
from sd_webui_all_in_one.env_check.sd_webui_extension_dependency_installer.runner import (
    run_extension_installer,
)
from sd_webui_all_in_one.env_check.sd_webui_extension_dependency_installer.installer import (
    install_extension_requirements,
)

__all__ = [
    "logger",
    "run_extension_installer",
    "install_extension_requirements",
]
