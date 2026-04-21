"""优化模块"""

from sd_webui_all_in_one.optimize.tcmalloc import TCMalloc
from sd_webui_all_in_one.optimize.cuda_malloc import (
    set_cuda_malloc,
    apply_pytorch_alloc_conf,
    get_cuda_malloc_var,
)

__all__ = [
    "TCMalloc",
    "set_cuda_malloc",
    "apply_pytorch_alloc_conf",
    "get_cuda_malloc_var",
]
