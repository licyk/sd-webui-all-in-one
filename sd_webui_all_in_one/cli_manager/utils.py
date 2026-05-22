"""CLI 其他模块"""

import argparse
import json
import sys
import os
import time
from pathlib import Path

from sd_webui_all_in_one.proxy import (
    get_system_proxy_address,
    test_proxy_connectivity,
)
from sd_webui_all_in_one import config as app_config
from sd_webui_all_in_one.updater import (
    check_aria2_version,
    check_and_update_uv,
    check_and_update_pip,
)
from sd_webui_all_in_one.cli_manager.auto_mirror import (
    add_auto_mirror_argument,
    with_auto_mirror,
)
from sd_webui_all_in_one.mirror_manager import get_pypi_mirror_config
from sd_webui_all_in_one.config import (
    LOGGER_NAME,
    LOGGER_COLOR,
    LOGGER_LEVEL,
    SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH,
)
from sd_webui_all_in_one.optimize import (
    get_cuda_malloc_var,
    get_tcmalloc_path,
    get_tcmalloc_var,
)
from sd_webui_all_in_one.tunnel import TunnelManager
from sd_webui_all_in_one.logger import get_logger, silence_logger_output
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
    """检查 Pip 版本并尝试更新

    Args:
        use_pypi_mirror (bool | None):
            是否使用 PyPI 国内镜像
    """
    check_and_update_pip(
        custom_env=get_pypi_mirror_config(use_cn_mirror=use_pypi_mirror),
    )


def check_uv(
    use_pypi_mirror: bool | None = False,
) -> None:
    """检查 uv 版本并尝试更新

    Args:
        use_pypi_mirror (bool | None):
            是否使用 PyPI 国内镜像
    """
    check_and_update_uv(
        custom_env=get_pypi_mirror_config(use_cn_mirror=use_pypi_mirror),
    )


def check_aria2() -> None:
    """检查 Aria2 是否需要更新"""
    if check_aria2_version():
        sys.exit(1)
    else:
        sys.exit(0)


def get_proxy() -> None:
    """获取当前系统中的代理地址"""
    addr = get_system_proxy_address()
    if addr is not None and test_proxy_connectivity(addr):
        print(addr)


def get_cuda_malloc() -> None:
    """获取支持当前设备的 CUDA 内存分配器配置"""
    silence_logger_output()
    conf = get_cuda_malloc_var()
    if conf is not None:
        print(conf)


def get_tcmalloc(
    output_path: bool | None = False,
) -> None:
    """获取支持当前系统的 TCMalloc 配置

    Args:
        output_path (bool | None):
            是否只输出可用的 TCMalloc 库路径
    """
    silence_logger_output()
    conf = get_tcmalloc_path() if output_path else get_tcmalloc_var()
    if conf is not None:
        print(conf)


def get_env_config() -> None:
    """获取 SD WebUI All In One 使用的环境变量信息"""
    env_config = {
        "SD_WEBUI_ALL_IN_ONE_LOGGER_NAME": app_config.LOGGER_NAME,
        "SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL": app_config.LOGGER_LEVEL,
        "SD_WEBUI_ALL_IN_ONE_LOGGER_COLOR": app_config.LOGGER_COLOR,
        "SD_WEBUI_ALL_IN_ONE_RETRY_TIMES": app_config.RETRY_TIMES,
        "SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH": app_config.SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH,
        "SD_WEBUI_ROOT": app_config.SD_WEBUI_ROOT_PATH,
        "COMFYUI_ROOT": app_config.COMFYUI_ROOT_PATH,
        "FOOOCUS_ROOT": app_config.FOOOCUS_ROOT_PATH,
        "INVOKEAI_ROOT": app_config.INVOKEAI_ROOT_PATH,
        "SD_TRAINER_ROOT": app_config.SD_TRAINER_ROOT_PATH,
        "SD_SCRIPTS_ROOT": app_config.SD_SCRIPTS_ROOT_PATH,
        "QWEN_TTS_WEBUI_ROOT": app_config.QWEN_TTS_WEBUI_ROOT_PATH,
        "SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR": app_config.SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR,
        "SD_WEBUI_ALL_IN_ONE_PROXY": app_config.SD_WEBUI_ALL_IN_ONE_PROXY,
        "SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH": app_config.SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH,
        "SD_WEBUI_ALL_IN_ONE_SET_CONFIG": app_config.SD_WEBUI_ALL_IN_ONE_SET_CONFIG,
        "SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY": app_config.SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY,
        "SD_WEBUI_ALL_IN_ONE_RAISE_WEBUI_RUNTIME_ERROR": app_config.SD_WEBUI_ALL_IN_ONE_RAISE_WEBUI_RUNTIME_ERROR,
        "SD_WEBUI_ALL_IN_ONE_RAISE_CHECK_ENV_ERROR_ON_LAUNCH": app_config.SD_WEBUI_ALL_IN_ONE_RAISE_CHECK_ENV_ERROR_ON_LAUNCH,
        "SD_WEBUI_ALL_IN_ONE_IGNORE_INSTALL_DEP_TYPE": app_config.SD_WEBUI_ALL_IN_ONE_IGNORE_INSTALL_DEP_TYPE,
    }
    for name, value in env_config.items():
        if isinstance(value, Path):
            value = value.as_posix()
        print(f"{name}: '{value}'")


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
        use_ngrok (bool):
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


def _print_json(data: dict | list) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def export_hotpatcher_config_cli(output: Path | None = None, force: bool = False) -> None:
    """导出 hotpatcher 默认配置

    Args:
        output (Path | None):
            配置导出路径
        force (bool):
            是否覆盖已有文件
    """

    from sd_webui_all_in_one.base_manager.hotpatcher_manager import export_hotpatcher_default_config

    path = export_hotpatcher_default_config(output, overwrite=force)
    logger.info("Hotpatcher 默认配置已导出: %s", path)


def normalize_hotpatcher_config_cli(config: Path | None = None, write_back: bool = False) -> None:
    """规范化 hotpatcher 配置

    Args:
        config (Path | None):
            配置文件路径
        write_back (bool):
            是否写回配置文件
    """

    from sd_webui_all_in_one.base_manager.hotpatcher_manager import load_hotpatcher_config, save_hotpatcher_config

    normalized = load_hotpatcher_config(config, normalize=True)
    if write_back:
        save_hotpatcher_config(config, normalized)
        logger.info("Hotpatcher 配置已规范化并写回: %s", config)
        return
    _print_json(normalized)


def apply_hotpatcher_config_cli(config: Path | None = None) -> None:
    """应用 hotpatcher 配置到当前进程

    Args:
        config (Path | None):
            配置文件路径
    """

    from sd_webui_all_in_one.base_manager.hotpatcher_manager import apply_hotpatcher_config

    _print_json(apply_hotpatcher_config(config))


def show_hotpatcher_catalog_cli() -> None:
    """显示 hotpatcher 功能目录"""

    from sd_webui_all_in_one.base_manager.hotpatcher_manager import get_hotpatcher_catalog

    _print_json(get_hotpatcher_catalog())


def launch_hotpatcher_gui_cli(
    config: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    token: str = "",
) -> None:
    """启动 hotpatcher 配置管理 GUI

    Args:
        config (Path | None):
            配置文件路径
        host (str):
            runtime host 监听地址
        port (int):
            runtime host 监听端口
        token (str):
            runtime host 访问令牌
    """

    from sd_webui_all_in_one.base_manager.hotpatcher_manager import launch_hotpatcher_manager_gui

    launch_hotpatcher_manager_gui(config_path=config, host=host, port=port, token=token)


def get_hotpatcher_pythonpath_cli() -> None:
    """输出注入 Hotpatcher 路径后的 PYTHONPATH"""

    from sd_webui_all_in_one.base_manager.hotpatcher_manager import ensure_hotpatcher_pythonpath_first

    print(ensure_hotpatcher_pythonpath_first(os.environ.copy()).get("PYTHONPATH", ""))


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
    add_auto_mirror_argument(check_pip_p)
    check_pip_p.set_defaults(
        func=with_auto_mirror(
            lambda args: check_pip(
                use_pypi_mirror=args.use_pypi_mirror,
            )
        )
    )

    # check-uv
    check_uv_p = sd_webui_all_in_one_sub.add_parser("check-uv", help="检查 uv 是否需要更新并尝试更新")
    check_uv_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    add_auto_mirror_argument(check_uv_p)
    check_uv_p.set_defaults(
        func=with_auto_mirror(
            lambda args: check_uv(
                use_pypi_mirror=args.use_pypi_mirror,
            )
        )
    )

    # patcher
    from sd_webui_all_in_one.base_manager.hotpatcher_manager import DEFAULT_HOTPATCHER_CONFIG_PATH

    patcher_p = sd_webui_all_in_one_sub.add_parser("patcher", help="Hotpatcher 配置管理")
    patcher_sub = patcher_p.add_subparsers(dest="patcher_action", required=True)

    patcher_export_p = patcher_sub.add_parser("export-config", help="导出 Hotpatcher 默认配置")
    patcher_export_p.add_argument("--output", type=normalized_filepath, default=DEFAULT_HOTPATCHER_CONFIG_PATH, help="输出配置文件路径")
    patcher_export_p.add_argument("--force", action="store_true", help="覆盖已有配置文件")
    patcher_export_p.set_defaults(
        func=lambda args: export_hotpatcher_config_cli(
            output=args.output,
            force=args.force,
        )
    )

    patcher_normalize_p = patcher_sub.add_parser("normalize-config", help="规范化 Hotpatcher 配置")
    patcher_normalize_p.add_argument("--config", type=normalized_filepath, default=DEFAULT_HOTPATCHER_CONFIG_PATH, help="配置文件路径")
    patcher_normalize_p.add_argument("--write-back", action="store_true", help="将规范化后的配置写回文件")
    patcher_normalize_p.set_defaults(
        func=lambda args: normalize_hotpatcher_config_cli(
            config=args.config,
            write_back=args.write_back,
        )
    )

    patcher_apply_p = patcher_sub.add_parser("apply-config", help="应用 Hotpatcher 配置到当前进程")
    patcher_apply_p.add_argument("--config", type=normalized_filepath, default=DEFAULT_HOTPATCHER_CONFIG_PATH, help="配置文件路径")
    patcher_apply_p.set_defaults(
        func=lambda args: apply_hotpatcher_config_cli(
            config=args.config,
        )
    )

    patcher_catalog_p = patcher_sub.add_parser("catalog", help="显示 Hotpatcher 功能目录")
    patcher_catalog_p.set_defaults(func=lambda args: show_hotpatcher_catalog_cli())

    patcher_pythonpath_p = patcher_sub.add_parser("get-pythonpath", help="输出注入 Hotpatcher 路径后的 PYTHONPATH")
    patcher_pythonpath_p.set_defaults(func=lambda args: get_hotpatcher_pythonpath_cli())

    patcher_gui_p = patcher_sub.add_parser("gui", help="启动 Hotpatcher 配置管理 GUI")
    patcher_gui_p.add_argument("--config", type=normalized_filepath, default=DEFAULT_HOTPATCHER_CONFIG_PATH, help="配置文件路径")
    patcher_gui_p.add_argument("--host", type=str, default="127.0.0.1", help="Runtime host 监听地址")
    patcher_gui_p.add_argument("--port", type=int, default=8765, help="Runtime host 监听端口")
    patcher_gui_p.add_argument("--token", type=str, default="", help="Runtime host 连接 token")
    patcher_gui_p.set_defaults(
        func=lambda args: launch_hotpatcher_gui_cli(
            config=args.config,
            host=args.host,
            port=args.port,
            token=args.token,
        )
    )

    # get-proxy
    get_proxy_p = sd_webui_all_in_one_sub.add_parser("get-proxy", help="获取系统代理地址")
    get_proxy_p.set_defaults(func=lambda args: get_proxy())

    # get-cuda-malloc
    get_cuda_malloc_p = sd_webui_all_in_one_sub.add_parser("get-cuda-malloc", help="获取支持当前设备的 CUDA 内存分配器配置")
    get_cuda_malloc_p.set_defaults(func=lambda args: get_cuda_malloc())

    # get-tcmalloc
    get_tcmalloc_p = sd_webui_all_in_one_sub.add_parser("get-tcmalloc", help="获取支持当前系统的 TCMalloc 配置")
    get_tcmalloc_p.add_argument("--path", action="store_true", help="只输出可用的 TCMalloc 库路径")
    get_tcmalloc_p.set_defaults(func=lambda args: get_tcmalloc(output_path=args.path))

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
