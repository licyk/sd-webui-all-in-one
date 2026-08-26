"""主机环境信息和环境检查任务。"""

import os
import platform
import sys

from sd_webui_all_in_one.pytorch_manager import (
    get_gpu_list,
)
from sd_webui_all_in_one.env_check import check_torch_version_status
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.version import VERSION

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


from .models import (
    CpuEnvironmentInfo,
    EnvironmentCollectionError,
    EnvCheckTask,
    GpuEnvironmentInfo,
    HostEnvironmentInfo,
    ManagerEnvironmentInfo,
    OperatingSystemEnvironmentInfo,
    PyTorchEnvironmentInfo,
)


def _gpu_memory_bytes(value: object) -> int | None:
    """将 GPU 探测器返回的显存值规范化为字节数。"""
    if isinstance(value, int) and not isinstance(value, bool):
        return value if value >= 0 else None
    if isinstance(value, str):
        normalized = value.strip()
        if normalized.isdigit():
            return int(normalized)
    return None


def collect_host_environment_info() -> HostEnvironmentInfo:
    """采集与具体 WebUI 无关的主机、硬件和 PyTorch 信息。

    各个探测项按尽力而为原则执行。GPU 或 PyTorch 探测失败不会阻止
    其余环境信息导出，失败详情会写入 ``collection_errors``。

    Returns:
        HostEnvironmentInfo: 结构化主机环境信息。
    """
    errors: list[EnvironmentCollectionError] = []
    gpus: list[GpuEnvironmentInfo] = []
    try:
        for gpu in get_gpu_list():
            name = gpu.get("Name")
            if not name:
                continue
            gpus.append(
                GpuEnvironmentInfo(
                    name=name,
                    vendor=gpu.get("AdapterCompatibility"),
                    memory_bytes=_gpu_memory_bytes(gpu.get("AdapterRAM")),
                    driver_version=gpu.get("DriverVersion"),
                )
            )
    except Exception as exc:
        errors.append(EnvironmentCollectionError(component="gpu", message=str(exc)))

    try:
        torch_status = check_torch_version_status()
        pytorch = PyTorchEnvironmentInfo(
            installed_version=torch_status["installed_version"],
            installed_type=torch_status["installed_type"],
            available_types=list(torch_status["available_types"]),
            status=torch_status["status"],
            is_compatible=torch_status["is_compatible"],
            message=torch_status["message"],
        )
    except Exception as exc:
        errors.append(EnvironmentCollectionError(component="pytorch", message=str(exc)))
        pytorch = PyTorchEnvironmentInfo(
            installed_version=None,
            installed_type=None,
            available_types=[],
            status="unknown",
            is_compatible=None,
            message="PyTorch 环境信息采集失败",
        )

    machine = platform.machine() or "unknown"
    return HostEnvironmentInfo(
        manager=ManagerEnvironmentInfo(name="sd-webui-all-in-one", version=VERSION),
        operating_system=OperatingSystemEnvironmentInfo(
            platform=platform.platform(),
            system=platform.system() or sys.platform,
            release=platform.release(),
            version=platform.version(),
            machine=machine,
        ),
        cpu=CpuEnvironmentInfo(
            name=platform.processor() or machine,
            logical_cores=os.cpu_count(),
        ),
        gpus=gpus,
        pytorch=pytorch,
        collection_errors=errors,
    )


def select_env_check_tasks(
    tasks: list[EnvCheckTask],
    include_checks: list[str] | None = None,
    exclude_checks: list[str] | None = None,
) -> list[EnvCheckTask]:
    """根据包含和排除列表筛选环境检查任务。

    Args:
        tasks (list[EnvCheckTask]): 环境检查任务列表。
        include_checks (list[str] | None): 仅执行的检查任务名称。
        exclude_checks (list[str] | None): 跳过的检查任务名称。

    Returns:
        list[EnvCheckTask]: 筛选后的环境检查任务列表。

    Raises:
        ValueError: 检查任务名称未知时抛出。
    """
    task_names = {task.name for task in tasks}
    include_set = set(include_checks or [])
    exclude_set = set(exclude_checks or [])
    unknown_names = (include_set | exclude_set) - task_names
    if unknown_names:
        raise ValueError(f"未知环境检查任务: {', '.join(sorted(unknown_names))}")

    selected_tasks = tasks
    if include_set:
        selected_tasks = [task for task in selected_tasks if task.name in include_set]
    if exclude_set:
        selected_tasks = [task for task in selected_tasks if task.name not in exclude_set]
    return selected_tasks


def run_env_check_tasks(
    tasks: list[EnvCheckTask],
    *,
    include_checks: list[str] | None = None,
    exclude_checks: list[str] | None = None,
    error_message: str,
) -> None:
    """运行命名环境检查任务并聚合异常。

    Args:
        tasks (list[EnvCheckTask]): 环境检查任务列表。
        include_checks (list[str] | None): 仅执行的检查任务名称。
        exclude_checks (list[str] | None): 跳过的检查任务名称。
        error_message (str): 聚合异常消息。

    Raises:
        AggregateError: 任一检查任务失败时抛出。
        ValueError: 检查任务名称未知时抛出。
    """
    err: list[Exception] = []
    for task in select_env_check_tasks(tasks, include_checks=include_checks, exclude_checks=exclude_checks):
        try:
            task.func(**task.kwargs)
        except Exception as e:
            err.append(e)
            logger.error("执行环境检查 '%s' 时发生错误: %s", task.name, e)

    if err:
        raise AggregateError(error_message, err)
