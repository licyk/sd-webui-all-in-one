"""xFormers CUTLASS CUDA compute capability 热补丁。"""

from .patches import (
    TARGET_CAPABILITY,
    apply_cutlass_cuda_capability_patch,
    apply_from_config,
    is_xformers_cutlass_patch_active,
    patch_xformers_cutlass_cuda_capability,
    should_patch_xformers_cutlass,
)

__all__ = [
    "TARGET_CAPABILITY",
    "apply_cutlass_cuda_capability_patch",
    "apply_from_config",
    "is_xformers_cutlass_patch_active",
    "patch_xformers_cutlass_cuda_capability",
    "should_patch_xformers_cutlass",
]
