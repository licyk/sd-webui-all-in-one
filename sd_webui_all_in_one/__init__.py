"""SD WebUI All In One
与 SD 有关的环境管理模块, 可用于 Jupyter Notebook
支持管理的环境:
- SD WebUI / SD WebUI Forge / SD WebUI reForge / SD WebUI Forge Classic / SD WebUI AMDGPU / SD.Next
- ComfyUI
- InvokeAI
- Fooocus
- SD Script
- SD Trainer
- Kohya GUI

如果需要显示所有等级的日志, 可设置环境变量`SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL=10`

禁用彩色日志可设置环境变量`SD_WEBUI_ALL_IN_ONE_LOGGER_COLOR=0`

设置日志器的名称可通过环境变量`SD_WEBUI_ALL_IN_ONE_LOGGER_NAME=<日志器名称>`进行设置

如果需要禁用补丁可设置环境变量`SD_WEBUI_ALL_IN_ONE_PATCHER=0`
"""

import os

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_NAME, LOGGER_LEVEL, LOGGER_COLOR, SD_WEBUI_ALL_IN_ONE_PATCHER, SD_WEBUI_ALL_IN_ONE_PATCHER_PATH
from sd_webui_all_in_one.version import VERSION
from sd_webui_all_in_one.notebook_manager.base_manager import BaseManager
from sd_webui_all_in_one.notebook_manager.sd_webui_manager import SDWebUIManager
from sd_webui_all_in_one.notebook_manager.comfyui_manager import ComfyUIManager
from sd_webui_all_in_one.notebook_manager.fooocus_manager import FooocusManager
from sd_webui_all_in_one.notebook_manager.invokeai_manager import InvokeAIManager
from sd_webui_all_in_one.notebook_manager.sd_trainer_manager import SDTrainerManager
from sd_webui_all_in_one.notebook_manager.sd_scripts_manager import SDScriptsManager
from sd_webui_all_in_one.notebook_manager.sd_trainer_scripts_manager import SDTrainerScriptsManager
from sd_webui_all_in_one.notebook_manager.qwen_tts_webui_manager import QwenTTSWebUIManager

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

if SD_WEBUI_ALL_IN_ONE_PATCHER:
    logger.debug("配置 SD WebUI All In One 补丁模块")
    if "PYTHONPATH" in os.environ and os.environ["PYTHONPATH"]:
        os.environ["PYTHONPATH"] = SD_WEBUI_ALL_IN_ONE_PATCHER_PATH.as_posix() + os.pathsep + os.environ["PYTHONPATH"]
    else:
        os.environ["PYTHONPATH"] = SD_WEBUI_ALL_IN_ONE_PATCHER_PATH.as_posix()
    logger.debug("PYTHONPATH: %s", os.getenv("PYTHONPATH"))


__all__ = [
    "BaseManager",
    "SDWebUIManager",
    "ComfyUIManager",
    "FooocusManager",
    "InvokeAIManager",
    "SDTrainerManager",
    "SDScriptsManager",
    "SDTrainerScriptsManager",
    "QwenTTSWebUIManager",
    "VERSION",
    "logger",
]
