"""PyTorch 版本检查"""

from sd_webui_all_in_one.utils import load_source_directly
from sd_webui_all_in_one.pytorch_manager import (
    auto_detect_available_pytorch_type,
    get_available_pytorch_device_type,
    get_gpu_list,
    has_gpus,
)
from sd_webui_all_in_one.env_check.shared import logger
from sd_webui_all_in_one.env_check.check_torch_version.models import (
    CPU_PYTORCH_TYPES,
    TorchVersionCheckResult,
)
from sd_webui_all_in_one.env_check.check_torch_version.compatibility import (
    _is_rocm_version_compatible,
    _is_ipex_version,
)


def check_torch_version_status() -> TorchVersionCheckResult:
    """检查 PyTorch 版本可用性并返回结构化结果。

    是否应当使用 GPU 版 PyTorch 的判断标准与自动选择 PyTorch 类型 (`auto_detect_available_pytorch_type`) 保持一致:
    当自动选择的结果为 CPU 类型时 (设备上没有显卡, 或者显卡不受 PyTorch 支持), CPU 类型的 PyTorch 视为适合当前设备。

    Returns:
        TorchVersionCheckResult: PyTorch 版本检查结果。
    """
    raw_gpu_list = get_gpu_list()
    available_types = [str(item) for item in get_available_pytorch_device_type(raw_gpu_list)]
    recommended_type = str(auto_detect_available_pytorch_type(raw_gpu_list))
    gpu_list = [str(item) for item in raw_gpu_list]
    has_gpu = has_gpus(raw_gpu_list)
    torch_data = load_source_directly("torch.version") or {}
    torch_ver: str | None = torch_data.get("__version__")
    if torch_ver is None:
        return {
            "available_types": available_types,
            "gpu_list": gpu_list,
            "has_gpu": has_gpu,
            "installed_version": None,
            "installed_type": None,
            "status": "missing",
            "is_compatible": False,
            "message": "当前环境中未安装 PyTorch, 这将导致无法正常进行推理或者训练任务, 请安装对应版本的 PyTorch 后再试",
        }

    torch_type = torch_ver.split("+")[-1] if "+" in torch_ver else "all"
    if torch_type in CPU_PYTORCH_TYPES:
        if recommended_type not in CPU_PYTORCH_TYPES:
            return {
                "available_types": available_types,
                "gpu_list": gpu_list,
                "has_gpu": has_gpu,
                "installed_version": torch_ver,
                "installed_type": torch_type,
                "status": "cpu_with_gpu",
                "is_compatible": False,
                "message": "当前环境使用的 PyTorch 类型为 CPU, 而当前设备有可用的 GPU, 可尝试重装适配 GPU 的 PyTorch 以加速推理",
            }
    elif has_gpu:
        if torch_type not in available_types:
            if _is_rocm_version_compatible(torch_type, available_types) or _is_ipex_version(torch_type, available_types):
                return {
                    "available_types": available_types,
                    "gpu_list": gpu_list,
                    "has_gpu": has_gpu,
                    "installed_version": torch_ver,
                    "installed_type": torch_type,
                    "status": "compatible",
                    "is_compatible": True,
                    "message": "当前环境中的 PyTorch 无版本问题",
                }

            return {
                "available_types": available_types,
                "gpu_list": gpu_list,
                "has_gpu": has_gpu,
                "installed_version": torch_ver,
                "installed_type": torch_type,
                "status": "unsupported_type",
                "is_compatible": False,
                "message": "当前设备支持的 PyTorch 类型和当前环境安装的 PyTorch 类型不匹配, 该类型并不支持当前设备, 可能会导致性能下降的问题, 可尝试重新安装对应版本的 PyTorch",
            }

    return {
        "available_types": available_types,
        "gpu_list": gpu_list,
        "has_gpu": has_gpu,
        "installed_version": torch_ver,
        "installed_type": torch_type,
        "status": "compatible",
        "is_compatible": True,
        "message": "当前环境中的 PyTorch 无版本问题",
    }


def check_torch_version() -> None:
    """检查 PyTorch 版本可用性"""
    logger.info("检查当前环境中的 PyTorch 版本中")
    result = check_torch_version_status()
    if result["status"] == "missing":
        logger.warning(result["message"])
        return

    if result["status"] == "cpu_with_gpu":
        logger.warning(result["message"])
        return

    if result["status"] == "unsupported_type":
        logger.warning(
            "当前设备支持的 PyTorch 类型有 %s, 而当前环境安装的 PyTorch 类型为 %s, 该类型并不支持当前设备, 可能会导致性能下降的问题, 可尝试重新安装对应版本的 PyTorch",
            result["available_types"],
            result["installed_type"],
        )
        return

    logger.info(result["message"])
