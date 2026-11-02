"""版本管理"""

import copy
import sys

from sd_webui_all_in_one.ansi_color import ANSIColor
from sd_webui_all_in_one.config import SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY
from sd_webui_all_in_one.package_analyzer import (
    Requirement,
    Specifier,
    Version,
)
from sd_webui_all_in_one.pytorch_manager.gpu_detector import (
    ROCM_MULTI_ARCH_PYTORCH_TYPE_LIST,
    GPUDeviceInfo,
    get_available_pytorch_device_type,
)
from sd_webui_all_in_one.pytorch_manager.types import (
    PYTORCH_DEVICE_LIST,
    PyTorchVersionInfo,
    PyTorchDeviceType,
    PyTorchDeviceTypeCategory,
    resolve_pytorch_device_type,
)
from sd_webui_all_in_one.pytorch_manager.version_data import (
    PYTORCH_DOWNLOAD_DICT,
    PyTorchVersionInfoList,
)


def find_torch_requirement(
    text: str,
) -> Requirement | None:
    """从 PyTorch 包版本声明中查找 torch 的依赖声明

    Args:
        text (str):
            以空格分隔的 PyTorch 包版本声明, 例如 `torch==2.8.0+cu128 torchvision==0.23.0+cu128`

    Returns:
        Requirement | None:
            torch 的依赖声明, 未找到时返回 None
    """
    for package in text.split():
        requirement = Requirement.try_parse(package)
        if requirement is not None and requirement.normalized_name == "torch":
            return requirement

    return None


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
    requirement = find_torch_requirement(text)
    if requirement is None or not requirement.specifier:
        return "0.0"

    return requirement.specifier.specifiers[0].version


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


def _get_pytorch_variant_lineage(
    dtype: PyTorchDeviceType,
) -> str | None:
    """获取 PyTorch 设备类型所属的构建系列

    同一构建系列内的设备类型可以互相迁移 (例如 `cu130` -> `cu132`), 用于在检查 PyTorch 更新时跨设备类型查找更新的版本。

    - `cuda`: 全部 CUDA 类型 (`cuXXX`)
    - `rocm_multi_arch`: AMD 多架构 wheel (`rocm7` / `rocm10`)
    - `rocm`: PyTorch 官方 ROCm wheel (如 `rocm7.2`)
    - `xpu`: Intel XPU (`xpu`)
    - `cpu`: CPU (`cpu`)

    旧版 IPEX (`ipex_legacy_*`), DirectML (`directml`) 和无类型标识 (`all`) 的 PyTorch 不属于任何构建系列, 不进行跨设备类型迁移。

    Args:
        dtype (PyTorchDeviceType):
            PyTorch 设备类型

    Returns:
        str | None:
            构建系列名称, 不属于任何构建系列时返回 None
    """
    dtype = resolve_pytorch_device_type(dtype)
    if dtype in ROCM_MULTI_ARCH_PYTORCH_TYPE_LIST:
        return "rocm_multi_arch"
    if dtype.startswith("ipex") or dtype == "all":
        return None
    return _get_pytorch_device_category(dtype)


def export_pytorch_list(
    gpu_list: list[GPUDeviceInfo] | None = None,
) -> PyTorchVersionInfoList:
    """导出 PyTorch 版本列表

    Args:
        gpu_list (list[GPUDeviceInfo] | None):
            GPU 列表, 用于判断版本组合是否受当前设备支持, 为 None 时自动获取当前平台上的 GPU 列表

    Returns:
        PyTorchVersionInfoList:
            PyTorch 版本列表
    """
    device_list = set(get_available_pytorch_device_type() if gpu_list is None else get_available_pytorch_device_type(gpu_list))
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
    pytorch_list: PyTorchVersionInfoList | None = None,
) -> PyTorchVersionInfo:
    """根据 PyTorch 类型在 PyTorch 版本下载信息列表中查找适合该类型的最新版本的 PyTorch 下载信息

    Args:
        dtype (PyTorchDeviceType):
            PyTorch 支持的设备类型
        pytorch_list (PyTorchVersionInfoList | None):
            已标注设备支持情况的 PyTorch 版本列表 (`export_pytorch_list` 的结果), 为 None 时重新导出

    Returns:
        PyTorchVersionInfo:
            PyTorch 版本下载信息

    Raises:
        ValueError:
            PyTorch 支持的设备类型无效时
    """

    dtype = resolve_pytorch_device_type(dtype)
    if pytorch_list is None:
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
        if Version.parse(current_ver) > Version.parse(history_ver):
            latest_info = info

    return latest_info


def find_pytorch_update_target(
    installed_dtype: PyTorchDeviceType,
    recommended_dtype: PyTorchDeviceType | None = None,
    pytorch_list: PyTorchVersionInfoList | None = None,
) -> PyTorchVersionInfo:
    """查找当前 PyTorch 可更新到的最新版本组合

    候选的设备类型包括:
    - 已安装的设备类型 (受当前设备支持时)
    - 推荐的设备类型 (通常为自动检测到的设备类型), 仅在与已安装的设备类型属于同一构建系列时加入

    在候选的设备类型中选择 torch 版本 (忽略本地版本号) 最新的版本组合, 版本相同时保留已安装的设备类型, 避免无意义的设备类型切换。
    例如已安装 `cu130` 且 `cu130` 已停止更新时, 若当前设备推荐 `cu132`, 则返回 `cu132` 中更新的版本组合。

    推荐的设备类型应当来自 `auto_detect_available_pytorch_type`, 因为其会检查显卡驱动支持的 CUDA 版本,
    而版本列表中的 `supported` 标记对于计算能力 >= 10.0 的显卡不检查驱动版本, 不能单独用于决定跨设备类型的更新目标。

    Args:
        installed_dtype (PyTorchDeviceType):
            当前已安装的 PyTorch 设备类型
        recommended_dtype (PyTorchDeviceType | None):
            推荐的 PyTorch 设备类型, 为 None 时只在已安装的设备类型中查找
        pytorch_list (PyTorchVersionInfoList | None):
            已标注设备支持情况的 PyTorch 版本列表 (`export_pytorch_list` 的结果), 为 None 时重新导出

    Returns:
        PyTorchVersionInfo:
            可更新到的最新 PyTorch 版本下载信息

    Raises:
        ValueError:
            已安装的设备类型和推荐的设备类型中都没有受支持的版本组合时
    """
    installed_dtype = resolve_pytorch_device_type(installed_dtype)
    if pytorch_list is None:
        pytorch_list = export_pytorch_list()

    candidates: list[PyTorchVersionInfo] = []
    installed_error: ValueError | None = None
    try:
        candidates.append(find_latest_pytorch_info(installed_dtype, pytorch_list=pytorch_list))
    except ValueError as exc:
        installed_error = exc

    if recommended_dtype is not None:
        recommended_dtype = resolve_pytorch_device_type(recommended_dtype)
        lineage = _get_pytorch_variant_lineage(installed_dtype)
        if recommended_dtype != installed_dtype and lineage is not None and lineage == _get_pytorch_variant_lineage(recommended_dtype):
            try:
                candidates.append(find_latest_pytorch_info(recommended_dtype, pytorch_list=pytorch_list))
            except ValueError:
                pass

    if not candidates:
        raise installed_error or ValueError(f"当前平台不支持 PyTorch 类型: '{installed_dtype}'")

    def _public_version(info: PyTorchVersionInfo) -> Version:
        # 忽略本地版本号 (如 +cu130), 避免同一 torch 版本因设备类型不同而被视为更新
        return Version.parse(_extract_torch_version(info.get("torch_ver") or "")).without_local()

    target = candidates[0]
    for candidate in candidates[1:]:
        if _public_version(candidate) > _public_version(target):
            target = candidate

    return target


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
        return all(Specifier(op, spec_version).matches(version) for op, spec_version in torch_specs)

    def _is_better(candidate: PyTorchVersionInfo, current: PyTorchVersionInfo) -> bool:
        candidate_preferred = candidate["dtype"] == preferred_dtype
        current_preferred = current["dtype"] == preferred_dtype
        if candidate_preferred != current_preferred:
            return candidate_preferred

        # 忽略本地版本号 (如 +cu130), 使同一 torch 版本的不同设备类型组合进入后续比较
        candidate_ver = Version.parse(_extract_torch_version(candidate.get("torch_ver") or "")).without_local()
        current_ver = Version.parse(_extract_torch_version(current.get("torch_ver") or "")).without_local()
        if candidate_ver != current_ver:
            return candidate_ver > current_ver

        candidate_xformers = candidate.get("xformers_ver") is not None
        current_xformers = current.get("xformers_ver") is not None
        if candidate_xformers != current_xformers:
            return candidate_xformers

        return PYTORCH_DEVICE_LIST.index(candidate["dtype"]) > PYTORCH_DEVICE_LIST.index(current["dtype"])

    if preferred_dtype is not None:
        preferred_dtype = resolve_pytorch_device_type(preferred_dtype)

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

    例如 AMD 多架构 wheel (`rocm7` / `rocm10`) 需要通过 `torch[device-all]` 安装 GPU 设备库。

    Args:
        dtype (PyTorchDeviceType):
            PyTorch 设备类型

    Returns:
        dict[str, list[str]]:
            规范化软件包名到 extras 列表的映射, 例如 `{"torch": ["device-all"]}`
    """
    dtype = resolve_pytorch_device_type(dtype)
    package_extras: dict[str, list[str]] = {}
    for info in PYTORCH_DOWNLOAD_DICT:
        if info["dtype"] != dtype:
            continue
        for package in (info.get("torch_ver") or "").split():
            requirement = Requirement.try_parse(package)
            if requirement is None or not requirement.extras:
                continue
            merged_extras = package_extras.setdefault(requirement.normalized_name, [])
            merged_extras.extend(extra for extra in requirement.extras if extra not in merged_extras)

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

    result: list[str] = []
    for package in packages.split():
        requirement = Requirement.try_parse(package)
        if requirement is None or requirement.url is not None:
            result.append(package)
            continue
        required_extras = package_extras.get(requirement.normalized_name)
        if not required_extras:
            result.append(package)
            continue
        merged_extras = list(requirement.extras) + [extra for extra in required_extras if extra not in requirement.extras]
        result.append(f"{requirement.name}[{','.join(merged_extras)}]{requirement.specifier}")

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
    dtype = resolve_pytorch_device_type(dtype)
    return any(info["dtype"] == dtype and info.get("xformers_ver") is not None for info in PYTORCH_DOWNLOAD_DICT)
