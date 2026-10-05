"""RVC Next WebUI 管理工具"""

import os
import sys
from pathlib import Path
from typing import Literal

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.notebook_manager.base_manager import BaseManager
from sd_webui_all_in_one.mirror_manager import set_mirror
from sd_webui_all_in_one.pytorch_manager import PyTorchDeviceType
from sd_webui_all_in_one.utils import warning_unexpected_params
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.optimize import set_cuda_malloc
from sd_webui_all_in_one.env_manager import (
    configure_env_var,
    configure_pip,
)
from sd_webui_all_in_one.pkg_manager import install_manager_depend
from sd_webui_all_in_one.base_manager import (
    install_rvc_next_webui,
    update_rvc_next_webui,
    check_rvc_next_webui_env,
)
from sd_webui_all_in_one.base_manager.rvc_next_webui_base.runtime import (
    apply_rvc_next_hf_mirror,
    apply_rvc_next_managed_launch_args,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class RvcNextWebUIManager(BaseManager):
    """RVC Next WebUI 管理工具"""

    def __init__(
        self,
        workspace: str | Path,
        workfolder: str,
        hf_token: str | None = None,
        ms_token: str | None = None,
        port: int = 7868,
    ) -> None:
        """管理工具初始化

        Args:
            workspace (str | Path):
                工作区路径
            workfolder (str):
                工作区的文件夹名称
            hf_token (str | None):
                HuggingFace Token
            ms_token (str | None):
                ModelScope Token
            port (int):
                内网穿透端口, 同时作为 RVC Next WebUI 的监听端口
        """
        super().__init__(
            workspace=workspace,
            workfolder=workfolder,
            hf_token=hf_token,
            ms_token=ms_token,
            port=port,
        )
        self.port = port

    def mount_drive(
        self,
        extras: list[dict[str, str | bool]] | None = None,
    ) -> None:
        """挂载 Google Drive 并创建 RVC Next WebUI 输出文件夹

        挂载额外目录需要使用`link_dir`指定要挂载的路径, 并且使用相对路径指定

        相对路径的起始位置为`{self.workspace}/{self.workfolder}`

        若额外链接路径为文件, 需指定`is_file`属性为`True`

        例如:
        ```python
        extras = [
            {"link_dir": "cache"},
        ]
        ```
        默认挂载的目录: `data` (RVC Next 的设置, 数据库, 模型, 实验和输出)

        Args:
            extras (list[dict[str, str | bool]] | None): 挂载额外目录
        """
        if not self.mount_google_drive_for_notebook():
            return

        drive_output = Path("/content/drive") / "MyDrive" / "rvc_next_webui_output"
        rvc_next_webui_path = self.workspace / self.workfolder
        links: list[dict[str, str | bool]] = [
            {"link_dir": "data"},
        ]
        if extras is not None:
            links += extras
        self.link_to_google_drive(
            base_dir=rvc_next_webui_path,
            drive_path=drive_output,
            links=links,
        )

    def check_env(
        self,
        use_uv: bool = True,
        use_pypi_mirror: bool = False,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
        include_checks: list[str] | None = None,
        exclude_checks: list[str] | None = None,
    ) -> None:
        """检查 RVC Next WebUI 运行环境

        Args:
            use_uv (bool):
                是否使用 uv 安装 Python 软件包
            use_pypi_mirror (bool):
                是否使用 PyPI 镜像源
            use_github_mirror (bool):
                是否使用 Github 镜像源
            custom_github_mirror (str | list[str] | None):
                自定义 Github 镜像源
            include_checks (list[str] | None):
                仅执行的环境检查任务名称。
            exclude_checks (list[str] | None):
                跳过的环境检查任务名称。
        """
        check_rvc_next_webui_env(
            rvc_next_webui_path=self.workspace / self.workfolder,
            use_uv=use_uv,
            use_pypi_mirror=use_pypi_mirror,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
            include_checks=include_checks,
            exclude_checks=exclude_checks,
        )

    def get_launch_command(
        self,
        params: list[str] | str | None = None,
    ) -> str:
        """获取 RVC Next WebUI 启动命令

        未指定 ``--port`` 时使用内网穿透端口并启用 ``--strict-port``, 保证 RVC Next WebUI 的监听端口和内网穿透端口一致.

        Args:
            params (list[str] | str | None): 启动 RVC Next WebUI 的参数
        Returns:
            str: 完整的启动 RVC Next WebUI 的命令
        """
        rvc_next_webui_path = self.workspace / self.workfolder
        args: list[str] = []
        if params is not None:
            args = self.parse_cmd_str_to_list(params) if isinstance(params, str) else list(params)
        if "--port" not in args:
            args += ["--port", str(self.port), "--strict-port"]
        if "--no-browser" not in args:
            args.append("--no-browser")
        cmd = [Path(sys.executable).as_posix(), (rvc_next_webui_path / "launch.py").as_posix()]
        cmd += apply_rvc_next_managed_launch_args(args)
        return self.parse_cmd_list_to_str(cmd)

    def apply_hf_mirror_env(self) -> None:
        """将已设置的 HuggingFace 镜像源 (``HF_ENDPOINT``) 应用到 RVC Next 的下载设置"""
        os.environ.update(apply_rvc_next_hf_mirror(dict(os.environ)))

    def run(
        self,
        params: list[str] | str | None = None,
        display_mode: Literal["terminal", "jupyter"] | None = None,
    ) -> None:
        """启动 RVC Next WebUI

        Args:
            params (list[str] | str | None): RVC Next WebUI 启动参数
            display_mode (Literal["terminal", "jupyter"] | None): 执行子进程时使用的输出模式
        """
        self.apply_hf_mirror_env()
        self.launch(
            name="RVC Next WebUI",
            base_path=self.workspace / self.workfolder,
            cmd=self.get_launch_command(params),
            display_mode=display_mode,
        )

    def install(
        self,
        pytorch_mirror_type: PyTorchDeviceType | None = None,
        custom_pytorch_package: str | None = None,
        use_pypi_mirror: bool = False,
        use_uv: bool = True,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
        # legecy
        use_hf_mirror: bool = False,
        pypi_index_mirror: str | None = None,
        pypi_extra_index_mirror: str | None = None,
        pypi_find_links_mirror: str | None = None,
        github_mirror: str | list[str] | None = None,
        huggingface_mirror: str | None = None,
        check_avaliable_gpu: bool = False,
        enable_tcmalloc: bool = True,
        enable_cuda_malloc: bool = True,
        custom_sys_pkg_cmd: list[list[str]] | list[str] | bool | None = None,
        huggingface_token: str | None = None,
        modelscope_token: str | None = None,
        update_core: bool = True,
        *args,
        **kwargs,
    ) -> None:
        """安装 RVC Next WebUI

        Args:
            pytorch_mirror_type (PyTorchDeviceType | None):
                设置使用的 PyTorch 镜像源类型
            custom_pytorch_package (str | None):
                自定义 PyTorch 软件包版本声明, 例如: `torch==2.8.0+cu128 torchvision==0.23.0+cu128`
            use_pypi_mirror (bool):
                是否使用国内 PyPI 镜像源
            use_uv (bool):
                是否使用 uv 安装 Python 软件包
            use_github_mirror (bool):
                是否使用 Github 镜像源
            custom_github_mirror (str | list[str] | None):
                自定义 Github 镜像源
            use_hf_mirror (bool):
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
            check_avaliable_gpu (bool):
                是否检查可用的 GPU, 当检查时没有可用 GPU 将引发`Exception`
            enable_tcmalloc (bool):
                是否启用 TCMalloc 内存优化
            enable_cuda_malloc (bool):
                启用 CUDA 显存优化
            custom_sys_pkg_cmd (list[list[str]] | list[str] | bool | None):
                自定义调用系统包管理器命令, 设置为 None 为使用默认的调用命令, 设置为 [] 则禁用该功能
            huggingface_token (str | None):
                配置 HuggingFace Token
            modelscope_token (str | None):
                配置 ModelScope Token
            update_core (bool):
                安装时更新内核
            *args:
                兼容旧接口的额外位置参数
            **kwargs:
                兼容旧接口的额外关键字参数
        """
        warning_unexpected_params(
            message="RvcNextWebUIManager.install() 接收到不期望参数, 请检查参数输入是否正确",
            args=args,
            kwargs=kwargs,
        )
        logger.info("开始安装 RVC Next WebUI")
        if custom_sys_pkg_cmd is False:
            custom_sys_pkg_cmd = []
        elif custom_sys_pkg_cmd is True:
            custom_sys_pkg_cmd = None

        os.chdir(self.workspace)
        rvc_next_webui_path = self.workspace / self.workfolder

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

        install_rvc_next_webui(
            rvc_next_webui_path=rvc_next_webui_path,
            pytorch_mirror_type=pytorch_mirror_type,
            custom_pytorch_package=custom_pytorch_package,
            use_pypi_mirror=use_pypi_mirror,
            use_uv=use_uv,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
        )

        if update_core:
            update_rvc_next_webui(
                rvc_next_webui_path=rvc_next_webui_path,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
            )

        self.repo_manager.configure_tokens(
            hf_token=huggingface_token,
            ms_token=modelscope_token,
        )

        if enable_tcmalloc:
            self.tcmalloc_manager.configure_tcmalloc()

        if enable_cuda_malloc:
            set_cuda_malloc()

        logger.info("RVC Next WebUI 安装完成")
