"""Stable Diffusion WebUI 管理工具"""

import os
import sys
from pathlib import Path
from typing import Literal

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL
from sd_webui_all_in_one.downloader import download_file
from sd_webui_all_in_one.notebook_manager.base_manager import BaseManager
from sd_webui_all_in_one.mirror_manager import set_mirror
from sd_webui_all_in_one.env_check.fix_torch import fix_torch_libomp
from sd_webui_all_in_one.env_check.fix_numpy import check_numpy
from sd_webui_all_in_one.utils import warning_unexpected_params
from sd_webui_all_in_one.optimize.cuda_malloc import set_cuda_malloc
from sd_webui_all_in_one.env_manager import configure_env_var, configure_pip
from sd_webui_all_in_one.env_check.fix_dependencies import py_dependency_checker
from sd_webui_all_in_one.colab_tools import is_colab_environment, mount_google_drive
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check import check_onnxruntime_gpu
from sd_webui_all_in_one.pkg_manager import install_manager_depend, install_pytorch, install_requirements
from sd_webui_all_in_one.env_check.sd_webui_extension_dependency_installer import install_extension_requirements


logger = get_logger(
    name="SD WebUI Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class SDWebUIManager(BaseManager):
    """Stable Diffusion WebUI 管理工具"""

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
        os.environ["STABLE_DIFFUSION_REPO"] = "https://github.com/licyk/stablediffusion"

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
        if not is_colab_environment():
            logger.warning("当前环境非 Colab, 无法挂载 Google Drive")
            return

        drive_path = Path("/content/drive")
        if not (drive_path / "MyDrive").exists():
            if not mount_google_drive(drive_path):
                raise RuntimeError("挂载 Google Drive 失败, 请尝试重新挂载 Google Drive")

        drive_output = drive_path / "MyDrive" / "sd_webui_output"
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

    def install_config(
        self,
        setting: str | None = None,
        requirements: str | None = None,
        requirements_file: str | None = None,
    ) -> None:
        """下载 Stable Diffusion WebUI 配置文件

        Args:
            setting (str | None): Stable Diffusion WebUI 设置文件下载链接, 下载后将保存在`{self.workspace}/{self.workfolder}/config.json`
            requirements (str | None): Stable Diffusion WebUI 依赖表文件下载链接, 下载后将保存在`{self.workspace}/{self.workfolder}/{requirements_file}`
            requirements_file (str | None): Stable Diffusion WebUI 依赖表文件名
        """
        setting_path = self.workspace / self.workfolder
        logger.info("下载配置文件")
        if setting is not None:
            download_file(
                url=setting,
                path=setting_path,
                save_name="config.json",
            )
        if requirements is not None:
            try:
                (setting_path / requirements_file).unlink(missing_ok=True)
                download_file(
                    url=requirements,
                    path=setting_path,
                    save_name=requirements_file,
                )
            except Exception as e:
                logger.error("下载 Stable Diffusion WebUI 依赖文件出现错误: %s", e)

    def install_extension(
        self,
        extension: str,
    ) -> Path | None:
        """安装 Stable Diffusion WebUI 扩展

        Args:
            extension (str): 扩展下载地址
        Returns:
            (Path | None): 扩展安装路径
        """
        extension_path = self.workspace / self.workfolder / "extensions"
        name = os.path.basename(extension)
        install_path = extension_path / name
        logger.info("安装 %s 扩展中", name)
        p = git_warpper.clone(repo=extension, path=install_path)
        if p is not None:
            logger.info("安装 %s 扩展完成", name)
            return p
        logger.error("安装 %s 扩展失败", name)
        return None

    def install_extensions_from_list(
        self,
        extension_list: list[str],
    ) -> None:
        """安装 Stable Diffusion WebUI 扩展

        Args:
            extension_list (list[str]): 扩展列表
        """
        logger.info("安装 Stable Diffusion WebUI 扩展中")
        for extension in extension_list:
            self.install_extension(extension)
        logger.info("安装 Stable Diffusion WebUI 扩展完成")

    def update_extensions(self) -> None:
        """更新 Stable Diffusion WebUI 扩展"""
        extension_path = self.workspace / self.workfolder / "extensions"
        extension_list = [x for x in extension_path.iterdir() if x.is_dir() and (x / ".git").is_dir()]
        for i in extension_list:
            logger.info("更新 %s 扩展中", i.name)
            if git_warpper.update(i):
                logger.info("更新 %s 扩展成功", i.name)
            else:
                logger.info("更新 %s 扩展失败", i.name)

    def fix_stable_diffusion_invaild_repo_url(self) -> None:
        """修复 Stable Diffusion WebUI 无效的组件仓库源"""
        logger.info("检查 Stable Diffusion WebUI 无效组件仓库源")
        stable_diffusion_path = self.workspace / self.workfolder / "repositories" / "stable-diffusion-stability-ai"
        new_repo_url = "https://github.com/licyk/stablediffusion"
        if not git_warpper.is_git_repo(stable_diffusion_path):
            return

        custom_env = os.environ.copy()
        custom_env.pop("GIT_CONFIG_GLOBAL", None)
        try:
            repo_url = self.run_cmd(
                ["git", "-C", str(stable_diffusion_path), "remote", "get-url", "origin"],
                custom_env=custom_env,
                live=False,
            )
        except Exception:
            return

        if repo_url in ["https://github.com/Stability-AI/stablediffusion.git", "https://github.com/Stability-AI/stablediffusion"]:
            try:
                self.run_cmd(
                    ["git", "-C", str(stable_diffusion_path), "remote", "set-url", "origin", new_repo_url],
                    custom_env=custom_env,
                    live=False,
                )
                logger.info("替换仓库源: %s -> %s", repo_url, new_repo_url)
            except Exception as e:
                logger.error("修复 Stable Diffusion WebUI 无效的组件仓库源时发生错误: %s", e)

    def check_env(
        self,
        use_uv: bool | None = True,
        requirements_file: str | None = "requirements_versions.txt",
    ) -> None:
        """检查 Stable Diffusion WebUI 运行环境

        Args:
            use_uv (bool | None): 使用 uv 安装依赖
            requirements_file (str | None): 依赖文件名
        """
        sd_webui_path = self.workspace / self.workfolder
        requirement_path = sd_webui_path / requirements_file
        self.fix_stable_diffusion_invaild_repo_url()
        py_dependency_checker(
            requirement_path=requirement_path,
            name="Stable Diffusion WebUI",
            use_uv=use_uv,
        )
        install_extension_requirements(sd_webui_base_path=sd_webui_path)
        fix_torch_libomp()
        check_onnxruntime_gpu(use_uv=use_uv, skip_if_missing=True)
        check_numpy(use_uv=use_uv)

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
        torch_ver: str | list[str] | None = None,
        xformers_ver: str | list[str] | None = None,
        use_uv: bool | None = True,
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list[str] | None = None,
        huggingface_mirror: str | None = None,
        pytorch_mirror: str | None = None,
        sd_webui_repo: str | None = None,
        sd_webui_branch: str | None = None,
        sd_webui_requirements: str | None = None,
        sd_webui_requirements_url: str | None = None,
        sd_webui_setting: str | None = None,
        extension_list: list[str] | None = None,
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
            torch_ver (str | list[str] | None): 指定的 PyTorch 软件包包名, 并包括版本号
            xformers_ver (str | list[str] | None): 指定的 xFormers 软件包包名, 并包括版本号
            use_uv (bool | None): 使用 uv 替代 Pip 进行 Python 软件包的安装
            pypi_index_mirror (str | None): PyPI Index 镜像源链接
            pypi_extra_index_mirror (str | None): PyPI Extra Index 镜像源链接
            pypi_find_links_mirror (str | None): PyPI Find Links 镜像源链接
            github_mirror (str | list[str] | None): Github 镜像源链接或者镜像源链接列表
            huggingface_mirror (str | None): HuggingFace 镜像源链接
            pytorch_mirror (str | None): PyTorch 镜像源链接
            sd_webui_repo (str | None): Stable Diffusion WebUI 仓库地址
            sd_webui_branch (str | None): Stable Diffusion WebUI 分支
            sd_webui_requirements (str | None): Stable Diffusion WebUI 依赖文件名
            sd_webui_requirements_url (str | None): Stable Diffusion WebUI 依赖文件下载地址
            sd_webui_setting (str | None): Stable Diffusion WebUI 预设文件下载链接
            extension_list (list[str] | None): 扩展列表
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
        sd_webui_path = self.workspace / self.workfolder
        sd_webui_repo = "https://github.com/AUTOMATIC1111/stable-diffusion-webui" if sd_webui_repo is None else sd_webui_repo
        sd_webui_setting = "https://github.com/licyk/sd-webui-all-in-one/raw/main/config/sd_webui_config.json" if sd_webui_setting is None else sd_webui_setting
        requirements_path = sd_webui_path / ("requirements_versions.txt" if sd_webui_requirements is None else sd_webui_requirements)
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
        git_warpper.clone(sd_webui_repo, sd_webui_path)
        if extension_list is not None:
            self.install_extensions_from_list(extension_list)
        if update_core:
            git_warpper.update(sd_webui_path)
            self.update_extensions()
        if sd_webui_branch is not None:
            git_warpper.switch_branch(
                path=sd_webui_path,
                branch=sd_webui_branch,
                recurse_submodules=True,
            )
        install_pytorch(
            torch_package=torch_ver,
            xformers_package=xformers_ver,
            custom_env=pytorch_mirror,
            use_uv=use_uv,
        )
        self.install_config(
            setting=sd_webui_setting,
            requirements=sd_webui_requirements_url,
            requirements_file=requirements_path.name,
        )
        install_requirements(
            path=requirements_path,
            use_uv=use_uv,
            cwd=sd_webui_path,
        )
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
        logger.info("Stable Diffusion WebUI 安装完成")
