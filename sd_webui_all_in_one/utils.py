"""其他工具合集"""

import shutil
import sys
import os
import socket
import urllib.request
import urllib.error
from typing import Any
from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    SD_WEBUI_ALL_IN_ONE_PATCHER_PATH,
    LOGGER_NAME,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def in_jupyter() -> bool:
    """检测当前环境是否在 Jupyter 中

    Returns:
        bool:
            是否在 Jupyter 中
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
        bool:
            清理输出结果
    """
    try:
        from IPython.display import clear_output

        clear_output(wait=False)
    except Exception as e:
        raise RuntimeError(f"清理 Jupyter Notebook 输出内容失败: {e}") from e


def warning_unexpected_params(
    message: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> None:
    """显示多余参数警告

    Args:
        message (str):
            提示信息
        args (tuple[Any, ...]):
            额外的位置参数
        kwargs (dict[str, Any]):
            额外的关键字参数
    """
    if args or kwargs:
        logger.warning(message)
        if args:
            logger.warning("多余的位置参数: %s", args)

        if kwargs:
            logger.warning("多余的关键字参数: %s", kwargs)

        logger.warning("请移除这些多余参数以避免引发错误")


def remove_duplicate_object_from_list(
    origin: list[Any],
) -> list[Any]:
    """对`list`进行去重

    例如: [1, 2, 3, 2] -> [1, 2, 3]

    Args:
        origin (list[Any]):
            原始的`list`

    Returns:
        list[Any]:
            去重后的`list`
    """
    return list(set(origin))


def get_sdaio_patcher_path() -> Path:
    """获取 SD WebUI All In One 补丁路径"""
    return SD_WEBUI_ALL_IN_ONE_PATCHER_PATH


def exec_from_path(
    path: Path,
) -> dict[str, Any] | None:
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
        exec(code, env)  # pylint: disable=exec-used
        return env
    except Exception:
        return None


def load_source_directly(
    module_name: str,
) -> dict[str, Any] | None:
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


def print_divider(
    char: str | None = "-",
) -> None:
    """在终端中输出一整行分隔符

    Args:
        char (str):
            输出的字符
    """
    columns = shutil.get_terminal_size(fallback=(80, 20)).columns
    print(char * columns)


def normalized_filepath(
    filepath: str | Path,
) -> Path:
    """将输入的路径转换为绝对路径

    Args:
        filepath (str | Path): 原始的路径
    Returns:
        Path: 绝对路径
    """
    if filepath is not None:
        filepath = Path(filepath).absolute()

    logger.debug("解析成绝对路径后的路径: '%s'", filepath)
    return filepath


def append_python_path(
    new_path: Path,
    origin_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """为环境变量中的 PYTHONPATH 环境变量追加路径

    Args:
        new_path (Path):
            追加的新路径
        origin_env (dict[str, str]):
            原始的环境变量字典

    Returns:
        (dict[str, str]):
            追加 PYTHONPATH 后的环境变量字典
    """

    if origin_env is None:
        custom_env = os.environ.copy()
    else:
        custom_env = origin_env.copy()

    if "PYTHONPATH" in custom_env and custom_env["PYTHONPATH"]:
        custom_env["PYTHONPATH"] = new_path.as_posix() + os.pathsep + custom_env["PYTHONPATH"]
    else:
        custom_env["PYTHONPATH"] = new_path.as_posix()

    return custom_env


def is_port_in_use(
    port: int,
) -> bool:
    """检测端口是否被占用

    Args:
        port (int):
            要查询的端口

    Returns:
        bool:
            端口被占用时返回 True
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("localhost", port)) == 0


def find_port(
    port: int,
) -> int:
    """寻找未被占用的服务器端口

    Args:
        port (int):
            要查询的端口

    Returns:
        int: 可用的端口
    """
    if is_port_in_use(port):
        logger.debug("%s 端口已占用, 寻找新端口", port)
        return find_port(port=port + 1)
    else:
        logger.debug("%s 端口可用", port)
        return port


def network_gfw_test(
    timeout: int | None = 3,
) -> bool:
    """检查当前网络环境是否被 GFW 阻挡

    Args:
        timeout (int | None):
            超时时间设置

    Returns:
        bool:
            当未被阻挡时则返回 True
    """
    try:
        proxy_support = urllib.request.ProxyHandler()
        opener = urllib.request.build_opener(proxy_support)
        urllib.request.install_opener(opener)
        with urllib.request.urlopen("https://www.google.com", timeout=timeout) as response:
            if response.status == 200:
                logger.debug("测试链接正常访问")
                return True
            else:
                logger.debug("测试链接访问失败: %s", response.status)
                return False
    except urllib.error.HTTPError as e:
        logger.debug("测试链接访问失败 (HTTPError): %s", e.code)
        return False
    except urllib.error.URLError as e:
        logger.debug("测试链接访问失败 (URLError): %s", e.reason)
        return False
    except Exception as e:
        logger.debug("测试链接访问失败: %s", e)
        return False
