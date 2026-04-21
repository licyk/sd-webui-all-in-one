"""检查当前环境的 PyTorch 版本正确性"""

import sys

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.utils import load_source_directly
from sd_webui_all_in_one.pytorch_manager import (
    get_avaliable_pytorch_device_type,
    get_gpu_list,
    has_gpus,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def _is_rocm_version_compatible(
    torch_type: str,
    available_types: list[str],
) -> bool:
    """检查 ROCm 版本是否兼容

    支持小版本号匹配，例如：
    - torch_type="rocm7.2.1" 可以匹配 available_types 中的 "rocm7.2"
    - torch_type="rocm6.2.4" 可以匹配 available_types 中的 "rocm6.2"

    Args:
        torch_type: 当前安装的 PyTorch ROCm 类型
        available_types: 可用的设备类型列表

    Returns:
        bool: 如果版本兼容则返回 True
    """
    if not torch_type.startswith("rocm"):
        return False

    for available_type in available_types:
        if not available_type.startswith("rocm"):
            continue

        # 提取主版本号（例如：rocm7.2.1 -> rocm7.2）
        torch_parts = torch_type.split(".")
        available_parts = available_type.split(".")

        # 比较前两个部分（rocm + 主版本号）
        if len(torch_parts) >= 2 and len(available_parts) >= 2:
            if torch_parts[0] == available_parts[0] and torch_parts[1] == available_parts[1]:
                return True

    if sys.platform == "win32" and "rocm_win" in available_types:
        return True

    return False


def _is_ipex_version(
    torch_type: str,
    available_types: list[str],
) -> bool:
    """检查 IPEX 版本是否兼容

    Args:
        torch_type: 当前安装的 PyTorch ROCm 类型
        available_types: 可用的设备类型列表

    Returns:
        bool: 如果版本兼容则返回 True
    """
    return all(i in available_types for i in ["xpu", "ipex_legacy_arc"]) and torch_type in ["gite9ebda2", "git7bcf7da", "cxx11.abi"]


def check_torch_version() -> None:
    """检查 PyTorch 版本可用性"""
    logger.info("检查当前环境中的 PyTorch 版本中")
    avaliable_types = get_avaliable_pytorch_device_type()
    gpu_list = get_gpu_list()
    torch_ver: str | None = load_source_directly("torch.version").get("__version__")
    if torch_ver is None:
        logger.warning("当前环境中未安装 PyTorch, 这将导致无法正常进行推理或者训练任务, 请安装对应版本的 PyTorch 后再试")
        return

    torch_type = torch_ver.split("+")[-1] if "+" in torch_ver else "all"
    if has_gpus(gpu_list):
        if torch_type in ("all", "cpu"):
            logger.warning("当前环境使用的 PyTorch 类型为 CPU, 而当前设备有可用的 GPU, 可尝试重装适配 GPU 的 PyTorch 以加速推理")
            return

        if torch_type not in avaliable_types:
            if _is_rocm_version_compatible(torch_type, avaliable_types) or _is_ipex_version(torch_type, avaliable_types):
                logger.info("当前环境中的 PyTorch 无版本问题")
                return

            logger.warning(
                "当前设备支持的 PyTorch 类型为 %s, 而当前环境安装的 PyTorch 类型有 %s, 该类型并不支持当前设备, 可能会导致性能下降的问题, 可尝试重新安装对应版本的 PyTorch", torch_type, avaliable_types
            )
            return

    logger.info("当前环境中的 PyTorch 无版本问题")
