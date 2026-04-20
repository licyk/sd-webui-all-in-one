"""模型类型定义"""

from typing import (
    Literal,
    TypedDict,
    TypeAlias,
    get_args,
)


SupportedWebUiType: TypeAlias = Literal[
    "sd_webui",
    "comfyui",
    "invokeai",
    "fooocus",
    "sd_trainer",
    "sd_scripts",
]
"""支持的 WebUI 类型"""

SUPPORTED_WEBUI_LIST: list[str] = list(get_args(SupportedWebUiType))
"""支持的 WebUI 类型列表"""


class ModelSavePath(TypedDict, total=False):
    """保存的路径 (使用相对路径, 初始位置为 WebUI 的根目录)"""

    sd_webui: str | None
    """Stable Diffusion WebUI 模型保存路径"""

    comfyui: str | None
    """ComfyUI 模型保存路径"""

    invokeai: str | None
    """InvokeAI 模型保存路径"""

    fooocus: str | None
    """Fooocus 模型保存路径"""

    sd_trainer: str | None
    """SD Trainer 模型保存路径"""

    sd_scripts: str | None
    """SD Scripts 模型保存路径"""


class ModelDownloadUrl(TypedDict, total=False):
    """模型下载地址"""

    huggingface: str | None
    """模型下载地址 (HuggingFace)"""

    modelscope: str | None
    """模型下载地址 (ModelScope)"""


ModelDownloadUrlType: TypeAlias = Literal["huggingface", "modelscope"]
"""模型下载源类型"""

MODEL_DOWNLOAD_URL_TYPE_LIST: list[str] = list(get_args(ModelDownloadUrlType))
"""模型下载源类型列表"""


class ModelCard(TypedDict):
    """模型下载信息"""

    name: str
    """模型名称"""

    filename: str
    """模型的保存名字"""

    url: ModelDownloadUrl
    """模型下载链接"""

    dtype: str
    """模型的类型"""

    supported_webui: SupportedWebUiType
    """支持的 WebUI 类型"""

    save_dir: ModelSavePath
    """保存的路径 (使用相对路径, 初始位置为 WebUI 的根目录)"""


ModelCardList = list[ModelCard]
"""模型下载信息列表"""
