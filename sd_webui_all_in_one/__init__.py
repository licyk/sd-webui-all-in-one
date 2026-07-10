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
    set_proxy,
    get_system_proxy_address,
    test_proxy_connectivity,
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
    os.environ["NO_PROXY"] = "localhost,127.0.0.1,::1"
    if SD_WEBUI_ALL_IN_ONE_PROXY:
        proxy_address = get_system_proxy_address()
        if proxy_address is not None:
            _logger.debug("检测到系统代理: %s", proxy_address)
            if test_proxy_connectivity(proxy_address):
                _logger.debug("代理连通性测试成功，配置系统代理: %s", proxy_address)
                set_proxy(proxy_address)
            else:
                _logger.debug("代理 %s 连通性测试失败，跳过代理配置", proxy_address)


def _apply_cache_path() -> None:
    if SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH:
        _logger.debug("设置缓存路径")
        os.environ["CACHE_HOME"] = os.getenv("CACHE_HOME", SD_WEBUI_ALL_IN_ONE_CACHE_PATH.as_posix())
        os.environ["HF_HOME"] = os.getenv("HF_HOME", (SD_WEBUI_ALL_IN_ONE_CACHE_PATH / "huggingface").as_posix())
        os.environ["MATPLOTLIBRC"] = os.getenv("MATPLOTLIBRC", SD_WEBUI_ALL_IN_ONE_CACHE_PATH.as_posix())
        os.environ["MODELSCOPE_CACHE"] = os.getenv("MODELSCOPE_CACHE", (SD_WEBUI_ALL_IN_ONE_CACHE_PATH / "modelscope" / "hub").as_posix())
        os.environ["MS_CACHE_HOME"] = os.getenv("MS_CACHE_HOME", (SD_WEBUI_ALL_IN_ONE_CACHE_PATH / "modelscope" / "hub").as_posix())
        os.environ["SYCL_CACHE_DIR"] = os.getenv("SYCL_CACHE_DIR", (SD_WEBUI_ALL_IN_ONE_CACHE_PATH / "libsycl_cache").as_posix())
        os.environ["TORCH_HOME"] = os.getenv("TORCH_HOME", (SD_WEBUI_ALL_IN_ONE_CACHE_PATH / "torch").as_posix())
        os.environ["U2NET_HOME"] = os.getenv("U2NET_HOME", (SD_WEBUI_ALL_IN_ONE_CACHE_PATH / "u2net").as_posix())
        os.environ["XDG_CACHE_HOME"] = os.getenv("XDG_CACHE_HOME", SD_WEBUI_ALL_IN_ONE_CACHE_PATH.as_posix())
        os.environ["PIP_CACHE_DIR"] = os.getenv("PIP_CACHE_DIR", (SD_WEBUI_ALL_IN_ONE_CACHE_PATH / "pip").as_posix())
        os.environ["PYTHONPYCACHEPREFIX"] = os.getenv("PYTHONPYCACHEPREFIX", (SD_WEBUI_ALL_IN_ONE_CACHE_PATH / "pycache").as_posix())
        os.environ["TORCHINDUCTOR_CACHE_DIR"] = os.getenv("TORCHINDUCTOR_CACHE_DIR", (SD_WEBUI_ALL_IN_ONE_CACHE_PATH / "torchinductor").as_posix())
        os.environ["TRITON_CACHE_DIR"] = os.getenv("TRITON_CACHE_DIR", (SD_WEBUI_ALL_IN_ONE_CACHE_PATH / "triton").as_posix())
        os.environ["UV_CACHE_DIR"] = os.getenv("UV_CACHE_DIR", (SD_WEBUI_ALL_IN_ONE_CACHE_PATH / "uv").as_posix())


def _apply_env_vars() -> None:
    if SD_WEBUI_ALL_IN_ONE_SET_CONFIG:
        _logger.debug("配置基础环境变量")
        for k, v in DEFAULT_ENV_VARS:
            os.environ[k] = v


def _apply_config_file() -> None:
    tmp_dir = Path(_temp_dir.name)
    pip_config_file = tmp_dir / "pip.ini"
    uv_config_file = tmp_dir / "uv.toml"
    git_config_file = tmp_dir / ".gitconfig"
    if SD_WEBUI_ALL_IN_ONE_DESKTOP_MODE:
        _logger.debug("在 %s 配置默认的 uv / Pip / Git 配置文件", tmp_dir)
        os.environ["PIP_CONFIG_FILE"] = pip_config_file.as_posix()
        os.environ["UV_CONFIG_FILE"] = uv_config_file.as_posix()
        os.environ["GIT_CONFIG_GLOBAL"] = git_config_file.as_posix()
        pip_config_file.write_text("", encoding="utf-8")
        uv_config_file.write_text("", encoding="utf-8")
        git_config_file.write_text(DEFAULT_GIT_CONFIG, encoding="utf-8")


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
