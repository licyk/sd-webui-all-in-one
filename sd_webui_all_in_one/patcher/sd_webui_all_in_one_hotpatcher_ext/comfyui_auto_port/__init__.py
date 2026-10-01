"""ComfyUI 默认端口自动避让热补丁。"""

from .patches import (
    TARGET_MODULE,
    adjust_comfyui_default_port,
    apply_from_config,
    is_comfyui_auto_port_patch_registered,
    patch_comfyui_auto_port,
)

__all__ = [
    "TARGET_MODULE",
    "adjust_comfyui_default_port",
    "apply_from_config",
    "is_comfyui_auto_port_patch_registered",
    "patch_comfyui_auto_port",
]
