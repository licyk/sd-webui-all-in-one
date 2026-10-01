"""PyTorch 版本检查结果类型"""

from typing import Literal, TypedDict


CPU_PYTORCH_TYPES = ("all", "cpu")
"""不使用 GPU 加速的 PyTorch 类型"""


TorchVersionCheckStatus = Literal["missing", "cpu_with_gpu", "unsupported_type", "compatible"]
"""PyTorch 版本检查状态。"""


class TorchVersionCheckResult(TypedDict):
    """PyTorch 版本检查结果。

    Attributes:
        available_types (list[str]): 当前设备支持的 PyTorch 类型列表。
        gpu_list (list[str]): 当前检测到的 GPU 列表。
        has_gpu (bool): 当前环境是否检测到显卡 (不代表该显卡受 PyTorch 支持)。
        installed_version (str | None): 当前环境安装的 PyTorch 版本。
        installed_type (str | None): 当前环境安装的 PyTorch 类型。
        status (TorchVersionCheckStatus): PyTorch 版本检查状态。
        is_compatible (bool): 当前 PyTorch 版本是否适合当前设备。
        message (str): 检查结果说明。
    """

    available_types: list[str]
    """当前设备支持的 PyTorch 类型列表。"""

    gpu_list: list[str]
    """当前检测到的 GPU 列表。"""

    has_gpu: bool
    """当前环境是否检测到显卡 (不代表该显卡受 PyTorch 支持)。"""

    installed_version: str | None
    """当前环境安装的 PyTorch 版本。"""

    installed_type: str | None
    """当前环境安装的 PyTorch 类型。"""

    status: TorchVersionCheckStatus
    """PyTorch 版本检查状态。"""

    is_compatible: bool
    """当前 PyTorch 版本是否适合当前设备。"""

    message: str
    """检查结果说明。"""
