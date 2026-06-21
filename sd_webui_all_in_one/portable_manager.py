"""整合包资源列表生成工具"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from functools import cmp_to_key
from pathlib import Path
from typing import Literal, TypeAlias, TypedDict, get_args

from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.package_analyzer.ver_cmp import CommonVersionComparison
from sd_webui_all_in_one.repo_manager import (
    ApiType,
    RepoManager,
    RepoType,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

PortableSourceType: TypeAlias = ApiType
"""整合包下载源类型"""

PortableChannelType: TypeAlias = Literal["stable", "nightly"]
"""整合包发行通道类型"""

PORTABLE_SOURCE_TYPE_LIST: list[PortableSourceType] = list(get_args(PortableSourceType))
"""整合包下载源类型列表"""

PORTABLE_CHANNEL_TYPE_LIST: list[PortableChannelType] = list(get_args(PortableChannelType))
"""整合包发行通道类型列表"""

DEFAULT_PORTABLE_PATH_IN_REPO = "portable"
"""默认整合包仓库目录"""

PORTABLE_NAME_PATTERN = r"""
    ^
    (?P<software>[\w_]+?)
    -
    (?P<signature>[a-z0-9]+)
    -
    (?:
        (?P<build_date>\d{8})
        -
        nightly
    |
        v
        (?P<version>[\d.]+)
    )
    \.
    (?P<extension>[a-z0-9]+(?:\.[a-z0-9]+)?)
    $
"""
"""整合包文件名解析正则"""

PORTABLE_NAME_REGEX = re.compile(PORTABLE_NAME_PATTERN, re.VERBOSE | re.IGNORECASE)
"""整合包文件名解析正则对象"""


class PortableSoftwareMetadata(TypedDict):
    """整合包软件元数据"""

    display_name: str
    """展示名称"""

    description: str
    """整合包描述"""


PORTABLE_SOFTWARE_METADATA: dict[str, PortableSoftwareMetadata] = {
    "sd_webui": {
        "display_name": "Stable Diffusion WebUI (NVIDIA)",
        "description": "Stable Diffusion WebUI 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，上手简单，操作方便，适合入门使用。",
    },
    "sd_webui_rocm": {
        "display_name": "Stable Diffusion WebUI (AMD)",
        "description": "Stable Diffusion WebUI 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，上手简单，操作方便，适合入门使用。",
    },
    "sd_webui_xpu": {
        "display_name": "Stable Diffusion WebUI (Intel)",
        "description": "Stable Diffusion WebUI 的 Intel 显卡整合包，使用 XPU 版 PyTorch，上手简单，操作方便，适合入门使用。",
    },
    "sd_webui_amdgpu": {
        "display_name": "Stable Diffusion WebUI AMDGPU (NVIDIA)",
        "description": "Stable Diffusion WebUI AMDGPU 分支的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，保留 Stable Diffusion WebUI 体验，并包含 DirectML 和 ZLUDA 等后端支持。",
    },
    "sd_webui_amdgpu_rocm": {
        "display_name": "Stable Diffusion WebUI AMDGPU (AMD)",
        "description": "Stable Diffusion WebUI AMDGPU 分支的 AMD 显卡整合包，使用 ROCm 版 PyTorch，支持 DirectML 和 ZLUDA，更适合 AMD 显卡用户使用。",
    },
    "sd_webui_amdgpu_xpu": {
        "display_name": "Stable Diffusion WebUI AMDGPU (Intel)",
        "description": "Stable Diffusion WebUI AMDGPU 分支的 Intel 显卡整合包，使用 XPU 版 PyTorch，保留 Stable Diffusion WebUI 体验，并包含 DirectML 等后端支持。",
    },
    "sd_webui_forge": {
        "display_name": "Stable Diffusion WebUI Forge (NVIDIA)",
        "description": "Stable Diffusion WebUI Forge 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，基于 Stable Diffusion WebUI，有更强的显存优化，多了 FLUX 模型支持。",
    },
    "sd_webui_forge_rocm": {
        "display_name": "Stable Diffusion WebUI Forge (AMD)",
        "description": "Stable Diffusion WebUI Forge 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，基于 Stable Diffusion WebUI，有更强的显存优化，多了 FLUX 模型支持。",
    },
    "sd_webui_forge_xpu": {
        "display_name": "Stable Diffusion WebUI Forge (Intel)",
        "description": "Stable Diffusion WebUI Forge 的 Intel 显卡整合包，使用 XPU 版 PyTorch，基于 Stable Diffusion WebUI，有更强的显存优化，多了 FLUX 模型支持。",
    },
    "sd_webui_reforge": {
        "display_name": "Stable Diffusion WebUI reForge (NVIDIA)",
        "description": "Stable Diffusion WebUI reForge 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，基于旧版 Stable Diffusion WebUI Forge 开发，插件兼容性比 Stable Diffusion WebUI Forge 好一点。",
    },
    "sd_webui_reforge_rocm": {
        "display_name": "Stable Diffusion WebUI reForge (AMD)",
        "description": "Stable Diffusion WebUI reForge 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，基于旧版 Stable Diffusion WebUI Forge 开发，插件兼容性比 Stable Diffusion WebUI Forge 好一点。",
    },
    "sd_webui_reforge_xpu": {
        "display_name": "Stable Diffusion WebUI reForge (Intel)",
        "description": "Stable Diffusion WebUI reForge 的 Intel 显卡整合包，使用 XPU 版 PyTorch，基于旧版 Stable Diffusion WebUI Forge 开发，插件兼容性比 Stable Diffusion WebUI Forge 好一点。",
    },
    "sd_webui_forge_classic": {
        "display_name": "Stable Diffusion WebUI Forge Classic (NVIDIA)",
        "description": "Stable Diffusion WebUI Forge Classic 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，属于 Stable Diffusion WebUI Forge 的经典版本。",
    },
    "sd_webui_forge_classic_rocm": {
        "display_name": "Stable Diffusion WebUI Forge Classic (AMD)",
        "description": "Stable Diffusion WebUI Forge Classic 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，属于 Stable Diffusion WebUI Forge 的经典版本。",
    },
    "sd_webui_forge_classic_xpu": {
        "display_name": "Stable Diffusion WebUI Forge Classic (Intel)",
        "description": "Stable Diffusion WebUI Forge Classic 的 Intel 显卡整合包，使用 XPU 版 PyTorch，属于 Stable Diffusion WebUI Forge 的经典版本。",
    },
    "sd_webui_forge_neo": {
        "display_name": "Stable Diffusion WebUI Forge Neo (NVIDIA)",
        "description": "Stable Diffusion WebUI Forge Neo 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，基于旧版 Stable Diffusion WebUI Forge 开发，精简了无用组件，更轻量。",
    },
    "sd_webui_forge_neo_rocm": {
        "display_name": "Stable Diffusion WebUI Forge Neo (AMD)",
        "description": "Stable Diffusion WebUI Forge Neo 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，基于旧版 Stable Diffusion WebUI Forge 开发，精简了无用组件，更轻量。",
    },
    "sd_webui_forge_neo_xpu": {
        "display_name": "Stable Diffusion WebUI Forge Neo (Intel)",
        "description": "Stable Diffusion WebUI Forge Neo 的 Intel 显卡整合包，使用 XPU 版 PyTorch，基于旧版 Stable Diffusion WebUI Forge 开发，精简了无用组件，更轻量。",
    },
    "sd_next": {
        "display_name": "SD Next (NVIDIA)",
        "description": "SD Next 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，基于 Stable Diffusion WebUI 开发，支持的模型种类多，就是比较臃肿。",
    },
    "sd_next_rocm": {
        "display_name": "SD Next (AMD)",
        "description": "SD Next 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，基于 Stable Diffusion WebUI 开发，支持的模型种类多，就是比较臃肿。",
    },
    "sd_next_xpu": {
        "display_name": "SD Next (Intel)",
        "description": "SD Next 的 Intel 显卡整合包，使用 XPU 版 PyTorch，基于 Stable Diffusion WebUI 开发，支持的模型种类多，就是比较臃肿。",
    },
    "comfyui": {
        "display_name": "ComfyUI (NVIDIA)",
        "description": "ComfyUI 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，流程高度自定义，可玩性高，显存优化强，支持的模型丰富。",
    },
    "comfyui_rocm": {
        "display_name": "ComfyUI (AMD)",
        "description": "ComfyUI 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，流程高度自定义，可玩性高。",
    },
    "comfyui_xpu": {
        "display_name": "ComfyUI (Intel)",
        "description": "ComfyUI 的 Intel 显卡整合包，使用 XPU 版 PyTorch，流程高度自定义，可玩性高。",
    },
    "fooocus": {
        "display_name": "Fooocus (NVIDIA)",
        "description": "Fooocus 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，化繁为简，更专注于提示词书写。",
    },
    "fooocus_rocm": {
        "display_name": "Fooocus (AMD)",
        "description": "Fooocus 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，化繁为简，更专注于提示词书写。",
    },
    "fooocus_xpu": {
        "display_name": "Fooocus (Intel)",
        "description": "Fooocus 的 Intel 显卡整合包，使用 XPU 版 PyTorch，化繁为简，更专注于提示词书写。",
    },
    "ruined_fooocus": {
        "display_name": "RuinedFooocus (NVIDIA)",
        "description": "RuinedFooocus 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，基于 Fooocus，加入样式、通配符、随机提示词和更多可调参数。",
    },
    "ruined_fooocus_rocm": {
        "display_name": "RuinedFooocus (AMD)",
        "description": "RuinedFooocus 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，基于 Fooocus，加入样式、通配符、随机提示词和更多可调参数。",
    },
    "ruined_fooocus_xpu": {
        "display_name": "RuinedFooocus (Intel)",
        "description": "RuinedFooocus 的 Intel 显卡整合包，使用 XPU 版 PyTorch，基于 Fooocus，加入样式、通配符、随机提示词和更多可调参数。",
    },
    "fooocus_mre": {
        "display_name": "Fooocus-MRE (NVIDIA)",
        "description": "Fooocus-MRE 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，基于 Fooocus，加入图生图、Control-LoRA、嵌入和更多采样参数。",
    },
    "fooocus_mre_rocm": {
        "display_name": "Fooocus-MRE (AMD)",
        "description": "Fooocus-MRE 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，基于 Fooocus，加入图生图、Control-LoRA、嵌入和更多采样参数。",
    },
    "fooocus_mre_xpu": {
        "display_name": "Fooocus-MRE (Intel)",
        "description": "Fooocus-MRE 的 Intel 显卡整合包，使用 XPU 版 PyTorch，基于 Fooocus，加入图生图、Control-LoRA、嵌入和更多采样参数。",
    },
    "invokeai": {
        "display_name": "InvokeAI (NVIDIA)",
        "description": "InvokeAI 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，拥有最强大的画布系统，更适合作为辅助绘画工具。",
    },
    "invokeai_rocm": {
        "display_name": "InvokeAI (AMD)",
        "description": "InvokeAI 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，拥有最强大的画布系统，更适合作为辅助绘画工具。",
    },
    "invokeai_xpu": {
        "display_name": "InvokeAI (Intel)",
        "description": "InvokeAI 的 Intel 显卡整合包，使用 XPU 版 PyTorch，拥有最强大的画布系统，更适合作为辅助绘画工具。",
    },
    "sd_trainer": {
        "display_name": "SD Trainer (NVIDIA)",
        "description": "SD Trainer 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，训练模型如此简单。",
    },
    "sd_trainer_rocm": {
        "display_name": "SD Trainer (AMD)",
        "description": "SD Trainer 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，训练模型如此简单。",
    },
    "sd_trainer_xpu": {
        "display_name": "SD Trainer (Intel)",
        "description": "SD Trainer 的 Intel 显卡整合包，使用 XPU 版 PyTorch，训练模型如此简单。",
    },
    "sd_trainer_next": {
        "display_name": "SD Trainer Next (NVIDIA)",
        "description": "SD Trainer Next 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，训练模型如此简单。基于 SD Trainer 分支，并且新增了 Anima 模型的支持。",
    },
    "sd_trainer_next_rocm": {
        "display_name": "SD Trainer Next (AMD)",
        "description": "SD Trainer Next 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，训练模型如此简单。基于 SD Trainer 分支，并且新增了 Anima 模型的支持。",
    },
    "sd_trainer_next_xpu": {
        "display_name": "SD Trainer Next (Intel)",
        "description": "SD Trainer Next 的 Intel 显卡整合包，使用 XPU 版 PyTorch，训练模型如此简单。基于 SD Trainer 分支，并且新增了 Anima 模型的支持。",
    },
    "kohya_gui": {
        "display_name": "Kohya GUI (NVIDIA)",
        "description": "Kohya GUI 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，支持训练更多种类的模型，不过操作麻烦一点。",
    },
    "kohya_gui_rocm": {
        "display_name": "Kohya GUI (AMD)",
        "description": "Kohya GUI 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，支持训练更多种类的模型，不过操作麻烦一点。",
    },
    "kohya_gui_xpu": {
        "display_name": "Kohya GUI (Intel)",
        "description": "Kohya GUI 的 Intel 显卡整合包，使用 XPU 版 PyTorch，支持训练更多种类的模型，不过操作麻烦一点。",
    },
    "sd_scripts": {
        "display_name": "SD Scripts (NVIDIA)",
        "description": "SD Scripts 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，支持训练 SD1.5，SDXL，FLUX，ControlNet 等多种模型，并且是 SD-Trainer 和 Kohya GUI 的训练核心，不过操作比较麻烦。",
    },
    "sd_scripts_rocm": {
        "display_name": "SD Scripts (AMD)",
        "description": "SD Scripts 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，支持训练 SD1.5，SDXL，FLUX，ControlNet 等多种模型，并且是 SD-Trainer 和 Kohya GUI 的训练核心，不过操作比较麻烦。",
    },
    "sd_scripts_xpu": {
        "display_name": "SD Scripts (Intel)",
        "description": "SD Scripts 的 Intel 显卡整合包，使用 XPU 版 PyTorch，支持训练 SD1.5，SDXL，FLUX，ControlNet 等多种模型，并且是 SD-Trainer 和 Kohya GUI 的训练核心，不过操作比较麻烦。",
    },
    "ai_toolkit": {
        "display_name": "AI Toolkit (NVIDIA)",
        "description": "AI Toolkit 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，易用的一体化扩散模型训练工具，支持图像和视频模型训练。",
    },
    "ai_toolkit_rocm": {
        "display_name": "AI Toolkit (AMD)",
        "description": "AI Toolkit 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，易用的一体化扩散模型训练工具，支持图像和视频模型训练。",
    },
    "ai_toolkit_xpu": {
        "display_name": "AI Toolkit (Intel)",
        "description": "AI Toolkit 的 Intel 显卡整合包，使用 XPU 版 PyTorch，易用的一体化扩散模型训练工具，支持图像和视频模型训练。",
    },
    "finetrainers": {
        "display_name": "Finetrainers (NVIDIA)",
        "description": "Finetrainers 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，面向扩散模型训练，支持 LoRA、全量微调、分布式训练和省显存单卡训练。",
    },
    "finetrainers_rocm": {
        "display_name": "Finetrainers (AMD)",
        "description": "Finetrainers 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，面向扩散模型训练，支持 LoRA、全量微调、分布式训练和省显存单卡训练。",
    },
    "finetrainers_xpu": {
        "display_name": "Finetrainers (Intel)",
        "description": "Finetrainers 的 Intel 显卡整合包，使用 XPU 版 PyTorch，面向扩散模型训练，支持 LoRA、全量微调、分布式训练和省显存单卡训练。",
    },
    "diffusion_pipe": {
        "display_name": "Diffusion Pipe (NVIDIA)",
        "description": "Diffusion Pipe 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，面向扩散模型的流水线并行训练，适合训练单张显卡放不下的大模型。",
    },
    "diffusion_pipe_rocm": {
        "display_name": "Diffusion Pipe (AMD)",
        "description": "Diffusion Pipe 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，面向扩散模型的流水线并行训练，适合训练单张显卡放不下的大模型。",
    },
    "diffusion_pipe_xpu": {
        "display_name": "Diffusion Pipe (Intel)",
        "description": "Diffusion Pipe 的 Intel 显卡整合包，使用 XPU 版 PyTorch，面向扩散模型的流水线并行训练，适合训练单张显卡放不下的大模型。",
    },
    "musubi_tuner": {
        "display_name": "Musubi Tuner (NVIDIA)",
        "description": "Musubi Tuner 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，支持训练 Hunyuan，Wan 等视频生成模型。",
    },
    "musubi_tuner_rocm": {
        "display_name": "Musubi Tuner (AMD)",
        "description": "Musubi Tuner 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，支持训练 Hunyuan，Wan 等视频生成模型。",
    },
    "musubi_tuner_xpu": {
        "display_name": "Musubi Tuner (Intel)",
        "description": "Musubi Tuner 的 Intel 显卡整合包，使用 XPU 版 PyTorch，支持训练 Hunyuan，Wan 等视频生成模型。",
    },
    "qwen_tts_webui": {
        "display_name": "Qwen TTS WebUI (NVIDIA)",
        "description": "Qwen TTS WebUI 的 NVIDIA 显卡整合包，使用 CUDA 版 PyTorch，支持使用 Qwen3 TTS 生成语音。",
    },
    "qwen_tts_webui_rocm": {
        "display_name": "Qwen TTS WebUI (AMD)",
        "description": "Qwen TTS WebUI 的 AMD 显卡整合包，使用 ROCm 版 PyTorch，支持使用 Qwen3 TTS 生成语音。",
    },
    "qwen_tts_webui_xpu": {
        "display_name": "Qwen TTS WebUI (Intel)",
        "description": "Qwen TTS WebUI 的 Intel 显卡整合包，使用 XPU 版 PyTorch，支持使用 Qwen3 TTS 生成语音。",
    },
}
"""整合包软件元数据

命名规则:
- Key 必须和整合包文件名中的 software 字段一致，例如 `sd_webui-licyk-v1.0.0.7z` 对应 `sd_webui`。
- 不带 GPU 后缀的 Key 表示 NVIDIA 显卡整合包并使用 CUDA 版 PyTorch；`_rocm` 后缀表示 AMD 显卡整合包并使用 ROCm 版 PyTorch；`_xpu` 后缀表示 Intel 显卡整合包并使用 XPU 版 PyTorch。
- 只为下载列表需要展示的产品或独立变体添加条目，不为 `_main`、`_dev`、`_sd3` 等分支细分单独添加条目，除非构建产物直接使用该标识作为 software。
- `display_name` 使用产品名加显卡厂商后缀，例如 `ComfyUI (NVIDIA)`、`ComfyUI (AMD)`、`ComfyUI (Intel)`。

描述规则:
- `description` 使用一句中文短描述，先说明这是哪个产品的哪类显卡整合包和使用的 PyTorch 类型，再补充该产品的主要定位或特点。
- NVIDIA / AMD / Intel 三类变体的产品定位描述应保持一致，只替换显卡厂商和 PyTorch 类型；确有项目特性的差异时再单独调整。
- 描述面向下载用户，避免写实现细节、分支名差异和过长功能清单。
"""


class PortableFilenameInfo(TypedDict):
    """解析后的整合包文件名信息"""

    software: str
    """整合包软件标识"""

    signature: str
    """整合包签名标识"""

    channel: PortableChannelType
    """整合包发行通道"""

    build_date: str | None
    """Nightly 构建日期"""

    version: str | None
    """Stable 版本号"""

    extension: str
    """文件扩展名"""


class PortableFileResource(TypedDict):
    """整合包文件资源"""

    filename: str
    """文件名"""

    path: str
    """仓库内文件路径"""

    url: str
    """文件下载地址"""

    signature: str
    """整合包签名标识"""

    channel: PortableChannelType
    """整合包发行通道"""

    version: str | None
    """Stable 版本号"""

    build_date: str | None
    """Nightly 构建日期"""

    extension: str
    """文件扩展名"""


class PortableSoftwareResource(TypedDict):
    """单个软件的整合包资源"""

    display_name: str
    """展示名称"""

    description: str
    """整合包描述"""

    stable: list[PortableFileResource]
    """Stable 资源列表"""

    nightly: list[PortableFileResource]
    """Nightly 资源列表"""


PortableSourceResources: TypeAlias = dict[str, PortableSoftwareResource]
"""单个下载源的整合包资源"""


class PortableListData(TypedDict):
    """整合包资源列表数据"""

    update_time: str
    """更新时间"""

    resources: dict[str, PortableSourceResources]
    """按下载源分组的整合包资源"""


class PortableRepoSourceConfig(TypedDict):
    """整合包仓库下载源配置"""

    source: PortableSourceType
    """下载源类型"""

    repo_id: str
    """仓库 ID"""

    repo_type: RepoType
    """仓库类型"""


PortableUploadTargetConfig: TypeAlias = PortableRepoSourceConfig
"""整合包上传目标配置"""


def utc_update_time() -> str:
    """获取 UTC ISO 格式更新时间

    Returns:
        str: UTC ISO 格式时间字符串
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_portable_filename(filename: str) -> PortableFilenameInfo:
    """解析整合包文件名

    Args:
        filename (str):
            整合包文件名

    Returns:
        PortableFilenameInfo: 解析后的整合包文件名信息

    Raises:
        ValueError: 文件名不符合整合包命名规则时抛出
    """
    match = PORTABLE_NAME_REGEX.match(filename)
    if match is None:
        raise ValueError(f"整合包文件名不符合规范: {filename}")

    groups = match.groupdict()
    build_date = groups.get("build_date")
    version = groups.get("version")
    channel: PortableChannelType = "nightly" if build_date is not None else "stable"
    return {
        "software": groups["software"],
        "signature": groups["signature"],
        "channel": channel,
        "build_date": build_date,
        "version": version,
        "extension": groups["extension"].lower(),
    }


def build_portable_file_resource(
    path: str,
    url: str,
) -> tuple[str, PortableFileResource]:
    """构建整合包文件资源

    Args:
        path (str):
            仓库内文件路径
        url (str):
            文件下载地址

    Returns:
        tuple[str, PortableFileResource]: 软件标识和文件资源

    Raises:
        ValueError: 文件名不符合整合包命名规则时抛出
    """
    filename = Path(path).name
    info = parse_portable_filename(filename)
    return info["software"], {
        "filename": filename,
        "path": path,
        "url": url,
        "signature": info["signature"],
        "channel": info["channel"],
        "version": info["version"],
        "build_date": info["build_date"],
        "extension": info["extension"],
    }


def normalize_portable_path_in_repo(
    path_in_repo: str | None = DEFAULT_PORTABLE_PATH_IN_REPO,
) -> str:
    """规范化整合包仓库目录

    Args:
        path_in_repo (str | None):
            仓库中的整合包目录, 为空字符串时不限制目录

    Returns:
        str: 规范化后的仓库目录

    Raises:
        ValueError: 路径包含父目录引用时抛出
    """
    if path_in_repo is None:
        return ""

    parts = []
    for part in path_in_repo.replace("\\", "/").strip("/").split("/"):
        if part in ["", "."]:
            continue
        if part == "..":
            raise ValueError("整合包仓库目录不能包含 '..'")
        parts.append(part)
    return "/".join(parts)


def filter_portable_paths(
    paths: list[str],
    path_in_repo: str | None = DEFAULT_PORTABLE_PATH_IN_REPO,
) -> list[str]:
    """筛选有效整合包路径

    Args:
        paths (list[str]):
            仓库文件路径列表
        path_in_repo (str | None):
            仓库中的整合包目录, 为空字符串时不限制目录

    Returns:
        list[str]: 有效整合包路径列表
    """
    normalized_path_in_repo = normalize_portable_path_in_repo(path_in_repo)
    path_prefix = f"{normalized_path_in_repo}/" if normalized_path_in_repo else ""
    portable_paths = []
    for path in paths:
        if path_prefix and not path.startswith(path_prefix):
            continue
        try:
            parse_portable_filename(Path(path).name)
        except ValueError as e:
            logger.warning("%s", e)
            continue
        portable_paths.append(path)
    return portable_paths


def collect_portable_files_from_repo(
    manager: RepoManager,
    source: PortableSourceType,
    repo_id: str,
    repo_type: RepoType = "model",
    revision: str | None = None,
    path_in_repo: str | None = DEFAULT_PORTABLE_PATH_IN_REPO,
) -> list[PortableFileResource]:
    """从仓库收集整合包文件资源

    Args:
        manager (RepoManager):
            仓库管理器
        source (PortableSourceType):
            下载源类型
        repo_id (str):
            仓库 ID
        repo_type (RepoType):
            仓库类型
        revision (str | None):
            仓库分支、标签或提交哈希
        path_in_repo (str | None):
            仓库中的整合包目录, 为空字符串时不限制目录

    Returns:
        list[PortableFileResource]: 整合包文件资源列表
    """
    repo_files = manager.get_repo_file(
        api_type=source,
        repo_id=repo_id,
        repo_type=repo_type,
        revision=revision,
    )
    portable_files = []
    for path in filter_portable_paths(repo_files, path_in_repo=path_in_repo):
        url = manager.get_repo_file_download_url(
            api_type=source,
            repo_id=repo_id,
            file_path=path,
            repo_type=repo_type,
            revision=revision,
        )
        _, resource = build_portable_file_resource(path=path, url=url)
        portable_files.append(resource)
    return portable_files


def build_portable_source_resources(
    files: list[PortableFileResource],
) -> PortableSourceResources:
    """按软件标识构建下载源资源

    Args:
        files (list[PortableFileResource]):
            整合包文件资源列表

    Returns:
        PortableSourceResources: 按软件标识分组的下载源资源
    """
    grouped: PortableSourceResources = {}
    for file in files:
        software = parse_portable_filename(file["filename"])["software"]
        if software not in grouped:
            metadata = PORTABLE_SOFTWARE_METADATA.get(
                software,
                {
                    "display_name": software,
                    "description": "",
                },
            )
            grouped[software] = {
                "display_name": metadata["display_name"],
                "description": metadata["description"],
                "stable": [],
                "nightly": [],
            }
        grouped[software][file["channel"]].append(file)

    result: PortableSourceResources = {}
    for software in sorted(grouped):
        resource = grouped[software]
        resource["stable"] = sort_portable_files(resource["stable"])
        resource["nightly"] = sort_portable_files(resource["nightly"])
        result[software] = resource
    return result


def sort_portable_files(
    files: list[PortableFileResource],
) -> list[PortableFileResource]:
    """排序整合包文件资源

    Args:
        files (list[PortableFileResource]):
            整合包文件资源列表

    Returns:
        list[PortableFileResource]: 排序后的整合包文件资源列表
    """

    def _compare(left: PortableFileResource, right: PortableFileResource) -> int:
        left_version = left["version"] if left["version"] is not None else left["build_date"] or "0"
        right_version = right["version"] if right["version"] is not None else right["build_date"] or "0"
        version_cmp = CommonVersionComparison(left_version).compare_versions(left_version, right_version)
        if version_cmp != 0:
            return -version_cmp
        if left["filename"] < right["filename"]:
            return -1
        if left["filename"] > right["filename"]:
            return 1
        return 0

    return sorted(files, key=cmp_to_key(_compare))


def build_portable_list_data(
    resources: dict[PortableSourceType, list[PortableFileResource]],
    update_time: str | None = None,
) -> PortableListData:
    """构建整合包资源列表数据

    Args:
        resources (dict[PortableSourceType, list[PortableFileResource]]):
            按下载源分组的文件资源
        update_time (str | None):
            更新时间, 未指定时使用当前 UTC 时间

    Returns:
        PortableListData: 整合包资源列表数据
    """
    output_resources: dict[str, PortableSourceResources] = {}
    for source in PORTABLE_SOURCE_TYPE_LIST:
        source_files = resources.get(source)
        if source_files is None:
            continue
        output_resources[source] = build_portable_source_resources(source_files)

    return {
        "update_time": update_time or utc_update_time(),
        "resources": output_resources,
    }


def build_portable_list_from_repositories(
    manager: RepoManager,
    sources: list[PortableRepoSourceConfig],
    revision: str | None = None,
    update_time: str | None = None,
    path_in_repo: str | None = DEFAULT_PORTABLE_PATH_IN_REPO,
) -> PortableListData:
    """从仓库构建整合包资源列表数据

    Args:
        manager (RepoManager):
            仓库管理器
        sources (list[PortableRepoSourceConfig]):
            仓库下载源配置列表
        revision (str | None):
            仓库分支、标签或提交哈希
        update_time (str | None):
            更新时间, 未指定时使用当前 UTC 时间
        path_in_repo (str | None):
            仓库中的整合包目录, 为空字符串时不限制目录

    Returns:
        PortableListData: 整合包资源列表数据

    Raises:
        ValueError: 下载源配置为空时抛出
    """
    if not sources:
        raise ValueError("至少需要配置一个整合包下载源")

    resources: dict[PortableSourceType, list[PortableFileResource]] = {}
    for source in sources:
        resources[source["source"]] = collect_portable_files_from_repo(
            manager=manager,
            source=source["source"],
            repo_id=source["repo_id"],
            repo_type=source["repo_type"],
            revision=revision,
            path_in_repo=path_in_repo,
        )
    return build_portable_list_data(resources=resources, update_time=update_time)


def _portable_target_name(target: PortableUploadTargetConfig) -> str:
    """获取上传目标的日志展示名称"""
    return f"{target['source']}:{target['repo_id']} ({target['repo_type']})"


def upload_portable_package_to_repositories(
    manager: RepoManager,
    upload_path: Path,
    targets: list[PortableUploadTargetConfig],
    revision: str | None = None,
    path_in_repo: str | None = None,
    visibility: bool = False,
    num_threads: int = 1,
    target_workers: int | None = None,
) -> None:
    """上传整合包目录到多个 HuggingFace / ModelScope 仓库

    Args:
        manager (RepoManager):
            仓库管理器
        upload_path (Path):
            要上传的本地目录
        targets (list[PortableUploadTargetConfig]):
            上传目标配置列表
        revision (str | None):
            上传目标分支、标签或提交哈希
        path_in_repo (str | None):
            仓库中的上传路径前缀, 为`None`时上传到仓库根目录
        visibility (bool):
            创建仓库时是否设为公开
        num_threads (int):
            单个目标仓库内部的上传线程数
        target_workers (int | None):
            上传目标之间的并发数, 未指定时按目标数量并发

    Raises:
        FileNotFoundError: 上传路径不是目录时抛出
        ValueError: 上传目标配置为空时抛出
        AggregateError: 任一上传目标最终失败时抛出
    """
    if not upload_path.is_dir():
        raise FileNotFoundError(f"整合包上传目录不存在: {upload_path}")
    if not targets:
        raise ValueError("至少需要配置一个整合包上传目标")

    upload_targets = list(targets)
    upload_threads = max(1, num_threads)
    max_workers = max(1, target_workers if target_workers is not None else len(upload_targets))
    errors: list[Exception] = []

    def _upload_target(target: PortableUploadTargetConfig) -> None:
        target_name = _portable_target_name(target)
        logger.info("开始上传整合包到 %s", target_name)
        manager.upload_files_to_repo(
            api_type=target["source"],
            repo_id=target["repo_id"],
            upload_path=upload_path,
            path_in_repo=path_in_repo,
            repo_type=target["repo_type"],
            visibility=visibility,
            num_threads=upload_threads,
            revision=revision,
        )
        logger.info("整合包上传到 %s 完成", target_name)

    def _record_error(target: PortableUploadTargetConfig, exc: Exception) -> None:
        target_name = _portable_target_name(target)
        logger.error("整合包上传到 %s 失败: %s", target_name, exc)
        target_error = RuntimeError(f"{target_name} 上传失败: {exc}")
        target_error.__cause__ = exc
        errors.append(target_error)

    if max_workers == 1:
        for target in upload_targets:
            try:
                _upload_target(target)
            except Exception as exc:
                _record_error(target, exc)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_target = {executor.submit(_upload_target, target): target for target in upload_targets}
            for future in as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    future.result()
                except Exception as exc:
                    _record_error(target, exc)

    if errors:
        raise AggregateError("上传整合包时发生错误", errors)


def save_portable_list(
    data: PortableListData,
    output: Path,
) -> None:
    """保存整合包资源列表数据

    Args:
        data (PortableListData):
            整合包资源列表数据
        output (Path):
            输出文件路径
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
