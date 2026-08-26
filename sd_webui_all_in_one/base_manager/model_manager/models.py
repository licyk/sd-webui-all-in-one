"""Implementation grouped from the former ``model_manager.py`` module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

WebUiModelType: TypeAlias = Literal[
    "sd_webui",
    "comfyui",
    "fooocus",
    "sd_trainer",
    "sd_scripts",
    "invokeai",
]

FileWebUiModelType: TypeAlias = Literal[
    "sd_webui",
    "comfyui",
    "fooocus",
    "sd_trainer",
    "sd_scripts",
]

FILE_MODEL_ROOT_DIRS: dict[FileWebUiModelType, str] = {
    "sd_webui": "models",
    "comfyui": "models",
    "fooocus": "models",
    "sd_trainer": "sd-models",
    "sd_scripts": "sd-models",
}

WEBUI_MODEL_TITLES: dict[WebUiModelType, str] = {
    "sd_webui": "Stable Diffusion WebUI",
    "comfyui": "ComfyUI",
    "fooocus": "Fooocus",
    "sd_trainer": "SD Trainer",
    "sd_scripts": "SD Scripts",
    "invokeai": "InvokeAI",
}


@dataclass(frozen=True, slots=True)
class ModelRoot:
    """WebUI 模型根目录信息"""

    webui_type: WebUiModelType
    webui_path: Path
    root_path: Path


@dataclass(frozen=True, slots=True)
class ModelEntry:
    """模型目录中的一个条目"""

    name: str
    path: Path
    relative_path: str
    is_dir: bool
    size: int
    modified_time: float
