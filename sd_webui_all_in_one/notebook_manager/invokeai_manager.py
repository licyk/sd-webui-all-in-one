"""InvokeAI 管理工具"""

import os
from pathlib import Path
from typing import Literal

from sd_webui_all_in_one.base_manager.invokeai_base import InvokeAIComponentManager
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.notebook_manager.base_manager import BaseManager
from sd_webui_all_in_one.mirror_manager import set_mirror
from sd_webui_all_in_one.file_operations.file_manager import get_file_list
from sd_webui_all_in_one.env_check.fix_torch import fix_torch_libomp
from sd_webui_all_in_one.env_check.fix_numpy import check_numpy
from sd_webui_all_in_one.utils import warning_unexpected_params
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL
from sd_webui_all_in_one.optimize.cuda_malloc import set_cuda_malloc
from sd_webui_all_in_one.env_manager import configure_env_var, configure_pip
from sd_webui_all_in_one.colab_tools import is_colab_environment, mount_google_drive
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check import check_onnxruntime_gpu
from sd_webui_all_in_one.pkg_manager import install_manager_depend
from sd_webui_all_in_one.base_manager.invokeai_base import import_model_to_invokeai

logger = get_logger(
    name="InvokeAI Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


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

    def import_model(self) -> None:
        """导入模型到 InvokeAI 中"""
        model_path = self.workspace / self.workfolder / "sd-models"
        model_list = get_file_list(model_path)
        try:
            self.mount_drive()
        except Exception as e:
            logger.error("挂载 Google Drive 失败, 无法导入模型: %s", e)
            return
        import_model_to_invokeai(model_list)

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
        check_onnxruntime_gpu(use_uv=use_uv, skip_if_missing=True)
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
