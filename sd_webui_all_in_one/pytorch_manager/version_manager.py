"""版本管理"""

import sys

from sd_webui_all_in_one.ansi_color import ANSIColor
from sd_webui_all_in_one.config import SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY
from sd_webui_all_in_one.package_analyzer import (
    PyWhlVersionComparison,
    get_package_name,
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
    device_list = set(get_avaliable_pytorch_device_type())
    new_pytorch_list: PyTorchVersionInfoList = []
    current_platform = sys.platform

    for i in PYTORCH_DOWNLOAD_DICT:
        item: PyTorchVersionInfo = {**i}
        supported = False
        if current_platform in item["platform"]:
            if SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY:
                supported = True
            elif item["dtype"] in device_list:
                supported = True

        item["supported"] = supported
        new_pytorch_list.append(item)

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

    def _extract_torch_version(text: str) -> str:
        for package in text.split():
            if get_package_name(package) != "torch":
                continue
            if is_package_has_version(package):
                return get_package_version(package)
            return "0.0"

        return "0.0"

    pytorch_list = export_pytorch_list()
    pytorch_info_list = [x for x in pytorch_list if x["dtype"] == dtype]
    if not pytorch_info_list:
        raise ValueError(f"PyTorch 类型不存在: '{dtype}'")

    supported_pytorch_info_list = [x for x in pytorch_info_list if x["supported"]]
    if not supported_pytorch_info_list:
        raise ValueError(f"当前平台不支持 PyTorch 类型: '{dtype}'")

    latest_info = supported_pytorch_info_list[0]

    for info in supported_pytorch_info_list[1:]:
        current_ver = _extract_torch_version(info.get("torch_ver") or "")
        history_ver = _extract_torch_version(latest_info.get("torch_ver") or "")
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

    def _validate_index(
        index: int,
    ) -> None:
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

    raise ValueError("`pytorch_name` 和 `pytorch_index` 缺失, 需要提供其中一项才能进行 PyTorch 下载信息查找")
