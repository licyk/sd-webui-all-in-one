"""其他工具合集"""

import sys
from typing import Any
from pathlib import Path
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, SD_WEBUI_ALL_IN_ONE_PATCHER_PATH


logger = get_logger(
    name="Utils",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def in_jupyter() -> bool:
    """检测当前环境是否在 Jupyter 中

    Returns:
        bool: 是否在 Jupyter 中
    """
    try:
        shell = get_ipython()  # type: ignore
        if shell is None:
            return False
        # Jupyter Notebook 或 JupyterLab
        if shell.__class__.__name__ == "ZMQInteractiveShell":
            return True
        # IPython 终端
        if shell.__class__.__name__ == "TerminalInteractiveShell":
            return False
        return True
    except NameError:
        # 没有 get_ipython, 不是 Jupyter
        return False


def clear_jupyter_output() -> None:
    """清理 Jupyter Notebook 输出内容

    Returns:
        bool: 清理输出结果
    """
    try:
        from IPython.display import clear_output

        clear_output(wait=False)
    except Exception as e:
        raise RuntimeError(f"清理 Jupyter Notebook 输出内容失败: {e}") from e


def check_gpu() -> bool:
    """检查环境中是否有可用的 GPU

    Returns:
        bool: 当有可用 GPU 时返回`True`

    ImportError:

    """
    # TODO: 替换成 get_avaliable_pytorch_device_type() 的实现
    logger.info("检查当前环境是否有 GPU 可用")
    try:
        import tensorflow as tf
    except ImportError as e:
        raise ImportError("tensorflow 未安装, 无法检测是否有可用的 GPU") from e

    if tf.test.gpu_device_name():
        logger.info("有可用的 GPU")
        return True
    else:
        logger.error("无可用 GPU")
        return False


def warning_unexpected_params(
    message: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> None:
    """显示多余参数警告

    Args:
        message (str): 提示信息
        args (tuple[Any, ...]): 额外的位置参数
        kwargs (dict[str, Any]): 额外的关键字参数
    """
    if args or kwargs:
        logger.warning(message)
        if args:
            logger.warning("多余的位置参数: %s", args)

        if kwargs:
            logger.warning("多余的关键字参数: %s", kwargs)

        logger.warning("请移除这些多余参数以避免引发错误")


def remove_duplicate_object_from_list(origin: list[Any]) -> list[Any]:
    """对`list`进行去重

    例如: [1, 2, 3, 2] -> [1, 2, 3]

    Args:
        origin (list[Any]): 原始的`list`

    Returns:
        list[Any]: 去重后的`list`
    """
    return list(set(origin))


def get_sdaio_patcher_path() -> Path:
    """获取 SD WebUI All In One 补丁路径"""
    return SD_WEBUI_ALL_IN_ONE_PATCHER_PATH


def exec_from_path(path: Path) -> dict[str, Any] | None:
    """读取并执行指定路径的 Python 文件, 返回其全局命名空间

    Args:
        path (Path):
            Python 源代码文件的路径

    Returns:
        (dict[str, Any] | None):
            - 如果执行成功, 返回包含该脚本全局变量、函数和类的字典
            - 如果读取或执行过程中发生任何错误, 返回 None
    """
    env: dict[str, Any] = {}
    try:
        code = path.read_text(encoding="utf-8")
        exec(code, env) # pylint: disable=exec-used
        return env
    except Exception:
        return None


def load_source_directly(module_name: str) -> dict[str, Any] | None:
    """在 sys.path 中搜索并直接加载指定的模块源码

    Args:
        module_name (str):
            模块全名, 例如 "tools.utils"

    Returns:
        (dict[str, Any] | None):
            - 如果找到并成功执行了对应的 .py 文件，返回其命名空间字典；
            - 如果在所有搜索路径中均未找到或执行失败, 返回 None
    """
    module_parts = module_name.split(".")
    relative_module_path = Path(*module_parts).with_suffix(".py")

    for search_path in sys.path:
        full_path = Path(search_path) / relative_module_path
        if full_path.is_file():
            return exec_from_path(full_path)

    return None
