"""SD WebUI All In One"""

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_NAME, LOGGER_LEVEL, LOGGER_COLOR
from sd_webui_all_in_one.version import VERSION
from sd_webui_all_in_one.manager.base import BaseManager
from sd_webui_all_in_one.manager.sd_webui import SDWebUIManager
from sd_webui_all_in_one.manager.comfyui import ComfyUIManager
from sd_webui_all_in_one.manager.fooocus import FooocusManager
from sd_webui_all_in_one.manager.invokeai import InvokeAIManager
from sd_webui_all_in_one.manager.sd_trainer import SDTrainerManager
from sd_webui_all_in_one.manager.sd_scripts import SDScriptsManager

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

__all__ = [
    "BaseManager",
    "SDWebUIManager",
    "ComfyUIManager",
    "FooocusManager",
    "InvokeAIManager",
    "SDTrainerManager",
    "SDScriptsManager",
    "VERSION",
    "logger",
]
