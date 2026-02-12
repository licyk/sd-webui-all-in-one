"""Onnxruntime GPU 检查工具"""

import os
import sys
import multiprocessing
import importlib.metadata
from multiprocessing.queues import Queue
from enum import Enum
from pathlib import Path

from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.pkg_manager import pip_install
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR, LOGGER_NAME
from sd_webui_all_in_one.package_analyzer.ver_cmp import CommonVersionComparison
from sd_webui_all_in_one.utils import load_source_directly


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class OrtType(str, Enum):
    """onnxruntime-gpu 的类型

    版本说明:
    - CU130: CU13.x
    - CU121CUDNN8: CUDA 12.1 + cuDNN8
    - CU121CUDNN9: CUDA 12.1 + cuDNN9
    - CU118: CUDA 11.8

    PyPI 中 1.19.0 及之后的版本为 CUDA 12.x 的

    Attributes:
        CU130 (str): CUDA 13.x 版本的 onnxruntime-gpu
        CU121CUDNN8 (str): CUDA 12.1 + cuDNN 8 版本的 onnxruntime-gpu
        CU121CUDNN9 (str): CUDA 12.1 + cuDNN 9 版本的 onnxruntime-gpu
        CU118 (str): CUDA 11.8 版本的 onnxruntime-gpu
    """

    CU130 = "cu130"
    CU121CUDNN8 = "cu121cudnn8"
    CU121CUDNN9 = "cu121cudnn9"
    CU118 = "cu118"

    def __str__(self) -> str:
        return self.value


def get_onnxruntime_support_cuda_version() -> tuple[str | None, str | None]:
    """获取 onnxruntime 支持的 CUDA, cuDNN 版本

    Returns:
        (tuple[str | None, str | None]): onnxruntime 支持的 CUDA, cuDNN 版本
    """
    ver = load_source_directly("onnxruntime.capi.version_info")
    if ver is None:
        return None, None

    return ver.get("cuda_version"), ver.get("cudnn_version")


def get_torch_version_worker(result_queue: Queue) -> None:
    """在子进程中执行的任务函数，用于获取 Torch 版本信息

    Args:
        result_queue (Queue): 用于返回结果的多进程队列
    """
    try:
        import torch

        torch_ver = str(torch.__version__) if hasattr(torch, "__version__") else None
        cuda_ver = str(torch.version.cuda) if hasattr(torch.version, "cuda") else None

        # 获取 cuDNN 版本
        try:
            cudnn_ver = str(torch.backends.cudnn.version())
        except Exception:
            cudnn_ver = None

        result_queue.put((torch_ver, cuda_ver, cudnn_ver))
    except Exception:
        # 如果导入失败或发生异常，返回空值
        result_queue.put((None, None, None))


def get_torch_cuda_ver_subprocess() -> tuple[str | None, str | None, str | None]:
    """获取 Torch 的本体, CUDA, cuDNN 版本 (通过子进程隔离)

    为了防止 torch 模块加载后无法从内存中彻底卸载，以及避免其占用显存

    此处通过开辟一个独立的子进程来完成版本检查工作

    Returns:
        (tuple[str | None, str | None, str | None]): Torch, CUDA, cuDNN 版本
    """
    # 使用 'spawn' 模式创建上下文，确保子进程拥有完全独立的内存空间
    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue()

    # 创建子进程
    process = ctx.Process(target=get_torch_version_worker, args=(result_queue,), name="TorchVersionChecker")

    torch_ver, cuda_ver, cudnn_ver = None, None, None

    try:
        logger.debug("启动子进程检查 Torch 版本")
        process.start()

        # 等待子进程返回结果，设置 15 秒超时防止意外卡死
        # 获取结果后，子进程的任务就完成了
        torch_ver, cuda_ver, cudnn_ver = result_queue.get(timeout=15)

        process.join()
    except Exception as e:
        logger.debug("通过子进程获取 Torch 版本失败: %s", e)
        # 发生异常时强制终止进程
        if process.is_alive():
            process.terminate()
    finally:
        # 确保进程资源被回收
        process.close()

    logger.debug("子进程返回结果 - Torch: %s, CUDA: %s, cuDNN: %s", torch_ver, cuda_ver, cudnn_ver)
    return torch_ver, cuda_ver, cudnn_ver


def get_torch_cuda_ver() -> tuple[str | None, str | None, str | None]:
    """获取 Torch 的本体, CUDA, cuDNN 版本

    Returns:
        (tuple[str | None, str | None, str | None]): Torch, CUDA, cuDNN 版本
    """
    try:
        import torch

        torch_ver = torch.__version__
        cuda_ver = torch.version.cuda
        cudnn_ver = torch.backends.cudnn.version()
        return (
            str(torch_ver) if torch_ver is not None else None,
            str(cuda_ver) if cuda_ver is not None else None,
            str(cudnn_ver) if cudnn_ver is not None else None,
        )
    except Exception as _:
        return None, None, None


def need_install_ort_ver(skip_if_missing: bool = True) -> OrtType | None:
    """判断需要安装的 onnxruntime 版本

    Args:
        skip_if_missing (bool | None):
            当 onnxruntime 未安装时是否跳过检查
            - `True`: 未安装时则不给出需要安装的 Onnxruntime GPU 版本
            - `False`: 即使 Onnxruntime GPU 未安装也给出推荐安装的 Onnxruntime GPU 版本

    Returns:
        OrtType:
            需要安装的 onnxruntime-gpu 类型
    """
    # 检测是否安装了 Torch
    torch_ver, cuda_ver, cuddn_ver = get_torch_cuda_ver_subprocess()
    logger.debug("torch_ver: %s, cuda_ver: %s, cuddn_ver: %s", torch_ver, cuda_ver, cuddn_ver)
    # 缺少 Torch / CUDA / cuDNN 版本时取消判断
    if torch_ver is None or cuda_ver is None or cuddn_ver is None:
        logger.debug("缺少 Torch / CUDA / cuDNN 版本")
        if not skip_if_missing:
            try:
                logger.debug("检查 Onnxruntime GPU 是否已安装")
                _ = importlib.metadata.version("onnxruntime-gpu")
            except Exception:
                logger.debug("Onnxruntime GPU 未安装, 使用默认版本进行安装")
                # onnxruntime-gpu 没有安装时
                return OrtType.CU130
        logger.debug("跳过安装 Onnxruntime GPU")
        return None

    # onnxruntime 记录的 cuDNN 支持版本只有一位数, 所以 Torch 的 cuDNN 版本只能截取一位
    cuddn_ver = cuddn_ver[0]

    # 检测是否安装了 onnxruntime-gpu
    ort_support_cuda_ver, ort_support_cudnn_ver = get_onnxruntime_support_cuda_version()
    logger.debug("cuddn_ver: %s, ort_support_cuda_ver: %s, ort_support_cudnn_ver: %s", cuddn_ver, ort_support_cuda_ver, ort_support_cudnn_ver)
    # 通常 onnxruntime 的 CUDA 版本和 cuDNN 版本会同时存在, 所以只需要判断 CUDA 版本是否存在即可
    if ort_support_cuda_ver is not None:
        # 当 onnxruntime 已安装
        logger.debug("检测到 Onnxruntime GPU 声明的 CUDA / cuDNN 版本, 开始检测是否匹配 PyTorch 中的 CUDA / cuDNN 版本")

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

                # 判断 Torch 和 onnxruntime 的 cuDNN 是否匹配
                if CommonVersionComparison(ort_support_cudnn_ver) > CommonVersionComparison(cuddn_ver):
                    # ort cuDNN 版本 > torch cuDNN 版本
                    return OrtType.CU121CUDNN8
                elif CommonVersionComparison(ort_support_cudnn_ver) < CommonVersionComparison(cuddn_ver):
                    # ort cuDNN 版本 < torch cuDNN 版本
                    return OrtType.CU121CUDNN9
                else:
                    # 版本相等, 无需重装
                    return None
            else:
                # CUDA 版本非 12.x, 不匹配
                if CommonVersionComparison(cuddn_ver) > CommonVersionComparison("8"):
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
        logger.debug("未检测到 Onnxruntime GPU 声明的 CUDA / cuDNN 版本")
        if skip_if_missing:
            return None

        logger.debug("确定需要安装的 Onnxruntime GPU 版本")
        if sys.platform != "win32":
            # 非 Windows 平台未在 Onnxruntime GPU 中声明支持的 CUDA 版本 (无 onnxruntime/capi/version_info.py)
            # 所以需要跳过检查, 直接给出版本
            logger.debug("非 Windows 版本, 当 Onnxruntime GPU 未安装时给出默认版本")
            try:
                _ = importlib.metadata.version("onnxruntime-gpu")
                return None
            except Exception as _:
                # onnxruntime-gpu 没有安装时
                return OrtType.CU130

        if CommonVersionComparison(cuda_ver) >= CommonVersionComparison("13.0"):
            # CUDA >= 13.x
            return OrtType.CU130
        elif CommonVersionComparison("12.0") <= CommonVersionComparison(cuda_ver) < CommonVersionComparison("13.0"):
            # 12.0 <= CUDA < 13.0
            if CommonVersionComparison(cuddn_ver) > CommonVersionComparison("8"):
                return OrtType.CU121CUDNN9
            else:
                return OrtType.CU121CUDNN8
        else:
            # CUDA <= 11.8
            return OrtType.CU118


def check_onnxruntime_gpu(
    use_uv: bool | None = True,
    skip_if_missing: bool | None = False,
    custom_env: dict[str, str] | None = None,
) -> None:
    """检查并修复 Onnxruntime GPU 版本问题

    Args:
        use_uv (bool | None):
            是否使用 uv 安装依赖
        skip_if_missing (bool | None):
            当 onnxruntime 未安装时是否跳过检查
            - `True`: 未安装时则不给出需要安装的 Onnxruntime GPU 版本
            - `False`: 即使 Onnxruntime GPU 未安装也给出推荐安装的 Onnxruntime GPU 版本
        custom_env (dict[str, str] | None):
            环境变量字典

    Raises:
        RuntimeError:
            当修复 Onnxruntime GPU 版本问题发生错误时
    """

    def _clean_env():
        custom_env.pop("PIP_EXTRA_INDEX_URL", None)
        custom_env.pop("UV_INDEX", None)
        custom_env.pop("PIP_FIND_LINKS", None)
        custom_env.pop("UV_FIND_LINKS", None)

    logger.info("检查 Onnxruntime GPU 版本问题中")
    ver = need_install_ort_ver(skip_if_missing)
    logger.debug("需要安装的 Onnxruntime GPU 版本类型: %s", ver)
    if ver is None:
        logger.info("Onnxruntime GPU 无版本问题")
        return

    if custom_env is None:
        custom_env = os.environ.copy()

    def _uninstall_onnxruntime_gpu() -> None:
        run_cmd([Path(sys.executable).as_posix(), "-m", "pip", "uninstall", "onnxruntime-gpu", "-y"])

    try:
        # TODO: 将 onnxruntime-gpu 的 1.23.2 版本替换成实际属于 CU130 的版本
        if ver == OrtType.CU118:
            _clean_env()
            custom_env["PIP_INDEX_URL"] = "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-11/pypi/simple/"
            custom_env["UV_DEFAULT_INDEX"] = "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-11/pypi/simple/"
            _uninstall_onnxruntime_gpu()
            pip_install("onnxruntime-gpu>=1.18.1", "--no-cache-dir", use_uv=use_uv, custom_env=custom_env)
        elif ver == OrtType.CU121CUDNN9:
            _uninstall_onnxruntime_gpu()
            pip_install("onnxruntime-gpu>=1.19.0,<1.23.2", "--no-cache-dir", use_uv=use_uv)
        elif ver == OrtType.CU121CUDNN8:
            _clean_env()
            custom_env["PIP_INDEX_URL"] = "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/"
            custom_env["UV_DEFAULT_INDEX"] = "https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/onnxruntime-cuda-12/pypi/simple/"
            _uninstall_onnxruntime_gpu()
            pip_install("onnxruntime-gpu==1.17.1", "--no-cache-dir", use_uv=use_uv, custom_env=custom_env)
        elif ver == OrtType.CU130:
            # 适用于 Cuda 13.x 的 onnxruntime-gpu 未发布正式版, 所以只要安装了就不检查版本对不对
            # TODO: 发布正式版后修改该部分逻辑
            try:
                importlib.metadata.version("onnxruntime-gpu")
                logger.info("Onnxruntime GPU 无版本问题")
                return
            except Exception:
                pass
            _uninstall_onnxruntime_gpu()
            pip_install("onnxruntime-gpu>=1.23.2", "--no-cache-dir", use_uv=use_uv)
    except RuntimeError as e:
        logger.error("修复 Onnxruntime GPU 版本问题时出现错误: %s", e)
        raise RuntimeError(f"修复 Onnxrunime GPU 版本问题时发生错误: {e}") from e

    logger.info("Onnxruntime GPU 版本问题修复完成")
