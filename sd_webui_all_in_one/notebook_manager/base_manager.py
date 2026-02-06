"""管理工具基础类"""

import os
import subprocess
import shlex
import traceback
from pathlib import Path
from typing import Literal

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.pytorch_manager.pytorch_mirror import get_gpu_list, has_gpus
from sd_webui_all_in_one.tunnel import TunnelManager
from sd_webui_all_in_one.repo_manager import ApiType, RepoManager, RepoType
from sd_webui_all_in_one.downloader import DownloadToolType, download_file, download_archive_and_unpack
from sd_webui_all_in_one.optimize.tcmalloc import TCMalloc
from sd_webui_all_in_one.utils import in_jupyter, clear_jupyter_output, print_divider
from sd_webui_all_in_one.colab_tools import is_colab_environment, mount_google_drive
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL
from sd_webui_all_in_one.file_operations.file_manager import copy_files, display_directories, remove_files, move_files, sync_files_and_create_symlink
from sd_webui_all_in_one.kaggle_tools import import_kaggle_input
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
        remove_files (Callable): 删除文件函数引用
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
        self.repo_manager = RepoManager(hf_token, ms_token)
        self.tun_manager = TunnelManager(self.workspace, port)
        self.tcmalloc_manager = TCMalloc(self.workspace)
        self.copy_files = copy_files
        self.remove_files = remove_files
        self.move_files = move_files
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
        self.repo_manager = RepoManager(
            hf_token=hf_token,
            ms_token=ms_token,
        )

    def get_model(
        self,
        url: str,
        path: str | Path,
        filename: str | None = None,
        tool: DownloadToolType = "aria2",
    ) -> Path | None:
        """下载模型文件到本地中

        Args:
            url (str):
                模型文件的下载链接
            path (str | Path):
                模型文件下载到本地的路径
            filename (str | None):
                指定下载的模型文件名称
            tool (DownloadToolType):
                下载工具

        Returns:
            (Path | None): 文件保存路径
        """
        try:
            return download_file(url=url, path=Path(path), save_name=filename, tool=tool)
        except Exception as e:
            traceback.print_exc()
            logger.error("下载 '%s' 到 '%s' 时发生错误: %s", url, path, e)
            return None

    def get_model_from_list(
        self,
        path: str | Path,
        model_list: list[str, int],
    ) -> None:
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
                    self.get_model(url=url, path=path)
                else:
                    self.get_model(url=url, path=path, filename=filename)

    def check_avaliable_gpu(
        self,
    ) -> bool:
        """检测当前环境是否有 GPU

        Returns:
            bool:
                环境有可用 GPU 时返回`True`

        Raises:
            RuntimeError:
                环境中无 GPU 时引发错误
        """
        if not has_gpus(get_gpu_list()):
            if is_colab_environment():
                notice = "没有可用的 GPU, 请在 Colab -> 代码执行程序 > 更改运行时类型 -> 硬件加速器 选择 GPU T4\n如果不能使用 GPU, 请尝试更换账号!"
            else:
                notice = "没有可用的 GPU, 请在 kaggle -> Notebook -> Session options -> ACCELERATOR 选择 GPU T4 x 2\n如果不能使用 GPU, 请检查 Kaggle 账号是否绑定了手机号或者尝试更换账号!"

            raise RuntimeError(notice)
        return True

    def link_to_google_drive(
        self,
        base_dir: str | Path,
        drive_path: str | Path,
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
            base_dir (Path | str): 链接的根路径
            drive_path (Path | str): 链接到的 Google Drive 的路径
            links (list[dict[str, str | bool]]): 要进行链接文件的路径表
        """
        for link in links:
            link_dir = link.get("link_dir")
            is_file = link.get("is_file", False)
            if link_dir is None:
                continue
            full_link_path = Path(base_dir) / link_dir
            full_drive_path = Path(drive_path) / link_dir
            if is_file and (not full_link_path.exists() and not full_drive_path.exists()):
                # 链接路径指定的是文件并且源文件和链接文件都不存在时则取消链接
                continue
            try:
                sync_files_and_create_symlink(
                    src_path=full_drive_path,
                    link_path=full_link_path,
                    src_is_file=is_file,
                )
            except Exception as e:
                traceback.print_exc()
                logger.error("链接文件时发生错误: %s", e)

    def parse_cmd_str_to_list(self, launch_args: str) -> list[str]:
        """解析命令行参数字符串，返回参数列表

        Args:
            launch_args (str): 命令行参数字符串

        Returns:
            list[str]: 解析后的参数列表
        """
        return shlex.split(launch_args)

    def parse_cmd_list_to_str(self, cmd_list: list[str]) -> str:
        """将命令列表转换为命令字符串

        Args:
            cmd_list (list[str]): 命令列表

        Returns:
            str: 命令字符串
        """
        return shlex.join(cmd_list)

    def launch(
        self,
        name: str,
        base_path: Path | str,
        cmd: list[str] | str,
        display_mode: Literal["terminal", "jupyter"] | None = None,
    ) -> None:
        """启动 WebUI

        Args:
            name (str): 启动的名称
            base_path (Path | str): 启动时得的根目录
            cmd (list[str] | str | None): 启动 WebUI 的参数
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

    def get_pytorch_mirror_env(
        self,
        mirror_url: str | None = None,
    ) -> dict[str, str]:
        """获取包含 PyTorch 镜像源配置的环境变量字典

        Args:
            mirror_url (str | None):
                PyTorch 镜像源地址

        Returns:
            (dict[str, str]):
                包含 PyTorch 镜像源配置的环境变量字典
        """
        custom_env = os.environ.copy()
        if mirror_url is None:
            return custom_env

        custom_env["PIP_INDEX_URL"] = mirror_url
        custom_env["UV_DEFAULT_INDEX"] = mirror_url
        custom_env.pop("PIP_EXTRA_INDEX_URL", None)
        custom_env.pop("UV_INDEX", None)
        custom_env.pop("PIP_FIND_LINKS", None)
        custom_env.pop("UV_FIND_LINKS", None)

        return custom_env

    def mount_google_drive_for_notebook(
        self,
    ) -> bool:
        """挂载 Google Drive

        Returns:
            bool:
                当挂载 Google Drive 成功时

        Raises:
            RuntimeError: 挂载 Google Drive 失败
        """
        if not is_colab_environment():
            logger.warning("当前环境非 Colab, 无法挂载 Google Drive")
            return False

        drive_path = Path("/content/drive")
        if not (drive_path / "MyDrive").exists():
            try:
                mount_google_drive(drive_path)
                return True
            except RuntimeError as e:
                raise RuntimeError(f"挂载 Google Drive 失败, 请尝试重新挂载 Google Drive: {e}") from e

        return True

    def download_and_extract(
        self,
        url: str,
        local_dir: Path | str,
        name: str | None = None,
    ) -> None:
        """下载压缩包并解压到指定路径

        Args:
            url (str):
                压缩包下载链接, 压缩包支持的格式: .zip, .7z, .rar, .tar, .tar.Z, .tar.lz, .tar.lzma, .tar.bz2, .tar.7z, .tar.gz, .tar.xz, .tar.zst
            local_dir (Path | str):
                下载路径
            name (str | None):
                下载文件保存的名称, 为`None`时从`url`解析文件名
        """
        download_archive_and_unpack(
            url=url,
            local_dir=Path(local_dir),
            name=name,
        )

    def upload_files_to_repo(
        self,
        api_type: ApiType,
        repo_id: str,
        upload_path: Path | str,
        repo_type: RepoType = "model",
        visibility: bool | None = False,
    ) -> None:
        """上传文件夹中的内容到 HuggingFace / ModelScope 仓库中

        Args:
            api_type (ApiType):
                Api 类型
            repo_id (str):
                仓库 ID
            repo_type (RepoType):
                仓库类型
            upload_path (Path | str):
                要上传的文件夹
            visibility (bool | None):
                当仓库不存在时自动创建的仓库的可见性
            retry (int | None):
                上传重试次数
        """
        self.repo_manager.upload_files_to_repo(
            api_type=api_type,
            repo_id=repo_id,
            upload_path=Path(upload_path),
            repo_type=repo_type,
            visibility=visibility,
        )

    def download_files_from_repo(
        self,
        api_type: ApiType,
        repo_id: str,
        local_dir: Path | str,
        repo_type: RepoType = "model",
        folder: str | None = None,
        num_threads: int | None = 16,
    ) -> None:
        """从 HuggingFace / ModelScope 仓库下载文文件

        `folder`参数未指定时, 则下载 HuggingFace / ModelScope 仓库中的所有文件, 如果`folder`参数指定了, 例如指定的是`aaaki`

        而仓库的文件结构如下:

        ```markdown
        HuggingFace / ModelScope Repositories
        ├── Nachoneko
        │   ├── 1_nachoneko
        │   │       ├── [メロンブックス (よろず)]Melonbooks Girls Collection 2019 winter 麗.png
        │   │       ├── [メロンブックス (よろず)]Melonbooks Girls Collection 2019 winter 麗.txt
        │   │       ├── [メロンブックス (よろず)]Melonbooks Girls Collection 2020 spring 彩 (オリジナル).png
        │   │       └── [メロンブックス (よろず)]Melonbooks Girls Collection 2020 spring 彩 (オリジナル).txt
        │   ├── 2_nachoneko
        │   │       ├── 0(8).txt
        │   │       ├── 0(8).webp
        │   │       ├── 001_2.png
        │   │       └── 001_2.txt
        │   └── 4_nachoneko
        │           ├── 0b1c8893-c9aa-49e5-8769-f90c4b6866f5.png
        │           ├── 0b1c8893-c9aa-49e5-8769-f90c4b6866f5.txt
        │           ├── 0d5149dd-3bc1-484f-8c1e-a1b94bab3be5.png
        │           └── 0d5149dd-3bc1-484f-8c1e-a1b94bab3be5.txt
        └ aaaki
            ├── 1_aaaki
            │   ├── 1.png
            │   ├── 1.txt
            │   ├── 11.png
            │   ├── 11.txt
            │   ├── 12.png
            │   └── 12.txt
            └── 3_aaaki
                ├── 14.png
                ├── 14.txt
                ├── 16.png
                └── 16.txt
        ```

        则使用该函数下载 HuggingFace / ModelScope 仓库的文件时将下载`aaaki`文件夹中的所有文件, 而`Nachoneko`文件夹中的文件不会被下载

        `folder`参数使用的是前缀匹配方式, 从路径的开头的字符串进行匹配, 匹配成功则进行下载

        如果要指定下载某个文件, 则`folder`参数需要指定该文件在仓库中的完整路径, 比如`aaaki/1_aaaki/1.png`, 此时只会下载该文件, 其他文件不会被下载

        文件下载下来后, 保存路径为`local_dir/<文件在仓库中的路径>`, 比如`local_dir`为`/kaggle/dataset`, 上面下载单个文件的例子下载下载下来的文件就会保存在`/kaggle/dataset/aaaki/1_aaaki/1.png`

        Args:
            api_type (ApiType):
                Api 类型
            repo_id (str):
                仓库 ID
            repo_type (RepoType):
                仓库类型
            local_dir (Path | str):
                下载路径
            folder (str | None):
                指定下载某个文件夹, 未指定时则下载整个文件夹
            num_threads (int | None):
                下载线程
        """
        self.repo_manager.download_files_from_repo(
            api_type=api_type,
            repo_id=repo_id,
            local_dir=Path(local_dir),
            repo_type=repo_type,
            folder=folder,
            num_threads=num_threads,
        )

    def clear_output(self) -> None:
        """清理 Jupyter Notebook 的输出"""
        clear_jupyter_output()

    def get_tunnel_url(
        self,
        use_ngrok: bool | None = False,
        ngrok_token: str | None = None,
        use_cloudflare: bool | None = False,
        use_remote_moe: bool | None = False,
        use_localhost_run: bool | None = False,
        use_gradio: bool | None = False,
        use_pinggy_io: bool | None = False,
        use_zrok: bool | None = False,
        zrok_token: str | None = None,
        webui_name: str | None = "WebUI",
    ) -> None:
        """获取内网穿透地址

        Args:
            use_ngrok (bool | None):
                启用 Ngrok 内网穿透
            ngrok_token (str | None):
                Ngrok 账号 Token
            use_cloudflare (bool | None):
                启用 CloudFlare 内网穿透
            use_remote_moe (bool | None):
                启用 remote.moe 内网穿透
            use_localhost_run (bool | None):
                使用 localhost.run 内网穿透
            use_gradio (bool | None):
                使用 Gradio 内网穿透
            use_pinggy_io (bool | None):
                使用 pinggy.io 内网穿透
            use_zrok (bool | None):
                使用 Zrok 内网穿透
            zrok_token (str | None):
                Zrok 账号 Token
            check (bool | None):
                检查内网穿透是否启动成功
            webui_name (str | None):
                WebUI 的名称
        """
        logger.info("为 %s 启动内网穿透", webui_name)
        tun = self.tun_manager.start_tunnel(
            use_ngrok=use_ngrok,
            ngrok_token=ngrok_token,
            use_cloudflare=use_cloudflare,
            use_remote_moe=use_remote_moe,
            use_localhost_run=use_localhost_run,
            use_gradio=use_gradio,
            use_pinggy_io=use_pinggy_io,
            use_zrok=use_zrok,
            zrok_token=zrok_token,
            check=False,
        )
        logger.info("内网穿透启动完成")
        print_divider("=")
        print(f"原 {webui_name} 访问地址: {tun['local_url']}")
        print(f"{webui_name} 的内网穿透地址: ")
        for k, v in tun.items():
            print(f"- {k}: {v}")
        print_divider("=")

    def download_file_from_url(
        self,
        url: str,
        path: Path | str | None = None,
        save_name: str | None = None,
        tool: DownloadToolType | None = "aria2",
    ) -> Path:
        """从链接中下载文件

        Args:
            url (str):
                文件下载链接
            path (Path | None):
                文件下载路径
            save_name (str | None):
                文件保存名称
            tool (DownloadToolType | None):
                下载工具
        """
        return download_file(
            url=url,
            path=Path(path) if isinstance(path, str) else path,
            save_name=save_name,
            tool=tool,
        )

    def display_directories_tree(
        self,
        *paths: Path | str | None,
        recursive: bool | None = False,
        show_hidden: bool | None = True,
    ) -> None:
        """列出多个指定文件夹的文件列表

        Args:
            *paths (Path | None):
                要展示的一个或多个路径
            recursive (bool | None):
                递归显示子目录的内容
            show_hidden (bool | None):
                显示隐藏文件
        """
        paths = [Path(p) for p in paths]
        display_directories(
            *paths,
            recursive=recursive,
            show_hidden=show_hidden,
        )

    def import_file_from_kaggle_input(
        self,
        output_path: str | Path,
    ) -> None:
        """从 Kaggle Input 文件夹中导入文件

        Args:
            output_path (Path):
                导出文件的路径
        """
        import_kaggle_input(Path(output_path))
