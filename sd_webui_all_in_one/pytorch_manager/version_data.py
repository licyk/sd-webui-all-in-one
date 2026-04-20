"""PyTorch 版本数据"""

from sd_webui_all_in_one.pytorch_manager.mirror_data import (
    PYTORCH_MIRROR_DICT,
    PYTORCH_MIRROR_NJU_DICT,
    PYTORCH_ROCM_MIRROR_DICT,
)
from sd_webui_all_in_one.pytorch_manager.types import (
    PYPI_EXTRA_INDEX_MIRROR_CERNET,
    PYPI_EXTRA_INDEX_MIRROR_LICYK,
    PYPI_EXTRA_INDEX_MIRROR_LICYK_HF,
    PYPI_INDEX_MIRROR_OFFICIAL,
    PYPI_INDEX_MIRROR_TENCENT,
    PYTORCH_FIND_LINKS_MIRROR_ALIYUN,
    PYTORCH_FIND_LINKS_MIRROR_OFFICIAL,
    PYTORCH_IPEX_EXTRA_INDEX_MIRROR_CN,
    PYTORCH_IPEX_EXTRA_INDEX_MIRROR_US,
    PyTorchVersionInfoList,
)


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
        "name": "Torch ROCm (RDNA3)",
        "dtype": "rocm_rdna3",
        "platform": ["linux"],
        "torch_ver": "torch torchvision torchaudio rocm rocm-sdk-core rocm-sdk-devel",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_ROCM_MIRROR_DICT["rocm_rdna3"][0]],
            "mirror": [PYTORCH_ROCM_MIRROR_DICT["rocm_rdna3"][0]],
        },
        "extra_index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch ROCm (RDNA3.5)",
        "dtype": "rocm_rdna3.5",
        "platform": ["linux"],
        "torch_ver": "torch torchvision torchaudio rocm rocm-sdk-core rocm-sdk-devel",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_ROCM_MIRROR_DICT["rocm_rdna3.5"][0]],
            "mirror": [PYTORCH_ROCM_MIRROR_DICT["rocm_rdna3.5"][0]],
        },
        "extra_index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch ROCm (RDNA4)",
        "dtype": "rocm_rdna4",
        "platform": ["linux"],
        "torch_ver": "torch torchvision torchaudio rocm rocm-sdk-core rocm-sdk-devel",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_ROCM_MIRROR_DICT["rocm_rdna4"][0]],
            "mirror": [PYTORCH_ROCM_MIRROR_DICT["rocm_rdna4"][0]],
        },
        "extra_index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "find_links": {
            "official": [],
            "mirror": [],
        },
    },
    {
        "name": "Torch ROCm (Windows)",
        "dtype": "rocm_win",
        "platform": ["win32"],
        "torch_ver": "torch torchvision torchaudio rocm rocm-sdk-core rocm-sdk-devel rocm-sdk-libraries-custom",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [PYTORCH_ROCM_MIRROR_DICT["rocm_win"][0]],
            "mirror": [PYTORCH_ROCM_MIRROR_DICT["rocm_win"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==1.12.1+cpu torchvision==0.13.1+cpu torchaudio==1.12.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu113"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu113"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==1.13.1+cpu torchvision==0.14.1+cpu torchaudio==0.13.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu117"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu117"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.0.0+cpu torchvision==0.15.1+cpu torchaudio==2.0.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
            "official": [PYPI_EXTRA_INDEX_MIRROR_LICYK_HF],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_LICYK],
        },
        "find_links": {
            "official": [],
            "mirror": [],
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
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.0.1+cpu torchvision==0.15.2+cpu torchaudio==2.0.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm5.4.2",
        "platform": ["linux"],
        "torch_ver": "torch==2.0.1+rocm5.4.2 torchvision==0.15.2+rocm5.4.2 torchaudio==2.0.1+rocm5.4.2",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm5.4.2"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm5.4.2"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.1.0+cpu torchvision==0.16.0+cpu torchaudio==2.1.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm5.6",
        "platform": ["linux"],
        "torch_ver": "torch==2.1.0+rocm5.6 torchvision==0.16.0+rocm5.6 torchaudio==2.1.0+rocm5.6",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm5.6"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm5.6"][0]],
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
            "official": [PYPI_EXTRA_INDEX_MIRROR_LICYK_HF],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_LICYK],
        },
        "find_links": {
            "official": [],
            "mirror": [],
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
            "official": [PYPI_EXTRA_INDEX_MIRROR_LICYK_HF],
            "mirror": [PYPI_EXTRA_INDEX_MIRROR_LICYK],
        },
        "find_links": {
            "official": [],
            "mirror": [],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.1.1+cpu torchvision==0.16.1+cpu torchaudio==2.1.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm5.6",
        "platform": ["linux"],
        "torch_ver": "torch==2.1.1+rocm5.6 torchvision==0.16.1+rocm5.6 torchaudio==2.1.1+rocm5.6",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm5.6"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm5.6"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu121"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.1.2+cpu torchvision==0.16.2+cpu torchaudio==2.1.2+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm5.6",
        "platform": ["linux"],
        "torch_ver": "torch==2.1.2+rocm5.6 torchvision==0.16.2+rocm5.6 torchaudio==2.1.2+rocm5.6",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm5.6"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm5.6"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu121"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.2.0+cpu torchvision==0.17.0+cpu torchaudio==2.2.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm5.7",
        "platform": ["linux"],
        "torch_ver": "torch==2.2.0+rocm5.7 torchvision==0.17.0+rocm5.7 torchaudio==2.2.0+rocm5.7",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm5.7"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm5.7"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu121"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.2.1+cpu torchvision==0.17.1+cpu torchaudio==2.2.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm5.7",
        "platform": ["linux"],
        "torch_ver": "torch==2.2.1+rocm5.7 torchvision==0.17.1+rocm5.7 torchaudio==2.2.1+rocm5.7",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm5.7"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm5.7"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu121"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.2.2+cpu torchvision==0.17.2+cpu torchaudio==2.2.2+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm5.7",
        "platform": ["linux"],
        "torch_ver": "torch==2.2.2+rocm5.7 torchvision==0.17.2+rocm5.7 torchaudio==2.2.2+rocm5.7",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm5.7"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm5.7"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu121"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.3.0+cpu torchvision==0.18.0+cpu torchaudio==2.3.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm6.0",
        "platform": ["linux"],
        "torch_ver": "torch==2.3.0+rocm6.0 torchvision==0.18.0+rocm6.0 torchaudio==2.3.0+rocm6.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.0"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.0"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu121"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.3.1+cpu torchvision==0.18.1+cpu torchaudio==2.3.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm6.0",
        "platform": ["linux"],
        "torch_ver": "torch==2.3.1+rocm6.0 torchvision==0.18.1+rocm6.0 torchaudio==2.3.1+rocm6.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.0"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.0"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu121"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.4.0+cpu torchvision==0.19.0+cpu torchaudio==2.4.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm6.0",
        "platform": ["linux"],
        "torch_ver": "torch==2.4.0+rocm6.0 torchvision==0.19.0+rocm6.0 torchaudio==2.4.0+rocm6.0",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.0"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.0"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu121"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu124"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu124"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.4.1+cpu torchvision==0.19.1+cpu torchaudio==2.4.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm6.1",
        "platform": ["linux"],
        "torch_ver": "torch==2.4.1+rocm6.1 torchvision==0.19.1+rocm6.1 torchaudio==2.4.1+rocm6.1",
        "xformers_ver": "xformers===0.0.28.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.1"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.1"][0]],
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
        "platform": ["linux"],
        "torch_ver": "torch==2.4.1+cu118 torchvision==0.19.1+cu118 torchaudio==2.4.1+cu118",
        "xformers_ver": "xformers===0.0.28.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
        "platform": ["linux"],
        "torch_ver": "torch==2.4.1+cu121 torchvision==0.19.1+cu121 torchaudio==2.4.1+cu121",
        "xformers_ver": "xformers===0.0.28.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu121"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu124"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu124"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.5.0+cpu torchvision==0.20.0+cpu torchaudio==2.5.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm6.1",
        "platform": ["linux"],
        "torch_ver": "torch==2.5.0+rocm6.1 torchvision==0.20.0+rocm6.1 torchaudio==2.5.0+rocm6.1",
        "xformers_ver": "xformers==0.0.28.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.1"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.1"][0]],
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
        "dtype": "rocm6.2",
        "platform": ["linux"],
        "torch_ver": "torch==2.5.0+rocm6.2 torchvision==0.20.0+rocm6.2 torchaudio==2.5.0+rocm6.2",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.2"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.2"][0]],
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
        "platform": ["linux"],
        "torch_ver": "torch==2.5.0+cu118 torchvision==0.20.0+cu118 torchaudio==2.5.0+cu118",
        "xformers_ver": "xformers==0.0.28.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
        "platform": ["linux"],
        "torch_ver": "torch==2.5.0+cu121 torchvision==0.20.0+cu121 torchaudio==2.5.0+cu121",
        "xformers_ver": "xformers==0.0.28.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu121"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu124"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu124"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.5.1+cpu torchvision==0.20.1+cpu torchaudio==2.5.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm6.1",
        "platform": ["linux"],
        "torch_ver": "torch==2.5.1+rocm6.1 torchvision==0.20.1+rocm6.1 torchaudio==2.5.1+rocm6.1",
        "xformers_ver": "xformers==0.0.28.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.1"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.1"][0]],
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
        "dtype": "rocm6.2",
        "platform": ["linux"],
        "torch_ver": "torch==2.5.1+rocm6.2 torchvision==0.20.1+rocm6.2 torchaudio==2.5.1+rocm6.2",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.2"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.2"][0]],
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
        "platform": ["linux"],
        "torch_ver": "torch==2.5.1+cu118 torchvision==0.20.1+cu118 torchaudio==2.5.1+cu118",
        "xformers_ver": "xformers==0.0.28.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
        "platform": ["linux"],
        "torch_ver": "torch==2.5.1+cu121 torchvision==0.20.1+cu121 torchaudio==2.5.1+cu121",
        "xformers_ver": "xformers==0.0.28.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu121"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu121"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu124"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu124"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.6.0+cpu torchvision==0.21.0+cpu torchaudio==2.6.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm6.1",
        "platform": ["linux"],
        "torch_ver": "torch==2.6.0+rocm6.1 torchvision==0.21.0+rocm6.1 torchaudio==2.6.0+rocm6.1",
        "xformers_ver": "xformers==0.0.29.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.1"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.1"][0]],
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
        "dtype": "rocm6.2.4",
        "platform": ["linux"],
        "torch_ver": "torch==2.6.0+rocm6.2.4 torchvision==0.21.0+rocm6.2.4 torchaudio==2.6.0+rocm6.2.4",
        "xformers_ver": "xformers==0.0.29.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.2.4"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.2.4"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["xpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"][0]],
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
        "platform": ["linux"],
        "torch_ver": "torch==2.6.0+cu118 torchvision==0.21.0+cu118 torchaudio==2.6.0+cu118",
        "xformers_ver": "xformers==0.0.29.post3",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu124"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu124"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu126"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.7.0+cpu torchvision==0.22.0+cpu torchaudio==2.7.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm6.2.4",
        "platform": ["linux"],
        "torch_ver": "torch==2.7.0+rocm6.2.4 torchvision==0.22.0+rocm6.2.4 torchaudio==2.7.0+rocm6.2.4",
        "xformers_ver": "xformers==0.0.30",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.2.4"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.2.4"][0]],
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
        "dtype": "rocm6.3",
        "platform": ["linux"],
        "torch_ver": "torch==2.7.0+rocm6.3 torchvision==0.22.0+rocm6.3 torchaudio==2.7.0+rocm6.3",
        "xformers_ver": "xformers==0.0.30",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.3"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.3"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["xpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"][0]],
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
        "platform": ["linux"],
        "torch_ver": "torch==2.7.0+cu118 torchvision==0.22.0+cu118 torchaudio==2.7.0+cu118",
        "xformers_ver": "xformers==0.0.30",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu126"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu128"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu128"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.7.1+cpu torchvision==0.22.1+cpu torchaudio==2.7.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm6.2.4",
        "platform": ["linux"],
        "torch_ver": "torch==2.7.1+rocm6.2.4 torchvision==0.22.1+rocm6.2.4 torchaudio==2.7.1+rocm6.2.4",
        "xformers_ver": "xformers==0.0.31.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.2.4"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.2.4"][0]],
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
        "dtype": "rocm6.3",
        "platform": ["linux"],
        "torch_ver": "torch==2.7.1+rocm6.3 torchvision==0.22.1+rocm6.3 torchaudio==2.7.1+rocm6.3",
        "xformers_ver": "xformers==0.0.31.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.3"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.3"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["xpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"][0]],
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
        "platform": ["linux"],
        "torch_ver": "torch==2.7.1+cu118 torchvision==0.22.1+cu118 torchaudio==2.7.1+cu118",
        "xformers_ver": "xformers==0.0.31.post1",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu118"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu118"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu126"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu128"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu128"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.8.0+cpu torchvision==0.23.0+cpu torchaudio==2.8.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm6.3",
        "platform": ["linux"],
        "torch_ver": "torch==2.8.0+rocm6.3 torchvision==0.23.0+rocm6.3 torchaudio==2.8.0+rocm6.3",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.3"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.3"][0]],
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
        "dtype": "rocm6.4",
        "platform": ["linux"],
        "torch_ver": "torch==2.8.0+rocm6.4 torchvision==0.23.0+rocm6.4 torchaudio==2.8.0+rocm6.4",
        "xformers_ver": "xformers==0.0.32.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.4"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.4"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["xpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu126"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu128"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu128"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu129"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu129"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.9.0+cpu torchvision==0.24.0+cpu torchaudio==2.9.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm6.3",
        "platform": ["linux"],
        "torch_ver": "torch==2.9.0+rocm6.3 torchvision==0.24.0+rocm6.3 torchaudio==2.9.0+rocm6.3",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.3"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.3"][0]],
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
        "dtype": "rocm6.4",
        "platform": ["linux"],
        "torch_ver": "torch==2.9.0+rocm6.4 torchvision==0.24.0+rocm6.4 torchaudio==2.9.0+rocm6.4",
        "xformers_ver": "xformers==0.0.33",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.4"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.4"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["xpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu126"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu128"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu128"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu130"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu130"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.9.1+cpu torchvision==0.24.1+cpu torchaudio==2.9.1+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm6.3",
        "platform": ["linux"],
        "torch_ver": "torch==2.9.1+rocm6.3 torchvision==0.24.1+rocm6.3 torchaudio==2.9.1+rocm6.3",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.3"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.3"][0]],
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
        "dtype": "rocm6.4",
        "platform": ["linux"],
        "torch_ver": "torch==2.9.1+rocm6.4 torchvision==0.24.1+rocm6.4 torchaudio==2.9.1+rocm6.4",
        "xformers_ver": "xformers==0.0.33.post2",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm6.4"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm6.4"][0]],
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
        "name": "Torch 2.9.1 (ROCm 7.2.1 Windows)",
        "dtype": "rocm_win",
        "platform": ["win32"],
        "torch_ver": "torch==2.9.1+rocm7.2.1 torchvision==0.24.1+rocm7.2.1 torchaudio==2.9.1+rocm7.2.1 rocm==7.2.1 rocm-sdk-core==7.2.1 rocm-sdk-devel==7.2.1 rocm-sdk-libraries-custom==7.2.1",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYPI_INDEX_MIRROR_OFFICIAL],
            "mirror": [PYPI_INDEX_MIRROR_TENCENT],
        },
        "extra_index_mirror": {
            "official": [],
            "mirror": [],
        },
        "find_links": {
            "official": [PYTORCH_ROCM_MIRROR_DICT["rocm_win"][0]],
            "mirror": [PYTORCH_ROCM_MIRROR_DICT["rocm_win"][0]],
        },
    },
    {
        "name": "Torch 2.9.1 (XPU)",
        "dtype": "xpu",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.9.1+xpu torchvision==0.24.1+xpu torchaudio==2.9.1+xpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["xpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu126"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu128"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu128"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu130"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu130"][0]],
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
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.10.0+cpu torchvision==0.25.0+cpu torchaudio==2.10.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "dtype": "rocm7.1",
        "platform": ["linux"],
        "torch_ver": "torch==2.10.0+rocm7.1 torchvision==0.25.0+rocm7.1 torchaudio==2.10.0+rocm7.1",
        "xformers_ver": "xformers==0.0.34",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm7.1"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm7.1"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["xpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu126"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu128"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu128"][0]],
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
            "official": [PYTORCH_MIRROR_DICT["cu130"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu130"][0]],
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
        "name": "Torch 2.11.0",
        "dtype": "all",
        "platform": ["win32", "linux", "darwin"],
        "torch_ver": "torch==2.11.0 torchvision==0.26.0 torchaudio==2.11.0",
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
        "name": "Torch 2.11.0 (CPU)",
        "dtype": "cpu",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.11.0+cpu torchvision==0.26.0+cpu torchaudio==2.11.0+cpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cpu"][0]],
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
        "name": "Torch 2.11.0 (ROCm 7.1) + xFormers 0.0.35",
        "dtype": "rocm7.1",
        "platform": ["linux"],
        "torch_ver": "torch==2.11.0+rocm7.1 torchvision==0.26.0+rocm7.1 torchaudio==2.11.0+rocm7.1",
        "xformers_ver": "xformers==0.0.35",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["rocm7.1"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["rocm7.1"][0]],
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
        "name": "Torch 2.11.0 (XPU)",
        "dtype": "xpu",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.11.0+xpu torchvision==0.26.0+xpu torchaudio==2.11.0+xpu",
        "xformers_ver": None,
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["xpu"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["xpu"][0]],
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
        "name": "Torch 2.11.0 (CUDA 12.6) + xFormers 0.0.35",
        "dtype": "cu126",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.11.0+cu126 torchvision==0.26.0+cu126 torchaudio==2.11.0+cu126",
        "xformers_ver": "xformers==0.0.35",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu126"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu126"][0]],
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
        "name": "Torch 2.11.0 (CUDA 12.8) + xFormers 0.0.35",
        "dtype": "cu128",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.11.0+cu128 torchvision==0.26.0+cu128 torchaudio==2.11.0+cu128",
        "xformers_ver": "xformers==0.0.35",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu128"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu128"][0]],
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
        "name": "Torch 2.11.0 (CUDA 13.0) + xFormers 0.0.35",
        "dtype": "cu130",
        "platform": ["win32", "linux"],
        "torch_ver": "torch==2.11.0+cu130 torchvision==0.26.0+cu130 torchaudio==2.11.0+cu130",
        "xformers_ver": "xformers==0.0.35",
        "index_mirror": {
            "official": [PYTORCH_MIRROR_DICT["cu130"][0]],
            "mirror": [PYTORCH_MIRROR_NJU_DICT["cu130"][0]],
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
