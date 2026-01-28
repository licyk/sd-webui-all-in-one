"""InvokeAI 管理工具"""

import os
import importlib.metadata
from pathlib import Path
from typing import Literal

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.manager.base_manager import BaseManager
from sd_webui_all_in_one.mirror_manager import set_mirror
from sd_webui_all_in_one.file_manager import get_file_list
from sd_webui_all_in_one.env_check.fix_torch import fix_torch_libomp
from sd_webui_all_in_one.env_check.fix_numpy import check_numpy
from sd_webui_all_in_one.utils import warning_unexpected_params
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL
from sd_webui_all_in_one.optimize.cuda_malloc import set_cuda_malloc
from sd_webui_all_in_one.env import configure_env_var, configure_pip
from sd_webui_all_in_one.colab_tools import is_colab_environment, mount_google_drive
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check import check_onnxruntime_gpu
from sd_webui_all_in_one.package_analyzer.ver_cmp import version_decrement, version_increment
from sd_webui_all_in_one.pytorch_manager.pytorch_mirror import get_pytorch_mirror_dict, get_pytorch_mirror_type
from sd_webui_all_in_one.env_manager import install_manager_depend, install_pytorch, pip_install
from sd_webui_all_in_one.package_analyzer.pkg_check import get_package_name, get_package_version, is_package_has_version


logger = get_logger(
    name="InvokeAI Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class InvokeAIComponentManager:
    """InvokeAI 组件管理器

    Attributes:
        pytorch_mirror_dict (dict[str, str] | None): PyTorch 镜像源字典, 需包含不同镜像源类型对应的镜像地址
    """

    def __init__(self, pytorch_mirror_dict: dict[str, str] = None) -> None:
        """InvokeAI 组件管理器初始化

        Args:
            pytorch_mirror_dict (dict[str, str] | None): PyTorch 镜像源字典, 需包含不同镜像源类型对应的镜像地址
        """
        if pytorch_mirror_dict is None:
            pytorch_mirror_dict = get_pytorch_mirror_dict()
        self.pytorch_mirror_dict = pytorch_mirror_dict

    def update_pytorch_mirror_dict(self, pytorch_mirror_dict: dict[str, str]) -> None:
        """更新 PyTorch 镜像源字典

        Args:
            pytorch_mirror_dict (dict[str, str]): PyTorch 镜像源字典, 需包含不同镜像源类型对应的镜像地址
        """
        logger.info("更新 PyTorch 镜像源信息")
        self.pytorch_mirror_dict = pytorch_mirror_dict

    def get_pytorch_mirror_url(self, mirror_type: str) -> str | None:
        """获取 PyTorch 类型对应的镜像源

        Args:
            mirror_type (str): PyTorch 类型
        Returns:
            (str | None): 对应的 PyTorch 镜像源
        """
        return self.pytorch_mirror_dict.get(mirror_type)

    def get_invokeai_require_torch_version(self) -> str:
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

    def get_pytorch_for_invokeai(self) -> str:
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

    def get_xformers_for_invokeai(self) -> str:
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
        if pytorch_mirror_type in ["cpu", "xpu", "ipex_legacy_arc", "rocm62", "other"]:
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
                    pytorch_mirror=pytorch_mirror,
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
        except Exception as e:
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


class InvokeAIManager(BaseManager):
    """InvokeAI 管理模块

    Attributes:
        component (InvokeAIComponentManager): InvokeAI 组件管理器
    """

    def __init__(
        self,
        workspace: str | Path,
        workfolder: str,
        hf_token: str | None = None,
        ms_token: str | None = None,
        port: int | None = 9090,
    ) -> None:
        """管理工具初始化

        Args:
            workspace (str | Path): 工作区路径
            workfolder (str): 工作区的文件夹名称
            hf_token (str | None): HuggingFace Token
            ms_token (str | None): ModelScope Token
            port (int | None): 内网穿透端口
        """
        super().__init__(
            workspace=workspace,
            workfolder=workfolder,
            hf_token=hf_token,
            ms_token=ms_token,
            port=port,
        )
        self.component = InvokeAIComponentManager()

    def mount_drive(self) -> None:
        """挂载 Google Drive 并创建 InvokeAI 输出文件夹, 并设置 INVOKEAI_ROOT 环境变量指定 InvokeAI 输出目录

        Raises:
            RuntimeError: 挂载 Google Drive 失败
        """
        if not is_colab_environment():
            logger.warning("当前环境非 Colab, 无法挂载 Google Drive")
            return

        drive_path = Path("/content/drive")
        if not (drive_path / "MyDrive").exists():
            if not mount_google_drive(drive_path):
                raise RuntimeError("挂载 Google Drive 失败, 请尝试重新挂载 Google Drive")

        invokeai_output = drive_path / "MyDrive" / "invokeai_output"
        invokeai_output.mkdir(parents=True, exist_ok=True)
        os.environ["INVOKEAI_ROOT"] = invokeai_output.as_posix()

    def import_model_to_invokeai(
        self,
        model_list: list[str],
    ) -> None:
        """将模型列表导入到 InvokeAI 中

        Args:
            model_list (list[str]): 模型路径列表
        """
        try:
            logger.info("导入 InvokeAI 模块中")
            import asyncio
            from invokeai.app.services.model_manager.model_manager_default import (
                ModelManagerService,
            )
            from invokeai.app.services.model_install.model_install_common import (
                InstallStatus,
            )
            from invokeai.app.services.model_records.model_records_sql import (
                ModelRecordServiceSQL,
            )
            from invokeai.app.services.download.download_default import (
                DownloadQueueService,
            )
            from invokeai.app.services.events.events_fastapievents import (
                FastAPIEventService,
            )
            from invokeai.app.services.config.config_default import get_config
            from invokeai.app.services.shared.sqlite.sqlite_util import init_db
            from invokeai.app.services.image_files.image_files_disk import (
                DiskImageFileStorage,
            )
            from invokeai.app.services.invoker import Invoker
        except Exception as e:
            logger.error("导入 InvokeAI 模块失败, 无法自动导入模型: %s", e)
            return

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

        def _import_model(model_manager: ModelManagerService, inplace: bool, model_path: str | Path) -> bool:
            model_path = Path(model_path)
            file_name = model_path.name
            try:
                logger.info("导入 %s 模型到 InvokeAI 中", file_name)
                job = model_manager.install.heuristic_import(source=model_path.as_posix(), inplace=inplace)
                result = model_manager.install.wait_for_job(job)
                if result.status == InstallStatus.COMPLETED:
                    logger.info("导入 %s 模型到 InvokeAI 成功", file_name)
                    return True
                else:
                    logger.error(
                        "导入 %s 模型到 InvokeAI 时出现了错误: %s",
                        file_name,
                        result.error,
                    )
                    return False
            except Exception as e:
                logger.error("导入 %s 模型到 InvokeAI 时出现了错误: %s", file_name, e)
                return False

        install_model_to_local = False
        install_result = []
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
            return
        logger.info("就地安装 (仅本地) 模式: %s", ("禁用" if install_model_to_local else "启用"))
        for model in model_list:
            count += 1
            file_name = os.path.basename(model)
            logger.info("[%s/%s] 添加模型: %s", count, task_sum, file_name)
            result = _import_model(
                model_manager=model_manager,
                inplace=not install_model_to_local,
                model_path=model,
            )
            install_result.append([model, file_name, result])
        logger.info("关闭 InvokeAI 模型管理服务")
        try:
            model_manager.stop(Invoker)
        except Exception as e:
            logger.error("关闭 InvokeAI 模型管理服务出现错误: %s", e)
        logger.info("导入 InvokeAI 模型结果")
        print("-" * 70)
        for _, file, status in install_result:
            status = "导入成功" if status else "导入失败"
            print(f"- {file}: {status}")

        print("-" * 70)
        has_failed = False
        for _, _, x in install_result:
            if not x:
                has_failed = True
                break

        if has_failed:
            logger.warning("导入失败的模型列表和模型路径")
            print("-" * 70)
            for model, file_name, status in install_result:
                if not status:
                    print(f"- {file_name}: {model}")
            print("-" * 70)
            logger.warning("导入失败的模型可尝试通过在 InvokeAI 的模型管理 -> 添加模型 -> 链接和本地路径, 手动输入模型路径并添加")

        logger.info("导入模型结束")

    def import_model(self) -> None:
        """导入模型到 InvokeAI 中"""
        model_path = self.workspace / self.workfolder / "sd-models"
        model_list = get_file_list(model_path)
        try:
            self.mount_drive()
        except Exception as e:
            logger.error("挂载 Google Drive 失败, 无法导入模型: %s", e)
            return
        self.import_model_to_invokeai(model_list)

    def get_sd_model(
        self,
        url: str,
        filename: str = None,
    ) -> Path | None:
        """下载模型

        Args:
            url (str): 模型的下载链接
            filename (str | None): 模型下载后保存的名称
            model_type (str | None): 模型的类型
        Returns:
            (Path | None): 模型保存路径
        """
        path = self.workspace / self.workfolder / "sd-models"
        return self.get_model(url=url, path=path, filename=filename, tool="aria2")

    def get_sd_model_from_list(
        self,
        model_list: list[str],
        retry: int | None = 3,
    ) -> None:
        """从模型列表下载模型

        Args:
            model_list (list[str]): 模型列表
            retry (int | None): 重试下载的次数, 默认为 3
        """
        new_model_list = [[model, 1] for model in model_list]
        self.get_model_from_list(
            path=self.workspace / self.workfolder / "sd-models",
            model_list=new_model_list,
            retry=retry,
        )

    def check_env(
        self,
        use_uv: bool | None = True,
    ) -> None:
        """检查 InvokeAI 运行环境

        Args:
            use_uv (bool | None): 使用 uv 安装依赖
        """
        fix_torch_libomp()
        check_onnxruntime_gpu(use_uv=use_uv, ignore_ort_install=True)
        check_numpy(use_uv=use_uv)

    def run(self) -> None:
        """启动 InvokeAI"""
        from invokeai.app.run_app import run_app

        logger.info("启动 InvokeAI 中")
        try:
            run_app()
        except KeyboardInterrupt:
            logger.info("关闭 InvokeAI")

    def install(
        self,
        device_type: Literal["cuda", "rocm", "xpu", "cpu"] = "cuda",
        use_uv: bool | None = True,
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list[str] | None = None,
        huggingface_mirror: str | None = None,
        pytorch_mirror_dict: dict[str, str] | None = None,
        model_list: list[str] | None = None,
        check_avaliable_gpu: bool | None = False,
        enable_tcmalloc: bool | None = True,
        enable_cuda_malloc: bool | None = True,
        custom_sys_pkg_cmd: list[list[str]] | list[str] | bool | None = None,
        huggingface_token: str | None = None,
        modelscope_token: str | None = None,
        update_core: bool | None = True,
        *args,
        **kwargs,
    ) -> None:
        """安装 InvokeAI

        Args:
            device_type (Literal["cuda", "rocm", "xpu", "cpu"]): 显卡设备类型
            use_uv (bool | None): 使用 uv 替代 Pip 进行 Python 软件包的安装
            pypi_index_mirror (str | None): PyPI Index 镜像源链接
            pypi_extra_index_mirror (str | None): PyPI Extra Index 镜像源链接
            pypi_find_links_mirror (str | None): PyPI Find Links 镜像源链接
            github_mirror (str | list | None): Github 镜像源链接或者镜像源链接列表
            huggingface_mirror (str | None): HuggingFace 镜像源链接
            pytorch_mirror_dict (dict[str, str] | None): PyTorch 镜像源字典, 需包含不同镜像源对应的 PyTorch 镜像源链接
            model_list (list[str] | None): 模型下载列表
            check_avaliable_gpu (bool | None): 是否检查可用的 GPU, 当检查时没有可用 GPU 将引发`Exception`
            enable_tcmalloc (bool | None): 是否启用 TCMalloc 内存优化
            enable_cuda_malloc (bool | None): 启用 CUDA 显存优化
            custom_sys_pkg_cmd (list[list[str]] | list[str] | bool | None): 自定义调用系统包管理器命令, 设置为 True / None 为使用默认的调用命令, 设置为 False 则禁用该功能ol | None): 自定义调用系统包管理器命令, 设置为 True / None 为使用默认的调用命令, 设置为 False 则禁用该功能
            huggingface_token (str | None): 配置 HuggingFace Token
            modelscope_token (str | None): 配置 ModelScope Token
            update_core (bool | None): 安装时更新内核和扩展
        Raises:
            Exception: GPU 不可用
        """
        warning_unexpected_params(
            message="InvokeAIManager.install() 接收到不期望参数, 请检查参数输入是否正确",
            args=args,
            kwargs=kwargs,
        )
        logger.info("开始安装 InvokeAI")
        if custom_sys_pkg_cmd is False:
            custom_sys_pkg_cmd = []
        elif custom_sys_pkg_cmd is True:
            custom_sys_pkg_cmd = None
        os.chdir(self.workspace)
        if check_avaliable_gpu:
            self.check_avaliable_gpu()
        set_mirror(
            pypi_index_mirror=pypi_index_mirror,
            pypi_extra_index_mirror=pypi_extra_index_mirror,
            pypi_find_links_mirror=pypi_find_links_mirror,
            github_mirror=github_mirror,
            huggingface_mirror=huggingface_mirror,
        )
        configure_pip()
        configure_env_var()
        install_manager_depend(
            use_uv=use_uv,
            custom_sys_pkg_cmd=custom_sys_pkg_cmd,
        )
        if pytorch_mirror_dict is not None:
            self.component.update_pytorch_mirror_dict(pytorch_mirror_dict)
        self.component.install_invokeai(
            device_type=device_type,
            upgrade=update_core,
            use_uv=use_uv,
        )
        if model_list is not None:
            self.get_sd_model_from_list(model_list=model_list)
        self.restart_repo_manager(
            hf_token=huggingface_token,
            ms_token=modelscope_token,
        )
        if enable_tcmalloc:
            self.tcmalloc.configure_tcmalloc()
        if enable_cuda_malloc:
            set_cuda_malloc()
        logger.info("InvokeAI 安装完成")
