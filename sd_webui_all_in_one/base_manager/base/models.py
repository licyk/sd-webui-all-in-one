"""共享管理类型。"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from sd_webui_all_in_one.pytorch_manager import (
    PyTorchDeviceType,
)
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


@dataclass(frozen=True)
class EnvCheckTask:
    """命名环境检查任务。"""

    name: str
    """稳定的检查任务名称。"""

    func: Callable[..., Any]
    """检查任务函数。"""

    kwargs: dict[str, Any]
    """检查任务参数。"""


@dataclass(frozen=True)
class WebUiLaunchInfo:
    """WebUI 启动参数信息。"""

    webui_path: Path
    """WebUI 根目录。"""

    launch_script: str | Path
    """启动脚本路径。"""

    webui_name: str
    """WebUI 显示名称。"""

    launch_args: list[str]
    """启动参数列表。"""

    custom_env: dict[str, str]
    """启动环境变量。"""


@dataclass(frozen=True)
class PyTorchUpdateStatus:
    """PyTorch 更新检查状态。"""

    installed: bool
    current_version: str | None
    device_type: PyTorchDeviceType
    latest_version: str | None
    latest_name: str | None
    has_update: bool
    error: str | None = None


@dataclass(frozen=True, slots=True)
class EnvironmentCollectionError:
    """单个环境信息采集项的错误。"""

    component: str
    """采集项稳定名称。"""

    message: str
    """错误说明。"""


@dataclass(frozen=True, slots=True)
class ManagerEnvironmentInfo:
    """管理器版本信息。"""

    name: str
    """管理器包名称。"""

    version: str
    """管理器版本。"""


@dataclass(frozen=True, slots=True)
class OperatingSystemEnvironmentInfo:
    """操作系统环境信息。"""

    platform: str
    """完整平台描述。"""

    system: str
    """操作系统名称。"""

    release: str
    """操作系统发行版本。"""

    version: str
    """操作系统详细版本。"""

    machine: str
    """机器架构。"""


@dataclass(frozen=True, slots=True)
class CpuEnvironmentInfo:
    """CPU 环境信息。"""

    name: str
    """CPU 或处理器名称。"""

    logical_cores: int | None
    """逻辑核心数。"""


@dataclass(frozen=True, slots=True)
class GpuEnvironmentInfo:
    """GPU 环境信息。"""

    name: str
    """GPU 名称。"""

    vendor: str | None = None
    """GPU 厂商。"""

    memory_bytes: int | None = None
    """显存字节数。"""

    driver_version: str | None = None
    """驱动版本。"""


@dataclass(frozen=True, slots=True)
class PyTorchEnvironmentInfo:
    """PyTorch 安装和硬件兼容信息。"""

    installed_version: str | None
    """已安装的 PyTorch 版本。"""

    installed_type: str | None
    """已安装的 PyTorch 设备类型。"""

    available_types: list[str]
    """当前设备可使用的 PyTorch 类型。"""

    status: str
    """兼容性状态；探测失败时为 ``unknown``。"""

    is_compatible: bool | None
    """当前 PyTorch 是否兼容硬件；探测失败时为 ``None``。"""

    message: str
    """兼容性说明。"""


@dataclass(frozen=True, slots=True)
class HostEnvironmentInfo:
    """与具体 WebUI 无关的主机环境信息。"""

    manager: ManagerEnvironmentInfo
    """管理器版本信息。"""

    operating_system: OperatingSystemEnvironmentInfo
    """操作系统信息。"""

    cpu: CpuEnvironmentInfo
    """CPU 信息。"""

    gpus: list[GpuEnvironmentInfo]
    """GPU 信息列表。"""

    pytorch: PyTorchEnvironmentInfo
    """PyTorch 兼容信息。"""

    collection_errors: list[EnvironmentCollectionError]
    """未能完成的采集项。"""
