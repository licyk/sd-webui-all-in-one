"""配置管理"""

import os
import sys
import logging
from pathlib import Path

LOGGER_NAME = None if os.getenv("SD_WEBUI_ALL_IN_ONE_LOGGER_NAME") in ["none", "None", "NONE"] else os.getenv("SD_WEBUI_ALL_IN_ONE_LOGGER_NAME", "SD WebUI All In One")
"""日志器名字"""

LOGGER_LEVEL = int(os.getenv("SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL", str(logging.INFO)))
"""日志等级"""

LOGGER_COLOR = os.getenv("SD_WEBUI_ALL_IN_ONE_LOGGER_COLOR") not in ["0", "False", "false", "None", "none", "null"]
"""日志颜色"""

RETRY_TIMES = int(os.getenv("SD_WEBUI_ALL_IN_ONE_RETRY_TIMES", str(3)))
"""重试次数"""

DEFAULT_ENV_VARS = [
    ["TF_CPP_MIN_LOG_LEVEL", "3"],
    ["BITSANDBYTES_NOWELCOME", "1"],
    ["GRADIO_ANALYTICS_ENABLED", "False"],
    ["ClDeviceGlobalMemSizeAvailablePercent", "100"],
    ["CUDA_MODULE_LOADING", "LAZY"],
    ["TORCH_CUDNN_V8_API_ENABLED", "1"],
    ["SAFETENSORS_FAST_GPU", "1"],
    ["SYCL_CACHE_PERSISTENT", "1"],
    ["PYTHONUTF8", "1"],
    ["PYTHONIOENCODING", "utf-8"],
    ["PYTHONUNBUFFERED", "1"],
    ["PYTHONFAULTHANDLER", "1"],
    [
        "PYTHONWARNINGS",
        "ignore:::torchvision.transforms.functional_tensor,ignore::UserWarning,ignore::FutureWarning,ignore::DeprecationWarning",
    ],
    ["UV_HTTP_TIMEOUT", "30"],
    ["UV_CONCURRENT_DOWNLOADS", "50"],
    ["UV_INDEX_STRATEGY", "unsafe-best-match"],
    ["PIP_DISABLE_PIP_VERSION_CHECK", "1"],
    ["PIP_NO_WARN_SCRIPT_LOCATION", "0"],
    ["PIP_TIMEOUT", "30"],
    ["PIP_RETRIES", "5"],
    ["PIP_PREFER_BINARY", "1"],
    ["PIP_YES", "1"],
    ["UV_PYTHON", Path(sys.executable).as_posix()],
    ["UV_LINK_MODE", "copy"],
]
"""默认配置的环境变量"""

ROOT_PATH = Path(__file__).parent
"""SD WebUI All In One 根目录"""

SD_WEBUI_ALL_IN_ONE_PATCHER_PATH = ROOT_PATH / "sdaio_patcher"
"""SD WebUI All In One 补丁目录"""

SD_WEBUI_ALL_IN_ONE_PATCHER = os.getenv("SD_WEBUI_ALL_IN_ONE_PATCHER") in ["1", "True", "true"]
"""是否 SD WebUI All In One 启用补丁"""

UV_MINIMUM_VER = "0.9.28"
"""uv 最低版本要求版本号"""

PIP_MINIMUM_VER = "26.0"
"""Pip 最低版本要求版本号"""

ARIA2_MINIMUM_VER = "1.37.0"
"""Aria2 最低版本要求版本号"""

SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH = Path(os.getenv("SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH", os.getcwd()))
"""SD WebUI All In One 运行时的起始目录"""

SD_WEBUI_ROOT_PATH = Path(os.getenv("SD_WEBUI_ROOT", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "stable-diffusion-webui").as_posix()))
"""Stable Diffusion WebUI 根目录"""

COMFYUI_ROOT_PATH = Path(os.getenv("COMFYUI_ROOT", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "ComfyUI").as_posix()))
"""ComfyUI 根目录"""

FOOOCUS_ROOT_PATH = Path(os.getenv("FOOOCUS_ROOT", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "Fooocus").as_posix()))
"""Fooocus 根目录"""

INVOKEAI_ROOT_PATH = Path(os.getenv("INVOKEAI_ROOT", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "InvokeAI").as_posix()))
"""InvokeAI 根目录"""

SD_TRAINER_ROOT_PATH = Path(os.getenv("SD_TRAINER_ROOT", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "SD-Trainer").as_posix()))
"""SD Trainer 根目录"""

SD_SCRIPTS_ROOT_PATH = Path(os.getenv("SD_SCRIPTS_ROOT", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "SD-Scripts").as_posix()))
"""SD Scripts 根目录"""

QWEN_TTS_WEBUI_ROOT_PATH = Path(os.getenv("QWEN_TTS_WEBUI_ROOT", (SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "qwen-tts-webui").as_posix()))
"""Qwen TTS WebUI 根目录"""

SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR = os.getenv("SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR") in ["1", "True", "true"]
"""是否启用 SD WebUI All In One 自带的额外 PyPI 镜像源"""

SD_WEBUI_ALL_IN_ONE_PROXY = os.getenv("SD_WEBUI_ALL_IN_ONE_PROXY") in ["1", "True", "true"]
"""是否自动读取系统代理配置并应用代理"""

SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH = os.getenv("SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH") in ["1", "True", "true"]
"""是否设置缓存路径"""

SD_WEBUI_ALL_IN_ONE_SET_CONFIG = os.getenv("SD_WEBUI_ALL_IN_ONE_SET_CONFIG") in ["1", "True", "true"]
"""是否在启动时通过环境变量进行配置"""

SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY = os.getenv("SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY") in ["1", "True", "true"]
"""是否跳过安装 PyTorch 时设备的兼容性检查"""
