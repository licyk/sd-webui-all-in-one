"""Implementation grouped from the former ``invokeai_base.py`` module."""

from __future__ import annotations

import importlib
import importlib.metadata
import os
from pathlib import Path
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
    pre_download_model_for_webui,
    EnvCheckTask,
    run_env_check_tasks,
)
from sd_webui_all_in_one.env_check import (
    check_torch_version,
    fix_torch_libomp,
    check_onnxruntime_gpu,
    py_package_metadata_dependency_checker,
)
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
    get_pypi_mirror_config,
)
from sd_webui_all_in_one.model_downloader import ModelDownloadUrlType
from sd_webui_all_in_one.package_analyzer import (
    get_package_name,
    get_package_version,
    get_package_version_specs,
    is_package_has_version,
    version_decrement,
    version_increment,
)
from sd_webui_all_in_one.pytorch_manager import (
    get_env_pytorch_type,
    PyTorchDeviceTypeCategory,
)
from sd_webui_all_in_one.config import (
    ROOT_PATH,
)

from sd_webui_all_in_one.base_manager.invokeai_base.components import _ensure_invokeai_package_installed, install_invokeai_component, install_pypatchmatch
from sd_webui_all_in_one.base_manager.invokeai_base.model_management import import_model_to_invokeai
from sd_webui_all_in_one.base_manager.invokeai_base.shared import logger

INVOKEAI_RUNNER_SCRIPT = ROOT_PATH / "base_manager" / "run_invokeai.py"


def get_invokeai_require_torch_version() -> str:
    """获取 InvokeAI 依赖的 PyTorch 版本

    Returns:
        str:
            PyTorch 版本
    """
    try:
        invokeai_requires = importlib.metadata.requires("invokeai") or []
    except Exception:
        return "2.2.2"

    torch_version = "torch==2.2.2"

    for require in invokeai_requires:
        if get_package_name(require) == "torch" and is_package_has_version(require):
            torch_version = require.split(";")[0]
            break

    specs = get_package_version_specs(torch_version)
    if not specs:
        return get_package_version(torch_version)

    # 按操作符优先级选择最合适的版本约束:
    # 优先使用精确匹配 (==, ===), 其次使用下界 (>=, >), 最后使用上界 (<, <=)
    specs_dict: dict[str, str] = {op: ver for op, ver in specs}

    if "==" in specs_dict:
        return specs_dict["=="]
    if "===" in specs_dict:
        return specs_dict["==="]
    if "~=" in specs_dict:
        return specs_dict["~="]
    if ">=" in specs_dict:
        return specs_dict[">="]
    if ">" in specs_dict:
        return version_increment(specs_dict[">"])
    if "!=" in specs_dict:
        return version_increment(specs_dict["!="])
    if "<" in specs_dict:
        return version_decrement(specs_dict["<"])
    if "<=" in specs_dict:
        return specs_dict["<="]

    # 回退: 返回第一个约束的版本号
    return specs[0][1]


def init_invokeai_default_config(
    invokeai_path: Path,
) -> None:
    """初始化 InvokeAI 默认配置文件

    Args:
        invokeai_path (Path):
            InvokeAI 根目录

    Raises:
        ImportError:
            导入 InvokeAI 模块发生错误时
        RuntimeError:
            初始化 InvokeAI 默认配置文件发生错误时
    """
    config_path = invokeai_path / "invokeai.yaml"
    if config_path.is_file():
        logger.info("InvokeAI 默认配置已存在, 跳过配置文件初始化")
        return
    try:
        logger.info("导入 InvokeAI 配置模块中")
        from invokeai.app.services.config.config_default import DefaultInvokeAIAppConfig  # ty: ignore[unresolved-import]
    except ImportError as e:
        logger.error("导入 InvokeAI 模块失败, 跳过初始化配置文件: %s", e)
        raise ImportError(f"导入 InvokeAI 模块发生错误: {e}") from e

    logger.info("初始化 InvokeAI 默认配置文件: %s", config_path)
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        DefaultInvokeAIAppConfig().write_file(config_path, as_example=False)
    except Exception as e:
        logger.error("初始化 InvokeAI 默认配置文件失败: %s", e)
        raise RuntimeError(f"初始化 InvokeAI 默认配置文件发生错误: {e}") from e

    logger.info("初始化 InvokeAI 配置文件完成")


def install_invokeai(
    invokeai_path: Path,
    device_type: PyTorchDeviceTypeCategory | None = None,
    invokeai_version: str | None = None,
    use_pypi_mirror: bool = True,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    no_pre_download_model: bool = False,
    model_download_resource_type: ModelDownloadUrlType | None = "modelscope",
) -> None:
    """安装 InvokeAI

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        device_type (PyTorchDeviceTypeCategory | None):
            设置使用的 PyTorch 镜像源类型
        invokeai_version (str | None):
            自定义安装 InvokeAI 的版本
        use_pypi_mirror (bool):
            是否使用国内 PyPI 镜像源
        use_uv (bool):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool):
            是否启用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        no_pre_download_model (bool):
            是否禁用预下载模型
        model_download_resource_type (ModelDownloadUrlType | None):
            下载模型使用的下载源
    """
    logger.info("准备 InvokeAI 安装配置")

    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)
    logger.info("开始安装 InvokeAI, 安装路径: %s", invokeai_path)

    install_invokeai_component(
        device_type=device_type,
        invokeai_version=invokeai_version,
        use_pypi_mirror=use_pypi_mirror,
        use_uv=use_uv,
    )

    install_pypatchmatch(
        use_cn_mirror=use_pypi_mirror,
    )

    init_invokeai_default_config(invokeai_path)

    if not no_pre_download_model:
        model_path = invokeai_path / "models" / "checkpoints"
        model_path.mkdir(parents=True, exist_ok=True)
        save_paths = pre_download_model_for_webui(
            dtype="invokeai",
            model_path=invokeai_path / "models" / "checkpoints",
            webui_base_path=invokeai_path,
            model_name="ChenkinNoob-XL-V0.2",
            download_resource_type=model_download_resource_type,
        )
        if save_paths is not None:
            import_model_to_invokeai(model_list=[save_paths], invokeai_path=invokeai_path)

    logger.info("安装 InvokeAI 完成")


def update_invokeai(
    use_pypi_mirror: bool = False,
    use_uv: bool = False,
) -> None:
    """更新 InvokeAI

    Args:
        use_pypi_mirror (bool):
            是否使用国内 PyPI 镜像源
        use_uv (bool):
            是否使用 uv 安装 Python 软件包
    """
    logger.info("更新 InvokeAI 中")
    install_invokeai_component(
        device_type=get_env_pytorch_type(),
        upgrade=True,
        use_pypi_mirror=use_pypi_mirror,
        use_uv=use_uv,
    )
    logger.info("更新 InvokeAI 完成")


def check_invokeai_env(
    use_uv: bool = True,
    use_pypi_mirror: bool = False,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    include_checks: list[str] | None = None,
    exclude_checks: list[str] | None = None,
) -> None:
    """检查 InvokeAI 运行环境

    Args:
        use_uv (bool):
            使用 uv 安装依赖
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
            检查 InvokeAI 环境发生错误时
    """
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
        EnvCheckTask("invokeai-package", _ensure_invokeai_package_installed, {"use_uv": use_uv, "custom_env": custom_env}),
        EnvCheckTask("invokeai-package-dependencies", py_package_metadata_dependency_checker, {"package_name": "invokeai", "name": "InvokeAI", "use_uv": use_uv, "custom_env": custom_env}),
        EnvCheckTask("torch-libomp", fix_torch_libomp, {}),
        EnvCheckTask("torch-version", check_torch_version, {}),
        EnvCheckTask("onnxruntime-gpu", check_onnxruntime_gpu, {"use_uv": use_uv, "skip_if_missing": True, "custom_env": custom_env}),
    ]
    run_env_check_tasks(
        tasks,
        include_checks=include_checks,
        exclude_checks=exclude_checks,
        error_message="检查 InvokeAI 环境时发生错误",
    )

    logger.info("检查 InvokeAI 环境完成")
