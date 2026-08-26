"""Snapshot data models and JSON-safe serialization."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
import platform
from pathlib import Path
from typing import Callable, Literal, TypeAlias, cast

from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger

SNAPSHOT_SCHEMA_VERSION = 1
logger = get_logger(name=LOGGER_NAME, level=LOGGER_LEVEL, color=LOGGER_COLOR)

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
SourceType: TypeAlias = Literal["vcs", "local-directory", "archive", "unknown"]
ExtensionSourceType: TypeAlias = Literal["git", "comfy-registry", "file", "unknown"]
ExtensionEnabledResolver = Callable[[str, Path], bool | None]


def default_system_snapshot() -> SystemSnapshot:
    return SystemSnapshot(system=platform.system(), architecture=platform.machine())


@dataclass(slots=True)
class DirectUrlVcsInfo:
    """PEP 610 VCS 来源信息"""

    vcs: str | None = None
    requested_revision: str | None = None
    commit_id: str | None = None
    resolved_revision_type: str | None = None
    extra: JsonObject = field(default_factory=dict)

    def to_dict(self) -> JsonObject:
        """转换为 direct_url.json 兼容结构

        Returns:
            JsonObject: JSON 可序列化对象。
        """
        return _compact_json_object(
            {
                "vcs": self.vcs,
                "requested_revision": self.requested_revision,
                "commit_id": self.commit_id,
                "resolved_revision_type": self.resolved_revision_type,
            },
            self.extra,
        )


@dataclass(slots=True)
class DirectUrlDirInfo:
    """PEP 610 本地目录来源信息"""

    editable: bool | None = None
    extra: JsonObject = field(default_factory=dict)

    def to_dict(self) -> JsonObject:
        """转换为 direct_url.json 兼容结构

        Returns:
            JsonObject: JSON 可序列化对象。
        """
        return _compact_json_object({"editable": self.editable}, self.extra)


@dataclass(slots=True)
class DirectUrlArchiveInfo:
    """PEP 610 归档来源信息"""

    hash: str | None = None
    hashes: dict[str, str] | None = None
    extra: JsonObject = field(default_factory=dict)

    def to_dict(self) -> JsonObject:
        """转换为 direct_url.json 兼容结构

        Returns:
            JsonObject: JSON 可序列化对象。
        """
        return _compact_json_object({"hash": self.hash, "hashes": self.hashes}, self.extra)


@dataclass(slots=True)
class DirectUrlSnapshot:
    """PEP 610 direct_url.json 来源信息"""

    url: str | None = None
    subdirectory: str | None = None
    vcs_info: DirectUrlVcsInfo | None = None
    dir_info: DirectUrlDirInfo | None = None
    archive_info: DirectUrlArchiveInfo | None = None
    extra: JsonObject = field(default_factory=dict)

    def to_dict(self) -> JsonObject:
        """转换为 direct_url.json 兼容结构

        Returns:
            JsonObject: JSON 可序列化对象。
        """
        return _compact_json_object(
            {
                "url": self.url,
                "subdirectory": self.subdirectory,
                "vcs_info": self.vcs_info,
                "dir_info": self.dir_info,
                "archive_info": self.archive_info,
            },
            self.extra,
        )


@dataclass(slots=True)
class WheelSnapshot:
    """Python wheel 元数据"""

    generator: str | None = None
    root_is_purelib: bool | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PackageSnapshot:
    """已安装 Python 包快照"""

    name: str
    version: str
    installer: str | None = None
    requested: bool = False
    editable: bool = False
    direct_url: DirectUrlSnapshot | None = None
    source_type: SourceType = "unknown"
    wheel: WheelSnapshot | None = None


@dataclass(slots=True)
class PythonSnapshot:
    """当前 Python 解释器快照"""

    version: str
    implementation: str
    executable: Path
    platform: str


@dataclass(slots=True)
class SystemSnapshot:
    """当前系统环境快照"""

    system: str
    architecture: str


@dataclass(slots=True)
class RepositorySnapshot:
    """Git 仓库快照"""

    path: Path
    name: str
    is_git_repo: bool
    url: str | None = None
    branch: str | None = None
    commit: str | None = None
    commit_date: str | None = None
    message: str | None = None
    error: str | None = None
    dirty: bool | None = None


@dataclass(slots=True)
class ExtensionSnapshot:
    """WebUI 扩展快照"""

    name: str
    path: Path
    enabled: bool | None
    is_git_repo: bool
    url: str | None = None
    branch: str | None = None
    commit: str | None = None
    commit_date: str | None = None
    message: str | None = None
    error: str | None = None
    dirty: bool | None = None
    source_type: ExtensionSourceType = "git"
    registry_id: str | None = None
    registry_version: str | None = None
    download_url: str | None = None
    repository: str | None = None
    dependencies: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WebUiIdentitySnapshot:
    """WebUI 身份信息"""

    name: str
    type: str
    path: Path


@dataclass(slots=True)
class WebUiSnapshot:
    """WebUI 环境快照"""

    schema_version: int
    created_at: str
    webui: WebUiIdentitySnapshot
    python: PythonSnapshot
    packages: list[PackageSnapshot] = field(default_factory=list)
    kernel: RepositorySnapshot | None = None
    extensions: list[ExtensionSnapshot] = field(default_factory=list)
    system: SystemSnapshot = field(default_factory=default_system_snapshot)

    def to_dict(self) -> JsonObject:
        """转换为 JSON 可序列化结构

        Returns:
            JsonObject: JSON 可序列化对象。
        """
        return cast(JsonObject, snapshot_to_dict(self))


@dataclass(slots=True)
class SnapshotSummary:
    """快照文件摘要。"""

    path: Path
    filename: str
    created_at: str | None = None
    webui_type: str | None = None
    webui_name: str | None = None
    package_count: int | None = None
    extension_count: int | None = None
    error: str | None = None


@dataclass(slots=True)
class SavedSnapshot:
    """已保存的 WebUI 快照。"""

    path: Path
    snapshot: WebUiSnapshot


def utc_now_iso() -> str:
    """获取当前 UTC 时间

    Returns:
        str: 当前 UTC 时间字符串。
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _compact_json_object(data: dict[str, object], extra: JsonObject | None = None) -> JsonObject:
    """生成不包含空字段的 JSON 对象"""
    result: JsonObject = {}
    for key, value in data.items():
        if value is None:
            continue
        result[key] = snapshot_to_dict(value)
    if extra:
        result.update(extra)
    return result


def snapshot_to_dict(value: object) -> JsonValue:
    """将快照数据转换为 JSON 可序列化结构

    Args:
        value (object):
            需要转换为 JSON 可序列化结构的值。

    Returns:
        JsonValue: JSON 可序列化值。
    """
    if isinstance(value, (DirectUrlVcsInfo, DirectUrlDirInfo, DirectUrlArchiveInfo, DirectUrlSnapshot)):
        return value.to_dict()
    if isinstance(value, Path):
        return value.as_posix()
    if is_dataclass(value) and not isinstance(value, type):
        logger.debug("序列化快照对象: %s", type(value).__name__)
        return {field_info.name: snapshot_to_dict(getattr(value, field_info.name)) for field_info in fields(value)}
    if isinstance(value, dict):
        return {str(key): snapshot_to_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [snapshot_to_dict(item) for item in value]
    return cast(JsonValue, value)


def json_safe(value: object) -> JsonValue:
    """将快照数据转换为 JSON 可序列化结构

    Args:
        value (object):
            需要转换为 JSON 可序列化结构的值。

    Returns:
        JsonValue: JSON 可序列化值。
    """
    return snapshot_to_dict(value)
