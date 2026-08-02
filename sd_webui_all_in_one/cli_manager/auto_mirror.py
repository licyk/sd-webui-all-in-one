"""CLI 自动镜像源选择工具"""

import argparse
from collections.abc import Callable
from typing import Any

from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.utils import network_gfw_test


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def add_auto_mirror_argument(
    parser: argparse.ArgumentParser,
) -> None:
    """为镜像相关子命令添加自动镜像控制参数

    Args:
        parser (argparse.ArgumentParser):
            需要添加自动镜像控制参数的 CLI 子命令解析器
    """
    parser.add_argument(
        "--no-auto-mirror",
        action="store_false",
        default=True,
        dest="auto_mirror",
        help="禁用自动镜像源选择; 默认自动模式会强制覆盖手动镜像参数",
    )


def apply_auto_mirror(
    args: argparse.Namespace,
) -> argparse.Namespace:
    """根据网络环境覆盖 CLI 镜像相关参数

    Args:
        args (argparse.Namespace):
            已解析的 CLI 参数命名空间

    Returns:
        argparse.Namespace:
            应用自动镜像选择后的 CLI 参数命名空间
    """
    if not getattr(args, "auto_mirror", True):
        logger.info("已禁用 CLI 自动镜像源选择, 将遵守手动镜像源参数设置")
        return args

    logger.info("启用 CLI 自动镜像源选择, 将根据网络检测结果强制覆盖镜像源相关参数")
    use_mirror = not network_gfw_test()
    model_resource = "modelscope" if use_mirror else "huggingface"
    if use_mirror:
        logger.info("网络检测结果: 将强制使用镜像源, 模型下载源设置为 ModelScope")
    else:
        logger.info("网络检测结果: 将强制使用官方源, 模型下载源设置为 HuggingFace")

    for attr in ("use_pypi_mirror", "use_github_mirror", "use_hf_mirror"):
        if hasattr(args, attr):
            setattr(args, attr, use_mirror)

    for attr in ("custom_github_mirror", "custom_hf_mirror"):
        if hasattr(args, attr):
            setattr(args, attr, None)

    for attr in ("model_download_resource_type", "source"):
        if hasattr(args, attr):
            setattr(args, attr, model_resource)

    return args


def with_auto_mirror(
    callback: Callable[[argparse.Namespace], Any],
) -> Callable[[argparse.Namespace], Any]:
    """包装 CLI 回调, 在执行前应用自动镜像选择

    Args:
        callback (Callable[[argparse.Namespace], Any]):
            原始 CLI 回调函数

    Returns:
        Callable[[argparse.Namespace], Any]:
            应用自动镜像选择后的 CLI 回调函数
    """

    def _wrapper(
        args: argparse.Namespace,
    ) -> Any:
        return callback(apply_auto_mirror(args))

    return _wrapper
