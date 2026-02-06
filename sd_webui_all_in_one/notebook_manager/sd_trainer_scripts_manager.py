"""SD Scripts 管理工具"""

import os
from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.notebook_manager.base_manager import BaseManager
from sd_webui_all_in_one.mirror_manager import set_mirror
from sd_webui_all_in_one.git_warpper import set_git_config
from sd_webui_all_in_one.env_check.fix_numpy import check_numpy
from sd_webui_all_in_one.pytorch_manager.base import PyTorchDeviceType
from sd_webui_all_in_one.utils import warning_unexpected_params
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL
from sd_webui_all_in_one.optimize.cuda_malloc import set_cuda_malloc
from sd_webui_all_in_one.env_manager import config_wandb_token, configure_env_var, configure_pip
from sd_webui_all_in_one.pkg_manager import install_manager_depend, pip_install
from sd_webui_all_in_one.base_manager.sd_scripts_base import SDScriptsBranchType, check_sd_scripts_env, install_sd_scripts, update_sd_scripts


logger = get_logger(
    name="SD Trainer Scripts Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class SDTrainerScriptsManager(BaseManager):
    """sd-scripts 管理工具"""

    def check_env(
        self,
        use_uv: bool | None = True,
        use_github_mirror: bool | None = False,
        custom_github_mirror: str | list[str] | None = None,
        use_pypi_mirror: bool | None = False,
    ) -> None:
        """检查 sd-scripts 运行环境

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
        check_sd_scripts_env(
            sd_scripts_path=self.workspace / self.workfolder,
            use_uv=use_uv,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
            use_pypi_mirror=use_pypi_mirror,
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
        install_branch: SDScriptsBranchType | None = None,
        no_pre_download_model: bool | None = False,
        use_cn_model_mirror: bool | None = True,
        # legecy
        use_hf_mirror: bool | None = False,
        model_path: str | Path = None,
        model_list: list[str, int] | None = None,
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list[str] | None = None,
        huggingface_mirror: str | None = None,
        huggingface_token: str | None = None,
        modelscope_token: str | None = None,
        wandb_token: str | None = None,
        git_username: str | None = None,
        git_email: str | None = None,
        check_avaliable_gpu: bool | None = False,
        enable_tcmalloc: bool | None = True,
        enable_cuda_malloc: bool | None = True,
        custom_sys_pkg_cmd: list[list[str]] | list[str] | bool | None = None,
        update_core: bool | None = True,
        *args,
        **kwargs,
    ) -> None:
        """安装 sd-scripts 和其余环境

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
            install_branch (SDScriptsBranchType | None):
                安装的 SD Scripts 分支
            no_pre_download_model (bool | None):
                是否禁用预下载模型
            use_cn_model_mirror (bool | None):
                是否使用国内镜像下载模型
            use_hf_mirror (bool | None):
                是否启用 HuggingFace 镜像源
            model_path (str | Path | None):
                指定模型下载的路径
            model_list (list[str, int] | None):
                模型下载列表
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
            huggingface_token (str | None):
                配置 HuggingFace Token
            modelscope_token (str | None):
                配置 ModelScope Token
            wandb_token (str | None):
                配置 WandB Token
            git_username (str | None):
                Git 用户名
            git_email (str | None):
                Git 邮箱
            check_avaliable_gpu (bool | None):
                检查是否有可用的 GPU
            enable_tcmalloc (bool | None):
                启用 TCMalloc 内存优化
            enable_cuda_malloc (bool | None):
                启用 CUDA 显存优化
            custom_sys_pkg_cmd (list[list[str]] | list[str] | bool | None):
                自定义调用系统包管理器命令, 设置为 True / None 为使用默认的调用命令, 设置为 False 则禁用该功能
            update_core (bool | None):
                安装时更新内核和扩展
        """
        warning_unexpected_params(
            message="SDScriptsManager.install() 接收到不期望参数, 请检查参数输入是否正确",
            args=args,
            kwargs=kwargs,
        )
        logger.info("开始安装 sd-scripts")
        if custom_sys_pkg_cmd is False:
            custom_sys_pkg_cmd = []
        elif custom_sys_pkg_cmd is True:
            custom_sys_pkg_cmd = None

        os.chdir(self.workspace)
        sd_scripts_path = self.workspace / self.workfolder
        model_path = model_path if model_path is not None else (self.workspace / "sd-models")
        model_list = model_list if model_list else []

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
        install_sd_scripts(
            sd_scripts_path=sd_scripts_path,
            pytorch_mirror_type=pytorch_mirror_type,
            custom_pytorch_package=custom_pytorch_package,
            custom_xformers_package=custom_xformers_package,
            use_pypi_mirror=use_pypi_mirror,
            use_uv=use_uv,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
            install_branch=install_branch,
            no_pre_download_model=no_pre_download_model,
            use_cn_model_mirror=use_cn_model_mirror,
        )
        if update_core:
            update_sd_scripts(
                sd_scripts_path=sd_scripts_path,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
            )
        pip_install("lycoris-lora", "dadaptation", "open-clip-torch", use_uv=use_uv)
        pip_install("urllib3", "--upgrade", use_uv=use_uv)
        check_numpy(use_uv=use_uv)
        self.get_model_from_list(path=model_path, model_list=model_list)
        self.restart_repo_manager(
            hf_token=huggingface_token,
            ms_token=modelscope_token,
        )
        config_wandb_token(wandb_token)
        set_git_config(
            username=git_username,
            email=git_email,
        )

        if enable_tcmalloc:
            self.tcmalloc_manager.configure_tcmalloc()

        if enable_cuda_malloc:
            set_cuda_malloc()

        logger.info("sd-scripts 安装完成")
