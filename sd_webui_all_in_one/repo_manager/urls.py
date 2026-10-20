"""仓库文件下载地址查询"""

from typing import Any

from sd_webui_all_in_one.config import RETRY_TIMES
from sd_webui_all_in_one.retry_decorator import retryable
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
from sd_webui_all_in_one.repo_manager.client import RepoApiClient


class RepoDownloadUrlMixin(RepoApiClient):
    """仓库文件下载地址查询功能"""

    @retryable(
        times=RETRY_TIMES,
        describe="获取 HuggingFace / ModelScope 仓库文件下载地址",
        catch_exceptions=(Exception),
        raise_exception=(RuntimeError),
        retry_on_none=False,
    )
    def get_repo_file_download_url(
        self,
        api_type: ApiType,
        repo_id: str,
        file_path: str,
        repo_type: RepoType = "model",
        revision: str | None = None,
    ) -> str:
        """获取 HuggingFace / ModelScope 仓库中文件的实际下载地址

        Args:
            api_type (ApiType):
                Api 类型
            repo_id (str):
                HuggingFace / ModelScope 仓库 ID
            file_path (str):
                仓库中的文件路径
            repo_type (RepoType):
                HuggingFace / ModelScope 仓库类型
            revision (str | None):
                指定仓库分支、标签或提交哈希, 为`None`时使用第三方库默认值

        Returns:
            str:
                文件下载地址

        Raises:
            RuntimeError:
                获取文件下载地址失败时
            ValueError:
                使用的 API 类型未知时
        """
        if api_type == "huggingface":
            logger.info(
                "获取 HuggingFace 仓库 %s (类型: %s) 中文件 %s 的下载地址",
                repo_id,
                repo_type,
                file_path,
            )
            return self.get_hf_repo_file_download_url(
                **_add_revision(
                    {
                        "repo_id": repo_id,
                        "file_path": file_path,
                        "repo_type": repo_type,
                    },
                    revision,
                )
            )
        if api_type == "modelscope":
            logger.info(
                "获取 ModelScope 仓库 %s (类型: %s) 中文件 %s 的下载地址",
                repo_id,
                repo_type,
                file_path,
            )
            return self.get_ms_repo_file_download_url(
                **_add_revision(
                    {
                        "repo_id": repo_id,
                        "file_path": file_path,
                        "repo_type": repo_type,
                    },
                    revision,
                )
            )

        logger.error("未知 Api 类型: %s", api_type)
        raise ValueError(f"未知的 API 类型: {api_type}")

    def get_hf_repo_file_download_url(
        self,
        repo_id: str,
        file_path: str,
        repo_type: RepoType = "model",
        revision: str | None = None,
    ) -> str:
        """获取 HuggingFace 仓库中文件的长期下载入口地址

        Args:
            repo_id (str):
                HuggingFace 仓库 ID
            file_path (str):
                仓库中的文件路径
            repo_type (RepoType):
                HuggingFace 仓库类型
            revision (str | None):
                指定仓库分支、标签或提交哈希, 为`None`时使用 HuggingFace 默认值

        Returns:
            str:
                文件下载地址
        """
        _ensure_huggingface_hub()
        from huggingface_hub import get_hf_file_metadata, hf_hub_url

        hf_api = self.hf_api

        url_kwargs: dict[str, Any] = _add_revision(
            {
                "repo_id": repo_id,
                "filename": file_path,
                "repo_type": repo_type,
                "endpoint": getattr(hf_api, "endpoint", None),
            },
            revision,
        )
        url = hf_hub_url(**url_kwargs)

        if hasattr(hf_api, "get_hf_file_metadata"):
            hf_api.get_hf_file_metadata(url=url, token=self.hf_token)
        else:
            get_hf_file_metadata(url=url, token=self.hf_token)
        return url

    def get_ms_repo_file_download_url(
        self,
        repo_id: str,
        file_path: str,
        repo_type: RepoType = "model",
        revision: str | None = None,
    ) -> str:
        """获取 ModelScope 仓库中文件的下载地址

        Args:
            repo_id (str):
                ModelScope 仓库 ID
            file_path (str):
                仓库中的文件路径
            repo_type (RepoType):
                ModelScope 仓库类型
            revision (str | None):
                指定仓库分支、标签或提交哈希, 为`None`时使用 ModelScope 默认值

        Returns:
            str:
                文件下载地址

        Raises:
            ValueError:
                ModelScope 不支持的仓库类型
        """
        _ensure_modelscope("modelscope.hub.file_download")
        _ensure_modelscope("modelscope.utils.constant")
        from modelscope.hub.file_download import get_file_download_url
        from modelscope.utils.constant import DEFAULT_DATASET_REVISION, DEFAULT_MODEL_REVISION

        if repo_type == "model":
            return get_file_download_url(
                model_id=repo_id,
                file_path=file_path,
                revision=revision or DEFAULT_MODEL_REVISION,
            )
        if repo_type == "dataset":
            owner, dataset_name = repo_id.split("/")
            return self.ms_api.get_dataset_file_url(
                file_name=file_path,
                dataset_name=dataset_name,
                namespace=owner,
                revision=revision or DEFAULT_DATASET_REVISION,
            )
        if repo_type == "space":
            logger.error("%s 仓库类型为创空间, 不支持获取文件下载地址", repo_id)
            raise ValueError(f"{repo_type} 仓库类型为创空间, 不支持获取文件下载地址")

        logger.error("未知的 %s 仓库类型", repo_type)
        raise ValueError(f"未知的仓库类型: {repo_type}")
