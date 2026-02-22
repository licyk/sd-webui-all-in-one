import argparse
import shlex
from pathlib import Path

from sd_webui_all_in_one.base_manager.sd_trainer_base import (
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
)
from sd_webui_all_in_one.config import SD_TRAINER_ROOT_PATH
from sd_webui_all_in_one.downloader import (
    DOWNLOAD_TOOL_TYPE_LIST,
    DownloadToolType,
)
from sd_webui_all_in_one.model_downloader.base import (
    MODEL_DOWNLOAD_URL_TYPE_LIST,
    ModelDownloadUrlType,
)
from sd_webui_all_in_one.pytorch_manager.base import (
    PYTORCH_DEVICE_LIST,
    PyTorchDeviceType,
)
from sd_webui_all_in_one.utils import normalized_filepath
from sd_webui_all_in_one.base_manager.base import reinstall_pytorch


def install(
    sd_trainer_path: Path,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_pypi_mirror: bool | None = True,
    use_uv: bool | None = True,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    install_branch: SDTrainerBranchType | None = None,
    no_pre_download_model: bool | None = False,
    use_cn_model_mirror: bool | None = True,
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
        use_pypi_mirror (bool | None):
            是否使用国内 PyPI 镜像源
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        install_branch (SDTrainerBranchType | None):
            安装的 SD Trainer 分支
        no_pre_download_model (bool | None):
            是否禁用预下载模型
        use_cn_model_mirror (bool | None):
            是否使用国内镜像下载模型
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
        use_cn_model_mirror=use_cn_model_mirror,
    )


def update(
    sd_trainer_path: Path,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 SD Trainer

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
    """
    update_sd_trainer(
        sd_trainer_path=sd_trainer_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def check_env(
    sd_trainer_path: Path,
    use_uv: bool | None = True,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool | None = False,
) -> None:
    """检查 SD Trainer 运行环境

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        use_pypi_mirror (bool | None):
            是否启用 PyPI 镜像源=
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
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    interactive_mode: bool | None = False,
    list_only: bool | None = False,
) -> None:
    """切换 SD Trainer 分支

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        branch (SDTrainerBranchType | None):
            要切换的 SD Trainer 分支
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        interactive_mode (bool | None):
            是否启用交互模式
        list_only (bool | None):
            是否仅列出分支列表并退出
    """
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
    use_hf_mirror: bool | None = False,
    custom_hf_mirror: str | list[str] | None = None,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool | None = False,
    use_cuda_malloc: bool | None = True,
    use_uv: bool | None = True,
    check_launch_env: bool | None = True,
) -> None:
    """启动 SD Trainer

    Args:
        sd_trainer_path (list[str] | None):
            启动 SD Trainer 的参数
        launch_args (str | list[str] | None):
            启动 SD Trainer 的参数
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
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        check_launch_env (bool | None):
            是否在启动前检查运行环境
    """
    if check_launch_env:
        check_sd_trainer_env(
            sd_trainer_path=sd_trainer_path,
            use_uv=use_uv,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
        )
    if isinstance(launch_args, str):
        launch_args = shlex.split(launch_args)
    elif launch_args is None:
        launch_args = []
    launch_sd_trainer(
        sd_trainer_path=sd_trainer_path,
        launch_args=launch_args,
        use_hf_mirror=use_hf_mirror,
        custom_hf_mirror=custom_hf_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        use_pypi_mirror=use_pypi_mirror,
        use_cuda_malloc=use_cuda_malloc,
    )


def install_model_from_library(
    sd_trainer_path: Path,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = "aria2",
    interactive_mode: bool | None = False,
    list_only: bool | None = False,
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
        interactive_mode (bool | None):
            是否启用交互模式
        list_only (bool | None):
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
    downloader: DownloadToolType | None = "aria2",
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
    interactive_mode: bool | None = False,
) -> None:
    """卸载 SD Trainer 中的模型

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        model_name (str):
            模型名称
        model_type (str | None):
            模型的类型
        interactive_mode (bool | None):
            是否启用交互模式
    """
    uninstall_sd_trainer_model(
        sd_trainer_path=sd_trainer_path,
        model_name=model_name,
        model_type=model_type,
        interactive_mode=interactive_mode,
    )


def register_sd_trainer(subparsers: "argparse._SubParsersAction") -> None:
    """注册 SD Trainer 模块及其子命令

    Args:
        subparsers (argparse._SubParsersAction):
            子命令行解析器
    """
    trainer_parser: argparse.ArgumentParser = subparsers.add_parser("sd-trainer", help="SD Trainer 相关命令")
    trainer_sub = trainer_parser.add_subparsers(dest="sd_trainer_action", required=True)

    # reinstall-pytorch
    reinstall_pytorch_p = trainer_sub.add_parser("reinstall-pytorch", help="重装 PyTorch")
    reinstall_pytorch_p.add_argument("--pytorch-name", type=str, dest="pytorch_name", help="PyTorch 版本组合名称")
    reinstall_pytorch_p.add_argument("--pytorch-index", type=int, dest="pytorch_index", help="PyTorch 版本组合索引值")
    # reinstall_pytorch_p.add_argument("--use-pypi-mirror", action="store_true", dest="use_pypi_mirror", help="使用国内 PyPI 镜像源")
    reinstall_pytorch_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    # reinstall_pytorch_p.add_argument("--use-uv", action="store_true", dest="use_uv", help="使用 uv 安装 PyTorch 软件包")
    reinstall_pytorch_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv 安装 PyTorch 软件包")
    reinstall_pytorch_p.add_argument("--interactive", action="store_true", dest="interactive_mode", help="启用交互模式")
    reinstall_pytorch_p.add_argument("--list-only", action="store_true", dest="list_only", help="列出 PyTorch 列表并退出")
    reinstall_pytorch_p.add_argument("--force-reinstall", action="store_true", dest="force_reinstall", help="强制重装 PyTorch")
    reinstall_pytorch_p.set_defaults(
        func=lambda args: reinstall_pytorch(
            pytorch_name=args.pytorch_name,
            pytorch_index=args.pytorch_index,
            use_pypi_mirror=args.use_pypi_mirror,
            use_uv=args.use_uv,
            interactive_mode=args.interactive_mode,
            list_only=args.list_only,
            force_reinstall=args.force_reinstall,
        )
    )

    # install
    install_p = trainer_sub.add_parser("install", help="安装 SD Trainer")
    install_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    install_p.add_argument("--pytorch-mirror-type", type=str, dest="pytorch_mirror_type", choices=PYTORCH_DEVICE_LIST, help="PyTorch 镜像源类型")
    install_p.add_argument("--custom-pytorch-package", type=str, dest="custom_pytorch_package", help="自定义 PyTorch 软件包版本声明")
    install_p.add_argument("--custom-xformers-package", type=str, dest="custom_xformers_package", help="自定义 xFormers 软件包版本声明")
    # install_p.add_argument("--use-pypi-mirror", action="store_true", dest="use_pypi_mirror", help="使用国内 PyPI 镜像源")
    install_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    # install_p.add_argument("--use-uv", action="store_true", dest="use_uv", help="使用 uv 安装 Python 软件包")
    install_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv 安装 Python 软件包")
    # install_p.add_argument("--use-github-mirror", action="store_true", dest="use_github_mirror", help="使用 Github 镜像源")
    install_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    install_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    install_p.add_argument("--install-branch", type=str, dest="install_branch", choices=SD_TRAINER_BRANCH_LIST, help="安装的分支")
    # install_p.add_argument("--pre-download-model", action="store_false", dest="no_pre_download_model", help="启用预下载模型")
    install_p.add_argument("--no-pre-download-model", action="store_true", dest="no_pre_download_model", help="禁用预下载模型")
    # install_p.add_argument("--use-cn-model-mirror", action="store_true", dest="use_cn_model_mirror", help="使用国内镜像下载模型")
    install_p.add_argument("--no-cn-model-mirror", action="store_false", dest="use_cn_model_mirror", help="不使用国内镜像下载模型")
    install_p.set_defaults(
        func=lambda args: install(
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
            use_cn_model_mirror=args.use_cn_model_mirror,
        )
    )

    # update
    update_p = trainer_sub.add_parser("update", help="更新 SD Trainer")
    update_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    # update_p.add_argument("--use-github-mirror", action="store_true", dest="use_github_mirror", help="使用 Github 镜像源")
    update_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    update_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    update_p.set_defaults(
        func=lambda args: update(
            sd_trainer_path=args.sd_trainer_path,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
        )
    )

    # check-env
    check_p = trainer_sub.add_parser("check-env", help="检查 SD Trainer 运行环境")
    check_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    # check_p.add_argument("--use-uv", action="store_true", dest="use_uv", help="使用 uv")
    check_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv")
    check_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    # check_p.add_argument("--use-github-mirror", action="store_true", dest="use_github_mirror", help="使用 Github 镜像源")
    check_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    # check_p.add_argument("--use-pypi-mirror", action="store_true", dest="use_pypi_mirror", help="使用国内 PyPI 镜像源")
    check_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    check_p.set_defaults(
        func=lambda args: check_env(
            sd_trainer_path=args.sd_trainer_path,
            use_uv=args.use_uv,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
            use_pypi_mirror=args.use_pypi_mirror,
        )
    )

    # switch
    switch_p = trainer_sub.add_parser("switch", help="切换 SD Trainer 分支")
    switch_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    switch_p.add_argument("--branch", type=str, dest="branch", choices=SD_TRAINER_BRANCH_LIST, help="要切换的分支")
    # switch_p.add_argument("--use-github-mirror", action="store_true", dest="use_github_mirror", help="使用 Github 镜像源")
    switch_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    switch_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    switch_p.add_argument("--interactive", action="store_true", dest="interactive_mode", help="启用交互模式")
    switch_p.add_argument("--list-only", action="store_true", dest="list_only", help="列出分支列表并退出")
    switch_p.set_defaults(
        func=lambda args: switch(
            sd_trainer_path=args.sd_trainer_path,
            branch=args.branch,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
            interactive_mode=args.interactive_mode,
            list_only=args.list_only,
        )
    )

    # launch
    launch_p = trainer_sub.add_parser("launch", help="启动 SD Trainer")
    launch_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    launch_p.add_argument("--launch-args", type=str, dest="launch_args", help='启动参数 (请使用引号包裹，例如 "--theme dark")')
    # launch_p.add_argument("--use-hf-mirror", action="store_true", dest="use_hf_mirror", help="启用 HuggingFace 镜像源")
    launch_p.add_argument("--no-hf-mirror", action="store_false", dest="use_hf_mirror", help="禁用 HuggingFace 镜像源")
    launch_p.add_argument("--custom-hf-mirror", type=str, dest="custom_hf_mirror", help="自定义 HuggingFace 镜像源")
    # launch_p.add_argument("--use-github-mirror", action="store_true", dest="use_github_mirror", help="启用 Github 镜像源")
    launch_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="禁用 Github 镜像源")
    launch_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    # launch_p.add_argument("--use-pypi-mirror", action="store_true", dest="use_pypi_mirror", help="启用 PyPI 镜像源")
    launch_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="禁用 PyPI 镜像源")
    # launch_p.add_argument("--use-cuda-malloc", action="store_true", dest="use_cuda_malloc", help="启用 CUDA Malloc 优化")
    launch_p.add_argument("--no-cuda-malloc", action="store_false", dest="use_cuda_malloc", help="禁用 CUDA Malloc 优化")
    # launch_p.add_argument("--use-uv", action="store_true", dest="use_uv", help="使用 uv")
    launch_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv")
    # launch_p.add_argument("--check-env", action="store_true", dest="check_env", help="检查运行环境完整性")
    launch_p.add_argument("--no-check-env", action="store_false", dest="check_env", help="不检查运行环境完整性")
    launch_p.set_defaults(
        func=lambda args: launch(
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
        )
    )

    # model
    model_parser = trainer_sub.add_parser("model", help="模型管理")
    model_sub = model_parser.add_subparsers(dest="model_action", required=True)

    # model install-library
    model_lib_p = model_sub.add_parser("install-library", help="从模型库安装模型")
    model_lib_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    model_lib_p.add_argument("--source", default="modelscope", dest="source", choices=MODEL_DOWNLOAD_URL_TYPE_LIST, help="模型下载源类型")
    model_lib_p.add_argument("--name", dest="name", help="模型名称")
    model_lib_p.add_argument("--index", type=int, dest="index", help="模型索引")
    model_lib_p.add_argument("--downloader", default="aria2", dest="downloader", choices=DOWNLOAD_TOOL_TYPE_LIST, help="下载工具")
    model_lib_p.add_argument("--interactive", action="store_true", dest="interactive", help="启用交互模式")
    model_lib_p.add_argument("--list-only", action="store_true", dest="list_only", help="列出模型列表并退出")
    model_lib_p.set_defaults(
        func=lambda args: install_model_from_library(
            sd_trainer_path=args.sd_trainer_path,
            download_resource_type=args.source,
            model_name=args.name,
            model_index=args.index,
            downloader=args.downloader,
            interactive_mode=args.interactive,
            list_only=args.list_only,
        )
    )

    # model install-url
    model_url_p = model_sub.add_parser("install-url", help="从链接安装模型")
    model_url_p.add_argument("--sd-trainer-path", type=normalized_filepath, required=False, default=SD_TRAINER_ROOT_PATH, dest="sd_trainer_path", help="SD Trainer 根目录")
    model_url_p.add_argument("--url", required=True, dest="url", help="模型下载地址")
    model_url_p.add_argument("--type", required=True, dest="type", help="模型类型")
    model_url_p.add_argument("--downloader", default="aria2", dest="downloader", choices=DOWNLOAD_TOOL_TYPE_LIST, help="下载工具")
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
