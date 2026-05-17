"""CLI 自动镜像源选择工具"""

import argparse
from collections.abc import Callable
from typing import Any

from sd_webui_all_in_one.utils import network_gfw_test


def add_auto_mirror_argument(
    parser: argparse.ArgumentParser,
) -> None:
    """为镜像相关子命令添加自动镜像控制参数"""
    parser.add_argument(
        "--no-auto-mirror",
        action="store_false",
        default=True,
        dest="auto_mirror",
        help="禁用自动镜像源选择, 遵守手动镜像参数设置",
    )


def apply_auto_mirror(
    args: argparse.Namespace,
) -> argparse.Namespace:
    """根据网络环境覆盖 CLI 镜像相关参数"""
    if not getattr(args, "auto_mirror", True):
        return args

    use_mirror = not network_gfw_test()
    model_resource = "modelscope" if use_mirror else "huggingface"

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
    """包装 CLI 回调, 在执行前应用自动镜像选择"""

    def _wrapper(
        args: argparse.Namespace,
    ) -> Any:
        return callback(apply_auto_mirror(args))

    return _wrapper
