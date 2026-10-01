"""ONNXRuntime GPU 与 PyTorch 的 CUDA 版本查询"""

import multiprocessing
from multiprocessing.queues import Queue

from sd_webui_all_in_one.utils import load_source_directly
from sd_webui_all_in_one.env_check.shared import logger


def get_onnxruntime_support_cuda_version() -> tuple[str | None, str | None]:
    """获取 onnxruntime 支持的 CUDA, cuDNN 版本

    Returns:
        (tuple[str | None, str | None]): onnxruntime 支持的 CUDA, cuDNN 版本
    """
    ver1 = load_source_directly("onnxruntime.capi.version_info") or {}
    ver2 = load_source_directly("onnxruntime.capi.build_and_package_info") or {}
    cuda_ver = ver1.get("cuda_version") or ver2.get("cuda_version")
    cuddn_ver = ver1.get("cudnn_version")
    return cuda_ver, cuddn_ver


def get_torch_version_worker(
    result_queue: Queue,
) -> None:
    """在子进程中执行的任务函数, 用于获取 Torch 版本信息

    Args:
        result_queue (Queue): 用于返回结果的多进程队列
    """
    try:
        import torch
        import torch.version

        torch_ver = str(torch.__version__) if hasattr(torch, "__version__") else None
        cuda_ver = str(torch.version.cuda) if hasattr(torch.version, "cuda") else None

        # 获取 cuDNN 版本
        try:
            cudnn_ver = str(torch.backends.cudnn.version())
        except Exception:
            cudnn_ver = None

        result_queue.put((torch_ver, cuda_ver, cudnn_ver))
    except ImportError as e:
        logger.debug("Torch 未安装: %s", e)
        result_queue.put((None, None, None))
    except Exception as e:
        # 导入 torch 可能因环境损坏抛出任意异常, 此时返回空值, 但需要提示用户
        logger.warning("导入 Torch 时发生错误, 无法获取 Torch 版本信息: %s", e)
        result_queue.put((None, None, None))


def get_torch_cuda_ver_subprocess() -> tuple[str | None, str | None, str | None]:
    """获取 Torch 的本体, CUDA, cuDNN 版本 (通过子进程隔离)

    为了防止 torch 模块加载后无法从内存中彻底卸载, 以及避免其占用显存

    此处通过开辟一个独立的子进程来完成版本检查工作

    Returns:
        (tuple[str | None, str | None, str | None]): Torch, CUDA, cuDNN 版本
    """
    # 使用 'spawn' 模式创建上下文, 确保子进程拥有完全独立的内存空间
    ctx = multiprocessing.get_context("spawn")
    result_queue = ctx.Queue()

    # 创建子进程
    process = ctx.Process(target=get_torch_version_worker, args=(result_queue,), name="TorchVersionChecker")

    torch_ver, cuda_ver, cudnn_ver = None, None, None

    try:
        logger.debug("启动子进程检查 Torch 版本")
        process.start()

        # 等待子进程返回结果, 设置 100 秒超时防止意外卡死
        # 获取结果后, 子进程的任务就完成了
        torch_ver, cuda_ver, cudnn_ver = result_queue.get(timeout=100)

        process.join()
    except Exception as e:
        logger.warning("通过子进程获取 Torch 版本失败: %s", e)
    finally:
        if process.is_alive():
            process.terminate()  # 如果还活着, 强制终止
            process.join()  # 终止后必须 join 释放僵尸进程资源
        process.close()  # 确保进程资源被回收

    logger.debug("子进程返回结果 - Torch: %s, CUDA: %s, cuDNN: %s", torch_ver, cuda_ver, cudnn_ver)
    return torch_ver, cuda_ver, cudnn_ver


def get_torch_cuda_ver() -> tuple[str | None, str | None, str | None]:
    """获取 Torch 的本体, CUDA, cuDNN 版本

    Returns:
        (tuple[str | None, str | None, str | None]): Torch, CUDA, cuDNN 版本
    """
    try:
        import torch
        import torch.version

        torch_ver = torch.__version__
        cuda_ver = torch.version.cuda
        cudnn_ver = torch.backends.cudnn.version()
        return (
            str(torch_ver) if torch_ver is not None else None,
            str(cuda_ver) if cuda_ver is not None else None,
            str(cudnn_ver) if cudnn_ver is not None else None,
        )
    except ImportError as e:
        logger.debug("Torch 未安装: %s", e)
        return None, None, None
    except Exception as e:
        # 导入 torch 可能因环境损坏抛出任意异常, 此时返回空值, 但需要提示用户
        logger.warning("导入 Torch 时发生错误, 无法获取 Torch 版本信息: %s", e)
        return None, None, None


def get_torch_cuda_ver_fast() -> tuple[str | None, str | None]:
    """快速获取 Torch 的本体和 CUDA 版本

    不导入 torch 主包, 避免为获取版本信息触发较慢的初始化逻辑。

    Returns:
        (tuple[str | None, str | None]): Torch, CUDA 版本
    """
    torch_data = load_source_directly("torch.version") or {}
    torch_ver: str | None = torch_data.get("__version__")
    cuda_ver: str | None = torch_data.get("cuda")
    return (torch_ver, cuda_ver)
