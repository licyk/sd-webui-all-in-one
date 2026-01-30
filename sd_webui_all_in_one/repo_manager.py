"""HuggingFace / Modelscope 仓库管理工具"""

import os
import traceback
from pathlib import Path
from typing import Any, Literal

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.file_manager import get_file_list
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR
from sd_webui_all_in_one.downloader import MultiThreadDownloader

logger = get_logger(
    name="Repo Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class RepoManager:
    """HuggingFace / ModelScope 仓库管理器

    Attributes:
        hf_api (HfApi | None): HuggingFace API 客户端实例, 用于与 HuggingFace 仓库进行交互
        ms_api (HubApi | None): ModelScope API 客户端实例, 用于与 ModelScope 仓库进行交互
        hf_token (str | None): HuggingFace认 证令牌, 用于访问私有仓库
        ms_token (str | None): ModelScope 认证令牌, 用于访问私有仓库
    """

    def __init__(
        self,
        hf_token: str | None = None,
        ms_token: str | None = None,
    ) -> None:
        """HuggingFace / ModelScope 仓库管理器初始化

        Args:
            hf_token (str | None): HugggingFace Token, 不为`None`时配置`HF_TOKEN`环境变量
            ms_token (str | None): ModelScope Token, 不为`None`时配置`MODELSCOPE_API_TOKEN`环境变量
        """
        try:
            from huggingface_hub import HfApi

            self.hf_api = HfApi(token=hf_token)
            if hf_token is not None:
                os.environ["HF_TOKEN"] = hf_token
                self.hf_token = hf_token
        except Exception as e:
            logger.warning("HuggingFace 库未安装, 部分功能将不可用: %s", e)
        try:
            from modelscope import HubApi

            self.ms_api = HubApi()
            if ms_token is not None:
                os.environ["MODELSCOPE_API_TOKEN"] = ms_token
                self.ms_api.login(access_token=ms_token)
                self.ms_token = ms_token
        except Exception as e:
            logger.warning("ModelScope 库未安装, 部分功能将不可用: %s", e)

    def get_repo_file(
        self,
        api_type: Literal["huggingface", "modelscope"],
        repo_id: str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        retry: int | None = 3,
    ) -> list[str]:
        """获取 HuggingFace / ModelScope 仓库文件列表

        Args:
            api_type (Literal["huggingface", "modelscope"]): Api 类型
            repo_id (str): HuggingFace / ModelScope 仓库 ID
            repo_type (str): HuggingFace / ModelScope 仓库类型
            retry (int | None): 重试次数
        Returns:
            list[str]: 仓库文件列表
        """
        if api_type == "huggingface":
            logger.info("获取 HuggingFace 仓库 %s (类型: %s) 的文件列表", repo_id, repo_type)
            return self.get_hf_repo_files(repo_id, repo_type, retry)
        if api_type == "modelscope":
            logger.info("获取 ModelScope 仓库 %s (类型: %s) 的文件列表", repo_id, repo_type)
            return self.get_ms_repo_files(repo_id, repo_type, retry)

        logger.error("未知 Api 类型: %s", api_type)
        return []

    def get_hf_repo_files(
        self,
        repo_id: str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        retry: int | None = 3,
    ) -> list[str]:
        """获取 HuggingFace 仓库文件列表

        Args:
            repo_id (str): HuggingFace 仓库 ID
            repo_type (str): HuggingFace 仓库类型
            retry (int | None): 重试次数
        Returns:
            list[str]: 仓库文件列表
        """
        count = 0
        while count < retry:
            count += 1
            try:
                return self.hf_api.list_repo_files(
                    repo_id=repo_id,
                    repo_type=repo_type,
                )
            except Exception as e:
                logger.error(
                    "[%s/%s] 获取 %s (类型: %s) 仓库的文件列表出现错误: %s",
                    count,
                    retry,
                    repo_id,
                    repo_type,
                    e,
                )
                traceback.print_exc()
                if count < retry:
                    logger.warning("[%s/%s] 重试获取文件列表中", count, retry)
        return []

    def get_ms_repo_files(
        self,
        repo_id: str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        retry: int | None = 3,
    ) -> list[str]:
        """获取 ModelScope 仓库文件列表

        Args:
            repo_id (str): ModelScope 仓库 ID
            repo_type (str): ModelScope 仓库类型
            retry (int | None): 重试次数
        Returns:
            list[str]: 仓库文件列表
        """
        file_list = []
        count = 0

        def _get_file_path(repo_files: list) -> list[str]:
            """获取 ModelScope Api 返回的仓库列表中的模型路径"""
            return [file["Path"] for file in repo_files if file["Type"] != "tree"]

        if repo_type == "model":
            while count < retry:
                count += 1
                try:
                    repo_files = self.ms_api.get_model_files(model_id=repo_id, recursive=True)
                    file_list = _get_file_path(repo_files)
                    break
                except Exception as e:
                    traceback.print_exc()
                    logger.error(
                        "[%s/%s] 获取 %s (类型: %s) 仓库的文件列表出现错误: %s",
                        count,
                        retry,
                        repo_id,
                        repo_type,
                        e,
                    )
                    if count < retry:
                        logger.warning("[%s/%s] 重试获取文件列表中", count, retry)
        elif repo_type == "dataset":
            while count < retry:
                count += 1
                try:
                    repo_files = self.ms_api.get_dataset_files(repo_id=repo_id, recursive=True)
                    file_list = _get_file_path(repo_files)
                    break
                except Exception as e:
                    traceback.print_exc()
                    logger.error(
                        "[%s/%s] 获取 %s (类型: %s) 仓库的文件列表出现错误: %s",
                        count,
                        retry,
                        repo_id,
                        repo_type,
                        e,
                    )
                    if count < retry:
                        logger.warning("[%s/%s] 重试获取文件列表中", count, retry)
        elif repo_type == "space":
            # TODO: 支持创空间
            logger.error("%s 仓库类型为创空间, 不支持获取文件列表", repo_id)
        else:
            logger.error("未知的 %s 仓库类型", repo_type)

        return file_list

    def check_repo(
        self,
        api_type: Literal["huggingface", "modelscope"],
        repo_id: str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        visibility: bool | None = False,
    ) -> bool:
        """检查 HuggingFace / ModelScope 仓库是否存在, 当不存在时则自动创建

        Args:
            api_type (Literal["huggingface", "modelscope"]): Api 类型
            repo_id (str): 仓库 ID
            repo_type (Literal["model", "dataset", "space"]): 仓库类型
        Returns:
            bool: 检查成功时 / 创建仓库成功时返回`True`
        """
        if api_type == "huggingface":
            return self.check_hf_repo(repo_id, repo_type, visibility)
        if api_type == "modelscope":
            return self.check_ms_repo(repo_id, repo_type, visibility)

        logger.error("未知 Api 类型: %s", api_type)
        return False

    def check_hf_repo(
        self,
        repo_id: str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        visibility: bool | None = False,
    ) -> bool:
        """检查 HuggingFace 仓库是否存在, 当不存在时则自动创建

        Args:
            repo_id (str): HuggingFace 仓库 ID
            repo_type (str): HuggingFace 仓库类型
            visibility (bool | None): HuggingFace 仓库可见性
        Returns:
            bool: 检查成功时 / 创建仓库成功时返回`True`
        """
        if repo_type in ["model", "dataset", "space"]:
            try:
                if not self.hf_api.repo_exists(repo_id=repo_id, repo_type=repo_type):
                    self.hf_api.create_repo(repo_id=repo_id, repo_type=repo_type, private=not visibility)
                return True
            except Exception as e:
                traceback.print_exc()
                logger.error("检查 HuggingFace 仓库时发生错误: %s", e)
                return False

        logger.error("未知 HuggingFace 仓库类型: %s", repo_type)
        return False

    def check_ms_repo(
        self,
        repo_id: str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        visibility: bool | None = False,
    ) -> bool:
        """检查 ModelScope 仓库是否存在, 当不存在时则自动创建

        Args:
            repo_id (str): ModelScope 仓库 ID
            repo_type (str): ModelScope 仓库类型
            visibility (bool | None): HuggingFace 仓库可见性
        Returns:
            bool: 检查成功时 / 创建仓库成功时返回`True`
        """
        from modelscope.hub.constants import Visibility

        if repo_type in ["model", "dataset"]:
            try:
                if not self.ms_api.repo_exists(
                    repo_id=repo_id,
                    repo_type=repo_type,
                    token=self.ms_token,
                ):
                    self.ms_api.create_repo(
                        repo_id=repo_id,
                        repo_type=repo_type,
                        visibility=Visibility.PUBLIC if visibility else Visibility.PRIVATE,
                        token=self.ms_token,
                    )
                return True
            except Exception as e:
                traceback.print_exc()
                logger.error("检查 ModelScope 仓库时发生错误: %s", e)
                return False
        if repo_type == "space":
            logger.error("未支持 ModelScope 创空间")
            return False

        logger.error("未知 ModelScope 仓库类型: %s", repo_type)
        return False

    def upload_files_to_repo(
        self,
        api_type: Literal["huggingface", "modelscope"],
        repo_id: str,
        upload_path: Path | str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        visibility: bool | None = False,
        retry: int | None = 3,
    ) -> None:
        """上传文件夹中的内容到 HuggingFace / ModelScope 仓库中

        Args:
            api_type (Literal["huggingface", "modelscope"]): Api 类型
            repo_id (str): 仓库 ID
            repo_type (str): 仓库类型
            upload_path (Path | str): 要上传的文件夹
            visibility (bool | None): 当仓库不存在时自动创建的仓库的可见性
            retry (int | None): 上传重试次数
        """
        if api_type in ["huggingface", "modelscope"]:
            if not self.check_repo(
                api_type=api_type,
                repo_id=repo_id,
                repo_type=repo_type,
                visibility=visibility,
            ):
                logger.error("检查 %s (类型: %s) 仓库失败, 无法上传文件")
                return

        upload_path = Path(upload_path) if not isinstance(upload_path, Path) and upload_path is not None else upload_path

        if api_type == "huggingface":
            self.upload_files_to_huggingface(
                repo_id=repo_id,
                repo_type=repo_type,
                upload_path=upload_path,
                retry=retry,
            )
        elif api_type == "modelscope":
            self.upload_files_to_modelscope(
                repo_id=repo_id,
                repo_type=repo_type,
                upload_path=upload_path,
                retry=retry,
            )
        else:
            logger.error("未知 Api 类型: %s", api_type)

    def upload_files_to_huggingface(
        self,
        repo_id: str,
        upload_path: Path | str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        retry: int | None = 3,
    ) -> None:
        """上传文件夹中的内容到 HuggingFace 仓库中

        Args:
            repo_id (str): HuggingFace 仓库 ID
            repo_type (str): HuggingFace 仓库类型
            upload_path (Path | str): 要上传到 HuggingFace 仓库的文件夹
            retry (int | None): 上传重试次数
        """
        upload_files = get_file_list(upload_path)
        repo_files = set(
            self.get_repo_file(
                api_type="huggingface",
                repo_id=repo_id,
                repo_type=repo_type,
                retry=retry,
            )
        )
        logger.info("上传到 HuggingFace 仓库: %s -> HuggingFace/%s", upload_path, repo_id)
        files_count = len(upload_files)
        count = 0
        for upload_file in upload_files:
            count += 1
            upload_file_rel_path = upload_file.relative_to(upload_path).as_posix()
            if upload_file_rel_path in repo_files:
                logger.info(
                    "[%s/%s] %s 已存在于 HuggingFace 仓库中, 跳过上传",
                    count,
                    files_count,
                    upload_file,
                )
                continue

            logger.info(
                "[%s/%s] 上传 %s 到 %s (类型: %s) 仓库中",
                count,
                files_count,
                upload_file,
                repo_id,
                repo_type,
            )
            retry_num = 0
            while retry_num < retry:
                retry_num += 1
                try:
                    self.hf_api.upload_file(
                        repo_id=repo_id,
                        repo_type=repo_type,
                        path_in_repo=upload_file_rel_path,
                        path_or_fileobj=upload_file,
                        commit_message=f"Upload {upload_file.name}",
                    )
                    break
                except Exception as e:
                    logger.error(
                        "[%s/%s] 上传 %s 时发生错误: %s",
                        count,
                        files_count,
                        upload_file.name,
                        e,
                    )
                    traceback.print_exc()
                    if retry_num < retry:
                        logger.warning("[%s/%s] 重试上传 %s", count, files_count, upload_file.name)

        logger.info(
            "[%s/%s] 上传 %s 到 %s (类型: %s) 完成",
            count,
            files_count,
            upload_path,
            repo_id,
            repo_type,
        )

    def upload_files_to_modelscope(
        self,
        repo_id: str,
        upload_path: Path | str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        retry: int | None = 3,
    ) -> None:
        """上传文件夹中的内容到 ModelScope 仓库中

        Args:
            repo_id (str): ModelScope 仓库 ID
            repo_type (str): ModelScope 仓库类型
            upload_path (Path | str): 要上传到 ModelScope 仓库的文件夹
            retry (int | None): 上传重试次数
        """
        upload_files = get_file_list(upload_path)
        repo_files = set(
            self.get_repo_file(
                api_type="modelscope",
                repo_id=repo_id,
                repo_type=repo_type,
                retry=retry,
            )
        )
        logger.info("上传到 ModelScope 仓库: %s -> ModelScope/%s", upload_path, repo_id)
        files_count = len(upload_files)
        count = 0
        for upload_file in upload_files:
            count += 1
            upload_file_rel_path = upload_file.relative_to(upload_path).as_posix()
            if upload_file_rel_path in repo_files:
                logger.info(
                    "[%s/%s] %s 已存在于 ModelScope 仓库中, 跳过上传",
                    count,
                    files_count,
                    upload_file,
                )
                continue

            logger.info(
                "[%s/%s] 上传 %s 到 %s (类型: %s) 仓库中",
                count,
                files_count,
                upload_file,
                repo_id,
                repo_type,
            )
            retry_num = 0
            while retry_num < retry:
                retry_num += 1
                try:
                    self.ms_api.upload_file(
                        repo_id=repo_id,
                        repo_type=repo_type,
                        path_in_repo=upload_file_rel_path,
                        path_or_fileobj=upload_file,
                        commit_message=f"Upload {upload_file.name}",
                        token=self.ms_token,
                    )
                    break
                except Exception as e:
                    logger.error(
                        "[%s/%s] 上传 %s 时发生错误: %s",
                        count,
                        files_count,
                        upload_file.name,
                        e,
                    )
                    traceback.print_exc()
                    if retry_num < retry:
                        logger.warning("[%s/%s] 重试上传 %s", count, files_count, upload_file.name)

        logger.info(
            "[%s/%s] 上传 %s 到 %s (类型: %s) 完成",
            count,
            files_count,
            upload_path,
            repo_id,
            repo_type,
        )

    def download_files_from_repo(
        self,
        api_type: Literal["huggingface", "modelscope"],
        repo_id: str,
        local_dir: Path | str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        folder: str | None = None,
        retry: int | None = 3,
        num_threads: int | None = 16,
    ) -> Path:
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
            api_type (Literal["huggingface", "modelscope"]): Api 类型
            repo_id (str): 仓库 ID
            repo_type (Literal["model", "dataset", "space"]): 仓库类型
            local_dir (Path | str): 下载路径
            folder (str | None): 指定下载某个文件夹, 未指定时则下载整个文件夹
            retry (int | None): 重试下载的次数
            num_threads (int | None): 下载线程
        Returns:
            Path: 下载路径


        """
        local_dir = Path(local_dir) if not isinstance(local_dir, Path) and local_dir is not None else local_dir

        logger.info("从 %s (类型: %s) 下载文件中", repo_id, repo_type)
        if api_type == "huggingface":
            self.download_files_from_huggingface(
                repo_id=repo_id,
                repo_type=repo_type,
                local_dir=local_dir,
                folder=folder,
                retry=retry,
                num_threads=num_threads,
            )
            return local_dir

        if api_type == "modelscope":
            self.download_files_from_modelscope(
                repo_id=repo_id,
                repo_type=repo_type,
                local_dir=local_dir,
                folder=folder,
                retry=retry,
                num_threads=num_threads,
            )
            return local_dir

        logger.error("未知 Api 类型: %s", api_type)
        return None

    def download_files_from_huggingface(
        self,
        repo_id: str,
        local_dir: Path | str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        folder: str | None = None,
        retry: int | None = 3,
        num_threads: int | None = 16,
    ) -> None:
        """从 HuggingFace 仓库下载文文件

        Args:
            repo_id (str): HuggingFace 仓库 ID
            repo_type (Literal["model", "dataset", "space"]): HuggingFace 仓库类型
            local_dir (Path | str): 下载路径
            folder (str | None): 指定下载某个文件夹, 未指定时则下载整个文件夹
            retry (int | None): 重试下载的次数
            num_threads (int | None): 下载线程
        """
        from huggingface_hub import hf_hub_download

        repo_files = self.get_repo_file(
            api_type="huggingface",
            repo_id=repo_id,
            repo_type=repo_type,
            retry=retry,
        )
        download_task: list[dict[str, Any]] = []

        for repo_file in repo_files:
            if folder is not None and not repo_file.startswith(folder):
                continue
            download_task.append(
                {
                    "repo_id": repo_id,
                    "repo_type": repo_type,
                    "local_dir": local_dir,
                    "filename": repo_file,
                }
            )

        if folder is not None:
            logger.info("指定下载文件: %s", folder)
        logger.info("下载文件数量: %s", len(download_task))

        files_downloader = MultiThreadDownloader(download_func=hf_hub_download, download_kwargs_list=download_task)
        files_downloader.start(
            num_threads=num_threads,
            retry_count=retry,
        )

    def download_files_from_modelscope(
        self,
        repo_id: str,
        local_dir: Path | str,
        repo_type: Literal["model", "dataset", "space"] = "model",
        folder: str | None = None,
        retry: int | None = 3,
        num_threads: int | None = 16,
    ) -> None:
        """从 ModelScope 仓库下载文文件

        Args:
            repo_id (str): ModelScope 仓库 ID
            repo_type (Literal["model", "dataset", "space"]): ModelScope 仓库类型
            local_dir (Path | str): 下载路径
            folder (str | None): 指定下载某个文件夹, 未指定时则下载整个文件夹
            retry (int | None): 重试下载的次数
            num_threads (int | None): 下载线程
        """
        from modelscope import snapshot_download

        repo_files = self.get_repo_file(
            api_type="modelscope",
            repo_id=repo_id,
            repo_type=repo_type,
            retry=retry,
        )
        download_task: list[dict[str, Any]] = []

        for repo_file in repo_files:
            if folder is not None and not repo_file.startswith(folder):
                continue
            download_task.append(
                {
                    "repo_id": repo_id,
                    "repo_type": repo_type,
                    "local_dir": local_dir,
                    "allow_patterns": repo_file,
                }
            )

        if folder is not None:
            logger.info("指定下载文件: %s", folder)
        logger.info("下载文件数量: %s", len(download_task))

        files_downloader = MultiThreadDownloader(download_func=snapshot_download, download_kwargs_list=download_task)
        files_downloader.start(
            num_threads=num_threads,
            retry_count=retry,
        )
