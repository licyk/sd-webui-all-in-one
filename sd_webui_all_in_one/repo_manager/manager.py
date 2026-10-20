"""HuggingFace / ModelScope 仓库管理器"""

from sd_webui_all_in_one.repo_manager.upload import RepoUploadMixin
from sd_webui_all_in_one.repo_manager.mirror import RepoMirrorMixin
from sd_webui_all_in_one.repo_manager.download import RepoDownloadMixin


class RepoManager(
    RepoUploadMixin,
    RepoMirrorMixin,
    RepoDownloadMixin,
):
    """HuggingFace / ModelScope 仓库管理器

    Attributes:
        hf_api (Any):
            HuggingFace API 客户端实例, 用于与 HuggingFace 仓库进行交互
        ms_api (Any):
            ModelScope API 客户端实例, 用于与 ModelScope 仓库进行交互
        hf_token (str | None):
            HuggingFace认 证令牌, 用于访问私有仓库
        ms_token (str | None):
            ModelScope 认证令牌, 用于访问私有仓库
    """
