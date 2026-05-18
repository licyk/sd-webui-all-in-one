"""优化模块"""

from sd_webui_all_in_one.optimize.tcmalloc import (
    TCMalloc,
    TCMallocInfo,
    set_tcmalloc,
    apply_tcmalloc_preload,
    get_tcmalloc_path,
    get_tcmalloc_var,
    get_tcmalloc_info,
)
from sd_webui_all_in_one.optimize.cuda_malloc import (
    set_cuda_malloc,
    apply_pytorch_alloc_conf,
    get_cuda_malloc_var,
)

__all__ = [
    "TCMalloc",
    "TCMallocInfo",
    "set_tcmalloc",
    "apply_tcmalloc_preload",
    "get_tcmalloc_path",
    "get_tcmalloc_var",
    "get_tcmalloc_info",
    "set_cuda_malloc",
    "apply_pytorch_alloc_conf",
    "get_cuda_malloc_var",
]
