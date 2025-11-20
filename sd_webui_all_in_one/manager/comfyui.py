"""ComfyUI 管理工具"""

import os
import sys
from pathlib import Path
from typing import Literal

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.manager.base import BaseManager
from sd_webui_all_in_one.downloader import download_file
from sd_webui_all_in_one.mirror_manager import set_mirror
from sd_webui_all_in_one.env_check.fix_torch import fix_torch_libomp
from sd_webui_all_in_one.env_check.fix_numpy import check_numpy
from sd_webui_all_in_one.utils import warning_unexpected_params
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL
from sd_webui_all_in_one.optimize.cuda_malloc import set_cuda_malloc
from sd_webui_all_in_one.env import configure_env_var, configure_pip
from sd_webui_all_in_one.env_check.fix_dependencies import py_dependency_checker
from sd_webui_all_in_one.colab_tools import is_colab_environment, mount_google_drive
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check import check_onnxruntime_gpu
from sd_webui_all_in_one.env_check.comfyui_env_analyze import comfyui_conflict_analyzer
from sd_webui_all_in_one.env_manager import install_manager_depend, install_pytorch, install_requirements


logger = get_logger(
    name="ComfyUI Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class ComfyUIManager(BaseManager):
    """ComfyUI 管理工具"""

    def mount_drive(
        self,
        extras: list[dict[str, str | bool]] = None,
    ) -> None:
        """挂载 Google Drive 并创建 ComfyUI 输出文件夹

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
        默认挂载的目录和文件: `output`, `user`, `input`, `extra_model_paths.yaml`

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

        drive_output = drive_path / "MyDrive" / "comfyui_output"
        comfyui_path = self.workspace / self.workfolder
        links: list[dict[str, str | bool]] = [
            {"link_dir": "output"},
            {"link_dir": "user"},
            {"link_dir": "input"},
            {"link_dir": "extra_model_paths.yaml", "is_file": True},
        ]
        if extras is not None:
            links += extras
        self.link_to_google_drive(
            base_dir=comfyui_path,
            drive_path=drive_output,
            links=links,
        )

    def get_sd_model(
        self,
        url: str,
        filename: str = None,
        model_type: str | None = "checkpoints",
    ) -> Path | None:
        """下载模型

        Args:
            url (str): 模型的下载链接
            filename (str | None): 模型下载后保存的名称
            model_type (str | None): 模型的类型
        Returns:
            Path | None: 模型保存路径
        """
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
            {"url": "url1", "type": "checkpoints"},
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
            model_type = model.get("type", "checkpoints")
            self.get_sd_model(url=url, filename=filename, model_type=model_type)

    def install_config(
        self,
        setting: str | None = None,
    ) -> None:
        """下载 ComfyUI 配置文件

        Args:
            setting ( str| None): ComfyUI 设置文件下载链接, 下载后将保存在`{self.workspace}/{self.workfolder}/user/default/comfy.settings.json`
        """
        setting_path = self.workspace / self.workfolder / "user" / "default"
        logger.info("下载配置文件")
        if setting is not None:
            download_file(
                url=setting,
                path=setting_path,
                save_name="comfy.settings.json",
            )

    def install_custom_node(
        self,
        custom_node: str,
    ) -> Path | None:
        """安装 ComfyUI 自定义节点

        Args:
            custom_node (str): 自定义节点下载地址
        Returns:
            (Path | None): 自定义节点安装路径
        """
        custom_node_path = self.workspace / self.workfolder / "custom_nodes"
        name = os.path.basename(custom_node)
        install_path = custom_node_path / name
        logger.info("安装 %s 自定义节点中", name)
        p = git_warpper.clone(repo=custom_node, path=install_path)
        if p is not None:
            logger.info("安装 %s 自定义节点完成", name)
            return p
        logger.error("安装 %s 自定义节点失败", name)
        return None

    def install_custom_nodes_from_list(
        self,
        custom_node_list: list[str],
    ) -> None:
        """安装 ComfyUI 自定义节点

        Args:
            custom_node_list (list[str]): 自定义节点列表
        """
        logger.info("安装 ComfyUI 自定义节点中")
        for node in custom_node_list:
            self.install_custom_node(node)
        logger.info("安装 ComfyUI 自定义节点完成")

    def update_custom_nodes(self) -> None:
        """更新 ComfyUI 自定义节点"""
        custom_node_path = self.workspace / self.workfolder / "custom_nodes"
        custom_node_list = [x for x in custom_node_path.iterdir() if x.is_dir() and (x / ".git").is_dir()]
        for i in custom_node_list:
            logger.info("更新 %s 自定义节点中", i.name)
            if git_warpper.update(i):
                logger.info("更新 %s 自定义节点成功", i.name)
            else:
                logger.info("更新 %s 自定义节点失败", i.name)

    def check_env(
        self,
        use_uv: bool | None = True,
        install_conflict_component_requirement: bool | None = True,
        requirements_file: str | None = "requirements.txt",
    ) -> None:
        """检查 ComfyUI 运行环境

        Args:
            use_uv (bool | None): 使用 uv 安装依赖
            install_conflict_component_requirement (bool | None): 检测到冲突依赖时是否按顺序安装组件依赖
            requirements_file (str | None): 依赖文件名
        """
        comfyui_path = self.workspace / self.workfolder
        requirement_path = comfyui_path / requirements_file
        py_dependency_checker(requirement_path=requirement_path, name="ComfyUI", use_uv=use_uv)
        comfyui_conflict_analyzer(
            comfyui_root_path=comfyui_path,
            install_conflict_component_requirement=install_conflict_component_requirement,
            use_uv=use_uv,
        )
        fix_torch_libomp()
        check_onnxruntime_gpu(use_uv=use_uv, ignore_ort_install=True)
        check_numpy(use_uv=use_uv)

    def get_launch_command(
        self,
        params: list[str] | str | None = None,
    ) -> str:
        """获取 ComfyUI 启动命令

        Args:
            params (list[str] | str | None): 启动 ComfyUI 的参数
        Returns:
            str: 完整的启动 ComfyUI 的命令
        """
        comfyui_path = self.workspace / self.workfolder
        cmd = [Path(sys.executable).as_posix(), (comfyui_path / "main.py").as_posix()]
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
        """启动 ComfyUI

        Args:
            params (list[str] | str | None): 启动 ComfyUI 的参数
            display_mode (Literal["terminal", "jupyter"] | None): 执行子进程时使用的输出模式
        """
        self.launch(
            name="ComfyUI",
            base_path=self.workspace / self.workfolder,
            cmd=self.get_launch_command(params),
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
        comfyui_repo: str | None = None,
        comfyui_requirements: str | None = None,
        comfyui_setting: str | None = None,
        custom_node_list: list[str] | None = None,
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
        """安装 ComfyUI

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
            comfyui_repo (str | None): ComfyUI 仓库地址
            comfyui_requirements (str | None): ComfyUI 依赖文件名
            comfyui_setting (str | None): ComfyUI 设置文件下载链接
            custom_node_list (list[str] | None): 自定义节点列表
            model_list (list[dict[str, str]] | None): 模型下载列表
            check_avaliable_gpu (bool | None): 是否检查可用的 GPU, 当检查时没有可用 GPU 将引发`Exception`
            enable_tcmalloc (bool | None): 是否启用 TCMalloc 内存优化
            enable_cuda_malloc (bool | None): 启用 CUDA 显存优化
            custom_sys_pkg_cmd (list[list[str]] | list[str] | bool | None): 自定义调用系统包管理器命令, 设置为 True / None 为使用默认的调用命令, 设置为 False 则禁用该功能
            huggingface_token (str | None): 配置 HuggingFace Token
            modelscope_token (str | None): 配置 ModelScope Token
            update_core (bool | None): 安装时更新内核和扩展
        Raises:
            Exception: GPU 不可用
        """
        warning_unexpected_params(
            message="ComfyUIManager.install() 接收到不期望参数, 请检查参数输入是否正确",
            args=args,
            kwargs=kwargs,
        )
        logger.info("开始安装 ComfyUI")
        if custom_sys_pkg_cmd is False:
            custom_sys_pkg_cmd = []
        elif custom_sys_pkg_cmd is True:
            custom_sys_pkg_cmd = None
        os.chdir(self.workspace)
        comfyui_path = self.workspace / self.workfolder
        comfyui_repo = "https://github.com/comfyanonymous/ComfyUI" if comfyui_repo is None else comfyui_repo
        comfyui_setting = "https://github.com/licyk/sd-webui-all-in-one/raw/main/config/comfy.settings.json" if comfyui_setting is None else comfyui_setting
        requirements_path = comfyui_path / ("requirements.txt" if comfyui_requirements is None else comfyui_requirements)
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
        git_warpper.clone(comfyui_repo, comfyui_path)
        if custom_node_list is not None:
            self.install_custom_nodes_from_list(custom_node_list)
        if update_core:
            git_warpper.update(comfyui_path)
            self.update_custom_nodes()
        install_pytorch(
            torch_package=torch_ver,
            xformers_package=xformers_ver,
            pytorch_mirror=pytorch_mirror,
            use_uv=use_uv,
        )
        install_requirements(
            path=requirements_path,
            use_uv=use_uv,
            cwd=comfyui_path,
        )
        self.install_config(comfyui_setting)
        if model_list is not None:
            self.get_sd_model_from_list(model_list)
        self.restart_repo_manager(
            hf_token=huggingface_token,
            ms_token=modelscope_token,
        )
        if enable_tcmalloc:
            self.tcmalloc.configure_tcmalloc()
        if enable_cuda_malloc:
            set_cuda_malloc()
        logger.info("ComfyUI 安装完成")
