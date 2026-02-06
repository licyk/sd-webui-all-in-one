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
from sd_webui_all_in_one.config import (
    LOGGER_NAME,
    LOGGER_LEVEL,
    LOGGER_COLOR,
    SD_WEBUI_ALL_IN_ONE_PATCHER,
    SD_WEBUI_ALL_IN_ONE_PATCHER_PATH,
    SD_WEBUI_ALL_IN_ONE_PROXY,
    SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH,
    SD_WEBUI_ALL_IN_ONE_SET_CONFIG,
    SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH,
    DEFAULT_ENV_VARS,
)
from sd_webui_all_in_one.proxy import set_proxy, get_system_proxy_address

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


os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"

if SD_WEBUI_ALL_IN_ONE_PROXY:
    proxy_address = get_system_proxy_address()
    if proxy_address is not None:
        logger.debug("配置系统代理: %s", proxy_address)
        set_proxy(proxy_address)

if SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH:
    logger.debug("设置缓存路径")
    os.environ["CACHE_HOME"] = os.getenv("CACHE_HOME", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "cache").as_posix())
    os.environ["HF_HOME"] = os.getenv("HF_HOME", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "cache" / "huggingface").as_posix())
    os.environ["MATPLOTLIBRC"] = os.getenv("MATPLOTLIBRC", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "cache").as_posix())
    os.environ["MODELSCOPE_CACHE"] = os.getenv("MODELSCOPE_CACHE", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "cache" / "modelscope" / "hub").as_posix())
    os.environ["MS_CACHE_HOME"] = os.getenv("MS_CACHE_HOME", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "cache" / "modelscope" / "hub").as_posix())
    os.environ["SYCL_CACHE_DIR"] = os.getenv("SYCL_CACHE_DIR", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "cache" / "libsycl_cache").as_posix())
    os.environ["TORCH_HOME"] = os.getenv("TORCH_HOME", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "cache" / "torch").as_posix())
    os.environ["U2NET_HOME"] = os.getenv("U2NET_HOME", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "cache" / "u2net").as_posix())
    os.environ["XDG_CACHE_HOME"] = os.getenv("XDG_CACHE_HOME", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "cache").as_posix())
    os.environ["PIP_CACHE_DIR"] = os.getenv("PIP_CACHE_DIR", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "cache" / "pip").as_posix())
    os.environ["PYTHONPYCACHEPREFIX"] = os.getenv("PYTHONPYCACHEPREFIX", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "cache" / "pycache").as_posix())
    os.environ["TORCHINDUCTOR_CACHE_DIR"] = os.getenv("TORCHINDUCTOR_CACHE_DIR", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "cache" / "torchinductor").as_posix())
    os.environ["TRITON_CACHE_DIR"] = os.getenv("TRITON_CACHE_DIR", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "cache" / "triton").as_posix())
    os.environ["UV_CACHE_DIR"] = os.getenv("UV_CACHE_DIR", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "cache" / "uv").as_posix())

if SD_WEBUI_ALL_IN_ONE_SET_CONFIG:
    logger.debug("配置基础环境变量")
    for k, v in DEFAULT_ENV_VARS:
        os.environ[k] = v

# pylint: disable=wrong-import-position
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
