"""PyTorch 镜像管理工具"""

import json
import re
import shutil
import subprocess
import sys
from typing import TypedDict

from sd_webui_all_in_one.package_analyzer.ver_cmp import CommonVersionComparison
from sd_webui_all_in_one.package_analyzer.py_ver_cmp import PyWhlVersionComparison
from sd_webui_all_in_one.package_analyzer.pkg_check import is_package_has_version, get_package_version
from sd_webui_all_in_one.pytorch_manager.base import (
    PYTORCH_MIRROR_DICT,
    PYTORCH_MIRROR_NJU_DICT,
    PYTORCH_DOWNLOAD_DICT,
    PyTorchVersionInfoList,
    PyTorchVersionInfo,
    PYTORCH_DEVICE_LIST,
    PyTorchDeviceType,
    PyTorchDeviceTypeCategory,
)
from sd_webui_all_in_one.utils import ANSIColor


def get_pytorch_mirror_dict(use_cn_mirror: bool | None = False) -> dict[str, str]:
    """获取 PyTorch 镜像源字典

    Args:
        use_cn_mirror (bool | None): 是否使用国内镜像 (NJU)
    Returns:
        (dict[str, str]): PyTorch 镜像源字典的副本, 键为设备类型 (如 "cu118", "rocm6.1" 等), 值为对应的 PyTorch wheel 下载地址
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
        return "all"
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


def get_pytorch_mirror_type_cpu(torch_ver: str) -> str:
    """获取 CPU 类型的 PyTorch 镜像源类型

    Args:
        torch_ver (str): PyTorch 版本
    Returns:
        str: CPU 类型的 PyTorch 镜像源类型
    """
    _ = torch_ver
    return "cpu"


def get_pytorch_mirror_type(torch_ver: str, device_type: PyTorchDeviceTypeCategory) -> str:
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


class GPUDeviceInfo(TypedDict, total=False):
    """显卡信息"""

    Name: str
    """显卡名称"""

    AdapterCompatibility: str | None
    """显卡兼容能力 (类型)"""

    AdapterRAM: str | None
    """显卡显存大小"""

    DriverVersion: str | None
    """驱动版本"""


def get_windows_gpu_list() -> list[GPUDeviceInfo]:
    """获取 Windows 上的显卡列表

    Args:
        list[GPUDeviceInfo]:
            显卡信息列表
    """
    try:
        cmd = ["powershell", "-Command", "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterCompatibility, AdapterRAM, DriverVersion | ConvertTo-Json"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        gpus = json.loads(result.stdout)
        if isinstance(gpus, dict):
            gpus = [gpus]

        gpu_info = []
        for gpu in gpus:
            gpu_info.append(
                {
                    "Name": gpu.get("Name", None),
                    "AdapterCompatibility": gpu.get("AdapterCompatibility", None),
                    "AdapterRAM": gpu.get("AdapterRAM", None),
                    "DriverVersion": gpu.get("DriverVersion", None),
                }
            )
        return gpu_info
    except Exception as _:
        return []


def get_lshw_gpus() -> list[GPUDeviceInfo]:
    """通过 lshw 获取 GPU 信息

    Args:
        list[GPUDeviceInfo]:
            显卡信息列表
    """
    if not shutil.which("lshw"):
        return []

    try:
        cmd = ["lshw", "-C", "display", "-json"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        gpus = [data] if isinstance(data, dict) else data

        gpu_info: list[GPUDeviceInfo] = []
        for gpu in gpus:
            gpu_info.append(
                {
                    "Name": gpu.get("product"),
                    "AdapterCompatibility": gpu.get("vendor"),
                    "AdapterRAM": str(gpu.get("size")) if gpu.get("size") else None,
                    "DriverVersion": gpu.get("configuration", {}).get("driver"),
                }
            )
        return gpu_info
    except Exception:
        return []


def get_nvidia_smi_gpus() -> list[GPUDeviceInfo]:
    """通过 nvidia-smi 获取 NVIDIA 显卡精确信息

    Args:
        list[GPUDeviceInfo]:
            显卡信息列表
    """
    if not shutil.which("nvidia-smi"):
        return []

    try:
        cmd = ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        gpu_info: list[GPUDeviceInfo] = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            gpu_info.append(
                {
                    "Name": parts[0],
                    "AdapterCompatibility": "NVIDIA",
                    "AdapterRAM": str(int(parts[1]) * 1024 * 1024) if parts[1].isdigit() else None,
                    "DriverVersion": parts[2],
                }
            )
        return gpu_info
    except Exception:
        return []


def get_lspci_gpus() -> list[GPUDeviceInfo]:
    """通过 lspci 获取显卡信息

    Args:
        list[GPUDeviceInfo]:
            显卡信息列表
    """
    if not shutil.which("lspci"):
        return []

    try:
        cmd = ["lspci", "-vmm", "-d", "::0300"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        gpu_info: list[GPUDeviceInfo] = []
        devices = result.stdout.strip().split("\n\n")
        for dev in devices:
            info = {line.split(":", 1)[0].strip(): line.split(":", 1)[1].strip() for line in dev.split("\n") if ":" in line}
            gpu_info.append(
                {
                    "Name": info.get("Device"),
                    "AdapterCompatibility": info.get("Vendor"),
                    "AdapterRAM": None,
                    "DriverVersion": info.get("Driver"),
                }
            )
        return gpu_info
    except Exception:
        return []


def get_linux_gpu_list() -> list[GPUDeviceInfo]:
    """获取 Linux 上的显卡列表

    Args:
        list[GPUDeviceInfo]:
            显卡信息列表
    """
    all_gpus: list[GPUDeviceInfo] = []

    all_gpus.extend(get_nvidia_smi_gpus())
    all_gpus.extend(get_lshw_gpus())
    all_gpus.extend(get_lspci_gpus())

    unique_gpus: GPUDeviceInfo = {}

    for gpu in all_gpus:
        name = gpu.get("Name")
        if not name:
            continue

        norm_name = name.strip().lower()

        if norm_name not in unique_gpus:
            unique_gpus[norm_name] = gpu
        else:
            existing = unique_gpus[norm_name]
            for key in ["AdapterCompatibility", "AdapterRAM", "DriverVersion"]:
                if not existing.get(key) and gpu.get(key):
                    existing[key] = gpu[key]

    return list(unique_gpus.values())


def get_gpu_list() -> list[GPUDeviceInfo]:
    """获取当前平台上的 GPU 列表

    Args:
        list[GPUDeviceInfo]:
            显卡信息列表
    """
    if sys.platform == "win32":
        return get_windows_gpu_list()
    elif sys.platform == "linux":
        return get_linux_gpu_list()
    else:
        return []


def has_gpus(
    gpu_list: list[GPUDeviceInfo],
) -> bool:
    """检测 GPU 列表中是否包含可用的显卡

    Args:
        gpu_list (list[GPUDeviceInfo]):
            GPU 列表

    Returns:
        bool:
            当列表中存在可用显卡时则返回 True
    """
    return any(
        x
        for x in gpu_list
        if "Intel" in x.get("AdapterCompatibility", "") or "NVIDIA" in x.get("AdapterCompatibility", "") or "Advanced Micro Devices" in x.get("AdapterCompatibility", "")
    )


def has_nvidia_gpu(
    gpu_list: list[GPUDeviceInfo],
) -> bool:
    """检测 GPU 列表中是否包含可用的 Nvidia 显卡

    Args:
        gpu_list (list[GPUDeviceInfo]):
            GPU 列表

    Returns:
        bool:
            当列表中存在可用的 Nvidia 显卡时则返回 True
    """
    return any(
        x
        for x in gpu_list
        if "NVIDIA" in x.get("AdapterCompatibility", "")
        and (x.get("Name", "").startswith("NVIDIA") or x.get("Name", "").startswith("GeForce") or x.get("Name", "").startswith("Tesla") or x.get("Name", "").startswith("Quadro"))
    )


def has_intel_xpu(
    gpu_list: list[GPUDeviceInfo],
) -> bool:
    """检测 GPU 列表中是否包含可用的 Intel 显卡

    Args:
        gpu_list (list[GPUDeviceInfo]):
            GPU 列表

    Returns:
        bool:
            当列表中存在可用的 Intel 显卡时则返回 True
    """
    return any(
        x
        for x in gpu_list
        if "Intel" in x.get("AdapterCompatibility", "") and (x.get("Name", "").startswith("Intel(R) Arc") or x.get("Name", "").startswith("Intel(R) Core Ultra"))
    )


def has_amd_gpu(
    gpu_list: list[GPUDeviceInfo],
) -> bool:
    """检测 GPU 列表中是否包含可用的 AMD 显卡

    Args:
        gpu_list (list[GPUDeviceInfo]):
            GPU 列表

    Returns:
        bool:
            当列表中存在可用的 AMD 显卡时则返回 True
    """
    return any(x for x in gpu_list if "Advanced Micro Devices" in x.get("AdapterCompatibility", "") and x.get("Name", "").startswith("AMD Radeon"))


def get_avaliable_pytorch_device_type() -> list[str]:
    """获取当前设备上可用的 PyTorch 设备类型

    Returns:
        list[str]:
            可用的 PyTorch 设备类型列表
    """
    gpu_list = get_gpu_list()
    cuda_comp_cap = get_cuda_comp_cap()
    cuda_support_ver = get_cuda_version()
    device_list = ["all"]
    if sys.platform != "darwin":
        device_list.append("cpu")

    gpu_avaliable = has_gpus(gpu_list)
    nvidia_gpu_avaliable = has_nvidia_gpu(gpu_list)
    intel_xpu_avaliable = has_intel_xpu(gpu_list)
    amd_gpu_avaliable = has_amd_gpu(gpu_list)

    if gpu_avaliable:
        device_list.append("directml")

    if nvidia_gpu_avaliable:
        if CommonVersionComparison(cuda_comp_cap) < CommonVersionComparison("10.0"):
            for ver in PYTORCH_DEVICE_LIST:
                if not ver.startswith("cu"):
                    continue

                if CommonVersionComparison(ver) >= CommonVersionComparison(str(int(12.8 * 10))):
                    device_list.append(ver)
        else:
            for ver in PYTORCH_DEVICE_LIST:
                if not ver.startswith("cu"):
                    continue

                if CommonVersionComparison(ver) <= CommonVersionComparison(str(int(cuda_support_ver * 10))):
                    device_list.append(ver)

    if intel_xpu_avaliable:
        device_list.append("xpu")
        device_list.append("ipex_legacy_arc")

    if amd_gpu_avaliable and sys.platform == "linux":
        for ver in PYTORCH_DEVICE_LIST:
            if not ver.startswith("rocm"):
                continue

            device_list.append(ver)

    return device_list


def export_pytorch_list() -> PyTorchVersionInfoList:
    """导出 PyTorch 版本列表

    Returns:
        PyTorchVersionInfoList:
            PyTorch 版本列表
    """
    pytorch_list = PYTORCH_DOWNLOAD_DICT.copy()
    device_list = set(get_avaliable_pytorch_device_type())
    new_pytorch_list: PyTorchVersionInfoList = []

    for i in pytorch_list:
        supported = False
        if i["dtype"] in device_list:
            supported = True

        i["supported"] = supported
        new_pytorch_list.append(i)

    return new_pytorch_list


def auto_detect_avaliable_pytorch_type() -> PyTorchDeviceType:
    """检测当前的设备并获取适配当前设备的 PyTorch 类型

    Returns:
        PyTorchDeviceType:
            支持当前设备的 PyTorch 类型
    """
    gpu_list = get_gpu_list()
    cuda_comp_cap = get_cuda_comp_cap()
    cuda_support_ver = get_cuda_version()

    gpu_avaliable = has_gpus(gpu_list)
    nvidia_gpu_avaliable = has_nvidia_gpu(gpu_list)
    intel_xpu_avaliable = has_intel_xpu(gpu_list)
    amd_gpu_avaliable = has_amd_gpu(gpu_list)

    if sys.platform == "darwin":
        return "all"

    if not gpu_avaliable:
        return "cpu"

    if nvidia_gpu_avaliable:
        if CommonVersionComparison(cuda_support_ver) >= CommonVersionComparison("13.0"):
            return "cu130"
        if CommonVersionComparison(cuda_support_ver) >= CommonVersionComparison("12.9"):
            return "cu129"
        if CommonVersionComparison(cuda_support_ver) >= CommonVersionComparison("12.8"):
            return "cu128"
        if CommonVersionComparison(cuda_support_ver) >= CommonVersionComparison("12.6"):
            return "cu126"
        if CommonVersionComparison(cuda_support_ver) >= CommonVersionComparison("12.4"):
            return "cu124"
        if CommonVersionComparison(cuda_support_ver) >= CommonVersionComparison("12.1"):
            return "cu121"
        if CommonVersionComparison(cuda_support_ver) >= CommonVersionComparison("11.8"):
            return "cu118"
        if CommonVersionComparison(cuda_comp_cap) >= CommonVersionComparison("10.0"):
            return "cu130"

    if intel_xpu_avaliable:
        return "xpu"

    if amd_gpu_avaliable and sys.platform == "linux":
        return "rocm7.1"

    return "cpu"


def auto_detect_pytorch_device_category() -> PyTorchDeviceTypeCategory:
    """检测当前的设备并获取大致的 PyTorch 设备分类类型 (不带版本号)

    Returns:
        PyTorchDeviceTypeCategory:
            支持当前设备的通用类型
    """
    gpu_list = get_gpu_list()
    gpu_avaliable = has_gpus(gpu_list)
    nvidia_gpu_avaliable = has_nvidia_gpu(gpu_list)
    intel_xpu_avaliable = has_intel_xpu(gpu_list)
    amd_gpu_avaliable = has_amd_gpu(gpu_list)

    if not gpu_avaliable:
        return "cpu"

    if nvidia_gpu_avaliable:
        return "cuda"

    if intel_xpu_avaliable:
        return "xpu"

    if amd_gpu_avaliable and sys.platform == "linux":
        return "rocm"

    return "cpu"


def find_latest_pytorch_info(dtype: PyTorchDeviceType) -> PyTorchVersionInfo:
    """根据 PyTorch 类型在 PyTorch 版本下载信息列表中查找适合该类型的最新版本的 PyTorch 下载信息

    Args:
        dtype (PyTorchDeviceType):
            PyTorch 支持的设备类型

    Returns:
        PyTorchVersionInfo:
            PyTorch 版本下载信息

    Raises:
        ValueError:
            PyTorch 支持的设备类型无效时
    """
    pytorch_list = PYTORCH_DOWNLOAD_DICT.copy()
    pytorch_info_list = [x for x in pytorch_list if x["dtype"] == dtype]
    if not pytorch_info_list:
        raise ValueError(f"PyTorch 类型不存在: '{dtype}'")

    latest_info = pytorch_info_list[0]

    for info in pytorch_info_list:
        current_torch = info["torch_ver"].split()[0]
        history_torch = latest_info["torch_ver"].split()[0]
        current_ver = get_package_version(current_torch) if is_package_has_version(current_torch) else "0.0"
        history_ver = get_package_version(history_torch) if is_package_has_version(history_torch) else "0.0"
        if PyWhlVersionComparison(current_ver) > PyWhlVersionComparison(history_ver):
            latest_info = info

    return latest_info


def get_pytorch_mirror(
    dtype: PyTorchDeviceType,
    use_cn_mirror: bool | None = False,
) -> str:
    """根据 PyTorch 类型获取对应的 PyTorch 镜像源

    Args:
        dtype (PyTorchDeviceType):
            PyTorch 支持的设备类型
        use_cn_mirror (bool | None):
            是否使用国内镜像源

    Returns:
        str:
            PyTorch 镜像源

    Raises:
        ValueError:
            未找到对应的 PyTorch 镜像源时
    """
    url = PYTORCH_MIRROR_NJU_DICT.get(dtype) if use_cn_mirror else PYTORCH_MIRROR_DICT.get(dtype)
    if url is None:
        raise ValueError(f"未找到 '{dtype}' 对应的 PyTorch 镜像源")

    return url


def display_pytorch_config(pytorch_list: PyTorchVersionInfoList) -> None:
    """显示 PyTorch 配置列表并标注当前平台是否支持

    Args:
        pytorch_list (PyTorchVersionInfoList):
            包含 PyTorch 配置信息的列表
    """
    for index, item in enumerate(pytorch_list, start=1):
        name = item["name"]

        if item["supported"]:
            status_text = f"{ANSIColor.GREEN}(支持✓){ANSIColor.RESET}"
        else:
            status_text = f"{ANSIColor.RED}(不支持×){ANSIColor.RESET}"

        print(f"- {ANSIColor.GOLD}{index}{ANSIColor.RESET}、{ANSIColor.WHITE}{name}{ANSIColor.RESET} {status_text}")


def query_pytorch_info_from_library(
    pytorch_name: str | None = None,
    pytorch_index: int | None = None,
) -> PyTorchVersionInfo:
    """从 PyTorch 版本库中查找指定的 PyTorch 版本下载信息

    Args:
        pytorch_name (str | None):
            PyTorch 版本组合名称
        pytorch_index (int | None):
            PyTorch 版本组合的索引值

    Returns:
        PyTorchVersionInfo:
            PyTorch 版本下载信息

    Raises:
        ValueError:
            索引值超出范围时
        FileNotFoundError:
            未根据 PyTorch 组合名称找到 PyTorch 版本下载信息时
    """

    def _validate_index(index: int) -> None:
        if not 0 < index <= len(pytorch_list):
            raise ValueError(f"索引值 {index} 超出范围, 模型有效的范围为: 1 ~ {len(pytorch_list)}")

    def _get_pytorch_with_name(name: str) -> PyTorchVersionInfo:
        for m in pytorch_list:
            if m["name"] == name:
                return m

        raise FileNotFoundError(f"未找到指定的 PyTorch 版本组合名称: {name}")

    pytorch_list = PYTORCH_DOWNLOAD_DICT.copy()
    if pytorch_name is None and pytorch_index is None:
        raise ValueError("`pytorch_name` 和 `pytorch_index` 缺失, 需要提供其中一项才能进行 PyTorch 下载信息查找")

    if pytorch_index is not None:
        _validate_index(pytorch_index)
        return pytorch_list[pytorch_index - 1]
    elif pytorch_name is not None:
        return _get_pytorch_with_name(pytorch_name)
