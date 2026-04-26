"""CLI 其他模块"""

import argparse
import sys
import logging
import os
import time
from pathlib import Path

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
    LOGGER_COLOR,
    LOGGER_LEVEL,
    SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH,
)
from sd_webui_all_in_one.optimize import get_cuda_malloc_var
from sd_webui_all_in_one.logger import set_all_loggers_level
from sd_webui_all_in_one.tunnel import TunnelManager
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.utils import (
    print_divider,
    normalized_filepath,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


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


def start_tunnel(
    port: int,
    workspace: Path | None = None,
    use_ngrok: bool = False,
    ngrok_token: str | None = None,
    use_cloudflare: bool | None = False,
    use_remote_moe: bool | None = False,
    use_localhost_run: bool | None = False,
    use_gradio: bool | None = False,
    use_pinggy_io: bool | None = False,
    use_zrok: bool | None = False,
    zrok_token: str | None = None,
) -> None:
    """启动内网穿透

    Args:
        port (int):
            要进行端口映射的端口
        workspace (Path | None):
            工作区路径，默认为当前目录
        use_ngrok (bool | None):
            启用 Ngrok 内网穿透
        ngrok_token (str | None):
            Ngrok 账号 Token
        use_cloudflare (bool | None):
            启用 CloudFlare 内网穿透
        use_remote_moe (bool | None):
            启用 remote.moe 内网穿透
        use_localhost_run (bool | None):
            使用 localhost.run 内网穿透
        use_gradio (bool | None):
            使用 Gradio 内网穿透
        use_pinggy_io (bool | None):
            使用 pinggy.io 内网穿透
        use_zrok (bool | None):
            使用 Zrok 内网穿透
        zrok_token (str | None):
            Zrok 账号 Token
    """
    if workspace is None:
        workspace = Path.cwd()

    logger.info("启动内网穿透，端口: %s", port)
    logger.info("工作区: %s", workspace)

    try:
        with TunnelManager(workspace=workspace, port=port) as manager:
            tunnel_url = manager.start_tunnel(
                use_ngrok=use_ngrok,
                ngrok_token=ngrok_token,
                use_cloudflare=use_cloudflare,
                use_remote_moe=use_remote_moe,
                use_localhost_run=use_localhost_run,
                use_gradio=use_gradio,
                use_pinggy_io=use_pinggy_io,
                use_zrok=use_zrok,
                zrok_token=zrok_token,
                check=False,
            )

            print_divider()
            logger.info("本地地址: %s", tunnel_url["local_url"])
            logger.info("内网穿透地址:")
            for service, url in tunnel_url.items():
                if service != "local_url" and url:
                    print(f"  - {service}: {url}")
            print_divider()
            logger.info("按 Ctrl + C 停止内网穿透")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("正在停止内网穿透")
    except Exception as e:
        logger.error("启动内网穿透失败: %s", e)
        sys.exit(1)


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

    # start-tunnel
    start_tunnel_p = sd_webui_all_in_one_sub.add_parser("start-tunnel", help="启动内网穿透")
    start_tunnel_p.add_argument("port", type=int, help="要进行端口映射的端口")
    start_tunnel_p.add_argument("--workspace", type=normalized_filepath, default=SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH, help="工作区路径（默认为当前目录）")
    start_tunnel_p.add_argument("--ngrok", action="store_true", help="启用 Ngrok 内网穿透")
    start_tunnel_p.add_argument("--ngrok-token", type=str, default=None, help="Ngrok 账号 Token, 可从 https://dashboard.ngrok.com/get-started/your-authtoken 获取")
    start_tunnel_p.add_argument("--cloudflare", action="store_true", help="启用 CloudFlare 内网穿透")
    start_tunnel_p.add_argument("--remote-moe", action="store_true", help="启用 remote.moe 内网穿透")
    start_tunnel_p.add_argument("--localhost-run", action="store_true", help="启用 localhost.run 内网穿透")
    start_tunnel_p.add_argument("--gradio", action="store_true", help="启用 Gradio 内网穿透")
    start_tunnel_p.add_argument("--pinggy-io", action="store_true", help="启用 pinggy.io 内网穿透")
    start_tunnel_p.add_argument("--zrok", action="store_true", help="启用 Zrok 内网穿透")
    start_tunnel_p.add_argument("--zrok-token", type=str, default=None, help="Zrok 账号 Token, 可从 https://netfoundry.io/docs/zrok/get-started/get-token 获取")
    start_tunnel_p.set_defaults(
        func=lambda args: start_tunnel(
            port=args.port,
            workspace=args.workspace,
            use_ngrok=args.ngrok,
            ngrok_token=args.ngrok_token,
            use_cloudflare=args.cloudflare,
            use_remote_moe=args.remote_moe,
            use_localhost_run=args.localhost_run,
            use_gradio=args.gradio,
            use_pinggy_io=args.pinggy_io,
            use_zrok=args.zrok,
            zrok_token=args.zrok_token,
        )
    )
