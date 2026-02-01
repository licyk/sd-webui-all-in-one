import os
import json
import uuid
import urllib.request
from typing import Any, TypedDict, Literal, TypeAlias, Callable, get_args
from pathlib import Path
from tempfile import TemporaryDirectory

from sd_webui_all_in_one.downloader import DownloadToolType
from sd_webui_all_in_one.env_check.fix_dependencies import py_dependency_checker
from sd_webui_all_in_one.env_check.fix_numpy import check_numpy
from sd_webui_all_in_one.env_check.fix_torch import fix_torch_libomp
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check import check_onnxruntime_gpu
from sd_webui_all_in_one.env_check.sd_webui_extension_dependency_installer import install_extension_requirements
from sd_webui_all_in_one.env_check.fix_sd_webui_invaild_repo import fix_stable_diffusion_invaild_repo_url
from sd_webui_all_in_one.model_downloader.base import ModelDownloadUrlType
from sd_webui_all_in_one.pytorch_manager.base import PyTorchDeviceType
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR, ROOT_PATH
from sd_webui_all_in_one.base_manager.base import (
    prepare_pytorch_install_info,
    clone_repo,
    install_pytorch_for_webui,
    get_pypi_mirror_config,
    pre_download_model_for_webui,
    launch_webui,
    get_repo_name_from_url,
    install_webui_model_from_library,
)
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.mirror_manager import GITHUB_MIRROR_LIST, set_github_mirror, HUGGINGFACE_MIRROR_LIST
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.file_operations.file_manager import copy_files, move_files, remove_files

logger = get_logger(
    name="SD WebUI Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

SDWebUiBranchType: TypeAlias = Literal[
    "sd_webui_main",
    "sd_webui_dev",
    "sd_webui_forge",
    "sd_webui_reforge_main",
    "sd_webui_reforge_dev",
    "sd_webui_forge_classic",
    "sd_webui_forge_neo",
    "sd_webui_amdgpu",
    "sd_next_main",
    "sd_next_dev",
]
"""Stable Diffusion WebUI 分支类型"""

SD_WEBUI_BRANCH_LIST: list[str] = list(get_args(SDWebUiBranchType))
"""Stable Diffusion WebUI 分支类型列表"""


class SDWebUiBranchInfo(TypedDict):
    """Stable Diffusion WebUI 分支信息"""

    name: str
    """Stable Diffusion WebUI 分支名称"""

    dtype: SDWebUiBranchType
    """Stable Diffusion WebUI 分支类型"""

    url: str
    """Stable Diffusion WebUI 分支的 Git 仓库地址"""

    branch: str
    """Stable Diffusion WebUI 的 Git 分支名称"""

    use_submodule: bool
    """Stable Diffusion WebUI 分支中是否包含 Git 子模块"""


SD_WEBUI_BRANCH_INFO_DICT: list[SDWebUiBranchInfo] = [
    {
        "name": "AUTOMATIC1111 - Stable-Diffusion-WebUI 主分支",
        "dtype": "sd_webui_main",
        "url": "https://github.com/AUTOMATIC1111/stable-diffusion-webui",
        "branch": "master",
        "use_submodule": False,
    },
    {
        "name": "AUTOMATIC1111 - Stable-Diffusion-WebUI 测试分支",
        "dtype": "sd_webui_dev",
        "url": "https://github.com/AUTOMATIC1111/stable-diffusion-webui",
        "branch": "dev",
        "use_submodule": False,
    },
    {
        "name": "lllyasviel - Stable-Diffusion-WebUI-Forge 分支",
        "dtype": "sd_webui_forge",
        "url": "https://github.com/lllyasviel/stable-diffusion-webui-forge",
        "branch": "main",
        "use_submodule": False,
    },
    {
        "name": "Panchovix - Stable-Diffusion-WebUI-reForge 主分支",
        "dtype": "sd_webui_reforge_main",
        "url": "https://github.com/Panchovix/stable-diffusion-webui-reForge",
        "branch": "main",
        "use_submodule": False,
    },
    {
        "name": "Panchovix - Stable-Diffusion-WebUI-reForge 测试分支",
        "dtype": "sd_webui_reforge_dev",
        "url": "https://github.com/Panchovix/stable-diffusion-webui-reForge",
        "branch": "dev_upstream",
        "use_submodule": False,
    },
    {
        "name": "Haoming02 - Stable-Diffusion-WebUI-Forge-Classic 分支",
        "dtype": "sd_webui_forge_classic",
        "url": "https://github.com/Haoming02/sd-webui-forge-classic",
        "branch": "classic",
        "use_submodule": False,
    },
    {
        "name": "Haoming02 - Stable-Diffusion-WebUI-Forge-Neo 分支",
        "dtype": "sd_webui_forge_neo",
        "url": "https://github.com/Haoming02/sd-webui-forge-classic",
        "branch": "neo",
        "use_submodule": False,
    },
    {
        "name": "lshqqytiger - Stable-Diffusion-WebUI-AMDGPU 分支",
        "dtype": "sd_webui_amdgpu",
        "url": "https://github.com/lshqqytiger/stable-diffusion-webui-amdgpu",
        "branch": "master",
        "use_submodule": False,
    },
    {
        "name": "vladmandic - SD.NEXT 主分支",
        "dtype": "sd_next_main",
        "url": "https://github.com/vladmandic/sdnext",
        "branch": "master",
        "use_submodule": True,
    },
    {
        "name": "vladmandic - SD.NEXT 测试分支",
        "dtype": "sd_next_dev",
        "url": "https://github.com/vladmandic/sdnext",
        "branch": "dev",
        "use_submodule": True,
    },
]
"""Stable Diffusion WebUI 分支信息字典"""


class SDWebUiExtensionInfo(TypedDict):
    """Stable Diffusion WebUI 扩展 / 组件信息"""

    name: str
    """Stable Diffusion WebUI 扩展 / 组件名称"""

    url: str
    """Stable Diffusion WebUI 扩展 / 组件的 Git 仓库地址"""

    save_dir: str
    """Stable Diffusion WebUI 扩展 / 组件安装路径 (使用相对路径, 初始位置为 WebUI 的根目录)"""

    supported_branch: list[SDWebUiBranchType]
    """Stable Diffusion WebUI 扩展 / 组件支持的分支类型"""


SDWebUiExtensionInfoList = list[SDWebUiExtensionInfo]
"""Stable Diffusion WebUI 扩展 / 组件信息列表"""

SD_WEBUI_EXTENSION_INFO_DICT: SDWebUiExtensionInfoList = [
    {
        "name": "ultimate-upscale-for-automatic1111",
        "url": "https://github.com/Coyote-A/ultimate-upscale-for-automatic1111",
        "save_dir": "extensions/ultimate-upscale-for-automatic1111",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "a1111-sd-webui-tagcomplete",
        "url": "https://github.com/DominikDoom/a1111-sd-webui-tagcomplete",
        "save_dir": "extensions/a1111-sd-webui-tagcomplete",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "adetailer",
        "url": "https://github.com/Bing-su/adetailer",
        "save_dir": "extensions/adetailer",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "sd-webui-infinite-image-browsing",
        "url": "https://github.com/zanllp/sd-webui-infinite-image-browsing",
        "save_dir": "extensions/sd-webui-infinite-image-browsing",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "sd-webui-openpose-editor",
        "url": "https://github.com/huchenlei/sd-webui-openpose-editor",
        "save_dir": "extensions/sd-webui-openpose-editor",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "sd-webui-prompt-all-in-one",
        "url": "https://github.com/Physton/sd-webui-prompt-all-in-one",
        "save_dir": "extensions/sd-webui-prompt-all-in-one",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "sd-webui-wd14-tagger",
        "url": "https://github.com/licyk/sd-webui-wd14-tagger",
        "save_dir": "extensions/sd-webui-wd14-tagger",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
        ],
    },
    {
        "name": "stable-diffusion-webui-localization-zh_Hans",
        "url": "https://github.com/hanamizuki-ai/stable-diffusion-webui-localization-zh_Hans",
        "save_dir": "extensions/stable-diffusion-webui-localization-zh_Hans",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "sd-webui-mosaic-outpaint",
        "url": "https://github.com/Haoming02/sd-webui-mosaic-outpaint",
        "save_dir": "extensions/sd-webui-mosaic-outpaint",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "sd-webui-resource-monitor",
        "url": "https://github.com/Haoming02/sd-webui-resource-monitor",
        "save_dir": "extensions/sd-webui-resource-monitor",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "sd-webui-tcd-sampler",
        "url": "https://github.com/licyk/sd-webui-tcd-sampler",
        "save_dir": "extensions/sd-webui-tcd-sampler",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "advanced_euler_sampler_extension",
        "url": "https://github.com/licyk/advanced_euler_sampler_extension",
        "save_dir": "extensions/advanced_euler_sampler_extension",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
        ],
    },
    {
        "name": "sd-webui-regional-prompter",
        "url": "https://github.com/hako-mikan/sd-webui-regional-prompter",
        "save_dir": "extensions/sd-webui-regional-prompter",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
        ],
    },
    {
        "name": "sd-webui-model-converter",
        "url": "https://github.com/Akegarasu/sd-webui-model-converter",
        "save_dir": "extensions/sd-webui-model-converter",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "sd-webui-controlnet",
        "url": "https://github.com/Mikubill/sd-webui-controlnet",
        "save_dir": "extensions/sd-webui-controlnet",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_amdgpu",
        ],
    },
    {
        "name": "multidiffusion-upscaler-for-automatic1111",
        "url": "https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111",
        "save_dir": "extensions/multidiffusion-upscaler-for-automatic1111",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_amdgpu",
        ],
    },
    {
        "name": "sd-dynamic-thresholding",
        "url": "https://github.com/mcmonkeyprojects/sd-dynamic-thresholding",
        "save_dir": "extensions/sd-dynamic-thresholding",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "sd-webui-lora-block-weight",
        "url": "https://github.com/hako-mikan/sd-webui-lora-block-weight",
        "save_dir": "extensions/sd-webui-lora-block-weight",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "stable-diffusion-webui-model-toolkit",
        "url": "https://github.com/arenasys/stable-diffusion-webui-model-toolkit",
        "save_dir": "extensions/stable-diffusion-webui-model-toolkit",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
        ],
    },
    {
        "name": "a1111-sd-webui-haku-img",
        "url": "https://github.com/licyk/a1111-sd-webui-haku-img",
        "save_dir": "extensions/a1111-sd-webui-haku-img",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "sd-webui-supermerger",
        "url": "https://github.com/hako-mikan/sd-webui-supermerger",
        "save_dir": "extensions/sd-webui-supermerger",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
        ],
    },
    {
        "name": "sd-webui-segment-anything",
        "url": "https://github.com/continue-revolution/sd-webui-segment-anything",
        "save_dir": "extensions/sd-webui-segment-anything",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "sd_forge_hypertile_svd_z123",
        "url": "https://github.com/licyk/sd_forge_hypertile_svd_z123",
        "save_dir": "extensions/sd_forge_hypertile_svd_z123",
        "supported_branch": [
            "sd_webui_forge",
        ],
    },
    {
        "name": "sd-forge-layerdiffuse",
        "url": "https://github.com/lllyasviel/sd-forge-layerdiffuse",
        "save_dir": "extensions/sd-forge-layerdiffuse",
        "supported_branch": [
            "sd_webui_forge",
        ],
    },
    {
        "name": "sd-webui-licyk-style-image",
        "url": "https://github.com/licyk/sd-webui-licyk-style-image",
        "save_dir": "extensions/sd-webui-licyk-style-image",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "sdwebui-close-confirmation-dialogue",
        "url": "https://github.com/w-e-w/sdwebui-close-confirmation-dialogue",
        "save_dir": "extensions/sdwebui-close-confirmation-dialogue",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "stable-diffusion-webui-zoomimage",
        "url": "https://github.com/viyiviyi/stable-diffusion-webui-zoomimage",
        "save_dir": "extensions/stable-diffusion-webui-zoomimage",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
]
"""Stable Diffusion WebUI 扩展信息字典"""

SD_WEBUI_REPOSITORY_INFO_DICT: SDWebUiExtensionInfoList = [
    {
        "name": "BLIP",
        "url": "https://github.com/salesforce/BLIP",
        "save_dir": "repositories/BLIP",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "stablediffusion",
        "url": "https://github.com/licyk/stablediffusion",
        "save_dir": "repositories/stable-diffusion-stability-ai",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "generative-models",
        "url": "https://github.com/Stability-AI/generative-models",
        "save_dir": "repositories/generative-models",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "k-diffusion",
        "url": "https://github.com/crowsonkb/k-diffusion",
        "save_dir": "repositories/k-diffusion",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "stable-diffusion-webui-assets",
        "url": "https://github.com/AUTOMATIC1111/stable-diffusion-webui-assets",
        "save_dir": "repositories/stable-diffusion-webui-assets",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "huggingface_guess",
        "url": "https://github.com/lllyasviel/huggingface_guess",
        "save_dir": "repositories/huggingface_guess",
        "supported_branch": [
            "sd_webui_forge",
        ],
    },
    {
        "name": "google_blockly_prototypes",
        "url": "https://github.com/lllyasviel/google_blockly_prototypes",
        "save_dir": "repositories/google_blockly_prototypes",
        "supported_branch": [
            "sd_webui_forge",
        ],
    },
]
"""Stable Diffusion WebUI 组件信息字典"""

SD_WEBUI_CONFIG_PATH = ROOT_PATH / "base_manager" / "config" / "sd_webui_config.json"
"""Stable Diffusion WebUI 预设配置文件路径"""


def install_sd_webui_config(
    sd_webui_path: Path,
) -> None:
    """安装 Stable Diffusion WebUI 配置文件

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录

    """
    config_path = sd_webui_path / "config.json"
    if not config_path.exists():
        copy_files(SD_WEBUI_CONFIG_PATH, config_path)


def install_sd_webui(
    sd_webui_path: Path,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_cn_pypi_mirror: bool | None = True,
    use_uv: bool | None = True,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    install_branch: SDWebUiBranchType | None = None,
    no_pre_download_extension: bool | None = False,
    no_pre_download_model: bool | None = False,
    use_cn_model_mirror: bool | None = True,
) -> None:
    """安装 Stable Diffusion WebUI

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        pytorch_mirror_type (PyTorchDeviceType | None):
            设置使用的 PyTorch 镜像源类型
        custom_pytorch_package (str | None):
            自定义 PyTorch 软件包版本声明, 例如: `torch==2.3.0+cu118 torchvision==0.18.0+cu118`
        custom_xformers_package (str | None):
            自定义 xFormers 软件包版本声明, 例如: `xformers===0.0.26.post1+cu118`
        use_cn_pypi_mirror (bool | None):
            是否使用国内 PyPI 镜像源
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        install_branch (SDWebUiBranchType | None):
            安装的 Stable Diffusion WebUI 分支
        no_pre_download_extension (bool | None):
            是否禁用预下载 Stable Diffusion WebUI 扩展
        no_pre_download_model (bool | None):
            是否禁用预下载模型
        use_cn_model_mirror (bool | None):
            是否使用国内镜像下载模型

    Raises:
        ValueError:
            安装的 Stable Diffusion WebUI 分支未知时
        FileNotFoundError:
            Stable Diffusion WebUI 依赖文件缺失时
    """
    logger.info("准备 Stable Diffusion WebUI 安装配置")

    # 准备 Stable Diffusion WebUI 安装分支信息
    if install_branch is None:
        install_branch = SD_WEBUI_BRANCH_LIST[0]

    if install_branch not in SD_WEBUI_BRANCH_LIST:
        raise ValueError(f"未知的 Stable Diffusion WebUI 类型: {install_branch}")

    for info in SD_WEBUI_BRANCH_INFO_DICT:
        if info["dtype"] == install_branch:
            branch_info = info
            break

    # 准备 PyTorch 安装信息
    pytorch_package, xformers_package, custom_env_pytorch = prepare_pytorch_install_info(
        pytorch_mirror_type=pytorch_mirror_type,
        custom_pytorch_package=custom_pytorch_package,
        custom_xformers_package=custom_xformers_package,
        use_cn_mirror=use_cn_pypi_mirror,
    )

    # 准备扩展 / 组件安装信息
    sd_weui_extension_list = [x for x in SD_WEBUI_EXTENSION_INFO_DICT if install_branch in x["supported_branch"] and not no_pre_download_extension]
    sd_webui_repository_list = [x for x in SD_WEBUI_REPOSITORY_INFO_DICT if install_branch in x["supported_branch"]]

    # 准备安装依赖的 PyPI 镜像源
    custom_env = get_pypi_mirror_config(use_cn_pypi_mirror)

    logger.debug("安装的 PyTorch 版本: %s", pytorch_package)
    logger.debug("安装的 xformers: %s", xformers_package)
    logger.debug("安装的扩展信息: %s", sd_weui_extension_list)
    logger.debug("安装的组件信息: %s", sd_webui_repository_list)

    logger.info("Stable Diffusion WebUI 安装配置准备完成")
    logger.info("开始安装 Stable Diffusion WebUI, 安装路径: %s", sd_webui_path)
    logger.info("安装的 Stable Diffusion WebUI 分支: '%s'", branch_info["name"])

    with TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        git_config_path = Path(os.getenv("GIT_CONFIG_GLOBAL", (tmp_dir / ".gitconfig").as_posix()))
        set_github_mirror(
            mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
            config_path=git_config_path,
        )

        logger.info("安装 Stable Diffusion WebUI 内核中")
        clone_repo(
            repo=branch_info["url"],
            path=sd_webui_path,
        )

        logger.info("切换 Stable Diffusion WebUI 分支中")
        git_warpper.switch_branch(
            path=sd_webui_path,
            branch=branch_info["branch"],
            new_url=branch_info["url"],
            recurse_submodules=branch_info["use_submodule"],
        )

        if sd_webui_repository_list:
            logger.info("安装 Stable Diffusion WebUI 组件中")
            for info in sd_webui_repository_list:
                clone_repo(
                    repo=info["url"],
                    path=sd_webui_path / info["save_dir"],
                )

        if sd_weui_extension_list:
            logger.info("安装 Stable Diffusion WebUI 扩展中")
            for info in sd_weui_extension_list:
                clone_repo(
                    repo=info["url"],
                    path=sd_webui_path / info["save_dir"],
                )

        install_pytorch_for_webui(
            pytorch_package=pytorch_package,
            xformers_package=xformers_package,
            custom_env=custom_env_pytorch,
            use_uv=use_uv,
        )

        requirements_version_path = sd_webui_path / "requirements_version.txt"
        requirements_path = sd_webui_path / "requirements.txt"

        if not requirements_path.is_file() and requirements_version_path.is_file():
            raise FileNotFoundError("未找到 Stable Diffusion WebUI 依赖文件记录表, 请检查 Stable Diffusion WebUI 文件是否完整")

        logger.info("安装 Stable Diffusion WebUI 依赖中")
        install_requirements(
            path=requirements_version_path if requirements_version_path.is_file() else requirements_path,
            use_uv=use_uv,
            custom_env=custom_env,
            cwd=sd_webui_path,
        )

        if not no_pre_download_model:
            pre_download_model_for_webui(
                dtype="sd_webui",
                model_path=sd_webui_path / "models" / "Stable-diffusion",
                webui_base_path=sd_webui_path,
                model_name="ChenkinNoob-XL-V0.2",
                download_resource_type="modelscope" if use_cn_model_mirror else "huggingface",
            )

        install_sd_webui_config(sd_webui_path)

    logger.info("安装 Stable Diffusion WebUI 完成")


def check_sd_webui_env(
    sd_webui_path: Path,
    check: bool | None = True,
    use_github_mirror: bool | None = False,
    use_uv: bool | None = True,
) -> None:
    """检查 Stable Diffusion WebUI 运行环境

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        check (bool | None):
            是否检查环境时发生的错误, 设置为 True 时, 如果检查环境发生错误时将抛出异常
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool | None):
            是否使用 Github 镜像源

    Raises:
        AggregateError:
            检查 Stable Diffusion WebUI 环境发生错误时
        FileNotFoundError:
            未找到 Stable Diffusion WebUI 依赖文件记录表时
    """
    req_v_path = sd_webui_path / "requirements_version.txt"
    req_path = sd_webui_path / "requirements.txt"

    if check and req_v_path.is_file() and not req_path.is_file():
        raise FileNotFoundError("未找到 Stable Diffusion WebUI 依赖文件记录表, 请检查文件是否完整")

    # 确定主要的依赖描述文件
    active_req_path = req_v_path if req_v_path.is_file() else req_path

    with TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        git_config_path = Path(os.getenv("GIT_CONFIG_GLOBAL", (tmp_dir / ".gitconfig").as_posix()))
        set_github_mirror(
            mirror=GITHUB_MIRROR_LIST if use_github_mirror else None,
            config_path=git_config_path,
        )

        # 检查任务列表
        tasks: list[tuple[Callable, dict[str, Any]]] = [
            (fix_stable_diffusion_invaild_repo_url, {"sd_webui_path": sd_webui_path}),
            (py_dependency_checker, {"requirement_path": active_req_path, "name": "Stable Diffusion WebUI", "use_uv": use_uv}),
            (install_extension_requirements, {"sd_webui_path": sd_webui_path}),
            (fix_torch_libomp, {}),
            (check_onnxruntime_gpu, {"use_uv": use_uv, "skip_if_missing": True}),
            (check_numpy, {"use_uv": use_uv}),
        ]
        err: list[Exception] = []

        for func, kwargs in tasks:
            try:
                func(**kwargs)
            except Exception as e:
                err.append(e)

        if err and check:
            raise AggregateError("检查 Stable Diffusion WebUI 环境时发生错误", err)

        logger.info("检查 Stable Diffusion WebUI 环境完成")


def set_sd_webui_extension_download_list_mirror(
    custom_github_mirror: str | list[str] | None = None,
    origin_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """配置 Stable Diffusion WebUI 扩展下载列表镜像源

    Args:
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源列表
        origin_env (dict[str, str] | None):
            原始的环境变量字典

    Raises:
        ValueError:
            传入的镜像源参数类型不支持时
    """
    if origin_env is None:
        origin_env = os.environ.copy()

    github_mirror = GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    if github_mirror is None:
        return origin_env
    if isinstance(github_mirror, str):
        origin_env["WEBUI_EXTENSIONS_INDEX"] = github_mirror
        return origin_env
    if isinstance(github_mirror, list):
        for gh in github_mirror:
            mirror_prefix = gh.replace("github.com", "raw.githubusercontent.com", 1)
            test_url = f"{mirror_prefix}/licyk/empty/main/README.md"
            req = urllib.request.Request(test_url, headers=headers)
            try:
                logger.info("测试镜像源: %s", gh)
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.getcode() == 200:
                        logger.info("该镜像源可用")
                        origin_env["WEBUI_EXTENSIONS_INDEX"] = f"{mirror_prefix}/AUTOMATIC1111/stable-diffusion-webui-extensions/master/index.json"
                        return origin_env
            except Exception:
                logger.info("该镜像源不可用")

        logger.info("无可用的 Github 镜像源")
        return origin_env

    raise ValueError(f"传入的 Github 镜像源列表类型不支持: {type(github_mirror)}")


def launch_sd_webui(
    sd_webui_path: Path,
    launch_args: list[str] | None = None,
    use_hf_mirror: bool | None = False,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool | None = False,
) -> None:
    """启动 Stable Diffusion WebUI

    Args:
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        launch_args (list[str] | None):
            启动 Stable Diffusion WebUI 的参数
        use_hf_mirror (bool | None):
            是否启用 HuggingFace 镜像源
        use_github_mirror (bool | None):
            是否启用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        use_pypi_mirror (bool | None):
            是否启用 PyPI 镜像源
    """
    with TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        logger.info("准备 Stable Diffusion WebUI 启动环境")
        git_config_path = Path(os.getenv("GIT_CONFIG_GLOBAL", (tmp_dir / ".gitconfig").as_posix()))
        set_github_mirror(
            mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
            config_path=git_config_path,
        )
        custom_env = os.environ.copy()

        if use_hf_mirror:
            custom_env["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT", HUGGINGFACE_MIRROR_LIST[0])

        custom_env = get_pypi_mirror_config(
            use_cn_mirror=use_pypi_mirror,
            origin_env=custom_env,
        )
        custom_env["STABLE_DIFFUSION_REPO"] = "https://github.com/licyk/stablediffusion"
        if use_github_mirror:
            custom_env = set_sd_webui_extension_download_list_mirror(
                custom_github_mirror=custom_github_mirror,
                origin_env=custom_env,
            )

        logger.info("启动 Stable Diffusion WebUI 中")
        launch_webui(
            webui_path=sd_webui_path,
            launch_script="launch.py",
            launch_args=launch_args,
            custom_env=custom_env,
        )


def install_extension(
    sd_webui_path: Path,
    extension_url: str | list[str],
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    check: bool | None = True,
) -> None:
    """安装 Stable Diffusion WebUI 扩展

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        extension_url (str | list[str]):
            Stable Diffusion WebUI 扩展下载链接
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        check (bool | None):
            是否检查安装扩展时发生的错误, 设置为 True 时, 如果安装扩展时发生错误时将抛出异常

    Raises:
        AggregateError:
            安装 Stable Diffusion WebUI 扩展发生错误时
    """
    urls = [extension_url] if isinstance(extension_url, str) else extension_url

    # 获取已安装扩展列表
    extension_list = list_extensions(sd_webui_path)
    installed_names = {x["name"] for x in extension_list}
    err: list[Exception] = []

    with TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        git_config_path = Path(os.getenv("GIT_CONFIG_GLOBAL", (tmp_dir / ".gitconfig").as_posix()))
        set_github_mirror(
            mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
            config_path=git_config_path,
        )

        for url in urls:
            extension_name = get_repo_name_from_url(url)
            extension_path = sd_webui_path / "extensions" / extension_name

            if extension_name in installed_names or extension_path.exists():
                logger.info("'%s' 扩展已安装", extension_name)
                continue

            logger.info("安装 '%s' 扩展到 '%s' 中", extension_name, extension_path)
            try:
                clone_repo(
                    repo=url,
                    path=extension_path,
                )
                logger.info("'%s' 扩展安装成功", extension_name)
                installed_names.add(extension_name)
            except Exception as e:
                err.append(e)
                logger.error("'%s' 扩展安装失败: %s", extension_name, e)

    if err and check:
        raise AggregateError("检查 Stable Diffusion WebUI 环境时发生错误", err)

    logger.info("安装 Stable Diffusion WebUI 扩展完成")


class SDWebUiLocalExtensionInfo(TypedDict, total=False):
    """Stable Diffusion WebUI 本地扩展信息"""

    name: str
    """Stable Diffusion WebUI 扩展名称"""

    status: bool
    """当前 Stable Diffusion WebUI 是否已经启用"""

    path: Path
    """Stable Diffusion WebUI 本地路径"""

    url: str | None
    """Stable Diffusion WebUI 扩展远程地址"""

    commit: str | None
    """Stable Diffusion WebUI 扩展的提交信息"""

    branch: str | None
    """Stable Diffusion WebUI 扩展的当前分支"""


SDWebUiLocalExtensionInfoList = list[SDWebUiLocalExtensionInfo]
"""Stable Diffusion WebUI 本地扩展信息"""


def set_extensions_status(
    sd_webui_path: Path,
    extension_name: str,
    status: bool,
) -> None:
    """设置 Stable Diffusion WebUI 启用状态

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        extension_name (str):
            Stable Diffusion WebUI 扩展名称
        status (bool):
            设置扩展的启用状态
            - `True`: 启用
            - `False`: 禁用

    Raises:
        FileNotFoundError:
            Stable Diffusion WebUI 未找到时
    """

    def _save(data: dict[str, Any]) -> None:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    config_path = sd_webui_path / "config.json"
    extension_path = sd_webui_path / "extensions"
    extension_list = [ext.name for ext in extension_path.iterdir() if ext.is_dir()]
    settings: dict[str, str | list[str] | Any] = {}

    if extension_name not in extension_list:
        raise FileNotFoundError(f"'{extension_name}' 扩展未找到, 请检查该扩展是否已安装")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except Exception as e:
        logger.error("加载 '%s' 配置文件发生错误: %s", config_path, e)
        logger.warning("尝试重置 Stable Diffusion WebUI 配置文件")
        move_files(config_path, f"config_{uuid.uuid4()}.json")

    if "disabled_extensions" not in settings:
        settings["disabled_extensions"] = []

    if status:
        if extension_name in settings["disabled_extensions"]:
            settings["disabled_extensions"].remove(extension_name)
            _save(settings)
        logger.info("启用 '%s' 扩展成功", extension_name)
    else:
        if extension_name not in settings["disabled_extensions"]:
            settings["disabled_extensions"].append(extension_name)
            _save(settings)
        logger.info("禁用 '%s' 扩展成功", extension_name)


def list_extensions(
    sd_webui_path: Path,
) -> SDWebUiLocalExtensionInfoList:
    """获取 Stable Diffusion WebUI 本地扩展列表

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录

    Returns:
        SDWebUiLocalExtensionInfoList:
            Stable Diffusion WebUI 本地扩展列表
    """
    config_path = sd_webui_path / "config.json"
    extension_path = sd_webui_path / "extensions"
    info_list: SDWebUiLocalExtensionInfoList = []

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except Exception as e:
        logger.debug("加载 '%s' 配置文件发生错误: %s", config_path, e)
        settings = {}

    disabled_extensions = set(settings.get("disabled_extensions", []))
    disable_all_extensions = settings.get("disable_all_extensions", "none")

    for ext in extension_path.iterdir():
        info: SDWebUiLocalExtensionInfo = {}
        if ext.is_file():
            continue

        name = ext.name
        path = ext

        if disable_all_extensions == "all":
            status = False
        elif disable_all_extensions != "extra":
            status = name not in disabled_extensions
        else:
            status = True

        try:
            url = git_warpper.get_current_branch_remote_url(ext)
        except ValueError:
            url = None

        try:
            commit = git_warpper.get_current_commit(ext)
        except ValueError:
            commit = None

        try:
            branch = git_warpper.get_current_branch(ext)
        except ValueError:
            branch = None

        info["name"] = name
        info["status"] = status
        info["path"] = path
        info["url"] = url
        info["commit"] = commit
        info["branch"] = branch
        info_list.append(info)

    return info_list


def update_extensions(
    sd_webui_path: Path,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    check: bool | None = True,
) -> None:
    """更新 Stable Diffusion WebUI 扩展

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录、
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        check (bool | None):
            是否检查更新时发生的错误, 设置为 True 时, 如果更新扩展时发生错误时将抛出异常

    Raises:
        AggregateError:
            检查 Stable Diffusion WebUI 环境发生错误时
    """
    extension_path = sd_webui_path / "extensions"
    err: list[Exception] = []
    with TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        git_config_path = Path(os.getenv("GIT_CONFIG_GLOBAL", (tmp_dir / ".gitconfig").as_posix()))
        set_github_mirror(
            mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
            config_path=git_config_path,
        )
        for ext in extension_path.iterdir():
            if ext.is_file():
                continue

            logger.info("更新 '%s' 扩展中", ext.name)
            try:
                git_warpper.update(ext)
            except Exception as e:
                err.append(e)
                logger.error("更新 '%s' 扩展时发生错误: %s", ext.name, e)

    if err and check:
        raise AggregateError("更新 Stable Diffusion WebUI 扩展时发生错误", err)

    logger.info("更新 Stable Diffusion WebUI 扩展完成")


def uninstall_extension(
    sd_webui_path: Path,
    extension_name: str,
    check: bool | None = True,
) -> None:
    """卸载 Stable Diffusion WebUI 扩展

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        extension_name (str):
            Stable Diffusion WebUI
        check (bool | None):
            是否卸载扩展时发生的错误, 设置为 True 时, 如果卸载扩展时发生错误时将抛出异常

    Raises:
        FileNotFoundError:
            要卸载的扩展未找到时
        RuntimeError:
            卸载扩展发生错误时
    """
    extension_path = sd_webui_path / "extensions"
    extension_list = [ext.name for ext in extension_path.iterdir() if ext.is_dir()]
    if extension_name not in extension_list:
        raise FileNotFoundError(f"'{extension_name}' 扩展未安装")

    try:
        logger.info("卸载 '%s' 扩展中", extension_name)
        remove_files(extension_path / extension_name)
        logger.info("卸载 '%s' 扩展完成", extension_name)
    except Exception as e:
        logger.info("卸载 '%s' 扩展时发生错误: %s", extension_name, e)
        if check:
            raise RuntimeError(f"卸载 '{extension_name}' 扩展时发生错误:{e}") from e


def install_model_from_library(
    sd_webui_path: Path,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = "aria2",
    interactive_mode: bool | None = False,
) -> None:
    """为 Stable Diffusion WebUI 下载模型, 使用模型库进行下载

    Args:
        webui_path (Path):
            Stable Diffusion WebUI 根目录
        download_resource_type (ModelDownloadUrlType | None):
            模型下载源类型
        model_name (str | None):
            下载的模型名称
        model_index (int | None):
            下载的模型在列表中的索引值, 索引值从 1 开始. 当同时提供 `model_name` 和 `model_index` 时, 优先使用 `model_index` 查找模型
        downloader (DownloadToolType | None):
            下载模型使用的工具
        interactive_mode (bool | None):
            是否启用交互模式
    """
    install_webui_model_from_library(
        webui_path=sd_webui_path,
        dtype="sd_webui",
        download_resource_type=download_resource_type,
        model_name=model_name,
        model_index=model_index,
        downloader=downloader,
        interactive_mode=interactive_mode,
    )


def install_model_from_url(
    sd_webui_path: Path,
) -> None: ...


def list_models(
    sd_webui_path: Path,
) -> None: ...


def uninstall_model(
    sd_webui_path: Path,
) -> None: ...
