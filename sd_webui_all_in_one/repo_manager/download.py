"""从仓库下载文件"""

from pathlib import Path
from typing import Any

from sd_webui_all_in_one.downloader import MultiThreadDownloader
from sd_webui_all_in_one.repo_manager.types import (
    ApiType,
    RepoType,
)
from sd_webui_all_in_one.repo_manager.shared import logger
from sd_webui_all_in_one.repo_manager.utils import _add_revision
from sd_webui_all_in_one.repo_manager.dependencies import (
    _ensure_huggingface_hub,
    _ensure_modelscope,
)
from sd_webui_all_in_one.repo_manager.listing import RepoListingMixin


class RepoDownloadMixin(RepoListingMixin):
    """从仓库下载文件的功能"""

    def download_files_from_repo(
        self,
        api_type: ApiType,
        repo_id: str,
        local_dir: Path,
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
            local_dir (Path):
                下载路径
            folder (str | None):
                指定下载某个文件夹, 未指定时则下载整个文件夹
            num_threads (int):
                下载线程
            revision (str | None):
                指定下载的分支、标签或提交哈希, 为`None`时使用第三方库默认值

        Raises:
            ValueError:
                API 类型未知时
        """
        if api_type not in ["huggingface", "modelscope"]:
            raise ValueError(f"未知的 API 类型: {api_type}")

        logger.info("从 %s (类型: %s) 下载文件中", repo_id, repo_type)
        if api_type == "huggingface":
            self.download_files_from_huggingface(
                **_add_revision(
                    {
                        "repo_id": repo_id,
                        "repo_type": repo_type,
                        "local_dir": local_dir,
                        "folder": folder,
                        "num_threads": num_threads,
                    },
                    revision,
                )
            )

        if api_type == "modelscope":
            self.download_files_from_modelscope(
                **_add_revision(
                    {
                        "repo_id": repo_id,
                        "repo_type": repo_type,
                        "local_dir": local_dir,
                        "folder": folder,
                        "num_threads": num_threads,
                    },
                    revision,
                )
            )

    def download_files_from_huggingface(
        self,
        repo_id: str,
        local_dir: Path,
        repo_type: RepoType = "model",
        folder: str | None = None,
        num_threads: int = 8,
        revision: str | None = None,
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
            num_threads (int):
                下载线程
            revision (str | None):
                指定下载的分支、标签或提交哈希, 为`None`时使用 HuggingFace 默认值
        """
        _ensure_huggingface_hub()

        repo_files = self.get_repo_file(
            api_type="huggingface",
            repo_id=repo_id,
            repo_type=repo_type,
            revision=revision,
        )
        download_task: list[dict[str, Any]] = []

        for repo_file in repo_files:
            if folder is not None and not repo_file.startswith(folder):
                continue
            download_task.append(
                _add_revision(
                    {
                        "repo_id": repo_id,
                        "repo_type": repo_type,
                        "local_dir": local_dir,
                        "filename": repo_file,
                    },
                    revision,
                )
            )

        if folder is not None:
            logger.info("指定下载文件: %s", folder)
        logger.info("下载文件数量: %s", len(download_task))

        files_downloader = MultiThreadDownloader(download_func=self.hf_api.hf_hub_download, download_kwargs_list=download_task)
        files_downloader.start(num_threads=num_threads)

    def download_files_from_modelscope(
        self,
        repo_id: str,
        local_dir: Path,
        repo_type: RepoType = "model",
        folder: str | None = None,
        num_threads: int = 8,
        revision: str | None = None,
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
            num_threads (int):
                下载线程
            revision (str | None):
                指定下载的分支、标签或提交哈希, 为`None`时使用 ModelScope 默认值
        """
        _ensure_modelscope()
        from modelscope import snapshot_download

        repo_files = self.get_repo_file(
            api_type="modelscope",
            repo_id=repo_id,
            repo_type=repo_type,
            revision=revision,
        )
        download_task: list[dict[str, Any]] = []

        for repo_file in repo_files:
            if folder is not None and not repo_file.startswith(folder):
                continue
            download_task.append(
                _add_revision(
                    {
                        "repo_id": repo_id,
                        "repo_type": repo_type,
                        "local_dir": local_dir,
                        "allow_patterns": repo_file,
                    },
                    revision,
                )
            )

        if folder is not None:
            logger.info("指定下载文件: %s", folder)
        logger.info("下载文件数量: %s", len(download_task))

        files_downloader = MultiThreadDownloader(download_func=snapshot_download, download_kwargs_list=download_task)
        files_downloader.start(num_threads=num_threads)
