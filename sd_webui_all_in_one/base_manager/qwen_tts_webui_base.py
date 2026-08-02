"""Qwen TTS WebUI 管理器模块"""

import importlib
import os
from pathlib import Path

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    EnvCheckTask,
    WebUiLaunchInfo,
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
    apply_hf_mirror,
    clone_repo,
    install_pytorch_for_webui,
    launch_webui,
    prepare_pytorch_install_info,
    run_env_check_tasks,
)
from sd_webui_all_in_one.base_manager.hotpatcher_manager import DEFAULT_RUNTIME_PORT, apply_hotpatcher_launch_env
from sd_webui_all_in_one.base_manager.snapshot import WebUiSnapshot, build_webui_snapshot
from sd_webui_all_in_one.base_manager.version_manager import WebUiUpdateOptions, WebUiUpdateStatus, check_webui_updates
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
    ROOT_PATH,
)
from sd_webui_all_in_one.env_check import (
    check_torch_version,
    fix_torch_libomp,
    py_dependency_checker,
)
from sd_webui_all_in_one.file_manager import copy_files
from sd_webui_all_in_one.launch_arguments import (
    DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    LaunchArgumentCatalog,
    build_script_help_command,
    discover_launch_argument_catalog,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
    HUGGINGFACE_MIRROR_LIST,
    get_pypi_mirror_config,
)
from sd_webui_all_in_one.model_downloader import ModelDownloadUrlType
from sd_webui_all_in_one.optimize import (
    apply_pytorch_alloc_conf,
    get_cuda_malloc_var,
)
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one.pytorch_manager import PyTorchDeviceType
from sd_webui_all_in_one.utils import TemporaryModulePath

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

QWEN_TTS_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY = "qwen_tts_webui.cmd_args:get_args_parser"
"""Qwen TTS WebUI 启动参数对象解析器的稳定标识。"""


def get_qwen_tts_webui_launch_argument_catalog(
    qwen_tts_webui_path: str | Path,
    use_parser_object: bool = True,
    *,
    python_executable: str | Path | None = None,
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
) -> LaunchArgumentCatalog:
    """发现 Qwen TTS 启动参数，对象解析失败时回退到 ``--help``。

    Args:
        qwen_tts_webui_path (str | Path): Qwen TTS WebUI 根目录。
        use_parser_object (bool): 是否优先解析实际参数对象。
        python_executable (str | Path | None): 执行 ``--help`` 的 Python。
        timeout_seconds (float): ``--help`` 命令超时秒数。

    Returns:
        LaunchArgumentCatalog: 规范化的启动参数目录。
    """
    path = Path(qwen_tts_webui_path)

    def load_parser():
        with TemporaryModulePath(path):
            return importlib.import_module("qwen_tts_webui.cmd_args").get_args_parser()

    return discover_launch_argument_catalog(
        "qwen_tts_webui",
        path,
        provider_identity=QWEN_TTS_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
        help_command_factory=lambda context: build_script_help_command(context, ("launch.py",)),
        parser_loader=load_parser,
        parser_source_identity="qwen_tts_webui.cmd_args:get_args_parser",
        use_parser_object=use_parser_object,
        python_executable=python_executable,
        timeout_seconds=timeout_seconds,
    )


QWEN_TTS_WEBUI_PRESET_HF_PATH = ROOT_PATH / "base_manager" / "config" / "qwen_tts_webui_config_huggingface.json"
"""Qwen TTS WebUI 预设配置文件路径, 使用 HuggingFace 下载源"""

QWEN_TTS_WEBUI_PRESET_MS_PATH = ROOT_PATH / "base_manager" / "config" / "qwen_tts_webui_config_modelscope.json"
"""Qwen TTS WebUI 预设配置文件路径, 使用 ModelScope 下载源"""

QWEN_TTS_WEBUI_REPO = "https://github.com/licyk/qwen-tts-webui"
"""Qwen TTS WebUI 仓库地址"""


def install_qwen_tts_webui_config(
    qwen_tts_webui_path: Path,
    download_resource_type: ModelDownloadUrlType | bool = False,
) -> None:
    """安装 Qwen TTS WebUI 配置文件
    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录
        download_resource_type (ModelDownloadUrlType | bool):
            默认配置资源来源

    Raises:
        ValueError:
            未知的下载配置源类型时抛出。
    """
    if not download_resource_type:
        return

    preset_path = qwen_tts_webui_path / "config.json"
    if download_resource_type == "huggingface":
        preset = QWEN_TTS_WEBUI_PRESET_HF_PATH
    elif download_resource_type == "modelscope":
        preset = QWEN_TTS_WEBUI_PRESET_MS_PATH
    else:
        raise ValueError(f"未知的下载配置源类型: {download_resource_type}")

    if not preset_path.exists():
        copy_files(preset, preset_path)


def install_qwen_tts_webui(
    qwen_tts_webui_path: Path,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_pypi_mirror: bool = True,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    no_pre_download_model: bool = False,
    model_download_resource_type: ModelDownloadUrlType | None = "modelscope",
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
        use_pypi_mirror (bool):
            是否使用国内 PyPI 镜像源
        use_uv (bool):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        no_pre_download_model (bool):
            是否禁用预下载模型
        model_download_resource_type (ModelDownloadUrlType | None):
            下载模型使用的下载源

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
    apply_git_config_global_to_process(custom_env)

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

    config_download_resource_type: ModelDownloadUrlType | bool = False if no_pre_download_model or model_download_resource_type is None else model_download_resource_type
    install_qwen_tts_webui_config(
        qwen_tts_webui_path=qwen_tts_webui_path,
        download_resource_type=config_download_resource_type,
    )

    logger.info("安装 Qwen TTS WebUI 完成")


def update_qwen_tts_webui(
    qwen_tts_webui_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 Qwen TTS WebUI

    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录
        use_github_mirror (bool):
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
    apply_git_config_global_to_process(custom_env)

    git_warpper.update(qwen_tts_webui_path)

    logger.info("更新 Qwen TTS WebUI 完成")


def check_qwen_tts_webui_updates(
    qwen_tts_webui_path: Path,
    options: WebUiUpdateOptions | None = None,
) -> WebUiUpdateStatus:
    """检查 Qwen TTS WebUI 的内核和 PyTorch 更新。

    Args:
        qwen_tts_webui_path (Path): Qwen TTS WebUI 根目录。
        options (WebUiUpdateOptions | None): 更新检查选项。

    Returns:
        WebUiUpdateStatus: 结构化更新检查结果。
    """
    return check_webui_updates("qwen_tts_webui", "Qwen TTS WebUI", qwen_tts_webui_path, options=options)


def get_qwen_tts_webui_snapshot(
    qwen_tts_webui_path: Path,
    include_packages: bool = True,
) -> WebUiSnapshot:
    """获取 Qwen TTS WebUI 环境快照

    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录
        include_packages (bool):
            是否记录当前 Python 环境已安装软件包

    Returns:
        WebUiSnapshot:
            Qwen TTS WebUI 环境快照
    """
    return build_webui_snapshot(
        webui_name="Qwen TTS WebUI",
        webui_type="qwen_tts_webui",
        webui_path=qwen_tts_webui_path,
        include_packages=include_packages,
    )


def check_qwen_tts_webui_env(
    qwen_tts_webui_path: Path,
    use_uv: bool = True,
    use_pypi_mirror: bool = False,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    include_checks: list[str] | None = None,
    exclude_checks: list[str] | None = None,
) -> None:
    """检查 Qwen TTS WebUI 运行环境

    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录
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
            检查 Qwen TTS WebUI 环境发生错误时
        FileNotFoundError:
            未找到 Qwen TTS WebUI 依赖文件记录表时
    """
    req_path = qwen_tts_webui_path / "requirements.txt"

    if not req_path.is_file():
        raise FileNotFoundError("未找到 Qwen TTS WebUI 依赖文件记录表, 请检查文件是否完整")

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
        EnvCheckTask("python-dependencies", py_dependency_checker, {"requirement_path": req_path, "name": "Qwen TTS WebUI", "use_uv": use_uv, "custom_env": custom_env}),
        EnvCheckTask("torch-libomp", fix_torch_libomp, {}),
        EnvCheckTask("torch-version", check_torch_version, {}),
    ]
    run_env_check_tasks(
        tasks,
        include_checks=include_checks,
        exclude_checks=exclude_checks,
        error_message="检查 Qwen TTS WebUI 环境时发生错误",
    )

    logger.info("检查 Qwen TTS WebUI 环境完成")


def prepare_qwen_tts_webui_launch(
    qwen_tts_webui_path: Path,
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
    """准备 Qwen TTS WebUI 启动参数。

    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录
        launch_args (list[str] | None):
            启动 Qwen TTS WebUI 的参数
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
        WebUiLaunchInfo: Qwen TTS WebUI 启动参数信息。
    """
    logger.info("准备 Qwen TTS WebUI 启动环境")

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)

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
        webui_path=qwen_tts_webui_path,
        launch_script="launch.py",
        webui_name="Qwen TTS WebUI",
        launch_args=(launch_args or []) + hf_mirror_args,
        custom_env=custom_env,
    )


def launch_qwen_tts_webui(
    qwen_tts_webui_path: Path,
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
    """启动 Qwen TTS WebUI

    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录
        launch_args (list[str] | None):
            启动 Qwen TTS WebUI 的参数
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
    launch_info = prepare_qwen_tts_webui_launch(
        qwen_tts_webui_path=qwen_tts_webui_path,
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

    logger.info("启动 Qwen TTS WebUI 中")
    launch_webui(
        webui_path=launch_info.webui_path,
        launch_script=launch_info.launch_script,
        webui_name=launch_info.webui_name,
        launch_args=launch_info.launch_args,
        custom_env=launch_info.custom_env,
    )


def launch_qwen_tts_webui_version_gui(
    qwen_tts_webui_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """启动 Qwen TTS WebUI 版本管理 GUI

    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源

    Raises:
        RuntimeError:
            环境未安装 tkinter 或者导入 GUI 模块失败时
    """
    try:
        from sd_webui_all_in_one.base_manager.gui.git_kernel_version_gui import launch_git_kernel_version_gui
    except ModuleNotFoundError as e:
        if e.name == "tkinter":
            raise RuntimeError("当前 Python 环境未安装 tkinter, 无法启动版本管理 GUI") from e
        raise RuntimeError(f"导入 GUI 管理模块发生错误: {e}") from e

    launch_git_kernel_version_gui(
        title="Qwen TTS WebUI",
        root_path=qwen_tts_webui_path,
        branch_presets=[{"name": "licyk - Qwen TTS WebUI", "url": QWEN_TTS_WEBUI_REPO, "branch": "main", "use_submodule": False}],
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def launch_qwen_tts_webui_snapshot_gui(
    qwen_tts_webui_path: Path,
    snapshot_dir: Path | None = None,
    use_uv: bool = True,
    use_pypi_mirror: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """启动 Qwen TTS WebUI 快照管理 GUI

    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录。
        snapshot_dir (Path | None):
            快照文件目录。
        use_uv (bool):
            是否使用 uv 执行 Python 包安装。
        use_pypi_mirror (bool):
            是否使用 PyPI 镜像源。
        use_github_mirror (bool):
            是否使用 GitHub 镜像源。
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源。

    Raises:
        RuntimeError:
            当恢复或 GUI 启动无法安全继续时抛出。
    """
    try:
        from sd_webui_all_in_one.base_manager.gui.snapshot_gui import launch_snapshot_manager_gui
    except ModuleNotFoundError as e:
        if e.name == "tkinter":
            raise RuntimeError("当前 Python 环境未安装 tkinter, 无法启动快照管理 GUI") from e
        raise RuntimeError(f"导入 GUI 管理模块发生错误: {e}") from e

    launch_snapshot_manager_gui(
        title="Qwen TTS WebUI",
        webui_type="qwen_tts_webui",
        webui_path=qwen_tts_webui_path,
        snapshot_factory=lambda include_packages: get_qwen_tts_webui_snapshot(qwen_tts_webui_path, include_packages=include_packages),
        snapshot_dir=snapshot_dir,
        use_uv=use_uv,
        use_pypi_mirror=use_pypi_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )
