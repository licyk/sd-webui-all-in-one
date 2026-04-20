"""镜像选择处理"""

import sys

from sd_webui_all_in_one.package_analyzer import CommonVersionComparison
from sd_webui_all_in_one.pytorch_manager.gpu_detector import (
    get_cuda_comp_cap,
    get_cuda_version,
)
from sd_webui_all_in_one.pytorch_manager.mirror_data import (
    PYTORCH_MIRROR_DICT,
    PYTORCH_MIRROR_NJU_DICT,
    PYTORCH_ROCM_MIRROR_DICT,
)
from sd_webui_all_in_one.pytorch_manager.types import (
    PyTorchMirrorInfo,
    PyTorchDeviceTypeCategory,
    PyTorchDeviceType,
)


def get_pytorch_mirror_type_cuda(
    torch_ver: str,
) -> str:
    """获取 CUDA 类型的 PyTorch 镜像源类型

    Args:
        torch_ver (str): PyTorch 版本
    Returns:
        str: CUDA 类型的 PyTorch 镜像源类型
    """
    # cu118: 2.0.0 ~ 2.4.0
    # cu121: 2.1.1 ~ 2.4.0
    # cu124: 2.4.0 ~ 2.6.0
    # cu126: 2.6.0 ~ 2.7.1
    # cu128: 2.7.0 ~ 2.7.1
    # cu129: 2.8.0
    # cu130: 2.9.0 ~ 2.10.0
    cuda_comp_cap = get_cuda_comp_cap()
    cuda_support_ver = get_cuda_version()

    torch_version = CommonVersionComparison(torch_ver)
    cuda_support_version = CommonVersionComparison(str(int(cuda_support_ver * 10)))

    if torch_version < CommonVersionComparison("2.0.0"):
        # torch < 2.0.0: default cu11x
        return "all"
    if CommonVersionComparison("2.0.0") <= torch_version < CommonVersionComparison("2.3.1"):
        # 2.0.0 <= torch < 2.3.1: default cu118
        return "cu118"
    if CommonVersionComparison("2.3.0") <= torch_version < CommonVersionComparison("2.4.1"):
        # 2.3.0 <= torch < 2.4.1: default cu121
        if cuda_support_version < CommonVersionComparison("121"):
            if cuda_support_version >= CommonVersionComparison("118"):
                return "cu118"
        return "cu121"
    if CommonVersionComparison("2.4.0") <= torch_version < CommonVersionComparison("2.6.0"):
        # 2.4.0 <= torch < 2.6.0: default cu124
        if cuda_support_version < CommonVersionComparison("124"):
            if cuda_support_version >= CommonVersionComparison("121"):
                return "cu121"
            if cuda_support_version >= CommonVersionComparison("118"):
                return "cu118"
        return "cu124"
    if CommonVersionComparison("2.6.0") <= torch_version < CommonVersionComparison("2.7.0"):
        # 2.6.0 <= torch < 2.7.0: default cu126
        if cuda_support_version < CommonVersionComparison("126"):
            if cuda_support_version >= CommonVersionComparison("124"):
                return "cu124"
        if CommonVersionComparison(cuda_comp_cap) > CommonVersionComparison("10.0"):
            if cuda_support_version >= CommonVersionComparison("128"):
                return "cu128"
        return "cu126"
    if CommonVersionComparison("2.7.0") <= torch_version < CommonVersionComparison("2.8.0"):
        # 2.7.0 <= torch < 2.8.0: default cu128
        if cuda_support_version < CommonVersionComparison("128"):
            if cuda_support_version > CommonVersionComparison("126"):
                return "cu126"
        return "cu128"
    if CommonVersionComparison("2.8.0") <= torch_version < CommonVersionComparison("2.9.0"):
        # 2.8.0 <= torch < 2.9.0: default cu129
        if cuda_support_version < CommonVersionComparison("129"):
            if cuda_support_version >= CommonVersionComparison("128"):
                return "cu128"
            if cuda_support_version >= CommonVersionComparison("126"):
                return "cu126"
        return "cu129"
    if CommonVersionComparison("2.9.0") <= torch_version < CommonVersionComparison("2.10.0"):
        # 2.9.0 <= torch < 2.10.0: default cu130
        if cuda_support_version < CommonVersionComparison("130"):
            if cuda_support_version >= CommonVersionComparison("128"):
                return "cu128"
            if cuda_support_version >= CommonVersionComparison("126"):
                return "cu126"
        return "cu130"
    if CommonVersionComparison("2.10.0") <= torch_version:
        # torch >= 2.10.0: default cu130
        if cuda_support_version < CommonVersionComparison("130"):
            if cuda_support_version >= CommonVersionComparison("128"):
                return "cu128"
            if cuda_support_version >= CommonVersionComparison("126"):
                return "cu126"
        return "cu130"

    return "cu130"


def get_pytorch_mirror_type_rocm(
    torch_ver: str,
) -> str:
    """获取 ROCm 类型的 PyTorch 镜像源类型

    Args:
        torch_ver (str): PyTorch 版本
    Returns:
        str: ROCm 类型的 PyTorch 镜像源类型
    """
    torch_version = CommonVersionComparison(torch_ver)
    if torch_version < CommonVersionComparison("2.4.0"):
        # torch < 2.4.0
        return "all"
    if sys.platform == "win32":
        # 使用 Windows 版本的 PyTorch
        return "rocm_win"
    if CommonVersionComparison("2.4.0") <= torch_version < CommonVersionComparison("2.5.0"):
        # 2.4.0 <= torch < 2.5.0
        return "rocm6.1"
    if CommonVersionComparison("2.5.0") <= torch_version < CommonVersionComparison("2.6.0"):
        # 2.5.0 <= torch < 2.6.0
        return "rocm6.2"
    if CommonVersionComparison("2.6.0") <= torch_version < CommonVersionComparison("2.7.0"):
        # 2.6.0 <= torch < 2.7.0
        return "rocm6.2.4"
    if CommonVersionComparison("2.7.0") <= torch_version < CommonVersionComparison("2.8.0"):
        # 2.7.0 <= torch < 2.8.0
        return "rocm6.3"
    if CommonVersionComparison("2.8.0") <= torch_version < CommonVersionComparison("2.10.0"):
        # 2.8.0 <= torch < 2.10.0
        return "rocm6.4"
    if CommonVersionComparison("2.10.0") <= torch_version:
        # 2.10.0 <= torch
        return "rocm7.1"

    return "rocm7.1"


def get_pytorch_mirror_type_ipex(
    torch_ver: str,
) -> str:
    """获取 IPEX 类型的 PyTorch 镜像源类型

    Args:
        torch_ver (str): PyTorch 版本
    Returns:
        str: IPEX 类型的 PyTorch 镜像源类型
    """
    torch_version = CommonVersionComparison(torch_ver)
    if torch_version < CommonVersionComparison("2.0.0"):
        # torch < 2.0.0
        return "all"
    if torch_version == CommonVersionComparison("2.0.0"):
        # torch == 2.0.0
        return "ipex_legacy_arc"
    if CommonVersionComparison("2.0.0") < torch_version < CommonVersionComparison("2.1.0"):
        # 2.0.0 < torch < 2.1.0
        return "all"
    if torch_version == CommonVersionComparison("2.1.0"):
        # torch == 2.1.0
        return "ipex_legacy_arc"
    if torch_version >= CommonVersionComparison("2.6.0"):
        # torch >= 2.6.0
        return "xpu"

    return "xpu"


def get_pytorch_mirror_type_cpu(
    torch_ver: str,
) -> str:
    """获取 CPU 类型的 PyTorch 镜像源类型

    Args:
        torch_ver (str): PyTorch 版本
    Returns:
        str: CPU 类型的 PyTorch 镜像源类型
    """
    _ = torch_ver
    return "cpu"


def get_pytorch_mirror_type(
    torch_ver: str,
    device_type: PyTorchDeviceTypeCategory,
) -> str:
    """获取 PyTorch 镜像源类型

    Args:
        torch_ver (str): PyTorch 版本号
        device_type (PyTorchDeviceTypeCategory): 显卡类型
    Returns:
        str: PyTorch 镜像源类型
    """
    if device_type == "cuda":
        return get_pytorch_mirror_type_cuda(torch_ver)

    if device_type == "rocm":
        return get_pytorch_mirror_type_rocm(torch_ver)

    if device_type == "xpu":
        return get_pytorch_mirror_type_ipex(torch_ver)

    if device_type == "mps":
        return "all"

    if device_type == "cpu":
        return get_pytorch_mirror_type_cpu(torch_ver)

    return "all"


def get_env_pytorch_type() -> PyTorchDeviceTypeCategory:
    """获取当前环境中 PyTorch 版本号对应的类型

    Returns:
        PyTorchDeviceTypeCategory: PyTorch 类型 (cuda, rocm, xpu, mps, cpu)
    """
    torch_ipex_legacy_ver_list = [
        "2.0.0a0+gite9ebda2",
        "2.1.0a0+git7bcf7da",
        "2.1.0a0+cxx11.abi",
        "2.0.1a0",
        "2.1.0.post0",
    ]
    try:
        import torch

        torch_ver = torch.__version__
    except Exception as _:
        return "cuda"

    torch_type = torch_ver.split("+")[-1]

    if torch_ver in torch_ipex_legacy_ver_list:
        return "xpu"

    if "cu" in torch_type:
        return "cuda"

    if "rocm" in torch_type:
        return "rocm"

    if "xpu" in torch_type:
        return "xpu"

    if "cpu" in torch_type:
        return "cpu"

    if sys.platform == "darwin":
        return "mps"

    return "cuda"


def get_pytorch_mirror(
    dtype: PyTorchDeviceType,
    use_cn_mirror: bool | None = False,
) -> PyTorchMirrorInfo:
    """根据 PyTorch 类型获取对应的 PyTorch 镜像源

    Args:
        dtype (PyTorchDeviceType):
            PyTorch 支持的设备类型
        use_cn_mirror (bool | None):
            是否使用国内镜像源

    Returns:
        PyTorchMirrorInfo:
            PyTorch 镜像源信息

    Raises:
        ValueError:
            未找到对应的 PyTorch 镜像源时
    """
    url = PYTORCH_MIRROR_NJU_DICT.get(dtype) if use_cn_mirror else PYTORCH_MIRROR_DICT.get(dtype)

    if url is None:
        url = PYTORCH_ROCM_MIRROR_DICT.get(dtype)

    if url is None:
        raise ValueError(f"未找到 '{dtype}' 对应的 PyTorch 镜像源")

    return url
