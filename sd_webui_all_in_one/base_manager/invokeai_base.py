import importlib.metadata
import os
import asyncio
import re
import sys
from tempfile import TemporaryDirectory
from typing import Any, Callable, TypedDict
from pathlib import Path


from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    apply_hf_mirror,
    clone_repo,
    get_repo_name_from_url,
    install_webui_model_from_library,
    pre_download_model_for_webui,
    prepare_pytorch_install_info,
)
from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.downloader import DownloadToolType, download_file
from sd_webui_all_in_one.env_check.fix_numpy import check_numpy
from sd_webui_all_in_one.env_check.fix_torch import fix_torch_libomp
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check import check_onnxruntime_gpu
from sd_webui_all_in_one.file_operations.file_manager import copy_files, move_files, remove_files
from sd_webui_all_in_one.mirror_manager import GITHUB_MIRROR_LIST, HUGGINGFACE_MIRROR_LIST, get_pypi_mirror_config
from sd_webui_all_in_one.model_downloader.base import ModelDownloadUrlType
from sd_webui_all_in_one.optimize.cuda_malloc import get_cuda_malloc_var
from sd_webui_all_in_one.pkg_manager import install_pytorch, pip_install
from sd_webui_all_in_one.package_analyzer.pkg_check import get_package_name, get_package_version, is_package_has_version
from sd_webui_all_in_one.package_analyzer.ver_cmp import version_decrement, version_increment
from sd_webui_all_in_one.pytorch_manager.base import PYTORCH_DEVICE_CATEGORY_LIST, PyTorchDeviceTypeCategory
from sd_webui_all_in_one.pytorch_manager.pytorch_mirror import get_env_pytorch_type, get_pytorch_mirror_type, auto_detect_pytorch_device_category
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.utils import print_divider, ANSIColor

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def get_invokeai_require_torch_version() -> str:
    """获取 InvokeAI 依赖的 PyTorch 版本

    Returns:
        str:
            PyTorch 版本
    """
    try:
        invokeai_requires = importlib.metadata.requires("invokeai")
    except Exception:
        return "2.2.2"

    torch_version = "torch==2.2.2"

    for require in invokeai_requires:
        if get_package_name(require) == "torch" and is_package_has_version(require):
            torch_version = require.split(";")[0]
            break

    if torch_version.startswith("torch>") and not torch_version.startswith("torch>="):
        return version_increment(get_package_version(torch_version))
    elif torch_version.startswith("torch<") and not torch_version.startswith("torch<="):
        return version_decrement(get_package_version(torch_version))
    elif torch_version.startswith("torch!="):
        return version_increment(get_package_version(torch_version))
    else:
        return get_package_version(torch_version)


def get_pytorch_mirror_type_for_ivnokeai(
    device_type: PyTorchDeviceTypeCategory,
) -> str:
    """获取 InvokeAI 安装 PyTorch 所需的 PyTorch 镜像源类型

    Args:
        device_type (PyTorchDeviceTypeCategory):
            显卡设备类型

    Returns:
        str:
            PyTorch 镜像源类型
    """
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
        invokeai_requires = importlib.metadata.requires("invokeai")
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
        invokeai_requires = importlib.metadata.requires("invokeai")
    except Exception as _:
        invokeai_requires = []

    for require in invokeai_requires:
        require = require.split(";")[0].strip()
        package_name = get_package_name(require)
        if package_name == "xformers":
            pytorch_ver.append(require)
            break

    return " ".join([str(x).strip() for x in pytorch_ver])


def sync_invokeai_component(
    device_type: PyTorchDeviceTypeCategory | None = None,
    use_pypi_mirror: bool | None = None,
    use_uv: bool | None = True,
) -> None:
    """同步 InvokeAI 组件

    Args:
        device_type (PyTorchDeviceTypeCategory | None):
            显卡设备类型
        use_pypi_mirror (bool | None):
            是否使用国内 PyPI 镜像
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包

    Raises:
        RuntimeError:
            同步 InvokeAI 组件发生错误时
    """
    logger.info("获取 InvokeAI 安装配置")

    # 获取 InvokeAI 和 InvokeAI 所需的 PyTorch 的版本
    invokeai_ver = importlib.metadata.version("invokeai")
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
            install_pytorch(
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
                install_pytorch(
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
    upgrade: bool | None = False,
    use_pypi_mirror: bool | None = False,
    use_uv: bool | None = True,
) -> None:
    """安装 InvokeAI

    Args:
        device_type (PyTorchDeviceTypeCategory | None):
            显卡设备类型
        invokeai_version (str | None):
            指定安装 InvokeAI 的版本
        upgrade (bool | None):
            更新 InvokeAI
        use_pypi_mirror (bool | None):
            是否使用国内 PyPI 镜像
        use_uv (bool | None):
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


def import_model_to_invokeai(
    model_list: list[Path],
    install_model_to_local: bool | None = False,
) -> bool:
    """将模型列表导入到 InvokeAI 中

    Args:
        model_list (list[Path]):
            模型路径列表
        install_model_to_local (bool | None):
            是否将模型安装到 InvokeAI 路径中, 为 False 时就地安装, 为 True 时则将模型复制到 InvokeAI 目录中

    Returns:
        bool:
            导入模型成功时

    Raises:
        ImportError:
            导入 InvokeAI 模块发生错误时
        RuntimeError:
            InvokeAI 模型管理服务发生异常时
    """
    try:
        logger.info("导入 InvokeAI 模块中")
        from invokeai.app.services.model_manager.model_manager_default import ModelManagerService
        from invokeai.app.services.model_install.model_install_common import InstallStatus
        from invokeai.app.services.model_records.model_records_sql import ModelRecordServiceSQL
        from invokeai.app.services.download.download_default import DownloadQueueService
        from invokeai.app.services.events.events_fastapievents import FastAPIEventService
        from invokeai.app.services.config.config_default import get_config
        from invokeai.app.services.shared.sqlite.sqlite_util import init_db
        from invokeai.app.services.image_files.image_files_disk import DiskImageFileStorage
        from invokeai.app.services.invoker import Invoker
    except ImportError as e:
        logger.error("导入 InvokeAI 模块失败, 无法自动导入模型: %s", e)
        raise ImportError(f"导入 InvokeAI 模块发生错误: {e}") from e

    def _get_invokeai_model_manager() -> ModelManagerService:
        logger.info("初始化 InvokeAI 模型管理服务中")
        configuration = get_config()
        output_folder = configuration.outputs_path
        configuration.models_path.mkdir(parents=True, exist_ok=True)
        image_files = DiskImageFileStorage(f"{output_folder}/images")
        db = init_db(config=configuration, logger=logger, image_files=image_files)
        event_handler_id = 1234
        loop = asyncio.get_event_loop()
        events = FastAPIEventService(event_handler_id, loop=loop)

        model_manager = ModelManagerService.build_model_manager(
            app_config=configuration,
            model_record_service=ModelRecordServiceSQL(db=db, logger=logger),
            download_queue=DownloadQueueService(app_config=configuration, event_bus=events),
            events=FastAPIEventService(event_handler_id, loop=loop),
        )

        logger.info("初始化 InvokeAI 模型管理服务完成")
        return model_manager

    def _import_model(
        model_manager: ModelManagerService,
        inplace: bool,
        model_path: Path,
    ) -> bool:
        file_name = model_path.name
        try:
            logger.info("导入 %s 模型到 InvokeAI 中", file_name)
            job = model_manager.install.heuristic_import(source=model_path.as_posix(), inplace=inplace)
            result = model_manager.install.wait_for_job(job)
            if result.status == InstallStatus.COMPLETED:
                logger.info("导入 %s 模型到 InvokeAI 成功", file_name)
                return True
            else:
                logger.error("导入 %s 模型到 InvokeAI 时出现了错误: %s", file_name, result.error)
                return False
        except Exception as e:
            logger.error("导入 %s 模型到 InvokeAI 时出现了错误: %s", file_name, e)
            return False

    def _model_exists(
        model_manager: ModelManagerService,
        model_path: Path,
    ) -> bool:
        try:
            # 获取所有已注册的模型记录
            all_models = model_manager.store.all_models()

            # 将待检测路径转换为绝对路径并统一格式
            target_path = model_path.resolve()

            for model_config in all_models:
                # model_config.path 可能是相对于 InvokeAI 根目录的路径, 也可能是绝对路径
                # 需要将其转换为绝对路径进行比对
                config_path = Path(model_config.path)
                if not config_path.is_absolute():
                    config_path = Path(get_config().models_path) / config_path

                if config_path.resolve() == target_path:
                    return True

            return False
        except Exception as e:
            logger.error("检查模型是否存在时发生错误: %s", e)
            return False

    install_result: list[tuple[Path, bool]] = []
    count = 0
    task_sum = len(model_list)

    if task_sum == 0:
        logger.info("无需要导入的模型")
        return

    logger.info("InvokeAI 根目录: %s", os.environ.get("INVOKEAI_ROOT"))

    try:
        model_manager = _get_invokeai_model_manager()
        logger.info("启动 InvokeAI 模型管理服务")
        model_manager.start(Invoker)
    except Exception as e:
        logger.error("启动 InvokeAI 模型管理服务失败, 无法导入模型: %s", e)
        raise RuntimeError(f"启动 InvokeAI 模型管理服务出现错误: {e}") from e

    logger.info("就地安装 (仅本地) 模式: %s", ("禁用" if install_model_to_local else "启用"))

    for model in model_list:
        count += 1
        if _model_exists(model_manager, model):
            logger.info("[%s/%s] 模型 %s 已经存在，跳过导入", count, task_sum, model.name)
            install_result.append((model, True))
            continue

        logger.info("[%s/%s] 添加模型: %s", count, task_sum, model.name)
        result = _import_model(
            model_manager=model_manager,
            inplace=not install_model_to_local,
            model_path=model,
        )
        install_result.append((model, result))

    logger.info("关闭 InvokeAI 模型管理服务")
    try:
        model_manager.stop(Invoker)
    except Exception as e:
        logger.error("关闭 InvokeAI 模型管理服务出现错误: %s", e)
        raise RuntimeError(f"关闭 InvokeAI 模型管理服务出现错误: {e}") from e

    logger.info("导入 InvokeAI 模型结果")
    print_divider("-")
    print(f"{'模型名称':<40} | {'状态':<10}")
    print_divider("-")

    failed_models: list[Path] = []
    for model, success in install_result:
        status_text = "导入成功" if success else "导入失败"
        print(f"- {model.name:<38} | {status_text}")
        if not success:
            failed_models.append(model)
    print_divider("-")

    if failed_models:
        logger.warning("以下模型导入失败：")
        for m in failed_models:
            print(f"- {m.name}: {m}")
        print_divider("-")
        logger.warning("导入失败的模型可尝试通过在 InvokeAI 的模型管理 -> 添加模型 -> 链接和本地路径, 手动输入模型路径并添加")
        return False

    logger.info("所有模型导入结束")
    return True


def install_pypatchmatch(
    use_cn_mirror: bool | None = False,
    downloader: DownloadToolType | None = "aria2",
) -> None:
    """为 Windows 的 PyPatchMatch 安装组件

    Args:
        use_cn_mirror (bool | None):
            是否使用国内下载镜像
        downloader (DownloadToolType):
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
        util = [p for p in importlib.metadata.files("pypatchmatch") if "__init__.py" in str(p)][0]
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


def install_invokeai(
    invokeai_path: Path,
    device_type: PyTorchDeviceTypeCategory | None = None,
    invokeai_version: str | None = None,
    use_pypi_mirror: bool | None = True,
    use_uv: bool | None = True,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
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
        use_github_mirror (bool | None):
            是否启用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        no_pre_download_model (bool | None):
            是否禁用预下载模型
        use_cn_model_mirror (bool | None):
            是否使用国内镜像下载模型
    """
    logger.info("准备 InvokeAI 安装配置")

    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")
    logger.info("开始安装 InvokeAI, 安装路径: %s", invokeai_path)

    with TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        install_invokeai_component(
            device_type=device_type,
            invokeai_version=invokeai_version,
            use_pypi_mirror=use_pypi_mirror,
            use_uv=use_uv,
        )

        install_pypatchmatch(
            use_cn_mirror=use_pypi_mirror,
            downloader="aria2",
        )

        if not no_pre_download_model:
            model_path = invokeai_path / "models" / "checkpoints"
            model_path.mkdir(parents=True, exist_ok=True)
            save_paths = pre_download_model_for_webui(
                dtype="invokeai",
                model_path=invokeai_path / "models" / "checkpoints",
                webui_base_path=invokeai_path,
                model_name="ChenkinNoob-XL-V0.2",
                download_resource_type="modelscope" if use_cn_model_mirror else "huggingface",
            )
            import_model_to_invokeai(model_list=([save_paths] if save_paths is not None else []))

    logger.info("安装 InvokeAI 完成")


def update_invokeai(
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
    logger.info("更新 InvokeAI 中")
    install_invokeai_component(
        device_type=get_env_pytorch_type(),
        upgrade=True,
        use_pypi_mirror=use_pypi_mirror,
        use_uv=use_uv,
    )
    logger.info("更新 InvokeAI 完成")


def check_invokeai_env(
    use_uv: bool | None = True,
    use_pypi_mirror: bool | None = False,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """检查 InvokeAI 运行环境

    Args:
        use_uv (bool | None):
            使用 uv 安装依赖
        use_pypi_mirror (bool | None):
            是否使用国内 PyPI 镜像源
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源

    Raises:
        AggregateError:
            检查 InvokeAI 环境发生错误时
    """
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

    # 准备安装依赖的 PyPI 镜像源
    custom_env = get_pypi_mirror_config(
        use_cn_mirror=use_pypi_mirror,
        origin_env=custom_env,
    )

    # 检查任务列表
    tasks: list[tuple[Callable, dict[str, Any]]] = [
        (fix_torch_libomp, {}),
        (check_onnxruntime_gpu, {"use_uv": use_uv, "skip_if_missing": True, "custom_env": custom_env}),
        (check_numpy, {"use_uv": use_uv, "custom_env": custom_env}),
    ]
    err: list[Exception] = []

    for func, kwargs in tasks:
        try:
            func(**kwargs)
        except Exception as e:
            err.append(e)
            logger.error("执行 '%s' 时发生错误: %s", func.__name__, e)

    if err:
        raise AggregateError("检查 InvokeAI 环境时发生错误", err)

    logger.info("检查 InvokeAI 环境完成")


def launch_invokeai(
    invokeai_path: Path,
    launch_args: list[str] | None = None,
    use_hf_mirror: bool | None = False,
    custom_hf_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool | None = False,
    use_cuda_malloc: bool | None = True,
) -> None:
    """启动 InvokeAI

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        launch_args (list[str] | None):
            启动 InvokeAI 的参数
        use_hf_mirror (bool | None):
            是否启用 HuggingFace 镜像源
        custom_hf_mirror (str | list[str] | None):
            自定义 HuggingFace 镜像源
        use_pypi_mirror (bool | None):
            是否启用 PyPI 镜像源
        use_cuda_malloc (bool | None):
            是否启用 CUDA Malloc 显存优化
    """

    logger.info("准备 InvokeAI 启动环境")
    custom_env = os.environ.copy()
    custom_env["INVOKEAI_ROOT"] = invokeai_path.as_posix()

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
            custom_env["PYTORCH_ALLOC_CONF"] = cuda_malloc_config
            custom_env["PYTORCH_CUDA_ALLOC_CONF"] = cuda_malloc_config

    logger.info("启动 InvokeAI 中")
    from invokeai.app.run_app import run_app

    if launch_args is not None:
        sys.argv = [sys.argv[0]] + launch_args
    sys.argv[0] = re.sub(r"(-script\.pyw|\.exe)?$", "", sys.argv[0])
    try:
        sys.exit(run_app())
    except KeyboardInterrupt:
        logger.info("已退出 InvokeAI")


def install_invokeai_custom_nodes(
    invokeai_path: Path,
    custom_node_url: str | list[str],
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
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

    Raises:
        AggregateError:
            安装 InvokeAI 扩展发生错误时
    """
    urls = [custom_node_url] if isinstance(custom_node_url, str) else custom_node_url

    # 获取已安装扩展列表
    custom_node_list = list_invokeai_custom_nodes(invokeai_path)
    installed_names = {x["name"] for x in custom_node_list}
    err: list[Exception] = []

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

    for url in urls:
        custom_node_name = get_repo_name_from_url(url)
        custom_node_path = invokeai_path / "nodes" / custom_node_name

        if custom_node_name in installed_names or custom_node_path.exists():
            logger.info("'%s' 扩展已安装", custom_node_name)
            continue

        logger.info("安装 '%s' 扩展到 '%s' 中", custom_node_name, custom_node_path)
        try:
            clone_repo(
                repo=url,
                path=custom_node_path,
            )
            logger.info("'%s' 扩展安装成功", custom_node_name)
            installed_names.add(custom_node_name)
        except Exception as e:
            err.append(e)
            logger.error("'%s' 扩展安装失败: %s", custom_node_name, e)

    if err:
        raise AggregateError("安装 InvokeAI 扩展时发生错误", err)

    logger.info("安装 InvokeAI 扩展完成")


def set_invokeai_custom_nodes_status(
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

    Raises:
        FileNotFoundError:
            InvokeAI 扩展未找到时
    """

    custom_node_path = invokeai_path / "nodes"
    custom_nodes_list = [ext.name for ext in custom_node_path.iterdir() if ext.is_dir()]

    if custom_node_name not in custom_nodes_list:
        raise FileNotFoundError(f"'{custom_node_name}' 扩展未找到, 请检查该扩展是否已安装")

    init_py = custom_node_path / custom_node_name / "__init__.py"
    init_bak_py = custom_node_path / custom_node_name / "__init__.py.bak"
    if status:
        if init_bak_py.is_file() and not init_py.is_file():
            move_files(init_bak_py, init_py)
        logger.info("启用 '%s' 扩展成功", custom_node_name)
    else:
        if init_py.is_file():
            move_files(init_py, init_bak_py)
        logger.info("禁用 '%s' 扩展成功", custom_node_name)


class InvokeAILocalExtensionInfo(TypedDict, total=False):
    """InvokeAI 本地扩展信息"""

    name: str
    """InvokeAI 扩展名称"""

    status: bool
    """当前 InvokeAI 扩展是否已经启用"""

    path: Path
    """InvokeAI 本地路径"""

    url: str | None
    """InvokeAI 扩展远程地址"""

    commit: str | None
    """InvokeAI 扩展的提交信息"""

    branch: str | None
    """InvokeAI 扩展的当前分支"""


InvokeAILocalExtensionInfoList = list[InvokeAILocalExtensionInfo]
"""InvokeAI 本地扩展信息"""


def list_invokeai_custom_nodes(
    invokeai_path: Path,
) -> InvokeAILocalExtensionInfoList:
    """获取 InvokeAI 本地扩展列表

    Args:
        invokeai_path (Path):
            InvokeAI 根目录

    Returns:
        InvokeAILocalExtensionInfoList:
            InvokeAI 本地扩展列表
    """
    custom_node_path = invokeai_path / "nodes"
    info_list: InvokeAILocalExtensionInfoList = []

    for ext in custom_node_path.iterdir():
        info: InvokeAILocalExtensionInfo = {}
        if ext.is_file():
            continue

        name = ext.name
        path = ext
        status = (path / "__init__.py").is_file()

        try:
            url = git_warpper.get_current_branch_remote_url(ext)
        except ValueError:
            url = None

        try:
            commit = git_warpper.get_current_commit(ext)
        except ValueError:
            commit = None

        try:
            branch = git_warpper.get_current_branch(ext)
        except ValueError:
            branch = None

        info["name"] = name
        info["status"] = status
        info["path"] = path
        info["url"] = url
        info["commit"] = commit
        info["branch"] = branch
        info_list.append(info)

    return info_list


def update_invokeai_custom_nodes(
    invokeai_path: Path,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 InvokeAI 扩展

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源

    Raises:
        AggregateError:
            检查 InvokeAI 环境发生错误时
    """
    custom_nodes_path = invokeai_path / "nodes"
    err: list[Exception] = []

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

    for ext in custom_nodes_path.iterdir():
        if ext.is_file():
            continue

        logger.info("更新 '%s' 扩展中", ext.name)
        try:
            git_warpper.update(ext)
        except Exception as e:
            err.append(e)
            logger.error("更新 '%s' 扩展时发生错误: %s", ext.name, e)

    if err:
        raise AggregateError("更新 InvokeAI 扩展时发生错误", err)

    logger.info("更新 InvokeAI 扩展完成")


def uninstall_invokeai_custom_node(
    invokeai_path: Path,
    custom_node_name: str,
) -> None:
    """卸载 InvokeAI 扩展

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        custom_node_name (str):
            InvokeAI 扩展名称

    Raises:
        FileNotFoundError:
            要卸载的扩展未找到时
        RuntimeError:
            卸载扩展发生错误时
    """
    custom_nodes_path = invokeai_path / "nodes"
    custom_nodes_list = [ext.name for ext in custom_nodes_path.iterdir() if ext.is_dir()]
    if custom_node_name not in custom_nodes_list:
        raise FileNotFoundError(f"'{custom_node_name}' 扩展未安装")

    try:
        logger.info("卸载 '%s' 扩展中", custom_node_name)
        remove_files(custom_nodes_path / custom_node_name)
        logger.info("卸载 '%s' 扩展完成", custom_node_name)
    except Exception as e:
        logger.info("卸载 '%s' 扩展时发生错误: %s", custom_node_name, e)
        raise RuntimeError(f"卸载 '{custom_node_name}' 扩展时发生错误:{e}") from e


def install_invokeai_model_from_library(
    invokeai_path: Path,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = "aria2",
    interactive_mode: bool | None = False,
    list_only: bool | None = False,
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
        list_only (bool | None):
            是否仅列出模型列表并退出
    """
    paths = install_webui_model_from_library(
        webui_path=invokeai_path,
        dtype="invokeai",
        download_resource_type=download_resource_type,
        model_name=model_name,
        model_index=model_index,
        downloader=downloader,
        interactive_mode=interactive_mode,
        list_only=list_only,
    )
    if paths is None:
        return
    import_model_to_invokeai(model_list=paths)


def install_invokeai_model_from_url(
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
    model_path = sd_webui_path / "models" / model_type
    path = download_file(
        url=model_url,
        path=model_path,
        tool=downloader,
    )
    import_model_to_invokeai(model_list=[path])


class InvokeAILocalModelInfo(TypedDict, total=False):
    """InvokeAI 本地已安装的模型信息"""

    id: str
    """模型的 ID"""

    name: str
    """模型的名称"""

    dtype: Any
    """模型的类型"""

    base: Any
    """模型的基底"""

    path: str
    """模型的安装路径"""

    description: str | None
    """模型的描述信息"""


InvokeAILocalModelInfoList = list[InvokeAILocalModelInfo]
"""InvokeAI 本地已安装的模型信息列表"""


def get_invokeai_model_list() -> InvokeAILocalModelInfoList:
    """获取 InvokeAI 中所有已导入的模型列表

    Returns:
        InvokeAILocalModelInfoList:
            包含模型信息的字典列表
    """
    try:
        logger.info("导入 InvokeAI 模块中")
        from invokeai.app.services.model_manager.model_manager_default import ModelManagerService
        from invokeai.app.services.model_records.model_records_sql import ModelRecordServiceSQL
        from invokeai.app.services.download.download_default import DownloadQueueService
        from invokeai.app.services.events.events_fastapievents import FastAPIEventService
        from invokeai.app.services.config.config_default import get_config
        from invokeai.app.services.shared.sqlite.sqlite_util import init_db
        from invokeai.app.services.image_files.image_files_disk import DiskImageFileStorage
        from invokeai.app.services.invoker import Invoker
    except ImportError as e:
        logger.error("导入 InvokeAI 模块失败: %s", e)
        raise ImportError(f"导入 InvokeAI 模块发生错误: {e}") from e

    def _get_invokeai_model_manager() -> ModelManagerService:
        configuration = get_config()
        image_files = DiskImageFileStorage(f"{configuration.outputs_path}/images")
        db = init_db(config=configuration, logger=logger, image_files=image_files)
        loop = asyncio.get_event_loop()
        events = FastAPIEventService(1234, loop=loop)
        return ModelManagerService.build_model_manager(
            app_config=configuration,
            model_record_service=ModelRecordServiceSQL(db=db, logger=logger),
            download_queue=DownloadQueueService(app_config=configuration, event_bus=events),
            events=events,
        )

    try:
        model_manager = _get_invokeai_model_manager()
        model_manager.start(Invoker)

        # 获取所有模型记录
        all_models = model_manager.store.all_models()

        model_list: InvokeAILocalModelInfoList = []
        for m in all_models:
            model_list.append(
                {
                    "id": m.key,
                    "name": m.name,
                    "type": m.type,
                    "base": m.base,
                    "path": m.path,
                    "description": m.description,
                }
            )

        model_manager.stop(Invoker)
        return model_list
    except Exception as e:
        logger.error("获取模型列表失败: %s", e)
        return []


def list_invokeai_models() -> None:
    """列出 InvokeAI 的模型目录"""
    logger.info("InvokeAI 模型列表")
    model_list = get_invokeai_model_list()
    for m in model_list:
        print(f"- {m['name']}")
        print(f"模型 ID: {m['id']}")
        print(f"安装路径: {m['path']}")
        print("\n")


def uninstall_model_from_invokeai(
    model_identifiers: list[str | Path],
    delete_files: bool = False,
) -> bool:
    """从 InvokeAI 中卸载模型

    Args:
        model_identifiers (list[str | Path]):
            模型 ID (Key) 列表或模型物理路径列表
        delete_files (bool):
            是否同时删除磁盘上的模型文件. 注意: 仅当文件位于 InvokeAI 管理的 models 目录下时才会执行物理删除
    """
    try:
        logger.info("导入 InvokeAI 模块中")
        from invokeai.app.services.model_manager.model_manager_default import ModelManagerService
        from invokeai.app.services.model_records.model_records_sql import ModelRecordServiceSQL
        from invokeai.app.services.download.download_default import DownloadQueueService
        from invokeai.app.services.events.events_fastapievents import FastAPIEventService
        from invokeai.app.services.config.config_default import get_config
        from invokeai.app.services.shared.sqlite.sqlite_util import init_db
        from invokeai.app.services.image_files.image_files_disk import DiskImageFileStorage
        from invokeai.app.services.invoker import Invoker
    except ImportError as e:
        logger.error("导入 InvokeAI 模块失败: %s", e)
        raise ImportError(f"导入 InvokeAI 模块发生错误: {e}") from e

    def _get_invokeai_model_manager() -> ModelManagerService:
        configuration = get_config()
        image_files = DiskImageFileStorage(f"{configuration.outputs_path}/images")
        db = init_db(config=configuration, logger=logger, image_files=image_files)
        loop = asyncio.get_event_loop()
        events = FastAPIEventService(1234, loop=loop)
        return ModelManagerService.build_model_manager(
            app_config=configuration,
            model_record_service=ModelRecordServiceSQL(db=db, logger=logger),
            download_queue=DownloadQueueService(app_config=configuration, event_bus=events),
            events=events,
        )

    def _resolve_to_key(model_manager: ModelManagerService, identifier: str | Path) -> str | None:
        """将路径或 ID 统一解析为模型 Key"""
        if isinstance(identifier, Path) or (isinstance(identifier, str) and os.path.exists(identifier)):
            target_path = Path(identifier).resolve()
            for m in model_manager.store.all_models():
                config_path = Path(m.path)
                if not config_path.is_absolute():
                    config_path = Path(get_config().models_path) / config_path
                if config_path.resolve() == target_path:
                    return m.key
            return None
        return str(identifier)  # 假设已经是 Key

    try:
        model_manager = _get_invokeai_model_manager()
        model_manager.start(Invoker)

        results = []
        for identifier in model_identifiers:
            key = _resolve_to_key(model_manager, identifier)
            if not key:
                logger.warning("未找到模型: %s", identifier)
                results.append(False)
                continue

            try:
                if delete_files:
                    # 删除记录并尝试删除物理文件
                    model_manager.install.delete(key)
                else:
                    # 仅注销记录，保留物理文件
                    model_manager.install.unregister(key)
                logger.info("成功卸载模型: %s", identifier)
                results.append(True)
            except Exception as e:
                logger.error("卸载模型 %s 失败: %s", identifier, e)
                results.append(False)

        model_manager.stop(Invoker)
        return all(results) if results else True
    except Exception as e:
        logger.error("卸载服务失败: %s", e)
        return False


def uninstall_invokeai_model(
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

    Raises:
        FileNotFoundError:
            未找到要删除的模型时
    """

    model_list = get_invokeai_model_list()
    delete_list = [x for x in model_list if model_name.lower() in x["name"].lower()]

    if not delete_list:
        raise FileNotFoundError(f"模型 '{model_name}' 不存在")

    logger.info("根据 '%s' 模型名找到的已有模型列表:\n", model_name)
    for d in delete_list:
        print(f"- `{d}`")

    print()
    if interactive_mode:
        logger.info("是否删除以上模型?")
        if input("[y/N]").strip().lower() not in ["yes", "y"]:
            logger.info("取消模型删除操作")
            return

    logger.info("删除模型: %s", ", ".join(delete_list))
    uninstall_model_from_invokeai(
        model_identifiers=[x["id"] for x in model_list if x["name"].lower() in delete_list],
        delete_files=True,
    )

    logger.info("模型删除完成")


def reinstall_invokeai_pytorch(
    device_type: PyTorchDeviceTypeCategory | None = None,
    use_pypi_mirror: bool | None = True,
    use_uv: bool | None = None,
    interactive_mode: bool | None = False,
    list_only: bool | None = False,
) -> None:
    """PyTorch 重装工具

    Args:
        pytorch_name (str | None):
            PyTorch 版本组合名称
        pytorch_index (device_type | None):
            PyTorch 版本组合索引值
        use_pypi_mirror (bool | None):
            是否使用 PyPI 国内镜像
        use_uv (bool | None):
            是否使用 uv 进行 PyTorch 安装
        interactive_mode (bool | None):
            是否启用交互模式
        list_only (bool | None):
            是否仅列出 PyTorch 列表并退出
    """

    def _uninstall() -> None:
        run_cmd([Path(sys.executable), "-m", "pip", "uninstall", "torch", "torchvision", "torchaudio", "xformers", "-y"])

    def _install(d: PyTorchDeviceTypeCategory) -> None:
        install_invokeai_component(
            device_type=d,
            use_pypi_mirror=use_pypi_mirror,
            use_uv=use_uv,
        )

    if list_only:
        print("".join([f"- {i}. {d}" for i, d in enumerate(PYTORCH_DEVICE_CATEGORY_LIST + ["auto"], start=1)]))
        return

    has_err = False

    if interactive_mode:
        while True:
            print_divider("=")
            print(
                "\n".join(
                    [f"- {ANSIColor.GOLD}{i}{ANSIColor.RESET}. {ANSIColor.WHITE}{d}{ANSIColor.RESET}" for i, d in enumerate(PYTORCH_DEVICE_CATEGORY_LIST + ["auto"], start=1)]
                )
            )
            print_divider("=")
            if has_err:
                logger.warning("输入有误, 请重试")
            has_err = False
            print(
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
                _install(user_input)
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
