"""SD Trainer 命令行工具"""

import argparse
import shlex
import sys
import traceback
from pathlib import Path

from sd_webui_all_in_one.base_manager import (
    SD_TRAINER_BRANCH_LIST,
    SDTrainerBranchType,
    install_sd_trainer,
    update_sd_trainer,
    check_sd_trainer_env,
    switch_sd_trainer_branch,
    launch_sd_trainer,
    install_sd_trainer_model_from_library,
    install_sd_trainer_model_from_url,
    list_sd_trainer_models,
    uninstall_sd_trainer_model,
    launch_sd_trainer_version_gui,
    launch_sd_trainer_snapshot_gui,
    launch_sd_trainer_model_manager_gui,
    reinstall_pytorch as reinstall_base_pytorch,
    get_sd_trainer_snapshot,
)
from sd_webui_all_in_one.config import (
    SD_TRAINER_ROOT_PATH,
    SD_WEBUI_ALL_IN_ONE_RAISE_WEBUI_RUNTIME_ERROR,
    SD_WEBUI_ALL_IN_ONE_RAISE_CHECK_ENV_ERROR_ON_LAUNCH,
    LOGGER_NAME,
    LOGGER_LEVEL,
    LOGGER_COLOR,
)
from sd_webui_all_in_one.downloader import (
    DOWNLOAD_TOOL_TYPE_LIST,
    DownloadToolType,
)
from sd_webui_all_in_one.model_downloader import (
    MODEL_DOWNLOAD_URL_TYPE_LIST,
    ModelDownloadUrlType,
)
from sd_webui_all_in_one.cli_manager.auto_mirror import (
    add_auto_mirror_argument,
    with_auto_mirror,
)
from sd_webui_all_in_one.cli_manager.snapshot import add_pre_operation_snapshot_arguments, create_pre_operation_snapshot, output_snapshot
from sd_webui_all_in_one.cli_manager.snapshot_restore import (
    add_restore_arguments,
    restore_snapshot,
)
from sd_webui_all_in_one.cli_manager.snapshot_gui import add_snapshot_gui_arguments
from sd_webui_all_in_one.pytorch_manager import (
    PYTORCH_DEVICE_LIST,
    PyTorchDeviceType,
)
from sd_webui_all_in_one.utils import normalized_filepath
from sd_webui_all_in_one.custom_exceptions import WebUiRuntimeError
from sd_webui_all_in_one.logger import get_logger

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def install(
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
    """
    install_sd_trainer(
        sd_trainer_path=sd_trainer_path,
        pytorch_mirror_type=pytorch_mirror_type,
        custom_pytorch_package=custom_pytorch_package,
        custom_xformers_package=custom_xformers_package,
        use_pypi_mirror=use_pypi_mirror,
        use_uv=use_uv,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        install_branch=install_branch,
        no_pre_download_model=no_pre_download_model,
        model_download_resource_type=model_download_resource_type,
    )


def update(
    sd_trainer_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    snapshot_enabled: bool = True,
    snapshot_dir: Path | None = None,
) -> None:
    """更新 SD Trainer

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录。
        use_github_mirror (bool):
            是否使用 GitHub 镜像源。
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源。
        snapshot_enabled (bool):
            是否启用操作前自动快照。
        snapshot_dir (Path | None):
            快照文件目录。
    """
    _create_pre_operation_snapshot(
        sd_trainer_path=sd_trainer_path,
        operation_name="更新 SD Trainer",
        snapshot_enabled=snapshot_enabled,
        snapshot_dir=snapshot_dir,
    )
    update_sd_trainer(
        sd_trainer_path=sd_trainer_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def _create_pre_operation_snapshot(
    sd_trainer_path: Path,
    operation_name: str,
    snapshot_enabled: bool = True,
    snapshot_dir: Path | None = None,
    show_gui_warning: bool = False,
) -> None:
    create_pre_operation_snapshot(
        lambda: get_sd_trainer_snapshot(sd_trainer_path=sd_trainer_path, include_packages=True),
        operation_name=operation_name,
        snapshot_enabled=snapshot_enabled,
        snapshot_dir=snapshot_dir,
        show_gui_warning=show_gui_warning,
    )


def snapshot(
    sd_trainer_path: Path,
    output: Path | None = None,
    include_packages: bool = True,
) -> None:
    """生成 SD Trainer 环境快照

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录。
        output (Path | None):
            快照输出路径或目录。
        include_packages (bool):
            是否采集当前 Python 包列表。
    """
    output_snapshot(
        lambda: get_sd_trainer_snapshot(
            sd_trainer_path=sd_trainer_path,
            include_packages=include_packages,
        ),
        output=output,
    )


def restore(
    snapshot_path: Path,
    sd_trainer_path: Path,
    prune_packages: bool = False,
    prune_extensions: bool = False,
    force_git_reset: bool = False,
    use_uv: bool = True,
    use_pypi_mirror: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """恢复 SD Trainer 环境快照

    Args:
        snapshot_path (Path):
            快照 JSON 文件路径。
        sd_trainer_path (Path):
            SD Trainer 根目录。
        prune_packages (bool):
            是否卸载快照外 Python 包。
        prune_extensions (bool):
            是否删除快照外扩展。
        force_git_reset (bool):
            是否允许覆盖 Git 仓库未提交变更。
        use_uv (bool):
            是否使用 uv 执行 Python 包安装。
        use_pypi_mirror (bool):
            是否使用 PyPI 镜像源。
        use_github_mirror (bool):
            是否使用 GitHub 镜像源。
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源。
    """
    restore_snapshot(
        snapshot_path=snapshot_path,
        webui_path=sd_trainer_path,
        expected_webui_type="sd_trainer",
        prune_packages=prune_packages,
        prune_extensions=prune_extensions,
        force_git_reset=force_git_reset,
        use_uv=use_uv,
        use_pypi_mirror=use_pypi_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def check_env(
    sd_trainer_path: Path,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool = False,
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
            是否启用 PyPI 镜像源
    """
    check_sd_trainer_env(
        sd_trainer_path=sd_trainer_path,
        use_uv=use_uv,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        use_pypi_mirror=use_pypi_mirror,
    )


def switch(
    sd_trainer_path: Path,
    branch: SDTrainerBranchType | None = None,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    interactive_mode: bool = False,
    list_only: bool = False,
    snapshot_enabled: bool = True,
    snapshot_dir: Path | None = None,
) -> None:
    """切换 SD Trainer 分支

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录。
        branch (SDTrainerBranchType | None):
            要切换的 SD Trainer 分支。
        use_github_mirror (bool):
            是否使用 GitHub 镜像源。
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源。
        interactive_mode (bool):
            是否启用交互模式。
        list_only (bool):
            是否仅列出可选分支并退出。
        snapshot_enabled (bool):
            是否启用操作前自动快照。
        snapshot_dir (Path | None):
            快照文件目录。
    """
    if not list_only and (interactive_mode or branch is not None):
        _create_pre_operation_snapshot(
            sd_trainer_path=sd_trainer_path,
            operation_name="切换 SD Trainer 分支",
            snapshot_enabled=snapshot_enabled,
            snapshot_dir=snapshot_dir,
        )
    switch_sd_trainer_branch(
        sd_trainer_path=sd_trainer_path,
        branch=branch,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        interactive_mode=interactive_mode,
        list_only=list_only,
    )


def launch(
    sd_trainer_path: Path,
    launch_args: str | list[str] | None = None,
    use_hf_mirror: bool = False,
    custom_hf_mirror: str | list[str] | None = None,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool = False,
    use_cuda_malloc: bool = True,
    use_uv: bool = True,
    check_launch_env: bool = True,
    enable_hotpatcher: bool = False,
    hotpatcher_config_path: str | Path | None = None,
    hotpatcher_port: int | None = None,
    enable_hotpatcher_runtime: bool = False,
) -> None:
    """启动 SD Trainer

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        launch_args (str | list[str] | None):
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
        use_uv (bool):
            是否使用 uv 安装 Python 软件包
        check_launch_env (bool):
            是否在启动前检查运行环境
        enable_hotpatcher (bool):
            是否启用补丁系统注入
        hotpatcher_config_path (str | Path | None):
            补丁系统配置文件路径
        hotpatcher_port (int | None):
            补丁系统 runtime 通信端口
        enable_hotpatcher_runtime (bool):
            是否启用补丁系统 runtime host 连接

    Raises:
        Exception:
            启动前环境检查失败并需要继续抛出时抛出。
    """
    if check_launch_env:
        try:
            check_sd_trainer_env(
                sd_trainer_path=sd_trainer_path,
                use_uv=use_uv,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
            )
        except Exception as e:
            if SD_WEBUI_ALL_IN_ONE_RAISE_CHECK_ENV_ERROR_ON_LAUNCH:
                raise e

            traceback.print_exc()
            logger.error("检查 SD Trainer 运行环境时发生了错误: %s", e)
            logger.warning("该问题并非致命, 但这可能会导致 SD Trainer 运行时发生问题")

    if isinstance(launch_args, str):
        launch_args = shlex.split(launch_args)
    elif launch_args is None:
        launch_args = []

    try:
        launch_sd_trainer(
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
    except WebUiRuntimeError as e:
        if SD_WEBUI_ALL_IN_ONE_RAISE_WEBUI_RUNTIME_ERROR:
            raise e

        logger.error("运行 SD Trainer 时异常退出: %s", e)
        sys.exit(1)


def install_model_from_library(
    sd_trainer_path: Path,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = None,
    interactive_mode: bool = False,
    list_only: bool = False,
) -> None:
    """为 SD Trainer 下载模型, 使用模型库进行下载

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        download_resource_type (ModelDownloadUrlType | None):
            模型下载源类型
        model_name (str | None):
            下载的模型名称
        model_index (int | None):
            下载的模型在列表中的索引值, 索引值从 1 开始. 当同时提供 `model_name` 和 `model_index` 时, 优先使用 `model_index` 查找模型
        downloader (DownloadToolType | None):
            下载模型使用的工具
        interactive_mode (bool):
            是否启用交互模式
        list_only (bool):
            是否仅列出模型列表并退出
    """
    install_sd_trainer_model_from_library(
        sd_trainer_path=sd_trainer_path,
        download_resource_type=download_resource_type,
        model_name=model_name,
        model_index=model_index,
        downloader=downloader,
        interactive_mode=interactive_mode,
        list_only=list_only,
    )


def install_model_from_url(
    sd_trainer_path: Path,
    model_url: str,
    model_type: str,
    downloader: DownloadToolType | None = None,
) -> None:
    """从链接下载模型到 SD Trainer

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        model_url (str):
            模型下载地址
        model_type (str):
            模型的类型
        downloader (DownloadToolType | None):
            下载模型使用的工具
    """
    install_sd_trainer_model_from_url(
        sd_trainer_path=sd_trainer_path,
        model_url=model_url,
        model_type=model_type,
        downloader=downloader,
    )


def list_models(
    sd_trainer_path: Path,
) -> None:
    """列出 SD Trainer 的模型目录

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
    """
    list_sd_trainer_models(
        sd_trainer_path=sd_trainer_path,
    )


def uninstall_model(
    sd_trainer_path: Path,
    model_name: str,
    model_type: str | None = None,
    interactive_mode: bool = False,
) -> None:
    """卸载 SD Trainer 中的模型

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        model_name (str):
            模型名称
        model_type (str | None):
            模型的类型
        interactive_mode (bool):
            是否启用交互模式
    """
    uninstall_sd_trainer_model(
        sd_trainer_path=sd_trainer_path,
        model_name=model_name,
        model_type=model_type,
        interactive_mode=interactive_mode,
    )


def launch_version_gui(
    sd_trainer_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    snapshot_enabled: bool = True,
    snapshot_dir: Path | None = None,
) -> None:
    """启动 SD Trainer 版本管理 GUI

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录。
        use_github_mirror (bool):
            是否使用 GitHub 镜像源。
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源。
        snapshot_enabled (bool):
            是否启用操作前自动快照。
        snapshot_dir (Path | None):
            快照文件目录。
    """
    _create_pre_operation_snapshot(
        sd_trainer_path=sd_trainer_path,
        operation_name="启动 SD Trainer 版本管理 GUI",
        snapshot_enabled=snapshot_enabled,
        snapshot_dir=snapshot_dir,
        show_gui_warning=True,
    )
    launch_sd_trainer_version_gui(
        sd_trainer_path=sd_trainer_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def reinstall_pytorch(
    sd_trainer_path: Path,
    pytorch_name: str | None = None,
    pytorch_index: int | None = None,
    use_pypi_mirror: bool = True,
    use_uv: bool | None = None,
    interactive_mode: bool = False,
    list_only: bool = False,
    force_reinstall: bool = False,
    snapshot_enabled: bool = True,
    snapshot_dir: Path | None = None,
) -> None:
    """为 SD Trainer 重装 PyTorch

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录。
        pytorch_name (str | None):
            PyTorch 版本条目名称。
        pytorch_index (int | None):
            PyTorch 版本条目索引。
        use_pypi_mirror (bool):
            是否使用 PyPI 镜像源。
        use_uv (bool | None):
            是否使用 uv 执行 Python 包安装。
        interactive_mode (bool):
            是否启用交互模式。
        list_only (bool):
            是否仅列出可选 PyTorch 版本并退出。
        force_reinstall (bool):
            是否强制重新安装。
        snapshot_enabled (bool):
            是否启用操作前自动快照。
        snapshot_dir (Path | None):
            快照文件目录。
    """
    if not list_only:
        _create_pre_operation_snapshot(
            sd_trainer_path=sd_trainer_path,
            operation_name="重装 SD Trainer PyTorch",
            snapshot_enabled=snapshot_enabled,
            snapshot_dir=snapshot_dir,
        )
    reinstall_base_pytorch(
        pytorch_name=pytorch_name,
        pytorch_index=pytorch_index,
        use_pypi_mirror=use_pypi_mirror,
        use_uv=use_uv,
        interactive_mode=interactive_mode,
        list_only=list_only,
        force_reinstall=force_reinstall,
    )


def launch_snapshot_gui(
    sd_trainer_path: Path,
    snapshot_dir: Path | None = None,
    use_uv: bool = True,
    use_pypi_mirror: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """启动 SD Trainer 快照管理 GUI

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录。
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
    """
    launch_sd_trainer_snapshot_gui(
        sd_trainer_path=sd_trainer_path,
        snapshot_dir=snapshot_dir,
        use_uv=use_uv,
        use_pypi_mirror=use_pypi_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def launch_model_gui(
    sd_trainer_path: Path,
) -> None:
    """启动 SD Trainer 模型管理 GUI

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录路径。
    """
    launch_sd_trainer_model_manager_gui(sd_trainer_path=sd_trainer_path)


def register_sd_trainer(
    subparsers: "argparse._SubParsersAction",
) -> None:
    """注册 SD Trainer 模块及其子命令

    Args:
        subparsers (argparse._SubParsersAction):
            子命令行解析器
    """
    trainer_parser: argparse.ArgumentParser = subparsers.add_parser("sd-trainer", help="SD Trainer 相关命令")
    trainer_sub = trainer_parser.add_subparsers(dest="sd_trainer_action", required=True)

    # reinstall-pytorch
    reinstall_pytorch_p = trainer_sub.add_parser("reinstall-pytorch", help="重装 PyTorch")
    reinstall_pytorch_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    reinstall_pytorch_p.add_argument("--name", type=str, dest="name", help="PyTorch 版本组合名称")
    reinstall_pytorch_p.add_argument("--index", type=int, dest="index", help="PyTorch 版本组合索引值")
    reinstall_pytorch_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    reinstall_pytorch_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv 安装 PyTorch 软件包")
    reinstall_pytorch_p.add_argument("--interactive", action="store_true", dest="interactive_mode", help="启用交互模式")
    reinstall_pytorch_p.add_argument("--list-only", action="store_true", dest="list_only", help="列出 PyTorch 列表并退出")
    reinstall_pytorch_p.add_argument("--force-reinstall", action="store_true", dest="force_reinstall", help="强制重装 PyTorch")
    add_pre_operation_snapshot_arguments(reinstall_pytorch_p)
    add_auto_mirror_argument(reinstall_pytorch_p)
    reinstall_pytorch_p.set_defaults(
        func=with_auto_mirror(
            lambda args: reinstall_pytorch(
                sd_trainer_path=args.sd_trainer_path,
                pytorch_name=args.name,
                pytorch_index=args.index,
                use_pypi_mirror=args.use_pypi_mirror,
                use_uv=args.use_uv,
                interactive_mode=args.interactive_mode,
                list_only=args.list_only,
                force_reinstall=args.force_reinstall,
                snapshot_enabled=args.snapshot_enabled,
                snapshot_dir=args.snapshot_dir,
            )
        )
    )

    # install
    install_p = trainer_sub.add_parser("install", help="安装 SD Trainer")
    install_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    install_p.add_argument("--pytorch-mirror-type", type=str, dest="pytorch_mirror_type", choices=PYTORCH_DEVICE_LIST, help="PyTorch 镜像源类型")
    install_p.add_argument("--custom-pytorch-package", type=str, dest="custom_pytorch_package", help="自定义 PyTorch 软件包版本声明")
    install_p.add_argument("--custom-xformers-package", type=str, dest="custom_xformers_package", help="自定义 xFormers 软件包版本声明")
    install_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    install_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv 安装 Python 软件包")
    install_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    install_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    install_p.add_argument("--install-branch", type=str, dest="install_branch", choices=SD_TRAINER_BRANCH_LIST, help="安装的分支")
    install_p.add_argument("--no-pre-download-model", action="store_true", dest="no_pre_download_model", help="禁用预下载模型")
    install_p.add_argument("--model-resource", default="modelscope", dest="model_download_resource_type", choices=MODEL_DOWNLOAD_URL_TYPE_LIST, help="下载模型使用的下载源")
    add_auto_mirror_argument(install_p)
    install_p.set_defaults(
        func=with_auto_mirror(
            lambda args: install(
                sd_trainer_path=args.sd_trainer_path,
                pytorch_mirror_type=args.pytorch_mirror_type,
                custom_pytorch_package=args.custom_pytorch_package,
                custom_xformers_package=args.custom_xformers_package,
                use_pypi_mirror=args.use_pypi_mirror,
                use_uv=args.use_uv,
                use_github_mirror=args.use_github_mirror,
                custom_github_mirror=args.custom_github_mirror,
                install_branch=args.install_branch,
                no_pre_download_model=args.no_pre_download_model,
                model_download_resource_type=args.model_download_resource_type,
            )
        )
    )

    # update
    update_p = trainer_sub.add_parser("update", help="更新 SD Trainer")
    update_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    update_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    update_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    add_pre_operation_snapshot_arguments(update_p)
    add_auto_mirror_argument(update_p)
    update_p.set_defaults(
        func=with_auto_mirror(
            lambda args: update(
                sd_trainer_path=args.sd_trainer_path,
                use_github_mirror=args.use_github_mirror,
                custom_github_mirror=args.custom_github_mirror,
                snapshot_enabled=args.snapshot_enabled,
                snapshot_dir=args.snapshot_dir,
            )
        )
    )

    # snapshot
    snapshot_p = trainer_sub.add_parser("snapshot", help="生成 SD Trainer 环境快照")
    snapshot_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    snapshot_p.add_argument("--output", type=normalized_filepath, default=None, help="输出目录路径, 未传时保存到默认快照目录")
    snapshot_p.add_argument("--no-packages", action="store_false", dest="include_packages", help="不记录当前 Python 环境已安装软件包")
    snapshot_p.set_defaults(
        func=lambda args: snapshot(
            sd_trainer_path=args.sd_trainer_path,
            output=args.output,
            include_packages=args.include_packages,
        )
    )

    # restore
    restore_p = trainer_sub.add_parser("restore", help="恢复 SD Trainer 环境快照")
    add_restore_arguments(restore_p, "--sd-trainer-path", "sd_trainer_path", SD_TRAINER_ROOT_PATH)
    restore_p.set_defaults(
        func=with_auto_mirror(
            lambda args: restore(
                snapshot_path=args.snapshot_path,
                sd_trainer_path=args.sd_trainer_path,
                prune_packages=args.prune_packages,
                prune_extensions=args.prune_extensions,
                force_git_reset=args.force_git_reset,
                use_uv=args.use_uv,
                use_pypi_mirror=args.use_pypi_mirror,
                use_github_mirror=args.use_github_mirror,
                custom_github_mirror=args.custom_github_mirror,
            )
        )
    )

    # check-env
    check_p = trainer_sub.add_parser("check-env", help="检查 SD Trainer 运行环境")
    check_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    check_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv")
    check_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    check_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    check_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    add_auto_mirror_argument(check_p)
    check_p.set_defaults(
        func=with_auto_mirror(
            lambda args: check_env(
                sd_trainer_path=args.sd_trainer_path,
                use_uv=args.use_uv,
                use_github_mirror=args.use_github_mirror,
                custom_github_mirror=args.custom_github_mirror,
                use_pypi_mirror=args.use_pypi_mirror,
            )
        )
    )

    # switch
    switch_p = trainer_sub.add_parser("switch", help="切换 SD Trainer 分支")
    switch_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    switch_p.add_argument("--branch", type=str, dest="branch", choices=SD_TRAINER_BRANCH_LIST, help="要切换的分支")
    switch_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    switch_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    switch_p.add_argument("--interactive", action="store_true", dest="interactive_mode", help="启用交互模式")
    switch_p.add_argument("--list-only", action="store_true", dest="list_only", help="列出分支列表并退出")
    add_pre_operation_snapshot_arguments(switch_p)
    add_auto_mirror_argument(switch_p)
    switch_p.set_defaults(
        func=with_auto_mirror(
            lambda args: switch(
                sd_trainer_path=args.sd_trainer_path,
                branch=args.branch,
                use_github_mirror=args.use_github_mirror,
                custom_github_mirror=args.custom_github_mirror,
                interactive_mode=args.interactive_mode,
                list_only=args.list_only,
                snapshot_enabled=args.snapshot_enabled,
                snapshot_dir=args.snapshot_dir,
            )
        )
    )

    # launch
    launch_p = trainer_sub.add_parser("launch", help="启动 SD Trainer")
    launch_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    launch_p.add_argument("--launch-args", type=str, dest="launch_args", help='启动参数 (请使用引号包裹，例如 "--theme dark")')
    launch_p.add_argument("--no-hf-mirror", action="store_false", dest="use_hf_mirror", help="禁用 HuggingFace 镜像源")
    launch_p.add_argument("--custom-hf-mirror", type=str, dest="custom_hf_mirror", help="自定义 HuggingFace 镜像源")
    launch_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="禁用 Github 镜像源")
    launch_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    launch_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="禁用 PyPI 镜像源")
    launch_p.add_argument("--no-cuda-malloc", action="store_false", dest="use_cuda_malloc", help="禁用 CUDA Malloc 优化")
    launch_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv")
    launch_p.add_argument("--no-check-env", action="store_false", dest="check_env", help="不检查运行环境完整性")
    launch_p.add_argument("--no-hotpatcher", action="store_false", dest="enable_hotpatcher", default=True, help="禁用补丁系统注入")
    launch_p.add_argument("--hotpatcher-runtime", action="store_true", dest="enable_hotpatcher_runtime", default=False, help="启用补丁系统 runtime host 连接")
    launch_p.add_argument("--hotpatcher-config", type=normalized_filepath, dest="hotpatcher_config_path", help="补丁系统配置文件路径")
    launch_p.add_argument("--hotpatcher-port", type=int, dest="hotpatcher_port", help="补丁系统 runtime 通信端口")
    add_auto_mirror_argument(launch_p)
    launch_p.set_defaults(
        func=with_auto_mirror(
            lambda args: launch(
                sd_trainer_path=args.sd_trainer_path,
                launch_args=args.launch_args,
                use_hf_mirror=args.use_hf_mirror,
                custom_hf_mirror=args.custom_hf_mirror,
                use_github_mirror=args.use_github_mirror,
                custom_github_mirror=args.custom_github_mirror,
                use_pypi_mirror=args.use_pypi_mirror,
                use_cuda_malloc=args.use_cuda_malloc,
                use_uv=args.use_uv,
                check_launch_env=args.check_env,
                enable_hotpatcher=args.enable_hotpatcher,
                enable_hotpatcher_runtime=args.enable_hotpatcher_runtime,
                hotpatcher_config_path=args.hotpatcher_config_path,
                hotpatcher_port=args.hotpatcher_port,
            )
        )
    )

    # gui
    gui_parser = trainer_sub.add_parser("gui", help="图形界面工具")
    gui_sub = gui_parser.add_subparsers(dest="gui_action", required=True)

    version_gui_p = gui_sub.add_parser("version-manager", help="启动 SD Trainer 版本管理 GUI")
    version_gui_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    version_gui_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    version_gui_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    add_pre_operation_snapshot_arguments(version_gui_p)
    add_auto_mirror_argument(version_gui_p)
    version_gui_p.set_defaults(
        func=with_auto_mirror(
            lambda args: launch_version_gui(
                sd_trainer_path=args.sd_trainer_path,
                use_github_mirror=args.use_github_mirror,
                custom_github_mirror=args.custom_github_mirror,
                snapshot_enabled=args.snapshot_enabled,
                snapshot_dir=args.snapshot_dir,
            )
        )
    )

    snapshot_gui_p = gui_sub.add_parser("snapshot-manager", help="启动 SD Trainer 快照管理 GUI")
    add_snapshot_gui_arguments(snapshot_gui_p, "--sd-trainer-path", "sd_trainer_path", SD_TRAINER_ROOT_PATH)
    snapshot_gui_p.set_defaults(
        func=with_auto_mirror(
            lambda args: launch_snapshot_gui(
                sd_trainer_path=args.sd_trainer_path,
                snapshot_dir=args.snapshot_dir,
                use_uv=args.use_uv,
                use_pypi_mirror=args.use_pypi_mirror,
                use_github_mirror=args.use_github_mirror,
                custom_github_mirror=args.custom_github_mirror,
            )
        )
    )

    model_gui_p = gui_sub.add_parser("model-manager", help="启动 SD Trainer 模型管理 GUI")
    model_gui_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    model_gui_p.set_defaults(func=lambda args: launch_model_gui(sd_trainer_path=args.sd_trainer_path))

    # model
    model_parser = trainer_sub.add_parser("model", help="模型管理")
    model_sub = model_parser.add_subparsers(dest="model_action", required=True)

    # model install-library
    model_lib_p = model_sub.add_parser("install-library", help="从模型库安装模型")
    model_lib_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    model_lib_p.add_argument("--source", default="modelscope", dest="source", choices=MODEL_DOWNLOAD_URL_TYPE_LIST, help="模型下载源类型")
    model_lib_p.add_argument("--name", dest="name", help="模型名称")
    model_lib_p.add_argument("--index", type=int, dest="index", help="模型索引")
    model_lib_p.add_argument("--downloader", default=None, dest="downloader", choices=DOWNLOAD_TOOL_TYPE_LIST, help="下载工具")
    model_lib_p.add_argument("--interactive", action="store_true", dest="interactive", help="启用交互模式")
    model_lib_p.add_argument("--list-only", action="store_true", dest="list_only", help="列出模型列表并退出")
    add_auto_mirror_argument(model_lib_p)
    model_lib_p.set_defaults(
        func=with_auto_mirror(
            lambda args: install_model_from_library(
                sd_trainer_path=args.sd_trainer_path,
                download_resource_type=args.source,
                model_name=args.name,
                model_index=args.index,
                interactive_mode=args.interactive,
                list_only=args.list_only,
                downloader=args.downloader,
            )
        )
    )

    # model install-url
    model_url_p = model_sub.add_parser("install-url", help="从链接安装模型")
    model_url_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    model_url_p.add_argument("--url", required=True, dest="url", help="模型下载地址")
    model_url_p.add_argument("--type", required=True, dest="type", help="模型类型")
    model_url_p.add_argument("--downloader", default=None, dest="downloader", choices=DOWNLOAD_TOOL_TYPE_LIST, help="下载工具")
    model_url_p.set_defaults(
        func=lambda args: install_model_from_url(
            sd_trainer_path=args.sd_trainer_path,
            model_url=args.url,
            model_type=args.type,
            downloader=args.downloader,
        )
    )

    # model list
    model_list_p = model_sub.add_parser("list", help="列出模型")
    model_list_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    model_list_p.set_defaults(func=lambda args: list_models(sd_trainer_path=args.sd_trainer_path))

    # model uninstall
    model_uninstall_p = model_sub.add_parser("uninstall", help="卸载模型")
    model_uninstall_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    model_uninstall_p.add_argument("--name", required=True, dest="name", help="模型名称")
    model_uninstall_p.add_argument("--type", dest="type", help="模型类型")
    model_uninstall_p.add_argument("--interactive", action="store_true", dest="interactive", help="启用交互模式")
    model_uninstall_p.set_defaults(
        func=lambda args: uninstall_model(
            sd_trainer_path=args.sd_trainer_path,
            model_name=args.name,
            model_type=args.type,
            interactive_mode=args.interactive,
        )
    )
