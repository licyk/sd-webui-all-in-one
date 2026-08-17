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
"""

import os
import atexit
from pathlib import Path
from tempfile import TemporaryDirectory

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_NAME,
    LOGGER_LEVEL,
    LOGGER_COLOR,
    SD_WEBUI_ALL_IN_ONE_PROXY,
    SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH,
    SD_WEBUI_ALL_IN_ONE_SET_CONFIG,
    SD_WEBUI_ALL_IN_ONE_CACHE_PATH,
    SD_WEBUI_ALL_IN_ONE_DESKTOP_MODE,
    DEFAULT_ENV_VARS,
    DEFAULT_GIT_CONFIG,
)
from sd_webui_all_in_one.proxy import (
    get_system_proxy_address,
    test_proxy_connectivity,
)
from sd_webui_all_in_one.env_manager import (
    generate_proxy_env_vars,
    generate_cache_path_env_vars,
    generate_config_file_env_vars,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

_logger = logger
_temp_dir = TemporaryDirectory()
atexit.register(_temp_dir.cleanup)


def _apply_proxy() -> None:
    os.environ.update(generate_proxy_env_vars())
    if SD_WEBUI_ALL_IN_ONE_PROXY:
        proxy_address = get_system_proxy_address()
        if proxy_address is not None:
            _logger.debug("检测到系统代理: %s", proxy_address)
            if test_proxy_connectivity(proxy_address):
                _logger.debug("代理连通性测试成功，配置系统代理: %s", proxy_address)
                os.environ.update(generate_proxy_env_vars(proxy_address))
            else:
                _logger.debug("代理 %s 连通性测试失败，跳过代理配置", proxy_address)


def _apply_cache_path() -> None:
    if SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH:
        _logger.debug("设置缓存路径")
        os.environ.update(generate_cache_path_env_vars(SD_WEBUI_ALL_IN_ONE_CACHE_PATH))


def _apply_env_vars() -> None:
    if SD_WEBUI_ALL_IN_ONE_SET_CONFIG:
        _logger.debug("配置基础环境变量")
        for k, v in DEFAULT_ENV_VARS:
            os.environ[k] = v


def _apply_config_file() -> None:
    tmp_dir = Path(_temp_dir.name)
    if SD_WEBUI_ALL_IN_ONE_DESKTOP_MODE:
        _logger.debug("在 %s 配置默认的 uv / Pip / Git 配置文件", tmp_dir)
        config_env = generate_config_file_env_vars(tmp_dir)
        os.environ.update(config_env)
        Path(config_env["PIP_CONFIG_FILE"]).write_text("", encoding="utf-8")
        Path(config_env["UV_CONFIG_FILE"]).write_text("", encoding="utf-8")
        Path(config_env["GIT_CONFIG_GLOBAL"]).write_text(DEFAULT_GIT_CONFIG, encoding="utf-8")


_apply_proxy()
_apply_cache_path()
_apply_env_vars()
_apply_config_file()

# pylint: disable=wrong-import-position
from sd_webui_all_in_one.version import VERSION
from sd_webui_all_in_one.notebook_manager import (
    BaseManager,
    SDWebUIManager,
    ComfyUIManager,
    FooocusManager,
    InvokeAIManager,
    SDTrainerManager,
    SDScriptsManager,
    SDTrainerScriptsManager,
    QwenTTSWebUIManager,
)

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
