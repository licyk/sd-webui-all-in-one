"""API 默认业务方法注册表。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from sd_webui_all_in_one.api_server.adapters import WEBUI_API_ADAPTERS, get_webui_adapter
from sd_webui_all_in_one.api_server.server import ApiMethodRegistry, ApiMethodSpec, ApiTaskContext, ApiTaskRegistry


WEBUI_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "webui_type": {"type": "string", "enum": sorted(WEBUI_API_ADAPTERS)},
        "webui_path": {"type": "string"},
        "options": {"type": "object"},
    },
    "required": ["webui_type", "webui_path"],
}


def _require_str(params: dict[str, Any], name: str) -> str:
    value = params.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Field '{name}' must be a non-empty string")
    return value


def _options(params: dict[str, Any]) -> dict[str, Any]:
    value = params.get("options", {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("Field 'options' must be an object")
    return value


def _adapter(params: dict[str, Any]):
    return get_webui_adapter(_require_str(params, "webui_type"))


def _webui_path(params: dict[str, Any]) -> Path:
    return Path(_require_str(params, "webui_path"))


def _optional_path(value: Any) -> Path | None:
    return Path(value) if isinstance(value, str) and value else None


def version_status(params: dict[str, Any]) -> dict[str, Any]:
    return _adapter(params).repository_status(_webui_path(params))


def version_branches(params: dict[str, Any]) -> dict[str, Any]:
    options = _options(params)
    return _adapter(params).list_branches(_webui_path(params), fetch=bool(options.get("fetch", True)))


def version_commits(params: dict[str, Any]) -> dict[str, Any]:
    options = _options(params)
    limit = options.get("limit", 100)
    if limit is not None:
        limit = int(limit)
    return _adapter(params).list_commits(_webui_path(params), limit=limit)


def snapshot_list(params: dict[str, Any]) -> dict[str, Any]:
    options = _options(params)
    return _adapter(params).list_snapshots(_webui_path(params), snapshot_dir=_optional_path(options.get("snapshot_dir")))


def snapshot_read(params: dict[str, Any]) -> dict[str, Any]:
    return _adapter(params).read_snapshot(Path(_require_str(params, "snapshot_path")))


def snapshot_delete(params: dict[str, Any]) -> dict[str, Any]:
    return _adapter(params).delete_snapshot(Path(_require_str(params, "snapshot_path")))


def extension_list(params: dict[str, Any]) -> dict[str, Any]:
    return _adapter(params).list_extensions(_webui_path(params))


def extension_index(params: dict[str, Any]) -> dict[str, Any]:
    return _adapter(params).fetch_extension_index(_webui_path(params), options=_options(params))


def extension_versions(params: dict[str, Any]) -> dict[str, Any]:
    options = _options(params)
    timeout = options.get("timeout", 20)
    if timeout is not None:
        timeout = int(timeout)
    return _adapter(params).fetch_extension_versions(_require_str(params, "node_id"), timeout=timeout)


def package_versions(params: dict[str, Any]) -> dict[str, Any]:
    options = _options(params)
    timeout = options.get("timeout", 20)
    if timeout is not None:
        timeout = int(timeout)
    return _adapter(params).list_package_versions(
        _require_str(params, "package_name"),
        current_version=options.get("current_version"),
        index_url=str(options.get("index_url") or "https://pypi.org/pypi"),
        timeout=timeout,
    )


def version_switch_branch(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Switching repository branch")
    options = _options(params)
    result = _adapter(params).switch_branch(
        _webui_path(params),
        branch=_require_str(params, "branch"),
        new_url=options.get("new_url"),
        recurse_submodules=bool(options.get("recurse_submodules", False)),
    )
    context.set_progress(100, "done")
    return result


def version_switch_commit(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Switching repository commit")
    result = _adapter(params).switch_commit(_webui_path(params), commit=_require_str(params, "commit"))
    context.set_progress(100, "done")
    return result


def version_update(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Updating repository")
    result = _adapter(params).update(_webui_path(params))
    context.set_progress(100, "done")
    return result


def snapshot_create(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Creating snapshot")
    options = _options(params)
    result = _adapter(params).create_snapshot(
        _webui_path(params),
        include_packages=bool(options.get("include_packages", True)),
        output_dir=_optional_path(options.get("output_dir")),
    )
    context.set_progress(100, "done")
    return result


def snapshot_preview_restore(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Previewing snapshot restore")
    result = _adapter(params).preview_restore_snapshot(
        _webui_path(params),
        snapshot_path=Path(_require_str(params, "snapshot_path")),
        options=_options(params),
    )
    context.set_progress(100, "done")
    return result


def snapshot_restore(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Restoring snapshot")
    result = _adapter(params).restore_snapshot(
        _webui_path(params),
        snapshot_path=Path(_require_str(params, "snapshot_path")),
        options=_options(params),
    )
    context.set_progress(100, "done")
    return result


def extension_set_enabled(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Changing extension status")
    result = _adapter(params).set_extension_enabled(_webui_path(params), name=_require_str(params, "name"), enabled=bool(params.get("enabled")))
    context.set_progress(100, "done")
    return result


def extension_install(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Installing extension")
    options = _options(params)
    result = _adapter(params).install_extension(
        _webui_path(params),
        url=_require_str(params, "url"),
        use_github_mirror=bool(options.get("use_github_mirror", False)),
        custom_github_mirror=options.get("custom_github_mirror"),
    )
    context.set_progress(100, "done")
    return result


def extension_install_index_item(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Installing extension index item")
    options = _options(params)
    item = params.get("item")
    if not isinstance(item, dict):
        raise ValueError("Field 'item' must be an object")
    result = _adapter(params).install_extension_index_item(
        _webui_path(params),
        item,
        use_github_mirror=bool(options.get("use_github_mirror", False)),
        custom_github_mirror=options.get("custom_github_mirror"),
    )
    context.set_progress(100, "done")
    return result


def extension_update(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Updating extension")
    result = _adapter(params).update_extension(_webui_path(params), name=_require_str(params, "name"))
    context.set_progress(100, "done")
    return result


def extension_update_all(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Updating all extensions")
    result = _adapter(params).update_all_extensions(_webui_path(params))
    context.set_progress(100, "done")
    return result


def extension_uninstall(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Uninstalling extension")
    result = _adapter(params).uninstall_extension(_webui_path(params), name=_require_str(params, "name"))
    context.set_progress(100, "done")
    return result


def extension_switch_commit(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Switching extension commit")
    result = _adapter(params).switch_extension_commit(_webui_path(params), name=_require_str(params, "name"), commit=_require_str(params, "commit"))
    context.set_progress(100, "done")
    return result


def extension_switch_branch(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Switching extension branch")
    result = _adapter(params).switch_extension_branch(_webui_path(params), name=_require_str(params, "name"), branch=_require_str(params, "branch"))
    context.set_progress(100, "done")
    return result


def extension_switch_registry_version(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Switching Comfy Registry extension version")
    options = _options(params)
    result = _adapter(params).switch_registry_extension_version(
        _webui_path(params),
        name=_require_str(params, "name"),
        version=_require_str(params, "version"),
        use_uv=bool(options.get("use_uv", True)),
    )
    context.set_progress(100, "done")
    return result


def invokeai_install_version(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    context.log("Installing InvokeAI version")
    options = _options(params)
    result = _adapter(params).install_invokeai_version(
        version=params.get("version"),
        upgrade=bool(options.get("upgrade", False)),
        use_pypi_mirror=bool(options.get("use_pypi_mirror", False)),
        use_uv=bool(options.get("use_uv", True)),
    )
    context.set_progress(100, "done")
    return result


def _sync_spec(name: str, handler: Callable[[dict[str, Any]], dict[str, Any]], description: str, schema: dict[str, Any] | None = None) -> ApiMethodSpec:
    return ApiMethodSpec(name=name, handler=handler, kind="sync", description=description, params_schema=schema or WEBUI_REQUEST_SCHEMA)


def _task_spec(name: str, handler: Callable[[dict[str, Any], ApiTaskContext], dict[str, Any]], description: str) -> ApiMethodSpec:
    return ApiMethodSpec(name=name, handler=handler, kind="task", description=description, params_schema=WEBUI_REQUEST_SCHEMA)


def get_default_methods() -> ApiMethodRegistry:
    """获取默认同步 API 方法。"""
    return {
        "version.status": _sync_spec("version.status", version_status, "Inspect WebUI kernel repository status."),
        "version.branches": _sync_spec("version.branches", version_branches, "List repository branches for a WebUI kernel."),
        "version.commits": _sync_spec("version.commits", version_commits, "List repository commits for a WebUI kernel."),
        "snapshot.list": _sync_spec("snapshot.list", snapshot_list, "List WebUI snapshot files."),
        "snapshot.read": _sync_spec(
            "snapshot.read",
            snapshot_read,
            "Read a snapshot file.",
            {"type": "object", "properties": {"webui_type": {"type": "string"}, "snapshot_path": {"type": "string"}}, "required": ["webui_type", "snapshot_path"]},
        ),
        "snapshot.delete": _sync_spec(
            "snapshot.delete",
            snapshot_delete,
            "Delete a snapshot file.",
            {"type": "object", "properties": {"webui_type": {"type": "string"}, "snapshot_path": {"type": "string"}}, "required": ["webui_type", "snapshot_path"]},
        ),
        "extension.list": _sync_spec("extension.list", extension_list, "List local extensions or custom nodes."),
        "extension.index": _sync_spec("extension.index", extension_index, "Fetch installable extension index items."),
        "extension.versions": _sync_spec("extension.versions", extension_versions, "List Comfy Registry extension versions."),
        "package.versions": _sync_spec("package.versions", package_versions, "List PyPI package versions."),
    }


def get_default_task_methods() -> ApiTaskRegistry:
    """获取默认后台任务 API 方法。"""
    return {
        "version.switch_branch": _task_spec("version.switch_branch", version_switch_branch, "Switch repository branch."),
        "version.switch_commit": _task_spec("version.switch_commit", version_switch_commit, "Switch repository commit."),
        "version.update": _task_spec("version.update", version_update, "Update repository."),
        "snapshot.create": _task_spec("snapshot.create", snapshot_create, "Create a WebUI snapshot."),
        "snapshot.preview_restore": _task_spec("snapshot.preview_restore", snapshot_preview_restore, "Preview WebUI snapshot restore plan."),
        "snapshot.restore": _task_spec("snapshot.restore", snapshot_restore, "Restore a WebUI snapshot."),
        "extension.set_enabled": _task_spec("extension.set_enabled", extension_set_enabled, "Enable or disable an extension."),
        "extension.install": _task_spec("extension.install", extension_install, "Install an extension from Git URL."),
        "extension.install_index_item": _task_spec("extension.install_index_item", extension_install_index_item, "Install an extension from an index item."),
        "extension.update": _task_spec("extension.update", extension_update, "Update one extension."),
        "extension.update_all": _task_spec("extension.update_all", extension_update_all, "Update all extensions."),
        "extension.uninstall": _task_spec("extension.uninstall", extension_uninstall, "Uninstall an extension."),
        "extension.switch_branch": _task_spec("extension.switch_branch", extension_switch_branch, "Switch extension branch."),
        "extension.switch_commit": _task_spec("extension.switch_commit", extension_switch_commit, "Switch extension commit."),
        "extension.switch_registry_version": _task_spec("extension.switch_registry_version", extension_switch_registry_version, "Switch Comfy Registry extension version."),
        "invokeai.install_version": _task_spec("invokeai.install_version", invokeai_install_version, "Install or upgrade InvokeAI from PyPI."),
    }
