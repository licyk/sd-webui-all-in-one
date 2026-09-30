"""版本管理"""

import copy
import sys

from sd_webui_all_in_one.ansi_color import ANSIColor
from sd_webui_all_in_one.config import SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY
from sd_webui_all_in_one.package_analyzer import (
    PyWhlVersionComparison,
    check_version_constraint,
    get_package_name,
    get_parse_bindings,
    normalize_package_name,
    parse_requirement,
    get_package_version,
    is_package_has_version,
)
from sd_webui_all_in_one.pytorch_manager.gpu_detector import get_available_pytorch_device_type
from sd_webui_all_in_one.pytorch_manager.types import (
    PYTORCH_DEVICE_LIST,
    PyTorchVersionInfo,
    PyTorchDeviceType,
    PyTorchDeviceTypeCategory,
)
from sd_webui_all_in_one.pytorch_manager.version_data import (
    PYTORCH_DOWNLOAD_DICT,
    PyTorchVersionInfoList,
)


def _extract_torch_version(
    text: str,
) -> str:
    """从 PyTorch 包版本声明中提取 torch 的版本号

    Args:
        text (str):
            PyTorch 包版本声明, 例如 `torch==2.8.0+cu128 torchvision==0.23.0+cu128`

    Returns:
        str:
            torch 版本号, 未声明版本时返回 `0.0`
    """
    for package in text.split():
        if get_package_name(package) != "torch":
            continue
        if is_package_has_version(package):
            return get_package_version(package)
        return "0.0"

    return "0.0"


def _get_pytorch_device_category(
    dtype: PyTorchDeviceType,
) -> PyTorchDeviceTypeCategory | None:
    """获取 PyTorch 设备类型对应的设备分类

    Args:
        dtype (PyTorchDeviceType):
            PyTorch 设备类型

    Returns:
        PyTorchDeviceTypeCategory | None:
            设备分类, 无法归类的类型 (如 `directml`) 返回 None
    """
    if dtype.startswith("cu"):
        return "cuda"
    if dtype.startswith("rocm"):
        return "rocm"
    if dtype == "xpu" or dtype.startswith("ipex"):
        return "xpu"
    if dtype == "cpu":
        return "cpu"
    if dtype == "all" and sys.platform == "darwin":
        return "mps"
    return None


def export_pytorch_list() -> PyTorchVersionInfoList:
    """导出 PyTorch 版本列表

    Returns:
        PyTorchVersionInfoList:
            PyTorch 版本列表
    """
    device_list = set(get_available_pytorch_device_type())
    new_pytorch_list: PyTorchVersionInfoList = []
    current_platform = sys.platform

    for i in PYTORCH_DOWNLOAD_DICT:
        item: PyTorchVersionInfo = copy.deepcopy(i)
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
                return copy.deepcopy(m)

        raise FileNotFoundError(f"未找到指定的 PyTorch 版本组合名称: {name}")

    pytorch_list = PYTORCH_DOWNLOAD_DICT
    if pytorch_name is None and pytorch_index is None:
        raise ValueError("`pytorch_name` 和 `pytorch_index` 缺失, 需要提供其中一项才能进行 PyTorch 下载信息查找")

    if pytorch_index is not None:
        _validate_index(pytorch_index)
        return copy.deepcopy(pytorch_list[pytorch_index - 1])
    elif pytorch_name is not None:
        return _get_pytorch_with_name(pytorch_name)

    raise ValueError("`pytorch_name` 和 `pytorch_index` 缺失, 需要提供其中一项才能进行 PyTorch 下载信息查找")


def find_pytorch_info_for_torch_requirement(
    device_category: PyTorchDeviceTypeCategory,
    torch_specs: list[tuple[str, str]],
    preferred_dtype: PyTorchDeviceType | None = None,
) -> PyTorchVersionInfo | None:
    """在 PyTorch 版本表中查找满足 torch 版本约束且支持当前设备的最佳版本组合

    候选条目需要同时满足:
    - 设备类型属于指定的设备分类
    - 在当前平台和设备上受支持
    - 固定的 torch 版本满足全部版本约束

    候选条目的优先级依次为:
    1. 设备类型为首选类型 (通常为自动检测到的设备类型)
    2. torch 版本更新
    3. 包含 xFormers
    4. 设备类型在 PYTORCH_DEVICE_LIST 中的位置更靠后 (如更新的 CUDA 版本)

    Args:
        device_category (PyTorchDeviceTypeCategory):
            设备分类
        torch_specs (list[tuple[str, str]]):
            torch 版本约束列表, 例如 `[("<", "3.0"), (">=", "2.7.0")]`
        preferred_dtype (PyTorchDeviceType | None):
            首选的 PyTorch 设备类型

    Returns:
        PyTorchVersionInfo | None:
            最佳的 PyTorch 版本下载信息, 没有满足条件的条目时返回 None
    """

    def _satisfies(version: str) -> bool:
        comparison = PyWhlVersionComparison(version)
        return all(check_version_constraint(version, op, spec_version, comparison) for op, spec_version in torch_specs)

    def _is_better(candidate: PyTorchVersionInfo, current: PyTorchVersionInfo) -> bool:
        candidate_preferred = candidate["dtype"] == preferred_dtype
        current_preferred = current["dtype"] == preferred_dtype
        if candidate_preferred != current_preferred:
            return candidate_preferred

        # 忽略本地版本号 (如 +cu130), 使同一 torch 版本的不同设备类型组合进入后续比较
        candidate_ver = PyWhlVersionComparison(_extract_torch_version(candidate.get("torch_ver") or "").split("+")[0])
        current_ver = PyWhlVersionComparison(_extract_torch_version(current.get("torch_ver") or "").split("+")[0])
        if candidate_ver != current_ver:
            return candidate_ver > current_ver

        candidate_xformers = candidate.get("xformers_ver") is not None
        current_xformers = current.get("xformers_ver") is not None
        if candidate_xformers != current_xformers:
            return candidate_xformers

        return PYTORCH_DEVICE_LIST.index(candidate["dtype"]) > PYTORCH_DEVICE_LIST.index(current["dtype"])

    best: PyTorchVersionInfo | None = None
    for info in export_pytorch_list():
        if not info["supported"] or _get_pytorch_device_category(info["dtype"]) != device_category:
            continue
        torch_ver = _extract_torch_version(info.get("torch_ver") or "")
        if torch_ver == "0.0" or not _satisfies(torch_ver):
            continue
        if best is None or _is_better(info, best):
            best = info

    return best


def get_pytorch_package_extras(
    dtype: PyTorchDeviceType,
) -> dict[str, list[str]]:
    """从 PyTorch 版本表中获取指定设备类型的 PyTorch 软件包所需的 extras

    例如 AMD 多架构 wheel (`rocm_win` / `rocm_linux`) 需要通过 `torch[device-all]` 安装 GPU 设备库。

    Args:
        dtype (PyTorchDeviceType):
            PyTorch 设备类型

    Returns:
        dict[str, list[str]]:
            规范化软件包名到 extras 列表的映射, 例如 `{"torch": ["device-all"]}`
    """
    bindings = get_parse_bindings()
    package_extras: dict[str, list[str]] = {}
    for info in PYTORCH_DOWNLOAD_DICT:
        if info["dtype"] != dtype:
            continue
        for package in (info.get("torch_ver") or "").split():
            try:
                name, extras, _, _ = parse_requirement(package, bindings)
            except ValueError:
                continue
            if not extras:
                continue
            merged_extras = package_extras.setdefault(normalize_package_name(name), [])
            merged_extras.extend(extra for extra in extras if extra not in merged_extras)

    return package_extras


def add_pytorch_package_extras(
    packages: str,
    dtype: PyTorchDeviceType,
) -> str:
    """根据 PyTorch 版本表为 PyTorch 软件包声明补充该设备类型所需的 extras

    Args:
        packages (str):
            以空格分隔的软件包声明, 例如 `torch<3.0,>=2.7.0 torchvision`
        dtype (PyTorchDeviceType):
            PyTorch 设备类型

    Returns:
        str:
            补充 extras 后的软件包声明, 例如 `torch[device-all]<3.0,>=2.7.0 torchvision[device-all]`
    """
    package_extras = get_pytorch_package_extras(dtype)
    if not package_extras:
        return packages

    bindings = get_parse_bindings()
    result: list[str] = []
    for package in packages.split():
        try:
            name, extras, version_specs, _ = parse_requirement(package, bindings)
        except ValueError:
            result.append(package)
            continue
        required_extras = package_extras.get(normalize_package_name(name))
        if not required_extras or isinstance(version_specs, str):
            result.append(package)
            continue
        merged_extras = list(extras) + [extra for extra in required_extras if extra not in extras]
        result.append(f"{name}[{','.join(merged_extras)}]{','.join(f'{op}{ver}' for op, ver in version_specs)}")

    return " ".join(result)


def has_pytorch_xformers_support(
    dtype: PyTorchDeviceType,
) -> bool:
    """根据 PyTorch 版本表判断指定设备类型是否有可用的 xFormers 版本组合

    Args:
        dtype (PyTorchDeviceType):
            PyTorch 设备类型

    Returns:
        bool:
            版本表中存在该设备类型且包含 xFormers 的版本组合时返回 True
    """
    return any(info["dtype"] == dtype and info.get("xformers_ver") is not None for info in PYTORCH_DOWNLOAD_DICT)
