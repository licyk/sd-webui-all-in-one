"""PyTorch 配置"""

from typing import (
    TypedDict,
    TypeAlias,
    Literal,
    get_args,
)

PYTORCH_MIRROR_DICT = {
    "other": "https://download.pytorch.org/whl",
    "cpu": "https://download.pytorch.org/whl/cpu",
    "xpu": "https://download.pytorch.org/whl/xpu",
    "rocm542": "https://download.pytorch.org/whl/rocm5.4.2",
    "rocm56": "https://download.pytorch.org/whl/rocm5.6",
    "rocm57": "https://download.pytorch.org/whl/rocm5.7",
    "rocm60": "https://download.pytorch.org/whl/rocm6.0",
    "rocm61": "https://download.pytorch.org/whl/rocm6.1",
    "rocm62": "https://download.pytorch.org/whl/rocm6.2",
    "rocm624": "https://download.pytorch.org/whl/rocm6.2.4",
    "rocm63": "https://download.pytorch.org/whl/rocm6.3",
    "rocm64": "https://download.pytorch.org/whl/rocm6.4",
    "rocm71": "https://download.pytorch.org/whl/rocm7.1",
    "cu113": "https://download.pytorch.org/whl/cu113",
    "cu117": "https://download.pytorch.org/whl/cu117",
    "cu118": "https://download.pytorch.org/whl/cu118",
    "cu121": "https://download.pytorch.org/whl/cu121",
    "cu124": "https://download.pytorch.org/whl/cu124",
    "cu126": "https://download.pytorch.org/whl/cu126",
    "cu128": "https://download.pytorch.org/whl/cu128",
    "cu129": "https://download.pytorch.org/whl/cu129",
    "cu130": "https://download.pytorch.org/whl/cu130",
}
"""PyTorch 镜像源字典"""

PYTORCH_MIRROR_NJU_DICT = {
    "other": "https://mirror.nju.edu.cn/pytorch/whl",
    "cpu": "https://mirror.nju.edu.cn/pytorch/whl/cpu",
    "xpu": "https://mirror.nju.edu.cn/pytorch/whl/xpu",
    "rocm542": "https://mirror.nju.edu.cn/pytorch/whl/rocm5.4.2",
    "rocm56": "https://mirror.nju.edu.cn/pytorch/whl/rocm5.6",
    "rocm57": "https://mirror.nju.edu.cn/pytorch/whl/rocm5.7",
    "rocm60": "https://mirror.nju.edu.cn/pytorch/whl/rocm6.0",
    "rocm61": "https://mirror.nju.edu.cn/pytorch/whl/rocm6.1",
    "rocm62": "https://mirror.nju.edu.cn/pytorch/whl/rocm6.2",
    "rocm624": "https://mirror.nju.edu.cn/pytorch/whl/rocm6.2.4",
    "rocm63": "https://mirror.nju.edu.cn/pytorch/whl/rocm6.3",
    "rocm64": "https://mirror.nju.edu.cn/pytorch/whl/rocm6.4",
    "rocm71": "https://mirror.nju.edu.cn/pytorch/whl/rocm7.1",
    "cu113": "https://mirror.nju.edu.cn/pytorch/whl/cu113",
    "cu117": "https://mirror.nju.edu.cn/pytorch/whl/cu117",
    "cu118": "https://mirror.nju.edu.cn/pytorch/whl/cu118",
    "cu121": "https://mirror.nju.edu.cn/pytorch/whl/cu121",
    "cu124": "https://mirror.nju.edu.cn/pytorch/whl/cu124",
    "cu126": "https://mirror.nju.edu.cn/pytorch/whl/cu126",
    "cu128": "https://mirror.nju.edu.cn/pytorch/whl/cu128",
    "cu129": "https://mirror.nju.edu.cn/pytorch/whl/cu129",
    "cu130": "https://mirror.nju.edu.cn/pytorch/whl/cu130",
}
"""PyTorch 国内镜像源 (NJU) 字典"""

PYPI_INDEX_MIRROR_OFFICIAL = "https://pypi.python.org/simple"
"""PyPI 主镜像源"""

PYPI_INDEX_MIRROR_TENCENT = "https://mirrors.cloud.tencent.com/pypi/simple"
"""PyPI 腾讯主镜像源"""

PYPI_EXTRA_INDEX_MIRROR_CERNET = "https://mirrors.cernet.edu.cn/pypi/web/simple"
"""PyPI 额外镜像源"""

PYTORCH_IPEX_EXTRA_INDEX_MIRROR_CN = "https://pytorch-extension.intel.com/release-whl/stable/xpu/cn"
"""PyTorch IPEX 镜像源 (CN)"""

PYTORCH_IPEX_EXTRA_INDEX_MIRROR_US = "https://pytorch-extension.intel.com/release-whl/stable/xpu/us"
"""PyTorch IPEX 镜像源 (US)"""

PYTORCH_FIND_LINKS_MIRROR_OFFICIAL = "https://download.pytorch.org/whl/torch_stable.html"
"""PyTorch 镜像源 (非 PEP 503)"""

PYTORCH_FIND_LINKS_MIRROR_ALIYUN = "https://mirrors.aliyun.com/pytorch-wheels/torch_stable.html"
"""PyTorch 阿里云镜像源 (非 PEP 503)"""

PYTORCH_FIND_LINKS_MIRROR_LICYK = "https://licyk.github.io/t/pypi/index.html"
"""PyTorch (licyk) 镜像源 (非 PEP 503)"""

PyTorchDeviceType: TypeAlias = Literal[
    "cu113",
    "cu117",
    "cu118",
    "cu121",
    "cu124",
    "cu126",
    "cu128",
    "cu129",
    "cu130",
    "rocm542",
    "rocm56",
    "rocm57",
    "rocm60",
    "rocm61",
    "rocm62",
    "rocm624",
    "rocm63",
    "rocm64",
    "rocm71",
    "xpu",
    "ipex_legacy_arc",
    "cpu",
    "directml",
    "all",
]
"""PyTorch 支持的设备类型"""

PYTORCH_DEVICE_LIST: list[str] = list(get_args(PyTorchDeviceType))
"""PyTorch 支持的设备类型列表"""

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


PYTORCH_DOWNLOAD_DICT: PyTorchVersionInfoList = [
    {
        "name": "Torch",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch torchvision torchaudio",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch + xFormers",
        "dtype": "all",
        "platform": ["win32", "linux"],
        "torch_ver": "torch torchvision torchaudio",
        "xformers_ver": "xformers",
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 1.12.1",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==1.12.1 torchvision==0.13.1 torchaudio==1.12.1",
        "xformers_ver": None,
        "index_mirror": {
            "official": [],
            "mirror": [],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [PYTORCH_FIND_LINKS_MIRROR_OFFICIAL],
            "mirror": [PYTORCH_FIND_LINKS_MIRROR_ALIYUN],
        },
    },
    {
        "name": "Torch 1.12.1 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==1.12.1+cpu torchvision==0.13.1+cpu torchaudio==1.12.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 1.12.1 (CUDA 11.3) + xFormers 0.0.14",
        "dtype": "cu113",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==1.12.1+cu113 torchvision==0.13.1+cu113 torchaudio==1.12.1+cu113",
        "xformers_ver": "xformers==0.0.14",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu113"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu113"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 1.13.1",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==1.13.1 torchvision==0.14.1 torchaudio==0.13.1",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 1.13.1 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==1.13.1+cpu torchvision==0.14.1+cpu torchaudio==0.13.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 1.13.1 (DirectML)",
        "dtype": "directml",
        "platform": ["win32"],
        "torch_ver": "torch==1.13.1 torchvision==0.14.1 torch-directml==0.1.13.1.dev230413",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 1.13.1 (CUDA 11.7) + xFormers 0.0.16",
        "dtype": "cu117",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==1.13.1+cu117 torchvision==0.14.1+cu117 torchaudio==0.13.1+cu117",
        "xformers_ver": "xformers==0.0.16",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu117"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu117"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.0.0",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.0.0 torchvision==0.15.1 torchaudio==2.0.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.0.0 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.0.0+cpu torchvision==0.15.1+cpu torchaudio==2.0.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.0.0 (DirectML)",
        "dtype": "directml",
        "platform": ["win32"],
        "torch_ver": "torch==2.0.0 torchvision==0.15.1 torch-directml==0.2.0.dev230426",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.0.0 (Intel Arc / Windows)",
        "dtype": "ipex_legacy_arc",
        "platform": ["win32"],
        "torch_ver": "torch==2.0.0a0+gite9ebda2 torchvision==0.15.2a0+fa99a53 intel_extension_for_pytorch==2.0.110+gitc6ea20b",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [PYTORCH_FIND_LINKS_MIRROR_LICYK],
            "mirror": [PYTORCH_FIND_LINKS_MIRROR_LICYK],
        },
    },
    {
        "name": "Torch 2.0.0 (Intel Arc / Linux)",
        "dtype": "ipex_legacy_arc",
        "platform": ["linux"],
        "torch_ver": "torch==2.0.1a0 torchvision==0.15.2a0 intel-extension-for-pytorch==2.0.120+xpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "extra_index_mirror": {
            "official": [PYTORCH_IPEX_EXTRA_INDEX_MIRROR_US],
            "mirror": [PYTORCH_IPEX_EXTRA_INDEX_MIRROR_CN],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.0.0 (CUDA 11.8) + xFormers 0.0.18",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.0.0+cu118 torchvision==0.15.1+cu118 torchaudio==2.0.0+cu118",
        "xformers_ver": "xformers==0.0.18",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.0.1",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.1",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.0.1 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.0.1+cpu torchvision==0.15.2+cpu torchaudio==2.0.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.0.1 (ROCm 5.4.2)",
        "dtype": "rocm542",
        "platform": ["linux"],
        "torch_ver": "torch==2.0.1+rocm5.4.2 torchvision==0.15.2+rocm5.4.2 torchaudio==2.0.1+rocm5.4.2",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm542"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm542"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.1.0",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.1.0 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.1.0+cpu torchvision==0.16.0+cpu torchaudio==2.1.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.1.0 (ROCm 5.6)",
        "dtype": "rocm56",
        "platform": ["linux"],
        "torch_ver": "torch==2.1.0+rocm5.6 torchvision==0.16.0+rocm5.6 torchaudio==2.1.0+rocm5.6",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm56"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm56"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.1.0 (Intel Core Ultra / Windows)",
        "dtype": "ipex_legacy_core_ultra",
        "platform": ["win32"],
        "torch_ver": "torch==2.1.0a0+git7bcf7da torchvision==0.16.0+fbb4cc5 torchaudio==2.1.0+6ea1133 intel_extension_for_pytorch==2.1.20+git4849f3b",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [PYTORCH_FIND_LINKS_MIRROR_LICYK],
            "mirror": [PYTORCH_FIND_LINKS_MIRROR_LICYK],
        },
    },
    {
        "name": "Torch 2.1.0 (Intel Arc / Windows)",
        "dtype": "ipex_legacy_arc",
        "platform": ["win32"],
        "torch_ver": "torch==2.1.0a0+cxx11.abi torchvision==0.16.0a0+cxx11.abi torchaudio==2.1.0a0+cxx11.abi intel_extension_for_pytorch==2.1.10+xpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [PYTORCH_FIND_LINKS_MIRROR_LICYK],
            "mirror": [PYTORCH_FIND_LINKS_MIRROR_LICYK],
        },
    },
    {
        "name": "Torch 2.1.0 (Intel Arc / Linux)",
        "dtype": "ipex_legacy_arc",
        "platform": ["linux"],
        "torch_ver": "torch==2.1.0.post0 torchvision==0.16.0.post0 torchaudio==2.1.0.post0 intel-extension-for-pytorch==2.1.20",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "extra_index_mirror": {
            "official": [PYTORCH_IPEX_EXTRA_INDEX_MIRROR_US],
            "mirror": [PYTORCH_IPEX_EXTRA_INDEX_MIRROR_CN],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.1.1",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.1.1 torchvision==0.16.1 torchaudio==2.1.1",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.1.1 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.1.1+cpu torchvision==0.16.1+cpu torchaudio==2.1.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.1.1 (ROCm 5.6)",
        "dtype": "rocm56",
        "platform": ["linux"],
        "torch_ver": "torch==2.1.1+rocm5.6 torchvision==0.16.1+rocm5.6 torchaudio==2.1.1+rocm5.6",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm56"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm56"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.1.1 (CUDA 12.1) + xFormers 0.0.23",
        "dtype": "cu121",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.1.1+cu121 torchvision==0.16.1+cu121 torchaudio==2.1.1+cu121",
        "xformers_ver": "xformers==0.0.23",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu121"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.1.1 (CUDA 11.8) + xFormers 0.0.23+cu118",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.1.1+cu118 torchvision==0.16.1+cu118 torchaudio==2.1.1+cu118",
        "xformers_ver": "xformers==0.0.23+cu118",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.1.2",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.1.2 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.1.2+cpu torchvision==0.16.2+cpu torchaudio==2.1.2+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.1.2 (ROCm 5.6)",
        "dtype": "rocm56",
        "platform": ["linux"],
        "torch_ver": "torch==2.1.2+rocm5.6 torchvision==0.16.2+rocm5.6 torchaudio==2.1.2+rocm5.6",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm56"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm56"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.1.2 (CUDA 12.1) + xFormers 0.0.23.post1",
        "dtype": "cu121",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.1.2+cu121 torchvision==0.16.2+cu121 torchaudio==2.1.2+cu121",
        "xformers_ver": "xformers==0.0.23.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu121"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.1.2 (CUDA 11.8) + xFormers 0.0.23.post1+cu118",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2+cu118",
        "xformers_ver": "xformers==0.0.23.post1+cu118",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.0",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.2.0 torchvision==0.17.0 torchaudio==2.2.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.0 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.2.0+cpu torchvision==0.17.0+cpu torchaudio==2.2.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.0 (ROCm 5.7)",
        "dtype": "rocm57",
        "platform": ["linux"],
        "torch_ver": "torch==2.2.0+rocm5.7 torchvision==0.17.0+rocm5.7 torchaudio==2.2.0+rocm5.7",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm57"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm57"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.0 (CUDA 12.1) + xFormers 0.0.24",
        "dtype": "cu121",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.2.0+cu121 torchvision==0.17.0+cu121 torchaudio==2.2.0+cu121",
        "xformers_ver": "xformers==0.0.24",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu121"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.0 (CUDA 11.8) + xFormers 0.0.24+cu118",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.2.0+cu118 torchvision==0.17.0+cu118 torchaudio==2.2.0+cu118",
        "xformers_ver": "xformers==0.0.24+cu118",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.1",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.2.1 torchvision==0.17.1 torchaudio==2.2.1",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.1 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.2.1+cpu torchvision==0.17.1+cpu torchaudio==2.2.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.1 (DirectML)",
        "dtype": "directml",
        "platform": ["win32"],
        "torch_ver": "torch==2.2.1 torchvision==0.17.1 torch-directml==0.2.1.dev240521",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.1 (ROCm 5.7)",
        "dtype": "rocm57",
        "platform": ["linux"],
        "torch_ver": "torch==2.2.1+rocm5.7 torchvision==0.17.1+rocm5.7 torchaudio==2.2.1+rocm5.7",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm57"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm57"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.1 (CUDA 12.1) + xFormers 0.0.25",
        "dtype": "cu121",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.2.1+cu121 torchvision==0.17.1+cu121 torchaudio==2.2.1+cu121",
        "xformers_ver": "xformers==0.0.25",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu121"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.1 (CUDA 11.8) + xFormers 0.0.25+cu118",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.2.1+cu118 torchvision==0.17.1+cu118 torchaudio==2.2.1+cu118",
        "xformers_ver": "xformers==0.0.25+cu118",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.2",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.2 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.2.2+cpu torchvision==0.17.2+cpu torchaudio==2.2.2+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.2 (ROCm 5.7)",
        "dtype": "rocm57",
        "platform": ["linux"],
        "torch_ver": "torch==2.2.2+rocm5.7 torchvision==0.17.2+rocm5.7 torchaudio==2.2.2+rocm5.7",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm57"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm57"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.2 (CUDA 12.1) + xFormers 0.0.25.post1",
        "dtype": "cu121",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.2.2+cu121 torchvision==0.17.2+cu121 torchaudio==2.2.2+cu121",
        "xformers_ver": "xformers==0.0.25.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu121"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.2.2 (CUDA 11.8) + xFormers 0.0.25.post1+cu118",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.2.2+cu118 torchvision==0.17.2+cu118 torchaudio==2.2.2+cu118",
        "xformers_ver": "xformers==0.0.25.post1+cu118",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.3.0",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.3.0 torchvision==0.18.0 torchaudio==2.3.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.3.0 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.3.0+cpu torchvision==0.18.0+cpu torchaudio==2.3.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.3.0 (ROCm 6.0)",
        "dtype": "rocm60",
        "platform": ["linux"],
        "torch_ver": "torch==2.3.0+rocm6.0 torchvision==0.18.0+rocm6.0 torchaudio==2.3.0+rocm6.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm60"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm60"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.3.0 (CUDA 12.1) + xFormers 0.0.26.post1",
        "dtype": "cu121",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.3.0+cu121 torchvision==0.18.0+cu121 torchaudio==2.3.0+cu121",
        "xformers_ver": "xformers==0.0.26.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu121"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.3.0 (CUDA 11.8) + xFormers 0.0.26.post1+cu118",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118",
        "xformers_ver": "xformers==0.0.26.post1+cu118",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.3.1",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.3.1 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.3.1+cpu torchvision==0.18.1+cpu torchaudio==2.3.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.3.1 (DirectML)",
        "dtype": "directml",
        "platform": ["win32"],
        "torch_ver": "torch==2.3.1 torchvision==0.18.1 torch-directml==0.2.3.dev240715",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.3.1 (ROCm 6.0)",
        "dtype": "rocm60",
        "platform": ["linux"],
        "torch_ver": "torch==2.3.1+rocm6.0 torchvision==0.18.1+rocm6.0 torchaudio==2.3.1+rocm6.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm60"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm60"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.3.1 (CUDA 12.1) + xFormers 0.0.27",
        "dtype": "cu121",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.3.1+cu121 torchvision==0.18.1+cu121 torchaudio==2.3.1+cu121",
        "xformers_ver": "xformers==0.0.27",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu121"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.3.1 (CUDA 11.8) + xFormers 0.0.27+cu118",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.3.1+cu118 torchvision==0.18.1+cu118 torchaudio==2.3.1+cu118",
        "xformers_ver": "xformers==0.0.27+cu118",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.4.0",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.4.0 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.4.0+cpu torchvision==0.19.0+cpu torchaudio==2.4.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.4.0 (ROCm 6.0)",
        "dtype": "rocm60",
        "platform": ["linux"],
        "torch_ver": "torch==2.4.0+rocm6.0 torchvision==0.19.0+rocm6.0 torchaudio==2.4.0+rocm6.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm60"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm60"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.4.0 (CUDA 12.4)",
        "dtype": "cu124",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.4.0+cu124 torchvision==0.19.0+cu124 torchaudio==2.4.0+cu124",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu124"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu124"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.4.0 (CUDA 12.1) + xFormers 0.0.27.post2",
        "dtype": "cu121",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.4.0+cu121 torchvision==0.19.0+cu121 torchaudio==2.4.0+cu121",
        "xformers_ver": "xformers==0.0.27.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu121"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.4.0 (CUDA 11.8) + xFormers 0.0.27.post2+cu118",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.4.0+cu118 torchvision==0.19.0+cu118 torchaudio==2.4.0+cu118",
        "xformers_ver": "xformers==0.0.27.post2+cu118",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.4.1",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.4.1 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.4.1+cpu torchvision==0.19.1+cpu torchaudio==2.4.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.4.1 (ROCm 6.1) + xFormers 0.0.28.post1",
        "dtype": "rocm61",
        "platform": ["linux"],
        "torch_ver": "torch==2.4.1+rocm6.1 torchvision==0.19.1+rocm6.1 torchaudio==2.4.1+rocm6.1",
        "xformers_ver": "xformers===0.0.28.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm61"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm61"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.4.1 (CUDA 12.4) + xFormers 0.0.28.post1",
        "dtype": "cu124",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.4.1+cu124 torchvision==0.19.1+cu124 torchaudio==2.4.1+cu124",
        "xformers_ver": "xformers===0.0.28.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu124"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu124"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.4.1 (CUDA 12.1) + xFormers 0.0.28.post1",
        "dtype": "cu121",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.4.1+cu121 torchvision==0.19.1+cu121 torchaudio==2.4.1+cu121",
        "xformers_ver": "xformers===0.0.28.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu121"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.4.1 (CUDA 11.8) + xFormers 0.0.28.post1",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.4.1+cu118 torchvision==0.19.1+cu118 torchaudio==2.4.1+cu118",
        "xformers_ver": "xformers===0.0.28.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.5.0",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.5.0 torchvision==0.20.0 torchaudio==2.5.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.5.0 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.5.0+cpu torchvision==0.20.0+cpu torchaudio==2.5.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.5.0 (ROCm 6.2)",
        "dtype": "rocm62",
        "platform": ["linux"],
        "torch_ver": "torch==2.5.0+rocm6.2 torchvision==0.20.0+rocm6.2 torchaudio==2.5.0+rocm6.2",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm62"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm62"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.5.0 (ROCm 6.1) + xFormers 0.0.28.post2",
        "dtype": "rocm61",
        "platform": ["linux"],
        "torch_ver": "torch==2.5.0+rocm6.1 torchvision==0.20.0+rocm6.1 torchaudio==2.5.0+rocm6.1",
        "xformers_ver": "xformers==0.0.28.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm61"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm61"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.5.0 (CUDA 12.4) + xFormers 0.0.28.post2",
        "dtype": "cu124",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.5.0+cu124 torchvision==0.20.0+cu124 torchaudio==2.5.0+cu124",
        "xformers_ver": "xformers==0.0.28.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu124"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu124"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.5.0 (CUDA 12.1) + xFormers 0.0.28.post2",
        "dtype": "cu121",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.5.0+cu121 torchvision==0.20.0+cu121 torchaudio==2.5.0+cu121",
        "xformers_ver": "xformers==0.0.28.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu121"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.5.0 (CUDA 11.8) + xFormers 0.0.28.post2",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.5.0+cu118 torchvision==0.20.0+cu118 torchaudio==2.5.0+cu118",
        "xformers_ver": "xformers==0.0.28.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.5.1",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.5.1 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.5.1+cpu torchvision==0.20.1+cpu torchaudio==2.5.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.5.1 (ROCm 6.2)",
        "dtype": "rocm62",
        "platform": ["linux"],
        "torch_ver": "torch==2.5.1+rocm6.2 torchvision==0.20.1+rocm6.2 torchaudio==2.5.1+rocm6.2",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm62"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm62"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.5.1 (ROCm 6.1) + xFormers 0.0.28.post3",
        "dtype": "rocm61",
        "platform": ["linux"],
        "torch_ver": "torch==2.5.1+rocm6.1 torchvision==0.20.1+rocm6.1 torchaudio==2.5.1+rocm6.1",
        "xformers_ver": "xformers==0.0.28.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm61"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm61"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.5.1 (CUDA 12.4) + xFormers 0.0.28.post3",
        "dtype": "cu124",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.5.1+cu124 torchvision==0.20.1+cu124 torchaudio==2.5.1+cu124",
        "xformers_ver": "xformers==0.0.28.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu124"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu124"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.5.1 (CUDA 12.1) + xFormers 0.0.28.post3",
        "dtype": "cu121",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121",
        "xformers_ver": "xformers==0.0.28.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu121"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.5.1 (CUDA 11.8) + xFormers 0.0.28.post3",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.5.1+cu118 torchvision==0.20.1+cu118 torchaudio==2.5.1+cu118",
        "xformers_ver": "xformers==0.0.28.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.6.0",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.6.0 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.6.0+cpu torchvision==0.21.0+cpu torchaudio==2.6.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.6.0 (ROCm 6.2.4) + xFormers 0.0.29.post3",
        "dtype": "rocm624",
        "platform": ["linux"],
        "torch_ver": "torch==2.6.0+rocm6.2.4 torchvision==0.21.0+rocm6.2.4 torchaudio==2.6.0+rocm6.2.4",
        "xformers_ver": "xformers==0.0.29.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm624"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm624"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.6.0 (ROCm 6.1) + xFormers 0.0.29.post3",
        "dtype": "rocm61",
        "platform": ["linux"],
        "torch_ver": "torch==2.6.0+rocm6.1 torchvision==0.21.0+rocm6.1 torchaudio==2.6.0+rocm6.1",
        "xformers_ver": "xformers==0.0.29.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm61"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm61"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.6.0 (XPU)",
        "dtype": "xpu",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.6.0+xpu torchvision==0.21.0+xpu torchaudio==2.6.0+xpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["xpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.6.0 (CUDA 12.6) + xFormers 0.0.29.post3",
        "dtype": "cu126",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.6.0+cu126 torchvision==0.21.0+cu126 torchaudio==2.6.0+cu126",
        "xformers_ver": "xformers==0.0.29.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu126"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.6.0 (CUDA 12.4) + xFormers 0.0.29.post3",
        "dtype": "cu124",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.6.0+cu124 torchvision==0.21.0+cu124 torchaudio==2.6.0+cu124",
        "xformers_ver": "xformers==0.0.29.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu124"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu124"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.6.0 (CUDA 11.8) + xFormers 0.0.29.post3",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.6.0+cu118 torchvision==0.21.0+cu118 torchaudio==2.6.0+cu118",
        "xformers_ver": "xformers==0.0.29.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.0",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.0 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.7.0+cpu torchvision==0.22.0+cpu torchaudio==2.7.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.0 (ROCm 6.3) + xFormers 0.0.30",
        "dtype": "rocm63",
        "platform": ["linux"],
        "torch_ver": "torch==2.7.0+rocm6.3 torchvision==0.22.0+rocm6.3 torchaudio==2.7.0+rocm6.3",
        "xformers_ver": "xformers==0.0.30",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm63"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm63"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.0 (ROCm 6.2.4) + xFormers 0.0.30",
        "dtype": "rocm624",
        "platform": ["linux"],
        "torch_ver": "torch==2.7.0+rocm6.2.4 torchvision==0.22.0+rocm6.2.4 torchaudio==2.7.0+rocm6.2.4",
        "xformers_ver": "xformers==0.0.30",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm624"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm624"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.0 (XPU)",
        "dtype": "xpu",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.7.0+xpu torchvision==0.22.0+xpu torchaudio==2.7.0+xpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["xpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.0 (CUDA 12.8) + xFormers 0.0.30",
        "dtype": "cu128",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.7.0+cu128 torchvision==0.22.0+cu128 torchaudio==2.7.0+cu128",
        "xformers_ver": "xformers==0.0.30",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu128"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu128"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.0 (CUDA 12.6) + xFormers 0.0.30",
        "dtype": "cu126",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.7.0+cu126 torchvision==0.22.0+cu126 torchaudio==2.7.0+cu126",
        "xformers_ver": "xformers==0.0.30",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu126"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.0 (CUDA 11.8) + xFormers 0.0.30",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.7.0+cu118 torchvision==0.22.0+cu118 torchaudio==2.7.0+cu118",
        "xformers_ver": "xformers==0.0.30",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.1",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.1 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.7.1+cpu torchvision==0.22.1+cpu torchaudio==2.7.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.1 (ROCm 6.3) + xFormers 0.0.31.post1",
        "dtype": "rocm63",
        "platform": ["linux"],
        "torch_ver": "torch==2.7.1+rocm6.3 torchvision==0.22.1+rocm6.3 torchaudio==2.7.1+rocm6.3",
        "xformers_ver": "xformers==0.0.31.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm63"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm63"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.1 (ROCm 6.2.4) + xFormers 0.0.31.post1",
        "dtype": "rocm624",
        "platform": ["linux"],
        "torch_ver": "torch==2.7.1+rocm6.2.4 torchvision==0.22.1+rocm6.2.4 torchaudio==2.7.1+rocm6.2.4",
        "xformers_ver": "xformers==0.0.31.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm624"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm624"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.1 (XPU)",
        "dtype": "xpu",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.7.1+xpu torchvision==0.22.1+xpu torchaudio==2.7.1+xpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["xpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.1 (CUDA 12.8) + xFormers 0.0.31.post1",
        "dtype": "cu128",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.7.1+cu128 torchvision==0.22.1+cu128 torchaudio==2.7.1+cu128",
        "xformers_ver": "xformers==0.0.31.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu128"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu128"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.1 (CUDA 12.6) + xFormers 0.0.31.post1",
        "dtype": "cu126",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.7.1+cu126 torchvision==0.22.1+cu126 torchaudio==2.7.1+cu126",
        "xformers_ver": "xformers==0.0.31.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu126"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.7.1 (CUDA 11.8) + xFormers 0.0.31.post1",
        "dtype": "cu118",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.7.1+cu118 torchvision==0.22.1+cu118 torchaudio==2.7.1+cu118",
        "xformers_ver": "xformers==0.0.31.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.8.0",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.8.0 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.8.0+cpu torchvision==0.23.0+cpu torchaudio==2.8.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.8.0 (ROCm 6.4) + xFormers 0.0.32.post2",
        "dtype": "rocm64",
        "platform": ["linux"],
        "torch_ver": "torch==2.8.0+rocm6.4 torchvision==0.23.0+rocm6.4 torchaudio==2.8.0+rocm6.4",
        "xformers_ver": "xformers==0.0.32.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm64"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm64"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.8.0 (ROCm 6.3)",
        "dtype": "rocm63",
        "platform": ["linux"],
        "torch_ver": "torch==2.8.0+rocm6.3 torchvision==0.23.0+rocm6.3 torchaudio==2.8.0+rocm6.3",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm63"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm63"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.8.0 (XPU)",
        "dtype": "xpu",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.8.0+xpu torchvision==0.23.0+xpu torchaudio==2.8.0+xpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["xpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.8.0 (CUDA 12.9) + xFormers 0.0.32.post2",
        "dtype": "cu129",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.8.0+cu129 torchvision==0.23.0+cu129 torchaudio==2.8.0+cu129",
        "xformers_ver": "xformers==0.0.32.post2",
        "index_mirror": {
            "official": PYTORCH_MIRROR_DICT["cu129"],
            "mirror": PYTORCH_MIRROR_NJU_DICT["cu129"],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.8.0 (CUDA 12.8) + xFormers 0.0.32.post2",
        "dtype": "cu128",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.8.0+cu128 torchvision==0.23.0+cu128 torchaudio==2.8.0+cu128",
        "xformers_ver": "xformers==0.0.32.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu128"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu128"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.8.0 (CUDA 12.6) + xFormers 0.0.32.post2",
        "dtype": "cu126",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.8.0+cu126 torchvision==0.23.0+cu126 torchaudio==2.8.0+cu126",
        "xformers_ver": "xformers==0.0.32.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu126"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.0",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.9.0 torchvision==0.24.0 torchaudio==2.9.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.0 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.9.0+cpu torchvision==0.24.0+cpu torchaudio==2.9.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.0 (ROCm 6.4) + xFormers 0.0.33",
        "dtype": "rocm64",
        "platform": ["linux"],
        "torch_ver": "torch==2.9.0+rocm6.4 torchvision==0.24.0+rocm6.4 torchaudio==2.9.0+rocm6.4",
        "xformers_ver": "xformers==0.0.33",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm64"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm64"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.0 (ROCm 6.3)",
        "dtype": "rocm63",
        "platform": ["linux"],
        "torch_ver": "torch==2.9.0+rocm6.3 torchvision==0.24.0+rocm6.3 torchaudio==2.9.0+rocm6.3",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm63"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm63"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.0 (XPU)",
        "dtype": "xpu",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.9.0+xpu torchvision==0.24.0+xpu torchaudio==2.9.0+xpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["xpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.0 (CUDA 13.0) + xFormers 0.0.33",
        "dtype": "cu130",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.9.0+cu130 torchvision==0.24.0+cu130 torchaudio==2.9.0+cu130",
        "xformers_ver": "xformers==0.0.33",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu130"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu130"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.0 (CUDA 12.8) + xFormers 0.0.33",
        "dtype": "cu128",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.9.0+cu128 torchvision==0.24.0+cu128 torchaudio==2.9.0+cu128",
        "xformers_ver": "xformers==0.0.33",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu128"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu128"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.0 (CUDA 12.6) + xFormers 0.0.33",
        "dtype": "cu126",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.9.0+cu126 torchvision==0.24.0+cu126 torchaudio==2.9.0+cu126",
        "xformers_ver": "xformers==0.0.33",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu126"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.1",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.9.1 torchvision==0.24.1 torchaudio==2.9.1",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.1 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.9.1+cpu torchvision==0.24.1+cpu torchaudio==2.9.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.1 (ROCm 6.4) + xFormers 0.0.33.post2",
        "dtype": "rocm64",
        "platform": ["linux"],
        "torch_ver": "torch==2.9.1+rocm6.4 torchvision==0.24.1+rocm6.4 torchaudio==2.9.1+rocm6.4",
        "xformers_ver": "xformers==0.0.33.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm64"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm64"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.1 (ROCm 6.3)",
        "dtype": "rocm63",
        "platform": ["linux"],
        "torch_ver": "torch==2.9.1+rocm6.3 torchvision==0.24.1+rocm6.3 torchaudio==2.9.1+rocm6.3",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm63"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm63"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.1 (XPU)",
        "dtype": "xpu",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.9.1+xpu torchvision==0.24.1+xpu torchaudio==2.9.1+xpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["xpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.1 (CUDA 13.0) + xFormers 0.0.33.post2",
        "dtype": "cu130",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.9.1+cu130 torchvision==0.24.1+cu130 torchaudio==2.9.1+cu130",
        "xformers_ver": "xformers==0.0.33.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu130"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu130"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.1 (CUDA 12.8) + xFormers 0.0.33.post2",
        "dtype": "cu128",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.9.1+cu128 torchvision==0.24.1+cu128 torchaudio==2.9.1+cu128",
        "xformers_ver": "xformers==0.0.33.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu128"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu128"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.9.1 (CUDA 12.6) + xFormers 0.0.33.post2",
        "dtype": "cu126",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.9.1+cu126 torchvision==0.24.1+cu126 torchaudio==2.9.1+cu126",
        "xformers_ver": "xformers==0.0.33.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu126"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.10.0",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.10.0 torchvision==0.25.0 torchaudio==2.10.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_CERNET],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.10.0 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.10.0+cpu torchvision==0.25.0+cpu torchaudio==2.10.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.10.0 (ROCm 7.1) + xFormers 0.0.34",
        "dtype": "rocm71",
        "platform": ["linux"],
        "torch_ver": "torch==2.10.0+rocm7.1 torchvision==0.25.0+rocm7.1 torchaudio==2.10.0+rocm7.1",
        "xformers_ver": "xformers==0.0.34",
        "index_mirror": {
            "official": PYTORCH_MIRROR_DICT["rocm71"],
            "mirror": PYTORCH_MIRROR_NJU_DICT["rocm71"],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.10.0 (XPU)",
        "dtype": "xpu",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.10.0+xpu torchvision==0.25.0+xpu torchaudio==2.10.0+xpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["xpu"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.10.0 (CUDA 13.0) + xFormers 0.0.34",
        "dtype": "cu130",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.10.0+cu130 torchvision==0.25.0+cu130 torchaudio==2.10.0+cu130",
        "xformers_ver": "xformers==0.0.34",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu130"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu130"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.10.0 (CUDA 12.8) + xFormers 0.0.34",
        "dtype": "cu128",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.10.0+cu128 torchvision==0.25.0+cu128 torchaudio==2.10.0+cu128",
        "xformers_ver": "xformers==0.0.34",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu128"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu128"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch 2.10.0 (CUDA 12.6) + xFormers 0.0.34",
        "dtype": "cu126",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.10.0+cu126 torchvision==0.25.0+cu126 torchaudio==2.10.0+cu126",
        "xformers_ver": "xformers==0.0.34",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu126"]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"]],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
]
"""PyTorch 可下载的列表"""
