"""SD Trainer 管理工具"""

import os
import sys
import traceback
import importlib.metadata
from pathlib import Path
from typing import Literal

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.manager.base import BaseManager
from sd_webui_all_in_one.mirror_manager import set_mirror
from sd_webui_all_in_one.env_check.fix_torch import fix_torch_libomp
from sd_webui_all_in_one.utils import warning_unexpected_params
from sd_webui_all_in_one.env_check.fix_numpy import check_numpy
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL
from sd_webui_all_in_one.optimize.cuda_malloc import set_cuda_malloc
from sd_webui_all_in_one.env import configure_env_var, configure_pip
from sd_webui_all_in_one.env_check.fix_dependencies import py_dependency_checker
from sd_webui_all_in_one.package_analyzer.py_ver_cmp import PyWhlVersionComparison
from sd_webui_all_in_one.colab_tools import is_colab_environment, mount_google_drive
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check import check_onnxruntime_gpu
from sd_webui_all_in_one.env_manager import install_manager_depend, install_pytorch, install_requirements, pip_install


logger = get_logger(
    name="SD Trainer Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class SDTrainerManager(BaseManager):
    """SD Trainer 管理工具"""

    def mount_drive(
        self,
        extras: list[dict[str, str | bool]] = None,
    ) -> None:
        """挂载 Google Drive 并创建 SD Trainer 输出文件夹

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
        默认挂载的目录和文件: `outputs`, `output`, `config`, `train`, `logs`

        Args:
            extras (list[dict[str, str | bool]]): 挂载额外目录
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

        drive_output = drive_path / "MyDrive" / "sd_trainer_output"
        sd_trainer_path = self.workspace / self.workfolder
        links: list[dict[str, str | bool]] = [
            {"link_dir": "outputs"},
            {"link_dir": "output"},
            {"link_dir": "config"},
            {"link_dir": "train"},
            {"link_dir": "logs"},
        ]
        if extras is not None:
            links += extras
        self.link_to_google_drive(
            base_dir=sd_trainer_path,
            drive_path=drive_output,
            links=links,
        )

    def get_sd_model(
        self,
        url: str,
        filename: str = None,
    ) -> Path | None:
        """下载模型

        Args:
            url (str): 模型的下载链接
            filename (str | None): 模型下载后保存的名称
        Returns:
            (Path | None): 模型保存路径
        """
        path = self.workspace / self.workfolder / "sd-models"
        return self.get_model(url=url, path=path, filename=filename, tool="aria2")

    def get_sd_model_from_list(
        self,
        model_list: list[dict[str, str]],
    ) -> None:
        """从模型列表下载模型

        `model_list`需要指定`url`(模型下载链接), 可选参数为`filename`(模型保存名称), 例如
        ```python
        model_list = [
            {"url": "url1", "type": "checkpoints"},
            {"url": "url2", "filename": "file.safetensors"},
            {"url": "url4"},
        ]
        ```

        Args:
            model_list (list[dict[str, str]]): 模型列表
        """
        for model in model_list:
            url = model.get("url")
            filename = model.get("filename")
            self.get_sd_model(url=url, filename=filename)

    def check_protobuf(
        self,
        use_uv: bool | None = True,
    ) -> None:
        """检查 protobuf 版本问题

        Args:
            use_uv (bool | None): 使用 uv 安装依赖
        """
        logger.info("检查 protobuf 版本问题中")
        try:
            ver = importlib.metadata.version("protobuf")
            if PyWhlVersionComparison(ver) != PyWhlVersionComparison("3.20.0"):
                logger.info("重新安装 protobuf 中")
                pip_install("protobuf==3.20.0", use_uv=use_uv)
                logger.info("重新安装 protobuf 成功")
                return
            logger.info("protobuf 检查完成")
        except Exception as e:
            traceback.print_exc()
            logger.error("检查 protobuf 时发送错误: %s", e)

    def check_env(
        self,
        use_uv: bool | None = True,
        requirements_file: str | None = "requirements.txt",
    ) -> None:
        """检查 SD Trainer 运行环境

        Args:
            use_uv (bool | None): 使用 uv 安装依赖
            requirements_file (str | None): 依赖文件名
        """
        sd_trainer_path = self.workspace / self.workfolder
        requirement_path = sd_trainer_path / requirements_file
        py_dependency_checker(requirement_path=requirement_path, name="SD Trainer", use_uv=use_uv)
        fix_torch_libomp()
        check_onnxruntime_gpu(use_uv=use_uv, ignore_ort_install=True)
        check_numpy(use_uv=use_uv)
        self.check_protobuf(use_uv=use_uv)

    def run(
        self,
        params: list[str] | str | None = None,
        display_mode: Literal["terminal", "jupyter"] | None = None,
    ) -> None:
        """启动 SD Trainer

        Args:
            params (list[str] | str | None): 启动 SD Trainer 的参数
            display_mode (Literal["terminal", "jupyter"] | None): 执行子进程时使用的输出模式
        """
        sd_trainer_path = self.workspace / self.workfolder
        if (sd_trainer_path / "gui.py").exists():
            scripts_name = "gui.py"
        elif (sd_trainer_path / "kohya_gui.py").exists():
            scripts_name = "kohya_gui.py"
        else:
            scripts_name = "kohya_gui.py"
        cmd = [Path(sys.executable).as_posix(), (sd_trainer_path / scripts_name).as_posix()]
        if params is not None:
            if isinstance(params, str):
                cmd += self.parse_arguments(params)
            else:
                cmd += params
        self.launch(
            name="SD Trainer",
            base_path=sd_trainer_path.parent,
            cmd=cmd,
            display_mode=display_mode,
        )

    def install(
        self,
        torch_ver: str | list[str] | None = None,
        xformers_ver: str | list[str] | None = None,
        use_uv: bool | None = True,
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list[str] | None = None,
        huggingface_mirror: str | None = None,
        pytorch_mirror: str | None = None,
        sd_trainer_repo: str | None = None,
        sd_trainer_requirements: str | None = None,
        model_list: list[dict[str, str]] | None = None,
        check_avaliable_gpu: bool | None = False,
        enable_tcmalloc: bool | None = True,
        enable_cuda_malloc: bool | None = True,
        custom_sys_pkg_cmd: list[list[str]] | list[str] | bool | None = None,
        *args,
        **kwargs,
    ) -> None:
        """安装 SD Trainer

        Args:
            torch_ver (str | list[str] | None): 指定的 PyTorch 软件包包名, 并包括版本号
            xformers_ver (str | list[str] | None): 指定的 xFormers 软件包包名, 并包括版本号
            use_uv (bool | None): 使用 uv 替代 Pip 进行 Python 软件包的安装
            pypi_index_mirror (str | None): PyPI Index 镜像源链接
            pypi_extra_index_mirror (str | None): PyPI Extra Index 镜像源链接
            pypi_find_links_mirror (str | None): PyPI Find Links 镜像源链接
            github_mirror (str | list[str] | None): Github 镜像源链接或者镜像源链接列表
            huggingface_mirror (str | None): HuggingFace 镜像源链接
            pytorch_mirror (str | None): PyTorch 镜像源链接
            sd_trainer_repo (str | None): SD Trainer 仓库地址
            sd_trainer_requirements (str | None): SD Trainer 依赖文件名
            model_list (list[dict[str, str]] | None): 模型下载列表
            check_avaliable_gpu (bool | None): 是否检查可用的 GPU, 当检查时没有可用 GPU 将引发`Exception`
            enable_tcmalloc (bool | None): 是否启用 TCMalloc 内存优化
            enable_cuda_malloc (bool | None): 启用 CUDA 显存优化
            custom_sys_pkg_cmd (list[list[str]] | list[str] | bool | None): 自定义调用系统包管理器命令, 设置为 True / None 为使用默认的调用命令, 设置为 False 则禁用该功能
        Raises:
            Exception: GPU 不可用
        """
        warning_unexpected_params(
            message="SDTrainerManager.install() 接收到不期望参数, 请检查参数输入是否正确",
            args=args,
            kwargs=kwargs,
        )
        logger.info("开始安装 SD Trainer")
        if custom_sys_pkg_cmd is False:
            custom_sys_pkg_cmd = []
        elif custom_sys_pkg_cmd is True:
            custom_sys_pkg_cmd = None
        os.chdir(self.workspace)
        sd_trainer_path = self.workspace / self.workfolder
        sd_trainer_repo = "https://github.com/Akegarasu/lora-scripts" if sd_trainer_repo is None else sd_trainer_repo
        requirements_path = sd_trainer_path / ("requirements.txt" if sd_trainer_requirements is None else sd_trainer_requirements)
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
        git_warpper.clone(sd_trainer_repo, sd_trainer_path)
        git_warpper.update(sd_trainer_path)
        install_pytorch(
            torch_package=torch_ver,
            xformers_package=xformers_ver,
            pytorch_mirror=pytorch_mirror,
            use_uv=use_uv,
        )
        install_requirements(
            path=requirements_path,
            use_uv=use_uv,
            cwd=sd_trainer_path.parent,
        )
        if model_list is not None:
            self.get_sd_model_from_list(model_list)
        if enable_tcmalloc:
            self.tcmalloc.configure_tcmalloc()
        if enable_cuda_malloc:
            set_cuda_malloc()
        logger.info("SD Trainer 安装完成")
