"""SD Scripts 命令行工具"""

import argparse
from pathlib import Path

from sd_webui_all_in_one.base_manager import (
    SD_SCRIPTS_BRANCH_LIST,
    SDScriptsBranchType,
    install_sd_scripts,
    update_sd_scripts,
    check_sd_scripts_env,
    switch_sd_scripts_branch,
    install_sd_scripts_model_from_library,
    install_sd_scripts_model_from_url,
    list_sd_scripts_models,
    uninstall_sd_scripts_model,
    launch_sd_scripts_version_gui,
    launch_sd_scripts_snapshot_gui,
    reinstall_pytorch as reinstall_base_pytorch,
    get_sd_scripts_snapshot,
)
from sd_webui_all_in_one.config import SD_SCRIPTS_ROOT_PATH
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


def install(
    sd_scripts_path: Path,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_pypi_mirror: bool = True,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    install_branch: SDScriptsBranchType | None = None,
    no_pre_download_model: bool = False,
    model_download_resource_type: ModelDownloadUrlType | None = "modelscope",
) -> None:
    """安装 SD Scripts

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录
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
        install_branch (SDScriptsBranchType | None):
            安装的 SD Scripts 分支
        no_pre_download_model (bool):
            是否禁用预下载模型
        model_download_resource_type (ModelDownloadUrlType | None):
            下载模型使用的下载源
    """
    install_sd_scripts(
        sd_scripts_path=sd_scripts_path,
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
    sd_scripts_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    snapshot_enabled: bool = True,
    snapshot_dir: Path | None = None,
) -> None:
    """更新 SD Scripts

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录。
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
        sd_scripts_path=sd_scripts_path,
        operation_name="更新 SD Scripts",
        snapshot_enabled=snapshot_enabled,
        snapshot_dir=snapshot_dir,
    )
    update_sd_scripts(
        sd_scripts_path=sd_scripts_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def _create_pre_operation_snapshot(
    sd_scripts_path: Path,
    operation_name: str,
    snapshot_enabled: bool = True,
    snapshot_dir: Path | None = None,
    show_gui_warning: bool = False,
) -> None:
    create_pre_operation_snapshot(
        lambda: get_sd_scripts_snapshot(sd_scripts_path=sd_scripts_path, include_packages=True),
        operation_name=operation_name,
        snapshot_enabled=snapshot_enabled,
        snapshot_dir=snapshot_dir,
        show_gui_warning=show_gui_warning,
    )


def snapshot(
    sd_scripts_path: Path,
    output: Path | None = None,
    include_packages: bool = True,
) -> None:
    """生成 SD Scripts 环境快照

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录。
        output (Path | None):
            快照输出路径或目录。
        include_packages (bool):
            是否采集当前 Python 包列表。
    """
    output_snapshot(
        lambda: get_sd_scripts_snapshot(
            sd_scripts_path=sd_scripts_path,
            include_packages=include_packages,
        ),
        output=output,
    )


def restore(
    snapshot_path: Path,
    sd_scripts_path: Path,
    prune_packages: bool = False,
    prune_extensions: bool = False,
    force_git_reset: bool = False,
    use_uv: bool = True,
    use_pypi_mirror: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """恢复 SD Scripts 环境快照

    Args:
        snapshot_path (Path):
            快照 JSON 文件路径。
        sd_scripts_path (Path):
            SD Scripts 根目录。
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
        webui_path=sd_scripts_path,
        expected_webui_type="sd_scripts",
        prune_packages=prune_packages,
        prune_extensions=prune_extensions,
        force_git_reset=force_git_reset,
        use_uv=use_uv,
        use_pypi_mirror=use_pypi_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def check_env(
    sd_scripts_path: Path,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool = False,
) -> None:
    """检查 SD Scripts 运行环境

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录
        use_uv (bool):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        use_pypi_mirror (bool):
            是否启用 PyPI 镜像源
    """
    check_sd_scripts_env(
        sd_scripts_path=sd_scripts_path,
        use_uv=use_uv,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        use_pypi_mirror=use_pypi_mirror,
    )


def switch(
    sd_scripts_path: Path,
    branch: SDScriptsBranchType | None = None,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    interactive_mode: bool = False,
    list_only: bool = False,
    snapshot_enabled: bool = True,
    snapshot_dir: Path | None = None,
) -> None:
    """切换 SD Scripts 分支

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录。
        branch (SDScriptsBranchType | None):
            要切换的 SD Scripts 分支。
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
            sd_scripts_path=sd_scripts_path,
            operation_name="切换 SD Scripts 分支",
            snapshot_enabled=snapshot_enabled,
            snapshot_dir=snapshot_dir,
        )
    switch_sd_scripts_branch(
        sd_scripts_path=sd_scripts_path,
        branch=branch,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        interactive_mode=interactive_mode,
        list_only=list_only,
    )


def install_model_from_library(
    sd_scripts_path: Path,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = None,
    interactive_mode: bool = False,
    list_only: bool = False,
) -> None:
    """为 SD Scripts 下载模型, 使用模型库进行下载

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录
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
    install_sd_scripts_model_from_library(
        sd_scripts_path=sd_scripts_path,
        download_resource_type=download_resource_type,
        model_name=model_name,
        model_index=model_index,
        downloader=downloader,
        interactive_mode=interactive_mode,
        list_only=list_only,
    )


def install_model_from_url(
    sd_scripts_path: Path,
    model_url: str,
    model_type: str,
    downloader: DownloadToolType | None = None,
) -> None:
    """从链接下载模型到 SD Scripts

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录
        model_url (str):
            模型下载地址
        model_type (str):
            模型的类型
        downloader (DownloadToolType | None):
            下载模型使用的工具
    """
    install_sd_scripts_model_from_url(
        sd_scripts_path=sd_scripts_path,
        model_url=model_url,
        model_type=model_type,
        downloader=downloader,
    )


def list_models(
    sd_scripts_path: Path,
) -> None:
    """列出 SD Scripts 的模型目录

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录
    """
    list_sd_scripts_models(
        sd_scripts_path=sd_scripts_path,
    )


def uninstall_model(
    sd_scripts_path: Path,
    model_name: str,
    model_type: str | None = None,
    interactive_mode: bool = False,
) -> None:
    """卸载 SD Scripts 中的模型

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录
        model_name (str):
            模型名称
        model_type (str | None):
            模型的类型
        interactive_mode (bool):
            是否启用交互模式
    """
    uninstall_sd_scripts_model(
        sd_scripts_path=sd_scripts_path,
        model_name=model_name,
        model_type=model_type,
        interactive_mode=interactive_mode,
    )


def launch_version_gui(
    sd_scripts_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    snapshot_enabled: bool = True,
    snapshot_dir: Path | None = None,
) -> None:
    """启动 SD Scripts 版本管理 GUI

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录。
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
        sd_scripts_path=sd_scripts_path,
        operation_name="启动 SD Scripts 版本管理 GUI",
        snapshot_enabled=snapshot_enabled,
        snapshot_dir=snapshot_dir,
        show_gui_warning=True,
    )
    launch_sd_scripts_version_gui(
        sd_scripts_path=sd_scripts_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def reinstall_pytorch(
    sd_scripts_path: Path,
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
    """为 SD Scripts 重装 PyTorch

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录。
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
            sd_scripts_path=sd_scripts_path,
            operation_name="重装 SD Scripts PyTorch",
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
    sd_scripts_path: Path,
    snapshot_dir: Path | None = None,
    use_uv: bool = True,
    use_pypi_mirror: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """启动 SD Scripts 快照管理 GUI

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录。
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
    launch_sd_scripts_snapshot_gui(
        sd_scripts_path=sd_scripts_path,
        snapshot_dir=snapshot_dir,
        use_uv=use_uv,
        use_pypi_mirror=use_pypi_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def register_sd_scripts(
    subparsers: "argparse._SubParsersAction",
) -> None:
    """注册 SD Scripts 模块及其子命令

    Args:
        subparsers (argparse._SubParsersAction):
            子命令行解析器
    """
    scripts_parser: argparse.ArgumentParser = subparsers.add_parser("sd-scripts", help="SD Scripts 相关命令")
    scripts_sub = scripts_parser.add_subparsers(dest="sd_scripts_action", required=True)

    # reinstall-pytorch
    reinstall_pytorch_p = scripts_sub.add_parser("reinstall-pytorch", help="重装 PyTorch")
    reinstall_pytorch_p.add_argument("--sd-scripts-path", type=normalized_filepath, required=False, default=SD_SCRIPTS_ROOT_PATH, dest="sd_scripts_path", help="SD Scripts 根目录")
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
                sd_scripts_path=args.sd_scripts_path,
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
    install_p = scripts_sub.add_parser("install", help="安装 SD Scripts")
    install_p.add_argument("--sd-scripts-path", type=normalized_filepath, required=False, default=SD_SCRIPTS_ROOT_PATH, dest="sd_scripts_path", help="SD Scripts 根目录")
    install_p.add_argument("--pytorch-mirror-type", type=str, dest="pytorch_mirror_type", choices=PYTORCH_DEVICE_LIST, help="PyTorch 镜像源类型")
    install_p.add_argument("--custom-pytorch-package", type=str, dest="custom_pytorch_package", help="自定义 PyTorch 软件包版本声明")
    install_p.add_argument("--custom-xformers-package", type=str, dest="custom_xformers_package", help="自定义 xFormers 软件包版本声明")
    install_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    install_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv 安装 Python 软件包")
    install_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    install_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    install_p.add_argument("--install-branch", type=str, dest="install_branch", choices=SD_SCRIPTS_BRANCH_LIST, help="安装的分支")
    install_p.add_argument("--no-pre-download-model", action="store_true", dest="no_pre_download_model", help="禁用预下载模型")
    install_p.add_argument("--model-resource", default="modelscope", dest="model_download_resource_type", choices=MODEL_DOWNLOAD_URL_TYPE_LIST, help="下载模型使用的下载源")
    add_auto_mirror_argument(install_p)
    install_p.set_defaults(
        func=with_auto_mirror(
            lambda args: install(
                sd_scripts_path=args.sd_scripts_path,
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
    update_p = scripts_sub.add_parser("update", help="更新 SD Scripts")
    update_p.add_argument("--sd-scripts-path", type=normalized_filepath, required=False, default=SD_SCRIPTS_ROOT_PATH, dest="sd_scripts_path", help="SD Scripts 根目录")
    update_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    update_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    add_pre_operation_snapshot_arguments(update_p)
    add_auto_mirror_argument(update_p)
    update_p.set_defaults(
        func=with_auto_mirror(
            lambda args: update(
                sd_scripts_path=args.sd_scripts_path,
                use_github_mirror=args.use_github_mirror,
                custom_github_mirror=args.custom_github_mirror,
                snapshot_enabled=args.snapshot_enabled,
                snapshot_dir=args.snapshot_dir,
            )
        )
    )

    # snapshot
    snapshot_p = scripts_sub.add_parser("snapshot", help="生成 SD Scripts 环境快照")
    snapshot_p.add_argument("--sd-scripts-path", type=normalized_filepath, required=False, default=SD_SCRIPTS_ROOT_PATH, dest="sd_scripts_path", help="SD Scripts 根目录")
    snapshot_p.add_argument("--output", type=normalized_filepath, default=None, help="输出目录路径, 未传时保存到默认快照目录")
    snapshot_p.add_argument("--no-packages", action="store_false", dest="include_packages", help="不记录当前 Python 环境已安装软件包")
    snapshot_p.set_defaults(
        func=lambda args: snapshot(
            sd_scripts_path=args.sd_scripts_path,
            output=args.output,
            include_packages=args.include_packages,
        )
    )

    # restore
    restore_p = scripts_sub.add_parser("restore", help="恢复 SD Scripts 环境快照")
    add_restore_arguments(restore_p, "--sd-scripts-path", "sd_scripts_path", SD_SCRIPTS_ROOT_PATH)
    restore_p.set_defaults(
        func=with_auto_mirror(
            lambda args: restore(
                snapshot_path=args.snapshot_path,
                sd_scripts_path=args.sd_scripts_path,
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
    check_p = scripts_sub.add_parser("check-env", help="检查 SD Scripts 运行环境")
    check_p.add_argument("--sd-scripts-path", type=normalized_filepath, required=False, default=SD_SCRIPTS_ROOT_PATH, dest="sd_scripts_path", help="SD Scripts 根目录")
    check_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv")
    check_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    check_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    check_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    add_auto_mirror_argument(check_p)
    check_p.set_defaults(
        func=with_auto_mirror(
            lambda args: check_env(
                sd_scripts_path=args.sd_scripts_path,
                use_uv=args.use_uv,
                use_github_mirror=args.use_github_mirror,
                custom_github_mirror=args.custom_github_mirror,
                use_pypi_mirror=args.use_pypi_mirror,
            )
        )
    )

    # switch
    switch_p = scripts_sub.add_parser("switch", help="切换 SD Scripts 分支")
    switch_p.add_argument("--sd-scripts-path", type=normalized_filepath, required=False, default=SD_SCRIPTS_ROOT_PATH, dest="sd_scripts_path", help="SD Scripts 根目录")
    switch_p.add_argument("--branch", type=str, dest="branch", choices=SD_SCRIPTS_BRANCH_LIST, help="要切换的分支")
    switch_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    switch_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    switch_p.add_argument("--interactive", action="store_true", dest="interactive_mode", help="启用交互模式")
    switch_p.add_argument("--list-only", action="store_true", dest="list_only", help="列出分支列表并退出")
    add_pre_operation_snapshot_arguments(switch_p)
    add_auto_mirror_argument(switch_p)
    switch_p.set_defaults(
        func=with_auto_mirror(
            lambda args: switch(
                sd_scripts_path=args.sd_scripts_path,
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

    # gui
    gui_parser = scripts_sub.add_parser("gui", help="图形界面工具")
    gui_sub = gui_parser.add_subparsers(dest="gui_action", required=True)

    version_gui_p = gui_sub.add_parser("version-manager", help="启动 SD Scripts 版本管理 GUI")
    version_gui_p.add_argument("--sd-scripts-path", type=normalized_filepath, required=False, default=SD_SCRIPTS_ROOT_PATH, dest="sd_scripts_path", help="SD Scripts 根目录")
    version_gui_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    version_gui_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    add_pre_operation_snapshot_arguments(version_gui_p)
    add_auto_mirror_argument(version_gui_p)
    version_gui_p.set_defaults(
        func=with_auto_mirror(
            lambda args: launch_version_gui(
                sd_scripts_path=args.sd_scripts_path,
                use_github_mirror=args.use_github_mirror,
                custom_github_mirror=args.custom_github_mirror,
                snapshot_enabled=args.snapshot_enabled,
                snapshot_dir=args.snapshot_dir,
            )
        )
    )

    snapshot_gui_p = gui_sub.add_parser("snapshot-manager", help="启动 SD Scripts 快照管理 GUI")
    add_snapshot_gui_arguments(snapshot_gui_p, "--sd-scripts-path", "sd_scripts_path", SD_SCRIPTS_ROOT_PATH)
    snapshot_gui_p.set_defaults(
        func=with_auto_mirror(
            lambda args: launch_snapshot_gui(
                sd_scripts_path=args.sd_scripts_path,
                snapshot_dir=args.snapshot_dir,
                use_uv=args.use_uv,
                use_pypi_mirror=args.use_pypi_mirror,
                use_github_mirror=args.use_github_mirror,
                custom_github_mirror=args.custom_github_mirror,
            )
        )
    )

    # model
    model_parser = scripts_sub.add_parser("model", help="模型管理")
    model_sub = model_parser.add_subparsers(dest="model_action", required=True)

    # model install-library
    model_lib_p = model_sub.add_parser("install-library", help="从模型库安装模型")
    model_lib_p.add_argument("--sd-scripts-path", type=normalized_filepath, required=False, default=SD_SCRIPTS_ROOT_PATH, dest="sd_scripts_path", help="SD Scripts 根目录")
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
                sd_scripts_path=args.sd_scripts_path,
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
    model_url_p.add_argument("--sd-scripts-path", type=normalized_filepath, required=False, default=SD_SCRIPTS_ROOT_PATH, dest="sd_scripts_path", help="SD Scripts 根目录")
    model_url_p.add_argument("--url", required=True, dest="url", help="模型下载地址")
    model_url_p.add_argument("--type", required=True, dest="type", help="模型类型")
    model_url_p.add_argument("--downloader", default=None, dest="downloader", choices=DOWNLOAD_TOOL_TYPE_LIST, help="下载工具")
    model_url_p.set_defaults(
        func=lambda args: install_model_from_url(
            sd_scripts_path=args.sd_scripts_path,
            model_url=args.url,
            model_type=args.type,
            downloader=args.downloader,
        )
    )

    # model list
    model_list_p = model_sub.add_parser("list", help="列出模型")
    model_list_p.add_argument("--sd-scripts-path", type=normalized_filepath, required=False, default=SD_SCRIPTS_ROOT_PATH, dest="sd_scripts_path", help="SD Scripts 根目录")
    model_list_p.set_defaults(func=lambda args: list_models(sd_scripts_path=args.sd_scripts_path))

    # model uninstall
    model_uninstall_p = model_sub.add_parser("uninstall", help="卸载模型")
    model_uninstall_p.add_argument("--sd-scripts-path", type=normalized_filepath, required=False, default=SD_SCRIPTS_ROOT_PATH, dest="sd_scripts_path", help="SD Scripts 根目录")
    model_uninstall_p.add_argument("--name", required=True, dest="name", help="模型名称")
    model_uninstall_p.add_argument("--type", dest="type", help="模型类型")
    model_uninstall_p.add_argument("--interactive", action="store_true", dest="interactive", help="启用交互模式")
    model_uninstall_p.set_defaults(
        func=lambda args: uninstall_model(
            sd_scripts_path=args.sd_scripts_path,
            model_name=args.name,
            model_type=args.type,
            interactive_mode=args.interactive,
        )
    )
