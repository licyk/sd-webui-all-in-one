import argparse
import shlex
from pathlib import Path

from sd_webui_all_in_one.base_manager.comfyui_base import (
    install_comfyui,
    update_comfyui,
    check_comfyui_env,
    launch_comfyui,
    install_comfyui_custom_node,
    set_comfyui_custom_node_status,
    list_comfyui_custom_nodes,
    update_comfyui_custom_nodes,
    uninstall_comfyui_custom_node,
    install_comfyui_model_from_library,
    install_comfyui_model_from_url,
    list_comfyui_models,
    uninstall_comfyui_model,
)
from sd_webui_all_in_one.config import COMFYUI_ROOT_PATH
from sd_webui_all_in_one.downloader import DownloadToolType
from sd_webui_all_in_one.model_downloader.base import ModelDownloadUrlType
from sd_webui_all_in_one.pytorch_manager.base import PyTorchDeviceType
from sd_webui_all_in_one.utils import normalized_filepath
from sd_webui_all_in_one.base_manager.base import reinstall_pytorch

def install(
    comfyui_path: Path,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_pypi_mirror: bool | None = True,
    use_uv: bool | None = True,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    no_pre_download_extension: bool | None = False,
    no_pre_download_model: bool | None = False,
    use_cn_model_mirror: bool | None = True,
) -> None:
    """安装 ComfyUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
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
        no_pre_download_extension (bool | None):
            是否禁用预下载 ComfyUI 扩展
        no_pre_download_model (bool | None):
            是否禁用预下载模型
        use_cn_model_mirror (bool | None):
            是否使用国内镜像下载模型
    """
    install_comfyui(
        comfyui_path=comfyui_path,
        pytorch_mirror_type=pytorch_mirror_type,
        custom_pytorch_package=custom_pytorch_package,
        custom_xformers_package=custom_xformers_package,
        use_pypi_mirror=use_pypi_mirror,
        use_uv=use_uv,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        no_pre_download_extension=no_pre_download_extension,
        no_pre_download_model=no_pre_download_model,
        use_cn_model_mirror=use_cn_model_mirror,
    )


def update(
    comfyui_path: Path,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 ComfyUI

    Args:
        comfyui_path (Path):
            Stable DIffusion WebUI 根目录
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
    """
    update_comfyui(
        comfyui_path=comfyui_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def check_env(
    comfyui_path: Path,
    install_conflict_component_requirement: bool | None = False,
    interactive_mode: bool | None = False,
    use_uv: bool | None = True,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool | None = False,
) -> None:
    """检查 ComfyUI 运行环境

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        install_conflict_component_requirement (bool | None):
            检测到冲突依赖时是否按顺序安装组件依赖
        interactive_mode (bool | None):
            是否启用交互模式, 当检测到冲突依赖时将询问是否安装冲突组件依赖
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        use_pypi_mirror (bool | None):
            是否启用 PyPI 镜像源
    """
    check_comfyui_env(
        comfyui_path=comfyui_path,
        install_conflict_component_requirement=install_conflict_component_requirement,
        interactive_mode=interactive_mode,
        use_uv=use_uv,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        use_pypi_mirror=use_pypi_mirror,
    )


def launch(
    comfyui_path: Path,
    launch_args: str | list[str] | None = None,
    use_hf_mirror: bool | None = False,
    custom_hf_mirror: str | list[str] | None = None,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool | None = False,
    use_cuda_malloc: bool | None = True,
    use_uv: bool | None = True,
    interactive_mode: bool | None = False,
    install_conflict_component_requirement: bool | None = False,
    check_launch_env: bool | None = True,
) -> None:
    """启动 ComfyUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        launch_args (str | list[str] | None):
            启动 ComfyUI 的参数
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
        interactive_mode (bool | None):
            是否启用交互模式
        install_conflict_component_requirement (bool | None):
            检测到冲突依赖时是否按顺序安装组件依赖
        check_launch_env (bool | None):
            是否在启动前检查运行环境
    """
    if check_launch_env:
        check_comfyui_env(
            comfyui_path=comfyui_path,
            install_conflict_component_requirement=install_conflict_component_requirement,
            interactive_mode=interactive_mode,
            use_uv=use_uv,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
            use_pypi_mirror=use_pypi_mirror,
        )
    if isinstance(launch_args, str):
        launch_args = shlex.split(launch_args)
    elif launch_args is None:
        launch_args = []
    launch_comfyui(
        comfyui_path=comfyui_path,
        launch_args=launch_args,
        use_hf_mirror=use_hf_mirror,
        custom_hf_mirror=custom_hf_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        use_pypi_mirror=use_pypi_mirror,
        use_cuda_malloc=use_cuda_malloc,
    )


def install_custom_node(
    comfyui_path: Path,
    custom_node_url: str | list[str],
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """安装 ComfyUI 扩展

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        custom_node_url (str | list[str]):
            ComfyUI 扩展下载链接
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
    """
    install_comfyui_custom_node(
        comfyui_path=comfyui_path,
        custom_node_url=custom_node_url,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def set_custom_node_status(
    comfyui_path: Path,
    custom_node_name: str,
    status: bool,
) -> None:
    """设置 ComfyUI 启用状态

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        extension_name (str):
            ComfyUI 扩展名称
        status (bool):
            设置扩展的启用状态
            - `True`: 启用
            - `False`: 禁用
    """
    set_comfyui_custom_node_status(
        comfyui_path=comfyui_path,
        custom_node_name=custom_node_name,
        status=status,
    )


def list_custom_nodes(
    comfyui_path: Path,
) -> None:
    """获取 ComfyUI 本地扩展列表

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
    """
    for ext in list_comfyui_custom_nodes(comfyui_path=comfyui_path):
        print(f"- {ext['name']}")
        print(f"  - 安装路径: {ext['path']}")
        print(f"  - 远程地址: {ext['url']}")
        print(f"  - 启用状态: {ext['status']}")
        print(f"  - 版本: {ext['commit']}")
        print(f"  - 分支: {ext['branch']}")
        print()


def update_custom_nodes(
    comfyui_path: Path,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 ComfyUI 扩展

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
    """
    update_comfyui_custom_nodes(
        comfyui_path=comfyui_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def uninstall_custom_node(
    comfyui_path: Path,
    custom_node_name: str,
) -> None:
    """卸载 ComfyUI 扩展

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        extension_name (str):
            ComfyUI 扩展名称
    """
    uninstall_comfyui_custom_node(
        comfyui_path=comfyui_path,
        custom_node_name=custom_node_name,
    )


def install_model_from_library(
    comfyui_path: Path,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = "aria2",
    interactive_mode: bool | None = False,
    list_only: bool | None = False,
) -> None:
    """为 ComfyUI 下载模型, 使用模型库进行下载

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
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
    install_comfyui_model_from_library(
        comfyui_path=comfyui_path,
        download_resource_type=download_resource_type,
        model_name=model_name,
        model_index=model_index,
        downloader=downloader,
        interactive_mode=interactive_mode,
        list_only=list_only,
    )


def install_model_from_url(
    comfyui_path: Path,
    model_url: str,
    model_type: str,
    downloader: DownloadToolType | None = "aria2",
) -> None:
    """从链接下载模型到 ComfyUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        model_url (str):
            模型下载地址
        model_type (str):
            模型的类型
        downloader (DownloadToolType | None):
            下载模型使用的工具
    """
    install_comfyui_model_from_url(
        comfyui_path=comfyui_path,
        model_url=model_url,
        model_type=model_type,
        downloader=downloader,
    )


def list_models(
    comfyui_path: Path,
) -> None:
    """列出 ComfyUI 的模型目录

    Args:
        sd_webui_path (Path):
            ComfyUI 根目录
    """
    list_comfyui_models(comfyui_path=comfyui_path)


def uninstall_model(
    comfyui_path: Path,
    model_name: str,
    model_type: str | None = None,
    interactive_mode: bool | None = False,
) -> None:
    """卸载 ComfyUI 中的模型

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        model_name (str):
            模型名称
        model_type (str | None):
            模型的类型
        interactive_mode (bool | None):
            是否启用交互模式
    """
    uninstall_comfyui_model(
        comfyui_path=comfyui_path,
        model_name=model_name,
        model_type=model_type,
        interactive_mode=interactive_mode,
    )


def register_comfyui(subparsers: "argparse._SubParsersAction") -> None:
    """注册 ComfyUI 模块及其子命令

    Args:
        subparsers (argparse._SubParsersAction):
            子命令行解析器
    """
    comfy_parser: argparse.ArgumentParser = subparsers.add_parser("comfyui", help="ComfyUI 相关命令")
    comfy_sub = comfy_parser.add_subparsers(dest="comfyui_action", required=True)

    # reinstall-pytorch
    reinstall_pytorch_p = comfy_sub.add_parser("reinstall-pytorch", help="重装 PyTorch")
    reinstall_pytorch_p.add_argument("--pytorch-name", type=str, dest="pytorch_name", help="PyTorch 版本组合名称")
    reinstall_pytorch_p.add_argument("--pytorch-index", type=int, dest="pytorch_index", help="PyTorch 版本组合索引值")
    # reinstall_pytorch_p.add_argument("--use-pypi-mirror", action="store_true", dest="use_pypi_mirror", help="使用国内 PyPI 镜像源")
    reinstall_pytorch_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    # reinstall_pytorch_p.add_argument("--use-uv", action="store_true", dest="use_uv", help="使用 uv 安装 PyTorch 软件包")
    reinstall_pytorch_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv 安装 PyTorch 软件包")
    reinstall_pytorch_p.add_argument("--interactive", action="store_true", dest="interactive_mode", help="启用交互模式")
    reinstall_pytorch_p.add_argument("--list-only", action="store_true", dest="list_only", help="列出 PyTorch 列表并退出")
    reinstall_pytorch_p.set_defaults(
        func=lambda args: reinstall_pytorch(
            pytorch_name=args.pytorch_name,
            pytorch_index=args.pytorch_index,
            use_pypi_mirror=args.use_pypi_mirror,
            use_uv=args.use_uv,
            interactive_mode=args.interactive_mode,
            list_only=args.list_only,
        )
    )

    # install
    install_p = comfy_sub.add_parser("install", help="安装 ComfyUI")
    install_p.add_argument("--comfyui-path", type=normalized_filepath, required=False, default=COMFYUI_ROOT_PATH, dest="comfyui_path", help="ComfyUI 根目录")
    install_p.add_argument("--pytorch-mirror-type", type=str, dest="pytorch_mirror_type", help="PyTorch 镜像源类型")
    install_p.add_argument("--custom-pytorch-package", type=str, dest="custom_pytorch_package", help="自定义 PyTorch 软件包版本声明")
    install_p.add_argument("--custom-xformers-package", type=str, dest="custom_xformers_package", help="自定义 xFormers 软件包版本声明")
    # install_p.add_argument("--use-pypi-mirror", action="store_true", dest="use_pypi_mirror", help="使用国内 PyPI 镜像源")
    install_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    # install_p.add_argument("--use-uv", action="store_true", dest="use_uv", help="使用 uv 安装 Python 软件包")
    install_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv 安装 Python 软件包")
    # install_p.add_argument("--use-github-mirror", action="store_true", dest="use_github_mirror", help="使用 Github 镜像源")
    install_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    install_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    # install_p.add_argument("--pre-download-extension", action="store_false", dest="no_pre_download_extension", help="启用预下载扩展")
    install_p.add_argument("--no-pre-download-extension", action="store_true", dest="no_pre_download_extension", help="禁用预下载扩展")
    # install_p.add_argument("--pre-download-model", action="store_false", dest="no_pre_download_model", help="启用预下载模型")
    install_p.add_argument("--no-pre-download-model", action="store_true", dest="no_pre_download_model", help="禁用预下载模型")
    # install_p.add_argument("--use-cn-model-mirror", action="store_true", dest="use_cn_model_mirror", help="使用国内镜像下载模型")
    install_p.add_argument("--no-cn-model-mirror", action="store_false", dest="use_cn_model_mirror", help="不使用国内镜像下载模型")
    install_p.set_defaults(
        func=lambda args: install(
            comfyui_path=args.comfyui_path,
            pytorch_mirror_type=args.pytorch_mirror_type,
            custom_pytorch_package=args.custom_pytorch_package,
            custom_xformers_package=args.custom_xformers_package,
            use_pypi_mirror=args.use_pypi_mirror,
            use_uv=args.use_uv,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
            no_pre_download_extension=args.no_pre_download_extension,
            no_pre_download_model=args.no_pre_download_model,
            use_cn_model_mirror=args.use_cn_model_mirror,
        )
    )

    # update
    update_p = comfy_sub.add_parser("update", help="更新 ComfyUI")
    update_p.add_argument("--comfyui-path", type=normalized_filepath, required=False, default=COMFYUI_ROOT_PATH, dest="comfyui_path", help="ComfyUI 根目录")
    # update_p.add_argument("--use-github-mirror", action="store_true", dest="use_github_mirror", help="使用 Github 镜像源")
    update_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    update_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    update_p.set_defaults(
        func=lambda args: update(
            comfyui_path=args.comfyui_path,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
        )
    )

    # check-env
    check_p = comfy_sub.add_parser("check-env", help="检查 ComfyUI 运行环境")
    check_p.add_argument("--comfyui-path", type=normalized_filepath, required=False, default=COMFYUI_ROOT_PATH, dest="comfyui_path", help="ComfyUI 根目录")
    # check_p.add_argument("--use-github-mirror", action="store_true", dest="use_github_mirror", help="使用 Github 镜像源")
    check_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    check_p.add_argument("--install-conflict", action="store_true", dest="install_conflict_component_requirement", help="自动安装冲突组件依赖")
    check_p.add_argument("--interactive", action="store_true", dest="interactive_mode", help="启用交互模式")
    # check_p.add_argument("--use-uv", action="store_true", dest="use_uv", help="使用 uv")
    check_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv")
    check_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    # check_p.add_argument("--use-pypi-mirror", action="store_true", dest="use_pypi_mirror", help="使用国内 PyPI 镜像源")
    check_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    check_p.set_defaults(
        func=lambda args: check_env(
            comfyui_path=args.comfyui_path,
            install_conflict_component_requirement=args.install_conflict_component_requirement,
            interactive_mode=args.interactive_mode,
            use_uv=args.use_uv,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
            use_pypi_mirror=args.use_pypi_mirror,
        )
    )

    # launch
    launch_p = comfy_sub.add_parser("launch", help="启动 ComfyUI")
    launch_p.add_argument("--comfyui-path", type=normalized_filepath, required=False, default=COMFYUI_ROOT_PATH, dest="comfyui_path", help="ComfyUI 根目录")
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
    launch_p.add_argument("--interactive", action="store_true", dest="interactive_mode", help="启用交互模式")
    launch_p.add_argument("--install-conflict", action="store_true", dest="install_conflict_component_requirement", help="自动安装冲突组件依赖")
    # launch_p.add_argument("--check-env", action="store_true", dest="check_env", help="检查运行环境完整性")
    launch_p.add_argument("--no-check-env", action="store_false", dest="check_env", help="不检查运行环境完整性")
    launch_p.set_defaults(
        func=lambda args: launch(
            comfyui_path=args.comfyui_path,
            launch_args=args.launch_args,
            use_hf_mirror=args.use_hf_mirror,
            custom_hf_mirror=args.custom_hf_mirror,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
            use_pypi_mirror=args.use_pypi_mirror,
            use_cuda_malloc=args.use_cuda_malloc,
            use_uv=args.use_uv,
            interactive_mode=args.interactive_mode,
            install_conflict_component_requirement=args.install_conflict_component_requirement,
            check_launch_env=args.check_env,
        )
    )

    # custom-node
    node_parser = comfy_sub.add_parser("custom-node", help="扩展管理")
    node_sub = node_parser.add_subparsers(dest="node_action", required=True)

    # custom-node install
    node_install_p = node_sub.add_parser("install", help="安装扩展")
    node_install_p.add_argument("--comfyui-path", type=normalized_filepath, required=False, default=COMFYUI_ROOT_PATH, dest="comfyui_path", help="ComfyUI 根目录")
    node_install_p.add_argument("--url", required=True, dest="url", help="扩展下载链接")
    # node_install_p.add_argument("--use-github-mirror", action="store_true", dest="use_github_mirror", help="使用 Github 镜像源")
    node_install_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    node_install_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    node_install_p.set_defaults(
        func=lambda args: install_custom_node(
            comfyui_path=args.comfyui_path,
            custom_node_url=args.url,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
        )
    )

    # custom-node status
    node_status_p = node_sub.add_parser("status", help="设置扩展启用状态")
    node_status_p.add_argument("--comfyui-path", type=normalized_filepath, required=False, default=COMFYUI_ROOT_PATH, dest="comfyui_path", help="ComfyUI 根目录")
    node_status_p.add_argument("--name", required=True, dest="name", help="扩展名称")
    node_status_p.add_argument("--enable", action="store_true", dest="status", help="启用扩展")
    node_status_p.add_argument("--disable", action="store_false", dest="status", help="禁用扩展")
    node_status_p.set_defaults(
        func=lambda args: set_custom_node_status(
            comfyui_path=args.comfyui_path,
            custom_node_name=args.name,
            status=args.status,
        )
    )

    # custom-node list
    node_list_p = node_sub.add_parser("list", help="列出扩展")
    node_list_p.add_argument("--comfyui-path", type=normalized_filepath, required=False, default=COMFYUI_ROOT_PATH, dest="comfyui_path", help="ComfyUI 根目录")
    node_list_p.set_defaults(func=lambda args: list_custom_nodes(comfyui_path=args.comfyui_path))

    # custom-node update
    node_update_p = node_sub.add_parser("update", help="更新扩展")
    node_update_p.add_argument("--comfyui-path", type=normalized_filepath, required=False, default=COMFYUI_ROOT_PATH, dest="comfyui_path", help="ComfyUI 根目录")
    # node_update_p.add_argument("--use-github-mirror", action="store_true", dest="use_github_mirror", help="使用 Github 镜像源")
    node_update_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    node_update_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    node_update_p.set_defaults(
        func=lambda args: update_custom_nodes(
            comfyui_path=args.comfyui_path,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
        )
    )

    # custom-node uninstall
    node_uninstall_p = node_sub.add_parser("uninstall", help="卸载扩展")
    node_uninstall_p.add_argument("--comfyui-path", type=normalized_filepath, required=False, default=COMFYUI_ROOT_PATH, dest="comfyui_path", help="ComfyUI 根目录")
    node_uninstall_p.add_argument("--name", required=True, dest="name", help="扩展名称")
    node_uninstall_p.set_defaults(
        func=lambda args: uninstall_custom_node(
            comfyui_path=args.comfyui_path,
            custom_node_name=args.name,
        )
    )

    # model
    model_parser = comfy_sub.add_parser("model", help="模型管理")
    model_sub = model_parser.add_subparsers(dest="model_action", required=True)

    # model install-library
    model_lib_p = model_sub.add_parser("install-library", help="从模型库安装模型")
    model_lib_p.add_argument("--comfyui-path", type=normalized_filepath, required=False, default=COMFYUI_ROOT_PATH, dest="comfyui_path", help="ComfyUI 根目录")
    model_lib_p.add_argument("--source", default="modelscope", dest="source", help="模型下载源类型")
    model_lib_p.add_argument("--name", dest="name", help="模型名称")
    model_lib_p.add_argument("--index", type=int, dest="index", help="模型索引")
    model_lib_p.add_argument("--downloader", default="aria2", dest="downloader", help="下载工具")
    model_lib_p.add_argument("--interactive", action="store_true", dest="interactive", help="启用交互模式")
    model_lib_p.add_argument("--list-only", action="store_true", dest="list_only", help="列出模型列表并退出")
    model_lib_p.set_defaults(
        func=lambda args: install_model_from_library(
            comfyui_path=args.comfyui_path,
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
    model_url_p.add_argument("--comfyui-path", type=normalized_filepath, required=False, default=COMFYUI_ROOT_PATH, dest="comfyui_path", help="ComfyUI 根目录")
    model_url_p.add_argument("--url", required=True, dest="url", help="模型下载地址")
    model_url_p.add_argument("--type", required=True, dest="type", help="模型类型")
    model_url_p.add_argument("--downloader", default="aria2", dest="downloader", help="下载工具")
    model_url_p.set_defaults(
        func=lambda args: install_model_from_url(
            comfyui_path=args.comfyui_path,
            model_url=args.url,
            model_type=args.type,
            downloader=args.downloader,
        )
    )

    # model list
    model_list_p = model_sub.add_parser("list", help="列出模型")
    model_list_p.add_argument("--comfyui-path", type=normalized_filepath, required=False, default=COMFYUI_ROOT_PATH, dest="comfyui_path", help="ComfyUI 根目录")
    model_list_p.set_defaults(func=lambda args: list_models(comfyui_path=args.comfyui_path))

    # model uninstall
    model_uninstall_p = model_sub.add_parser("uninstall", help="卸载模型")
    model_uninstall_p.add_argument("--comfyui-path", type=normalized_filepath, required=False, default=COMFYUI_ROOT_PATH, dest="comfyui_path", help="ComfyUI 根目录")
    model_uninstall_p.add_argument("--name", required=True, dest="name", help="模型名称")
    model_uninstall_p.add_argument("--type", dest="type", help="模型类型")
    model_uninstall_p.add_argument("--interactive", action="store_true", dest="interactive", help="启用交互模式")
    model_uninstall_p.set_defaults(
        func=lambda args: uninstall_model(
            comfyui_path=args.comfyui_path,
            model_name=args.name,
            model_type=args.type,
            interactive_mode=args.interactive,
        )
    )
