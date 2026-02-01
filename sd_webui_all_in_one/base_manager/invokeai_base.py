import importlib.metadata
import os
import asyncio
from typing import Literal
from pathlib import Path


from sd_webui_all_in_one.env_check.fix_numpy import check_numpy
from sd_webui_all_in_one.env_check.fix_torch import fix_torch_libomp
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check import check_onnxruntime_gpu
from sd_webui_all_in_one.pkg_manager import install_pytorch, pip_install
from sd_webui_all_in_one.package_analyzer.pkg_check import get_package_name, get_package_version, is_package_has_version
from sd_webui_all_in_one.package_analyzer.ver_cmp import version_decrement, version_increment
from sd_webui_all_in_one.pytorch_manager.pytorch_mirror import get_pytorch_mirror_dict, get_pytorch_mirror_type
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL
from sd_webui_all_in_one.logger import get_logger

logger = get_logger(
    name="InvokeAI Base Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)




class InvokeAIComponentManager:
    """InvokeAI 组件管理器

    Attributes:
        pytorch_mirror_dict (dict[str, str] | None): PyTorch 镜像源字典, 需包含不同镜像源类型对应的镜像地址
    """

    def __init__(
        self,
        pytorch_mirror_dict: dict[str, str] = None,
    ) -> None:
        """InvokeAI 组件管理器初始化

        Args:
            pytorch_mirror_dict (dict[str, str] | None): PyTorch 镜像源字典, 需包含不同镜像源类型对应的镜像地址
        """
        if pytorch_mirror_dict is None:
            pytorch_mirror_dict = get_pytorch_mirror_dict()
        self.pytorch_mirror_dict = pytorch_mirror_dict

    def update_pytorch_mirror_dict(
        self,
        pytorch_mirror_dict: dict[str, str],
    ) -> None:
        """更新 PyTorch 镜像源字典

        Args:
            pytorch_mirror_dict (dict[str, str]): PyTorch 镜像源字典, 需包含不同镜像源类型对应的镜像地址
        """
        logger.info("更新 PyTorch 镜像源信息")
        self.pytorch_mirror_dict = pytorch_mirror_dict

    def get_pytorch_mirror_url(
        self,
        mirror_type: str,
    ) -> str | None:
        """获取 PyTorch 类型对应的镜像源

        Args:
            mirror_type (str): PyTorch 类型
        Returns:
            (str | None): 对应的 PyTorch 镜像源
        """
        return self.pytorch_mirror_dict.get(mirror_type)

    def get_invokeai_require_torch_version(
        self,
    ) -> str:
        """获取 InvokeAI 依赖的 PyTorch 版本

        Returns:
            str: PyTorch 版本
        """
        try:
            invokeai_requires = importlib.metadata.requires("invokeai")
        except Exception as _:
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
        self,
        device_type: Literal["cuda", "rocm", "xpu", "cpu"],
    ) -> str:
        """获取 InvokeAI 安装 PyTorch 所需的 PyTorch 镜像源类型

        Args:
            device_type (Literal["cuda", "rocm", "xpu", "cpu"]): 显卡设备类型
        Returns:
            str: PyTorch 镜像源类型
        """
        torch_ver = self.get_invokeai_require_torch_version()
        return get_pytorch_mirror_type(torch_ver=torch_ver, device_type=device_type)

    def get_pytorch_for_invokeai(
        self,
    ) -> str:
        """获取 InvokeAI 所依赖的 PyTorch 包版本声明

        Returns:
            str: PyTorch 包版本声明
        """
        pytorch_ver = []
        try:
            invokeai_requires = importlib.metadata.requires("invokeai")
        except Exception as _:
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

    def get_xformers_for_invokeai(
        self,
    ) -> str:
        """获取 InvokeAI 所依赖的 xFormers 包版本声明

        Returns:
            str: xFormers 包版本声明
        """
        pytorch_ver = []
        try:
            invokeai_requires = importlib.metadata.requires("invokeai")
        except Exception as _:
            invokeai_requires = []

        xformers_added = False

        for require in invokeai_requires:
            require = require.split(";")[0].strip()
            package_name = get_package_name(require)

            if package_name == "xformers" and not xformers_added:
                pytorch_ver.append(require)
                xformers_added = True

        return " ".join([str(x).strip() for x in pytorch_ver])

    def sync_invokeai_component(
        self,
        device_type: str,
        use_uv: bool | None = True,
    ) -> None:
        """同步 InvokeAI 组件

        Args:
            device_type (str): 显卡设备类型
            use_uv (bool | None): 是否使用 uv 安装 Python 软件包
        Returns:
            bool: 同步组件结果
        """
        logger.info("获取安装配置")
        invokeai_ver = importlib.metadata.version("invokeai")
        torch_ver = self.get_invokeai_require_torch_version()
        pytorch_mirror_type = get_pytorch_mirror_type(
            torch_ver=torch_ver,
            device_type=device_type,
        )
        pytorch_mirror = self.get_pytorch_mirror_url(pytorch_mirror_type)
        pytorch_package = self.get_pytorch_for_invokeai()
        xformers_package = self.get_xformers_for_invokeai()
        logger.debug("InvokeAI 所需的 PyTorch 版本: %s", torch_ver)
        logger.debug("InvokeAI 使用的 PyTorch 镜像源类型: %s", pytorch_mirror_type)
        logger.debug("PyTorch 镜像源: %s", pytorch_mirror)
        logger.debug("安装的 PyTorch: %s", pytorch_package)
        logger.debug("安装的 xFormers: %s", xformers_package)
        pytorch_package_args = []
        if pytorch_mirror_type in ["cpu", "xpu", "ipex_legacy_arc", "rocm6.2", "other"]:
            for i in pytorch_package.split():
                pytorch_package_args.append(i.strip())
        else:
            for i in pytorch_package.split():
                pytorch_package_args.append(i.strip())
            for i in xformers_package.split():
                pytorch_package_args.append(i.strip())

        try:
            logger.info("同步 PyTorch 组件中")
            if pytorch_mirror is not None:
                install_pytorch(
                    torch_package=pytorch_package_args,
                    custom_env=pytorch_mirror,
                    use_uv=use_uv,
                )
            else:
                install_pytorch(
                    torch_package=pytorch_package_args,
                    use_uv=use_uv,
                )
            logger.info("同步 InvokeAI 其他组件中")
            pip_install(f"invokeai=={invokeai_ver}", use_uv=use_uv)
            logger.info("同步 InvokeAI 组件完成")
            return True
        except RuntimeError as e:
            logger.error("同步 InvokeAI 组件时发生了错误: %s", e)
            return False

    def install_invokeai(
        self,
        device_type: str,
        upgrade: bool | None = False,
        use_uv: bool | None = True,
    ) -> None:
        """安装 InvokeAI

        Args:
            device_type (str): 显卡设备类型
            upgrade (bool | None): 更新 InvokeAI
            use_uv (bool | None): 是否使用 uv 安装 Python 软件包
        """
        logger.info("安装 InvokeAI 核心中")
        try:
            if upgrade:
                pip_install("invokeai", "--no-deps", "--upgrade", use_uv=use_uv)
            else:
                pip_install("invokeai", "--no-deps", use_uv=use_uv)

            self.sync_invokeai_component(
                device_type=device_type,
                use_uv=use_uv,
            )
        except Exception as e:
            logger.error("安装 InvokeAI 失败: %s", e)


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
    print("-" * 70)
    print(f"{'模型名称':<40} | {'状态':<10}")
    print("-" * 70)

    failed_models: list[Path] = []
    for model, success in install_result:
        status_text = "导入成功" if success else "导入失败"
        print(f"- {model.name:<38} | {status_text}")
        if not success:
            failed_models.append(model)
    print("-" * 70)

    if failed_models:
        logger.warning("以下模型导入失败：")
        for m in failed_models:
            print(f"- {m.name}: {m}")
        print("-" * 70)
        logger.warning("导入失败的模型可尝试通过在 InvokeAI 的模型管理 -> 添加模型 -> 链接和本地路径, 手动输入模型路径并添加")
        return False

    logger.info("所有模型导入结束")
    return True


def check_invokeai_env(
    use_uv: bool | None = True,
) -> None:
    """检查 InvokeAI 运行环境

    Args:
        use_uv (bool | None): 使用 uv 安装依赖
    """
    fix_torch_libomp()
    check_onnxruntime_gpu(use_uv=use_uv, skip_if_missing=True)
    check_numpy(use_uv=use_uv)
