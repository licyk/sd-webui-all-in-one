"""配置管理"""

import os
import logging

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

PYTORCH_MIRROR_DICT = {
    "other": "https://download.pytorch.org/whl",
    "cpu": "https://download.pytorch.org/whl/cpu",
    "xpu": "https://download.pytorch.org/whl/xpu",
    "rocm61": "https://download.pytorch.org/whl/rocm6.1",
    "rocm62": "https://download.pytorch.org/whl/rocm6.2",
    "rocm624": "https://download.pytorch.org/whl/rocm6.2.4",
    "rocm63": "https://download.pytorch.org/whl/rocm6.3",
    "rocm64": "https://download.pytorch.org/whl/rocm6.4",
    "cu118": "https://download.pytorch.org/whl/cu118",
    "cu121": "https://download.pytorch.org/whl/cu121",
    "cu124": "https://download.pytorch.org/whl/cu124",
    "cu126": "https://download.pytorch.org/whl/cu126",
    "cu128": "https://download.pytorch.org/whl/cu128",
    "cu129": "https://download.pytorch.org/whl/cu129",
    "cu130": "https://download.pytorch.org/whl/cu130",
}
"""PyTorch 镜像源字典"""
