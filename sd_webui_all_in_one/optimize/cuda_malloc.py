"""CUDA Malloc 配置工具"""

import os
import ctypes
import subprocess
import importlib.util

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def get_gpu_names() -> set[str]:
    """获取 GPU 的列表

    Returns:
        set[str]: GPU 名称列表
    """
    if os.name == "nt":

        class DisplayDevicea(ctypes.Structure):
            """显示设备信息结构类型"""

            _fields_ = [
                ("cb", ctypes.c_ulong),
                ("DeviceName", ctypes.c_char * 32),
                ("DeviceString", ctypes.c_char * 128),
                ("StateFlags", ctypes.c_ulong),
                ("DeviceID", ctypes.c_char * 128),
                ("DeviceKey", ctypes.c_char * 128),
            ]
            cb = None

        # Load user32.dll
        user32 = ctypes.windll.user32

        # Call EnumDisplayDevicesA
        def enum_display_devices():
            device_info = DisplayDevicea()
            device_info.cb = ctypes.sizeof(device_info)
            device_index = 0
            gpu_names = set()

            while user32.EnumDisplayDevicesA(None, device_index, ctypes.byref(device_info), 0):
                device_index += 1
                gpu_names.add(device_info.DeviceString.decode("utf-8"))
            return gpu_names

        return enum_display_devices()
    else:
        gpu_names = set()
        out = subprocess.check_output(["nvidia-smi", "-L"])
        for line in out.split(b"\n"):
            if len(line) > 0:
                gpu_names.add(line.decode("utf-8").split(" (UUID")[0])
        return gpu_names


GPU_BLACKLIST = {
    "GeForce GTX TITAN X",
    "GeForce GTX 980",
    "GeForce GTX 970",
    "GeForce GTX 960",
    "GeForce GTX 950",
    "GeForce 945M",
    "GeForce 940M",
    "GeForce 930M",
    "GeForce 920M",
    "GeForce 910M",
    "GeForce GTX 750",
    "GeForce GTX 745",
    "Quadro K620",
    "Quadro K1200",
    "Quadro K2200",
    "Quadro M500",
    "Quadro M520",
    "Quadro M600",
    "Quadro M620",
    "Quadro M1000",
    "Quadro M1200",
    "Quadro M2000",
    "Quadro M2200",
    "Quadro M3000",
    "Quadro M4000",
    "Quadro M5000",
    "Quadro M5500",
    "Quadro M6000",
    "GeForce MX110",
    "GeForce MX130",
    "GeForce 830M",
    "GeForce 840M",
    "GeForce GTX 850M",
    "GeForce GTX 860M",
    "GeForce GTX 1650",
    "GeForce GTX 1630",
    "Tesla M4",
    "Tesla M6",
    "Tesla M10",
    "Tesla M40",
    "Tesla M60",
}

NVIDIA_GPU_KEYWORD = ["NVIDIA", "GeForce", "Tesla", "Quadro"]


def cuda_malloc_supported() -> bool:
    """检查是否有支持 CUDA Malloc 的 GPU

    Returns:
        bool: 有支持 CUDA Malloc 的 GPU 时返回 True
    """
    try:
        names = get_gpu_names()
    except Exception as _:
        names = set()
    for x in names:
        if any(keyword in x for keyword in NVIDIA_GPU_KEYWORD):
            for b in GPU_BLACKLIST:
                if b in x:
                    return False
    return True


def is_nvidia_device():
    """检查 GPU 是否为 Nvidia 的 GPU

    Returns:
        bool: 当 GPU 为 Nvidia 的 GPU 时返回 True
    """
    try:
        names = get_gpu_names()
    except Exception as _:
        names = set()
    for x in names:
        if any(keyword in x for keyword in NVIDIA_GPU_KEYWORD):
            return True
    return False


def get_pytorch_cuda_alloc_conf(is_cuda: bool | None = True) -> str | None:
    """获取用于配置 PYTORCH_CUDA_ALLOC_CONF / PYTORCH_ALLOC_CONF 环境变量的配置

    Args:
        is_cuda (bool | None): 是否为 CUDA 设备

    Returns:
        (str | None): CUDA Malloc 配置
    """
    if is_nvidia_device():
        if cuda_malloc_supported():
            if is_cuda:
                return "cuda_malloc"
            else:
                return "pytorch_malloc"
        else:
            return "pytorch_malloc"
    else:
        return None


def get_cuda_malloc_var() -> str | None:
    """获取配置 CUDA Malloc 内存优化所需的环境变量, 可将参数设置到 PYTORCH_CUDA_ALLOC_CONF / PYTORCH_ALLOC_CONF 环境变量

    Returns:
        (str | None):
            当可用时返回配置 CUDA Malloc 内存优化的参数, 否则返回 None
    """

    try:
        version = ""
        torch_spec = importlib.util.find_spec("torch")
        for folder in torch_spec.submodule_search_locations:
            ver_file = os.path.join(folder, "version.py")
            if os.path.isfile(ver_file):
                spec = importlib.util.spec_from_file_location("torch_version_import", ver_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                version = module.__version__
        if int(version[0]) >= 2:  # enable by default for torch version 2.0 and up
            if "+cu" in version:  # only on cuda torch
                malloc_type = get_pytorch_cuda_alloc_conf()
            else:
                malloc_type = get_pytorch_cuda_alloc_conf(False)
        else:
            malloc_type = None
    except Exception:
        malloc_type = None

    if malloc_type == "cuda_malloc":
        logger.info("可用的 CUDA 内存分配器: CUDA 内置异步分配器")
        return "backend:cudaMallocAsync"
    elif malloc_type == "pytorch_malloc":
        logger.info("可用的 CUDA 内存分配器: PyTorch 原生分配器")
        return "garbage_collection_threshold:0.9,max_split_size_mb:512"
    else:
        logger.warning("无可用的 CUDA 内存分配器")
        return None


def set_cuda_malloc() -> None:
    """配置 CUDA Malloc 内存优化, 通过 PYTORCH_CUDA_ALLOC_CONF / PYTORCH_ALLOC_CONF 环境变量进行配置"""
    malloc_var = get_cuda_malloc_var()
    if malloc_var is None:
        return

    os.environ["PYTORCH_ALLOC_CONF"] = malloc_var
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = malloc_var
