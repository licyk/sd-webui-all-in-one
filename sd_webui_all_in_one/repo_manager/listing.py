"""仓库文件列表与文件元数据查询"""

from typing import Any

from sd_webui_all_in_one.config import RETRY_TIMES
from sd_webui_all_in_one.retry_decorator import retryable
from sd_webui_all_in_one.repo_manager.types import (
    ApiType,
    RepoType,
    RepoFileType,
    RepoFileMetadata,
)
from sd_webui_all_in_one.repo_manager.shared import logger
from sd_webui_all_in_one.repo_manager.utils import (
    _add_revision,
    _repo_path_name,
    _get_mapping_or_attr,
    _get_first_mapping_or_attr,
    _object_to_dict,
    _callable_accepts_keyword,
)
from sd_webui_all_in_one.repo_manager.metadata import (
    _ms_repo_file_path,
    _ms_repo_directory_paths,
    _ms_repo_file_is_dir,
)
from sd_webui_all_in_one.repo_manager.client import RepoApiClient


class RepoListingMixin(RepoApiClient):
    """仓库文件列表与文件元数据查询功能"""

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

        def _get_file_path(repo_files: list[Any]) -> list[str]:
            """获取 ModelScope Api 返回的仓库列表中的模型路径"""
            all_paths = [_ms_repo_file_path(item) for item in repo_files]
            directory_paths = _ms_repo_directory_paths(all_paths)
            return [path for item, path in zip(repo_files, all_paths) if path and not _ms_repo_file_is_dir(item, directory_paths)]

        if repo_type == "model":
            repo_files = self._get_ms_model_files(repo_id=repo_id, revision=revision)
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

    def _get_ms_model_files(
        self,
        repo_id: str,
        revision: str | None = None,
    ) -> list[Any]:
        """兼容新旧 ModelScope SDK 获取模型仓库条目。"""
        ms_api = self.ms_api

        # 新版 modelscope.HubApi 是 modelscope_hub.HubApi 的兼容包装层。
        # 包装层的 get_model_files 会丢弃 Type / Sha256，且不再接收 revision；
        # 优先使用其通用接口可以保留完整的 FileInfo 数据。
        for api in (ms_api, getattr(ms_api, "_api", None)):
            list_repo_files = getattr(api, "list_repo_files", None)
            if callable(list_repo_files) and _callable_accepts_keyword(list_repo_files, "repo_id") and _callable_accepts_keyword(list_repo_files, "repo_type"):
                list_kwargs = _add_revision(
                    {
                        "repo_id": repo_id,
                        "repo_type": "model",
                        "recursive": True,
                    },
                    revision,
                )
                return list(list_repo_files(**list_kwargs))

        list_kwargs: dict[str, Any] = {
            "model_id": repo_id,
            "recursive": True,
        }
        if revision is not None and _callable_accepts_keyword(ms_api.get_model_files, "revision"):
            list_kwargs["revision"] = revision
        return list(ms_api.get_model_files(**list_kwargs))

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

        def _normalize_ms_files(repo_files: list[Any]) -> list[RepoFileMetadata]:
            entries = []
            all_paths = [_ms_repo_file_path(item) for item in repo_files]
            directory_paths = _ms_repo_directory_paths(all_paths)
            for item in repo_files:
                is_dir = _ms_repo_file_is_dir(item, directory_paths)
                if is_dir and not include_dirs:
                    continue

                path = _ms_repo_file_path(item)
                entry_type: RepoFileType = "directory" if is_dir else "file"
                sha256 = _get_first_mapping_or_attr(item, ("Sha256", "sha256", "BlobId", "blob_id"))
                is_lfs = _get_first_mapping_or_attr(item, ("IsLFS", "is_lfs"))
                metadata: RepoFileMetadata = {
                    "path": path,
                    "name": _get_first_mapping_or_attr(item, ("Name", "name")) or _repo_path_name(path),
                    "type": entry_type,
                    "size": None if is_dir else _get_first_mapping_or_attr(item, ("Size", "size")),
                    "sha256": None if is_dir else sha256,
                    "is_lfs": None if is_dir else is_lfs,
                    "object_id": None if is_dir else sha256,
                    "revision": _get_first_mapping_or_attr(item, ("Revision", "revision")) or revision,
                }
                if include_raw:
                    metadata["raw"] = _object_to_dict(item)
                entries.append(metadata)
            return entries

        if repo_type == "model":
            repo_files = self._get_ms_model_files(repo_id=repo_id, revision=revision)
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
