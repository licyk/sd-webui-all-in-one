"""版本管理"""

import sys
import re

from sd_webui_all_in_one.ansi_color import ANSIColor
from sd_webui_all_in_one.config import SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY
from sd_webui_all_in_one.package_analyzer import (
    PyWhlVersionComparison,
    get_package_version,
    is_package_has_version,
)
from sd_webui_all_in_one.pytorch_manager.gpu_detector import get_avaliable_pytorch_device_type
from sd_webui_all_in_one.pytorch_manager.types import (
    PyTorchVersionInfo,
    PyTorchDeviceType,
)
from sd_webui_all_in_one.pytorch_manager.version_data import (
    PYTORCH_DOWNLOAD_DICT,
    PyTorchVersionInfoList,
)


def export_pytorch_list() -> PyTorchVersionInfoList:
    """导出 PyTorch 版本列表

    Returns:
        PyTorchVersionInfoList:
            PyTorch 版本列表
    """
    pytorch_list = PYTORCH_DOWNLOAD_DICT.copy()
    device_list = set(get_avaliable_pytorch_device_type())
    new_pytorch_list: PyTorchVersionInfoList = []
    current_platform = sys.platform

    for i in pytorch_list:
        supported = False
        if current_platform in i["platform"]:
            if SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY:
                supported = True
            elif i["dtype"] in device_list:
                supported = True

        i["supported"] = supported
        new_pytorch_list.append(i)

    return new_pytorch_list


def find_latest_pytorch_info(
    dtype: PyTorchDeviceType,
) -> PyTorchVersionInfo:
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

    def _extract_torch(text: str) -> str | None:
        pattern = r"\btorch(?:==[0-9.]+)?\b"
        match = re.search(pattern, text)
        return match.group(0) if match else None

    pytorch_list = export_pytorch_list()
    pytorch_info_list = [x for x in pytorch_list if x["dtype"] == dtype]
    if not pytorch_info_list:
        raise ValueError(f"PyTorch 类型不存在: '{dtype}'")

    latest_info = pytorch_info_list[0]

    for info in pytorch_info_list:
        if not info["supported"]:
            continue
        current_torch = _extract_torch(info["torch_ver"])
        history_torch = _extract_torch(latest_info["torch_ver"])
        current_ver = get_package_version(current_torch) if current_torch is not None and is_package_has_version(current_torch) else "0.0"
        history_ver = get_package_version(history_torch) if history_torch is not None and is_package_has_version(history_torch) else "0.0"
        if PyWhlVersionComparison(current_ver) > PyWhlVersionComparison(history_ver):
            latest_info = info

    return latest_info


def display_pytorch_config(
    pytorch_list: PyTorchVersionInfoList,
) -> None:
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
