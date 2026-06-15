"""HuggingFace / Modelscope 仓库管理工具"""

import hashlib
import importlib
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, cast

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.file_manager import get_file_list
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    RETRY_TIMES,
    LOGGER_NAME,
)
from sd_webui_all_in_one.downloader import (
    DownloadToolType,
    MultiThreadDownloader,
    download_file,
)
from sd_webui_all_in_one.optional_dependency import install_optional_dependency
from sd_webui_all_in_one.retry_decorator import retryable
from sd_webui_all_in_one.custom_exceptions import AggregateError

if TYPE_CHECKING:
    from huggingface_hub import HfApi
    from modelscope import HubApi

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

ApiType: TypeAlias = Literal["huggingface", "modelscope"]
"""API 类型"""

RepoType: TypeAlias = Literal["model", "dataset", "space"]
"""HuggingFace / ModelScope 仓库类型"""

RepoFileType: TypeAlias = Literal["file", "directory"]
"""仓库条目类型"""

RepoFileMetadata: TypeAlias = dict[str, Any]
"""归一化后的仓库文件元数据"""

_API_NOT_INITIALIZED = object()
"""API 客户端未初始化标记"""


def _add_revision(
    kwargs: dict[str, Any],
    revision: str | None,
) -> dict[str, Any]:
    if revision is not None:
        kwargs["revision"] = revision
    return kwargs


def _repo_path_name(path: str) -> str:
    return path.rstrip("/").rsplit("/", 1)[-1]


def _get_mapping_or_attr(
    value: Any,
    key: str,
    default: Any = None,
) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _object_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return dict(getattr(value, "__dict__", {}))


def _file_sha256(file_path: Path) -> str:
    hash_sha256 = hashlib.sha256()
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def _repo_file_metadata_by_path(repo_files_metadata: list[RepoFileMetadata]) -> dict[str, RepoFileMetadata]:
    return {
        metadata["path"]: metadata
        for metadata in repo_files_metadata
        if metadata.get("type") == "file" and metadata.get("path")
    }


def _normalize_sha256(value: Any) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip().lower()
    return normalized or None


def _repo_file_hash_matches(src_metadata: RepoFileMetadata, dst_metadata: RepoFileMetadata) -> bool:
    src_sha256 = _normalize_sha256(src_metadata.get("sha256"))
    dst_sha256 = _normalize_sha256(dst_metadata.get("sha256"))
    return src_sha256 is not None and dst_sha256 is not None and src_sha256 == dst_sha256


def _ensure_optional_dependency(
    module_name: str,
    package_name: str,
    display_name: str | None = None,
) -> None:
    """确保可选依赖可导入, 导入失败时先安装依赖后再重试"""
    display_name = display_name or module_name
    try:
        importlib.import_module(module_name)
        return
    except ImportError as import_error:
        logger.warning("%s 模块导入失败, 尝试自动安装依赖: %s", display_name, import_error)

    try:
        install_optional_dependency(package_name, display_name=display_name)
        importlib.invalidate_caches()
        importlib.import_module(module_name)
    except (RuntimeError, ImportError) as e:
        logger.error("导入 %s 模块失败: %s", display_name, e)
        raise RuntimeError(f"导入 {display_name} 模块失败: {e}") from e


def _ensure_huggingface_hub(
    module_name: str = "huggingface_hub",
) -> None:
    """确保 huggingface_hub 相关模块可导入, 缺失时自动安装 huggingface_hub"""
    _ensure_optional_dependency(module_name, "huggingface_hub", display_name=module_name)


def _ensure_modelscope(
    module_name: str = "modelscope",
) -> None:
    """确保 modelscope 相关模块可导入, 缺失时自动安装 modelscope"""
    _ensure_optional_dependency(module_name, "modelscope", display_name=module_name)


class RepoManager:
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
        self._hf_api: "HfApi | object" = _API_NOT_INITIALIZED
        self._ms_api: "HubApi | object" = _API_NOT_INITIALIZED
        self._hf_api_lock = Lock()
        self._ms_api_lock = Lock()
        self.hf_token: str | None = hf_token
        self.ms_token: str | None = ms_token
        if hf_token is not None:
            os.environ["HF_TOKEN"] = hf_token
        if ms_token is not None:
            os.environ["MODELSCOPE_API_TOKEN"] = ms_token

    def _get_hf_api_lock(self) -> Lock:
        """获取 HuggingFace API 懒初始化锁"""
        lock = getattr(self, "_hf_api_lock", None)
        if lock is None:
            lock = Lock()
            self._hf_api_lock = lock
        return lock

    def _get_ms_api_lock(self) -> Lock:
        """获取 ModelScope API 懒初始化锁"""
        lock = getattr(self, "_ms_api_lock", None)
        if lock is None:
            lock = Lock()
            self._ms_api_lock = lock
        return lock

    def _init_hf_api(self) -> "HfApi":
        """初始化 HuggingFace API 客户端"""
        _ensure_huggingface_hub()
        from huggingface_hub import HfApi

        return HfApi(token=self.hf_token)

    def _init_ms_api(self) -> "HubApi":
        """初始化 ModelScope API 客户端"""
        _ensure_modelscope()
        from modelscope import HubApi

        ms_api = HubApi()
        if self.ms_token is not None:
            ms_api.login(access_token=self.ms_token)
        return ms_api

    def configure_tokens(
        self,
        hf_token: str | None = None,
        ms_token: str | None = None,
    ) -> None:
        """配置 HuggingFace / ModelScope Token

        Args:
            hf_token (str | None):
                HuggingFace Token, 为`None`时保持当前配置
            ms_token (str | None):
                ModelScope Token, 为`None`时保持当前配置
        """
        if hf_token is not None and hf_token != self.hf_token:
            self.hf_token = hf_token
            os.environ["HF_TOKEN"] = hf_token
            self._hf_api = _API_NOT_INITIALIZED

        if ms_token is not None and ms_token != self.ms_token:
            self.ms_token = ms_token
            os.environ["MODELSCOPE_API_TOKEN"] = ms_token
            self._ms_api = _API_NOT_INITIALIZED

    @property
    def hf_api(self) -> "HfApi":
        """HuggingFace API 客户端实例, 首次访问时懒初始化

        Returns:
            HfApi:
                HuggingFace API 客户端实例
        """
        if getattr(self, "_hf_api", _API_NOT_INITIALIZED) is _API_NOT_INITIALIZED:
            with self._get_hf_api_lock():
                if getattr(self, "_hf_api", _API_NOT_INITIALIZED) is _API_NOT_INITIALIZED:
                    self._hf_api = self._init_hf_api()
        return cast("HfApi", self._hf_api)

    @hf_api.setter
    def hf_api(self, value: Any) -> None:
        self._hf_api = value

    @property
    def ms_api(self) -> "HubApi":
        """ModelScope API 客户端实例, 首次访问时懒初始化

        Returns:
            HubApi:
                ModelScope API 客户端实例
        """
        if getattr(self, "_ms_api", _API_NOT_INITIALIZED) is _API_NOT_INITIALIZED:
            with self._get_ms_api_lock():
                if getattr(self, "_ms_api", _API_NOT_INITIALIZED) is _API_NOT_INITIALIZED:
                    self._ms_api = self._init_ms_api()
        return cast("HubApi", self._ms_api)

    @ms_api.setter
    def ms_api(self, value: Any) -> None:
        self._ms_api = value

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
        revision: str | None = None,
    ) -> list[str]:
        """获取 HuggingFace / ModelScope 仓库文件列表

        Args:
            api_type (ApiType):
                Api 类型
            repo_id (str):
                HuggingFace / ModelScope 仓库 ID
            repo_type (RepoType):
                HuggingFace / ModelScope 仓库类型
            revision (str | None):
                指定仓库分支、标签或提交哈希, 为`None`时使用第三方库默认值

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
            return self.get_hf_repo_files(**_add_revision({"repo_id": repo_id, "repo_type": repo_type}, revision))
        if api_type == "modelscope":
            logger.info("获取 ModelScope 仓库 %s (类型: %s) 的文件列表", repo_id, repo_type)
            return self.get_ms_repo_files(**_add_revision({"repo_id": repo_id, "repo_type": repo_type}, revision))

        logger.error("未知 Api 类型: %s", api_type)
        raise ValueError(f"未知的 API 类型: {api_type}")

    def get_hf_repo_files(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
        revision: str | None = None,
    ) -> list[str]:
        """获取 HuggingFace 仓库文件列表

        Args:
            repo_id (str):
                HuggingFace 仓库 ID
            repo_type (RepoType):
                HuggingFace 仓库类型
            revision (str | None):
                指定仓库分支、标签或提交哈希, 为`None`时使用 HuggingFace 默认值

        Returns:
            list[str]:
                仓库文件列表
        """
        list_kwargs: dict[str, Any] = _add_revision(
            {
                "repo_id": repo_id,
                "repo_type": repo_type,
            },
            revision,
        )
        return self.hf_api.list_repo_files(**list_kwargs)

    def get_ms_repo_files(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
        revision: str | None = None,
    ) -> list[str]:
        """获取 ModelScope 仓库文件列表

        Args:
            repo_id (str):
                ModelScope 仓库 ID
            repo_type (RepoType):
                ModelScope 仓库类型
            revision (str | None):
                指定仓库分支、标签或提交哈希, 为`None`时使用 ModelScope 默认值

        Returns:
            list[str]:
                仓库文件列表

        Raises:
            ValueError:
                使用的 API 类型未知时或者不支持时
        """

        def _get_file_path(
            repo_files: list[dict[str, Any]],
        ) -> list[str]:
            """获取 ModelScope Api 返回的仓库列表中的模型路径"""
            return [file["Path"] for file in repo_files if file["Type"] != "tree"]

        if repo_type == "model":
            list_kwargs = _add_revision(
                {
                    "model_id": repo_id,
                    "recursive": True,
                },
                revision,
            )
            repo_files = self.ms_api.get_model_files(**list_kwargs)
            return _get_file_path(repo_files)
        if repo_type == "dataset":
            all_files = []
            page_number = 1
            page_size = 100
            owner, dataset_name = repo_id.split("/")
            dataset_hub_id, _ = self.ms_api.get_dataset_id_and_type(
                dataset_name=dataset_name,
                namespace=owner,
            )
            while True:
                list_kwargs = _add_revision(
                    {
                        "repo_id": repo_id,
                        "recursive": True,
                        "page_number": page_number,
                        "page_size": page_size,
                        "dataset_hub_id": dataset_hub_id,
                    },
                    revision,
                )
                repo_files = self.ms_api.get_dataset_files(**list_kwargs)
                if not repo_files:
                    break

                all_files.extend(repo_files)
                if len(repo_files) < page_size:
                    break

                page_number += 1
            return _get_file_path(all_files)
        if repo_type == "space":
            # TODO: 支持创空间
            logger.error("%s 仓库类型为创空间, 不支持获取文件列表", repo_id)
            raise ValueError(f"{repo_type} 仓库类型为创空间, 不支持获取文件列表")

        logger.error("未知的 %s 仓库类型", repo_type)
        raise ValueError(f"未知的仓库类型: {repo_type}")

    @retryable(
        times=RETRY_TIMES,
        describe="获取 HuggingFace / ModelScope 仓库文件元数据列表",
        catch_exceptions=(Exception),
        raise_exception=(RuntimeError),
        retry_on_none=False,
    )
    def get_repo_files_metadata(
        self,
        api_type: ApiType,
        repo_id: str,
        repo_type: RepoType = "model",
        revision: str | None = None,
        include_dirs: bool = False,
        include_raw: bool = False,
    ) -> list[RepoFileMetadata]:
        """获取 HuggingFace / ModelScope 仓库文件元数据列表

        Args:
            api_type (ApiType):
                Api 类型
            repo_id (str):
                HuggingFace / ModelScope 仓库 ID
            repo_type (RepoType):
                HuggingFace / ModelScope 仓库类型
            revision (str | None):
                指定仓库分支、标签或提交哈希, 为`None`时使用第三方库默认值
            include_dirs (bool):
                是否包含目录条目
            include_raw (bool):
                是否包含第三方库原始返回

        Returns:
            list[RepoFileMetadata]:
                归一化后的仓库文件元数据列表

        Raises:
            RuntimeError:
                获取仓库文件元数据列表失败时
            ValueError:
                使用的 API 类型未知时
        """
        if api_type == "huggingface":
            logger.info("获取 HuggingFace 仓库 %s (类型: %s) 的文件元数据列表", repo_id, repo_type)
            return self.get_hf_repo_files_metadata(
                **_add_revision(
                    {
                        "repo_id": repo_id,
                        "repo_type": repo_type,
                        "include_dirs": include_dirs,
                        "include_raw": include_raw,
                    },
                    revision,
                )
            )
        if api_type == "modelscope":
            logger.info("获取 ModelScope 仓库 %s (类型: %s) 的文件元数据列表", repo_id, repo_type)
            return self.get_ms_repo_files_metadata(
                **_add_revision(
                    {
                        "repo_id": repo_id,
                        "repo_type": repo_type,
                        "include_dirs": include_dirs,
                        "include_raw": include_raw,
                    },
                    revision,
                )
            )

        logger.error("未知 Api 类型: %s", api_type)
        raise ValueError(f"未知的 API 类型: {api_type}")

    def get_hf_repo_files_metadata(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
        revision: str | None = None,
        include_dirs: bool = False,
        include_raw: bool = False,
    ) -> list[RepoFileMetadata]:
        """获取 HuggingFace 仓库文件元数据列表

        Args:
            repo_id (str):
                HuggingFace 仓库 ID
            repo_type (RepoType):
                HuggingFace 仓库类型
            revision (str | None):
                指定仓库分支、标签或提交哈希, 为`None`时使用 HuggingFace 默认值
            include_dirs (bool):
                是否包含目录条目
            include_raw (bool):
                是否包含 HuggingFace 原始返回

        Returns:
            list[RepoFileMetadata]:
                归一化后的仓库文件元数据列表
        """
        list_kwargs: dict[str, Any] = _add_revision(
            {
                "repo_id": repo_id,
                "repo_type": repo_type,
                "recursive": True,
            },
            revision,
        )
        entries = []
        for item in self.hf_api.list_repo_tree(**list_kwargs):
            is_file = hasattr(item, "blob_id")
            if not is_file and not include_dirs:
                continue

            path = _get_mapping_or_attr(item, "path", "")
            lfs = _get_mapping_or_attr(item, "lfs")
            last_commit = _get_mapping_or_attr(item, "last_commit")
            entry_type: RepoFileType = "file" if is_file else "directory"
            metadata: RepoFileMetadata = {
                "path": path,
                "name": _repo_path_name(path),
                "type": entry_type,
                "size": _get_mapping_or_attr(item, "size") if is_file else None,
                "sha256": _get_mapping_or_attr(lfs, "sha256"),
                "is_lfs": lfs is not None if is_file else None,
                "object_id": _get_mapping_or_attr(item, "blob_id") if is_file else _get_mapping_or_attr(item, "tree_id"),
                "revision": _get_mapping_or_attr(last_commit, "oid") or revision,
            }
            if include_raw:
                metadata["raw"] = _object_to_dict(item)
            entries.append(metadata)
        return entries

    def get_ms_repo_files_metadata(
        self,
        repo_id: str,
        repo_type: RepoType = "model",
        revision: str | None = None,
        include_dirs: bool = False,
        include_raw: bool = False,
    ) -> list[RepoFileMetadata]:
        """获取 ModelScope 仓库文件元数据列表

        Args:
            repo_id (str):
                ModelScope 仓库 ID
            repo_type (RepoType):
                ModelScope 仓库类型
            revision (str | None):
                指定仓库分支、标签或提交哈希, 为`None`时使用 ModelScope 默认值
            include_dirs (bool):
                是否包含目录条目
            include_raw (bool):
                是否包含 ModelScope 原始返回

        Returns:
            list[RepoFileMetadata]:
                归一化后的仓库文件元数据列表

        Raises:
            ValueError:
                使用的仓库类型未知时或者不支持时
        """

        def _normalize_ms_files(repo_files: list[dict[str, Any]]) -> list[RepoFileMetadata]:
            entries = []
            for item in repo_files:
                is_dir = item.get("Type") == "tree"
                if is_dir and not include_dirs:
                    continue

                path = item.get("Path", "")
                entry_type: RepoFileType = "directory" if is_dir else "file"
                metadata: RepoFileMetadata = {
                    "path": path,
                    "name": item.get("Name") or _repo_path_name(path),
                    "type": entry_type,
                    "size": None if is_dir else item.get("Size"),
                    "sha256": item.get("Sha256"),
                    "is_lfs": item.get("IsLFS") if "IsLFS" in item else None,
                    "object_id": item.get("Sha256") if not is_dir else None,
                    "revision": item.get("Revision") or revision,
                }
                if include_raw:
                    metadata["raw"] = dict(item)
                entries.append(metadata)
            return entries

        if repo_type == "model":
            list_kwargs = _add_revision(
                {
                    "model_id": repo_id,
                    "recursive": True,
                },
                revision,
            )
            repo_files = self.ms_api.get_model_files(**list_kwargs)
            return _normalize_ms_files(repo_files)
        if repo_type == "dataset":
            all_files = []
            page_number = 1
            page_size = 100
            owner, dataset_name = repo_id.split("/")
            dataset_hub_id, _ = self.ms_api.get_dataset_id_and_type(
                dataset_name=dataset_name,
                namespace=owner,
            )
            while True:
                list_kwargs = _add_revision(
                    {
                        "repo_id": repo_id,
                        "recursive": True,
                        "page_number": page_number,
                        "page_size": page_size,
                        "dataset_hub_id": dataset_hub_id,
                    },
                    revision,
                )
                repo_files = self.ms_api.get_dataset_files(**list_kwargs)
                if not repo_files:
                    break

                all_files.extend(repo_files)
                if len(repo_files) < page_size:
                    break

                page_number += 1
            return _normalize_ms_files(all_files)
        if repo_type == "space":
            logger.error("%s 仓库类型为创空间, 不支持获取文件元数据列表", repo_id)
            raise ValueError(f"{repo_type} 仓库类型为创空间, 不支持获取文件元数据列表")

        logger.error("未知的 %s 仓库类型", repo_type)
        raise ValueError(f"未知的仓库类型: {repo_type}")

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
        """获取 HuggingFace 仓库中文件的实际下载地址

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
            metadata = hf_api.get_hf_file_metadata(url=url, token=self.hf_token)
        else:
            metadata = get_hf_file_metadata(url=url, token=self.hf_token)
        return metadata.location or url

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

    def upload_files_to_repo(
        self,
        api_type: ApiType,
        repo_id: str,
        upload_path: Path,
        repo_type: RepoType = "model",
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
            repo_type (RepoType):
                仓库类型
            upload_path (Path):
                要上传的文件夹
            visibility (bool):
                当仓库不存在时自动创建的仓库的可见性
            num_threads (int):
                上传线程数
            revision (str | None):
                指定上传目标分支或标签, 为`None`时使用第三方库默认值

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
                **_add_revision(
                    {
                        "repo_id": repo_id,
                        "repo_type": repo_type,
                        "upload_path": upload_path,
                        "num_threads": num_threads,
                    },
                    revision,
                )
            )
        elif api_type == "modelscope":
            self.upload_files_to_modelscope(
                **_add_revision(
                    {
                        "repo_id": repo_id,
                        "repo_type": repo_type,
                        "upload_path": upload_path,
                        "num_threads": num_threads,
                    },
                    revision,
                )
            )

    def upload_files_to_huggingface(
        self,
        repo_id: str,
        upload_path: Path,
        repo_type: RepoType = "model",
        num_threads: int = 1,
        revision: str | None = None,
    ) -> None:
        """上传文件夹中的内容到 HuggingFace 仓库中

        Args:
            repo_id (str):
                HuggingFace 仓库 ID
            repo_type (RepoType):
                HuggingFace 仓库类型
            upload_path (Path):
                要上传到 HuggingFace 仓库的文件夹
            num_threads (int):
                上传线程数
            revision (str | None):
                指定上传目标分支或标签, 为`None`时使用 HuggingFace 默认值

        Raises:
            AggregateError:
                上传任务出现错误时
        """
        upload_files = get_file_list(upload_path)
        repo_files = _repo_file_metadata_by_path(
            self.get_repo_files_metadata(
                api_type="huggingface",
                repo_id=repo_id,
                repo_type=repo_type,
                revision=revision,
            )
        )
        logger.info("上传到 HuggingFace 仓库: %s -> HuggingFace/%s", upload_path, repo_id)
        files_count = len(upload_files)
        err: list[Exception] = []
        upload_tasks: list[Path] = []

        for index, upload_file in enumerate(upload_files, start=1):
            upload_file_rel_path = upload_file.relative_to(upload_path).as_posix()
            repo_file_metadata = repo_files.get(upload_file_rel_path)
            if repo_file_metadata is None:
                upload_tasks.append(upload_file)
                continue

            remote_sha256 = _normalize_sha256(repo_file_metadata.get("sha256"))
            local_sha256 = _file_sha256(upload_file)
            if remote_sha256 is None or local_sha256 != remote_sha256:
                upload_tasks.append(upload_file)
                logger.info(
                    "[%s/%s] %s 已存在于 HuggingFace 仓库中但 hash 缺失或不同, 将重新上传",
                    index,
                    files_count,
                    upload_file,
                )
                continue

            logger.info(
                "[%s/%s] %s 已存在于 HuggingFace 仓库中且 hash 相同, 跳过上传",
                index,
                files_count,
                upload_file,
            )

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
            upload_kwargs = _add_revision(
                {
                    "repo_id": repo_id,
                    "repo_type": repo_type,
                    "path_in_repo": path_in_repo,
                    "path_or_fileobj": path_or_fileobj,
                    "commit_message": f"Upload {path_or_fileobj.name}",
                },
                revision,
            )
            self.hf_api.upload_file(**upload_kwargs)

        if upload_tasks:
            logger.info("实际需要上传文件数量: %s", len(upload_tasks))
        upload_count = len(upload_tasks)

        err_lock = Lock()

        def _run_upload(
            task: tuple[int, Path],
        ) -> None:
            index, upload_file = task
            upload_file_rel_path = upload_file.relative_to(upload_path).as_posix()
            logger.info("[%s/%s] 上传 %s 到 %s (类型: %s) 仓库中", index, upload_count, upload_file, repo_id, repo_type)
            try:
                _upload_file(
                    repo_id=repo_id,
                    repo_type=repo_type,
                    path_in_repo=upload_file_rel_path,
                    path_or_fileobj=upload_file,
                )
            except RuntimeError as e:
                with err_lock:
                    err.append(e)
                logger.error("[%s/%s] 上传 %s 最终失败: %s", index, upload_count, upload_file.name, e)

        max_workers = max(1, num_threads)
        if max_workers == 1:
            for task in enumerate(upload_tasks, start=1):
                _run_upload(task)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(executor.map(_run_upload, enumerate(upload_tasks, start=1)))

        if err:
            raise AggregateError(f"上传 {repo_id} (类型: {repo_type}) 时发生了错误", err)

        logger.info("上传 %s 到 %s (类型: %s) 完成", upload_path, repo_id, repo_type)

    def upload_files_to_modelscope(
        self,
        repo_id: str,
        upload_path: Path,
        repo_type: RepoType = "model",
        num_threads: int = 1,
        revision: str | None = None,
    ) -> None:
        """上传文件夹中的内容到 ModelScope 仓库中

        Args:
            repo_id (str):
                ModelScope 仓库 ID
            repo_type (RepoType):
                ModelScope 仓库类型
            upload_path (Path):
                要上传到 ModelScope 仓库的文件夹
            num_threads (int):
                上传线程数
            revision (str | None):
                指定上传目标分支或标签, 为`None`时使用 ModelScope 默认值

        Raises:
            AggregateError:
                上传任务出现错误时
        """
        upload_files = get_file_list(upload_path)
        repo_files = _repo_file_metadata_by_path(
            self.get_repo_files_metadata(
                api_type="modelscope",
                repo_id=repo_id,
                repo_type=repo_type,
                revision=revision,
            )
        )
        logger.info("上传到 ModelScope 仓库: %s -> ModelScope/%s", upload_path, repo_id)
        files_count = len(upload_files)
        err: list[Exception] = []
        upload_tasks: list[Path] = []

        for index, upload_file in enumerate(upload_files, start=1):
            upload_file_rel_path = upload_file.relative_to(upload_path).as_posix()
            repo_file_metadata = repo_files.get(upload_file_rel_path)
            if repo_file_metadata is None:
                upload_tasks.append(upload_file)
                continue

            remote_sha256 = _normalize_sha256(repo_file_metadata.get("sha256"))
            local_sha256 = _file_sha256(upload_file)
            if remote_sha256 is None or local_sha256 != remote_sha256:
                upload_tasks.append(upload_file)
                logger.info(
                    "[%s/%s] %s 已存在于 ModelScope 仓库中但 hash 缺失或不同, 将重新上传",
                    index,
                    files_count,
                    upload_file,
                )
                continue

            logger.info(
                "[%s/%s] %s 已存在于 ModelScope 仓库中且 hash 相同, 跳过上传",
                index,
                files_count,
                upload_file,
            )

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
            upload_kwargs = _add_revision(
                {
                    "repo_id": repo_id,
                    "repo_type": repo_type,
                    "path_in_repo": path_in_repo,
                    "path_or_fileobj": path_or_fileobj,
                    "commit_message": f"Upload {path_or_fileobj.name}",
                    "token": self.ms_token,
                },
                revision,
            )
            self.ms_api.upload_file(**upload_kwargs)

        if upload_tasks:
            logger.info("实际需要上传文件数量: %s", len(upload_tasks))
        upload_count = len(upload_tasks)

        err_lock = Lock()

        def _run_upload(
            task: tuple[int, Path],
        ) -> None:
            index, upload_file = task
            upload_file_rel_path = upload_file.relative_to(upload_path).as_posix()
            logger.info("[%s/%s] 上传 %s 到 %s (类型: %s) 仓库中", index, upload_count, upload_file, repo_id, repo_type)
            try:
                _upload_file(
                    repo_id=repo_id,
                    repo_type=repo_type,
                    path_in_repo=upload_file_rel_path,
                    path_or_fileobj=upload_file,
                )
            except RuntimeError as e:
                with err_lock:
                    err.append(e)
                logger.error("[%s/%s] 上传 %s 最终失败: %s", index, upload_count, upload_file.name, e)

        max_workers = max(1, num_threads)
        if max_workers == 1:
            for task in enumerate(upload_tasks, start=1):
                _run_upload(task)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(executor.map(_run_upload, enumerate(upload_tasks, start=1)))

        if err:
            raise AggregateError(f"上传 {repo_id} (类型: {repo_type}) 时发生了错误", err)

        logger.info("上传 %s 到 %s (类型: %s) 完成", upload_path, repo_id, repo_type)

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

        Raises:
            AggregateError:
                镜像任务出现错误时
            ValueError:
                API 类型未知时
        """
        if src_api_type not in ["huggingface", "modelscope"]:
            raise ValueError(f"未知的源 API 类型: {src_api_type}")
        if dst_api_type not in ["huggingface", "modelscope"]:
            raise ValueError(f"未知的目标 API 类型: {dst_api_type}")

        logger.info(
            "镜像仓库文件: %s/%s (类型: %s) -> %s/%s (类型: %s)",
            src_api_type,
            src_repo_id,
            src_repo_type,
            dst_api_type,
            dst_repo_id,
            dst_repo_type,
        )

        self.check_repo(
            api_type=dst_api_type,
            repo_id=dst_repo_id,
            repo_type=dst_repo_type,
            visibility=visibility,
        )

        src_files = _repo_file_metadata_by_path(
            self.get_repo_files_metadata(
                api_type=src_api_type,
                repo_id=src_repo_id,
                repo_type=src_repo_type,
                revision=revision,
            )
        )
        dst_files = _repo_file_metadata_by_path(
            self.get_repo_files_metadata(
                api_type=dst_api_type,
                repo_id=dst_repo_id,
                repo_type=dst_repo_type,
                revision=revision,
            )
        )

        mirror_tasks: list[str] = []
        files_count = len(src_files)
        for index, (repo_file, src_metadata) in enumerate(src_files.items(), start=1):
            dst_metadata = dst_files.get(repo_file)
            if dst_metadata is None:
                mirror_tasks.append(repo_file)
                continue

            if not _repo_file_hash_matches(src_metadata, dst_metadata):
                mirror_tasks.append(repo_file)
                logger.info(
                    "[%s/%s] %s 已存在于目标仓库中但 hash 缺失或不同, 将重新镜像",
                    index,
                    files_count,
                    repo_file,
                )
                continue

            logger.info(
                "[%s/%s] %s 已存在于目标仓库中且 hash 相同, 跳过镜像",
                index,
                files_count,
                repo_file,
            )

        logger.info("需要镜像的文件数量: %s", len(mirror_tasks))
        if not mirror_tasks:
            logger.info("镜像仓库文件完成")
            return
        mirror_count = len(mirror_tasks)

        actual_retry_times = max(1, retry_times)

        @retryable(
            times=actual_retry_times,
            describe="镜像仓库文件",
            catch_exceptions=(Exception),
            raise_exception=(RuntimeError),
            retry_on_none=False,
        )
        def _mirror_file(repo_file: str, index: int) -> None:
            with tempfile.TemporaryDirectory(prefix="repo-mirror-") as tmp_dir_str:
                tmp_dir = Path(tmp_dir_str)
                file_path = tmp_dir / repo_file
                logger.info("[%s/%s] 镜像 %s", index, mirror_count, repo_file)

                if use_fast_download:
                    download_url = self.get_repo_file_download_url(
                        api_type=src_api_type,
                        repo_id=src_repo_id,
                        file_path=repo_file,
                        repo_type=src_repo_type,
                        revision=revision,
                    )
                    download_file(
                        url=download_url,
                        path=file_path.parent,
                        save_name=file_path.name,
                        tool=download_tool,
                        progress=download_progress,
                        split=download_split,
                    )
                elif src_api_type == "huggingface":
                    self.hf_api.hf_hub_download(
                        **_add_revision(
                            {
                                "repo_id": src_repo_id,
                                "repo_type": src_repo_type,
                                "filename": repo_file,
                                "local_dir": tmp_dir,
                            },
                            revision,
                        )
                    )
                else:
                    _ensure_modelscope()
                    from modelscope import snapshot_download

                    snapshot_download(
                        **_add_revision(
                            {
                                "repo_id": src_repo_id,
                                "repo_type": src_repo_type,
                                "allow_patterns": repo_file,
                                "local_dir": tmp_dir,
                            },
                            revision,
                        )
                    )

                if not file_path.exists():
                    raise FileNotFoundError(f"镜像下载后的文件不存在: {file_path}")

                upload_kwargs = _add_revision(
                    {
                        "repo_id": dst_repo_id,
                        "repo_type": dst_repo_type,
                        "path_in_repo": repo_file,
                        "path_or_fileobj": file_path,
                        "commit_message": f"Mirror {repo_file}",
                    },
                    revision,
                )
                if dst_api_type == "huggingface":
                    self.hf_api.upload_file(**upload_kwargs)
                else:
                    upload_kwargs["token"] = self.ms_token
                    self.ms_api.upload_file(**upload_kwargs)

        err: list[Exception] = []
        err_lock = Lock()

        def _run_mirror(task: tuple[int, str]) -> None:
            index, repo_file = task
            try:
                _mirror_file(repo_file=repo_file, index=index)
            except RuntimeError as e:
                with err_lock:
                    err.append(e)
                logger.error("[%s/%s] 镜像 %s 最终失败: %s", index, mirror_count, repo_file, e)

        max_workers = max(1, num_threads)
        if max_workers == 1:
            for task in enumerate(mirror_tasks, start=1):
                _run_mirror(task)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                list(executor.map(_run_mirror, enumerate(mirror_tasks, start=1)))

        if err:
            raise AggregateError(f"镜像 {src_repo_id} -> {dst_repo_id} 时发生了错误", err)

        logger.info("镜像仓库文件完成")

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
