"""WebUI 环境快照工具"""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Callable, Literal, TypeAlias, cast

from sd_webui_all_in_one.base_manager.repository_inspector import (
    RepositoryState,
    inspect_repository,
    run_git_output,
)


SNAPSHOT_SCHEMA_VERSION = 1
"""环境快照结构版本"""

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
SourceType: TypeAlias = Literal["vcs", "local-directory", "archive", "unknown"]

ExtensionEnabledResolver = Callable[[str, Path], bool | None]
"""扩展启用状态解析器"""


@dataclass(slots=True)
class DirectUrlVcsInfo:
    """PEP 610 VCS 来源信息"""

    vcs: str | None = None
    requested_revision: str | None = None
    commit_id: str | None = None
    resolved_revision_type: str | None = None
    extra: JsonObject = field(default_factory=dict)

    def to_dict(self) -> JsonObject:
        """转换为 direct_url.json 兼容结构"""
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
        """转换为 direct_url.json 兼容结构"""
        return _compact_json_object({"editable": self.editable}, self.extra)


@dataclass(slots=True)
class DirectUrlArchiveInfo:
    """PEP 610 归档来源信息"""

    hash: str | None = None
    hashes: dict[str, str] | None = None
    extra: JsonObject = field(default_factory=dict)

    def to_dict(self) -> JsonObject:
        """转换为 direct_url.json 兼容结构"""
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
        """转换为 direct_url.json 兼容结构"""
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

    def to_dict(self) -> JsonObject:
        """转换为 JSON 可序列化结构"""
        return cast(JsonObject, snapshot_to_dict(self))


def utc_now_iso() -> str:
    """获取当前 UTC 时间"""
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
    """将快照数据转换为 JSON 可序列化结构"""
    if isinstance(value, (DirectUrlVcsInfo, DirectUrlDirInfo, DirectUrlArchiveInfo, DirectUrlSnapshot)):
        return value.to_dict()
    if isinstance(value, Path):
        return value.as_posix()
    if is_dataclass(value) and not isinstance(value, type):
        return {field_info.name: snapshot_to_dict(getattr(value, field_info.name)) for field_info in fields(value)}
    if isinstance(value, dict):
        return {str(key): snapshot_to_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [snapshot_to_dict(item) for item in value]
    return cast(JsonValue, value)


def json_safe(value: object) -> JsonValue:
    """将快照数据转换为 JSON 可序列化结构"""
    return snapshot_to_dict(value)


def collect_python_info() -> PythonSnapshot:
    """采集当前 Python 解释器信息"""
    return PythonSnapshot(
        version=platform.python_version(),
        implementation=platform.python_implementation(),
        executable=Path(sys.executable),
        platform=sys.platform,
    )


def _read_distribution_text(dist: metadata.Distribution, filename: str) -> str | None:
    try:
        return dist.read_text(filename)
    except Exception:
        return None


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _bool_or_none(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def _json_extra(data: JsonObject, known_keys: set[str]) -> JsonObject:
    return {key: value for key, value in data.items() if key not in known_keys}


def _parse_direct_url_vcs_info(value: JsonValue) -> DirectUrlVcsInfo | None:
    if not isinstance(value, dict):
        return None
    return DirectUrlVcsInfo(
        vcs=_string_or_none(value.get("vcs")),
        requested_revision=_string_or_none(value.get("requested_revision")),
        commit_id=_string_or_none(value.get("commit_id")),
        resolved_revision_type=_string_or_none(value.get("resolved_revision_type")),
        extra=_json_extra(value, {"vcs", "requested_revision", "commit_id", "resolved_revision_type"}),
    )


def _parse_direct_url_dir_info(value: JsonValue) -> DirectUrlDirInfo | None:
    if not isinstance(value, dict):
        return None
    return DirectUrlDirInfo(
        editable=_bool_or_none(value.get("editable")),
        extra=_json_extra(value, {"editable"}),
    )


def _parse_archive_hashes(value: JsonValue) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    hashes = {str(key): item for key, item in value.items() if isinstance(item, str)}
    return hashes or None


def _parse_direct_url_archive_info(value: JsonValue) -> DirectUrlArchiveInfo | None:
    if not isinstance(value, dict):
        return None
    return DirectUrlArchiveInfo(
        hash=_string_or_none(value.get("hash")),
        hashes=_parse_archive_hashes(value.get("hashes")),
        extra=_json_extra(value, {"hash", "hashes"}),
    )


def _parse_direct_url(raw_direct_url: str | None) -> DirectUrlSnapshot | None:
    if not raw_direct_url:
        return None
    try:
        data = json.loads(raw_direct_url)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    direct_url = cast(JsonObject, data)
    return DirectUrlSnapshot(
        url=_string_or_none(direct_url.get("url")),
        subdirectory=_string_or_none(direct_url.get("subdirectory")),
        vcs_info=_parse_direct_url_vcs_info(direct_url.get("vcs_info")),
        dir_info=_parse_direct_url_dir_info(direct_url.get("dir_info")),
        archive_info=_parse_direct_url_archive_info(direct_url.get("archive_info")),
        extra=_json_extra(direct_url, {"url", "subdirectory", "vcs_info", "dir_info", "archive_info"}),
    )


def _source_type_from_direct_url(direct_url: DirectUrlSnapshot | None) -> SourceType:
    if direct_url is None:
        return "unknown"
    if direct_url.vcs_info is not None:
        return "vcs"
    if direct_url.dir_info is not None:
        return "local-directory"
    if direct_url.archive_info is not None:
        return "archive"
    return "unknown"


def _editable_from_direct_url(direct_url: DirectUrlSnapshot | None) -> bool:
    if direct_url is None:
        return False
    if direct_url.dir_info is None:
        return False
    return bool(direct_url.dir_info.editable)


def _parse_wheel_metadata(raw_wheel: str | None) -> WheelSnapshot | None:
    if not raw_wheel:
        return None

    generator: str | None = None
    root_is_purelib: bool | None = None
    tags: list[str] = []
    for line in raw_wheel.splitlines():
        key, sep, value = line.partition(":")
        if sep == "":
            continue
        normalized_key = key.strip().lower()
        normalized_value = value.strip()
        if normalized_key == "generator":
            generator = normalized_value
        elif normalized_key == "root-is-purelib":
            root_is_purelib = normalized_value.lower() == "true"
        elif normalized_key == "tag":
            tags.append(normalized_value)

    return WheelSnapshot(
        generator=generator,
        root_is_purelib=root_is_purelib,
        tags=tags,
    )


def collect_installed_packages() -> list[PackageSnapshot]:
    """采集当前 Python 环境已安装软件包信息"""
    packages: list[PackageSnapshot] = []
    for dist in metadata.distributions():
        name = dist.metadata.get("Name")
        if not name:
            continue

        direct_url = _parse_direct_url(_read_distribution_text(dist, "direct_url.json"))
        installer_raw = _read_distribution_text(dist, "INSTALLER")
        requested_raw = _read_distribution_text(dist, "REQUESTED")
        wheel = _parse_wheel_metadata(_read_distribution_text(dist, "WHEEL"))

        packages.append(
            PackageSnapshot(
                name=name,
                version=dist.version,
                installer=installer_raw.strip() if installer_raw else None,
                requested=requested_raw is not None,
                editable=_editable_from_direct_url(direct_url),
                direct_url=direct_url,
                source_type=_source_type_from_direct_url(direct_url),
                wheel=wheel,
            )
        )

    return sorted(packages, key=lambda item: item.name.lower())


def repository_state_to_snapshot(state: RepositoryState) -> RepositorySnapshot:
    """将仓库状态转换为快照字段"""
    return RepositorySnapshot(
        path=state.path,
        name=state.name,
        is_git_repo=state.is_git_repo,
        url=state.url,
        branch=state.branch,
        commit=state.commit,
        commit_date=state.commit_date,
        message=state.message,
        error=state.error,
    )


def repository_dirty(path: Path, is_git_repo: bool) -> bool | None:
    """检查 Git 仓库是否存在未提交变更"""
    if not is_git_repo:
        return None
    try:
        return run_git_output(path, "status", "--porcelain") != ""
    except Exception:
        return None


def collect_repository_snapshot(path: Path) -> RepositorySnapshot:
    """采集 Git 仓库快照"""
    state = inspect_repository(path)
    snapshot = repository_state_to_snapshot(state)
    snapshot.dirty = repository_dirty(path, state.is_git_repo)
    return snapshot


def collect_git_extensions(
    extension_dir: Path,
    enabled_resolver: ExtensionEnabledResolver | None = None,
    ignored_names: set[str] | None = None,
) -> list[ExtensionSnapshot]:
    """采集扩展目录中的 Git 扩展快照"""
    if ignored_names is None:
        ignored_names = {"__pycache__"}
    if not extension_dir.is_dir():
        return []

    extensions: list[ExtensionSnapshot] = []
    for ext_path in sorted(extension_dir.iterdir(), key=lambda item: item.name.lower()):
        if ext_path.name in ignored_names or not ext_path.is_dir():
            continue
        repo = collect_repository_snapshot(ext_path)
        if not repo.is_git_repo:
            continue
        enabled = enabled_resolver(ext_path.name, ext_path) if enabled_resolver is not None else None
        extensions.append(
            ExtensionSnapshot(
                name=ext_path.name,
                path=ext_path,
                enabled=enabled,
                is_git_repo=repo.is_git_repo,
                url=repo.url,
                branch=repo.branch,
                commit=repo.commit,
                commit_date=repo.commit_date,
                message=repo.message,
                error=repo.error,
                dirty=repo.dirty,
            )
        )
    return extensions


def build_webui_snapshot(
    webui_name: str,
    webui_type: str,
    webui_path: Path,
    include_packages: bool = True,
    extensions: list[ExtensionSnapshot] | None = None,
) -> WebUiSnapshot:
    """构建 WebUI 环境快照"""
    return WebUiSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        created_at=utc_now_iso(),
        webui=WebUiIdentitySnapshot(
            name=webui_name,
            type=webui_type,
            path=webui_path,
        ),
        python=collect_python_info(),
        packages=collect_installed_packages() if include_packages else [],
        kernel=collect_repository_snapshot(webui_path),
        extensions=extensions or [],
    )


def save_snapshot(snapshot: WebUiSnapshot, output: Path) -> Path:
    """保存快照 JSON 文件"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot_to_dict(snapshot), ensure_ascii=False, indent=2), encoding="utf-8")
    return output
