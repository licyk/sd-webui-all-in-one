"""管理工具基础类"""

import re
import subprocess
from pathlib import Path
from typing import Literal

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.tunnel import TunnelManager
from sd_webui_all_in_one.repo_manager import RepoManager
from sd_webui_all_in_one.downloader import download_file, download_archive_and_unpack
from sd_webui_all_in_one.optimize.tcmalloc import TCMalloc
from sd_webui_all_in_one.utils import check_gpu, in_jupyter, clear_up
from sd_webui_all_in_one.colab_tools import is_colab_environment
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL
from sd_webui_all_in_one.file_manager import copy_files, sync_files_and_create_symlink
from sd_webui_all_in_one.kaggle_tools import display_model_and_dataset_dir, import_kaggle_input
from sd_webui_all_in_one.cmd import run_cmd


logger = get_logger(
    name="Base Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class BaseManager:
    """管理工具基础类

    Attributes:
        workspace (Path): 工作区路径
        workfolder (str): 工作区的文件夹名称
        repo (RepoManager): 仓库管理器实例, 用于 HuggingFace / ModelScope 仓库操作
        tun (TunnelManager): 隧道管理器实例, 用于内网穿透
        tcmalloc (TCMalloc): TCMalloc 内存分配器实例
        copy_files (Callable): 文件复制函数引用
        import_kaggle_input (Callable): Kaggle Input 导入函数引用
        display_model_and_dataset_dir (Callable): 展示模型 / 数据集目录函数引用
        clear_up (Callable): 清理 Jupyter 输出函数引用
        download_file (Callable): 文件下载函数引用
        download_archive_and_unpack (Callable): 下载压缩包并解压的函数引用
        run_cmd (Callable): Shell 命令执行函数引用
    """

    def __init__(
        self,
        workspace: str | Path,
        workfolder: str,
        hf_token: str | None = None,
        ms_token: str | None = None,
        port: int | None = 7860,
    ) -> None:
        """管理工具初始化

        Args:
            workspace (str | Path): 工作区路径
            workfolder (str): 工作区的文件夹名称
            hf_token (str | None): HuggingFace Token
            ms_token (str | None): ModelScope Token
            port (int | None): 内网穿透端口
        """
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.workfolder = workfolder
        self.repo = RepoManager(hf_token, ms_token)
        self.tun = TunnelManager(workspace, port)
        self.tcmalloc = TCMalloc(workspace)
        self.copy_files = copy_files
        self.import_kaggle_input = import_kaggle_input
        self.display_model_and_dataset_dir = display_model_and_dataset_dir
        self.clear_up = clear_up
        self.download_file = download_file
        self.download_archive_and_unpack = download_archive_and_unpack
        self.run_cmd = run_cmd

    def restart_repo_manager(
        self,
        hf_token: str | None = None,
        ms_token: str | None = None,
    ) -> None:
        """重新初始化 HuggingFace / ModelScope 仓库管理工具

        Args:
            hf_token (str | None): HugggingFace Token, 不为`None`时配置`HF_TOKEN`环境变量
            ms_token (str | None): ModelScope Token, 不为`None`时配置`MODELSCOPE_API_TOKEN`环境变量
        """
        logger.info("重启 HuggingFace / ModelScope 仓库管理模块")
        self.repo = RepoManager(
            hf_token=hf_token,
            ms_token=ms_token,
        )

    def get_model(
        self,
        url: str,
        path: str | Path,
        filename: str | None = None,
        tool: Literal["aria2", "request"] = "aria2",
        retry: int | None = 3,
    ) -> Path | None:
        """下载模型文件到本地中

        Args:
            url (str): 模型文件的下载链接
            path (str | Path): 模型文件下载到本地的路径
            filename (str | None): 指定下载的模型文件名称
            tool (Literal["aria2", "request"]): 下载工具
            retry (int | None): 重试下载的次数, 默认为 3
        Returns:
            (Path | None): 文件保存路径
        """
        return download_file(url=url, path=path, save_name=filename, tool=tool, retry=retry)

    def get_model_from_list(self, path: str | Path, model_list: list[str, int], retry: int | None = 3) -> None:
        """从模型列表下载模型

        `model_list`需要指定模型下载的链接和下载状态, 例如
        ```python
        model_list = [
            ["url1", 0],
            ["url2", 1],
            ["url3", 0],
            ["url4", 1, "file.safetensors"]
        ]
        ```

        在这个例子中, 第一个参数指定了模型的下载链接, 第二个参数设置了是否要下载这个模型, 当这个值为 1 时则下载该模型

        第三个参数是可选参数, 用于指定下载到本地后的文件名称

        则上面的例子中`url2`和`url4`下载链接所指的文件将被下载, 并且`url4`所指的文件将被重命名为`file.safetensors`

        Args:
            path (str | Path): 将模型下载到的本地路径
            model_list (list[str | int]): 模型列表
            retry (int | None): 重试下载的次数, 默认为 3
        """
        for model in model_list:
            try:
                url = model[0]
                status = model[1]
                filename = model[2] if len(model) > 2 else None
            except Exception as e:
                logger.error("模型下载列表长度不合法: %s\n出现异常的列表:%s", e, model)
                continue
            if status >= 1:
                if filename is None:
                    self.get_model(url=url, path=path, retry=retry)
                else:
                    self.get_model(url=url, path=path, filename=filename, retry=retry)

    def check_avaliable_gpu(self) -> bool:
        """检测当前环境是否有 GPU

        Returns:
            bool: 环境有可用 GPU 时返回`True`
        Raises:
            RuntimeError: 环境中无 GPU 时引发错误
        """
        if not check_gpu():
            if is_colab_environment():
                notice = "没有可用的 GPU, 请在 Colab -> 代码执行程序 > 更改运行时类型 -> 硬件加速器 选择 GPU T4\n如果不能使用 GPU, 请尝试更换账号!"
            else:
                notice = "没有可用的 GPU, 请在 kaggle -> Notebook -> Session options -> ACCELERATOR 选择 GPU T4 x 2\n如果不能使用 GPU, 请检查 Kaggle 账号是否绑定了手机号或者尝试更换账号!"

            raise RuntimeError(notice)
        return True

    def link_to_google_drive(
        self,
        base_dir: Path,
        drive_path: Path,
        links: list[dict[str, str | bool]],
    ) -> None:
        """将 Colab 中的文件夹 / 文件链接到 Google Drive 中

        挂载额外目录需要使用`link_dir`指定要挂载的路径, 并且使用相对路径指定

        若额外链接路径为文件, 需指定`is_file`属性为`True`

        例如:
        ```python
        links = [
            {"link_dir": "models/loras"},
            {"link_dir": "custom_nodes"},
            {"link_dir": "extra_model_paths.yaml", "is_file": True},
        ]
        ```

        Args:
            base_dir (Path): 链接的根路径
            drive_path (Path): 链接到的 Google Drive 的路径
            links (list[dict[str, str | bool]]): 要进行链接文件的路径表
        """
        for link in links:
            link_dir = link.get("link_dir")
            is_file = link.get("is_file", False)
            if link_dir is None:
                continue
            full_link_path = base_dir / link_dir
            full_drive_path = drive_path / link_dir
            if is_file and (not full_link_path.exists() and not full_drive_path.exists()):
                # 链接路径指定的是文件并且源文件和链接文件都不存在时则取消链接
                continue
            sync_files_and_create_symlink(
                src_path=full_drive_path,
                link_path=full_link_path,
                src_is_file=is_file,
            )

    def parse_arguments(self, launch_args: str) -> list[str]:
        """解析命令行参数字符串，返回参数列表

        Args:
            launch_args (str): 命令行参数字符串

        Returns:
            list[str]: 解析后的参数列表
        """
        if not launch_args:
            return []

        # 去除首尾空格
        trimmed_args = launch_args.strip()

        # 如果参数数量 <= 1, 使用简单分割
        if len(trimmed_args.split()) <= 1:
            arguments = trimmed_args.split()
        else:
            # 使用正则表达式处理复杂情况 (包含引号的参数)
            pattern = r'("[^"]*"|\'[^\']*\'|\S+)'
            matches = re.findall(pattern, trimmed_args)

            # 去除参数两端的引号
            arguments = [match.strip("\"'") for match in matches]

        return arguments

    def launch(
        self,
        name: str,
        base_path: Path | str,
        cmd: list[str],
        display_mode: Literal["terminal", "jupyter"] | None = None,
    ) -> None:
        """启动 WebUI

        Args:
            name (str): 启动的名称
            base_path (Path | str): 启动时得的根目录
            params (list[str] | str | None): 启动 WebUI 的参数
            display_mode (Literal["terminal", "jupyter"] | None): 执行子进程时使用的输出模式
        """

        if display_mode is None:
            if in_jupyter():
                display_mode = "jupyter"
            else:
                display_mode = "terminal"
        logger.info("启动 %s 中", name)
        try:
            if display_mode == "jupyter":
                with subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    text=True,
                    shell=True,
                    cwd=base_path,
                    encoding="utf-8",
                    errors="replace",
                ) as p:
                    for line in p.stdout:
                        print(line, end="", flush=True)
            elif display_mode == "terminal":
                subprocess.run(
                    cmd,
                    shell=True,
                    cwd=base_path,
                    encoding="utf-8",
                    errors="replace",
                )
            else:
                logger.error("未知的显示模式: %s", display_mode)
        except KeyboardInterrupt:
            logger.info("关闭 %s", name)
