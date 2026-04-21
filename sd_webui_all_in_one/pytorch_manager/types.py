"""PyTorch 镜像源类型与定义"""

from typing import (
    Literal,
    TypeAlias,
    TypedDict,
    get_args,
)


PYPI_INDEX_MIRROR_OFFICIAL = "https://pypi.python.org/simple"
"""PyPI 主镜像源"""

PYPI_INDEX_MIRROR_TENCENT = "https://mirrors.cloud.tencent.com/pypi/simple"
"""PyPI 腾讯主镜像源"""

PYPI_EXTRA_INDEX_MIRROR_CERNET = "https://mirrors.cernet.edu.cn/pypi/web/simple"
"""PyPI 额外镜像源"""

PYPI_EXTRA_INDEX_MIRROR_LICYK = "https://licyk.github.io/wheels/pypi"
"""PyPI (licyk) 镜像源"""

PYPI_EXTRA_INDEX_MIRROR_LICYK_HF = "https://licyk.github.io/wheels/pypi_hf"
"""PyPI (licyk HuggingFace) 镜像源"""

PYTORCH_IPEX_EXTRA_INDEX_MIRROR_CN = "https://pytorch-extension.intel.com/release-whl/stable/xpu/cn"
"""PyTorch IPEX 镜像源 (CN)"""

PYTORCH_IPEX_EXTRA_INDEX_MIRROR_US = "https://pytorch-extension.intel.com/release-whl/stable/xpu/us"
"""PyTorch IPEX 镜像源 (US)"""

PYTORCH_FIND_LINKS_MIRROR_OFFICIAL = "https://download.pytorch.org/whl/torch_stable.html"
"""PyTorch 镜像源 (非 PEP 503)"""

PYTORCH_FIND_LINKS_MIRROR_ALIYUN = "https://mirrors.aliyun.com/pytorch-wheels/torch_stable.html"
"""PyTorch 阿里云镜像源 (非 PEP 503)"""

PyTorchMirrorKind: TypeAlias = Literal[
    "index_url",
    "extra_index_url",
    "find_links",
]
"""PyTorch 镜像源地址类型 PyTorchMirrorKind"""

PyTorchMirrorInfo = tuple[str, PyTorchMirrorKind]
"""PyTorch 镜像源地址信息"""

PyTorchDeviceType: TypeAlias = Literal[
    "cu75",
    "cu80",
    "cu90",
    "cu91",
    "cu92",
    "cu100",
    "cu101",
    "cu102",
    "cu110",
    "cu111",
    "cu113",
    "cu115",
    "cu116",
    "cu117",
    "cu118",
    "cu121",
    "cu124",
    "cu126",
    "cu128",
    "cu129",
    "cu130",
    "rocm3.7",
    "rocm3.8",
    "rocm3.10",
    "rocm4.0.1",
    "rocm4.1",
    "rocm4.2",
    "rocm4.3.1",
    "rocm4.5.2",
    "rocm5.0",
    "rocm5.1.1",
    "rocm5.2",
    "rocm5.3",
    "rocm5.4.2",
    "rocm5.6",
    "rocm5.7",
    "rocm6.0",
    "rocm6.1",
    "rocm6.2",
    "rocm6.2.4",
    "rocm6.3",
    "rocm6.4",
    "rocm7.1",
    "rocm_rdna3",
    "rocm_rdna3.5",
    "rocm_rdna4",
    "rocm_win",
    "xpu",
    "ipex_legacy_arc",
    "cpu",
    "directml",
    "all",
]
"""PyTorch 支持的设备类型"""

PYTORCH_DEVICE_LIST: list[str] = list(get_args(PyTorchDeviceType))
"""PyTorch 支持的设备类型列表"""

PyTorchMirrorMap = dict[PyTorchDeviceType, PyTorchMirrorInfo]
"""
PyTorch 镜像配置映射表类型

用于存储不同硬件环境对应的安装源信息:
- key: 具体的设备版本标识符
- value: 包含两个元素的元组:
    1. str: PyTorch 官方或镜像站的 Wheel 仓库地址
    2. PyTorchMirrorKind: 对应的 Pip 安装指令类型 ("index_url" | "extra_index_url" | "find_links")
"""

PyTorchDeviceTypeCategory: TypeAlias = Literal["cuda", "rocm", "xpu", "mps", "cpu"]
"""PyTorch 支持的设备类型 (不带版本号)"""

PYTORCH_DEVICE_CATEGORY_LIST: list[str] = list(get_args(PyTorchDeviceTypeCategory))
"""PyTorch 支持的设备类型列表 (不带版本号)"""


class PyTorchMirrorType(TypedDict, total=False):
    """PyTorch 镜像源类型"""

    official: list[str] | None
    """官方镜像源列表, 如果为 [] 则需要将对应的 PyPI 镜像源配置进行清空; 为 None 时则不进行任何配置操作"""

    mirror: list[str] | None
    """国内镜像源列表, 如果为 [] 则需要将对应的 PyPI 镜像源配置进行清空; 为 None 时则不进行任何配置操作"""


class PyTorchVersionInfo(TypedDict, total=False):
    """PyTorch 版本下载信息"""

    name: str
    """版本组合名称"""

    dtype: PyTorchDeviceType
    """适配推理设备的类型"""

    platform: list[Literal["win32", "linux", "darwin"]]
    """支持的系统平台"""

    supported: bool | None
    """是否支持当前平台"""

    torch_ver: str | None
    """PyTorch 包版本信息"""

    xformers_ver: str | None
    """xFormers 包版本信息"""

    index_mirror: PyTorchMirrorType
    """PyPI 主镜像源"""

    extra_index_mirror: PyTorchMirrorType
    """PyPI 额外镜像源"""

    find_links: PyTorchMirrorType
    """PyPI 额外镜像源 (非 PEP 503)"""


PyTorchVersionInfoList = list[PyTorchVersionInfo]
"""PyTorch 版本下载信息列表"""
