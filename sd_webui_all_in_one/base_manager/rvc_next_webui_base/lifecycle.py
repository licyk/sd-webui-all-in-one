"""RVC Next WebUI 安装, 更新和运行环境检查。"""

from __future__ import annotations

import os
from pathlib import Path
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
    clone_repo,
    install_pytorch_for_webui,
    prepare_pytorch_install_info,
    EnvCheckName,
    EnvCheckTask,
    run_env_check_tasks,
)
from sd_webui_all_in_one.env_check import (
    check_torch_version,
    fix_torch_libomp,
)
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
    get_pypi_mirror_config,
)
from sd_webui_all_in_one.package_analyzer import (
    Requirement,
    Version,
    get_missing_package_metadata_dependencies,
    is_package_installed,
    validate_requirements,
)
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one.pytorch_manager import PyTorchDeviceType
from sd_webui_all_in_one.pytorch_manager.version_manager import find_torch_requirement

from sd_webui_all_in_one.base_manager.rvc_next_webui_base.catalog import (
    RVC_NEXT_PACKAGE_NAME,
    RVC_NEXT_TORCH_MIN_VERSION,
    RVC_NEXT_WEBUI_REPO,
)
from sd_webui_all_in_one.base_manager.rvc_next_webui_base.shared import logger

PYTORCH_PACKAGE_NAMES = {"torch", "torchvision", "torchaudio"}
"""由 PyTorch 安装流程管理的软件包, 不在依赖检查中自动安装"""


class RvcNextEnvCheckName(EnvCheckName):
    """RVC Next WebUI 环境检查任务名称。"""

    PYTHON_DEPENDENCIES = "python-dependencies"
    TORCH_LIBOMP = "torch-libomp"
    TORCH_VERSION = "torch-version"


def check_rvc_next_pytorch_package(
    pytorch_package: str | None,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
) -> None:
    """检查将要安装的 PyTorch 是否满足 RVC Next 的要求

    Args:
        pytorch_package (str | None):
            PyTorch 软件包版本声明
        pytorch_mirror_type (PyTorchDeviceType | None):
            指定的 PyTorch 镜像源类型

    Raises:
        ValueError:
            PyTorch 类型为 DirectML 或版本低于 RVC Next 的最低要求时
    """
    if pytorch_mirror_type == "directml" or (pytorch_package is not None and "torch-directml" in pytorch_package):
        raise ValueError("RVC Next WebUI 不支持 DirectML 版本的 PyTorch, 请选择其他类型的 PyTorch")

    torch_requirement = find_torch_requirement(pytorch_package or "")
    if torch_requirement is None or not torch_requirement.specifier:
        return

    torch_version = Version.try_parse(torch_requirement.specifier.specifiers[0].version)
    if torch_version is not None and torch_version.without_local() < Version.parse(RVC_NEXT_TORCH_MIN_VERSION):
        raise ValueError(f"RVC Next WebUI 需要 {RVC_NEXT_TORCH_MIN_VERSION} 及以上版本的 PyTorch, 当前选择的 PyTorch 版本为 {torch_version}")


def check_rvc_next_webui_dependencies(
    requirement_path: Path,
    use_uv: bool = True,
    custom_env: dict[str, str] | None = None,
) -> None:
    """检查 RVC Next WebUI 依赖及 RVC Next 自身声明的依赖, 缺失时进行安装

    ``requirements.txt`` 只记录 RVC Next, RVC Next 的依赖需要从软件包元数据中检查.
    PyTorch 缺失或版本过低时不自动安装, 避免从默认 PyPI 源安装错误类型的 PyTorch.

    Args:
        requirement_path (Path):
            RVC Next WebUI 依赖文件路径
        use_uv (bool):
            是否使用 uv 安装依赖
        custom_env (dict[str, str] | None):
            环境变量字典

    Raises:
        FileNotFoundError:
            未找到依赖文件时
        RuntimeError:
            PyTorch 不满足要求或安装依赖发生错误时
    """
    if not requirement_path.is_file():
        raise FileNotFoundError(f"未在 '{requirement_path}' 找到依赖文件, 无法检查依赖完整性")

    torch_requirement = f"torch>={RVC_NEXT_TORCH_MIN_VERSION}"
    if not is_package_installed(torch_requirement):
        raise RuntimeError(f"当前环境的 PyTorch 未安装或版本低于 {RVC_NEXT_TORCH_MIN_VERSION}, 请使用 PyTorch 重装工具重新安装 PyTorch")

    logger.info("检查 RVC Next WebUI 依赖完整性中")
    missing: list[str] = []
    if validate_requirements(requirement_path):
        missing = [declaration for declaration in get_missing_package_metadata_dependencies(RVC_NEXT_PACKAGE_NAME) if Requirement.parse(declaration).normalized_name not in PYTORCH_PACKAGE_NAMES]
        if not missing:
            logger.info("RVC Next WebUI 依赖完整性检查完成")
            return
        logger.debug("RVC Next 缺失的依赖: %s", missing)

    logger.info("安装 RVC Next WebUI 依赖中")
    try:
        install_requirements(
            path=requirement_path,
            use_uv=use_uv,
            cwd=requirement_path.parent,
            custom_env=custom_env,
        )
    except RuntimeError as e:
        raise RuntimeError(f"安装 RVC Next WebUI 依赖时出现错误: {e}") from e

    logger.info("RVC Next WebUI 依赖完整性检查完成")


def install_rvc_next_webui(
    rvc_next_webui_path: Path,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    use_pypi_mirror: bool = True,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """安装 RVC Next WebUI

    Args:
        rvc_next_webui_path (Path):
            RVC Next WebUI 根目录
        pytorch_mirror_type (PyTorchDeviceType | None):
            设置使用的 PyTorch 镜像源类型
        custom_pytorch_package (str | None):
            自定义 PyTorch 软件包版本声明, 例如: `torch==2.8.0+cu128 torchvision==0.23.0+cu128`
        use_pypi_mirror (bool):
            是否使用国内 PyPI 镜像源
        use_uv (bool):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源

    Raises:
        ValueError:
            选择的 PyTorch 不满足 RVC Next 的要求时
        FileNotFoundError:
            RVC Next WebUI 依赖文件缺失时
    """
    logger.info("准备 RVC Next WebUI 安装配置")

    # 准备 PyTorch 安装信息, RVC Next 不需要 xFormers
    pytorch_package, _, custom_env_pytorch = prepare_pytorch_install_info(
        pytorch_mirror_type=pytorch_mirror_type,
        custom_pytorch_package=custom_pytorch_package,
        use_cn_mirror=use_pypi_mirror,
    )
    check_rvc_next_pytorch_package(pytorch_package, pytorch_mirror_type)

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

    logger.info("RVC Next WebUI 安装配置准备完成")
    logger.info("开始安装 RVC Next WebUI, 安装路径: %s", rvc_next_webui_path)

    logger.info("安装 RVC Next WebUI 内核中")
    clone_repo(
        repo=RVC_NEXT_WEBUI_REPO,
        path=rvc_next_webui_path,
    )

    install_pytorch_for_webui(
        pytorch_package=pytorch_package,
        xformers_package=None,
        custom_env=custom_env_pytorch,
        use_uv=use_uv,
    )
    requirements_path = rvc_next_webui_path / "requirements.txt"

    if not requirements_path.is_file():
        raise FileNotFoundError("未找到 RVC Next WebUI 依赖文件记录表, 请检查 RVC Next WebUI 文件是否完整")

    logger.info("安装 RVC Next WebUI 依赖中")
    install_requirements(
        path=requirements_path,
        use_uv=use_uv,
        custom_env=custom_env,
        cwd=rvc_next_webui_path,
    )

    logger.info("安装 RVC Next WebUI 完成")


def update_rvc_next_webui(
    rvc_next_webui_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 RVC Next WebUI

    Args:
        rvc_next_webui_path (Path):
            RVC Next WebUI 根目录
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
    """
    logger.info("更新 RVC Next WebUI 中")

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)

    git_warpper.update(rvc_next_webui_path)

    logger.info("更新 RVC Next WebUI 完成")


def check_rvc_next_webui_env(
    rvc_next_webui_path: Path,
    use_uv: bool = True,
    use_pypi_mirror: bool = False,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    include_checks: list[str] | None = None,
    exclude_checks: list[str] | None = None,
) -> None:
    """检查 RVC Next WebUI 运行环境

    Args:
        rvc_next_webui_path (Path):
            RVC Next WebUI 根目录
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
            检查 RVC Next WebUI 环境发生错误时
        FileNotFoundError:
            未找到 RVC Next WebUI 依赖文件记录表时
    """
    req_path = rvc_next_webui_path / "requirements.txt"

    if not req_path.is_file():
        raise FileNotFoundError("未找到 RVC Next WebUI 依赖文件记录表, 请检查文件是否完整")

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
    tasks: list[EnvCheckTask[RvcNextEnvCheckName]] = [
        EnvCheckTask(RvcNextEnvCheckName.PYTHON_DEPENDENCIES, check_rvc_next_webui_dependencies, {"requirement_path": req_path, "use_uv": use_uv, "custom_env": custom_env}),
        EnvCheckTask(RvcNextEnvCheckName.TORCH_LIBOMP, fix_torch_libomp, {}),
        EnvCheckTask(RvcNextEnvCheckName.TORCH_VERSION, check_torch_version, {}),
    ]
    run_env_check_tasks(
        tasks,
        include_checks=include_checks,
        exclude_checks=exclude_checks,
        error_message="检查 RVC Next WebUI 环境时发生错误",
    )

    logger.info("检查 RVC Next WebUI 环境完成")
