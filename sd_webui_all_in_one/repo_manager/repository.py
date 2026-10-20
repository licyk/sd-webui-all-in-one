"""仓库存在性检查与自动创建"""

from sd_webui_all_in_one.config import RETRY_TIMES
from sd_webui_all_in_one.retry_decorator import retryable
from sd_webui_all_in_one.repo_manager.types import (
    ApiType,
    RepoType,
)
from sd_webui_all_in_one.repo_manager.shared import logger
from sd_webui_all_in_one.repo_manager.dependencies import _ensure_modelscope
from sd_webui_all_in_one.repo_manager.client import RepoApiClient


class RepoCheckMixin(RepoApiClient):
    """仓库存在性检查与自动创建功能"""

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
        visibility: bool = False,
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
        visibility: bool = False,
    ) -> bool:
        """检查 HuggingFace 仓库是否存在, 当不存在时则自动创建

        Args:
            repo_id (str):
                HuggingFace 仓库 ID
            repo_type (RepoType):
                HuggingFace 仓库类型
            visibility (bool):
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
        visibility: bool = False,
    ) -> bool:
        """检查 ModelScope 仓库是否存在, 当不存在时则自动创建

        Args:
            repo_id (str):
                ModelScope 仓库 ID
            repo_type (RepoType):
                ModelScope 仓库类型
            visibility (bool):
                ModelScope 仓库可见性

        Returns:
            bool:
                检查成功时 / 创建仓库成功时返回`True`

        Raises:
            ValueError:
                仓库类型未知时
        """
        _ensure_modelscope("modelscope.hub.constants")
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
