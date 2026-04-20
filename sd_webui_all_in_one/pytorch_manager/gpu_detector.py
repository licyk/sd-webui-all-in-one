"""硬件检测"""

import re
import json
import shutil
import sys
import subprocess
from typing import TypedDict

from sd_webui_all_in_one.package_analyzer import CommonVersionComparison
from sd_webui_all_in_one.pytorch_manager.types import (
    PYTORCH_DEVICE_LIST,
    PyTorchDeviceType,
    PyTorchDeviceTypeCategory,
)


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
                subprocess.run(
                    ["nvidia-smi", "--query-gpu=compute_cap", "--format=noheader,csv"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding="utf-8",
                    text=True,
                    errors="ignore",
                    check=True,
                ).stdout.splitlines(),
            )
        )
    except Exception:
        return 0.0


def get_cuda_version() -> float:
    """获取驱动支持的 CUDA 版本

    Returns:
        float: CUDA 支持的版本
    """
    try:
        # 获取 nvidia-smi 输出
        output = subprocess.run(
            ["nvidia-smi", "-q"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            text=True,
            errors="ignore",
            check=True,
        ).stdout
        match = re.search(r"CUDA Version\s+:\s+(\d+\.\d+)", output)
        if match:
            return float(match.group(1))
        return 0.0
    except Exception:
        return 0.0


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
        cmd = ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterCompatibility, AdapterRAM, DriverVersion | ConvertTo-Json"]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            text=True,
            errors="ignore",
            check=True,
        ).stdout
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
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            text=True,
            errors="ignore",
            check=True,
        )
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
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            text=True,
            errors="ignore",
            check=True,
        )
        gpu_info: list[GPUDeviceInfo] = []
        for line in result.stdout.strip().splitlines():
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
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            text=True,
            errors="ignore",
            check=True,
        )
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
    return any(x for x in gpu_list if "Intel" in x.get("AdapterCompatibility", "") or "NVIDIA" in x.get("AdapterCompatibility", "") or "Advanced Micro Devices" in x.get("AdapterCompatibility", ""))


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
    return any(x for x in gpu_list if "Intel" in x.get("AdapterCompatibility", "") and (x.get("Name", "").startswith("Intel(R) Arc") or x.get("Name", "").startswith("Intel(R) Core Ultra")))


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
        if CommonVersionComparison(cuda_comp_cap) >= CommonVersionComparison("10.0"):
            # RTX 50xx
            for ver in PYTORCH_DEVICE_LIST:
                if not ver.startswith("cu"):
                    continue

                if CommonVersionComparison(ver.removeprefix("cu")) >= CommonVersionComparison(str(int(12.8 * 10))):
                    device_list.append(ver)
        else:
            for ver in PYTORCH_DEVICE_LIST:
                if not ver.startswith("cu"):
                    continue

                if CommonVersionComparison(ver.removeprefix("cu")) <= CommonVersionComparison(str(int(cuda_support_ver * 10))):
                    device_list.append(ver)

    if intel_xpu_avaliable:
        device_list.append("xpu")
        device_list.append("ipex_legacy_arc")

    if amd_gpu_avaliable and sys.platform == "linux":
        for ver in PYTORCH_DEVICE_LIST:
            if not ver.startswith("rocm") or ver == "rocm_win":
                continue

            device_list.append(ver)

    if amd_gpu_avaliable and sys.platform == "win32":
        device_list.append("rocm_win")

    return device_list


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

    if amd_gpu_avaliable:
        if sys.platform == "linux":
            return "rocm7.1"
        if sys.platform == "win32":
            return "rocm_win"

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

    if sys.platform == "darwin":
        return "mps"

    if not gpu_avaliable:
        return "cpu"

    if nvidia_gpu_avaliable:
        return "cuda"

    if intel_xpu_avaliable:
        return "xpu"

    if amd_gpu_avaliable:
        return "rocm"

    return "cpu"
