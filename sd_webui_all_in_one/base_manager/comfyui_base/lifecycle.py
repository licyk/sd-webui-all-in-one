"""Implementation grouped from the former ``comfyui_base.py`` module."""

from __future__ import annotations

import os
from pathlib import Path
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
    clone_repo,
    install_pytorch_for_webui,
    pre_download_model_for_webui,
    prepare_pytorch_install_info,
    EnvCheckTask,
    run_env_check_tasks,
)
from sd_webui_all_in_one.file_manager import (
    copy_files,
)
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
    get_pypi_mirror_config,
)
from sd_webui_all_in_one.model_downloader import ModelDownloadUrlType
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one.pytorch_manager import PyTorchDeviceType
from sd_webui_all_in_one.env_check import (
    py_dependency_checker,
    fix_torch_libomp,
    check_onnxruntime_gpu,
    comfyui_conflict_analyzer,
    check_comfyui_manager_dependence,
    check_torch_version,
)

from sd_webui_all_in_one.base_manager.comfyui_base.catalog import COMFYUI_CONFIG_PATH, COMFYUI_REPO_URL
from sd_webui_all_in_one.base_manager.comfyui_base.extensions import COMFYUI_CUSTOM_NODES_INFO_DICT
from sd_webui_all_in_one.base_manager.comfyui_base.shared import logger


def install_comfyui_config(
    comfyui_path: Path,
) -> None:
    """安装 ComfyUI 配置文件

    Args:
        comfyui_path (Path):
            ComfyUI 根目录

    """
    config_path = comfyui_path / "user" / "default" / "comfy.settings.json"
    if not config_path.exists():
        copy_files(COMFYUI_CONFIG_PATH, config_path)


def install_comfyui(
    comfyui_path: Path,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_pypi_mirror: bool = True,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    no_pre_download_extension: bool = False,
    no_pre_download_model: bool = False,
    model_download_resource_type: ModelDownloadUrlType | None = "modelscope",
) -> None:
    """安装 ComfyUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        pytorch_mirror_type (PyTorchDeviceType | None):
            设置使用的 PyTorch 镜像源类型
        custom_pytorch_package (str | None):
            自定义 PyTorch 软件包版本声明, 例如: `torch==2.3.0+cu118 torchvision==0.18.0+cu118`
        custom_xformers_package (str | None):
            自定义 xFormers 软件包版本声明, 例如: `xformers===0.0.26.post1+cu118`
        use_pypi_mirror (bool):
            是否使用国内 PyPI 镜像源
        use_uv (bool):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        no_pre_download_extension (bool):
            是否禁用预下载 ComfyUI 扩展
        no_pre_download_model (bool):
            是否禁用预下载模型
        model_download_resource_type (ModelDownloadUrlType | None):
            下载模型使用的下载源

    Raises:
        FileNotFoundError:
            ComfyUI 依赖文件缺失时
    """
    logger.info("准备 ComfyUI 安装配置")

    # 准备 PyTorch 安装信息
    pytorch_package, xformers_package, custom_env_pytorch = prepare_pytorch_install_info(
        pytorch_mirror_type=pytorch_mirror_type,
        custom_pytorch_package=custom_pytorch_package,
        custom_xformers_package=custom_xformers_package,
        use_cn_mirror=use_pypi_mirror,
    )

    # 准备扩展安装信息
    comfyui_custom_node_list = COMFYUI_CUSTOM_NODES_INFO_DICT.copy() if not no_pre_download_extension else []

    # 准备安装依赖的 PyPI 镜像源
    custom_env = get_pypi_mirror_config(use_pypi_mirror)

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=custom_env,
    )
    apply_git_config_global_to_process(custom_env)

    logger.debug("安装的 PyTorch 版本: %s", pytorch_package)
    logger.debug("安装的 xformers: %s", xformers_package)
    logger.debug("安装的扩展信息: %s", comfyui_custom_node_list)

    logger.info("ComfyUI 安装配置准备完成")
    logger.info("开始安装 ComfyUI, 安装路径: %s", comfyui_path)

    logger.info("安装 ComfyUI 内核中")
    clone_repo(
        repo=COMFYUI_REPO_URL,
        path=comfyui_path,
    )

    if comfyui_custom_node_list:
        logger.info("安装 ComfyUI 扩展中")
        for info in comfyui_custom_node_list:
            clone_repo(
                repo=info["url"],
                path=comfyui_path / info["save_dir"],
            )

    install_pytorch_for_webui(
        pytorch_package=pytorch_package,
        xformers_package=xformers_package,
        custom_env=custom_env_pytorch,
        use_uv=use_uv,
    )

    requirements_path = comfyui_path / "requirements.txt"

    if not requirements_path.is_file():
        raise FileNotFoundError("未找到 ComfyUI 依赖文件记录表, 请检查 ComfyUI 文件是否完整")

    logger.info("安装 ComfyUI 依赖中")
    install_requirements(
        path=requirements_path,
        use_uv=use_uv,
        custom_env=custom_env,
        cwd=comfyui_path,
    )

    if not no_pre_download_model:
        pre_download_model_for_webui(
            dtype="comfyui",
            model_path=comfyui_path / "models" / "checkpoints",
            webui_base_path=comfyui_path,
            model_name="ChenkinNoob-XL-V0.2",
            download_resource_type=model_download_resource_type,
        )

    install_comfyui_config(comfyui_path)

    logger.info("安装 ComfyUI 完成")


def update_comfyui(
    comfyui_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 ComfyUI

    Args:
        comfyui_path (Path):
            Stable DIffusion WebUI 根目录
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
    """
    logger.info("更新 ComfyUI 中")
    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)

    git_warpper.update(comfyui_path)

    logger.info("更新 ComfyUI 完成")


def check_comfyui_env(
    comfyui_path: Path,
    install_conflict_component_requirement: bool = False,
    interactive_mode: bool = False,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool = False,
    include_checks: list[str] | None = None,
    exclude_checks: list[str] | None = None,
) -> None:
    """检查 ComfyUI 运行环境

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        install_conflict_component_requirement (bool):
            检测到冲突依赖时是否按顺序安装组件依赖
        interactive_mode (bool):
            是否启用交互模式, 当检测到冲突依赖时将询问是否安装冲突组件依赖
        use_uv (bool):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        use_pypi_mirror (bool):
            是否使用国内 PyPI 镜像源
        include_checks (list[str] | None):
            仅执行的环境检查任务名称。
        exclude_checks (list[str] | None):
            跳过的环境检查任务名称。

    Raises:
        AggregateError:
            检查 ComfyUI 环境发生错误时
        FileNotFoundError:
            未找到 ComfyUI 依赖文件记录表时
    """
    req_path = comfyui_path / "requirements.txt"

    if not req_path.is_file():
        raise FileNotFoundError("未找到 ComfyUI 依赖文件记录表, 请检查文件是否完整")

    # 准备安装依赖的 PyPI 镜像源
    custom_env = get_pypi_mirror_config(
        use_cn_mirror=use_pypi_mirror,
        origin_env=os.environ.copy(),
    )

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=custom_env,
    )
    apply_git_config_global_to_process(custom_env)

    # 检查任务列表
    tasks = [
        EnvCheckTask("python-dependencies", py_dependency_checker, {"requirement_path": req_path, "name": "ComfyUI", "use_uv": use_uv, "custom_env": custom_env}),
        EnvCheckTask("comfyui-manager-dependencies", check_comfyui_manager_dependence, {"comfyui_root_path": comfyui_path, "use_uv": use_uv, "custom_env": custom_env}),
        EnvCheckTask(
            "comfyui-conflicts",
            comfyui_conflict_analyzer,
            {
                "comfyui_root_path": comfyui_path,
                "install_conflict_component_requirement": install_conflict_component_requirement,
                "interactive_mode": interactive_mode,
                "use_uv": use_uv,
                "custom_env": custom_env,
            },
        ),
        EnvCheckTask("torch-libomp", fix_torch_libomp, {}),
        EnvCheckTask("torch-version", check_torch_version, {}),
        EnvCheckTask("onnxruntime-gpu", check_onnxruntime_gpu, {"use_uv": use_uv, "skip_if_missing": True, "custom_env": custom_env}),
    ]
    run_env_check_tasks(
        tasks,
        include_checks=include_checks,
        exclude_checks=exclude_checks,
        error_message="检查 ComfyUI 环境时发生错误",
    )

    logger.info("检查 ComfyUI 环境完成")
