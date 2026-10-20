"""仓库文件元数据归一化工具"""

from typing import Any

from sd_webui_all_in_one.repo_manager.types import RepoFileMetadata
from sd_webui_all_in_one.repo_manager.utils import _get_first_mapping_or_attr


def _ms_repo_file_path(item: Any) -> str:
    return str(_get_first_mapping_or_attr(item, ("Path", "path"), "") or "")


def _ms_repo_directory_paths(all_paths: list[str]) -> set[str]:
    directory_paths = set()
    for path in all_paths:
        parent = path.rpartition("/")[0]
        while parent:
            directory_paths.add(parent)
            parent = parent.rpartition("/")[0]
    return directory_paths


def _ms_repo_file_is_dir(item: Any, inferred_directory_paths: set[str]) -> bool:
    entry_type = _get_first_mapping_or_attr(item, ("Type", "type"))
    if entry_type is not None:
        return str(entry_type).lower() in {"tree", "directory", "dir"}

    is_dir = _get_first_mapping_or_attr(item, ("IsDir", "is_dir"))
    if is_dir is not None:
        return bool(is_dir)

    # ModelScope 1.38 的兼容接口仅保留 Path / Size。Git 仓库中的目录
    # 必然是其他条目的父路径，因此可在不把零字节文件误判为目录的前提下恢复类型。
    return _ms_repo_file_path(item).rstrip("/") in inferred_directory_paths


def _repo_file_metadata_by_path(repo_files_metadata: list[RepoFileMetadata]) -> dict[str, RepoFileMetadata]:
    return {metadata["path"]: metadata for metadata in repo_files_metadata if metadata.get("type") == "file" and metadata.get("path")}


def _normalize_sha256(value: Any) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip().lower()
    return normalized or None


def _repo_file_hash_matches(src_metadata: RepoFileMetadata, dst_metadata: RepoFileMetadata) -> bool:
    src_sha256 = _normalize_sha256(src_metadata.get("sha256"))
    dst_sha256 = _normalize_sha256(dst_metadata.get("sha256"))
    return src_sha256 is not None and dst_sha256 is not None and src_sha256 == dst_sha256


def _normalize_file_size(value: Any) -> int | None:
    try:
        size = int(value)
    except (TypeError, ValueError):
        return None
    return size if size >= 0 else None
