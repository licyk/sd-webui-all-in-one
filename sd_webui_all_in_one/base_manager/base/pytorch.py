"""PyTorch 状态、安装和回退策略。"""

import sys
import importlib.metadata
from pathlib import Path
from typing import cast

from sd_webui_all_in_one.mirror_manager import (
    get_auto_pypi_mirror_config,
)
from sd_webui_all_in_one.pytorch_manager import (
    query_pytorch_info_from_library,
    auto_detect_available_pytorch_type,
    auto_detect_pytorch_device_category,
    get_pytorch_mirror,
    get_pytorch_mirror_type,
    display_pytorch_config,
    export_pytorch_list,
    find_latest_pytorch_info,
    normalize_pytorch_version_suffix,
    PyTorchDeviceType,
    PyTorchDeviceTypeCategory,
)
from sd_webui_all_in_one.env_manager import generate_uv_and_pip_env_mirror_config
from sd_webui_all_in_one.package_analyzer import (
    PyWhlVersionComparison,
    get_package_name,
    is_package_has_version,
    get_package_version,
)
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.pkg_manager import install_pytorch
from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.utils import (
    print_divider,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


from .models import PyTorchUpdateStatus


def get_pytorch_update_status() -> PyTorchUpdateStatus:
    """获取当前环境中 PyTorch 的详细更新状态。

    从已安装的 ``torch`` 版本后缀推断并规范化 PyTorch 类型。无法识别
    类型时使用 ``all``，然后与版本表中该类型的最新受支持版本比较。

    Returns:
        PyTorchUpdateStatus:
            PyTorch 安装状态、设备类型、当前版本、最新版本及错误信息。
    """
    try:
        current_version = importlib.metadata.version("torch")
    except importlib.metadata.PackageNotFoundError:
        current_version = None

    _, separator, suffix = (current_version or "").partition("+")
    dtype = normalize_pytorch_version_suffix(suffix) if separator else None
    resolved_dtype: PyTorchDeviceType = dtype or "all"
    try:
        latest_info = find_latest_pytorch_info(resolved_dtype)
    except Exception as exc:
        return PyTorchUpdateStatus(
            installed=current_version is not None,
            current_version=current_version,
            device_type=resolved_dtype,
            latest_version=None,
            latest_name=None,
            has_update=current_version is None,
            error=str(exc),
        )
    latest_torch_spec = next(
        (package for package in (latest_info.get("torch_ver") or "").split() if get_package_name(package) == "torch" and is_package_has_version(package)),
        None,
    )
    if latest_torch_spec is None:
        return PyTorchUpdateStatus(
            installed=current_version is not None,
            current_version=current_version,
            device_type=resolved_dtype,
            latest_version=None,
            latest_name=latest_info.get("name"),
            has_update=current_version is None,
            error=f"PyTorch 版本表中的 '{resolved_dtype}' 类型缺少可比较的 torch 版本",
        )

    latest_version = get_package_version(latest_torch_spec)
    return PyTorchUpdateStatus(
        installed=current_version is not None,
        current_version=current_version,
        device_type=resolved_dtype,
        latest_version=latest_version,
        latest_name=latest_info.get("name"),
        has_update=current_version is None or PyWhlVersionComparison(current_version) < PyWhlVersionComparison(latest_version),
    )


def check_pytorch_version() -> bool:
    """检查当前环境中的 PyTorch 是否需要更新。

    Returns:
        bool:
            未安装 PyTorch 或当前版本低于版本表中的最新版本时返回 True，
            否则返回 False。

    Raises:
        ValueError:
            无法从版本表获取可比较的 PyTorch 版本时抛出。
    """
    status = get_pytorch_update_status()
    if status.error is not None:
        raise ValueError(status.error)
    return status.has_update


def prepare_pytorch_install_info(
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_cn_mirror: bool = False,
) -> tuple[str | None, str | None, dict[str, str]]:
    """配置安装 PyTorch 所需的 PyTorch, xFormers 包版本声明和 PyTorch 镜像源

    Args:
        pytorch_mirror_type (PyTorchDeviceType | None):
            指定的 PyTorch 镜像源类型
        custom_pytorch_package (str | None):
            自定义 PyTorch 软件包版本声明, 例如: `torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118`
        custom_xformers_package (str | None):
            自定义 xFormers 软件包版本声明, 例如: `xformers===0.0.26.post1+cu118`
        use_cn_mirror (bool):
            是否使用国内镜像

    Returns:
        tuple[str | None, str | None, dict[str, str]]:
            PyTorch 软件包版本声明, xFormers 软件包版本声明, 带有 PyPI 镜像源配置的环境变量字典
    """

    def _update_mirror(
        dtype: PyTorchDeviceType,
    ) -> None:
        url, kind = get_pytorch_mirror(
            dtype=dtype,
            use_cn_mirror=use_cn_mirror,
        )
        mirrors[kind] = url

    torch_part: list[str] = []
    mirrors: dict[str, str | list[str] | None] = {
        "index_url": [],
        "extra_index_url": [],
        "find_links": [],
    }

    # 配置 PyTorch 软件包列表
    if custom_pytorch_package is None:
        if pytorch_mirror_type is not None:
            dtype = pytorch_mirror_type
        else:
            dtype = auto_detect_available_pytorch_type()
        pytorch_info = find_latest_pytorch_info(dtype)
        device_type = pytorch_info["dtype"]
        mirrors["index_url"] = pytorch_info["index_mirror"]["mirror"] if use_cn_mirror else pytorch_info["index_mirror"]["official"]
        mirrors["extra_index_url"] = pytorch_info["extra_index_mirror"]["mirror"] if use_cn_mirror else pytorch_info["extra_index_mirror"]["official"]
        mirrors["find_links"] = pytorch_info["find_links"]["mirror"] if use_cn_mirror else pytorch_info["find_links"]["official"]
        torch_ver = pytorch_info["torch_ver"]
        xformers_ver = pytorch_info["xformers_ver"]
    else:
        device_type = None
        torch_part = [x for x in custom_pytorch_package.split() if get_package_name(x) == "torch"]
        torch_ver = custom_pytorch_package
        xformers_ver = custom_xformers_package

    # 配置 PyTorch 镜像源
    if pytorch_mirror_type is not None:
        _update_mirror(pytorch_mirror_type)
    elif torch_part and is_package_has_version(torch_part[0]):
        # 声明了 PyTorch 版本
        if "+" in torch_part[0]:
            # 存在类型声明
            _update_mirror(cast(PyTorchDeviceType, torch_part[0].split("+")[-1]))
        else:
            # 不存在类型声明时
            mirror_device_type: PyTorchDeviceTypeCategory = auto_detect_pytorch_device_category() if device_type is None else cast(PyTorchDeviceTypeCategory, device_type)
            _update_mirror(
                get_pytorch_mirror_type(
                    torch_ver=get_package_version(torch_part[0]),
                    device_type=mirror_device_type,
                )
            )
    else:
        _update_mirror(auto_detect_available_pytorch_type())

    custom_env = generate_uv_and_pip_env_mirror_config(
        index_url=mirrors["index_url"],
        extra_index_url=mirrors["extra_index_url"],
        find_links=mirrors["find_links"],
    )

    return (torch_ver, xformers_ver, custom_env)


def install_pytorch_for_webui(
    pytorch_package: str | None = None,
    xformers_package: str | None = None,
    custom_env: dict[str, str] | None = None,
    use_uv: bool = True,
) -> None:
    """为 WebUI 环境安装 PyTorch

    Args:
        pytorch_package: (str | None):
            PyTorch 包版本声明
        xformers_package (str | None):
            xFormers 包版本声明
        custom_env (dict[str, str] | None):
            环境变量字典, 用于设置安装 PyTorch 时使用的 PyTorch 镜像源
        use_uv (bool):
            是否使用 uv 进行 PyTorch 安装
    """
    logger.info("检查 PyTorch / xFormers 是否需要安装")
    need_install_pytorch = False
    need_install_xformers = False
    if pytorch_package is not None:
        try:
            importlib.metadata.version("torch")
        except Exception:
            need_install_pytorch = True

    if xformers_package is not None:
        try:
            importlib.metadata.version("xformers")
        except Exception:
            need_install_xformers = True

    if not need_install_pytorch and not need_install_xformers:
        logger.info("PyTorch / xFormers 已安装")
        return

    install_pytorch_with_fallback(
        torch_package=pytorch_package,
        xformers_package=xformers_package,
        custom_env=custom_env,
        use_uv=use_uv,
    )

    logger.info("PyTorch / xFormers 安装完成")


def reinstall_pytorch(
    pytorch_name: str | None = None,
    pytorch_index: int | None = None,
    use_pypi_mirror: bool = True,
    use_uv: bool = True,
    interactive_mode: bool = False,
    list_only: bool = False,
    force_reinstall: bool = False,
) -> None:
    """PyTorch 重装工具

    Args:
        pytorch_name (str | None):
            PyTorch 版本组合名称
        pytorch_index (int | None):
            PyTorch 版本组合索引值
        use_pypi_mirror (bool):
            是否使用 PyPI 国内镜像
        use_uv (bool):
            是否使用 uv 进行 PyTorch 安装
        interactive_mode (bool):
            是否启用交互模式
        list_only (bool):
            是否仅列出 PyTorch 列表并退出
        force_reinstall (bool):
            是否强制重装 PyTorch
    """

    def _install(
        input_name: str | None = None,
        input_index: int | None = None,
    ) -> None:
        info = query_pytorch_info_from_library(
            pytorch_name=input_name,
            pytorch_index=input_index,
        )
        custom_env = generate_uv_and_pip_env_mirror_config(
            index_url=info["index_mirror"]["mirror"] if use_pypi_mirror else info["index_mirror"]["official"],
            extra_index_url=info["extra_index_mirror"]["mirror"] if use_pypi_mirror else info["extra_index_mirror"]["official"],
            find_links=info["find_links"]["mirror"] if use_pypi_mirror else info["find_links"]["official"],
        )
        logger.info("安装 PyTorch 中")
        _uninstall()
        install_pytorch_with_fallback(
            torch_package=info["torch_ver"],
            xformers_package=info["xformers_ver"],
            custom_env=custom_env,
            use_uv=use_uv,
        )

    def _uninstall() -> None:
        if enable_force_reinstall:
            run_cmd([Path(sys.executable).as_posix(), "-m", "pip", "uninstall", "torch", "torchvision", "torchaudio", "xformers", "-y"])

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

    pytorch_list = export_pytorch_list()

    if list_only:
        print_divider("=")
        display_pytorch_config(pytorch_list)
        print_divider("=")
        return

    display_model = True
    input_err = (0, None)
    enable_force_reinstall = force_reinstall
    if interactive_mode:
        while True:
            if display_model:
                print_divider("=")
                display_pytorch_config(pytorch_list)
                print_divider("=")

            display_model = True
            enable_force_reinstall = False
            i, m = input_err
            if i == 1:
                logger.warning("输入有误, 请重试")
            elif i == 2:
                logger.warning("输入的数字有误, %s, 请重新输入", m)
            input_err = (0, None)
            torch_ver, xformers_ver = _get_torch_and_xformers_ver()
            print(
                f"当前已安装的 PyTorch 版本: {torch_ver}\n"
                f"当前已安装的 xFormers 版本: {xformers_ver}\n"
                "请选择 PyTorch 版本\n"
                "提示:\n"
                "1. PyTorch 版本通常来说选择最新版的即可\n"
                "2. 驱动支持的最高 CUDA 版本需要大于或等于要安装的 PyTorch 中所带的 CUDA 版本, 若驱动支持的最高 CUDA 版本低于要安装的 PyTorch 中所带的 CUDA 版本, 可尝试更新显卡驱动, 或者选择 CUDA 版本更低的 PyTorch\n"
                "3. 输入数字后回车即可选择安装指定的 PyTorch 版本组合\n"
                "4. 输入 auto 后回车可以自动根据设备支持情况选择最佳 PyTorch 版本组合进行安装\n"
                "5. 输入 exit 后回车退出 PyTorch 重装"
            )
            user_input = input("==> ").strip()

            if user_input == "exit":
                return

            if user_input == "auto":
                if input("是否启用强制重装? [y/N] ").strip().lower() in ["yes", "y"]:
                    enable_force_reinstall = True

                logger.info("自动根据设备支持情况选择最佳 PyTorch 版本组合中")
                pytorch, xformers, custom_env = prepare_pytorch_install_info(use_cn_mirror=use_pypi_mirror)
                logger.info("安装 PyTorch 中")
                _uninstall()
                install_pytorch_with_fallback(
                    torch_package=pytorch,
                    xformers_package=xformers,
                    custom_env=custom_env,
                    use_uv=use_uv,
                )
                return

            try:
                index = int(user_input)
            except Exception:
                input_err = (1, None)
                continue

            try:
                if input("是否启用强制重装? [y/N] ").strip().lower() in ["yes", "y"]:
                    enable_force_reinstall = True

                _install(input_index=index)
                return
            except ValueError as e:
                input_err = (1, str(e))
                continue

    else:
        _install(
            input_name=pytorch_name,
            input_index=pytorch_index,
        )


def install_pytorch_with_fallback(
    torch_package: str | list[str] | None = None,
    xformers_package: str | list[str] | None = None,
    custom_env: dict[str, str] | None = None,
    use_uv: bool = True,
) -> None:
    """使用 Pip / uv 安装 PyTorch 和 Xformers, 当失败时尝试使用回退方式安装 PyTorch

    Args:
        torch_package (str | list[str] | None):
            PyTorch 软件包名称
        xformers_package (str | list[str] | None):
            Xformers 软件包名称
        custom_env (dict[str, str] | None):
            自定义环境变量
        use_uv (bool):
            是否使用 uv

    Raises:
        RuntimeError:
            安装 PyTorch / xFormers 或使用回退方式安装时发生错误
    """

    def _package_to_list(
        package: str | list[str] | None,
    ) -> list[str] | None:
        if package is None:
            return None
        if isinstance(package, str):
            return package.split()
        return package.copy()

    def _append_no_deps(
        package: list[str] | None,
    ) -> list[str] | None:
        if package is None:
            return None
        package_with_no_deps = package.copy()
        if "--no-deps" not in package_with_no_deps:
            package_with_no_deps.append("--no-deps")
        return package_with_no_deps

    def _dedupe_mirror_values(
        values: list[str],
    ) -> list[str]:
        deduped_values: list[str] = []
        for value in values:
            if value not in deduped_values:
                deduped_values.append(value)
        return deduped_values

    def _get_mirror_values(
        env: dict[str, str] | None,
        env_names: tuple[str, ...],
        split_comma: bool = False,
    ) -> list[str]:
        if env is None:
            return []

        mirror_values: list[str] = []
        for env_name in env_names:
            mirror_value = env.get(env_name)
            if mirror_value is None:
                continue

            if split_comma:
                mirror_value = mirror_value.replace(",", " ")

            mirror_values.extend([x.strip() for x in mirror_value.split() if x.strip() != ""])

        return _dedupe_mirror_values(mirror_values)

    def _get_first_mirror_value(
        env: dict[str, str] | None,
        env_names: tuple[str, ...],
    ) -> str | None:
        mirror_values = _get_mirror_values(env=env, env_names=env_names)
        if len(mirror_values) == 0:
            return None
        return mirror_values[0]

    def _build_merged_pypi_mirror_env(
        auto_pypi_mirror_env: dict[str, str] | None,
    ) -> dict[str, str]:
        if auto_pypi_mirror_env is None:
            auto_pypi_mirror_env = get_auto_pypi_mirror_config(custom_env=custom_env)

        custom_extra_index_url = _get_mirror_values(custom_env, ("PIP_EXTRA_INDEX_URL", "UV_INDEX"))
        auto_extra_index_url = _get_mirror_values(auto_pypi_mirror_env, ("PIP_EXTRA_INDEX_URL", "UV_INDEX"))
        extra_index_url = _dedupe_mirror_values(custom_extra_index_url + auto_extra_index_url)

        custom_find_links = _get_mirror_values(custom_env, ("PIP_FIND_LINKS", "UV_FIND_LINKS"), split_comma=True)
        auto_find_links = _get_mirror_values(auto_pypi_mirror_env, ("PIP_FIND_LINKS", "UV_FIND_LINKS"), split_comma=True)
        find_links = _dedupe_mirror_values(custom_find_links + auto_find_links)

        index_url = _get_first_mirror_value(custom_env, ("PIP_INDEX_URL", "UV_DEFAULT_INDEX"))
        if index_url is None:
            index_url = _get_first_mirror_value(auto_pypi_mirror_env, ("PIP_INDEX_URL", "UV_DEFAULT_INDEX"))
        if index_url is None and len(custom_extra_index_url) > 0:
            index_url = custom_extra_index_url[0]
        if index_url is None:
            index_url = ""

        return generate_uv_and_pip_env_mirror_config(
            index_url=index_url,
            extra_index_url=extra_index_url,
            find_links=find_links,
            origin_env=custom_env,
        )

    try:
        install_pytorch(
            torch_package=torch_package,
            xformers_package=xformers_package,
            custom_env=custom_env,
            use_uv=use_uv,
        )
    except RuntimeError:
        logger.warning("安装 PyTorch 时发生错误, 尝试使用回退方式安装 PyTorch")
        origin_torch_package = _package_to_list(torch_package)
        origin_xformers_package = _package_to_list(xformers_package)
        fallback_torch_package = _append_no_deps(origin_torch_package)
        fallback_xformers_package = _append_no_deps(origin_xformers_package)
        auto_pypi_mirror_env: dict[str, str] | None = None
        try:
            install_pytorch(
                torch_package=fallback_torch_package,
                xformers_package=fallback_xformers_package,
                custom_env=custom_env,
                use_uv=use_uv,
            )
            auto_pypi_mirror_env = get_auto_pypi_mirror_config(custom_env=custom_env)
            install_pytorch(
                torch_package=origin_torch_package,
                xformers_package=origin_xformers_package,
                custom_env=auto_pypi_mirror_env,
                use_uv=use_uv,
            )
        except RuntimeError as fallback_error:
            logger.warning("使用回退方式安装 PyTorch 时发生错误, 尝试合并镜像源后安装 PyTorch")
            try:
                install_pytorch(
                    torch_package=origin_torch_package,
                    xformers_package=origin_xformers_package,
                    custom_env=_build_merged_pypi_mirror_env(auto_pypi_mirror_env=auto_pypi_mirror_env),
                    use_uv=use_uv,
                )
            except RuntimeError as merged_mirror_error:
                raise RuntimeError(f"使用回退方式安装 PyTorch 时发生错误: {fallback_error}; 使用合并镜像源安装 PyTorch 时发生错误: {merged_mirror_error}") from merged_mirror_error
