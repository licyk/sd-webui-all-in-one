"""RVC Next WebUI 启动环境准备和启动。"""

from __future__ import annotations

import os
from pathlib import Path
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
    apply_hf_mirror,
    launch_webui,
    WebUiLaunchInfo,
)
from sd_webui_all_in_one.base_manager.hotpatcher_manager import DEFAULT_RUNTIME_PORT, apply_hotpatcher_launch_env
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
    HUGGINGFACE_MIRROR_LIST,
    get_pypi_mirror_config,
)
from sd_webui_all_in_one.optimize import (
    get_cuda_malloc_var,
    apply_pytorch_alloc_conf,
)

from sd_webui_all_in_one.base_manager.rvc_next_webui_base.catalog import RVC_NEXT_WEBUI_MANAGED_LAUNCH_ARGS
from sd_webui_all_in_one.base_manager.rvc_next_webui_base.shared import logger

RVC_NEXT_DOWNLOAD_SOURCE_ENV = "RVC_NEXT_DOWNLOADS__SOURCE"
"""RVC Next 下载源设置的环境变量覆盖"""

RVC_NEXT_DOWNLOAD_ENDPOINT_ENV = "RVC_NEXT_DOWNLOADS__ENDPOINT"
"""RVC Next 自定义下载端点设置的环境变量覆盖"""


def apply_rvc_next_hf_mirror(
    custom_env: dict[str, str],
) -> dict[str, str]:
    """将 HuggingFace 镜像源应用到 RVC Next 的下载设置

    RVC Next 不读取 ``HF_ENDPOINT``, 需要通过环境变量覆盖 ``downloads.source`` 和 ``downloads.endpoint`` 设置.
    已手动设置 RVC Next 下载设置的环境变量时不进行覆盖.

    Args:
        custom_env (dict[str, str]):
            已设置 ``HF_ENDPOINT`` 的环境变量字典

    Returns:
        dict[str, str]:
            应用 RVC Next 下载设置后的环境变量字典
    """
    endpoint = custom_env.get("HF_ENDPOINT")
    if not endpoint:
        return custom_env

    if RVC_NEXT_DOWNLOAD_SOURCE_ENV in custom_env or RVC_NEXT_DOWNLOAD_ENDPOINT_ENV in custom_env:
        logger.info("已设置 RVC Next 下载源环境变量, 跳过设置 HuggingFace 镜像源")
        return custom_env

    custom_env = custom_env.copy()
    custom_env[RVC_NEXT_DOWNLOAD_SOURCE_ENV] = "custom"
    custom_env[RVC_NEXT_DOWNLOAD_ENDPOINT_ENV] = endpoint
    logger.info("RVC Next 使用 HuggingFace 镜像源: %s", endpoint)
    return custom_env


def apply_rvc_next_managed_launch_args(
    launch_args: list[str] | None,
) -> list[str]:
    """补充 RVC Next WebUI 固定使用的启动参数

    RVC Next WebUI 自带的运行环境检查和代理设置由 SD WebUI All In One 接管, 因此始终传入对应的禁用参数.

    Args:
        launch_args (list[str] | None):
            用户设置的启动参数

    Returns:
        list[str]:
            补充固定参数后的启动参数
    """
    args = list(launch_args or [])
    return args + [arg for arg in RVC_NEXT_WEBUI_MANAGED_LAUNCH_ARGS if arg not in args]


def prepare_rvc_next_webui_launch(
    rvc_next_webui_path: Path,
    launch_args: list[str] | None = None,
    use_hf_mirror: bool = False,
    custom_hf_mirror: str | list[str] | None = None,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool = False,
    use_cuda_malloc: bool = True,
    enable_hotpatcher: bool = False,
    hotpatcher_config_path: str | Path | None = None,
    hotpatcher_port: int = DEFAULT_RUNTIME_PORT,
    enable_hotpatcher_runtime: bool = False,
) -> WebUiLaunchInfo:
    """准备 RVC Next WebUI 启动参数。

    Args:
        rvc_next_webui_path (Path):
            RVC Next WebUI 根目录
        launch_args (list[str] | None):
            启动 RVC Next WebUI 的参数
        use_hf_mirror (bool):
            是否启用 HuggingFace 镜像源
        custom_hf_mirror (str | list[str] | None):
            自定义 HuggingFace 镜像源
        use_github_mirror (bool):
            是否启用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        use_pypi_mirror (bool):
            是否启用 PyPI 镜像源
        use_cuda_malloc (bool):
            是否启用 CUDA Malloc 显存优化
        enable_hotpatcher (bool):
            是否启用补丁系统注入
        hotpatcher_config_path (str | Path | None):
            补丁系统配置文件路径
        hotpatcher_port (int):
            补丁系统 runtime 通信端口
        enable_hotpatcher_runtime (bool):
            是否启用补丁系统 runtime host 连接

    Returns:
        WebUiLaunchInfo: RVC Next WebUI 启动参数信息。
    """
    logger.info("准备 RVC Next WebUI 启动环境")

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)

    if use_hf_mirror:
        custom_env = apply_hf_mirror(
            use_hf_mirror=use_hf_mirror,
            custom_hf_mirror=(HUGGINGFACE_MIRROR_LIST if custom_hf_mirror is None else custom_hf_mirror) if use_hf_mirror else None,
            origin_env=custom_env,
        )
        custom_env = apply_rvc_next_hf_mirror(custom_env)

    custom_env = get_pypi_mirror_config(
        use_cn_mirror=use_pypi_mirror,
        origin_env=custom_env,
    )

    if use_cuda_malloc:
        cuda_malloc_config = get_cuda_malloc_var()
        if cuda_malloc_config is not None:
            custom_env = apply_pytorch_alloc_conf(
                config=cuda_malloc_config,
                origin_env=custom_env,
            )
    custom_env = apply_hotpatcher_launch_env(
        origin_env=custom_env,
        enabled=enable_hotpatcher,
        config_path=hotpatcher_config_path,
        port=hotpatcher_port,
        enable_runtime=enable_hotpatcher_runtime,
    )
    return WebUiLaunchInfo(
        webui_path=rvc_next_webui_path,
        launch_script="launch.py",
        webui_name="RVC Next WebUI",
        launch_args=apply_rvc_next_managed_launch_args(launch_args),
        custom_env=custom_env,
    )


def launch_rvc_next_webui(
    rvc_next_webui_path: Path,
    launch_args: list[str] | None = None,
    use_hf_mirror: bool = False,
    custom_hf_mirror: str | list[str] | None = None,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool = False,
    use_cuda_malloc: bool = True,
    enable_hotpatcher: bool = False,
    hotpatcher_config_path: str | Path | None = None,
    hotpatcher_port: int = DEFAULT_RUNTIME_PORT,
    enable_hotpatcher_runtime: bool = False,
) -> None:
    """启动 RVC Next WebUI

    Args:
        rvc_next_webui_path (Path):
            RVC Next WebUI 根目录
        launch_args (list[str] | None):
            启动 RVC Next WebUI 的参数
        use_hf_mirror (bool):
            是否启用 HuggingFace 镜像源
        custom_hf_mirror (str | list[str] | None):
            自定义 HuggingFace 镜像源
        use_github_mirror (bool):
            是否启用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        use_pypi_mirror (bool):
            是否启用 PyPI 镜像源
        use_cuda_malloc (bool):
            是否启用 CUDA Malloc 显存优化
        enable_hotpatcher (bool):
            是否启用补丁系统注入
        hotpatcher_config_path (str | Path | None):
            补丁系统配置文件路径
        hotpatcher_port (int):
            补丁系统 runtime 通信端口
        enable_hotpatcher_runtime (bool):
            是否启用补丁系统 runtime host 连接
    """
    launch_info = prepare_rvc_next_webui_launch(
        rvc_next_webui_path=rvc_next_webui_path,
        launch_args=launch_args,
        use_hf_mirror=use_hf_mirror,
        custom_hf_mirror=custom_hf_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        use_pypi_mirror=use_pypi_mirror,
        use_cuda_malloc=use_cuda_malloc,
        enable_hotpatcher=enable_hotpatcher,
        hotpatcher_config_path=hotpatcher_config_path,
        hotpatcher_port=hotpatcher_port,
        enable_hotpatcher_runtime=enable_hotpatcher_runtime,
    )

    logger.info("启动 RVC Next WebUI 中")
    launch_webui(
        webui_path=launch_info.webui_path,
        launch_script=launch_info.launch_script,
        webui_name=launch_info.webui_name,
        launch_args=launch_info.launch_args,
        custom_env=launch_info.custom_env,
    )
