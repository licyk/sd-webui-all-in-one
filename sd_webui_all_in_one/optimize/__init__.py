"""优化模块"""

from sd_webui_all_in_one.optimize.cuda_malloc import (
    apply_pytorch_alloc_conf,
    get_cuda_malloc_var,
    set_cuda_malloc,
)
from sd_webui_all_in_one.optimize.tcmalloc import (
    TCMalloc,
    TCMallocInfo,
    apply_tcmalloc_preload,
    get_tcmalloc_info,
    get_tcmalloc_path,
    get_tcmalloc_var,
    set_tcmalloc,
)

__all__ = [
    "TCMalloc",
    "TCMallocInfo",
    "apply_pytorch_alloc_conf",
    "apply_tcmalloc_preload",
    "get_cuda_malloc_var",
    "get_tcmalloc_info",
    "get_tcmalloc_path",
    "get_tcmalloc_var",
    "set_cuda_malloc",
    "set_tcmalloc",
]
