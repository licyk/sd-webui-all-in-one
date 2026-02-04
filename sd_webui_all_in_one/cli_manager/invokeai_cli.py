import argparse
import shlex
from pathlib import Path

from sd_webui_all_in_one.base_manager.invokeai_base import (
    install_invokeai,
    update_invokeai,
    check_invokeai_env,
    launch_invokeai,
    install_invokeai_custom_nodes,
    set_invokeai_custom_nodes_status,
    list_invokeai_custom_nodes,
    update_invokeai_custom_nodes,
    uninstall_invokeai_custom_node,
    install_invokeai_model_from_library,
    install_invokeai_model_from_url,
    list_invokeai_models,
    uninstall_invokeai_model,
)
from sd_webui_all_in_one.config import INVOKEAI_ROOT_PATH
from sd_webui_all_in_one.downloader import DownloadToolType
from sd_webui_all_in_one.model_downloader.base import ModelDownloadUrlType
from sd_webui_all_in_one.pytorch_manager.base import PyTorchDeviceTypeCategory
from sd_webui_all_in_one.utils import normalized_filepath
from sd_webui_all_in_one.base_manager.invokeai_base import reinstall_invokeai_pytorch

def install(
    invokeai_path: Path,
    device_type: PyTorchDeviceTypeCategory | None = None,
    invokeai_version: str | None = None,
    use_pypi_mirror: bool | None = True,
    use_uv: bool | None = True,
    no_pre_download_model: bool | None = False,
    use_cn_model_mirror: bool | None = True,
) -> None:
    """安装 InvokeAI

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        device_type (PyTorchDeviceTypeCategory | None):
            设置使用的 PyTorch 镜像源类型
        invokeai_version (str | None):
            自定义安装 InvokeAI 的版本
        use_pypi_mirror (bool | None):
            是否使用国内 PyPI 镜像源
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        no_pre_download_model (bool | None):
            是否禁用预下载模型
        use_cn_model_mirror (bool | None):
            是否使用国内镜像下载模型
    """
    install_invokeai(
        invokeai_path=invokeai_path,
        device_type=device_type,
        invokeai_version=invokeai_version,
        use_pypi_mirror=use_pypi_mirror,
        use_uv=use_uv,
        no_pre_download_model=no_pre_download_model,
        use_cn_model_mirror=use_cn_model_mirror,
    )


def update(
    use_pypi_mirror: bool | None = False,
    use_uv: bool | None = False,
) -> None:
    """更新 InvokeAI

    Args:
        use_pypi_mirror (bool | None):
            是否使用国内 PyPI 镜像源
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
    """
    update_invokeai(
        use_pypi_mirror=use_pypi_mirror,
        use_uv=use_uv,
    )


def check_env(
    use_uv: bool | None = True,
    use_pypi_mirror: bool | None = False,
) -> None:
    """检查 InvokeAI 运行环境

    Args:
        use_uv (bool | None):
            使用 uv 安装依赖
        use_pypi_mirror (bool | None):
            是否启用 PyPI 镜像源
    """
    check_invokeai_env(
        use_uv=use_uv,
        use_pypi_mirror=use_pypi_mirror,
    )


def launch(
    invokeai_path: Path,
    launch_args: str | list[str] | None = None,
    use_hf_mirror: bool | None = False,
    use_pypi_mirror: bool | None = False,
    use_cuda_malloc: bool | None = True,
    use_uv: bool | None = True,
    check_launch_env: bool | None = True,
) -> None:
    """启动 InvokeAI

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        launch_args (str | list[str] | None):
            启动 InvokeAI 的参数
        use_hf_mirror (bool | None):
            是否启用 HuggingFace 镜像源
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
        check_invokeai_env(
            use_uv=use_uv,
            use_pypi_mirror=use_pypi_mirror,
        )
    if isinstance(launch_args, str):
        launch_args = shlex.split(launch_args)
    elif launch_args is None:
        launch_args = []
    launch_invokeai(
        invokeai_path=invokeai_path,
        launch_args=launch_args,
        use_hf_mirror=use_hf_mirror,
        use_pypi_mirror=use_pypi_mirror,
        use_cuda_malloc=use_cuda_malloc,
    )


def install_custom_nodes(
    invokeai_path: Path,
    custom_node_url: str | list[str],
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    check: bool | None = True,
) -> None:
    """安装 InvokeAI 扩展

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        custom_node_url (str | list[str]):
            InvokeAI 扩展下载链接
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        check (bool | None):
            是否检查安装扩展时发生的错误, 设置为 True 时, 如果安装扩展时发生错误时将抛出异常
    """
    install_invokeai_custom_nodes(
        invokeai_path=invokeai_path,
        custom_node_url=custom_node_url,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        check=check,
    )


def set_custom_node_status(
    invokeai_path: Path,
    custom_node_name: str,
    status: bool,
) -> None:
    """设置 InvokeAI 启用状态

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        custom_node_name (str):
            InvokeAI 扩展名称
        status (bool):
            设置扩展的启用状态
            - `True`: 启用
            - `False`: 禁用
    """
    set_invokeai_custom_nodes_status(
        invokeai_path=invokeai_path,
        custom_node_name=custom_node_name,
        status=status,
    )


def list_custom_nodes(
    invokeai_path: Path,
) -> None:
    """获取 InvokeAI 本地扩展列表

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
    """
    for ext in list_invokeai_custom_nodes(invokeai_path=invokeai_path):
        print(f"- {ext['name']}")
        print(f"  - 安装路径: {ext['path']}")
        print(f"  - 远程地址: {ext['url']}")
        print(f"  - 启用状态: {ext['status']}")
        print(f"  - 版本: {ext['commit']}")
        print(f"  - 分支: {ext['branch']}")


def update_custom_nodes(
    invokeai_path: Path,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    check: bool | None = True,
) -> None:
    """更新 InvokeAI 扩展

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        check (bool | None):
            是否检查更新时发生的错误, 设置为 True 时, 如果更新扩展时发生错误时将抛出异常
    """
    update_invokeai_custom_nodes(
        invokeai_path=invokeai_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        check=check,
    )


def uninstall_custom_node(
    invokeai_path: Path,
    custom_node_name: str,
    check: bool | None = True,
) -> None:
    """卸载 InvokeAI 扩展

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        custom_node_name (str):
            InvokeAI 扩展名称
        check (bool | None):
            是否卸载扩展时发生的错误, 设置为 True 时, 如果卸载扩展时发生错误时将抛出异常
    """
    uninstall_invokeai_custom_node(
        invokeai_path=invokeai_path,
        custom_node_name=custom_node_name,
        check=check,
    )


def install_model_from_library(
    invokeai_path: Path,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = "aria2",
    interactive_mode: bool | None = False,
) -> None:
    """为 InvokeAI 下载模型, 使用模型库进行下载

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
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
    install_invokeai_model_from_library(
        invokeai_path=invokeai_path,
        download_resource_type=download_resource_type,
        model_name=model_name,
        model_index=model_index,
        downloader=downloader,
        interactive_mode=interactive_mode,
    )


def install_model_from_url(
    sd_webui_path: Path,
    model_url: str,
    model_type: str,
    downloader: DownloadToolType | None = "aria2",
) -> None:
    """从链接下载模型到 InvokeAI

    Args:
        sd_webui_path (Path):
            InvokeAI 根目录
        model_url (str):
            模型下载地址
        model_type (str):
            模型的类型
        downloader (DownloadToolType | None):
            下载模型使用的工具
    """
    install_invokeai_model_from_url(
        sd_webui_path=sd_webui_path,
        model_url=model_url,
        model_type=model_type,
        downloader=downloader,
    )


def list_models() -> None:
    """列出 InvokeAI 的模型目录"""
    list_invokeai_models()


def uninstall_model(
    model_name: str,
    interactive_mode: bool | None = False,
) -> None:
    """卸载 InvokeAI 中的模型

    Args:
        sd_webui_path (Path):
            InvokeAI 根目录
        model_name (str):
            模型名称
        interactive_mode (bool | None):
            是否启用交互模式
    """
    uninstall_invokeai_model(
        model_name=model_name,
        interactive_mode=interactive_mode,
    )


def register_invokeai(subparsers: "argparse._SubParsersAction") -> None:
    """注册 InvokeAI 模块及其子命令

    Args:
        subparsers (argparse._SubParsersAction):
            子命令行解析器
    """
    invoke_parser: argparse.ArgumentParser = subparsers.add_parser("invokeai", help="InvokeAI 相关命令")
    invoke_sub = invoke_parser.add_subparsers(dest="invokeai_action", required=True)

    # reinstall-pytorch
    reinstall_pytorch_p = invoke_sub.add_parser("reinstall-pytorch", help="重装 PyTorch")
    reinstall_pytorch_p.add_argument("--device-type", type=str, dest="device_type", help="设备类型 (cuda, rocm, cpu, mps)")
    # reinstall_pytorch_p.add_argument("--use-pypi-mirror", action="store_true", dest="use_pypi_mirror", help="使用国内 PyPI 镜像源")
    reinstall_pytorch_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    # reinstall_pytorch_p.add_argument("--use-uv", action="store_true", dest="use_uv", help="使用 uv 安装 PyTorch 软件包")
    reinstall_pytorch_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv 安装 PyTorch 软件包")
    reinstall_pytorch_p.add_argument("--interactive", action="store_true", dest="interactive_mode", help="启用交互模式")
    reinstall_pytorch_p.set_defaults(
        func=lambda args: reinstall_invokeai_pytorch(
            device_type=args.device_type,
            use_pypi_mirror=args.use_pypi_mirror,
            use_uv=args.use_uv,
            interactive_mode=args.interactive_mode,
        )
    )

    # install
    install_p = invoke_sub.add_parser("install", help="安装 InvokeAI")
    install_p.add_argument("--invokeai-path", type=normalized_filepath, required=False, default=INVOKEAI_ROOT_PATH, dest="invokeai_path", help="InvokeAI 根目录")
    install_p.add_argument("--device-type", type=str, dest="device_type", help="设备类型 (cuda, rocm, cpu, mps)")
    install_p.add_argument("--version", dest="version", help="自定义安装版本")
    # install_p.add_argument("--use-pypi-mirror", action="store_true", dest="use_pypi_mirror", help="使用国内 PyPI 镜像源")
    install_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    # install_p.add_argument("--use-uv", action="store_true", dest="use_uv", help="使用 uv 安装 Python 软件包")
    install_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv 安装 Python 软件包")
    # install_p.add_argument("--pre-download-model", action="store_false", dest="no_pre_download_model", help="启用预下载模型")
    install_p.add_argument("--no-pre-download-model", action="store_true", dest="no_pre_download_model", help="禁用预下载模型")
    # install_p.add_argument("--use-cn-model-mirror", action="store_true", dest="use_cn_model_mirror", help="使用国内镜像下载模型")
    install_p.add_argument("--no-cn-model-mirror", action="store_false", dest="use_cn_model_mirror", help="不使用国内镜像下载模型")
    install_p.set_defaults(
        func=lambda args: install(
            invokeai_path=args.invokeai_path,
            device_type=args.device_type,
            invokeai_version=args.version,
            use_pypi_mirror=args.use_pypi_mirror,
            use_uv=args.use_uv,
            no_pre_download_model=args.no_pre_download_model,
            use_cn_model_mirror=args.use_cn_model_mirror,
        )
    )

    # update
    update_p = invoke_sub.add_parser("update", help="更新 InvokeAI")
    # update_p.add_argument("--use-pypi-mirror", action="store_true", dest="use_pypi_mirror", help="使用国内 PyPI 镜像源")
    update_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    # update_p.add_argument("--use-uv", action="store_true", dest="use_uv", help="使用 uv 安装 Python 软件包")
    update_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv 安装 Python 软件包")
    update_p.set_defaults(
        func=lambda args: update(
            use_pypi_mirror=args.use_pypi_mirror,
            use_uv=args.use_uv,
        )
    )

    # check-env
    check_p = invoke_sub.add_parser("check-env", help="检查 InvokeAI 运行环境")
    # check_p.add_argument("--use-uv", action="store_true", dest="use_uv", help="使用 uv")
    check_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv")
    # check_p.add_argument("--use-pypi-mirror", action="store_true", dest="use_pypi_mirror", help="使用国内 PyPI 镜像源")
    check_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    check_p.set_defaults(
        func=lambda args: check_env(
            use_uv=args.use_uv,
            use_pypi_mirror=args.use_pypi_mirror,
        )
    )

    # launch
    launch_p = invoke_sub.add_parser("launch", help="启动 InvokeAI")
    launch_p.add_argument("--invokeai-path", type=normalized_filepath, required=False, default=INVOKEAI_ROOT_PATH, dest="invokeai_path", help="InvokeAI 根目录")
    launch_p.add_argument("--launch-args", type=str, dest="launch_args", help='启动参数 (请使用引号包裹，例如 "--theme dark")')
    # launch_p.add_argument("--use-hf-mirror", action="store_true", dest="use_hf_mirror", help="启用 HuggingFace 镜像源")
    launch_p.add_argument("--no-hf-mirror", action="store_false", dest="use_hf_mirror", help="禁用 HuggingFace 镜像源")
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
            invokeai_path=args.invokeai_path,
            launch_args=args.launch_args,
            use_hf_mirror=args.use_hf_mirror,
            use_pypi_mirror=args.use_pypi_mirror,
            use_cuda_malloc=args.use_cuda_malloc,
            check_launch_env=args.check_env,
        )
    )

    # custom-node
    node_parser = invoke_sub.add_parser("custom-node", help="扩展管理")
    node_sub = node_parser.add_subparsers(dest="node_action", required=True)

    # custom-node install
    node_install_p = node_sub.add_parser("install", help="安装扩展")
    node_install_p.add_argument("--invokeai-path", type=normalized_filepath, required=False, default=INVOKEAI_ROOT_PATH, dest="invokeai_path", help="InvokeAI 根目录")
    node_install_p.add_argument("--url", required=True, dest="url", help="扩展下载链接")
    # node_install_p.add_argument("--use-github-mirror", action="store_true", dest="use_github_mirror", help="使用 Github 镜像源")
    node_install_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    node_install_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    # node_install_p.add_argument("--check-error", action="store_true", dest="check", help="检查错误")
    node_install_p.add_argument("--no-check-error", action="store_false", dest="check", help="不检查错误")
    node_install_p.set_defaults(
        func=lambda args: install_custom_nodes(
            invokeai_path=args.invokeai_path,
            custom_node_url=args.url,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
            check=args.check,
        )
    )

    # custom-node status
    node_status_p = node_sub.add_parser("status", help="设置扩展启用状态")
    node_status_p.add_argument("--invokeai-path", type=normalized_filepath, required=False, default=INVOKEAI_ROOT_PATH, dest="invokeai_path", help="InvokeAI 根目录")
    node_status_p.add_argument("--name", required=True, dest="name", help="扩展名称")
    node_status_p.add_argument("--enable", action="store_true", dest="status", help="启用扩展")
    node_status_p.add_argument("--disable", action="store_false", dest="status", help="禁用扩展")
    node_status_p.set_defaults(
        func=lambda args: set_custom_node_status(
            invokeai_path=args.invokeai_path,
            custom_node_name=args.name,
            status=args.status,
        )
    )

    # custom-node list
    node_list_p = node_sub.add_parser("list", help="列出扩展")
    node_list_p.add_argument("--invokeai-path", type=normalized_filepath, required=False, default=INVOKEAI_ROOT_PATH, dest="invokeai_path", help="InvokeAI 根目录")
    node_list_p.set_defaults(func=lambda args: list_custom_nodes(invokeai_path=args.invokeai_path))

    # custom-node update
    node_update_p = node_sub.add_parser("update", help="更新扩展")
    node_update_p.add_argument("--invokeai-path", type=normalized_filepath, required=False, default=INVOKEAI_ROOT_PATH, dest="invokeai_path", help="InvokeAI 根目录")
    # node_update_p.add_argument("--use-github-mirror", action="store_true", dest="use_github_mirror", help="使用 Github 镜像源")
    node_update_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    node_update_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    # node_update_p.add_argument("--check-error", action="store_true", dest="check", help="检查错误")
    node_update_p.add_argument("--no-check-error", action="store_false", dest="check", help="不检查错误")
    node_update_p.set_defaults(
        func=lambda args: update_custom_nodes(
            invokeai_path=args.invokeai_path,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
            check=args.check,
        )
    )

    # custom-node uninstall
    node_uninstall_p = node_sub.add_parser("uninstall", help="卸载扩展")
    node_uninstall_p.add_argument("--invokeai-path", type=normalized_filepath, required=False, default=INVOKEAI_ROOT_PATH, dest="invokeai_path", help="InvokeAI 根目录")
    node_uninstall_p.add_argument("--name", required=True, dest="name", help="扩展名称")
    # node_uninstall_p.add_argument("--check-error", action="store_true", dest="check", help="检查错误")
    node_uninstall_p.add_argument("--no-check-error", action="store_false", dest="check", help="不检查错误")
    node_uninstall_p.set_defaults(
        func=lambda args: uninstall_custom_node(
            invokeai_path=args.invokeai_path,
            custom_node_name=args.name,
            check=args.check,
        )
    )

    # model
    model_parser = invoke_sub.add_parser("model", help="模型管理")
    model_sub = model_parser.add_subparsers(dest="model_action", required=True)

    # model install-library
    model_lib_p = model_sub.add_parser("install-library", help="从模型库安装模型")
    model_lib_p.add_argument("--invokeai-path", type=normalized_filepath, required=False, default=INVOKEAI_ROOT_PATH, dest="invokeai_path", help="InvokeAI 根目录")
    model_lib_p.add_argument("--source", default="modelscope", dest="source", help="模型下载源类型")
    model_lib_p.add_argument("--name", dest="name", help="模型名称")
    model_lib_p.add_argument("--index", type=int, dest="index", help="模型索引")
    model_lib_p.add_argument("--downloader", default="aria2", dest="downloader", help="下载工具")
    model_lib_p.add_argument("--interactive", action="store_true", dest="interactive", help="启用交互模式")
    model_lib_p.set_defaults(
        func=lambda args: install_model_from_library(
            invokeai_path=args.invokeai_path,
            download_resource_type=args.source,
            model_name=args.name,
            model_index=args.index,
            downloader=args.downloader,
            interactive_mode=args.interactive,
        )
    )

    # model install-url
    model_url_p = model_sub.add_parser("install-url", help="从链接安装模型")
    model_url_p.add_argument("--invokeai-path", type=normalized_filepath, required=False, default=INVOKEAI_ROOT_PATH, dest="invokeai_path", help="InvokeAI 根目录")
    model_url_p.add_argument("--url", required=True, dest="url", help="模型下载地址")
    model_url_p.add_argument("--type", required=True, dest="type", help="模型类型")
    model_url_p.add_argument("--downloader", default="aria2", dest="downloader", help="下载工具")
    model_url_p.set_defaults(
        func=lambda args: install_model_from_url(
            sd_webui_path=args.invokeai_path,
            model_url=args.url,
            model_type=args.type,
            downloader=args.downloader,
        )
    )

    # model list
    model_list_p = model_sub.add_parser("list", help="列出模型")
    model_list_p.set_defaults(func=lambda args: list_models())

    # model uninstall
    model_uninstall_p = model_sub.add_parser("uninstall", help="卸载模型")
    model_uninstall_p.add_argument("--name", required=True, dest="name", help="模型名称")
    model_uninstall_p.add_argument("--interactive", action="store_true", dest="interactive", help="启用交互模式")
    model_uninstall_p.set_defaults(
        func=lambda args: uninstall_model(
            model_name=args.name,
            interactive_mode=args.interactive,
        )
    )
