"""WebUI 环境快照工具"""

from __future__ import annotations

import json
import platform
import re
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
from sd_webui_all_in_one.config import SD_WEBUI_ALL_IN_ONE_SNAPSHOT_DIR


SNAPSHOT_SCHEMA_VERSION = 1
"""环境快照结构版本"""

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
SourceType: TypeAlias = Literal["vcs", "local-directory", "archive", "unknown"]
ExtensionSourceType: TypeAlias = Literal["git", "comfy-registry", "file", "unknown"]

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
    system: SystemSnapshot = field(default_factory=lambda: collect_system_info())

    def to_dict(self) -> JsonObject:
        """转换为 JSON 可序列化结构

        Returns:
            JsonObject: JSON 可序列化对象。
        """
        return cast(JsonObject, snapshot_to_dict(self))


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


def collect_python_info() -> PythonSnapshot:
    """采集当前 Python 解释器信息

    Returns:
        PythonSnapshot: 当前 Python 解释器快照。
    """
    return PythonSnapshot(
        version=platform.python_version(),
        implementation=platform.python_implementation(),
        executable=Path(sys.executable),
        platform=sys.platform,
    )


def collect_system_info() -> SystemSnapshot:
    """采集当前系统和架构信息

    Returns:
        SystemSnapshot: 当前系统环境快照。
    """
    return SystemSnapshot(
        system=platform.system() or sys.platform,
        architecture=platform.machine() or "unknown",
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


def _require_object(data: object, field_name: str) -> JsonObject:
    if not isinstance(data, dict):
        raise ValueError(f"快照字段 '{field_name}' 应为对象")
    return cast(JsonObject, data)


def _require_list(data: object, field_name: str) -> list[JsonValue]:
    if not isinstance(data, list):
        raise ValueError(f"快照字段 '{field_name}' 应为列表")
    return cast(list[JsonValue], data)


def _require_str(data: object, field_name: str) -> str:
    if not isinstance(data, str):
        raise ValueError(f"快照字段 '{field_name}' 应为字符串")
    return data


def _optional_str(data: object, field_name: str) -> str | None:
    if data is None:
        return None
    return _require_str(data, field_name)


def _require_bool(data: object, field_name: str) -> bool:
    if not isinstance(data, bool):
        raise ValueError(f"快照字段 '{field_name}' 应为布尔值")
    return data


def _optional_bool(data: object, field_name: str) -> bool | None:
    if data is None:
        return None
    return _require_bool(data, field_name)


def _require_path(data: object, field_name: str) -> Path:
    return Path(_require_str(data, field_name))


def _get_required(data: JsonObject, key: str, field_name: str) -> JsonValue:
    if key not in data:
        raise ValueError(f"快照缺少字段 '{field_name}'")
    return data[key]


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


def _direct_url_from_json(value: JsonValue, field_name: str) -> DirectUrlSnapshot | None:
    if value is None:
        return None

    direct_url = _require_object(value, field_name)
    return DirectUrlSnapshot(
        url=_optional_str(direct_url.get("url"), f"{field_name}.url"),
        subdirectory=_optional_str(direct_url.get("subdirectory"), f"{field_name}.subdirectory"),
        vcs_info=_parse_direct_url_vcs_info(direct_url.get("vcs_info")),
        dir_info=_parse_direct_url_dir_info(direct_url.get("dir_info")),
        archive_info=_parse_direct_url_archive_info(direct_url.get("archive_info")),
        extra=_json_extra(direct_url, {"url", "subdirectory", "vcs_info", "dir_info", "archive_info"}),
    )


def _wheel_from_json(value: JsonValue, field_name: str) -> WheelSnapshot | None:
    if value is None:
        return None

    wheel = _require_object(value, field_name)
    raw_tags = wheel.get("tags", [])
    tags = [_require_str(tag, f"{field_name}.tags[]") for tag in _require_list(raw_tags, f"{field_name}.tags")]
    return WheelSnapshot(
        generator=_optional_str(wheel.get("generator"), f"{field_name}.generator"),
        root_is_purelib=_optional_bool(wheel.get("root_is_purelib"), f"{field_name}.root_is_purelib"),
        tags=tags,
    )


def _package_from_json(value: JsonValue, field_name: str) -> PackageSnapshot:
    package = _require_object(value, field_name)
    source_type = package.get("source_type", "unknown")
    if source_type not in ("vcs", "local-directory", "archive", "unknown"):
        raise ValueError(f"快照字段 '{field_name}.source_type' 不支持: {source_type}")

    return PackageSnapshot(
        name=_require_str(_get_required(package, "name", f"{field_name}.name"), f"{field_name}.name"),
        version=_require_str(_get_required(package, "version", f"{field_name}.version"), f"{field_name}.version"),
        installer=_optional_str(package.get("installer"), f"{field_name}.installer"),
        requested=_require_bool(package.get("requested", False), f"{field_name}.requested"),
        editable=_require_bool(package.get("editable", False), f"{field_name}.editable"),
        direct_url=_direct_url_from_json(package.get("direct_url"), f"{field_name}.direct_url"),
        source_type=cast(SourceType, source_type),
        wheel=_wheel_from_json(package.get("wheel"), f"{field_name}.wheel"),
    )


def _python_from_json(value: JsonValue, field_name: str) -> PythonSnapshot:
    python = _require_object(value, field_name)
    return PythonSnapshot(
        version=_require_str(_get_required(python, "version", f"{field_name}.version"), f"{field_name}.version"),
        implementation=_require_str(_get_required(python, "implementation", f"{field_name}.implementation"), f"{field_name}.implementation"),
        executable=_require_path(_get_required(python, "executable", f"{field_name}.executable"), f"{field_name}.executable"),
        platform=_require_str(_get_required(python, "platform", f"{field_name}.platform"), f"{field_name}.platform"),
    )


def _system_from_json(value: JsonValue, field_name: str) -> SystemSnapshot:
    system = _require_object(value, field_name)
    return SystemSnapshot(
        system=_require_str(_get_required(system, "system", f"{field_name}.system"), f"{field_name}.system"),
        architecture=_require_str(_get_required(system, "architecture", f"{field_name}.architecture"), f"{field_name}.architecture"),
    )


def _repository_from_json(value: JsonValue, field_name: str) -> RepositorySnapshot | None:
    if value is None:
        return None

    repo = _require_object(value, field_name)
    return RepositorySnapshot(
        path=_require_path(_get_required(repo, "path", f"{field_name}.path"), f"{field_name}.path"),
        name=_require_str(_get_required(repo, "name", f"{field_name}.name"), f"{field_name}.name"),
        is_git_repo=_require_bool(_get_required(repo, "is_git_repo", f"{field_name}.is_git_repo"), f"{field_name}.is_git_repo"),
        url=_optional_str(repo.get("url"), f"{field_name}.url"),
        branch=_optional_str(repo.get("branch"), f"{field_name}.branch"),
        commit=_optional_str(repo.get("commit"), f"{field_name}.commit"),
        commit_date=_optional_str(repo.get("commit_date"), f"{field_name}.commit_date"),
        message=_optional_str(repo.get("message"), f"{field_name}.message"),
        error=_optional_str(repo.get("error"), f"{field_name}.error"),
        dirty=_optional_bool(repo.get("dirty"), f"{field_name}.dirty"),
    )


def _extension_from_json(value: JsonValue, field_name: str) -> ExtensionSnapshot:
    extension = _require_object(value, field_name)
    is_git_repo = _require_bool(_get_required(extension, "is_git_repo", f"{field_name}.is_git_repo"), f"{field_name}.is_git_repo")
    source_type = extension.get("source_type", "git" if is_git_repo else "unknown")
    if source_type not in ("git", "comfy-registry", "file", "unknown"):
        raise ValueError(f"快照字段 '{field_name}.source_type' 不支持: {source_type}")
    dependencies = extension.get("dependencies", [])
    return ExtensionSnapshot(
        name=_require_str(_get_required(extension, "name", f"{field_name}.name"), f"{field_name}.name"),
        path=_require_path(_get_required(extension, "path", f"{field_name}.path"), f"{field_name}.path"),
        enabled=_optional_bool(extension.get("enabled"), f"{field_name}.enabled"),
        is_git_repo=is_git_repo,
        url=_optional_str(extension.get("url"), f"{field_name}.url"),
        branch=_optional_str(extension.get("branch"), f"{field_name}.branch"),
        commit=_optional_str(extension.get("commit"), f"{field_name}.commit"),
        commit_date=_optional_str(extension.get("commit_date"), f"{field_name}.commit_date"),
        message=_optional_str(extension.get("message"), f"{field_name}.message"),
        error=_optional_str(extension.get("error"), f"{field_name}.error"),
        dirty=_optional_bool(extension.get("dirty"), f"{field_name}.dirty"),
        source_type=cast(ExtensionSourceType, source_type),
        registry_id=_optional_str(extension.get("registry_id"), f"{field_name}.registry_id"),
        registry_version=_optional_str(extension.get("registry_version"), f"{field_name}.registry_version"),
        download_url=_optional_str(extension.get("download_url"), f"{field_name}.download_url"),
        repository=_optional_str(extension.get("repository"), f"{field_name}.repository"),
        dependencies=[_require_str(item, f"{field_name}.dependencies[]") for item in _require_list(dependencies, f"{field_name}.dependencies")],
    )


def _webui_identity_from_json(value: JsonValue, field_name: str) -> WebUiIdentitySnapshot:
    webui = _require_object(value, field_name)
    return WebUiIdentitySnapshot(
        name=_require_str(_get_required(webui, "name", f"{field_name}.name"), f"{field_name}.name"),
        type=_require_str(_get_required(webui, "type", f"{field_name}.type"), f"{field_name}.type"),
        path=_require_path(_get_required(webui, "path", f"{field_name}.path"), f"{field_name}.path"),
    )


def snapshot_from_dict(data: JsonObject) -> WebUiSnapshot:
    """从 JSON 对象解析 WebUI 快照

    Args:
        data (JsonObject):
            快照 JSON 对象。

    Returns:
        WebUiSnapshot: 解析后的 WebUI 环境快照。

    Raises:
        ValueError:
            当输入数据无效或快照内容不匹配时抛出。
    """
    schema_version = _get_required(data, "schema_version", "schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        raise ValueError("快照字段 'schema_version' 应为整数")
    if schema_version != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError(f"不支持的快照结构版本: {schema_version}")

    packages = [_package_from_json(item, f"packages[{index}]") for index, item in enumerate(_require_list(_get_required(data, "packages", "packages"), "packages"))]
    extensions = [_extension_from_json(item, f"extensions[{index}]") for index, item in enumerate(_require_list(_get_required(data, "extensions", "extensions"), "extensions"))]

    return WebUiSnapshot(
        schema_version=schema_version,
        created_at=_require_str(_get_required(data, "created_at", "created_at"), "created_at"),
        webui=_webui_identity_from_json(_get_required(data, "webui", "webui"), "webui"),
        python=_python_from_json(_get_required(data, "python", "python"), "python"),
        packages=packages,
        kernel=_repository_from_json(_get_required(data, "kernel", "kernel"), "kernel"),
        extensions=extensions,
        system=_system_from_json(data["system"], "system") if "system" in data else collect_system_info(),
    )


def load_snapshot(path: Path) -> WebUiSnapshot:
    """从 JSON 文件加载 WebUI 快照

    Args:
        path (Path):
            快照 JSON 文件路径。

    Returns:
        WebUiSnapshot: 从文件加载的 WebUI 环境快照。

    Raises:
        ValueError:
            当输入数据无效或快照内容不匹配时抛出。
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"快照文件不是有效 JSON: {path}") from e
    snapshot_data = _require_object(data, "snapshot")
    if _is_comfyui_manager_snapshot(snapshot_data):
        return comfyui_manager_snapshot_from_dict(snapshot_data, path)
    return snapshot_from_dict(snapshot_data)


def _is_comfyui_manager_snapshot(data: JsonObject) -> bool:
    return any(key in data for key in ("git_custom_nodes", "cnr_custom_nodes", "file_custom_nodes")) and "schema_version" not in data


def _package_snapshots_from_comfyui_manager_pips(value: JsonValue) -> list[PackageSnapshot]:
    if not isinstance(value, dict):
        return []
    packages: list[PackageSnapshot] = []
    for name, version in value.items():
        if not isinstance(name, str):
            continue
        if isinstance(version, str) and version:
            packages.append(PackageSnapshot(name=name, version=version))
    return sorted(packages, key=lambda item: item.name.lower())


def comfyui_manager_snapshot_from_dict(data: JsonObject, snapshot_path: Path | None = None) -> WebUiSnapshot:
    """将 ComfyUI-Manager 原生快照转换为本项目快照对象。

    Args:
        data (JsonObject):
            ComfyUI-Manager 原生快照数据。
        snapshot_path (Path | None):
            快照文件路径，用于推导快照来源目录。

    Returns:
        WebUiSnapshot:
            转换后的本项目快照对象。
    """
    from sd_webui_all_in_one.base_manager.base import get_repo_name_from_url

    extensions: list[ExtensionSnapshot] = []
    git_nodes = data.get("git_custom_nodes", {})
    if isinstance(git_nodes, dict):
        for url, raw_info in git_nodes.items():
            if not isinstance(url, str) or not url:
                continue
            info = raw_info if isinstance(raw_info, dict) else {}
            name = get_repo_name_from_url(url)
            commit = info.get("hash") if isinstance(info.get("hash"), str) else None
            disabled = info.get("disabled") if isinstance(info.get("disabled"), bool) else False
            extensions.append(
                ExtensionSnapshot(
                    name=name,
                    path=Path("custom_nodes") / name,
                    enabled=not disabled,
                    is_git_repo=True,
                    url=url,
                    commit=commit,
                    source_type="git",
                )
            )

    cnr_nodes = data.get("cnr_custom_nodes", {})
    if isinstance(cnr_nodes, dict):
        for node_id, version in cnr_nodes.items():
            if not isinstance(node_id, str) or not node_id:
                continue
            version_text = str(version) if version is not None else None
            extensions.append(
                ExtensionSnapshot(
                    name=node_id,
                    path=Path("custom_nodes") / node_id,
                    enabled=True,
                    is_git_repo=False,
                    source_type="comfy-registry",
                    registry_id=node_id,
                    registry_version=version_text,
                )
            )

    file_nodes = data.get("file_custom_nodes", [])
    if isinstance(file_nodes, list):
        for raw_item in file_nodes:
            if not isinstance(raw_item, dict):
                continue
            filename = raw_item.get("filename")
            if not isinstance(filename, str) or not filename:
                continue
            disabled = raw_item.get("disabled") if isinstance(raw_item.get("disabled"), bool) else filename.endswith(".disabled")
            extensions.append(
                ExtensionSnapshot(
                    name=filename,
                    path=Path("custom_nodes") / filename,
                    enabled=not disabled,
                    is_git_repo=False,
                    source_type="file",
                )
            )

    comfyui_commit = data.get("comfyui")
    kernel = None
    if isinstance(comfyui_commit, str) and comfyui_commit:
        kernel = RepositorySnapshot(
            path=Path("."),
            name="ComfyUI",
            is_git_repo=True,
            commit=comfyui_commit,
        )

    return WebUiSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        created_at=utc_now_iso(),
        webui=WebUiIdentitySnapshot(name="ComfyUI", type="comfyui", path=snapshot_path.parent if snapshot_path else Path(".")),
        python=collect_python_info(),
        packages=_package_snapshots_from_comfyui_manager_pips(data.get("pips")),
        kernel=kernel,
        extensions=extensions,
        system=collect_system_info(),
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
    """采集当前 Python 环境已安装软件包信息

    Returns:
        list[PackageSnapshot]: 已安装 Python 包快照列表。
    """
    packages: list[PackageSnapshot] = []
    for dist in metadata.distributions():
        try:
            name = dist.metadata["Name"]
        except KeyError:
            continue
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
    """将仓库状态转换为快照字段

    Args:
        state (RepositoryState):
            仓库检查结果。

    Returns:
        RepositorySnapshot: 仓库快照对象。
    """
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
    """检查 Git 仓库是否存在未提交变更

    Args:
        path (Path):
            Git 仓库路径。
        is_git_repo (bool):
            目标路径是否为 Git 仓库。

    Returns:
        bool | None: Git 仓库是否存在未提交变更；非 Git 仓库或检查失败时返回 None。
    """
    if not is_git_repo:
        return None
    try:
        return run_git_output(path, "status", "--porcelain") != ""
    except Exception:
        return None


def collect_repository_snapshot(path: Path) -> RepositorySnapshot:
    """采集 Git 仓库快照

    Args:
        path (Path):
            Git 仓库路径。

    Returns:
        RepositorySnapshot: Git 仓库快照。
    """
    state = inspect_repository(path)
    snapshot = repository_state_to_snapshot(state)
    snapshot.dirty = repository_dirty(path, state.is_git_repo)
    return snapshot


def collect_git_extensions(
    extension_dir: Path,
    enabled_resolver: ExtensionEnabledResolver | None = None,
    ignored_names: set[str] | None = None,
) -> list[ExtensionSnapshot]:
    """采集扩展目录中的 Git 扩展快照

    Args:
        extension_dir (Path):
            扩展根目录。
        enabled_resolver (ExtensionEnabledResolver | None):
            用于判断扩展启用状态的回调。
        ignored_names (set[str] | None):
            采集扩展时需要忽略的目录名。

    Returns:
        list[ExtensionSnapshot]: Git 扩展快照列表。
    """
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
                source_type="git",
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
    """构建 WebUI 环境快照

    Args:
        webui_name (str):
            WebUI 显示名称。
        webui_type (str):
            WebUI 类型标识。
        webui_path (Path):
            WebUI 根目录。
        include_packages (bool):
            是否采集当前 Python 包列表。
        extensions (list[ExtensionSnapshot] | None):
            已采集的扩展快照列表。

    Returns:
        WebUiSnapshot: WebUI 环境快照。
    """
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
        system=collect_system_info(),
    )


def save_snapshot(snapshot: WebUiSnapshot, output: Path) -> Path:
    """保存快照 JSON 文件

    Args:
        snapshot (WebUiSnapshot):
            WebUI 环境快照。
        output (Path):
            快照输出路径或目录。

    Returns:
        Path: 已写入的快照文件路径。
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot_to_dict(snapshot), ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _safe_filename_part(value: str) -> str:
    part = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return part.strip("-._") or "snapshot"


def _snapshot_timestamp(snapshot: WebUiSnapshot) -> str:
    return _safe_filename_part(snapshot.created_at.replace(":", "").replace("+", ""))


def default_snapshot_output(snapshot: WebUiSnapshot, output_dir: Path | None = None) -> Path:
    """生成默认快照输出文件路径

    Args:
        snapshot (WebUiSnapshot):
            WebUI 环境快照。
        output_dir (Path | None):
            快照输出目录。

    Returns:
        Path: 默认快照输出路径。
    """
    if output_dir is None:
        output_dir = SD_WEBUI_ALL_IN_ONE_SNAPSHOT_DIR
    filename = f"{_safe_filename_part(snapshot.webui.type)}-{_snapshot_timestamp(snapshot)}.json"
    return output_dir / filename


def resolve_snapshot_output(snapshot: WebUiSnapshot, output_dir: Path | None = None) -> Path:
    """解析快照输出文件路径

    Args:
        snapshot (WebUiSnapshot):
            WebUI 环境快照。
        output_dir (Path | None):
            快照输出目录。

    Returns:
        Path: 最终快照输出路径。
    """
    if output_dir is None:
        return default_snapshot_output(snapshot)
    return default_snapshot_output(snapshot, output_dir=output_dir)
