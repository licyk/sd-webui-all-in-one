"""Implementation grouped from the former ``extensions.py`` module."""

from __future__ import annotations

from typing import (
    TypedDict,
)
from ..catalog import SDWebUiBranchType


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
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "ADetailer-Neo",
        "url": "https://github.com/Haoming02/ADetailer-Neo",
        "save_dir": "extensions/ADetailer-Neo",
        "supported_branch": [
            "sd_webui_forge_neo",
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
        "url": "https://github.com/licyk/sd-webui-prompt-all-in-one",
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
            "sd_webui_forge_classic",
            "sd_webui_forge_neo",
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
        "url": "https://github.com/licyk/sd-webui-controlnet",
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
