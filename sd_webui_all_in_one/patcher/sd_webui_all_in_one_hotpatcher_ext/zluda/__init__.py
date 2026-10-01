"""ZLUDA 兼容性扩展补丁"""

from .patches import (
    apply_from_config,
    apply_torch_zluda_timer_hotfix,
    apply_zluda_compat,
    apply_zluda_library,
)

__all__ = [
    "apply_from_config",
    "apply_torch_zluda_timer_hotfix",
    "apply_zluda_compat",
    "apply_zluda_library",
]
