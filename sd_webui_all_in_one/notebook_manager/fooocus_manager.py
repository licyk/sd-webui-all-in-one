"""Fooocus 管理工具"""

import os
import sys
import json
from pathlib import Path
from typing import Any, Literal

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.notebook_manager.base_manager import BaseManager
from sd_webui_all_in_one.mirror_manager import set_mirror
from sd_webui_all_in_one.env_check.fix_torch import fix_torch_libomp
from sd_webui_all_in_one.utils import warning_unexpected_params
from sd_webui_all_in_one.env_check.fix_numpy import check_numpy
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL
from sd_webui_all_in_one.optimize.cuda_malloc import set_cuda_malloc
from sd_webui_all_in_one.env_manager import configure_env_var, configure_pip
from sd_webui_all_in_one.downloader import MultiThreadDownloader, download_file
from sd_webui_all_in_one.env_check.fix_dependencies import py_dependency_checker
from sd_webui_all_in_one.colab_tools import is_colab_environment, mount_google_drive
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check import check_onnxruntime_gpu
from sd_webui_all_in_one.pkg_manager import install_manager_depend, install_pytorch, install_requirements


logger = get_logger(
    name="Fooocus Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class FooocusManager(BaseManager):
    """Fooocus 管理工具"""

    def mount_drive(
        self,
        extras: list[dict[str, str | bool]] = None,
    ) -> None:
        """挂载 Google Drive 并创建 Fooocus 输出文件夹

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
        默认挂载的目录和文件: `outputs`, `presets`, `language`, `wildcards`, `config.txt`

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

        drive_output = drive_path / "MyDrive" / "fooocus_output"
        fooocus_path = self.workspace / self.workfolder
        links: list[dict[str, str | bool]] = [
            {"link_dir": "outputs"},
            {"link_dir": "presets"},
            {"link_dir": "language"},
            {"link_dir": "wildcards"},
            {"link_dir": "config.txt", "is_file": True},
        ]
        if extras is not None:
            links += extras
        self.link_to_google_drive(
            base_dir=fooocus_path,
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
            (Path | None): 模型保存路径
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
        preset: str | None = None,
        translation: str | None = None,
    ) -> None:
        """下载 Fooocus 配置文件

        Args:
            preset (str | None): Fooocus 预设文件下载链接, 下载后将保存在`{self.workspace}/{self.workfolder}/presets/custom.json`
            path_config (str | None): Fooocus 路径配置文件下载链接, 下载后将保存在`{self.workspace}/{self.workfolder}/config.txt`
            translation (str | None): Fooocus 翻译文件下载链接, 下载后将保存在`{self.workspace}/{self.workfolder}/language/zh.json`
        """
        path = self.workspace / self.workfolder
        preset_path = path / "presets"
        language_path = path / "language"
        logger.info("下载配置文件")
        if preset is not None:
            download_file(url=preset, path=preset_path, save_name="custom.json")
        if translation is not None:
            download_file(url=translation, path=language_path, save_name="zh.json")

    def pre_download_model(
        self,
        path: str | Path,
        thread_num: int | None = 16,
        downloader: Literal["aria2", "request", "mix"] = "mix",
    ) -> None:
        """根据 Fooocus 配置文件预下载模型

        Args:
            path (str | Path): Fooocus 配置文件路径
            thread_num (int | None): 下载模型的线程数
            downloader (Literal["aria2", "request", "mix"]): 预下载模型时使用的下载器 (`aria2`, `request`, `mix`)
        """
        path = Path(path) if not isinstance(path, Path) and path is not None else path
        if path.exists():
            try:
                with open(path, "r", encoding="utf8") as file:
                    data = json.load(file)
            except Exception as e:
                logger.warning("打开 Fooocus 配置文件时出现错误: %s", e)
                data = {}
        else:
            data = {}

        if downloader == "aria2":
            sd_model_downloader = "aria2"
            vae_downloader = "aria2"
            embedding_downloader = "aria2"
            lora_downloader = "aria2"
        elif downloader == "requests":
            sd_model_downloader = "requests"
            vae_downloader = "requests"
            embedding_downloader = "requests"
            lora_downloader = "requests"
        elif downloader == "mix":
            sd_model_downloader = "aria2"
            vae_downloader = "aria2"
            embedding_downloader = "requests"
            lora_downloader = "requests"
        else:
            sd_model_downloader = "aria2"
            vae_downloader = "aria2"
            embedding_downloader = "aria2"
            lora_downloader = "aria2"

        sd_model_list: dict[str, str] = data.get("checkpoint_downloads", {})
        lora_list: dict[str, str] = data.get("lora_downloads", {})
        vae_list: dict[str, str] = data.get("vae_downloads", {})
        embedding_list: dict[str, str] = data.get("embeddings_downloads", {})
        fooocus_path = self.workspace / self.workfolder
        sd_model_path = fooocus_path / "models" / "checkpoints"
        lora_path = fooocus_path / "models" / "loras"
        vae_path = fooocus_path / "models" / "vae"
        embedding_path = fooocus_path / "models" / "embeddings"

        downloader_params: list[dict[str, Any]] = []
        downloader_params += [
            {
                "url": sd_model_list.get(i),
                "path": sd_model_path,
                "save_name": i,
                "tool": sd_model_downloader,
                "progress": True if sd_model_downloader == "aria2" else False,
            }
            for i in sd_model_list
        ]
        downloader_params += [
            {
                "url": lora_list.get(i),
                "path": lora_path,
                "save_name": i,
                "tool": lora_downloader,
                "progress": True if lora_downloader == "aria2" else False,
            }
            for i in lora_list
        ]
        downloader_params += [
            {
                "url": vae_list.get(i),
                "path": vae_path,
                "save_name": i,
                "tool": vae_downloader,
                "progress": True if vae_downloader == "aria2" else False,
            }
            for i in vae_list
        ]
        downloader_params += [
            {
                "url": embedding_list.get(i),
                "path": embedding_path,
                "save_name": i,
                "tool": embedding_downloader,
                "progress": True if embedding_downloader == "aria2" else False,
            }
            for i in embedding_list
        ]

        model_downloader = MultiThreadDownloader(
            download_func=download_file,
            download_kwargs_list=downloader_params,
        )
        model_downloader.start(num_threads=thread_num)
        logger.info("预下载 Fooocus 模型完成")

    def check_env(
        self,
        use_uv: bool | None = True,
        requirements_file: str | None = "requirements_versions.txt",
    ) -> None:
        """检查 Fooocus 运行环境

        Args:
            use_uv (bool | None): 使用 uv 安装依赖
            requirements_file (str | None): 依赖文件名
        """
        sd_webui_path = self.workspace / self.workfolder
        requirement_path = sd_webui_path / requirements_file
        py_dependency_checker(
            requirement_path=requirement_path,
            name="Fooocus",
            use_uv=use_uv,
        )
        fix_torch_libomp()
        check_onnxruntime_gpu(use_uv=use_uv, ignore_ort_install=True)
        check_numpy(use_uv=use_uv)

    def get_launch_command(
        self,
        params: list[str] | str | None = None,
    ) -> str:
        """获取 Fooocus 启动命令

        Args:
            params (list[str] | str | None): 启动 Fooocus 的参数
        Returns:
            str: 完整的启动 Fooocus 的命令
        """
        fooocus_path = self.workspace / self.workfolder
        cmd = [Path(sys.executable).as_posix(), (fooocus_path / "launch.py").as_posix()]
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
        """启动 Fooocus

        Args:
            params (list[str] | str | None): Fooocus 启动参数
            display_mode (Literal["terminal", "jupyter"] | None): 执行子进程时使用的输出模式
        """
        self.launch(
            name="Fooocus",
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
        fooocus_repo: str | None = None,
        fooocus_requirements: str | None = None,
        fooocus_preset: str | None = None,
        fooocus_translation: str | None = None,
        model_downloader: Literal["aria2", "request", "mix"] = "mix",
        download_model_thread: int | None = 16,
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
        """安装 Fooocus

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
            fooocus_repo (str | None): Fooocus 仓库地址
            fooocus_requirements (str | None): Fooocus 依赖文件名
            fooocus_preset (str | None): Fooocus 预设文件下载链接
            fooocus_translation (str | None): Fooocus 翻译文件下载地址
            model_downloader (Literal["aria2", "request", "mix"]): 预下载模型时使用的模型下载器
            download_model_thread (int | None): 预下载模型的线程
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
            message="FooocusManager.install() 接收到不期望参数, 请检查参数输入是否正确",
            args=args,
            kwargs=kwargs,
        )
        logger.info("开始安装 Fooocus")
        if custom_sys_pkg_cmd is False:
            custom_sys_pkg_cmd = []
        elif custom_sys_pkg_cmd is True:
            custom_sys_pkg_cmd = None
        os.chdir(self.workspace)
        fooocus_path = self.workspace / self.workfolder
        fooocus_repo = "https://github.com/lllyasviel/Fooocus" if fooocus_repo is None else fooocus_repo
        fooocus_preset = "https://github.com/licyk/sd-webui-all-in-one/raw/main/config/fooocus_config.json" if fooocus_preset is None else fooocus_preset
        fooocus_translation = "https://github.com/licyk/sd-webui-all-in-one/raw/main/config/fooocus_zh_cn.json" if fooocus_translation is None else fooocus_translation
        requirements_path = fooocus_path / ("requirements_versions.txt" if fooocus_requirements is None else fooocus_requirements)
        config_file = fooocus_path / "presets" / "custom.json"
        if check_avaliable_gpu:
            self.check_avaliable_gpu()
        logger.info("Fooocus 内核分支: %s", fooocus_repo)
        logger.info("Fooocus 预设配置: %s", fooocus_preset)
        logger.info("Fooocus 翻译配置: %s", fooocus_translation)
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
        git_warpper.clone(fooocus_repo, fooocus_path)
        if update_core:
            git_warpper.update(fooocus_path)
        install_pytorch(
            torch_package=torch_ver,
            xformers_package=xformers_ver,
            custom_env=pytorch_mirror,
            use_uv=use_uv,
        )
        install_requirements(
            path=requirements_path,
            use_uv=use_uv,
            cwd=fooocus_path,
        )
        self.install_config(
            preset=fooocus_preset,
            translation=fooocus_translation,
        )
        self.restart_repo_manager(
            hf_token=huggingface_token,
            ms_token=modelscope_token,
        )
        if enable_tcmalloc:
            self.tcmalloc.configure_tcmalloc()
        if enable_cuda_malloc:
            set_cuda_malloc()
        self.pre_download_model(
            path=config_file,
            thread_num=download_model_thread,
            downloader=model_downloader,
        )
        logger.info("Fooocus 安装完成")
