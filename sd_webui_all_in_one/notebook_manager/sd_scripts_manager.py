"""SD Scripts 管理工具"""

import os
from pathlib import Path

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.notebook_manager.base_manager import BaseManager
from sd_webui_all_in_one.mirror_manager import set_mirror
from sd_webui_all_in_one.git_warpper import set_git_config
from sd_webui_all_in_one.env_check.fix_torch import fix_torch_libomp
from sd_webui_all_in_one.env_check.fix_numpy import check_numpy
from sd_webui_all_in_one.utils import warning_unexpected_params
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL
from sd_webui_all_in_one.optimize.cuda_malloc import set_cuda_malloc
from sd_webui_all_in_one.env_check.fix_dependencies import py_dependency_checker
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check import check_onnxruntime_gpu
from sd_webui_all_in_one.env_manager import config_wandb_token, configure_env_var, configure_pip
from sd_webui_all_in_one.pkg_manager import install_manager_depend, install_pytorch, install_requirements, pip_install


logger = get_logger(
    name="SD Scripts Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class SDScriptsManager(BaseManager):
    """sd-scripts 管理工具"""

    def check_env(
        self,
        use_uv: bool | None = True,
        requirements_file: str | None = "requirements.txt",
    ) -> None:
        """检查 sd-scripts 运行环境

        Args:
            use_uv (bool | None): 使用 uv 安装依赖
            requirements_file (str | None): 依赖文件名
        """
        sd_webui_path = self.workspace / self.workfolder
        requirement_path = sd_webui_path / requirements_file
        py_dependency_checker(
            requirement_path=requirement_path,
            name="sd-scripts",
            use_uv=use_uv,
        )
        fix_torch_libomp()
        check_onnxruntime_gpu(use_uv=use_uv, ignore_ort_install=False)
        check_numpy(use_uv=use_uv)

    def install(
        self,
        torch_ver: str | list[str] | None = None,
        xformers_ver: str | list[str] | None = None,
        git_branch: str | None = None,
        git_commit: str | None = None,
        model_path: str | Path = None,
        model_list: list[str, int] | None = None,
        use_uv: bool | None = True,
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list[str] | None = None,
        huggingface_mirror: str | None = None,
        pytorch_mirror: str | None = None,
        sd_scripts_repo: str | None = None,
        sd_scripts_requirements: str | None = None,
        retry: int | None = 3,
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

        配置并安装 sd-scripts 及其相关依赖环境, 包括 PyTorch、xFormers 等, 并可选择性下载模型文件.

        SDScriptsManager.install() 将会以下几件事
        ```
        1. 配置 PyPI / Github / HuggingFace 镜像源
        2. 配置 Pip / uv
        3. 安装管理工具自身依赖
        4. 安装 sd-scripts
        5. 安装 PyTorch / xFormers
        6. 安装 sd-scripts 的依赖
        7. 下载模型
        8. 配置 HuggingFace / ModelScope / WandB Token 环境变量
        9. 配置其他工具
        ```

        Args:
            torch_ver (str | list[str] | None): 指定的 PyTorch 软件包包名, 并包括版本号
            xformers_ver (str | list[str] | None): 指定的 xFormers 软件包包名, 并包括版本号
            git_branch (str | None): 指定要切换 sd-scripts 的分支
            git_commit (str | None): 指定要切换到 sd-scripts 的提交记录
            model_path (str | Path | None): 指定模型下载的路径
            model_list (list[str, int] | None): 模型下载列表
            use_uv (bool | None): 使用 uv 替代 Pip 进行 Python 软件包的安装
            pypi_index_mirror (str | None): PyPI Index 镜像源链接
            pypi_extra_index_mirror (str | None): PyPI Extra Index 镜像源链接
            pypi_find_links_mirror (str | None): PyPI Find Links 镜像源链接
            github_mirror (str | list[str] | None): Github 镜像源链接或者镜像源链接列表
            huggingface_mirror (str | None): HuggingFace 镜像源链接
            pytorch_mirror (str | None): PyTorch 镜像源链接
            sd_scripts_repo (str | None): sd-scripts 仓库地址, 未指定时默认为`https://github.com/kohya-ss/sd-scripts`
            sd_scripts_requirements (str | None): sd-scripts 的依赖文件名, 未指定时默认为 requirements.txt
            retry (int | None): 设置下载模型失败时重试次数
            huggingface_token (str | None): 配置 HuggingFace Token
            modelscope_token (str | None): 配置 ModelScope Token
            wandb_token (str | None): 配置 WandB Token
            git_username (str | None): Git 用户名
            git_email (str | None): Git 邮箱
            check_avaliable_gpu (bool | None): 检查是否有可用的 GPU, 当 GPU 不可用时引发`Exception`
            enable_tcmalloc (bool | None): 启用 TCMalloc 内存优化
            enable_cuda_malloc (bool | None): 启用 CUDA 显存优化
            custom_sys_pkg_cmd (list[list[str]] | list[str] | bool | None): 自定义调用系统包管理器命令, 设置为 True / None 为使用默认的调用命令, 设置为 False 则禁用该功能
            update_core (bool | None): 安装时更新内核和扩展
        Raises:
            Exception: GPU 不可用
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
        requirement_path = sd_scripts_path / (sd_scripts_requirements if sd_scripts_requirements is not None else "requirements.txt")
        sd_scripts_repo = sd_scripts_repo if sd_scripts_repo is not None else "https://github.com/kohya-ss/sd-scripts"
        model_path = model_path if model_path is not None else (self.workspace / "sd-models")
        model_list = model_list if model_list else []
        # 检查是否有可用的 GPU
        if check_avaliable_gpu:
            self.check_avaliable_gpu()
        # 配置镜像源
        set_mirror(
            pypi_index_mirror=pypi_index_mirror,
            pypi_extra_index_mirror=pypi_extra_index_mirror,
            pypi_find_links_mirror=pypi_find_links_mirror,
            github_mirror=github_mirror,
            huggingface_mirror=huggingface_mirror,
        )
        configure_pip()  # 配置 Pip / uv
        configure_env_var()
        install_manager_depend(
            use_uv=use_uv,
            custom_sys_pkg_cmd=custom_sys_pkg_cmd,
        )  # 准备 Notebook 的运行依赖
        # 下载 sd-scripts
        git_warpper.clone(
            repo=sd_scripts_repo,
            path=sd_scripts_path,
        )
        if update_core:
            git_warpper.update(sd_scripts_path)  # 更新 sd-scripts
        # 切换指定的 sd-scripts 分支
        if git_branch is not None:
            git_warpper.switch_branch(path=sd_scripts_path, branch=git_branch)
        # 切换到指定的 sd-scripts 提交记录
        if git_commit is not None:
            git_warpper.switch_commit(path=sd_scripts_path, commit=git_commit)
        # 安装 PyTorch 和 xFormers
        install_pytorch(
            torch_package=torch_ver,
            xformers_package=xformers_ver,
            custom_env=pytorch_mirror,
            use_uv=use_uv,
        )
        # 安装 sd-scripts 的依赖
        install_requirements(
            path=requirement_path,
            use_uv=use_uv,
            cwd=sd_scripts_path,
        )
        # 安装使用 sd-scripts 进行训练所需的其他软件包
        logger.info("安装其他 Python 模块中")
        try:
            pip_install("lycoris-lora", "dadaptation", "open-clip-torch", use_uv=use_uv)
        except Exception as e:
            logger.error("安装额外 Python 软件包时发生错误: %s", e)
        # 更新 urllib3
        try:
            pip_install("urllib3", "--upgrade", use_uv=use_uv)
        except Exception as e:
            logger.error("更新 urllib3 时发生错误: %s", e)
        check_numpy(use_uv=use_uv)
        self.get_model_from_list(path=model_path, model_list=model_list, retry=retry)
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
            self.tcmalloc.configure_tcmalloc()
        if enable_cuda_malloc:
            set_cuda_malloc()
        logger.info("sd-scripts 安装完成")
