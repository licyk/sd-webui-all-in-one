"""其他工具合集"""

from typing import Any
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL


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
        elif shell.__class__.__name__ == "TerminalInteractiveShell":
            return False
        else:
            return False
    except NameError:
        # 没有 get_ipython, 不是 Jupyter
        return False


def clear_up() -> bool:
    """清理 Jupyter Notebook 输出内容

    Returns:
        bool: 清理输出结果
    """
    try:
        from IPython.display import clear_output

        clear_output(wait=False)
        return True
    except Exception as e:
        logger.error("清理 Jupyter Notebook 输出内容失败: %s", e)
        return False


def check_gpu() -> bool:
    """检查环境中是否有可用的 GPU

    Returns:
        bool: 当有可用 GPU 时返回`True`
    """
    logger.info("检查当前环境是否有 GPU 可用")
    import tensorflow as tf

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
