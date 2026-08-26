"""Native snapshot schema encoding and decoding."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from .models import (
    SNAPSHOT_SCHEMA_VERSION,
    DirectUrlArchiveInfo,
    DirectUrlDirInfo,
    DirectUrlSnapshot,
    DirectUrlVcsInfo,
    ExtensionSnapshot,
    ExtensionSourceType,
    JsonObject,
    JsonValue,
    PackageSnapshot,
    PythonSnapshot,
    RepositorySnapshot,
    SourceType,
    SystemSnapshot,
    WebUiIdentitySnapshot,
    WebUiSnapshot,
    WheelSnapshot,
    logger,
)


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
        logger.warning("解析 direct_url 失败: %s", raw_direct_url[:120])
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
    logger.debug("解析快照: 包 %s 个, 扩展 %s 个", len(packages), len(extensions))

    return WebUiSnapshot(
        schema_version=schema_version,
        created_at=_require_str(_get_required(data, "created_at", "created_at"), "created_at"),
        webui=_webui_identity_from_json(_get_required(data, "webui", "webui"), "webui"),
        python=_python_from_json(_get_required(data, "python", "python"), "python"),
        packages=packages,
        kernel=_repository_from_json(_get_required(data, "kernel", "kernel"), "kernel"),
        extensions=extensions,
        system=_system_from_json(data["system"], "system") if "system" in data else _collect_current_system_info(),
    )


def _collect_current_system_info() -> SystemSnapshot:
    from .collection import collect_system_info

    return collect_system_info()
