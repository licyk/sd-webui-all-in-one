"""管理工具基础类"""

import os
import subprocess
import shlex
import traceback
from pathlib import Path
from typing import Literal, TypeAlias, TypedDict

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.pytorch_manager import (
    get_gpu_list,
    has_gpus,
)
from sd_webui_all_in_one.tunnel import (
    TunnelManager,
    TunnelUrl,
)
from sd_webui_all_in_one.repo_manager import (
    ApiType,
    RepoManager,
    RepoType,
)
from sd_webui_all_in_one.downloader import (
    DownloadToolType,
    download_file,
    download_archive_and_unpack,
)
from sd_webui_all_in_one.optimize import TCMalloc
from sd_webui_all_in_one.utils import (
    in_jupyter,
    clear_jupyter_output,
    print_divider,
)
from sd_webui_all_in_one.colab_tools import (
    get_colab_secret as _get_colab_secret,
    is_colab_environment,
    mount_google_drive,
)
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
    RETRY_TIMES,
)
from sd_webui_all_in_one.file_manager import (
    copy_files,
    display_directories,
    remove_files,
    move_files,
    sync_files_and_create_symlink,
)
from sd_webui_all_in_one.kaggle_tools import (
    get_kaggle_secret as _get_kaggle_secret,
    import_kaggle_input,
)
from sd_webui_all_in_one.cmd import run_cmd

SecretType = Literal["colab", "kaggle"]
ModelListItem: TypeAlias = list[str | int] | tuple[str | int, ...]


class ModelDownloadDictRequired(TypedDict):
    """模型下载字典的必填字段。"""

    url: str


class ModelDownloadDict(ModelDownloadDictRequired, total=False):
    """模型下载字典的可选字段。"""

    status: str | int
    filename: str


ModelDownloadList: TypeAlias = list[ModelListItem | ModelDownloadDict]


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class BaseManager:
    """管理工具基础类

    Attributes:
        workspace (Path):
            工作区路径
        workfolder (str):
            工作区的文件夹名称
        repo (RepoManager):
            仓库管理器实例, 用于 HuggingFace / ModelScope 仓库操作
        tun (TunnelManager):
            隧道管理器实例, 用于内网穿透
        tcmalloc (TCMalloc):
            TCMalloc 内存分配器实例
        copy_files (Callable):
            文件复制函数引用
        remove_files (Callable):
            删除文件函数引用
        move_files (Callable):
            移动文件函数引用
        run_cmd (Callable):
            Shell 命令执行函数引用
    """

    def __init__(
        self,
        workspace: str | Path,
        workfolder: str,
        hf_token: str | None = None,
        ms_token: str | None = None,
        port: int = 7860,
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
                内网穿透端口
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

    def stop_all_tunnels(
        self,
    ) -> None:
        """停止所有内网穿透

        终止所有已启动的内网穿透进程。
        """
        self.tun_manager.stop_all()

    def get_secret(
        self,
        secret_type: SecretType,
        key: str,
    ) -> str | None:
        """根据密钥类型获取密钥

        Args:
            secret_type (SecretType):
                密钥类型, 支持 `colab` / `kaggle`
            key (str):
                密钥名称

        Returns:
            (str | None):
                密钥名称对应的密钥
        """
        if secret_type == "colab":
            return _get_colab_secret(key)
        if secret_type == "kaggle":
            return _get_kaggle_secret(key)

        logger.error("未知的密钥类型: %s", secret_type)
        return None

    def get_model(
        self,
        url: str,
        path: str | Path,
        filename: str | None = None,
        tool: DownloadToolType | None = None,
    ) -> Path | None:
        """下载模型文件到本地中

        Args:
            url (str):
                模型文件的下载链接
            path (str | Path):
                模型文件下载到本地的路径
            filename (str | None):
                指定下载的模型文件名称
            tool (DownloadToolType | None):
                下载工具

        Returns:
            (Path | None): 文件保存路径
        """
        try:
            return download_file(
                url=url,
                path=Path(path),
                save_name=filename,
                tool=tool,
            )
        except Exception as e:
            traceback.print_exc()
            logger.error("下载 '%s' 到 '%s' 时发生错误: %s", url, path, e)
            return None

    def get_model_from_list(
        self,
        path: str | Path,
        model_list: ModelDownloadList,
    ) -> None:
        """从模型列表下载模型

        `model_list`需要指定模型下载的链接和下载状态, 支持使用 list 或 tuple 描述单个模型, 例如
        ```python
        model_list = [
            ["url1", 0],
            ("url2", 1),
            ["url3", 0],
            ("url4", 1, "file.safetensors"),
            {"url": "url5", "status": 1, "filename": "file.safetensors"},
        ]
        ```

        在这个例子中, 第一个参数指定了模型的下载链接, 第二个参数设置了是否要下载这个模型, 当这个值为 1 时则下载该模型

        第三个参数是可选参数, 用于指定下载到本地后的文件名称

        则上面的例子中`url2`和`url4`下载链接所指的文件将被下载, 并且`url4`所指的文件将被重命名为`file.safetensors`

        Args:
            path (str | Path): 将模型下载到的本地路径
            model_list (ModelDownloadList): 模型列表
        """
        for model in model_list:
            try:
                if isinstance(model, (list, tuple)):
                    url = str(model[0])
                    status = int(model[1])
                    filename = str(model[2]) if len(model) > 2 else None
                else:
                    url = model.get("url")
                    status = int(model.get("status", "1"))
                    filename = model.get("filename")
            except Exception as e:
                logger.error("模型下载列表长度不合法: %s\n出现异常的列表:%s", e, model)
                continue
            if url is None:
                logger.error("模型下载列表缺少 url: %s", model)
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
            base_dir (Path | str):
                链接的根路径
            drive_path (Path | str):
                链接到的 Google Drive 的路径
            links (list[dict[str, str | bool]]):
                要进行链接文件的路径表
        """
        for link in links:
            link_dir = link.get("link_dir")
            is_file = bool(link.get("is_file", False))
            if not isinstance(link_dir, str):
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

    def parse_cmd_str_to_list(
        self,
        launch_args: str,
    ) -> list[str]:
        """解析命令行参数字符串, 返回参数列表

        Args:
            launch_args (str):
                命令行参数字符串

        Returns:
            list[str]:
                解析后的参数列表
        """
        return shlex.split(launch_args)

    def parse_cmd_list_to_str(
        self,
        cmd_list: list[str],
    ) -> str:
        """将命令列表转换为命令字符串

        Args:
            cmd_list (list[str]):
                命令列表

        Returns:
            str:
                命令字符串
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
            name (str):
                启动的名称
            base_path (Path | str):
                启动时得的根目录
            cmd (list[str] | str):
                启动 WebUI 的参数
            display_mode (Literal["terminal", "jupyter"] | None):
                执行子进程时使用的输出模式
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
                    if p.stdout is None:
                        return
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
        path_in_repo: str | None = None,
        visibility: bool = False,
        num_threads: int = 1,
        revision: str | None = None,
    ) -> None:
        """上传文件夹中的内容到 HuggingFace / ModelScope 仓库中

        Args:
            api_type (ApiType):
                Api 类型
            repo_id (str):
                仓库 ID
            upload_path (Path | str):
                要上传的文件夹
            repo_type (RepoType):
                仓库类型
            path_in_repo (str | None):
                仓库中的上传路径前缀, 为`None`时上传到仓库根目录
            visibility (bool):
                当仓库不存在时自动创建的仓库的可见性
            num_threads (int):
                上传线程数
            revision (str | None):
                指定上传目标分支或标签, 为`None`时使用第三方库默认值
        """
        self.repo_manager.upload_files_to_repo(
            api_type=api_type,
            repo_id=repo_id,
            upload_path=Path(upload_path),
            path_in_repo=path_in_repo,
            repo_type=repo_type,
            visibility=visibility,
            num_threads=num_threads,
            revision=revision,
        )

    def download_files_from_repo(
        self,
        api_type: ApiType,
        repo_id: str,
        local_dir: Path | str,
        repo_type: RepoType = "model",
        folder: str | None = None,
        num_threads: int = 8,
        revision: str | None = None,
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
            num_threads (int):
                下载线程
            revision (str | None):
                指定下载的分支、标签或提交哈希, 为`None`时使用第三方库默认值
        """
        self.repo_manager.download_files_from_repo(
            api_type=api_type,
            repo_id=repo_id,
            local_dir=Path(local_dir),
            repo_type=repo_type,
            folder=folder,
            num_threads=num_threads,
            revision=revision,
        )

    def get_repo_files_metadata(
        self,
        api_type: ApiType,
        repo_id: str,
        repo_type: RepoType = "model",
        revision: str | None = None,
        include_dirs: bool = False,
        include_raw: bool = False,
    ) -> list[dict[str, object]]:
        """获取 HuggingFace / ModelScope 仓库文件元数据列表

        Args:
            api_type (ApiType):
                Api 类型
            repo_id (str):
                仓库 ID
            repo_type (RepoType):
                仓库类型
            revision (str | None):
                指定仓库分支、标签或提交哈希, 为`None`时使用第三方库默认值
            include_dirs (bool):
                是否包含目录条目
            include_raw (bool):
                是否包含第三方库原始返回

        Returns:
            list[dict[str, object]]:
                归一化后的仓库文件元数据列表
        """
        metadata_kwargs = {
            "api_type": api_type,
            "repo_id": repo_id,
            "repo_type": repo_type,
            "include_dirs": include_dirs,
            "include_raw": include_raw,
        }
        if revision is not None:
            metadata_kwargs["revision"] = revision
        return self.repo_manager.get_repo_files_metadata(**metadata_kwargs)

    def get_repo_file_download_url(
        self,
        api_type: ApiType,
        repo_id: str,
        file_path: str,
        repo_type: RepoType = "model",
        revision: str | None = None,
    ) -> str:
        """获取 HuggingFace / ModelScope 仓库中文件的下载地址

        Args:
            api_type (ApiType):
                Api 类型
            repo_id (str):
                仓库 ID
            file_path (str):
                仓库中的文件路径
            repo_type (RepoType):
                仓库类型
            revision (str | None):
                指定仓库分支、标签或提交哈希, 为`None`时使用第三方库默认值

        Returns:
            str:
                文件下载地址
        """
        url_kwargs = {
            "api_type": api_type,
            "repo_id": repo_id,
            "file_path": file_path,
            "repo_type": repo_type,
        }
        if revision is not None:
            url_kwargs["revision"] = revision
        return self.repo_manager.get_repo_file_download_url(**url_kwargs)

    def mirror_repo_files(
        self,
        src_api_type: ApiType,
        dst_api_type: ApiType,
        src_repo_id: str,
        dst_repo_id: str,
        src_repo_type: RepoType = "model",
        dst_repo_type: RepoType = "model",
        visibility: bool = False,
        revision: str | None = None,
        num_threads: int = 1,
        retry_times: int = RETRY_TIMES,
        use_fast_download: bool = False,
        download_tool: DownloadToolType | None = "requests",
        download_split: int = 5,
        download_progress: bool = True,
    ) -> None:
        """镜像 HuggingFace / ModelScope 仓库文件

        Args:
            src_api_type (ApiType):
                源仓库 API 类型
            dst_api_type (ApiType):
                目标仓库 API 类型
            src_repo_id (str):
                源仓库 ID
            dst_repo_id (str):
                目标仓库 ID
            src_repo_type (RepoType):
                源仓库类型
            dst_repo_type (RepoType):
                目标仓库类型
            visibility (bool):
                当目标仓库不存在时自动创建的仓库的可见性
            revision (str | None):
                指定源仓库读取和目标仓库上传的分支、标签或提交哈希, 为`None`时使用第三方库默认值
            num_threads (int):
                镜像线程数
            retry_times (int):
                单个文件镜像失败后的重试次数
            use_fast_download (bool):
                是否使用项目内`download_file()`下载器进行下载
            download_tool (DownloadToolType | None):
                `use_fast_download`启用时使用的下载器
            download_split (int):
                `use_fast_download`启用时传给`download_file()`的下载 split
            download_progress (bool):
                `use_fast_download`启用时是否显示下载进度
        """
        self.repo_manager.mirror_repo_files(
            src_api_type=src_api_type,
            dst_api_type=dst_api_type,
            src_repo_id=src_repo_id,
            dst_repo_id=dst_repo_id,
            src_repo_type=src_repo_type,
            dst_repo_type=dst_repo_type,
            visibility=visibility,
            revision=revision,
            num_threads=num_threads,
            retry_times=retry_times,
            use_fast_download=use_fast_download,
            download_tool=download_tool,
            download_split=download_split,
            download_progress=download_progress,
        )

    def clear_output(
        self,
    ) -> None:
        """清理 Jupyter Notebook 的输出"""
        clear_jupyter_output()

    def get_tunnel_url(
        self,
        use_ngrok: bool = False,
        ngrok_token: str | None = None,
        use_cloudflare: bool = False,
        use_remote_moe: bool = False,
        use_localhost_run: bool = False,
        use_gradio: bool = False,
        use_pinggy_io: bool = False,
        use_zrok: bool = False,
        zrok_token: str | None = None,
        webui_name: str | None = "WebUI",
    ) -> TunnelUrl:
        """获取内网穿透地址

        支持两种使用方式:
        1. 直接调用（原有用法）: 返回 TunnelUrl 字典
        2. 使用上下文管理器: 通过 tun_manager 使用 with 语句

        Examples:
            ```python
            # 方式1: 直接调用（原有用法）
            manager = BaseManager(workspace="/workspace", workfolder="sd-webui")
            tunnel_url = manager.get_tunnel_url(use_cloudflare=True)
            # 需要手动停止: manager.stop_all_tunnels()

            # 方式2: 使用上下文管理器（推荐）
            manager = BaseManager(workspace="/workspace", workfolder="sd-webui")
            with manager.tun_manager:
                tunnel_url = manager.get_tunnel_url(use_cloudflare=True)
                # 做其他操作...
            # 退出时自动停止所有内网穿透
            ```

        Args:
            use_ngrok (bool):
                启用 Ngrok 内网穿透
            ngrok_token (str | None):
                Ngrok 账号 Token
            use_cloudflare (bool):
                启用 CloudFlare 内网穿透
            use_remote_moe (bool):
                启用 remote.moe 内网穿透
            use_localhost_run (bool):
                使用 localhost.run 内网穿透
            use_gradio (bool):
                使用 Gradio 内网穿透
            use_pinggy_io (bool):
                使用 pinggy.io 内网穿透
            use_zrok (bool):
                使用 Zrok 内网穿透
            zrok_token (str | None):
                Zrok 账号 Token
            webui_name (str | None):
                WebUI 的名称

        Returns:
            TunnelUrl:
                内网穿透的地址字典
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
            if k == "local_url":
                continue
            print(f"- {k}: {v}")
        print_divider("=")
        return tun

    def download_file_from_url(
        self,
        url: str,
        path: Path | str | None = None,
        save_name: str | None = None,
        tool: DownloadToolType | None = None,
    ) -> Path:
        """从链接中下载文件

        Args:
            url (str):
                文件下载链接
            path (Path | str | None):
                文件下载路径
            save_name (str | None):
                文件保存名称
            tool (DownloadToolType | None):
                下载工具

        Returns:
            Path:
                文件保存路径
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
        recursive: bool = False,
        show_hidden: bool = True,
    ) -> None:
        """列出多个指定文件夹的文件列表

        Args:
            *paths (Path | str | None):
                要展示的一个或多个路径
            recursive (bool):
                递归显示子目录的内容
            show_hidden (bool):
                显示隐藏文件
        """
        display_paths = [Path(p) for p in paths if p is not None]
        display_directories(
            *display_paths,
            recursive=recursive,
            show_hidden=show_hidden,
        )

    def import_file_from_kaggle_input(
        self,
        output_path: str | Path,
    ) -> None:
        """从 Kaggle Input 文件夹中导入文件

        Args:
            output_path (str | Path):
                导出文件的路径
        """
        import_kaggle_input(Path(output_path))
