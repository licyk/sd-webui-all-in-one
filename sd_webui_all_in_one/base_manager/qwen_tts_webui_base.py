import os
from pathlib import Path
from typing import Any, Callable


from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    apply_hf_mirror,
    clone_repo,
    install_pytorch_for_webui,
    launch_webui,
    prepare_pytorch_install_info,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.env_check.fix_dependencies import py_dependency_checker
from sd_webui_all_in_one.env_check.fix_torch import fix_torch_libomp
from sd_webui_all_in_one.file_operations.file_manager import copy_files
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR, ROOT_PATH
from sd_webui_all_in_one.mirror_manager import GITHUB_MIRROR_LIST, HUGGINGFACE_MIRROR_LIST, get_pypi_mirror_config
from sd_webui_all_in_one.optimize.cuda_malloc import get_cuda_malloc_var
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one.pytorch_manager.base import PyTorchDeviceType

logger = get_logger(
    name="Qwen TTS WebUI Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


QWEN_TTS_WEBUI_PRESET_HF_PATH = ROOT_PATH / "base_manager" / "config" / "qwen_tts_webui_config_huggingface.json"
"""Qwen TTS WebUI 预设配置文件路径, 使用 HuggingFace 下载源"""

QWEN_TTS_WEBUI_PRESET_MS_PATH = ROOT_PATH / "base_manager" / "config" / "qwen_tts_webui_config_modelscope.json"
"""Qwen TTS WebUI 预设配置文件路径, 使用 ModelScope 下载源"""

QWEN_TTS_WEBUI_REPO = "https://github.com/licyk/qwen-tts-webui"
"""Qwen TTS WebUI 仓库地址"""


def install_qwen_tts_webui_config(
    qwen_tts_webui_path: Path,
    use_cn_model_mirror: bool | None = False,
) -> None:
    """安装 Qwen TTS WebUI 配置文件
    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录

    """
    preset_path = qwen_tts_webui_path / "config.json"
    if not preset_path.exists():
        copy_files(QWEN_TTS_WEBUI_PRESET_MS_PATH if use_cn_model_mirror else QWEN_TTS_WEBUI_PRESET_HF_PATH, preset_path)


def install_qwen_tts_webui(
    qwen_tts_webui_path: Path,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_pypi_mirror: bool | None = True,
    use_uv: bool | None = True,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    use_cn_model_mirror: bool | None = True,
) -> None:
    """安装 Qwen TTS WebUI

    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录
        pytorch_mirror_type (PyTorchDeviceType | None):
            设置使用的 PyTorch 镜像源类型
        custom_pytorch_package (str | None):
            自定义 PyTorch 软件包版本声明, 例如: `torch==2.3.0+cu118 torchvision==0.18.0+cu118`
        custom_xformers_package (str | None):
            自定义 xFormers 软件包版本声明, 例如: `xformers===0.0.26.post1+cu118`
        use_pypi_mirror (bool | None):
            是否使用国内 PyPI 镜像源
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        use_cn_model_mirror (bool | None):
            是否使用国内镜像下载模型

    Raises:
        ValueError:
            安装的 Qwen TTS WebUI 分支未知时
        FileNotFoundError:
            Qwen TTS WebUI 依赖文件缺失时
    """
    logger.info("准备 Qwen TTS WebUI 安装配置")

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
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

    logger.debug("安装的 PyTorch 版本: %s", pytorch_package)
    logger.debug("安装的 xformers: %s", xformers_package)

    logger.info("Qwen TTS WebUI 安装配置准备完成")
    logger.info("开始安装 Qwen TTS WebUI, 安装路径: %s", qwen_tts_webui_path)

    logger.info("安装 Qwen TTS WebUI 内核中")
    clone_repo(
        repo=QWEN_TTS_WEBUI_REPO,
        path=qwen_tts_webui_path,
    )

    install_pytorch_for_webui(
        pytorch_package=pytorch_package,
        xformers_package=xformers_package,
        custom_env=custom_env_pytorch,
        use_uv=use_uv,
    )
    requirements_path = qwen_tts_webui_path / "requirements.txt"

    if not requirements_path.is_file():
        raise FileNotFoundError("未找到 Qwen TTS WebUI 依赖文件记录表, 请检查 Qwen TTS WebUI 文件是否完整")

    logger.info("安装 Qwen TTS WebUI 依赖中")
    install_requirements(
        path=requirements_path,
        use_uv=use_uv,
        custom_env=custom_env,
        cwd=qwen_tts_webui_path,
    )

    install_qwen_tts_webui_config(
        qwen_tts_webui_path=qwen_tts_webui_path,
        use_cn_model_mirror=use_cn_model_mirror,
    )

    logger.info("安装 Qwen TTS WebUI 完成")


def update_qwen_tts_webui(
    qwen_tts_webui_path: Path,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 Qwen TTS WebUI

    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
    """
    logger.info("更新 Qwen TTS WebUI 中")

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

    git_warpper.update(qwen_tts_webui_path)

    logger.info("更新 Qwen TTS WebUI 完成")


def check_qwen_tts_webui_env(
    qwen_tts_webui_path: Path,
    use_uv: bool | None = True,
    use_pypi_mirror: bool | None = False,
) -> None:
    """检查 Qwen TTS WebUI 运行环境

    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        use_pypi_mirror (bool | None):
            是否使用国内 PyPI 镜像源

    Raises:
        AggregateError:
            检查 Qwen TTS WebUI 环境发生错误时
        FileNotFoundError:
            未找到 Qwen TTS WebUI 依赖文件记录表时
    """
    req_path = qwen_tts_webui_path / "requirements.txt"

    if not req_path.is_file():
        raise FileNotFoundError("未找到 Qwen TTS WebUI 依赖文件记录表, 请检查文件是否完整")

    # 准备安装依赖的 PyPI 镜像源
    custom_env = get_pypi_mirror_config(
        use_cn_mirror=use_pypi_mirror,
        origin_env=os.environ.copy(),
    )

    # 检查任务列表
    tasks: list[tuple[Callable, dict[str, Any]]] = [
        (py_dependency_checker, {"requirement_path": req_path, "name": "Qwen TTS WebUI", "use_uv": use_uv, "custom_env": custom_env}),
        (fix_torch_libomp, {}),
    ]
    err: list[Exception] = []

    for func, kwargs in tasks:
        try:
            func(**kwargs)
        except Exception as e:
            err.append(e)
            logger.error("执行 '%s' 时发生错误: %s", func.__name__, e)

    if err:
        raise AggregateError("检查 Qwen TTS WebUI 环境时发生错误", err)

    logger.info("检查 Qwen TTS WebUI 环境完成")


def launch_qwen_tts_webui(
    qwen_tts_webui_path: Path,
    launch_args: list[str] | None = None,
    use_hf_mirror: bool | None = False,
    custom_hf_mirror: str | list[str] | None = None,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool | None = False,
    use_cuda_malloc: bool | None = True,
) -> None:
    """启动 Qwen TTS WebUI

    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录
        launch_args (list[str] | None):
            启动 Qwen TTS WebUI 的参数
        use_hf_mirror (bool | None):
            是否启用 HuggingFace 镜像源
        custom_hf_mirror (str | list[str] | None):
            自定义 HuggingFace 镜像源
        use_github_mirror (bool | None):
            是否启用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        use_pypi_mirror (bool | None):
            是否启用 PyPI 镜像源
        use_cuda_malloc (bool | None):
            是否启用 CUDA Malloc 显存优化
    """
    logger.info("准备 Qwen TTS WebUI 启动环境")

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

    hf_mirror_args: list[str] = []

    if use_hf_mirror:
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
            custom_env["PYTORCH_ALLOC_CONF"] = cuda_malloc_config
            custom_env["PYTORCH_CUDA_ALLOC_CONF"] = cuda_malloc_config

    logger.info("启动 Qwen TTS WebUI 中")
    launch_webui(
        webui_path=qwen_tts_webui_path,
        launch_script="launch.py",
        webui_name="Qwen TTS WebUI",
        launch_args=launch_args + hf_mirror_args,
        custom_env=custom_env,
    )
