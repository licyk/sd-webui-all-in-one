"""PyTorch / PyPI 镜像管理器"""

from sd_webui_all_in_one.pytorch_manager.types import (
    PYPI_INDEX_MIRROR_OFFICIAL,
    PYPI_INDEX_MIRROR_TENCENT,
    PYPI_EXTRA_INDEX_MIRROR_CERNET,
    PYPI_EXTRA_INDEX_MIRROR_LICYK,
    PYPI_EXTRA_INDEX_MIRROR_LICYK_HF,
    PYTORCH_IPEX_EXTRA_INDEX_MIRROR_CN,
    PYTORCH_IPEX_EXTRA_INDEX_MIRROR_US,
    PYTORCH_FIND_LINKS_MIRROR_OFFICIAL,
    PYTORCH_FIND_LINKS_MIRROR_ALIYUN,
    PyTorchMirrorKind,
    PyTorchMirrorInfo,
    PyTorchDeviceType,
    PYTORCH_DEVICE_LIST,
    PyTorchMirrorMap,
    PyTorchDeviceTypeCategory,
    PYTORCH_DEVICE_CATEGORY_LIST,
    PyTorchMirrorType,
    PyTorchVersionInfo,
    PyTorchVersionInfoList,
)
from sd_webui_all_in_one.pytorch_manager.mirror_data import (
    PYTORCH_MIRROR_DICT,
    PYTORCH_MIRROR_NJU_DICT,
    PYTORCH_ROCM_MIRROR_DICT,
)
from sd_webui_all_in_one.pytorch_manager.version_data import (
    PYTORCH_DOWNLOAD_DICT,
)
from sd_webui_all_in_one.pytorch_manager.gpu_detector import (
    GPUDeviceInfo,
    get_cuda_comp_cap,
    get_cuda_version,
    get_windows_gpu_list,
    get_lshw_gpus,
    get_nvidia_smi_gpus,
    get_lspci_gpus,
    get_linux_gpu_list,
    get_gpu_list,
    has_gpus,
    has_nvidia_gpu,
    has_intel_xpu,
    has_amd_gpu,
    get_avaliable_pytorch_device_type,
    auto_detect_avaliable_pytorch_type,
    auto_detect_pytorch_device_category,
)
from sd_webui_all_in_one.pytorch_manager.mirror_selector import (
    get_pytorch_mirror_type_cuda,
    get_pytorch_mirror_type_rocm,
    get_pytorch_mirror_type_ipex,
    get_pytorch_mirror_type_cpu,
    get_pytorch_mirror_type,
    get_env_pytorch_type,
    get_pytorch_mirror,
)
from sd_webui_all_in_one.pytorch_manager.version_manager import (
    export_pytorch_list,
    find_latest_pytorch_info,
    display_pytorch_config,
    query_pytorch_info_from_library,
)

__all__ = [
    # types.py: URL 常量
    "PYPI_INDEX_MIRROR_OFFICIAL",
    "PYPI_INDEX_MIRROR_TENCENT",
    "PYPI_EXTRA_INDEX_MIRROR_CERNET",
    "PYPI_EXTRA_INDEX_MIRROR_LICYK",
    "PYPI_EXTRA_INDEX_MIRROR_LICYK_HF",
    "PYTORCH_IPEX_EXTRA_INDEX_MIRROR_CN",
    "PYTORCH_IPEX_EXTRA_INDEX_MIRROR_US",
    "PYTORCH_FIND_LINKS_MIRROR_OFFICIAL",
    "PYTORCH_FIND_LINKS_MIRROR_ALIYUN",
    # types.py: 类型定义
    "PyTorchMirrorKind",
    "PyTorchMirrorInfo",
    "PyTorchDeviceType",
    "PYTORCH_DEVICE_LIST",
    "PyTorchMirrorMap",
    "PyTorchDeviceTypeCategory",
    "PYTORCH_DEVICE_CATEGORY_LIST",
    "PyTorchMirrorType",
    "PyTorchVersionInfo",
    "PyTorchVersionInfoList",
    # mirror_data.py: 镜像源数据
    "PYTORCH_MIRROR_DICT",
    "PYTORCH_MIRROR_NJU_DICT",
    "PYTORCH_ROCM_MIRROR_DICT",
    # version_data.py: 版本下载数据
    "PYTORCH_DOWNLOAD_DICT",
    # gpu_detector.py: 硬件检测
    "GPUDeviceInfo",
    "get_cuda_comp_cap",
    "get_cuda_version",
    "get_windows_gpu_list",
    "get_lshw_gpus",
    "get_nvidia_smi_gpus",
    "get_lspci_gpus",
    "get_linux_gpu_list",
    "get_gpu_list",
    "has_gpus",
    "has_nvidia_gpu",
    "has_intel_xpu",
    "has_amd_gpu",
    "get_avaliable_pytorch_device_type",
    "auto_detect_avaliable_pytorch_type",
    "auto_detect_pytorch_device_category",
    # mirror_selector.py: 镜像选择逻辑
    "get_pytorch_mirror_type_cuda",
    "get_pytorch_mirror_type_rocm",
    "get_pytorch_mirror_type_ipex",
    "get_pytorch_mirror_type_cpu",
    "get_pytorch_mirror_type",
    "get_env_pytorch_type",
    "get_pytorch_mirror",
    # version_manager.py: 版本管理
    "export_pytorch_list",
    "find_latest_pytorch_info",
    "display_pytorch_config",
    "query_pytorch_info_from_library",
]
