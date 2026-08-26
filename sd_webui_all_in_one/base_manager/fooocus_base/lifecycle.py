"""Implementation grouped from the former ``fooocus_base.py`` module."""

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
    check_torch_version,
    py_dependency_checker,
    check_numpy,
    fix_torch_libomp,
    check_onnxruntime_gpu,
)
from sd_webui_all_in_one.file_manager import (
    copy_files,
)
from sd_webui_all_in_one.config import (
    ROOT_PATH,
)
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
    get_pypi_mirror_config,
)
from sd_webui_all_in_one.model_downloader import ModelDownloadUrlType
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one.pytorch_manager import PyTorchDeviceType

from .catalog import FOOOCUS_BRANCH_INFO_DICT, FOOOCUS_BRANCH_LIST, FOOOCUS_PRESET_HF_PATH, FOOOCUS_PRESET_MS_PATH, FooocusBranchType
from .shared import logger

FOOOCUS_TRANSLATE_ZH_PATH = ROOT_PATH / "base_manager" / "config" / "fooocus_zh_cn.json"


def install_fooocus_config(
    fooocus_path: Path,
    download_resource_type: ModelDownloadUrlType | bool = False,
) -> None:
    """安装 Fooocus 配置文件

    Args:
        fooocus_path (Path):
            Fooocus 根目录
        download_resource_type (ModelDownloadUrlType | bool):
            下载模型使用的下载源

    Raises:
        ValueError:
            未知的下载配置源类型时
    """
    preset_path = fooocus_path / "presets" / "sd_webui_all_in_one.json"
    translate_path = fooocus_path / "language" / "zh.json"
    if not preset_path.exists():
        if download_resource_type == "huggingface":
            preset = FOOOCUS_PRESET_HF_PATH
        elif download_resource_type == "modelscope":
            preset = FOOOCUS_PRESET_MS_PATH
        else:
            raise ValueError(f"未知的下载配置源类型: {download_resource_type}")

        copy_files(preset, preset_path)
    if not translate_path.exists():
        copy_files(FOOOCUS_TRANSLATE_ZH_PATH, translate_path)


def _launch_args_has_option(launch_args: list[str], option_name: str) -> bool:
    return any(arg == option_name or arg.startswith(f"{option_name}=") for arg in launch_args)


def install_fooocus(
    fooocus_path: Path,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_pypi_mirror: bool = True,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    install_branch: FooocusBranchType | None = None,
    no_pre_download_model: bool = False,
    model_download_resource_type: ModelDownloadUrlType | None = "modelscope",
) -> None:
    """安装 Fooocus

    Args:
        fooocus_path (Path):
            Fooocus 根目录
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
        install_branch (FooocusBranchType | None):
            安装的 Fooocus 分支
        no_pre_download_model (bool):
            是否禁用预下载模型
        model_download_resource_type (ModelDownloadUrlType | None):
            下载模型使用的下载源

    Raises:
        ValueError:
            安装的 Fooocus 分支未知时
        FileNotFoundError:
            Fooocus 依赖文件缺失时
    """
    logger.info("准备 Fooocus 安装配置")

    # 准备 Fooocus 安装分支信息
    need_switch_branch = True
    if install_branch is None:
        need_switch_branch = False
        install_branch = FOOOCUS_BRANCH_LIST[0]

    if install_branch not in FOOOCUS_BRANCH_LIST:
        raise ValueError(f"未知的 Fooocus 类型: {install_branch}")

    for info in FOOOCUS_BRANCH_INFO_DICT:
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

    logger.info("Fooocus 安装配置准备完成")
    logger.info("开始安装 Fooocus, 安装路径: %s", fooocus_path)
    logger.info("安装的 Fooocus 分支: '%s'", branch_info["name"])

    logger.info("安装 Fooocus 内核中")
    clone_repo(
        repo=branch_info["url"],
        path=fooocus_path,
    )

    if need_switch_branch:
        logger.info("切换 Fooocus 分支中")
        git_warpper.switch_branch(
            path=fooocus_path,
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

    requirements_version_path = fooocus_path / "requirements_versions.txt"
    requirements_path = fooocus_path / "requirements.txt"

    if not requirements_path.is_file() and not requirements_version_path.is_file():
        raise FileNotFoundError("未找到 Fooocus 依赖文件记录表, 请检查 Fooocus 文件是否完整")

    logger.info("安装 Fooocus 依赖中")
    install_requirements(
        path=requirements_version_path if requirements_version_path.is_file() else requirements_path,
        use_uv=use_uv,
        custom_env=custom_env,
        cwd=fooocus_path,
    )

    if not no_pre_download_model:
        pre_download_model_for_webui(
            dtype="fooocus",
            model_path=fooocus_path / "models" / "checkpoints",
            webui_base_path=fooocus_path,
            model_name="ChenkinNoob-XL-V0.2",
            download_resource_type=model_download_resource_type,
        )

    config_download_resource_type: ModelDownloadUrlType | bool = model_download_resource_type if model_download_resource_type is not None else False
    install_fooocus_config(
        fooocus_path=fooocus_path,
        download_resource_type=config_download_resource_type,
    )

    logger.info("安装 Fooocus 完成")


def update_fooocus(
    fooocus_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 Fooocus

    Args:
        fooocus_path (Path):
            Fooocus 根目录
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
    """
    logger.info("更新 Fooocus 中")

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)

    git_warpper.update(fooocus_path)

    logger.info("更新 Fooocus 完成")


def check_fooocus_env(
    fooocus_path: Path,
    use_uv: bool = True,
    use_pypi_mirror: bool = False,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    include_checks: list[str] | None = None,
    exclude_checks: list[str] | None = None,
) -> None:
    """检查 Fooocus 运行环境

    Args:
        fooocus_path (Path):
            Fooocus 根目录
        use_uv (bool):
            是否使用 uv 安装 Python 软件包
        use_pypi_mirror (bool):
            是否使用国内 PyPI 镜像源
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        include_checks (list[str] | None):
            仅执行的环境检查任务名称。
        exclude_checks (list[str] | None):
            跳过的环境检查任务名称。

    Raises:
        AggregateError:
            检查 Fooocus 环境发生错误时
        FileNotFoundError:
            未找到 Fooocus 依赖文件记录表时
    """
    req_v_path = fooocus_path / "requirements_versions.txt"
    req_path = fooocus_path / "requirements.txt"

    if not req_v_path.is_file() and not req_path.is_file():
        raise FileNotFoundError("未找到 Fooocus 依赖文件记录表, 请检查文件是否完整")

    # 确定主要的依赖描述文件
    active_req_path = req_v_path if req_v_path.is_file() else req_path

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
        EnvCheckTask("python-dependencies", py_dependency_checker, {"requirement_path": active_req_path, "name": "Fooocus", "use_uv": use_uv, "custom_env": custom_env}),
        EnvCheckTask("torch-libomp", fix_torch_libomp, {}),
        EnvCheckTask("torch-version", check_torch_version, {}),
        EnvCheckTask("onnxruntime-gpu", check_onnxruntime_gpu, {"use_uv": use_uv, "skip_if_missing": True, "custom_env": custom_env}),
        EnvCheckTask("numpy", check_numpy, {"use_uv": use_uv, "custom_env": custom_env}),
    ]
    run_env_check_tasks(
        tasks,
        include_checks=include_checks,
        exclude_checks=exclude_checks,
        error_message="检查 Fooocus 环境时发生错误",
    )

    logger.info("检查 Fooocus 环境完成")
