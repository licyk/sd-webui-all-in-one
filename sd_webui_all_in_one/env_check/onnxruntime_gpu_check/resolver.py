"""ONNXRuntime GPU 所需版本判断"""

import sys
import importlib.metadata

from sd_webui_all_in_one.package_analyzer import CommonVersionComparison
from sd_webui_all_in_one.env_check.shared import logger
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check.models import (
    OrtType,
)
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check.versions import (
    get_onnxruntime_support_cuda_version,
    get_torch_cuda_ver,
    get_torch_cuda_ver_fast,
)


def need_install_ort_ver(
    skip_if_missing: bool = True,
) -> OrtType | None:
    """判断需要安装的 onnxruntime 版本

    Args:
        skip_if_missing (bool):
            当 onnxruntime 未安装时是否跳过检查
            - `True`: 未安装时则不给出需要安装的 ONNXRuntime GPU 版本
            - `False`: 即使 ONNXRuntime GPU 未安装也给出推荐安装的 ONNXRuntime GPU 版本

    Returns:
        OrtType | None:
            需要安装的 ONNXRuntime GPU 类型, 不需要安装时返回 None
    """

    def _fallback_if_missing_torch_detail() -> OrtType | None:
        if not skip_if_missing:
            try:
                logger.debug("检查 ONNXRuntime GPU 是否已安装")
                _ = importlib.metadata.version("onnxruntime-gpu")
            except importlib.metadata.PackageNotFoundError:
                logger.debug("ONNXRuntime GPU 未安装, 使用默认版本进行安装")
                # ONNXRuntime GPU 没有安装时
                return OrtType.CU130
        logger.debug("跳过安装 ONNXRuntime GPU")
        return None

    def _get_required_cudnn_ver() -> str | None:
        _, _, cudnn_ver = get_torch_cuda_ver()
        logger.debug("按需获取 cudnn_ver: %s", cudnn_ver)
        if cudnn_ver is None:
            logger.debug("缺少 Torch cuDNN 版本")
            return None

        # onnxruntime 记录的 cuDNN 支持版本只有一位数, 所以 Torch 的 cuDNN 版本只能截取一位
        return cudnn_ver[0]

    # 检测是否安装了 Torch
    torch_ver, cuda_ver = get_torch_cuda_ver_fast()
    logger.debug("torch_ver: %s, cuda_ver: %s", torch_ver, cuda_ver)
    # 缺少 Torch / CUDA 版本时取消判断
    if torch_ver is None or cuda_ver is None:
        logger.debug("缺少 Torch / CUDA 版本")
        return _fallback_if_missing_torch_detail()

    # 检测是否安装了 ONNXRuntime GPU
    ort_support_cuda_ver, ort_support_cudnn_ver = get_onnxruntime_support_cuda_version()
    logger.debug("ort_support_cuda_ver: %s, ort_support_cudnn_ver: %s", ort_support_cuda_ver, ort_support_cudnn_ver)
    # 通常 onnxruntime 的 CUDA 版本和 cuDNN 版本会同时存在, 所以只需要判断 CUDA 版本是否存在即可
    if ort_support_cuda_ver is not None:
        # 当 onnxruntime 已安装
        logger.debug("检测到 ONNXRuntime GPU 声明的 CUDA / cuDNN 版本, 开始检测是否匹配 PyTorch 中的 CUDA / cuDNN 版本")

        # 判断 Torch 中的 CUDA 版本
        if CommonVersionComparison(cuda_ver) >= CommonVersionComparison("13.0"):
            # CUDA >= 13.0
            if CommonVersionComparison(ort_support_cuda_ver) < CommonVersionComparison("13.0"):
                return OrtType.CU130
            else:
                return None
        elif CommonVersionComparison("12.0") <= CommonVersionComparison(cuda_ver) < CommonVersionComparison("13.0"):
            # 12.0 =< CUDA < 13.0

            # 比较 onnxtuntime 支持的 CUDA 版本是否和 Torch 中所带的 CUDA 版本匹配
            if CommonVersionComparison("12.0") <= CommonVersionComparison(ort_support_cuda_ver) < CommonVersionComparison("13.0"):
                # CUDA 版本为 12.x, torch 和 ort 的 CUDA 版本匹配

                # cuDNN 版本可能不存在, 则默认版本正确
                if ort_support_cudnn_ver is None:
                    return None

                cudnn_ver = _get_required_cudnn_ver()
                if cudnn_ver is None:
                    return _fallback_if_missing_torch_detail()

                # 判断 Torch 和 onnxruntime 的 cuDNN 是否匹配
                if CommonVersionComparison(ort_support_cudnn_ver) > CommonVersionComparison(cudnn_ver):
                    # ort cuDNN 版本 > torch cuDNN 版本
                    return OrtType.CU121CUDNN8
                elif CommonVersionComparison(ort_support_cudnn_ver) < CommonVersionComparison(cudnn_ver):
                    # ort cuDNN 版本 < torch cuDNN 版本
                    return OrtType.CU121CUDNN9
                else:
                    # 版本相等, 无需重装
                    return None
            else:
                # CUDA 版本非 12.x, 不匹配
                cudnn_ver = _get_required_cudnn_ver()
                if cudnn_ver is None:
                    return _fallback_if_missing_torch_detail()

                if CommonVersionComparison(cudnn_ver) > CommonVersionComparison("8"):
                    return OrtType.CU121CUDNN9
                else:
                    return OrtType.CU121CUDNN8
        else:
            # CUDA <= 11.8
            if CommonVersionComparison(ort_support_cuda_ver) < CommonVersionComparison("12.0"):
                return None
            else:
                return OrtType.CU118
    else:
        logger.debug("未检测到 ONNXRuntime GPU 声明的 CUDA / cuDNN 版本")
        if skip_if_missing:
            return None

        logger.debug("确定需要安装的 ONNXRuntime GPU 版本")
        if sys.platform != "win32":
            # 非 Windows 平台未在 ONNXRuntime GPU 中声明支持的 CUDA 版本 (无 onnxruntime/capi/version_info.py)
            # 所以需要跳过检查, 直接给出版本
            logger.debug("非 Windows 版本, 当 ONNXRuntime GPU 未安装时给出默认版本")
            try:
                _ = importlib.metadata.version("onnxruntime-gpu")
                return None
            except importlib.metadata.PackageNotFoundError:
                # ONNXRuntime GPU 没有安装时
                return OrtType.CU130

        if CommonVersionComparison(cuda_ver) >= CommonVersionComparison("13.0"):
            # CUDA >= 13.x
            return OrtType.CU130
        elif CommonVersionComparison("12.0") <= CommonVersionComparison(cuda_ver) < CommonVersionComparison("13.0"):
            # 12.0 <= CUDA < 13.0
            cudnn_ver = _get_required_cudnn_ver()
            if cudnn_ver is None:
                return _fallback_if_missing_torch_detail()

            if CommonVersionComparison(cudnn_ver) > CommonVersionComparison("8"):
                return OrtType.CU121CUDNN9
            else:
                return OrtType.CU121CUDNN8
        else:
            # CUDA <= 11.8
            return OrtType.CU118
