import argparse
import shlex
from pathlib import Path

from sd_webui_all_in_one.base_manager.qwen_tts_webui_base import (
    install_qwen_tts_webui,
    update_qwen_tts_webui,
    check_qwen_tts_webui_env,
    launch_qwen_tts_webui,
)
from sd_webui_all_in_one.config import QWEN_TTS_WEBUI_ROOT_PATH
from sd_webui_all_in_one.pytorch_manager.base import (
    PYTORCH_DEVICE_LIST,
    PyTorchDeviceType,
)
from sd_webui_all_in_one.utils import normalized_filepath
from sd_webui_all_in_one.base_manager.base import reinstall_pytorch


def install(
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
    """
    install_qwen_tts_webui(
        qwen_tts_webui_path=qwen_tts_webui_path,
        pytorch_mirror_type=pytorch_mirror_type,
        custom_pytorch_package=custom_pytorch_package,
        custom_xformers_package=custom_xformers_package,
        use_pypi_mirror=use_pypi_mirror,
        use_uv=use_uv,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        use_cn_model_mirror=use_cn_model_mirror,
    )


def update(
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
    update_qwen_tts_webui(
        qwen_tts_webui_path=qwen_tts_webui_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def check_env(
    qwen_tts_webui_path: Path,
    use_uv: bool | None = True,
    use_pypi_mirror: bool | None = False,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """检查 Qwen TTS WebUI 运行环境

    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        use_pypi_mirror (bool | None):
            是否使用国内 PyPI 镜像源
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
    """
    check_qwen_tts_webui_env(
        qwen_tts_webui_path=qwen_tts_webui_path,
        use_uv=use_uv,
        use_pypi_mirror=use_pypi_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def launch(
    qwen_tts_webui_path: Path,
    launch_args: list[str] | None = None,
    use_hf_mirror: bool | None = False,
    custom_hf_mirror: str | list[str] | None = None,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool | None = False,
    use_cuda_malloc: bool | None = True,
    use_uv: bool | None = True,
    check_launch_env: bool | None = True,
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
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        check_launch_env (bool | None):
            是否在启动前检查运行环境
    """
    if check_launch_env:
        check_qwen_tts_webui_env(
            qwen_tts_webui_path=qwen_tts_webui_path,
            use_uv=use_uv,
            use_pypi_mirror=use_pypi_mirror,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
        )
    if isinstance(launch_args, str):
        launch_args = shlex.split(launch_args)
    elif launch_args is None:
        launch_args = []
    launch_qwen_tts_webui(
        qwen_tts_webui_path=qwen_tts_webui_path,
        launch_args=launch_args,
        use_hf_mirror=use_hf_mirror,
        custom_hf_mirror=custom_hf_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        use_pypi_mirror=use_pypi_mirror,
        use_cuda_malloc=use_cuda_malloc,
    )


def register_qwen_tts_webui(subparsers: "argparse._SubParsersAction") -> None:
    """注册 Qwen TTS WebUI 模块及其子命令

    Args:
        subparsers (argparse._SubParsersAction):
            子命令行解析器
    """
    qwen_tts_webui_parser: argparse.ArgumentParser = subparsers.add_parser("qwen-tts-webui", help="Qwen TTS WebUI 相关命令")
    qwen_tts_webui_sub = qwen_tts_webui_parser.add_subparsers(dest="qwen_tts_webui_action", required=True)

    # reinstall-pytorch
    reinstall_pytorch_p = qwen_tts_webui_sub.add_parser("reinstall-pytorch", help="重装 PyTorch")
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
    install_p = qwen_tts_webui_sub.add_parser("install", help="安装 Qwen TTS WebUI")
    install_p.add_argument(
        "--qwen-tts-webui-path", type=normalized_filepath, required=False, default=QWEN_TTS_WEBUI_ROOT_PATH, dest="qwen_tts_webui_path", help="Qwen TTS WebUI 根目录"
    )
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
    # install_p.add_argument("--use-cn-model-mirror", action="store_true", dest="use_cn_model_mirror", help="使用国内镜像下载模型")
    install_p.add_argument("--no-cn-model-mirror", action="store_false", dest="use_cn_model_mirror", help="不使用国内镜像下载模型")
    install_p.set_defaults(
        func=lambda args: install(
            qwen_tts_webui_path=args.qwen_tts_webui_path,
            pytorch_mirror_type=args.pytorch_mirror_type,
            custom_pytorch_package=args.custom_pytorch_package,
            custom_xformers_package=args.custom_xformers_package,
            use_pypi_mirror=args.use_pypi_mirror,
            use_uv=args.use_uv,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
            use_cn_model_mirror=args.use_cn_model_mirror,
        )
    )

    # update
    update_p = qwen_tts_webui_sub.add_parser("update", help="更新 Qwen TTS WebUI")
    update_p.add_argument(
        "--qwen-tts-webui-path", type=normalized_filepath, required=False, default=QWEN_TTS_WEBUI_ROOT_PATH, dest="qwen_tts_webui_path", help="Qwen TTS WebUI 根目录"
    )
    # update_p.add_argument("--use-github-mirror", action="store_true", dest="use_github_mirror", help="使用 Github 镜像源")
    update_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    update_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    update_p.set_defaults(
        func=lambda args: update(
            qwen_tts_webui_path=args.qwen_tts_webui_path,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
        )
    )

    # check-env
    check_p = qwen_tts_webui_sub.add_parser("check-env", help="检查 Qwen TTS WebUI 运行环境")
    check_p.add_argument(
        "--qwen-tts-webui-path", type=normalized_filepath, required=False, default=QWEN_TTS_WEBUI_ROOT_PATH, dest="qwen_tts_webui_path", help="Qwen TTS WebUI 根目录"
    )
    # check_p.add_argument("--use-uv", action="store_true", dest="use_uv", help="使用 uv")
    check_p.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv")
    # check_p.add_argument("--use-pypi-mirror", action="store_true", dest="use_pypi_mirror", help="使用国内 PyPI 镜像源")
    check_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    # check_p.add_argument("--use-github-mirror", action="store_true", dest="use_github_mirror", help="使用 Github 镜像源")
    check_p.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    check_p.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    check_p.set_defaults(
        func=lambda args: check_env(
            qwen_tts_webui_path=args.qwen_tts_webui_path,
            use_uv=args.use_uv,
            use_pypi_mirror=args.use_pypi_mirror,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
        )
    )

    # launch
    launch_p = qwen_tts_webui_sub.add_parser("launch", help="启动 Qwen TTS WebUI")
    launch_p.add_argument(
        "--qwen-tts-webui-path", type=normalized_filepath, required=False, default=QWEN_TTS_WEBUI_ROOT_PATH, dest="qwen_tts_webui_path", help="Qwen TTS WebUI 根目录"
    )
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
    # launch_p.add_argument("--check-env", action="store_true", dest="check_env", help="检查运行环境完整性")
    launch_p.add_argument("--no-check-env", action="store_false", dest="check_env", help="不检查运行环境完整性")
    launch_p.set_defaults(
        func=lambda args: launch(
            qwen_tts_webui_path=args.qwen_tts_webui_path,
            launch_args=args.launch_args,
            use_hf_mirror=args.use_hf_mirror,
            custom_hf_mirror=args.custom_hf_mirror,
            use_github_mirror=args.use_github_mirror,
            custom_github_mirror=args.custom_github_mirror,
            use_pypi_mirror=args.use_pypi_mirror,
            use_cuda_malloc=args.use_cuda_malloc,
            check_launch_env=args.check_env,
        )
    )
