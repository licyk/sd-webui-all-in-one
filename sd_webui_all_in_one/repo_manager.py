"""HuggingFace / Modelscope 仓库管理工具"""

import os
from pathlib import Path
from typing import Any, Literal, TypeAlias

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.file_operations.file_manager import get_file_list
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR, RETRY_TIMES
from sd_webui_all_in_one.downloader import MultiThreadDownloader
from sd_webui_all_in_one.retry_decorator import retryable
from sd_webui_all_in_one.custom_exceptions import AggregateError

logger = get_logger(
    name="Repo Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

ApiType: TypeAlias = Literal["huggingface", "modelscope"]
"""API 类型"""

RepoType: TypeAlias = Literal["model", "dataset", "space"]
"""HuggingFace / ModelScope 仓库类型"""


class RepoManager:
    """HuggingFace / ModelScope 仓库管理器

    Attributes:
        hf_api (HfApi | None):
            HuggingFace API 客户端实例, 用于与 HuggingFace 仓库进行交互
        ms_api (HubApi | None):
            ModelScope API 客户端实例, 用于与 ModelScope 仓库进行交互
        hf_token (str | None):
            HuggingFace认 证令牌, 用于访问私有仓库
        ms_token (str | None):
            ModelScope 认证令牌, 用于访问私有仓库
    """

    def __init__(
        self,
        hf_token: str | None = None,
        ms_token: str | None = None,
    ) -> None:
        """HuggingFace / ModelScope 仓库管理器初始化

        Args:
            hf_token (str | None):
                HugggingFace Token, 不为`None`时配置`HF_TOKEN`环境变量
            ms_token (str | None):
                ModelScope Token, 不为`None`时配置`MODELSCOPE_API_TOKEN`环境变量
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

    @retryable(
        times=RETRY_TIMES,
        describe="获取 HuggingFace / ModelScope 仓库文件列表",
        catch_exceptions=(Exception),
        raise_exception=(RuntimeError),
        retry_on_none=False,
    )
    def get_repo_file(
        self,
        api_type: ApiType,
        repo_id: str,
        repo_type: RepoType = "model",
    ) -> list[str]:
        """获取 HuggingFace / ModelScope 仓库文件列表

        Args:
            api_type (ApiType):
                Api 类型
            repo_id (str):
                HuggingFace / ModelScope 仓库 ID
            repo_type (RepoType):
                HuggingFace / ModelScope 仓库类型

        Returns:
            list[str]:
                仓库文件列表

        Raises:
            RuntimeError:
                获取仓库文件列表失败时
            ValueError:
                使用的 API 类型未知时
        """
        if api_type == "huggingface":
            logger.info("获取 HuggingFace 仓库 %s (类型: %s) 的文件列表", repo_id, repo_type)
            return self.get_hf_repo_files(repo_id, repo_type)
        if api_type == "modelscope":
            logger.info("获取 ModelScope 仓库 %s (类型: %s) 的文件列表", repo_id, repo_type)
            return self.get_ms_repo_files(repo_id, repo_type)

        logger.error("未知 Api 类型: %s", api_type)
        raise ValueError(f"未知的 API 类型: {api_type}")

    def get_hf_repo_files(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
    ) -> list[str]:
        """获取 HuggingFace 仓库文件列表

        Args:
            repo_id (str):
                HuggingFace 仓库 ID
            repo_type (RepoType):
                HuggingFace 仓库类型

        Returns:
            list[str]:
                仓库文件列表
        """
        return self.hf_api.list_repo_files(
            repo_id=repo_id,
            repo_type=repo_type,
        )

    def get_ms_repo_files(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
    ) -> list[str]:
        """获取 ModelScope 仓库文件列表

        Args:
            repo_id (str):
                ModelScope 仓库 ID
            repo_type (RepoType):
                ModelScope 仓库类型

        Returns:
            list[str]:
                仓库文件列表

        Raises:
            ValueError:
                使用的 API 类型未知时或者不支持时
        """

        def _get_file_path(repo_files: list) -> list[str]:
            """获取 ModelScope Api 返回的仓库列表中的模型路径"""
            return [file["Path"] for file in repo_files if file["Type"] != "tree"]

        if repo_type == "model":
            repo_files = self.ms_api.get_model_files(model_id=repo_id, recursive=True)
            return _get_file_path(repo_files)
        if repo_type == "dataset":
            repo_files = self.ms_api.get_dataset_files(repo_id=repo_id, recursive=True)
            return _get_file_path(repo_files)
        if repo_type == "space":
            # TODO: 支持创空间
            logger.error("%s 仓库类型为创空间, 不支持获取文件列表", repo_id)
            raise ValueError(f"{repo_type} 仓库类型为创空间, 不支持获取文件列表")

        logger.error("未知的 %s 仓库类型", repo_type)
        raise ValueError(f"未知的仓库类型: {repo_type}")

    @retryable(
        times=RETRY_TIMES,
        describe="检查 HuggingFace / ModelScope 仓库是否存在",
        catch_exceptions=(Exception),
        raise_exception=(RuntimeError),
        retry_on_none=False,
    )
    def check_repo(
        self,
        api_type: ApiType,
        repo_id: str,
        repo_type: RepoType = "model",
        visibility: bool | None = False,
    ) -> bool:
        """检查 HuggingFace / ModelScope 仓库是否存在, 当不存在时则自动创建

        Args:
            api_type (ApiType):
                Api 类型
            repo_id (str):
                仓库 ID
            repo_type (RepoType):
                仓库类型
            visibility:
                设置创建仓库是设置的仓库可见性

        Returns:
            bool:
                检查成功时 / 创建仓库成功时返回`True`

        Raises:
            ValueError:
                使用的 API 类型未知时
            RuntimeError:
                检查失败时
        """
        if api_type == "huggingface":
            return self.check_hf_repo(repo_id, repo_type, visibility)
        if api_type == "modelscope":
            return self.check_ms_repo(repo_id, repo_type, visibility)

        logger.error("未知 Api 类型: %s", api_type)
        raise ValueError(f"未知的 API 类型: {api_type}")

    def check_hf_repo(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
        visibility: bool | None = False,
    ) -> bool:
        """检查 HuggingFace 仓库是否存在, 当不存在时则自动创建

        Args:
            repo_id (str):
                HuggingFace 仓库 ID
            repo_type (RepoType):
                HuggingFace 仓库类型
            visibility (bool | None):
                HuggingFace 仓库可见性

        Returns:
            bool:
                检查成功时 / 创建仓库成功时返回`True`

        Raises:
            ValueError:
                仓库类型未知时
        """
        if repo_type not in ["model", "dataset", "space"]:
            raise ValueError(f"未知的仓库类型: {repo_type}")

        if not self.hf_api.repo_exists(repo_id=repo_id, repo_type=repo_type):
            self.hf_api.create_repo(repo_id=repo_id, repo_type=repo_type, private=not visibility)

        return True

    def check_ms_repo(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
        visibility: bool | None = False,
    ) -> bool:
        """检查 ModelScope 仓库是否存在, 当不存在时则自动创建

        Args:
            repo_id (str):
                ModelScope 仓库 ID
            repo_type (RepoType):
                ModelScope 仓库类型
            visibility (bool | None):
                ModelScope 仓库可见性

        Returns:
            bool:
                检查成功时 / 创建仓库成功时返回`True`

        Raises:
            ValueError:
                仓库类型未知时
        """
        from modelscope.hub.constants import Visibility

        if repo_type not in ["model", "dataset"]:
            raise ValueError(f"未知的仓库类型: {repo_type}")

        if not self.ms_api.repo_exists(repo_id=repo_id, repo_type=repo_type, token=self.ms_token):
            self.ms_api.create_repo(
                repo_id=repo_id,
                repo_type=repo_type,
                visibility=Visibility.PUBLIC if visibility else Visibility.PRIVATE,
                token=self.ms_token,
            )

        return True

    def upload_files_to_repo(
        self,
        api_type: ApiType,
        repo_id: str,
        upload_path: Path,
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
            upload_path (Path):
                要上传的文件夹
            visibility (bool | None):
                当仓库不存在时自动创建的仓库的可见性
            retry (int | None):
                上传重试次数

        Raises:
            ValueError:
                API 类型未知时
        """
        if api_type not in ["huggingface", "modelscope"]:
            raise ValueError(f"未知的 API 类型: {api_type}")

        self.check_repo(
            api_type=api_type,
            repo_id=repo_id,
            repo_type=repo_type,
            visibility=visibility,
        )

        if api_type == "huggingface":
            self.upload_files_to_huggingface(
                repo_id=repo_id,
                repo_type=repo_type,
                upload_path=upload_path,
            )
        elif api_type == "modelscope":
            self.upload_files_to_modelscope(
                repo_id=repo_id,
                repo_type=repo_type,
                upload_path=upload_path,
            )

    def upload_files_to_huggingface(
        self,
        repo_id: str,
        upload_path: Path,
        repo_type: RepoType = "model",
        retry: int | None = 3,
    ) -> None:
        """上传文件夹中的内容到 HuggingFace 仓库中

        Args:
            repo_id (str):
                HuggingFace 仓库 ID
            repo_type (RepoType):
                HuggingFace 仓库类型
            upload_path (Path):
                要上传到 HuggingFace 仓库的文件夹
            retry (int | None):
                上传重试次数

        Raises:
            AggregateError:
                上传任务出现错误时
        """
        upload_files = get_file_list(upload_path)
        repo_files = set(
            self.get_repo_file(
                api_type="huggingface",
                repo_id=repo_id,
                repo_type=repo_type,
            )
        )
        logger.info("上传到 HuggingFace 仓库: %s -> HuggingFace/%s", upload_path, repo_id)
        files_count = len(upload_files)
        count = 0
        err: list[Exception] = []
        for upload_file in upload_files:
            count += 1
            upload_file_rel_path = upload_file.relative_to(upload_path).as_posix()
            if upload_file_rel_path in repo_files:
                logger.info("[%s/%s] %s 已存在于 HuggingFace 仓库中, 跳过上传", count, files_count, upload_file)
                continue

            logger.info("[%s/%s] 上传 %s 到 %s (类型: %s) 仓库中", count, files_count, upload_file, repo_id, repo_type)

            @retryable(
                times=RETRY_TIMES,
                describe="上传文件到 HuggingFace",
                catch_exceptions=(Exception),
                raise_exception=(RuntimeError),
                retry_on_none=False,
            )
            def _upload_file(
                repo_id: str,
                repo_type: str,
                path_in_repo: str,
                path_or_fileobj: Path,
            ) -> None:
                self.hf_api.upload_file(
                    repo_id=repo_id,
                    repo_type=repo_type,
                    path_in_repo=path_in_repo,
                    path_or_fileobj=path_or_fileobj,
                    commit_message=f"Upload {path_or_fileobj.name}",
                )

            try:
                _upload_file(
                    repo_id=repo_id,
                    repo_type=repo_type,
                    path_in_repo=upload_file_rel_path,
                    path_or_fileobj=upload_file,
                    retry=retry,
                )
            except RuntimeError as e:
                err.append(e)
                logger.error("[%s/%s] 上传 %s 最终失败: %s", count, files_count, upload_file.name, e)

        if err:
            raise AggregateError(f"上传 {repo_id} (类型: {repo_type}) 时发生了错误", err)

        logger.info("[%s/%s] 上传 %s 到 %s (类型: %s) 完成", count, files_count, upload_path, repo_id, repo_type)

    def upload_files_to_modelscope(
        self,
        repo_id: str,
        upload_path: Path,
        repo_type: RepoType = "model",
    ) -> None:
        """上传文件夹中的内容到 ModelScope 仓库中

        Args:
            repo_id (str):
                ModelScope 仓库 ID
            repo_type (RepoType):
                ModelScope 仓库类型
            upload_path (Path):
                要上传到 ModelScope 仓库的文件夹
            retry (int | None):
                上传重试次数

        Raises:
            AggregateError:
                上传任务出现错误时
        """
        upload_files = get_file_list(upload_path)
        repo_files = set(
            self.get_repo_file(
                api_type="modelscope",
                repo_id=repo_id,
                repo_type=repo_type,
            )
        )
        logger.info("上传到 ModelScope 仓库: %s -> ModelScope/%s", upload_path, repo_id)
        files_count = len(upload_files)
        count = 0
        err: list[Exception] = []
        for upload_file in upload_files:
            count += 1
            upload_file_rel_path = upload_file.relative_to(upload_path).as_posix()
            if upload_file_rel_path in repo_files:
                logger.info("[%s/%s] %s 已存在于 ModelScope 仓库中, 跳过上传", count, files_count, upload_file)
                continue

            logger.info("[%s/%s] 上传 %s 到 %s (类型: %s) 仓库中", count, files_count, upload_file, repo_id, repo_type)

            @retryable(
                times=RETRY_TIMES,
                describe="上传文件到 ModelScope",
                catch_exceptions=(Exception),
                raise_exception=(RuntimeError),
                retry_on_none=False,
            )
            def _upload_file(
                repo_id: str,
                repo_type: str,
                path_in_repo: str,
                path_or_fileobj: Path,
            ) -> None:
                self.ms_api.upload_file(
                    repo_id=repo_id,
                    repo_type=repo_type,
                    path_in_repo=path_in_repo,
                    path_or_fileobj=path_or_fileobj,
                    commit_message=f"Upload {path_or_fileobj.name}",
                    token=self.ms_token,
                )

            try:
                _upload_file(
                    repo_id=repo_id,
                    repo_type=repo_type,
                    path_in_repo=upload_file_rel_path,
                    path_or_fileobj=upload_file,
                )
            except RuntimeError as e:
                err.append(e)
                logger.error("[%s/%s] 上传 %s 最终失败: %s", count, files_count, upload_file.name, e)

        if err:
            raise AggregateError(f"上传 {repo_id} (类型: {repo_type}) 时发生了错误", err)

        logger.info("[%s/%s] 上传 %s 到 %s (类型: %s) 完成", count, files_count, upload_path, repo_id, repo_type)

    def download_files_from_repo(
        self,
        api_type: ApiType,
        repo_id: str,
        local_dir: Path,
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
            local_dir (Path):
                下载路径
            folder (str | None):
                指定下载某个文件夹, 未指定时则下载整个文件夹
            num_threads (int | None):
                下载线程

        Raises:
            ValueError:
                API 类型未知时
        """
        if api_type not in ["huggingface", "modelscope"]:
            raise ValueError(f"未知的 API 类型: {api_type}")

        logger.info("从 %s (类型: %s) 下载文件中", repo_id, repo_type)
        if api_type == "huggingface":
            self.download_files_from_huggingface(
                repo_id=repo_id,
                repo_type=repo_type,
                local_dir=local_dir,
                folder=folder,
                num_threads=num_threads,
            )

        if api_type == "modelscope":
            self.download_files_from_modelscope(
                repo_id=repo_id,
                repo_type=repo_type,
                local_dir=local_dir,
                folder=folder,
                num_threads=num_threads,
            )

    def download_files_from_huggingface(
        self,
        repo_id: str,
        local_dir: Path,
        repo_type: RepoType = "model",
        folder: str | None = None,
        num_threads: int | None = 16,
    ) -> None:
        """从 HuggingFace 仓库下载文文件

        Args:
            repo_id (str):
                HuggingFace 仓库 ID
            repo_type (RepoType):
                HuggingFace 仓库类型
            local_dir (Path):
                下载路径
            folder (str | None):
                指定下载某个文件夹, 未指定时则下载整个文件夹
            num_threads (int | None):
                下载线程
        """
        from huggingface_hub import hf_hub_download

        repo_files = self.get_repo_file(
            api_type="huggingface",
            repo_id=repo_id,
            repo_type=repo_type,
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
        files_downloader.start(num_threads=num_threads)

    def download_files_from_modelscope(
        self,
        repo_id: str,
        local_dir: Path,
        repo_type: RepoType = "model",
        folder: str | None = None,
        num_threads: int | None = 16,
    ) -> None:
        """从 ModelScope 仓库下载文文件

        Args:
            repo_id (str):
                ModelScope 仓库 ID
            repo_type (RepoType):
                ModelScope 仓库类型
            local_dir (Path):
                下载路径
            folder (str | None):
                指定下载某个文件夹, 未指定时则下载整个文件夹
            retry (int | None):
                重试下载的次数
            num_threads (int | None):
                下载线程
        """
        from modelscope import snapshot_download

        repo_files = self.get_repo_file(
            api_type="modelscope",
            repo_id=repo_id,
            repo_type=repo_type,
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
        files_downloader.start(num_threads=num_threads)
