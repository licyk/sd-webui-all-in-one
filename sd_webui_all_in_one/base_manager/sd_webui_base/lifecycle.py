"""Implementation grouped from the former ``sd_webui_base.py`` module."""

from __future__ import annotations

import importlib
import os
import importlib.metadata
from pathlib import Path
from sd_webui_all_in_one.env_check import (
    check_torch_version,
    py_dependency_checker,
    fix_torch_libomp,
    check_onnxruntime_gpu,
    install_extension_requirements,
    fix_stable_diffusion_invaild_repo_url,
    fix_forge_neo_alert,
)
from sd_webui_all_in_one.model_downloader import ModelDownloadUrlType
from sd_webui_all_in_one.pytorch_manager import PyTorchDeviceType
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
    prepare_pytorch_install_info,
    clone_repo,
    install_pytorch_for_webui,
    pre_download_model_for_webui,
    EnvCheckTask,
    run_env_check_tasks,
)
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
    get_pypi_mirror_config,
)
from sd_webui_all_in_one.file_manager import (
    copy_files,
)
from sd_webui_all_in_one.pkg_manager import pip_install

from sd_webui_all_in_one.base_manager.sd_webui_base.catalog import SDWebUiBranchType, SD_WEBUI_BRANCH_INFO_DICT, SD_WEBUI_BRANCH_LIST, SD_WEBUI_CONFIG_PATH
from sd_webui_all_in_one.base_manager.sd_webui_base.extensions import SDWebUiExtensionInfoList, SD_WEBUI_EXTENSION_INFO_DICT
from sd_webui_all_in_one.base_manager.sd_webui_base.shared import logger

SD_WEBUI_REPOSITORY_INFO_DICT: SDWebUiExtensionInfoList = [
    {
        "name": "BLIP",
        "url": "https://github.com/salesforce/BLIP",
        "save_dir": "repositories/BLIP",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "stablediffusion",
        "url": "https://github.com/licyk/stablediffusion",
        "save_dir": "repositories/stable-diffusion-stability-ai",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "generative-models",
        "url": "https://github.com/Stability-AI/generative-models",
        "save_dir": "repositories/generative-models",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "k-diffusion",
        "url": "https://github.com/crowsonkb/k-diffusion",
        "save_dir": "repositories/k-diffusion",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "stable-diffusion-webui-assets",
        "url": "https://github.com/AUTOMATIC1111/stable-diffusion-webui-assets",
        "save_dir": "repositories/stable-diffusion-webui-assets",
        "supported_branch": [
            "sd_webui_main",
            "sd_webui_dev",
            "sd_webui_forge",
            "sd_webui_reforge_main",
            "sd_webui_reforge_dev",
            "sd_webui_amdgpu",
            "sd_next_main",
            "sd_next_dev",
        ],
    },
    {
        "name": "huggingface_guess",
        "url": "https://github.com/lllyasviel/huggingface_guess",
        "save_dir": "repositories/huggingface_guess",
        "supported_branch": [
            "sd_webui_forge",
        ],
    },
    {
        "name": "google_blockly_prototypes",
        "url": "https://github.com/lllyasviel/google_blockly_prototypes",
        "save_dir": "repositories/google_blockly_prototypes",
        "supported_branch": [
            "sd_webui_forge",
        ],
    },
]


def install_sd_webui_config(
    sd_webui_path: Path,
) -> None:
    """安装 Stable Diffusion WebUI 配置文件

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录

    """
    config_path = sd_webui_path / "config.json"
    if not config_path.exists():
        copy_files(SD_WEBUI_CONFIG_PATH, config_path)


def install_clip_package(
    use_pypi_mirror: bool = False,
    custom_env: dict[str, str] | None = None,
    use_uv: bool = True,
) -> None:
    """安装 CLIP 软件包

    Args:
        use_pypi_mirror (bool):
            是否使用 PyPI 国内镜像
        custom_env (dict[str, str] | None):
            自定义环境变量字典
        use_uv (bool):
            是否使用 uv 安装 Python 软件包

    Raises:
        RuntimeError:
            安装 CLIP 软件包发生错误时
    """

    if use_pypi_mirror:
        pkg_url = "https://modelscope.cn/models/licyks/wheels/resolve/master/clip/clip-1.0-py3-none-any.whl"
    else:
        pkg_url = "https://huggingface.co/licyk/wheel/resolve/main/clip/clip-1.0-py3-none-any.whl"

    logger.info("检测是否需要安装 CLIP 软件包")
    try:
        importlib.metadata.version("clip")
        logger.info("CLIP 软件包已安装")
        return
    except Exception:
        logger.info("安装 CLIP 软件包中")

    try:
        pip_install(
            pkg_url,
            use_uv=use_uv,
            custom_env=custom_env,
        )
    except RuntimeError as e:
        raise RuntimeError(f"安装 CLIP 软件包时发生错误: {e}") from e

    logger.info("CLIP 软件包安装成功")


def install_sd_webui(
    sd_webui_path: Path,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_pypi_mirror: bool = True,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    install_branch: SDWebUiBranchType | None = None,
    no_pre_download_extension: bool = False,
    no_pre_download_model: bool = False,
    model_download_resource_type: ModelDownloadUrlType | None = "modelscope",
) -> None:
    """安装 Stable Diffusion WebUI

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
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
        install_branch (SDWebUiBranchType | None):
            安装的 Stable Diffusion WebUI 分支
        no_pre_download_extension (bool):
            是否禁用预下载 Stable Diffusion WebUI 扩展
        no_pre_download_model (bool):
            是否禁用预下载模型
        model_download_resource_type (ModelDownloadUrlType | None):
            下载模型使用的下载源

    Raises:
        ValueError:
            安装的 Stable Diffusion WebUI 分支未知时
        FileNotFoundError:
            Stable Diffusion WebUI 依赖文件缺失时
    """
    logger.info("准备 Stable Diffusion WebUI 安装配置")

    # 准备 Stable Diffusion WebUI 安装分支信息
    need_switch_branch = True
    if install_branch is None:
        need_switch_branch = False
        install_branch = SD_WEBUI_BRANCH_LIST[0]

    if install_branch not in SD_WEBUI_BRANCH_LIST:
        raise ValueError(f"未知的 Stable Diffusion WebUI 类型: {install_branch}")

    for info in SD_WEBUI_BRANCH_INFO_DICT:
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

    # 准备扩展 / 组件安装信息
    sd_weui_extension_list = [x for x in SD_WEBUI_EXTENSION_INFO_DICT if install_branch in x["supported_branch"] and not no_pre_download_extension]
    sd_webui_repository_list = [x for x in SD_WEBUI_REPOSITORY_INFO_DICT if install_branch in x["supported_branch"]]

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
    logger.debug("安装的扩展信息: %s", sd_weui_extension_list)
    logger.debug("安装的组件信息: %s", sd_webui_repository_list)

    logger.info("Stable Diffusion WebUI 安装配置准备完成")
    logger.info("开始安装 Stable Diffusion WebUI, 安装路径: %s", sd_webui_path)
    logger.info("安装的 Stable Diffusion WebUI 分支: '%s'", branch_info["name"])

    logger.info("安装 Stable Diffusion WebUI 内核中")
    clone_repo(
        repo=branch_info["url"],
        path=sd_webui_path,
    )

    if need_switch_branch:
        logger.info("切换 Stable Diffusion WebUI 分支中")
        git_warpper.switch_branch(
            path=sd_webui_path,
            branch=branch_info["branch"],
            new_url=branch_info["url"],
            recurse_submodules=branch_info["use_submodule"],
        )

    if sd_webui_repository_list:
        logger.info("安装 Stable Diffusion WebUI 组件中")
        for info in sd_webui_repository_list:
            clone_repo(
                repo=info["url"],
                path=sd_webui_path / info["save_dir"],
            )

    if sd_weui_extension_list:
        logger.info("安装 Stable Diffusion WebUI 扩展中")
        for info in sd_weui_extension_list:
            clone_repo(
                repo=info["url"],
                path=sd_webui_path / info["save_dir"],
            )

    install_pytorch_for_webui(
        pytorch_package=pytorch_package,
        xformers_package=xformers_package,
        custom_env=custom_env_pytorch,
        use_uv=use_uv,
    )

    requirements_version_path = sd_webui_path / "requirements_versions.txt"
    requirements_path = sd_webui_path / "requirements.txt"

    if not requirements_path.is_file() and not requirements_version_path.is_file():
        raise FileNotFoundError("未找到 Stable Diffusion WebUI 依赖文件记录表, 请检查 Stable Diffusion WebUI 文件是否完整")

    logger.info("安装 Stable Diffusion WebUI 依赖中")
    install_clip_package(
        use_pypi_mirror=use_pypi_mirror,
        use_uv=use_uv,
        custom_env=custom_env,
    )
    install_requirements(
        path=requirements_version_path if requirements_version_path.is_file() else requirements_path,
        use_uv=use_uv,
        custom_env=custom_env,
        cwd=sd_webui_path,
    )

    if not no_pre_download_model:
        logger.info("预下载模型中")
        pre_download_model_for_webui(
            dtype="sd_webui",
            model_path=sd_webui_path / "models" / "Stable-diffusion",
            webui_base_path=sd_webui_path,
            model_name="ChenkinNoob-XL-V0.2",
            download_resource_type=model_download_resource_type,
        )
        pre_download_model_for_webui(
            dtype="sd_webui",
            model_path=sd_webui_path / "models" / "VAE-approx",
            webui_base_path=sd_webui_path,
            model_name=["model", "vaeapprox-sdxl", "vaeapprox-sd3"],
            download_resource_type=model_download_resource_type,
            check_exists=False,
        )

    install_sd_webui_config(sd_webui_path)

    logger.info("安装 Stable Diffusion WebUI 完成")


def update_sd_webui(
    sd_webui_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 Stable Diffusion WebUI

    Args:
        sd_webui_path (Path):
            Stable DIffusion WebUI 根目录
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
    """
    logger.info("更新 Stable Diffusion WebUI 中")
    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)

    git_warpper.update(sd_webui_path)

    logger.info("更新 Stable Diffusion WebUI 完成")


def check_sd_webui_env(
    sd_webui_path: Path,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool = False,
    include_checks: list[str] | None = None,
    exclude_checks: list[str] | None = None,
) -> None:
    """检查 Stable Diffusion WebUI 运行环境

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
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
            检查 Stable Diffusion WebUI 环境发生错误时
        FileNotFoundError:
            未找到 Stable Diffusion WebUI 依赖文件记录表时
    """
    req_v_path = sd_webui_path / "requirements_versions.txt"
    req_path = sd_webui_path / "requirements.txt"

    if not req_v_path.is_file() and not req_path.is_file():
        raise FileNotFoundError("未找到 Stable Diffusion WebUI 依赖文件记录表, 请检查文件是否完整")

    # 确定主要的依赖描述文件
    active_req_path = req_v_path if req_v_path.is_file() else req_path

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
        EnvCheckTask("sd-webui-invalid-repo", fix_stable_diffusion_invaild_repo_url, {"sd_webui_path": sd_webui_path, "custom_env": custom_env}),
        EnvCheckTask("forge-neo-alert", fix_forge_neo_alert, {"sd_webui_path": sd_webui_path}),
        EnvCheckTask("python-dependencies", py_dependency_checker, {"requirement_path": active_req_path, "name": "Stable Diffusion WebUI", "use_uv": use_uv, "custom_env": custom_env}),
        EnvCheckTask("sd-webui-extension-dependencies", install_extension_requirements, {"sd_webui_path": sd_webui_path, "custom_env": custom_env}),
        EnvCheckTask("torch-libomp", fix_torch_libomp, {}),
        EnvCheckTask("torch-version", check_torch_version, {}),
        EnvCheckTask("onnxruntime-gpu", check_onnxruntime_gpu, {"use_uv": use_uv, "skip_if_missing": True, "custom_env": custom_env}),
    ]
    run_env_check_tasks(
        tasks,
        include_checks=include_checks,
        exclude_checks=exclude_checks,
        error_message="检查 Stable Diffusion WebUI 环境时发生错误",
    )

    logger.info("检查 Stable Diffusion WebUI 环境完成")
