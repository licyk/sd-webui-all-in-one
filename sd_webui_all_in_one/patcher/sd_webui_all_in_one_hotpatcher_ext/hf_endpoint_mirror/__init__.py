"""基于 HF_ENDPOINT 的 Hugging Face 镜像补丁"""

from .config import (
    apply_from_config,
)
from .download import (
    compare_sha256,
    load_file_from_url,
)
from .patches import (
    apply_mirror,
    patch_comfyui_manager_model_downloads,
    patch_comfyui_wd14_tagger,
    patch_sd_webui_load_file_from_url,
    patch_torchhub,
    patch_torchvision,
)
from .urls import (
    HUGGINGFACE_URL_PATTERN,
    rewrite_huggingface_url,
)

__all__ = [
    "HUGGINGFACE_URL_PATTERN",
    "apply_from_config",
    "apply_mirror",
    "compare_sha256",
    "load_file_from_url",
    "patch_comfyui_manager_model_downloads",
    "patch_comfyui_wd14_tagger",
    "patch_sd_webui_load_file_from_url",
    "patch_torchhub",
    "patch_torchvision",
    "rewrite_huggingface_url",
]
