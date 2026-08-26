"""Implementation grouped from the former ``sd_trainer_base.py`` module."""

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
from sd_webui_all_in_one.env_check import (
    check_accelerate_bin,
    check_onnxruntime_gpu,
    check_torch_version,
    py_dependency_checker,
    check_numpy,
    fix_torch_libomp,
)
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
    get_pypi_mirror_config,
)
from sd_webui_all_in_one.model_downloader import ModelDownloadUrlType
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one.pytorch_manager import PyTorchDeviceType

from .catalog import SDTrainerBranchType, SD_TRAINER_BRANCH_INFO_DICT, SD_TRAINER_BRANCH_LIST
from .shared import logger


def install_sd_trainer(
    sd_trainer_path: Path,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_pypi_mirror: bool = True,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    install_branch: SDTrainerBranchType | None = None,
    no_pre_download_model: bool = False,
    model_download_resource_type: ModelDownloadUrlType | None = "modelscope",
) -> None:
    """安装 SD Trainer

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
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
        install_branch (SDTrainerBranchType | None):
            安装的 SD Trainer 分支
        no_pre_download_model (bool):
            是否禁用预下载模型
        model_download_resource_type (ModelDownloadUrlType | None):
            下载模型使用的下载源

    Raises:
        ValueError:
            安装的 SD Trainer 分支未知时
        FileNotFoundError:
            SD Trainer 依赖文件缺失时
    """
    logger.info("准备 SD Trainer 安装配置")

    # 准备 SD Trainer 安装分支信息
    need_switch_branch = True
    if install_branch is None:
        need_switch_branch = False
        install_branch = SD_TRAINER_BRANCH_LIST[0]

    if install_branch not in SD_TRAINER_BRANCH_LIST:
        raise ValueError(f"未知的 SD Trainer 类型: {install_branch}")

    for info in SD_TRAINER_BRANCH_INFO_DICT:
        if info["dtype"] == install_branch:
            branch_info = info
            break

    # 准备 PyTorch 安装信息
    pytorch_package, xformers_package, custom_env_pytorch = prepare_pytorch_install_info(
        pytorch_mirror_type=pytorch_mirror_type,
        custom_pytorch_package=custom_pytorch_package,
        custom_xformers_package=custom_xformers_package,
        use_cn_mirror=use_pypi_mirror,
    )

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

    logger.info("SD Trainer 安装配置准备完成")
    logger.info("开始安装 SD Trainer, 安装路径: %s", sd_trainer_path)
    logger.info("安装的 SD Trainer 分支: '%s'", branch_info["name"])

    logger.info("安装 SD Trainer 内核中")
    clone_repo(
        repo=branch_info["url"],
        path=sd_trainer_path,
    )
    git_warpper.update_submodule(sd_trainer_path)

    if need_switch_branch:
        logger.info("切换 SD Trainer 分支中")
        git_warpper.switch_branch(
            path=sd_trainer_path,
            branch=branch_info["branch"],
            new_url=branch_info["url"],
            recurse_submodules=branch_info["use_submodule"],
        )

    install_pytorch_for_webui(
        pytorch_package=pytorch_package,
        xformers_package=xformers_package,
        custom_env=custom_env_pytorch,
        use_uv=use_uv,
    )

    req_path = sd_trainer_path / "requirements.txt"
    if not req_path.is_file():
        raise FileNotFoundError("未找到 SD Trainer 依赖文件记录表, 请检查 SD Trainer 文件是否完整")

    logger.info("安装 SD Trainer 依赖中")
    install_requirements(
        path=req_path,
        use_uv=use_uv,
        custom_env=custom_env,
        cwd=sd_trainer_path,
    )

    if not no_pre_download_model:
        pre_download_model_for_webui(
            dtype="sd_trainer",
            model_path=sd_trainer_path / "sd-models",
            webui_base_path=sd_trainer_path,
            model_name="ChenkinNoob-XL-V0.2",
            download_resource_type=model_download_resource_type,
        )

    logger.info("安装 SD Trainer 完成")


def update_sd_trainer(
    sd_trainer_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 SD Trainer

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
    """
    logger.info("更新 SD Trainer 中")
    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)

    git_warpper.update(sd_trainer_path)

    logger.info("更新 SD Trainer 完成")


def check_sd_trainer_env(
    sd_trainer_path: Path,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool = False,
    include_checks: list[str] | None = None,
    exclude_checks: list[str] | None = None,
) -> None:
    """检查 SD Trainer 运行环境

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
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
            检查 SD Trainer 环境发生错误时
        FileNotFoundError:
            未找到 SD Trainer 依赖文件记录表时
    """
    req_path = sd_trainer_path / "requirements.txt"

    if not req_path.is_file():
        raise FileNotFoundError("未找到 SD Trainer 依赖文件记录表, 请检查文件是否完整")

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)

    # 准备安装依赖的 PyPI 镜像源
    custom_env = get_pypi_mirror_config(
        use_cn_mirror=use_pypi_mirror,
        origin_env=custom_env,
    )

    # 检查任务列表
    tasks = [
        EnvCheckTask("python-dependencies", py_dependency_checker, {"requirement_path": req_path, "name": "SD Trainer", "use_uv": use_uv, "custom_env": custom_env}),
        EnvCheckTask("torch-libomp", fix_torch_libomp, {}),
        EnvCheckTask("torch-version", check_torch_version, {}),
        EnvCheckTask("accelerate-bin", check_accelerate_bin, {"base_path": sd_trainer_path, "use_uv": use_uv, "custom_env": custom_env}),
        EnvCheckTask("onnxruntime-gpu", check_onnxruntime_gpu, {"use_uv": use_uv, "skip_if_missing": False, "custom_env": custom_env}),
        EnvCheckTask("numpy", check_numpy, {"use_uv": use_uv, "custom_env": custom_env}),
    ]
    run_env_check_tasks(
        tasks,
        include_checks=include_checks,
        exclude_checks=exclude_checks,
        error_message="检查 SD Trainer 环境时发生错误",
    )

    logger.info("检查 SD Trainer 环境完成")
