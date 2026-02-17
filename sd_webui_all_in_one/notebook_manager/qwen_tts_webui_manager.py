"""Qwen TTS WebUI 管理工具"""

import os
import sys
from pathlib import Path
from typing import Literal

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.notebook_manager.base_manager import BaseManager
from sd_webui_all_in_one.mirror_manager import set_mirror
from sd_webui_all_in_one.pytorch_manager.base import PyTorchDeviceType
from sd_webui_all_in_one.utils import warning_unexpected_params
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.optimize.cuda_malloc import set_cuda_malloc
from sd_webui_all_in_one.env_manager import configure_env_var, configure_pip
from sd_webui_all_in_one.pkg_manager import install_manager_depend
from sd_webui_all_in_one.base_manager.qwen_tts_webui_base import install_qwen_tts_webui, update_qwen_tts_webui, check_qwen_tts_webui_env

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class QwenTTSWebUIManager(BaseManager):
    """Qwen TTS WebUI 管理工具"""

    def mount_drive(
        self,
        extras: list[dict[str, str | bool]] = None,
    ) -> None:
        """挂载 Google Drive 并创建 Qwen TTS WebUI 输出文件夹

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
        默认挂载的目录和文件: `outputs`, `config.json`

        Args:
            extras (list[dict[str, str | bool]]): 挂载额外目录
        """
        if not self.mount_google_drive_for_notebook():
            return

        drive_output = Path("/content/drive") / "MyDrive" / "qwen_tts_webui_output"
        qwen_tts_webui_path = self.workspace / self.workfolder
        links: list[dict[str, str | bool]] = [
            {"link_dir": "outputs"},
            {"link_dir": "config.json", "is_file": True},
        ]
        if extras is not None:
            links += extras
        self.link_to_google_drive(
            base_dir=qwen_tts_webui_path,
            drive_path=drive_output,
            links=links,
        )

    def check_env(
        self,
        use_uv: bool | None = True,
        use_pypi_mirror: bool | None = False,
        use_github_mirror: bool | None = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> None:
        """检查 Qwen TTS WebUI 运行环境

        Args:
            use_uv (bool | None):
                是否使用 uv 安装 Python 软件包
            use_pypi_mirror (bool | None):
                是否使用 PyPI 镜像源
            use_github_mirror (bool | None):
                是否使用 Github 镜像源
            custom_github_mirror (str | list[str] | None):
                自定义 Github 镜像源
        """
        check_qwen_tts_webui_env(
            qwen_tts_webui_path=self.workspace / self.workfolder,
            use_uv=use_uv,
            use_pypi_mirror=use_pypi_mirror,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
        )

    def get_launch_command(
        self,
        params: list[str] | str | None = None,
    ) -> str:
        """获取 Qwen TTS WebUI 启动命令

        Args:
            params (list[str] | str | None): 启动 Qwen TTS WebUI 的参数
        Returns:
            str: 完整的启动 Qwen TTS WebUI 的命令
        """
        qwen_tts_webui_path = self.workspace / self.workfolder
        cmd = [Path(sys.executable).as_posix(), (qwen_tts_webui_path / "launch.py").as_posix()]
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
        """启动 Qwen TTS WebUI

        Args:
            params (list[str] | str | None): Qwen TTS WebUI 启动参数
            display_mode (Literal["terminal", "jupyter"] | None): 执行子进程时使用的输出模式
        """
        self.launch(
            name="Qwen TTS WebUI",
            base_path=self.workspace / self.workfolder,
            cmd=self.get_launch_command(params),
            display_mode=display_mode,
        )

    def install(
        self,
        pytorch_mirror_type: PyTorchDeviceType | None = None,
        custom_pytorch_package: str | None = None,
        custom_xformers_package: str | None = None,
        use_pypi_mirror: bool | None = False,
        use_uv: bool | None = True,
        use_github_mirror: bool | None = False,
        custom_github_mirror: str | list[str] | None = None,
        use_cn_model_mirror: bool | None = False,
        # legecy
        use_hf_mirror: bool | None = False,
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list[str] | None = None,
        huggingface_mirror: str | None = None,
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
        """安装 Qwen TTS WebUI

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
            use_cn_model_mirror (bool | None):
                是否使用国内镜像下载模型
            use_hf_mirror (bool | None):
                是否启用 HuggingFace 镜像源
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
            message="QwenTTSWebUIManager.install() 接收到不期望参数, 请检查参数输入是否正确",
            args=args,
            kwargs=kwargs,
        )
        logger.info("开始安装 Qwen TTS WebUI")
        if custom_sys_pkg_cmd is False:
            custom_sys_pkg_cmd = []
        elif custom_sys_pkg_cmd is True:
            custom_sys_pkg_cmd = None

        os.chdir(self.workspace)
        qwen_tts_webui_path = self.workspace / self.workfolder

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

        install_qwen_tts_webui(
            qwen_tts_webui_path=qwen_tts_webui_path,
            pytorch_mirror_type=pytorch_mirror_type,
            custom_pytorch_package=custom_pytorch_package,
            custom_xformers_package=custom_xformers_package,
            use_pypi_mirror=use_pypi_mirror,
            use_uv=use_uv,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
            use_cn_model_mirror=use_cn_model_mirror,
        )

        if update_core:
            update_qwen_tts_webui(
                qwen_tts_webui_path=qwen_tts_webui_path,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
            )

        self.restart_repo_manager(
            hf_token=huggingface_token,
            ms_token=modelscope_token,
        )

        if enable_tcmalloc:
            self.tcmalloc_manager.configure_tcmalloc()

        if enable_cuda_malloc:
            set_cuda_malloc()

        logger.info("Qwen TTS WebUI 安装完成")
