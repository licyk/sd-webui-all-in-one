"""PyTorch 镜像管理工具"""

import re
import subprocess
from typing import Literal

from sd_webui_all_in_one.config import PYTORCH_MIRROR_DICT, PYTORCH_MIRROR_NJU_DICT
from sd_webui_all_in_one.package_analyzer.ver_cmp import CommonVersionComparison


def get_pytorch_mirror_dict(use_cn_mirror: bool | None = False) -> dict[str, str]:
    """获取 PyTorch 镜像源字典

    Args:
        use_cn_mirror (bool | None): 是否使用国内镜像 (NJU)
    Returns:
        (dict[str, str]): PyTorch 镜像源字典的副本, 键为设备类型 (如 "cu118", "rocm61" 等), 值为对应的 PyTorch wheel 下载地址
    """
    if use_cn_mirror:
        PYTORCH_MIRROR_NJU_DICT.copy()
    return PYTORCH_MIRROR_DICT.copy()


def get_cuda_comp_cap() -> float:
    """获取 CUDA 的计算能力

    当获取值失败时则返回 0.0

    Blackwell 消费级 GPU 应得到 12.0

    数据中心级 GPU 应得到 10.0

    参考:
    ```
    https://developer.nvidia.com/cuda-gpus
    https://en.wikipedia.org/wiki/CUDA
    ```

    Returns:
        float: CUDA 计算能力值
    """
    try:
        return max(
            map(
                float,
                subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=compute_cap",
                        "--format=noheader,csv",
                    ],
                    text=True,
                ).splitlines(),
            )
        )
    except Exception as _:
        return 0.0


def get_cuda_version() -> float:
    """获取驱动支持的 CUDA 版本

    Returns:
        float: CUDA 支持的版本
    """
    try:
        # 获取 nvidia-smi 输出
        output = subprocess.check_output(["nvidia-smi", "-q"], text=True)
        match = re.search(r"CUDA Version\s+:\s+(\d+\.\d+)", output)
        if match:
            return float(match.group(1))
        return 0.0
    except Exception as _:
        return 0.0


def get_pytorch_mirror_type_cuda(torch_ver: str) -> str:
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
        return "other"
    if CommonVersionComparison("2.0.0") <= torch_version < CommonVersionComparison("2.3.1"):
        # 2.0.0 <= torch < 2.3.1: default cu118
        return "cu118"
    if CommonVersionComparison("2.3.0") <= torch_version < CommonVersionComparison("2.4.1"):
        # 2.3.0 <= torch < 2.4.1: default cu121
        if CommonVersionComparison(cuda_support_version) < CommonVersionComparison("121"):
            if CommonVersionComparison(cuda_support_version) >= CommonVersionComparison("118"):
                return "cu118"
        return "cu121"
    if CommonVersionComparison("2.4.0") <= torch_version < CommonVersionComparison("2.6.0"):
        # 2.4.0 <= torch < 2.6.0: default cu124
        if CommonVersionComparison(cuda_support_version) < CommonVersionComparison("124"):
            if CommonVersionComparison(cuda_support_version) >= CommonVersionComparison("121"):
                return "cu121"
            if CommonVersionComparison(cuda_support_version) >= CommonVersionComparison("118"):
                return "cu118"
        return "cu124"
    if CommonVersionComparison("2.6.0") <= torch_version < CommonVersionComparison("2.7.0"):
        # 2.6.0 <= torch < 2.7.0: default cu126
        if CommonVersionComparison(cuda_support_version) < CommonVersionComparison("126"):
            if CommonVersionComparison(cuda_support_version) >= CommonVersionComparison("124"):
                return "cu124"
        if CommonVersionComparison(cuda_comp_cap) > CommonVersionComparison("10.0"):
            if CommonVersionComparison(cuda_support_version) >= CommonVersionComparison("128"):
                return "cu128"
        return "cu126"
    if CommonVersionComparison("2.7.0") <= torch_version < CommonVersionComparison("2.8.0"):
        # 2.7.0 <= torch < 2.8.0: default cu128
        if CommonVersionComparison(cuda_support_version) < CommonVersionComparison("128"):
            if CommonVersionComparison(cuda_support_version) > CommonVersionComparison("126"):
                return "cu126"
        return "cu128"
    if CommonVersionComparison("2.8.0") <= torch_version < CommonVersionComparison("2.9.0"):
        # 2.8.0 <= torch < 2.9.0: default cu129
        if CommonVersionComparison(cuda_support_version) < CommonVersionComparison("129"):
            if CommonVersionComparison(cuda_support_version) >= CommonVersionComparison("128"):
                return "cu128"
            if CommonVersionComparison(cuda_support_version) >= CommonVersionComparison("126"):
                return "cu126"
        return "cu129"
    if CommonVersionComparison("2.9.0") <= torch_version < CommonVersionComparison("2.10.0"):
        # 2.9.0 <= torch < 2.10.0: default cu130
        if CommonVersionComparison(cuda_support_version) < CommonVersionComparison("130"):
            if CommonVersionComparison(cuda_support_version) >= CommonVersionComparison("128"):
                return "cu128"
            if CommonVersionComparison(cuda_support_version) >= CommonVersionComparison("126"):
                return "cu126"
        return "cu130"
    if CommonVersionComparison("2.10.0") <= torch_version:
        # torch >= 2.10.0: default cu130
        if CommonVersionComparison(cuda_support_version) < CommonVersionComparison("130"):
            if CommonVersionComparison(cuda_support_version) >= CommonVersionComparison("128"):
                return "cu128"
            if CommonVersionComparison(cuda_support_version) >= CommonVersionComparison("126"):
                return "cu126"
        return "cu130"

    return "cu129"


def get_pytorch_mirror_type_rocm(torch_ver: str) -> str:
    """获取 ROCm 类型的 PyTorch 镜像源类型

    Args:
        torch_ver (str): PyTorch 版本
    Returns:
        str: ROCm 类型的 PyTorch 镜像源类型
    """
    torch_version = CommonVersionComparison(torch_ver)
    if torch_version < CommonVersionComparison("2.4.0"):
        # torch < 2.4.0
        return "other"
    if CommonVersionComparison("2.4.0") <= torch_version < CommonVersionComparison("2.5.0"):
        # 2.4.0 <= torch < 2.5.0
        return "rocm61"
    if CommonVersionComparison("2.5.0") <= torch_version < CommonVersionComparison("2.6.0"):
        # 2.5.0 <= torch < 2.6.0
        return "rocm62"
    if CommonVersionComparison("2.6.0") <= torch_version < CommonVersionComparison("2.7.0"):
        # 2.6.0 <= torch < 2.7.0
        return "rocm624"
    if CommonVersionComparison("2.7.0") <= torch_version < CommonVersionComparison("2.8.0"):
        # 2.7.0 <= torch < 2.8.0
        return "rocm63"
    if CommonVersionComparison("2.8.0") <= torch_version < CommonVersionComparison("2.10.0"):
        # 2.8.0 <= torch < 2.10.0
        return "rocm64"
    if CommonVersionComparison("2.10.0") <= torch_version:
        # 2.10.0 <= torch
        return "rocm71"

    return "rocm71"


def get_pytorch_mirror_type_ipex(torch_ver: str) -> str:
    """获取 IPEX 类型的 PyTorch 镜像源类型

    Args:
        torch_ver (str): PyTorch 版本
    Returns:
        str: IPEX 类型的 PyTorch 镜像源类型
    """
    torch_version = CommonVersionComparison(torch_ver)
    if torch_version < CommonVersionComparison("2.0.0"):
        # torch < 2.0.0
        return "other"
    if torch_version == CommonVersionComparison("2.0.0"):
        # torch == 2.0.0
        return "ipex_legacy_arc"
    if CommonVersionComparison("2.0.0") < torch_version < CommonVersionComparison("2.1.0"):
        # 2.0.0 < torch < 2.1.0
        return "other"
    if torch_version == CommonVersionComparison("2.1.0"):
        # torch == 2.1.0
        return "ipex_legacy_arc"
    if torch_version >= CommonVersionComparison("2.6.0"):
        # torch >= 2.6.0
        return "xpu"

    return "xpu"


def get_pytorch_mirror_type_cpu(torch_ver: str) -> str:
    """获取 CPU 类型的 PyTorch 镜像源类型

    Args:
        torch_ver (str): PyTorch 版本
    Returns:
        str: CPU 类型的 PyTorch 镜像源类型
    """
    _ = torch_ver
    return "cpu"


def get_pytorch_mirror_type(torch_ver: str, device_type: Literal["cuda", "rocm", "xpu", "cpu"]) -> str:
    """获取 PyTorch 镜像源类型

    Args:
        torch_ver (str): PyTorch 版本号
        device_type (Literal["cuda", "rocm", "xpu", "cpu"]): 显卡类型
    Returns:
        str: PyTorch 镜像源类型
    """
    if device_type == "cuda":
        return get_pytorch_mirror_type_cuda(torch_ver)

    if device_type == "rocm":
        return get_pytorch_mirror_type_rocm(torch_ver)

    if device_type == "xpu":
        return get_pytorch_mirror_type_ipex(torch_ver)

    if device_type == "cpu":
        return get_pytorch_mirror_type_cpu(torch_ver)

    return "other"


def get_env_pytorch_type() -> str:
    """获取当前环境中 PyTorch 版本号对应的类型

    Returns:
        str: PyTorch 类型 (cuda, rocm, xpu, cpu)
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

    torch_type = torch_ver.split("+").pop()

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

    return "cuda"
