"""Stable Diffusion WebUI 管理工具"""

import os
import sys
from pathlib import Path
from typing import Literal

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL
from sd_webui_all_in_one.notebook_manager.base_manager import BaseManager
from sd_webui_all_in_one.mirror_manager import set_mirror
from sd_webui_all_in_one.pytorch_manager.base import PyTorchDeviceType
from sd_webui_all_in_one.utils import warning_unexpected_params
from sd_webui_all_in_one.optimize.cuda_malloc import set_cuda_malloc
from sd_webui_all_in_one.env_manager import configure_env_var, configure_pip
from sd_webui_all_in_one.pkg_manager import install_manager_depend
from sd_webui_all_in_one.base_manager.sd_webui_base import (
    SDWebUiBranchType,
    install_sd_webui_extension,
    update_sd_webui_extensions,
    update_sd_webui,
    check_sd_webui_env,
    install_sd_webui,
)


logger = get_logger(
    name="SD WebUI Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class SDWebUIManager(BaseManager):
    """Stable Diffusion WebUI 管理工具"""

    def mount_drive(
        self,
        extras: list[dict[str, str | bool]] = None,
    ) -> None:
        """挂载 Google Drive 并创建 Stable Diffusion WebUI 输出文件夹

        挂载额外目录需要使用`link_dir`指定要挂载的路径, 并且使用相对路径指定

        相对路径的起始位置为`{self.workspace}/{self.workfolder}`

        若额外链接路径为文件, 需指定`is_file`属性为`True`

        例如:
        ```python
        extras = [
            {"link_dir": "models/loras"},
            {"link_dir": "custom_nodes"},
            {"link_dir": "extra_model_paths.yaml", "is_file": True},
        ]
        ```
        默认挂载的目录和文件: `outputs`, `config_states`, `params.txt`, `config.json`, `ui-config.json`, `styles.csv`

        Args:
            extras (list[dict[str, str | bool]]): 挂载额外目录
        Raises:
            RuntimeError: 挂载 Google Drive 失败
        """
        if not self.mount_google_drive_for_notebook():
            return

        drive_output = Path("/content/drive") / "MyDrive" / "sd_webui_output"
        sd_webui_path = self.workspace / self.workfolder
        links: list[dict[str, str | bool]] = [
            {"link_dir": "outputs"},
            {"link_dir": "config_states"},
            {"link_dir": "params.txt", "is_file": True},
            {"link_dir": "config.json", "is_file": True},
            {"link_dir": "ui-config.json", "is_file": True},
            {"link_dir": "styles.csv", "is_file": True},
        ]
        if extras is not None:
            links += extras
        self.link_to_google_drive(
            base_dir=sd_webui_path,
            drive_path=drive_output,
            links=links,
        )

    def get_sd_model(
        self,
        url: str,
        filename: str = None,
        model_type: str | None = "Stable-diffusion",
    ) -> Path | None:
        """下载模型

        Args:
            url (str): 模型的下载链接
            filename (str | None): 模型下载后保存的名称
            model_type (str | None): 模型的类型
        Returns:
            (Path | None): 模型保存路径
        """
        if model_type == "embeddings":
            path = self.workspace / self.workfolder / model_type
        else:
            path = self.workspace / self.workfolder / "models" / model_type
        return self.get_model(url=url, path=path, filename=filename, tool="aria2")

    def get_sd_model_from_list(
        self,
        model_list: list[dict[str, str]],
    ) -> None:
        """从模型列表下载模型

        `model_list`需要指定`url`(模型下载链接), 可选参数为`type`(模型类型), `filename`(模型保存名称), 例如
        ```python
        model_list = [
            {"url": "url1", "type": "Stable-diffusion"},
            {"url": "url2", "filename": "file.safetensors"},
            {"url": "url3", "type": "loras", "filename": "lora1.safetensors"},
            {"url": "url4"},
        ]
        ```

        Args:
            model_list (list[dict[str, str]]): 模型列表
        """
        for model in model_list:
            url = model.get("url")
            filename = model.get("filename")
            model_type = model.get("type", "Stable-diffusion")
            self.get_sd_model(url=url, filename=filename, model_type=model_type)

    def install_extension(
        self,
        extension: str | list[str],
        use_github_mirror: bool | None = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> None:
        """安装 Stable Diffusion WebUI 扩展

        Args:
            extension (str | list[str]):
                扩展下载地址
            use_github_mirror (bool | None):
                是否使用 Github 镜像源
            custom_github_mirror (str | list[str] | None):
                自定义 Github 镜像源
        """
        install_sd_webui_extension(
            sd_webui_path=self.workspace / self.workfolder,
            extension_url=extension,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
        )

    def update_extensions(
        self,
        use_github_mirror: bool | None = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> None:
        """更新 Stable Diffusion WebUI 扩展

        Args:
            use_github_mirror (bool | None):
                是否使用 Github 镜像源
            custom_github_mirror (str | list[str] | None):
                自定义 Github 镜像源
        """
        update_sd_webui_extensions(
            sd_webui_path=self.workspace / self.workfolder,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
        )

    def check_env(
        self,
        use_uv: bool | None = True,
        use_github_mirror: bool | None = False,
        custom_github_mirror: str | list[str] | None = None,
        use_pypi_mirror: bool | None = False,
    ) -> None:
        """检查 Stable Diffusion WebUI 运行环境

        Args:
            use_uv (bool | None):
                是否使用 uv 安装 Python 软件包
            use_github_mirror (bool | None):
                是否使用 Github 镜像源
            custom_github_mirror (str | list[str] | None):
                自定义 Github 镜像源
            use_pypi_mirror (bool | None):
                是否使用国内 PyPI 镜像源
        """
        check_sd_webui_env(
            sd_webui_path=self.workspace / self.workfolder,
            use_uv=use_uv,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
            use_pypi_mirror=use_pypi_mirror,
        )

    def get_launch_command(
        self,
        params: list[str] | str | None = None,
    ) -> str:
        """获取 Stable Diffusion WebUI 启动命令

        Args:
            params (list[str] | str | None): 启动 Stable Diffusion WebUI 的参数
        Returns:
            str: 完整的启动 Stable Diffusion WebUI 的命令
        """
        sd_webui_path = self.workspace / self.workfolder
        cmd = [Path(sys.executable).as_posix(), (sd_webui_path / "launch.py").as_posix()]
        if params is not None:
            if isinstance(params, str):
                cmd += self.parse_cmd_str_to_list(params)
            else:
                cmd += params
        return self.parse_cmd_list_to_str(cmd)

    def run(
        self,
        params: list[str] | str | None = None,
        display_mode: Literal["terminal", "jupyter"] | None = None,
    ) -> None:
        """启动 Stable Diffusion WebUI

        Args:
            params (list[str] | str | None): 启动 Stable Diffusion WebUI 的参数
            display_mode (Literal["terminal", "jupyter"] | None): 执行子进程时使用的输出模式
        """
        self.launch(
            name="Stable Diffusion WebUI",
            base_path=self.workspace / self.workfolder,
            cmd=self.get_launch_command(params),
            display_mode=display_mode,
        )

    def install(
        self,
        pytorch_mirror_type: PyTorchDeviceType | None = None,
        custom_pytorch_package: str | None = None,
        custom_xformers_package: str | None = None,
        use_pypi_mirror: bool | None = True,
        use_uv: bool | None = True,
        use_github_mirror: bool | None = False,
        custom_github_mirror: str | list[str] | None = None,
        install_branch: SDWebUiBranchType | None = None,
        no_pre_download_extension: bool | None = True,
        no_pre_download_model: bool | None = True,
        use_cn_model_mirror: bool | None = False,
        # legecy
        extension_list: list[str] | None = None,
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
        """安装 Stable Diffusion WebUI

        Args:
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
            install_branch (SDWebUiBranchType | None):
                安装的 Stable Diffusion WebUI 分支
            no_pre_download_extension (bool | None):
                是否禁用预下载 Stable Diffusion WebUI 扩展
            no_pre_download_model (bool | None):
                是否禁用预下载模型
            use_cn_model_mirror (bool | None):
                是否使用国内镜像下载模型
            extension_list (list[str] | None):
                扩展列表
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
            message="SDWebUIManager.install() 接收到不期望参数, 请检查参数输入是否正确",
            args=args,
            kwargs=kwargs,
        )
        logger.info("开始安装 Stable Diffusion WebUI")
        if custom_sys_pkg_cmd is False:
            custom_sys_pkg_cmd = []
        elif custom_sys_pkg_cmd is True:
            custom_sys_pkg_cmd = None

        os.chdir(self.workspace)
        os.environ["STABLE_DIFFUSION_REPO"] = "https://github.com/licyk/stablediffusion"
        sd_webui_path = self.workspace / self.workfolder

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

        install_sd_webui(
            sd_webui_path=sd_webui_path,
            pytorch_mirror_type=pytorch_mirror_type,
            custom_pytorch_package=custom_pytorch_package,
            custom_xformers_package=custom_xformers_package,
            use_pypi_mirror=use_pypi_mirror,
            use_uv=use_uv,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
            install_branch=install_branch,
            no_pre_download_extension=no_pre_download_extension,
            no_pre_download_model=no_pre_download_model,
            use_cn_model_mirror=use_cn_model_mirror,
        )

        if extension_list is not None:
            self.install_extension(
                extension=extension_list,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
            )

        if update_core:
            update_sd_webui(sd_webui_path=sd_webui_path)
            self.update_extensions(
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
            )

        if model_list is not None:
            self.get_sd_model_from_list(model_list)

        self.restart_repo_manager(
            hf_token=huggingface_token,
            ms_token=modelscope_token,
        )
        if enable_tcmalloc:
            self.tcmalloc_manager.configure_tcmalloc()

        if enable_cuda_malloc:
            set_cuda_malloc()

        logger.info("Stable Diffusion WebUI 安装完成")
