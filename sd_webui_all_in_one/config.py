"""配置管理"""

import os
import logging
from pathlib import Path

LOGGER_NAME = os.getenv("SD_WEBUI_ALL_IN_ONE_LOGGER_NAME", "SD WebUI All In One")
"""日志器名字"""

LOGGER_LEVEL = int(os.getenv("SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL", str(logging.INFO)))
"""日志等级"""

LOGGER_COLOR = os.getenv("SD_WEBUI_ALL_IN_ONE_LOGGER_COLOR") not in ["0", "False", "false", "None", "none", "null"]
"""日志颜色"""

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
]
"""默认配置的环境变量"""

ROOT_PATH = Path(__file__).parent
"""SD WebUI All In One 根目录"""

SD_WEBUI_ALL_IN_ONE_PATCHER_PATH = ROOT_PATH / "sdaio_patcher"
"""SD WebUI All In One 补丁目录"""

SD_WEBUI_ALL_IN_ONE_PATCHER = os.getenv("SD_WEBUI_ALL_IN_ONE_PATCHER") not in ["0", "False", "false", "None", "none", "null"]
"""是否 SD WebUI All In One 启用补丁"""
