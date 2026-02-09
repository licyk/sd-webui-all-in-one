"""InvokeAI 管理工具"""

import os
from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.notebook_manager.base_manager import BaseManager
from sd_webui_all_in_one.mirror_manager import set_mirror
from sd_webui_all_in_one.file_operations.file_manager import get_file_list
from sd_webui_all_in_one.pytorch_manager.base import PyTorchDeviceTypeCategory
from sd_webui_all_in_one.utils import warning_unexpected_params
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL
from sd_webui_all_in_one.optimize.cuda_malloc import set_cuda_malloc
from sd_webui_all_in_one.env_manager import configure_env_var, configure_pip
from sd_webui_all_in_one.pkg_manager import install_manager_depend
from sd_webui_all_in_one.base_manager.invokeai_base import import_model_to_invokeai, check_invokeai_env, install_invokeai, update_invokeai

logger = get_logger(
    name="InvokeAI Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class InvokeAIManager(BaseManager):
    """InvokeAI 管理模块"""

    def mount_drive(self) -> None:
        """挂载 Google Drive 并创建 InvokeAI 输出文件夹, 并设置 INVOKEAI_ROOT 环境变量指定 InvokeAI 输出目录

        Raises:
            RuntimeError: 挂载 Google Drive 失败
        """
        if not self.mount_google_drive_for_notebook():
            return

        drive_output = Path("/content/drive") / "MyDrive" / "invokeai_output"
        drive_output.mkdir(parents=True, exist_ok=True)
        os.environ["INVOKEAI_ROOT"] = drive_output.as_posix()

    def import_model(self) -> None:
        """导入模型到 InvokeAI 中"""
        model_path = self.workspace / self.workfolder / "sd-models"
        model_list = get_file_list(model_path)
        try:
            self.mount_drive()
            import_model_to_invokeai(model_list)
        except Exception as e:
            logger.error("挂载 Google Drive 失败, 无法导入模型: %s", e)

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
    ) -> None:
        """从模型列表下载模型

        Args:
            model_list (list[str]):
                模型列表
            retry (int | None):
                重试下载的次数, 默认为 3
        """
        for url in model_list:
            self.get_sd_model(url=url)

    def check_env(
        self,
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
        """
        check_invokeai_env(
            use_uv=use_uv,
            use_pypi_mirror=use_pypi_mirror,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
        )

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
        device_type: PyTorchDeviceTypeCategory | None = None,
        invokeai_version: str | None = None,
        use_pypi_mirror: bool | None = False,
        use_uv: bool | None = True,
        no_pre_download_model: bool | None = True,
        use_cn_model_mirror: bool | None = False,
        # legecy
        use_hf_mirror: bool | None = False,
        use_github_mirror: bool | None = False,
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list[str] | None = None,
        huggingface_mirror: str | None = None,
        model_list: list[dict[str, str]] | None = None,
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
            pypi_index_mirror (str | None):
                PyPI Index 镜像源链接
            pypi_extra_index_mirror (str | None):
                PyPI Extra Index 镜像源链接
            pypi_find_links_mirror (str | None):
                PyPI Find Links 镜像源链接
            github_mirror (str | list[str] | None):
                Github 镜像源链接或者镜像源链接列表
            huggingface_mirror (str | None):
                HuggingFace 镜像源链接
            use_hf_mirror (bool | None):
                是否启用 HuggingFace 镜像源
            use_github_mirror (bool | None):
                是否使用 Github 镜像源
            model_list (list[dict[str, str]] | None):
                模型下载列表
            check_avaliable_gpu (bool | None):
                是否检查可用的 GPU, 当检查时没有可用 GPU 将引发`Exception`
            enable_tcmalloc (bool | None):
                是否启用 TCMalloc 内存优化
            enable_cuda_malloc (bool | None):
                启用 CUDA 显存优化
            custom_sys_pkg_cmd (list[list[str]] | list[str] | bool | None):
                自定义调用系统包管理器命令, 设置为 True / None 为使用默认的调用命令, 设置为 False 则禁用该功能
            huggingface_token (str | None):
                配置 HuggingFace Token
            modelscope_token (str | None):
                配置 ModelScope Token
            update_core (bool | None):
                安装时更新内核和扩展
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
            github_mirror=github_mirror if use_github_mirror else None,
            huggingface_mirror=huggingface_mirror if use_hf_mirror else None,
        )
        configure_pip()
        configure_env_var()
        install_manager_depend(
            use_uv=use_uv,
            custom_sys_pkg_cmd=custom_sys_pkg_cmd,
        )

        install_invokeai(
            invokeai_path=self.workspace / self.workfolder,
            device_type=device_type,
            invokeai_version=invokeai_version,
            use_pypi_mirror=use_pypi_mirror,
            use_uv=use_uv,
            no_pre_download_model=no_pre_download_model,
            use_cn_model_mirror=use_cn_model_mirror,
        )

        if update_core:
            update_invokeai(
                use_pypi_mirror=use_pypi_mirror,
                use_uv=use_uv,
            )

        if model_list is not None:
            self.get_model_from_list(
                path=self.workspace / self.workfolder,
                model_list=model_list,
            )

        self.restart_repo_manager(
            hf_token=huggingface_token,
            ms_token=modelscope_token,
        )
        if enable_tcmalloc:
            self.tcmalloc_manager.configure_tcmalloc()

        if enable_cuda_malloc:
            set_cuda_malloc()

        logger.info("InvokeAI 安装完成")
