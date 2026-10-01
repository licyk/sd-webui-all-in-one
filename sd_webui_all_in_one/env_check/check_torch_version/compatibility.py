"""PyTorch 类型兼容性判断"""

from collections.abc import Sequence

from sd_webui_all_in_one.pytorch_manager import (
    PYTORCH_DEVICE_TYPE_ALIAS_DICT,
    normalize_pytorch_version_suffix,
)


def _is_rocm_version_compatible(
    torch_type: str,
    available_types: Sequence[str],
) -> bool:
    """检查 ROCm 版本是否兼容

    支持小版本号匹配，例如：
    - torch_type="rocm7.2.1" 可以匹配 available_types 中的 "rocm7.2"
    - torch_type="rocm6.2.4" 可以匹配 available_types 中的 "rocm6.2"

    同时支持平台专用类型匹配，例如：
    - Windows 上的 ROCm 类型根据 ROCm 主版本号匹配 "rocm7" / "rocm10"
    - Linux 上 AMD 多架构 wheel 类型 (如 "rocm7.14.1", "rocm10.0.0") 根据 ROCm 主版本号匹配 "rocm7" / "rocm10"
    - 旧版类型名称 "rocm_win" / "rocm_linux" 等价于 "rocm10"

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

    return normalize_pytorch_version_suffix(torch_type) in {PYTORCH_DEVICE_TYPE_ALIAS_DICT.get(x, x) for x in available_types}


def _is_ipex_version(
    torch_type: str,
    available_types: Sequence[str],
) -> bool:
    """检查 IPEX 版本是否兼容

    Args:
        torch_type: 当前安装的 PyTorch ROCm 类型
        available_types: 可用的设备类型列表

    Returns:
        bool: 如果版本兼容则返回 True
    """
    return all(i in available_types for i in ["xpu", "ipex_legacy_arc"]) and torch_type in ["gite9ebda2", "git7bcf7da", "cxx11.abi"]
