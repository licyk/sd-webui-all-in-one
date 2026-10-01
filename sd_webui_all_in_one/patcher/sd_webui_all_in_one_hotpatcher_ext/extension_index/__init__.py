"""扩展索引镜像补丁"""

from .config import (
    apply_from_config,
)
from .constants import (
    A1111_EXTENSION_INDEX_AUTO,
    A1111_EXTENSION_INDEX_RAW_FILE_PATH,
    A1111_EXTENSION_INDEX_URLS,
    COMFYUI_MANAGER_RAW_FILE_PATH,
    COMFYUI_MANAGER_RAW_PREFIX,
)
from .mirror import (
    resolve_a1111_extension_index_url,
    resolve_comfyui_manager_channel_prefix,
)
from .patches import (
    patch_extension_index_a1111,
    patch_extension_index_comfyui_manager,
)

__all__ = [
    "A1111_EXTENSION_INDEX_AUTO",
    "A1111_EXTENSION_INDEX_RAW_FILE_PATH",
    "A1111_EXTENSION_INDEX_URLS",
    "COMFYUI_MANAGER_RAW_FILE_PATH",
    "COMFYUI_MANAGER_RAW_PREFIX",
    "apply_from_config",
    "patch_extension_index_a1111",
    "patch_extension_index_comfyui_manager",
    "resolve_a1111_extension_index_url",
    "resolve_comfyui_manager_channel_prefix",
]
