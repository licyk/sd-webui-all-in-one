"""Implementation grouped from the former ``invokeai_base.py`` module."""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import sys
from contextlib import contextmanager
from tempfile import TemporaryDirectory
from typing import (
    Iterator,
    cast,
)
from pathlib import Path
from sd_webui_all_in_one.ansi_color import ANSIColor
from sd_webui_all_in_one.base_manager.base import (
    prepare_pytorch_install_info,
    install_pytorch_with_fallback,
)
from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.downloader import (
    DownloadToolType,
    download_file,
)
from sd_webui_all_in_one.file_manager import (
    copy_files,
)
from sd_webui_all_in_one.mirror_manager import (
    get_pypi_mirror_config,
)
from sd_webui_all_in_one.pkg_manager import (
    install_pytorch,
    pip_install,
)
from sd_webui_all_in_one.package_analyzer import (
    get_package_name,
    get_package_version_from_library,
)
from sd_webui_all_in_one.pytorch_manager import (
    auto_detect_pytorch_device_category,
    get_pytorch_mirror_type,
    PYTORCH_DEVICE_CATEGORY_LIST,
    PyTorchDeviceType,
    PyTorchDeviceTypeCategory,
)
from sd_webui_all_in_one.launch_arguments import (
    HelpCommand,
    LaunchArgumentDiscoveryContext,
)
from sd_webui_all_in_one.utils import print_divider

from .shared import logger


@contextmanager
def _temporary_invokeai_root(
    invokeai_path: Path | None,
) -> Iterator[None]:
    """临时指定 InvokeAI 根目录"""
    if invokeai_path is None:
        yield
        return

    old_root = os.environ.get("INVOKEAI_ROOT")
    os.environ["INVOKEAI_ROOT"] = Path(invokeai_path).as_posix()
    try:
        yield
    finally:
        if old_root is None:
            os.environ.pop("INVOKEAI_ROOT", None)
        else:
            os.environ["INVOKEAI_ROOT"] = old_root


def _invokeai_help_command(
    context: LaunchArgumentDiscoveryContext,
) -> HelpCommand:
    """构建 InvokeAI 参数解析器的 ``--help`` 等价命令。"""
    try:
        version = importlib.metadata.version("invokeai")
    except importlib.metadata.PackageNotFoundError:
        version = "unavailable"
    code = "from invokeai.frontend.cli.arg_parser import _parser; _parser.print_help()"
    env = os.environ.copy()
    env["INVOKEAI_ROOT"] = str(context.webui_path)
    return HelpCommand(
        [str(context.python_executable), "-c", code],
        f"invokeai.frontend.cli.arg_parser:_parser:{version}",
        env,
    )


def get_pytorch_mirror_type_for_ivnokeai(
    device_type: PyTorchDeviceTypeCategory,
) -> PyTorchDeviceType:
    """获取 InvokeAI 安装 PyTorch 所需的 PyTorch 镜像源类型

    Args:
        device_type (PyTorchDeviceTypeCategory):
            显卡设备类型

    Returns:
        PyTorchDeviceType:
            PyTorch 镜像源类型
    """
    from .lifecycle import get_invokeai_require_torch_version

    torch_ver = get_invokeai_require_torch_version()
    return get_pytorch_mirror_type(torch_ver=torch_ver, device_type=device_type)


def get_pytorch_for_invokeai() -> str:
    """获取 InvokeAI 所依赖的 PyTorch 包版本声明

    Returns:
        str:
            PyTorch 包版本声明
    """
    pytorch_ver = []
    try:
        invokeai_requires = importlib.metadata.requires("invokeai") or []
    except Exception:
        invokeai_requires = []

    torch_added = False
    torchvision_added = False
    torchaudio_added = False

    for require in invokeai_requires:
        require = require.split(";")[0].strip()
        package_name = get_package_name(require)

        if package_name == "torch" and not torch_added:
            pytorch_ver.append(require)
            torch_added = True

        if package_name == "torchvision" and not torchvision_added:
            pytorch_ver.append(require)
            torchvision_added = True

        if package_name == "torchaudio" and not torchaudio_added:
            pytorch_ver.append(require)
            torchaudio_added = True

    return " ".join([str(x).strip() for x in pytorch_ver])


def get_xformers_for_invokeai() -> str:
    """获取 InvokeAI 所依赖的 xFormers 包版本声明

    Returns:
        str: xFormers 包版本声明
    """
    pytorch_ver = []
    try:
        invokeai_requires = importlib.metadata.requires("invokeai") or []
    except Exception as _:
        invokeai_requires = []

    for require in invokeai_requires:
        require = require.split(";")[0].strip()
        package_name = get_package_name(require)
        if package_name == "xformers":
            pytorch_ver.append(require)
            break

    return " ".join([str(x).strip() for x in pytorch_ver])


def _ensure_invokeai_package_installed(
    use_uv: bool = True,
    custom_env: dict[str, str] | None = None,
) -> None:
    """确保 InvokeAI 核心包已安装"""
    if get_package_version_from_library("invokeai") is not None:
        logger.info("检测到 InvokeAI 核心包已安装")
        return

    logger.info("未检测到 InvokeAI 核心包, 使用 --no-deps 安装 InvokeAI")
    pip_install(
        "invokeai",
        "--no-deps",
        use_uv=use_uv,
        custom_env=custom_env,
    )


def sync_invokeai_component(
    device_type: PyTorchDeviceTypeCategory | None = None,
    use_pypi_mirror: bool = False,
    use_uv: bool = True,
) -> None:
    """同步 InvokeAI 组件

    Args:
        device_type (PyTorchDeviceTypeCategory | None):
            显卡设备类型
        use_pypi_mirror (bool):
            是否使用国内 PyPI 镜像
        use_uv (bool):
            是否使用 uv 安装 Python 软件包

    Raises:
        RuntimeError:
            同步 InvokeAI 组件发生错误时
    """
    logger.info("获取 InvokeAI 安装配置")

    # 获取 InvokeAI 和 InvokeAI 所需的 PyTorch 的版本
    invokeai_ver = importlib.metadata.version("invokeai")
    from .lifecycle import get_invokeai_require_torch_version

    torch_ver = get_invokeai_require_torch_version()

    # 配置安装 PyTorch 的镜像源
    if device_type is None:
        device_type = auto_detect_pytorch_device_category()

    pytorch_mirror_type = get_pytorch_mirror_type_for_ivnokeai(device_type)
    _, _, custom_env_pytorch = prepare_pytorch_install_info(
        pytorch_mirror_type=pytorch_mirror_type,
        custom_pytorch_package=f"torch=={torch_ver}",
        use_cn_mirror=use_pypi_mirror,
    )

    # 配置安装 PyTorch 所需的包版本声明
    pytorch_package = get_pytorch_for_invokeai()
    xformers_package = get_xformers_for_invokeai()
    torch_with_xformers = " ".join(pytorch_package.split() + xformers_package.split())
    torch_without_xformers = " ".join(pytorch_package.split())

    # 准备安装依赖的 PyPI 镜像源
    custom_env = get_pypi_mirror_config(use_pypi_mirror)

    logger.debug("InvokeAI 所需的 PyTorch 版本: %s", torch_ver)
    logger.debug("InvokeAI 使用的 PyTorch 镜像源类型: %s", pytorch_mirror_type)
    logger.debug("安装的 PyTorch: %s", pytorch_package)
    logger.debug("安装的 xFormers: %s", xformers_package)

    try:
        logger.info("同步 PyTorch 组件中")
        if pytorch_mirror_type in ["cpu", "xpu", "ipex_legacy_arc", "rocm6.2", "all"]:
            logger.debug("使用无 xFormers 安装")
            install_pytorch_with_fallback(
                torch_package=torch_without_xformers,
                custom_env=custom_env_pytorch,
                use_uv=use_uv,
            )
        else:
            try:
                logger.debug("尝试加上 xFormer 进行安装")
                install_pytorch(
                    torch_package=torch_with_xformers,
                    custom_env=custom_env_pytorch,
                    use_uv=use_uv,
                )
            except RuntimeError:
                logger.debug("尝试无 xFormers 安装")
                install_pytorch_with_fallback(
                    torch_package=torch_without_xformers,
                    custom_env=custom_env_pytorch,
                    use_uv=use_uv,
                )

        logger.info("同步 InvokeAI 其他组件中")
        pip_install(
            f"invokeai=={invokeai_ver}",
            use_uv=use_uv,
            custom_env=custom_env,
        )
        logger.info("同步 InvokeAI 组件完成")

    except RuntimeError as e:
        logger.error("同步 InvokeAI 组件时发生了错误: %s", e)
        raise RuntimeError(f"同步 InvokeAI 组件时发生了错误: {e}") from e


def install_invokeai_component(
    device_type: PyTorchDeviceTypeCategory | None = None,
    invokeai_version: str | None = None,
    upgrade: bool = False,
    use_pypi_mirror: bool = False,
    use_uv: bool = True,
) -> None:
    """安装 InvokeAI

    Args:
        device_type (PyTorchDeviceTypeCategory | None):
            显卡设备类型
        invokeai_version (str | None):
            指定安装 InvokeAI 的版本
        upgrade (bool):
            更新 InvokeAI
        use_pypi_mirror (bool):
            是否使用国内 PyPI 镜像
        use_uv (bool):
            是否使用 uv 安装 Python 软件包

    Raises:
        RuntimeError:
            安装 InvokeAI 出现错误时
    """

    if invokeai_version is None:
        invokeai_package = "invokeai"
    else:
        invokeai_package = f"invokeai=={invokeai_version}"

    logger.info("安装 InvokeAI 核心中")
    try:
        if upgrade:
            pip_install(invokeai_package, "--no-deps", "--upgrade", use_uv=use_uv)
        else:
            pip_install(invokeai_package, "--no-deps", use_uv=use_uv)

        sync_invokeai_component(
            device_type=device_type,
            use_pypi_mirror=use_pypi_mirror,
            use_uv=use_uv,
        )
    except RuntimeError as e:
        logger.error("安装 InvokeAI 失败: %s", e)
        raise RuntimeError(f"安装 InvokeAI 发生错误: {e}") from e


def install_pypatchmatch(
    use_cn_mirror: bool = False,
    downloader: DownloadToolType | None = None,
) -> None:
    """为 Windows 的 PyPatchMatch 安装组件

    Args:
        use_cn_mirror (bool):
            是否使用国内下载镜像
        downloader (DownloadToolType | None):
            使用的下载器

    Raises:
        ModuleNotFoundError:
            未找到 PyPatchMatch 时
        RuntimeError:
            安装 pypatchmatch 模块组件发生错误时
    """
    if sys.platform != "win32":
        return

    try:
        package_files = importlib.metadata.files("pypatchmatch")
        if package_files is None:
            raise ModuleNotFoundError("未找到 pypatchmatch 模块文件列表")
        util = [p for p in package_files if "__init__.py" in str(p)][0]
        path = Path(util.locate()).parent
    except Exception as e:
        raise ModuleNotFoundError(f"未找到 pypatchmatch 模块路径, 无法安装 pypatchmatch 所需库: {e}") from e

    tasks = [
        (
            [
                "https://www.modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/patchmatch/libpatchmatch_windows_amd64.dll",
                "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/patchmatch/libpatchmatch_windows_amd64.dll",
            ],
            "libpatchmatch_windows_amd64.dll",
        ),
        (
            [
                "https://www.modelscope.cn/models/licyks/sd-webui-all-in-one/resolve/master/patchmatch/opencv_world460.dll",
                "https://huggingface.co/licyk/sd-webui-all-in-one/resolve/main/patchmatch/opencv_world460.dll",
            ],
            "opencv_world460.dll",
        ),
    ]

    logger.info("安装 PyPatchMatch 组件中")
    with TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        for urls, file in tasks:
            save_path = path / file
            if save_path.is_file():
                continue

            try:
                file_path = download_file(
                    url=urls[0] if use_cn_mirror else urls[1],
                    path=tmp_dir / file,
                    save_name=file,
                    tool=downloader,
                )
                copy_files(file_path, save_path)
            except Exception as e:
                raise RuntimeError(f"下载 '{file}' 时发生错误, 无法安装 pypatchmatch 模块组件: {e}") from e

    logger.info("PyPatchMatch 组件安装完成")


def reinstall_invokeai_pytorch(
    device_type: PyTorchDeviceTypeCategory | None = None,
    use_pypi_mirror: bool = True,
    use_uv: bool = True,
    interactive_mode: bool = False,
    list_only: bool = False,
) -> None:
    """PyTorch 重装工具

    Args:
        device_type (PyTorchDeviceTypeCategory | None):
            PyTorch 设备类型
        use_pypi_mirror (bool):
            是否使用 PyPI 国内镜像
        use_uv (bool):
            是否使用 uv 进行 PyTorch 安装
        interactive_mode (bool):
            是否启用交互模式
        list_only (bool):
            是否仅列出 PyTorch 列表并退出
    """

    def _uninstall() -> None:
        run_cmd([Path(sys.executable).as_posix(), "-m", "pip", "uninstall", "torch", "torchvision", "torchaudio", "xformers", "-y"])

    def _install(
        d: PyTorchDeviceTypeCategory | None,
    ) -> None:
        install_invokeai_component(
            device_type=d,
            use_pypi_mirror=use_pypi_mirror,
            use_uv=use_uv,
        )

    def _get_torch_and_xformers_ver() -> tuple[str | None, str | None]:
        try:
            _torch_ver = importlib.metadata.version("torch")
        except Exception:
            _torch_ver = None
        try:
            _xformers_ver = importlib.metadata.version("xformers")
        except Exception:
            _xformers_ver = None
        return (_torch_ver, _xformers_ver)

    if list_only:
        print("".join([f"- {i}. {d}" for i, d in enumerate(PYTORCH_DEVICE_CATEGORY_LIST + ["auto"], start=1)]))
        return

    has_err = False

    if interactive_mode:
        while True:
            print_divider("=")
            print("\n".join([f"- {ANSIColor.GOLD}{i}{ANSIColor.RESET}. {ANSIColor.WHITE}{d}{ANSIColor.RESET}" for i, d in enumerate(PYTORCH_DEVICE_CATEGORY_LIST + ["auto"], start=1)]))
            print_divider("=")
            if has_err:
                logger.warning("输入有误, 请重试")
            has_err = False
            torch_ver, xformers_ver = _get_torch_and_xformers_ver()
            print(
                f"当前已安装的 PyTorch 版本: {torch_ver}\n"
                f"当前已安装的 xFormers 版本: {xformers_ver}\n"
                "请输入要重装的 PyTorch 类型:\n"
                "提示:\n"
                "1. 输入类型后回车即可开始 PyTorch 重装\n"
                "2. 如果不知道使用什么类型的 PyTorch, 可输入 auto 后回车, 此时将根据设备类型自动选择最佳的 PyTorch 类型"
            )
            user_input = input("==> ").strip()
            if user_input == "exit":
                return
            if user_input == "auto" or user_input in PYTORCH_DEVICE_CATEGORY_LIST:
                if user_input == "auto":
                    logger.info("自动根据设备支持情况选择最佳 PyTorch 版本组合")
                    user_input = None
                logger.info("重装 PyTorch 中")
                _uninstall()
                _install(cast(PyTorchDeviceTypeCategory, user_input))
                logger.info("PyTorch 重装完成")
                return
            else:
                has_err = True
                continue
    else:
        logger.info("重装 PyTorch 中")
        _uninstall()
        _install(device_type)
        logger.info("PyTorch 重装完成")
