"""ONNXRuntime GPU 版本类型"""

from enum import Enum


class OrtType(str, Enum):
    """ONNXRuntime GPU 的类型

    版本说明:
    - CU130: CU13.x
    - CU121CUDNN8: CUDA 12.1 + cuDNN8
    - CU121CUDNN9: CUDA 12.1 + cuDNN9
    - CU118: CUDA 11.8

    PyPI 中 1.19.0 及之后的版本为 CUDA 12.x 的,
    1.27.0 及之后的版本为 CUDA 13.x 的

    Attributes:
        CU130 (str): CUDA 13.x 版本的 ONNXRuntime GPU
        CU121CUDNN8 (str): CUDA 12.1 + cuDNN 8 版本的 ONNXRuntime GPU
        CU121CUDNN9 (str): CUDA 12.1 + cuDNN 9 版本的 ONNXRuntime GPU
        CU118 (str): CUDA 11.8 版本的 ONNXRuntime GPU
    """

    CU130 = "cu130"
    CU121CUDNN8 = "cu121cudnn8"
    CU121CUDNN9 = "cu121cudnn9"
    CU118 = "cu118"

    def __str__(self) -> str:
        return self.value
