"""Implementation grouped from the former ``sd_trainer_base.py`` module."""

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

from sd_webui_all_in_one.base_manager.sd_trainer_base.shared import logger


def prepare_sd_trainer_launch(
    sd_trainer_path: Path,
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
    """准备 SD Trainer 启动参数。

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        launch_args (list[str] | None):
            启动 SD Trainer 的参数
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
        WebUiLaunchInfo: SD Trainer 启动参数信息。
    """
    logger.info("准备 SD Trainer 启动环境")

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)

    custom_env = apply_hf_mirror(
        use_hf_mirror=use_hf_mirror,
        custom_hf_mirror=(HUGGINGFACE_MIRROR_LIST if custom_hf_mirror is None else custom_hf_mirror) if use_hf_mirror else None,
        origin_env=custom_env,
    )

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
        webui_path=sd_trainer_path,
        launch_script="gui.py" if (sd_trainer_path / "gui.py").is_file() else "kohya_gui.py",
        webui_name="SD Trainer",
        launch_args=launch_args or [],
        custom_env=custom_env,
    )


def launch_sd_trainer(
    sd_trainer_path: Path,
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
    """启动 SD Trainer

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        launch_args (list[str] | None):
            启动 SD Trainer 的参数
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
    launch_info = prepare_sd_trainer_launch(
        sd_trainer_path=sd_trainer_path,
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

    logger.info("启动 SD Trainer 中")
    launch_webui(
        webui_path=launch_info.webui_path,
        launch_script=launch_info.launch_script,
        webui_name=launch_info.webui_name,
        launch_args=launch_info.launch_args,
        custom_env=launch_info.custom_env,
    )
