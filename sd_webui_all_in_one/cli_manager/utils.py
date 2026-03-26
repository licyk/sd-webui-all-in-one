"""CLI 其他模块"""

import argparse
import sys
import logging
import os

from sd_webui_all_in_one.proxy import (
    get_system_proxy_address,
    test_proxy_connectivity,
)
from sd_webui_all_in_one.updater import (
    check_aria2_version,
    check_and_update_uv,
    check_and_update_pip,
)
from sd_webui_all_in_one.mirror_manager import get_pypi_mirror_config
from sd_webui_all_in_one.config import (
    SD_WEBUI_ALL_IN_ONE_PATCHER_PATH,
    LOGGER_NAME,
)
from sd_webui_all_in_one.optimize.cuda_malloc import get_cuda_malloc_var
from sd_webui_all_in_one.logger import set_all_loggers_level


def check_pip(
    use_pypi_mirror: bool | None = False,
) -> None:
    """检查 Pip 版本并尝试更新"""
    check_and_update_pip(
        custom_env=get_pypi_mirror_config(use_cn_mirror=use_pypi_mirror),
    )


def check_uv(
    use_pypi_mirror: bool | None = False,
) -> None:
    """检查 uv 版本并尝试更新"""
    check_and_update_uv(
        custom_env=get_pypi_mirror_config(use_cn_mirror=use_pypi_mirror),
    )


def check_aria2() -> None:
    """检查 Aria2 是否需要更新"""
    if check_aria2_version():
        sys.exit(1)
    else:
        sys.exit(0)


def get_patcher_path() -> None:
    """获取 SD WebUI All In One 补丁路径"""
    print(SD_WEBUI_ALL_IN_ONE_PATCHER_PATH)


def get_proxy() -> None:
    """获取当前系统中的代理地址"""
    addr = get_system_proxy_address()
    if addr is not None and test_proxy_connectivity(addr):
        print(addr)


def get_cuda_malloc() -> None:
    """获取支持当前设备的 CUDA 内存分配器配置"""
    from sd_webui_all_in_one import config

    config.LOGGER_LEVEL = logging.CRITICAL
    set_all_loggers_level(
        level=logging.CRITICAL,
        prefix=LOGGER_NAME if LOGGER_NAME is not None else "sd_webui_all_in_one",
    )
    conf = get_cuda_malloc_var()
    if conf is not None:
        print(conf)


def get_env_config() -> None:
    """获取 SD WebUI All In One 使用的环境变量信息"""
    env = [
        "SD_WEBUI_ALL_IN_ONE_LOGGER_NAME",
        "SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL",
        "SD_WEBUI_ALL_IN_ONE_LOGGER_COLOR",
        "SD_WEBUI_ALL_IN_ONE_RETRY_TIMES",
        "SD_WEBUI_ALL_IN_ONE_PATCHER",
        "SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH",
        "SD_WEBUI_ROOT",
        "COMFYUI_ROOT",
        "FOOOCUS_ROOT",
        "INVOKEAI_ROOT",
        "SD_TRAINER_ROOT",
        "SD_SCRIPTS_ROOT",
        "QWEN_TTS_WEBUI_ROOT",
        "SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR",
        "SD_WEBUI_ALL_IN_ONE_PROXY",
        "SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH",
        "SD_WEBUI_ALL_IN_ONE_SET_CONFIG",
        "SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY",
        "SD_WEBUI_ALL_IN_ONE_RAISE_WEBUI_RUNTIME_ERROR",
        "SD_WEBUI_ALL_IN_ONE_RAISE_CHECK_ENV_ERROR_ON_LAUNCH",
    ]
    for e in env:
        print(f"{e}: '{os.getenv(e)}'")


def register_manager(
    subparsers: "argparse._SubParsersAction",
) -> None:
    """注册 SD WebUI All In One 模块及其子命令

    Args:
        subparsers (argparse._SubParsersAction):
            子命令行解析器
    """
    sd_webui_all_in_one_parser: argparse.ArgumentParser = subparsers.add_parser("self-manager", help="SD WebUI All In One 相关命令")
    sd_webui_all_in_one_sub = sd_webui_all_in_one_parser.add_subparsers(dest="sd_webui_all_in_one_action", required=True)

    # check-aria2
    check_aria2_p = sd_webui_all_in_one_sub.add_parser("check-aria2", help="检查 Aria2 是否需要更新 (当退出代码非 0 时则说明需要更新)")
    check_aria2_p.set_defaults(func=lambda args: check_aria2())

    # check-pip
    check_pip_p = sd_webui_all_in_one_sub.add_parser("check-pip", help="检查 Pip 是否需要更新并尝试更新")
    check_pip_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    check_pip_p.set_defaults(
        func=lambda args: check_pip(
            use_pypi_mirror=args.use_pypi_mirror,
        )
    )

    # check-uv
    check_uv_p = sd_webui_all_in_one_sub.add_parser("check-uv", help="检查 uv 是否需要更新并尝试更新")
    check_uv_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    check_uv_p.set_defaults(
        func=lambda args: check_uv(
            use_pypi_mirror=args.use_pypi_mirror,
        )
    )

    # get-patcher
    get_patcher_p = sd_webui_all_in_one_sub.add_parser("get-patcher", help="获取 SD WebUI All In One 补丁路径")
    get_patcher_p.set_defaults(
        func=lambda args: get_patcher_path(),
    )

    # get-proxy
    get_proxy_p = sd_webui_all_in_one_sub.add_parser("get-proxy", help="获取系统代理地址")
    get_proxy_p.set_defaults(func=lambda args: get_proxy())

    # get-cuda-malloc
    get_cuda_malloc_p = sd_webui_all_in_one_sub.add_parser("get-cuda-malloc", help="获取支持当前设备的 CUDA 内存分配器配置")
    get_cuda_malloc_p.set_defaults(func=lambda args: get_cuda_malloc())

    # get-env-config
    get_env_config_p = sd_webui_all_in_one_sub.add_parser("get-env-config", help="获取 SD WebUI All In One 使用的环境变量配置")
    get_env_config_p.set_defaults(func=lambda args: get_env_config())
