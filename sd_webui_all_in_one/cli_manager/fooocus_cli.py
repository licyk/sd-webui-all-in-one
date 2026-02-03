import argparse
from pathlib import Path

from sd_webui_all_in_one.base_manager.fooocus_base import (
    FooocusBranchType,
    install_fooocus,
    update_fooocus,
    check_fooocus_env,
    switch_fooocus_branch,
    launch_fooocus,
    install_fooocus_model_from_library,
    install_fooocus_model_from_url,
    list_fooocus_models,
    uninstall_fooocus_model,
)
from sd_webui_all_in_one.config import FOOOCUS_ROOT_PATH
from sd_webui_all_in_one.downloader import DownloadToolType
from sd_webui_all_in_one.model_downloader.base import ModelDownloadUrlType
from sd_webui_all_in_one.pytorch_manager.base import PyTorchDeviceType
from sd_webui_all_in_one.utils import normalized_filepath


def install(
    fooocus_path: Path,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_pypi_mirror: bool | None = True,
    use_uv: bool | None = True,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    install_branch: FooocusBranchType | None = None,
    no_pre_download_model: bool | None = False,
    use_cn_model_mirror: bool | None = True,
) -> None:
    """安装 Fooocus

    Args:
        sd_webui_path (Path):
            Fooocus 根目录
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
        install_branch (FooocusBranchType | None):
            安装的 Fooocus 分支
        no_pre_download_model (bool | None):
            是否禁用预下载模型
        use_cn_model_mirror (bool | None):
            是否使用国内镜像下载模型

    Raises:
        ValueError:
            安装的 Fooocus 分支未知时
        FileNotFoundError:
            Fooocus 依赖文件缺失时
    """
    install_fooocus(
        fooocus_path=fooocus_path,
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
    fooocus_path: Path,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 Fooocus

    Args:
        fooocus_path (Path):
            Stable DIffusion WebUI 根目录
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
    """
    update_fooocus(
        fooocus_path=fooocus_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def check_env(
    fooocus_path: Path,
    check: bool | None = True,
    use_uv: bool | None = True,
) -> None:
    """检查 Fooocus 运行环境

    Args:
        fooocus_path (Path):
            Fooocus 根目录
        check (bool | None):
            是否检查环境时发生的错误, 设置为 True 时, 如果检查环境发生错误时将抛出异常
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包

    Raises:
        AggregateError:
            检查 Fooocus 环境发生错误时
        FileNotFoundError:
            未找到 Fooocus 依赖文件记录表时
    """
    check_fooocus_env(
        fooocus_path=fooocus_path,
        check=check,
        use_uv=use_uv,
    )


def switch(
    fooocus_path: Path,
    branch: FooocusBranchType,
) -> None:
    """切换 Fooocus 分支

    Args:
        fooocus_path (Path):
            Fooocus 根目录
        branch (FooocusBranchType):
            要切换的 Fooocus 分支

    Raises:
        ValueError:
            传入未知的 Fooocus 分支时
    """
    switch_fooocus_branch(
        fooocus_path=fooocus_path,
        branch=branch,
    )


def launch(
    fooocus_path: Path,
    launch_args: list[str] | None = None,
    use_hf_mirror: bool | None = False,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool | None = False,
    use_cuda_malloc: bool | None = True,
    check: bool | None = True,
    use_uv: bool | None = True,
    check_launch_env: bool | None = True,
) -> None:
    """启动 Fooocus

    Args:
        fooocus_path (Path):
            Fooocus 根目录
        launch_args (list[str] | None):
            启动 Fooocus 的参数
        use_hf_mirror (bool | None):
            是否启用 HuggingFace 镜像源
        use_github_mirror (bool | None):
            是否启用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        use_pypi_mirror (bool | None):
            是否启用 PyPI 镜像源
        use_cuda_malloc (bool | None): 
            是否启用 CUDA Malloc 显存优化
        check (bool | None):
            是否检查环境时发生的错误
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        check_launch_env (bool | None):
            是否在启动前检查运行环境
    """
    if check_launch_env:
        check_fooocus_env(
            fooocus_path=fooocus_path,
            check=check,
            use_uv=use_uv,
        )
    launch_fooocus(
        fooocus_path=fooocus_path,
        launch_args=launch_args,
        use_hf_mirror=use_hf_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        use_pypi_mirror=use_pypi_mirror,
        use_cuda_malloc=use_cuda_malloc,
    )


def install_model_from_library(
    fooocus_path: Path,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = "aria2",
    interactive_mode: bool | None = False,
) -> None:
    """为 Fooocus 下载模型, 使用模型库进行下载

    Args:
        fooocus_path (Path):
            Fooocus 根目录
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
    """
    install_fooocus_model_from_library(
        fooocus_path=fooocus_path,
        download_resource_type=download_resource_type,
        model_name=model_name,
        model_index=model_index,
        downloader=downloader,
        interactive_mode=interactive_mode,
    )


def install_model_from_url(
    fooocus_path: Path,
    model_url: str,
    model_type: str,
    downloader: DownloadToolType | None = "aria2",
) -> None:
    """从链接下载模型到 Fooocus

    Args:
        fooocus_path (Path):
            Fooocus 根目录
        model_url (str):
            模型下载地址
        model_type (str):
            模型的类型
        downloader (DownloadToolType | None):
            下载模型使用的工具
    """
    install_fooocus_model_from_url(
        fooocus_path=fooocus_path,
        model_url=model_url,
        model_type=model_type,
        downloader=downloader,
    )


def list_models(
    fooocus_path: Path,
) -> None:
    """列出 Fooocus 的模型目录

    Args:
        fooocus_path (Path):
            Fooocus 根目录
    """
    list_fooocus_models(
        fooocus_path=fooocus_path,
    )


def uninstall_model(
    fooocus_path: Path,
    model_name: str,
    model_type: str | None = None,
    interactive_mode: bool | None = False,
) -> None:
    """卸载 Fooocus 中的模型

    Args:
        fooocus_path (Path):
            Fooocus 根目录
        model_name (str):
            模型名称
        model_type (str | None):
            模型的类型
        interactive_mode (bool | None):
            是否启用交互模式

    Raises:
        FileNotFoundError:
            未找到要删除的模型时
    """
    uninstall_fooocus_model(
        fooocus_path=fooocus_path,
        model_name=model_name,
        model_type=model_type,
        interactive_mode=interactive_mode,
    )


def register_fooocus(subparsers: "argparse._SubParsersAction") -> None:
    """注册 Fooocus 模块及其子命令

    Args:
        subparsers (argparse._SubParsersAction):
            子命令行解析器
    """
    fooocus_parser: argparse.ArgumentParser = subparsers.add_parser("fooocus", help="Fooocus 相关命令")
    fooocus_sub = fooocus_parser.add_subparsers(dest="fooocus_action", required=True)

    # install
    install_p = fooocus_sub.add_parser("install", help="安装 Fooocus")
    install_p.add_argument("--fooocus-path", type=normalized_filepath, required=False, default=FOOOCUS_ROOT_PATH, help="Fooocus 根目录")
    install_p.add_argument("--pytorch-mirror-type", type=str, help="PyTorch 镜像源类型")
    install_p.add_argument("--custom-pytorch-package", type=str, help="自定义 PyTorch 软件包版本声明")
    install_p.add_argument("--custom-xformers-package", type=str, help="自定义 xFormers 软件包版本声明")
    install_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    install_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv 安装 Python 软件包")
    install_p.add_argument("--use-github-mirror", action="store_true", help="使用 Github 镜像源")
    install_p.add_argument("--custom-github-mirror", type=str, help="自定义 Github 镜像源")
    install_p.add_argument("--install-branch", type=str, help="安装的分支")
    install_p.add_argument("--no-pre-download-model", action="store_true", help="禁用预下载模型")
    install_p.add_argument("--no-cn-model-mirror", action="store_false", dest="use_cn_model_mirror", help="不使用国内镜像下载模型")
    install_p.set_defaults(
        func=lambda args: install(
            fooocus_path=args.fooocus_path,
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
    update_p = fooocus_sub.add_parser("update", help="更新 Fooocus")
    update_p.add_argument("--fooocus-path", type=normalized_filepath, required=False, default=FOOOCUS_ROOT_PATH, help="Fooocus 根目录")
    update_p.add_argument("--use-github-mirror", action="store_true", help="使用 Github 镜像源")
    update_p.add_argument("--custom-github-mirror", type=str, help="自定义 Github 镜像源")
    update_p.set_defaults(
        func=lambda args: update(
            fooocus_path=args.fooocus_path,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
        )
    )

    # check-env
    check_p = fooocus_sub.add_parser("check-env", help="检查 Fooocus 运行环境")
    check_p.add_argument("--fooocus-path", type=normalized_filepath, required=False, default=FOOOCUS_ROOT_PATH, help="Fooocus 根目录")
    check_p.add_argument("--no-check", action="store_false", dest="check", help="不抛出环境检查错误")
    check_p.add_argument("--use-github-mirror", action="store_true", help="使用 Github 镜像源")
    check_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv")
    check_p.set_defaults(
        func=lambda args: check_env(
            fooocus_path=args.fooocus_path,
            check=args.check,
            use_uv=args.use_uv,
        )
    )

    # switch
    switch_p = fooocus_sub.add_parser("switch", help="切换 Fooocus 分支")
    switch_p.add_argument("--fooocus-path", type=normalized_filepath, required=False, default=FOOOCUS_ROOT_PATH, help="Fooocus 根目录")
    switch_p.add_argument("--branch", type=str, required=True, help="要切换的分支")
    switch_p.set_defaults(
        func=lambda args: switch(
            fooocus_path=args.fooocus_path,
            branch=args.branch,
        )
    )

    # launch
    launch_p = fooocus_sub.add_parser("launch", help="启动 Fooocus")
    launch_p.add_argument("--fooocus-path", type=normalized_filepath, required=False, default=FOOOCUS_ROOT_PATH, help="Fooocus 根目录")
    launch_p.add_argument("--launch-args", nargs="*", help="启动参数")
    launch_p.add_argument("--use-hf-mirror", action="store_true", help="启用 HuggingFace 镜像源")
    launch_p.add_argument("--use-github-mirror", action="store_true", help="启用 Github 镜像源")
    launch_p.add_argument("--custom-github-mirror", type=str, help="自定义 Github 镜像源")
    launch_p.add_argument("--use-pypi-mirror", action="store_true", help="启用 PyPI 镜像源")
    launch_p.add_argument("--no-cuda-malloc", action="store_false", dest="use_cuda_malloc", help="禁用 CUDA Malloc 优化")
    launch_p.add_argument("--no-check-env", action="store_false", dest="check_env", help="不检查运行环境完整性")
    launch_p.set_defaults(
        func=lambda args: launch(
            fooocus_path=args.fooocus_path,
            launch_args=args.launch_args,
            use_hf_mirror=args.use_hf_mirror,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
            use_pypi_mirror=args.use_pypi_mirror,
            use_cuda_malloc=args.use_cuda_malloc,
            check_launch_env=args.check_env,
        )
    )

    # model
    model_parser = fooocus_sub.add_parser("model", help="模型管理")
    model_sub = model_parser.add_subparsers(dest="model_action", required=True)

    # model install-library
    model_lib_p = model_sub.add_parser("install-library", help="从模型库安装模型")
    model_lib_p.add_argument("--fooocus-path", type=normalized_filepath, required=False, default=FOOOCUS_ROOT_PATH, help="Fooocus 根目录")
    model_lib_p.add_argument("--source", default="modelscope", help="模型下载源类型")
    model_lib_p.add_argument("--name", help="模型名称")
    model_lib_p.add_argument("--index", type=int, help="模型索引")
    model_lib_p.add_argument("--downloader", default="aria2", help="下载工具")
    model_lib_p.add_argument("--interactive", action="store_true", help="启用交互模式")
    model_lib_p.set_defaults(
        func=lambda args: install_model_from_library(
            fooocus_path=args.fooocus_path,
            download_resource_type=args.source,
            model_name=args.name,
            model_index=args.index,
            downloader=args.downloader,
            interactive_mode=args.interactive,
        )
    )

    # model install-url
    model_url_p = model_sub.add_parser("install-url", help="从链接安装模型")
    model_url_p.add_argument("--fooocus-path", type=normalized_filepath, required=False, default=FOOOCUS_ROOT_PATH, help="Fooocus 根目录")
    model_url_p.add_argument("--url", required=True, help="模型下载地址")
    model_url_p.add_argument("--type", required=True, help="模型类型")
    model_url_p.add_argument("--downloader", default="aria2", help="下载工具")
    model_url_p.set_defaults(
        func=lambda args: install_model_from_url(
            fooocus_path=args.fooocus_path,
            model_url=args.url,
            model_type=args.type,
            downloader=args.downloader,
        )
    )

    # model list
    model_list_p = model_sub.add_parser("list", help="列出模型")
    model_list_p.add_argument("--fooocus-path", type=normalized_filepath, required=False, default=FOOOCUS_ROOT_PATH, help="Fooocus 根目录")
    model_list_p.set_defaults(func=lambda args: list_models(fooocus_path=args.fooocus_path))

    # model uninstall
    model_uninstall_p = model_sub.add_parser("uninstall", help="卸载模型")
    model_uninstall_p.add_argument("--fooocus-path", type=normalized_filepath, required=False, default=FOOOCUS_ROOT_PATH, help="Fooocus 根目录")
    model_uninstall_p.add_argument("--name", required=True, help="模型名称")
    model_uninstall_p.add_argument("--type", help="模型类型")
    model_uninstall_p.add_argument("--interactive", action="store_true", help="启用交互模式")
    model_uninstall_p.set_defaults(
        func=lambda args: uninstall_model(
            fooocus_path=args.fooocus_path,
            model_name=args.name,
            model_type=args.type,
            interactive_mode=args.interactive,
        )
    )