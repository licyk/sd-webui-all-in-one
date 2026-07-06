"""API 默认业务方法注册表。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, cast

from sd_webui_all_in_one.api_server.adapters import HOTPATCHER_API_ADAPTER, MODEL_API_ADAPTER, WEBUI_API_ADAPTERS, get_webui_adapter
from sd_webui_all_in_one.api_server.server import ApiMethodRegistry, ApiMethodSpec, ApiTaskContext, ApiTaskRegistry
from sd_webui_all_in_one.base_manager import fooocus_base, sd_trainer_base, sd_webui_base
from sd_webui_all_in_one.env_check import check_torch_version_status
from sd_webui_all_in_one.model_downloader import SUPPORTED_WEBUI_LIST, SupportedWebUiType, export_model_list
from sd_webui_all_in_one.pytorch_manager import auto_detect_pytorch_device_category, export_pytorch_list, get_available_pytorch_device_type


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


def _optional_str(params: dict[str, Any], name: str) -> str | None:
    value = params.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Field '{name}' must be a string")
    return value


def _optional_bool(params: dict[str, Any], name: str, default: bool = False) -> bool:
    value = params.get(name, default)
    return bool(value)


def _require_object(params: dict[str, Any], name: str) -> dict[str, Any]:
    value = params.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"Field '{name}' must be an object")
    return value


def _require_str_list(params: dict[str, Any], name: str) -> list[str]:
    value = params.get(name)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Field '{name}' must be a string list")
    return value


def version_status(params: dict[str, Any]) -> dict[str, Any]:
    """读取 WebUI 内核仓库状态。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 仓库状态信息。
    """
    return _adapter(params).repository_status(_webui_path(params))


def version_branches(params: dict[str, Any]) -> dict[str, Any]:
    """列出 WebUI 内核仓库分支。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 分支列表。
    """
    options = _options(params)
    return _adapter(params).list_branches(_webui_path(params), fetch=bool(options.get("fetch", True)))


def version_commits(params: dict[str, Any]) -> dict[str, Any]:
    """列出 WebUI 内核仓库提交。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 提交列表。
    """
    options = _options(params)
    limit = options.get("limit", 100)
    if limit is not None:
        limit = int(limit)
    return _adapter(params).list_commits(_webui_path(params), limit=limit)


def version_branch_presets(params: dict[str, Any]) -> dict[str, Any]:
    """列出 WebUI 内置分支预设。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 内置分支预设列表。
    """
    webui_type = _require_str(params, "webui_type")
    result: dict[str, Any] = {"webui_type": webui_type, "source": "preset"}
    if webui_type == "sd_webui":
        return result | {
            "supported": True,
            "branches": list(sd_webui_base.SD_WEBUI_BRANCH_INFO_DICT),
            "types": list(sd_webui_base.SD_WEBUI_BRANCH_LIST),
        }
    if webui_type == "fooocus":
        return result | {
            "supported": True,
            "branches": list(fooocus_base.FOOOCUS_BRANCH_INFO_DICT),
            "types": list(fooocus_base.FOOOCUS_BRANCH_LIST),
        }
    if webui_type == "sd_trainer":
        return result | {
            "supported": True,
            "branches": list(sd_trainer_base.SD_TRAINER_BRANCH_INFO_DICT),
            "types": list(sd_trainer_base.SD_TRAINER_BRANCH_LIST),
        }
    return result | {"supported": False, "branches": [], "types": []}


def snapshot_list(params: dict[str, Any]) -> dict[str, Any]:
    """列出 WebUI 快照文件。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 快照文件列表。
    """
    options = _options(params)
    return _adapter(params).list_snapshots(_webui_path(params), snapshot_dir=_optional_path(options.get("snapshot_dir")))


def snapshot_read(params: dict[str, Any]) -> dict[str, Any]:
    """读取快照文件。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 快照内容。
    """
    return _adapter(params).read_snapshot(Path(_require_str(params, "snapshot_path")))


def snapshot_delete(params: dict[str, Any]) -> dict[str, Any]:
    """删除快照文件。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 删除结果。
    """
    return _adapter(params).delete_snapshot(Path(_require_str(params, "snapshot_path")))


def extension_list(params: dict[str, Any]) -> dict[str, Any]:
    """列出本地扩展或自定义节点。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 扩展列表。
    """
    return _adapter(params).list_extensions(_webui_path(params))


def extension_index(params: dict[str, Any]) -> dict[str, Any]:
    """获取可安装扩展源条目。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 可安装扩展列表。
    """
    return _adapter(params).fetch_extension_index(_webui_path(params), options=_options(params))


def extension_versions(params: dict[str, Any]) -> dict[str, Any]:
    """获取 Comfy Registry 扩展版本。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 扩展版本列表。
    """
    options = _options(params)
    timeout = options.get("timeout", 20)
    if timeout is not None:
        timeout = int(timeout)
    return _adapter(params).fetch_extension_versions(_require_str(params, "node_id"), timeout=timeout)


def environment_dependencies(params: dict[str, Any]) -> dict[str, Any]:
    """检查环境依赖状态。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 环境依赖检查结果。
    """
    return _adapter(params).check_environment_dependencies(_webui_path(params))


def environment_pytorch_version(_params: dict[str, Any]) -> dict[str, Any]:
    """检查当前环境中的 PyTorch 版本状态。

    Args:
        _params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: PyTorch 版本检查结果。
    """
    return {"pytorch": check_torch_version_status()}


def package_versions(params: dict[str, Any]) -> dict[str, Any]:
    """获取 PyPI 包版本列表。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 包版本列表。
    """
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


def launch_prepare(params: dict[str, Any]) -> dict[str, Any]:
    """准备 WebUI 启动参数。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: WebUI 启动参数信息。
    """
    return _adapter(params).prepare_launch(_webui_path(params), options=_options(params))


def pytorch_device_type(params: dict[str, Any]) -> dict[str, Any]:
    """获取当前设备支持的 PyTorch 类型。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: PyTorch 设备类型信息。
    """
    options = _options(params)
    if bool(options.get("category", False)):
        return {"category": auto_detect_pytorch_device_category()}
    return {"types": get_available_pytorch_device_type()}


def pytorch_library(params: dict[str, Any]) -> dict[str, Any]:
    """列出内置 PyTorch 版本组合。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: PyTorch 版本组合列表。

    Raises:
        ValueError: 过滤参数类型无效时抛出。
    """
    options = _options(params)
    items = export_pytorch_list()
    dtype = options.get("dtype")
    if dtype is not None:
        if not isinstance(dtype, str):
            raise ValueError("Field 'options.dtype' must be a string")
        items = [item for item in items if item["dtype"] == dtype]
    if "supported" in options:
        supported = bool(options["supported"])
        items = [item for item in items if item.get("supported") is supported]
    return {"count": len(items), "items": items}


def version_switch_branch(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """切换 WebUI 内核仓库分支。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 切换结果。
    """
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
    """切换 WebUI 内核仓库提交。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 切换结果。
    """
    context.log("Switching repository commit")
    result = _adapter(params).switch_commit(_webui_path(params), commit=_require_str(params, "commit"))
    context.set_progress(100, "done")
    return result


def version_update(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """更新 WebUI 内核仓库。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 更新结果。
    """
    context.log("Updating repository")
    result = _adapter(params).update(_webui_path(params))
    context.set_progress(100, "done")
    return result


def snapshot_create(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """创建 WebUI 快照。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 快照创建结果。
    """
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
    """预览快照恢复计划。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 恢复计划。
    """
    context.log("Previewing snapshot restore")
    result = _adapter(params).preview_restore_snapshot(
        _webui_path(params),
        snapshot_path=Path(_require_str(params, "snapshot_path")),
        options=_options(params),
    )
    context.set_progress(100, "done")
    return result


def snapshot_restore(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """恢复 WebUI 快照。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 恢复结果。
    """
    context.log("Restoring snapshot")
    result = _adapter(params).restore_snapshot(
        _webui_path(params),
        snapshot_path=Path(_require_str(params, "snapshot_path")),
        options=_options(params),
    )
    context.set_progress(100, "done")
    return result


def extension_set_enabled(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """启用或禁用扩展。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 修改结果。
    """
    context.log("Changing extension status")
    result = _adapter(params).set_extension_enabled(_webui_path(params), name=_require_str(params, "name"), enabled=bool(params.get("enabled")))
    context.set_progress(100, "done")
    return result


def extension_install(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """从 Git URL 安装扩展。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 安装结果。
    """
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
    """从扩展源条目安装扩展。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 安装结果。

    Raises:
        ValueError: item 字段不是对象。
    """
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
    """更新单个扩展。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 更新结果。
    """
    context.log("Updating extension")
    result = _adapter(params).update_extension(_webui_path(params), name=_require_str(params, "name"))
    context.set_progress(100, "done")
    return result


def extension_update_all(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """更新所有扩展。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 更新结果。
    """
    context.log("Updating all extensions")
    result = _adapter(params).update_all_extensions(_webui_path(params))
    context.set_progress(100, "done")
    return result


def extension_uninstall(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """卸载扩展。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 卸载结果。
    """
    context.log("Uninstalling extension")
    result = _adapter(params).uninstall_extension(_webui_path(params), name=_require_str(params, "name"))
    context.set_progress(100, "done")
    return result


def extension_switch_commit(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """切换扩展提交。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 切换结果。
    """
    context.log("Switching extension commit")
    result = _adapter(params).switch_extension_commit(_webui_path(params), name=_require_str(params, "name"), commit=_require_str(params, "commit"))
    context.set_progress(100, "done")
    return result


def extension_switch_branch(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """切换扩展分支。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 切换结果。
    """
    context.log("Switching extension branch")
    result = _adapter(params).switch_extension_branch(_webui_path(params), name=_require_str(params, "name"), branch=_require_str(params, "branch"))
    context.set_progress(100, "done")
    return result


def extension_switch_registry_version(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """切换 Comfy Registry 扩展版本。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 切换结果。
    """
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
    """安装或升级 InvokeAI PyPI 版本。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 安装结果。
    """
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


def model_root(params: dict[str, Any]) -> dict[str, Any]:
    """读取文件型模型根目录信息。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 模型根目录信息。
    """
    return MODEL_API_ADAPTER.root(_require_str(params, "webui_type"), _webui_path(params))


def model_library(params: dict[str, Any]) -> dict[str, Any]:
    """列出内置模型库条目。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 内置模型库条目列表。

    Raises:
        ValueError: WebUI 类型不支持内置模型库时抛出。
    """
    webui_type = _require_str(params, "webui_type")
    if webui_type not in SUPPORTED_WEBUI_LIST:
        raise ValueError(f"Unsupported model library webui_type: {webui_type}")
    models = export_model_list(cast(SupportedWebUiType, webui_type))
    return {"webui_type": webui_type, "count": len(models), "models": models}


def model_directories(params: dict[str, Any]) -> dict[str, Any]:
    """列出模型目录。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 模型目录列表。
    """
    return MODEL_API_ADAPTER.list_directories(_require_str(params, "webui_type"), _webui_path(params))


def model_entries(params: dict[str, Any]) -> dict[str, Any]:
    """列出模型目录条目。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 模型条目列表。
    """
    options = _options(params)
    return MODEL_API_ADAPTER.list_entries(_require_str(params, "webui_type"), _webui_path(params), relative_path=options.get("relative_path"))


def model_invokeai_list(params: dict[str, Any]) -> dict[str, Any]:
    """列出 InvokeAI 已注册模型。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: InvokeAI 模型列表。
    """
    return MODEL_API_ADAPTER.list_invokeai_models(_webui_path(params))


def hotpatcher_default_config(params: dict[str, Any]) -> dict[str, Any]:
    """获取 Hotpatcher 默认配置。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 默认配置。
    """
    del params
    return HOTPATCHER_API_ADAPTER.default_config()


def hotpatcher_catalog(params: dict[str, Any]) -> dict[str, Any]:
    """获取 Hotpatcher 功能目录。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 功能目录。
    """
    del params
    return HOTPATCHER_API_ADAPTER.catalog()


def hotpatcher_load_config(params: dict[str, Any]) -> dict[str, Any]:
    """读取 Hotpatcher 配置文件。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 配置对象。
    """
    options = _options(params)
    return HOTPATCHER_API_ADAPTER.load_config(_optional_path(params.get("path")), normalize=bool(options.get("normalize", True)))


def hotpatcher_normalize_config(params: dict[str, Any]) -> dict[str, Any]:
    """规范化 Hotpatcher 配置。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 规范化配置。
    """
    return HOTPATCHER_API_ADAPTER.normalize_config(_require_object(params, "config"))


def hotpatcher_runtime_env(params: dict[str, Any]) -> dict[str, Any]:
    """构建 Hotpatcher runtime 环境变量。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: 环境变量映射。
    """
    options = _options(params)
    return HOTPATCHER_API_ADAPTER.runtime_env(
        host=str(options.get("host") or "127.0.0.1"),
        port=int(options.get("port", 8765)),
        token=str(options.get("token") or ""),
        config_source=str(options.get("config_source") or "remote"),
    )


def hotpatcher_runtime_status(params: dict[str, Any]) -> dict[str, Any]:
    """获取 Hotpatcher runtime host 状态。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: runtime host 状态。
    """
    del params
    return HOTPATCHER_API_ADAPTER.runtime_status()


def hotpatcher_runtime_logs(params: dict[str, Any]) -> dict[str, Any]:
    """获取 Hotpatcher runtime host 日志。

    Args:
        params (dict[str, Any]): API 请求参数。

    Returns:
        dict[str, Any]: runtime host 日志。
    """
    options = _options(params)
    limit = options.get("limit", 200)
    return HOTPATCHER_API_ADAPTER.runtime_logs(limit=int(limit) if limit is not None else None)


def model_create_folder(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """创建模型文件夹。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 创建结果。
    """
    context.log("Creating model folder")
    result = MODEL_API_ADAPTER.create_folder(_require_str(params, "webui_type"), _webui_path(params), _optional_str(params, "parent"), _require_str(params, "name"))
    context.set_progress(100, "done")
    return result


def model_copy(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """复制模型条目。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 复制结果。
    """
    context.log("Copying model entry")
    result = MODEL_API_ADAPTER.copy_entry(_require_str(params, "webui_type"), _webui_path(params), _require_str(params, "source"), _optional_str(params, "target_dir"), new_name=_optional_str(params, "new_name"), overwrite=_optional_bool(params, "overwrite"))
    context.set_progress(100, "done")
    return result


def model_move(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """移动模型条目。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 移动结果。
    """
    context.log("Moving model entry")
    result = MODEL_API_ADAPTER.move_entry(_require_str(params, "webui_type"), _webui_path(params), _require_str(params, "source"), _optional_str(params, "target_dir"), new_name=_optional_str(params, "new_name"), overwrite=_optional_bool(params, "overwrite"))
    context.set_progress(100, "done")
    return result


def model_delete(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """删除模型条目。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 删除结果。
    """
    context.log("Deleting model entry")
    result = MODEL_API_ADAPTER.delete_entry(_require_str(params, "webui_type"), _webui_path(params), _require_str(params, "relative_path"))
    context.set_progress(100, "done")
    return result


def model_import(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """导入本地模型文件或文件夹。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 导入结果。
    """
    context.log("Importing model paths")
    result = MODEL_API_ADAPTER.import_paths(_require_str(params, "webui_type"), _webui_path(params), _require_str_list(params, "source_paths"), _optional_str(params, "target_dir"), overwrite=_optional_bool(params, "overwrite"))
    context.set_progress(100, "done")
    return result


def model_download(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """下载模型到模型目录。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 下载结果。
    """
    context.log("Downloading model")
    result = MODEL_API_ADAPTER.download_url(_require_str(params, "webui_type"), _webui_path(params), _require_str(params, "url"), _optional_str(params, "target_dir"), save_name=_optional_str(params, "save_name"), downloader=params.get("downloader"))
    context.set_progress(100, "done")
    return result


def model_invokeai_install_url(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """通过 InvokeAI 从 URL 安装模型。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 安装结果。
    """
    context.log("Installing InvokeAI model from URL")
    result = MODEL_API_ADAPTER.invokeai_install_url(_webui_path(params), _require_str(params, "url"))
    context.set_progress(100, "done")
    return result


def model_invokeai_import(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """导入本地模型到 InvokeAI。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 导入结果。
    """
    context.log("Importing InvokeAI model paths")
    result = MODEL_API_ADAPTER.invokeai_import_paths(_webui_path(params), _require_str_list(params, "source_paths"))
    context.set_progress(100, "done")
    return result


def model_invokeai_unregister(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """注销 InvokeAI 模型。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 注销结果。
    """
    context.log("Unregistering InvokeAI model")
    result = MODEL_API_ADAPTER.invokeai_unregister(_webui_path(params), _require_str(params, "model_id"))
    context.set_progress(100, "done")
    return result


def model_invokeai_delete(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """删除 InvokeAI 模型。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 删除结果。
    """
    context.log("Deleting InvokeAI model")
    result = MODEL_API_ADAPTER.invokeai_delete(_webui_path(params), _require_str(params, "model_id"))
    context.set_progress(100, "done")
    return result


def hotpatcher_save_config(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """保存 Hotpatcher 配置文件。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 保存结果。
    """
    context.log("Saving hotpatcher config")
    result = HOTPATCHER_API_ADAPTER.save_config(_optional_path(params.get("path")), _require_object(params, "config"))
    context.set_progress(100, "done")
    return result


def hotpatcher_export_default_config(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """导出 Hotpatcher 默认配置文件。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 导出结果。
    """
    context.log("Exporting hotpatcher default config")
    result = HOTPATCHER_API_ADAPTER.export_default_config(_optional_path(params.get("path")), overwrite=_optional_bool(params, "overwrite"))
    context.set_progress(100, "done")
    return result


def hotpatcher_apply_config(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """应用 Hotpatcher 配置到当前 API 进程。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 应用结果。
    """
    context.log("Applying hotpatcher config locally")
    config_or_path: dict[str, Any] | Path | None = _require_object(params, "config") if "config" in params else _optional_path(params.get("path"))
    result = HOTPATCHER_API_ADAPTER.apply_config(config_or_path)
    context.set_progress(100, "done")
    return result


def hotpatcher_runtime_start(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """启动 Hotpatcher runtime host。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: runtime host 状态。
    """
    context.log("Starting hotpatcher runtime host")
    options = _options(params)
    config = params.get("config") if isinstance(params.get("config"), dict) else None
    result = HOTPATCHER_API_ADAPTER.start_runtime(host=str(options.get("host") or "127.0.0.1"), port=int(options.get("port", 8765)), token=str(options.get("token") or ""), config=config)
    context.set_progress(100, "done")
    return result


def hotpatcher_runtime_stop(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """停止 Hotpatcher runtime host。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 停止结果。
    """
    del params
    context.log("Stopping hotpatcher runtime host")
    result = HOTPATCHER_API_ADAPTER.stop_runtime()
    context.set_progress(100, "done")
    return result


def hotpatcher_runtime_apply_remote(params: dict[str, Any], context: ApiTaskContext) -> dict[str, Any]:
    """应用配置到远端 Hotpatcher runtime。

    Args:
        params (dict[str, Any]): API 请求参数。
        context (ApiTaskContext): 后台任务上下文。

    Returns:
        dict[str, Any]: 远端应用结果。
    """
    context.log("Applying hotpatcher config remotely")
    options = _options(params)
    result = HOTPATCHER_API_ADAPTER.apply_remote_config(_require_object(params, "config"), timeout=float(options.get("timeout", 10.0)))
    context.set_progress(100, "done")
    return result


def _sync_spec(name: str, handler: Callable[[dict[str, Any]], dict[str, Any]], description: str, schema: dict[str, Any] | None = None) -> ApiMethodSpec:
    return ApiMethodSpec(name=name, handler=handler, kind="sync", description=description, params_schema=schema or WEBUI_REQUEST_SCHEMA)


def _task_spec(name: str, handler: Callable[[dict[str, Any], ApiTaskContext], dict[str, Any]], description: str) -> ApiMethodSpec:
    return ApiMethodSpec(name=name, handler=handler, kind="task", description=description, params_schema=WEBUI_REQUEST_SCHEMA)


def get_default_methods() -> ApiMethodRegistry:
    """获取默认同步 API 方法。

    Returns:
        ApiMethodRegistry: 默认同步方法注册表。
    """
    return {
        "version.status": _sync_spec("version.status", version_status, "Inspect WebUI kernel repository status."),
        "version.branches": _sync_spec("version.branches", version_branches, "List repository branches for a WebUI kernel."),
        "version.commits": _sync_spec("version.commits", version_commits, "List repository commits for a WebUI kernel."),
        "version.branch_presets": _sync_spec(
            "version.branch_presets",
            version_branch_presets,
            "List built-in WebUI branch presets.",
            {
                "type": "object",
                "properties": {
                    "webui_type": {
                        "type": "string",
                        "enum": ["fooocus", "sd_trainer", "sd_webui"],
                    }
                },
                "required": ["webui_type"],
            },
        ),
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
        "environment.dependencies": _sync_spec("environment.dependencies", environment_dependencies, "Check local environment dependency status."),
        "environment.pytorch_version": _sync_spec("environment.pytorch_version", environment_pytorch_version, "Check current PyTorch version compatibility."),
        "package.versions": _sync_spec("package.versions", package_versions, "List PyPI package versions."),
        "launch.prepare": _sync_spec("launch.prepare", launch_prepare, "Prepare WebUI launch arguments and environment."),
        "system.pytorch_device_type": _sync_spec("system.pytorch_device_type", pytorch_device_type, "Get available PyTorch device types."),
        "system.pytorch_library": _sync_spec(
            "system.pytorch_library",
            pytorch_library,
            "List built-in PyTorch version combinations.",
        ),
        "model.root": _sync_spec("model.root", model_root, "Inspect file model root."),
        "model.library": _sync_spec(
            "model.library",
            model_library,
            "List built-in downloadable models.",
            {
                "type": "object",
                "properties": {
                    "webui_type": {
                        "type": "string",
                        "enum": sorted(SUPPORTED_WEBUI_LIST),
                    }
                },
                "required": ["webui_type"],
            },
        ),
        "model.directories": _sync_spec("model.directories", model_directories, "List model directories."),
        "model.entries": _sync_spec("model.entries", model_entries, "List model directory entries."),
        "model.invokeai.list": _sync_spec("model.invokeai.list", model_invokeai_list, "List InvokeAI registered models."),
        "hotpatcher.default_config": _sync_spec("hotpatcher.default_config", hotpatcher_default_config, "Get hotpatcher default config."),
        "hotpatcher.catalog": _sync_spec("hotpatcher.catalog", hotpatcher_catalog, "Get hotpatcher feature catalog."),
        "hotpatcher.load_config": _sync_spec("hotpatcher.load_config", hotpatcher_load_config, "Load hotpatcher config file."),
        "hotpatcher.normalize_config": _sync_spec("hotpatcher.normalize_config", hotpatcher_normalize_config, "Normalize hotpatcher config."),
        "hotpatcher.runtime_env": _sync_spec("hotpatcher.runtime_env", hotpatcher_runtime_env, "Build hotpatcher runtime environment variables."),
        "hotpatcher.runtime_status": _sync_spec("hotpatcher.runtime_status", hotpatcher_runtime_status, "Get hotpatcher runtime host status."),
        "hotpatcher.runtime_logs": _sync_spec("hotpatcher.runtime_logs", hotpatcher_runtime_logs, "Get hotpatcher runtime logs."),
    }


def get_default_task_methods() -> ApiTaskRegistry:
    """获取默认后台任务 API 方法。

    Returns:
        ApiTaskRegistry: 默认后台任务方法注册表。
    """
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
        "model.create_folder": _task_spec("model.create_folder", model_create_folder, "Create model folder."),
        "model.copy": _task_spec("model.copy", model_copy, "Copy model entry."),
        "model.move": _task_spec("model.move", model_move, "Move model entry."),
        "model.delete": _task_spec("model.delete", model_delete, "Delete model entry."),
        "model.import": _task_spec("model.import", model_import, "Import local model files or folders."),
        "model.download": _task_spec("model.download", model_download, "Download model from URL."),
        "model.invokeai.install_url": _task_spec("model.invokeai.install_url", model_invokeai_install_url, "Install InvokeAI model from URL."),
        "model.invokeai.import": _task_spec("model.invokeai.import", model_invokeai_import, "Import local models into InvokeAI."),
        "model.invokeai.unregister": _task_spec("model.invokeai.unregister", model_invokeai_unregister, "Unregister InvokeAI model."),
        "model.invokeai.delete": _task_spec("model.invokeai.delete", model_invokeai_delete, "Delete InvokeAI model."),
        "hotpatcher.save_config": _task_spec("hotpatcher.save_config", hotpatcher_save_config, "Save hotpatcher config file."),
        "hotpatcher.export_default_config": _task_spec("hotpatcher.export_default_config", hotpatcher_export_default_config, "Export hotpatcher default config file."),
        "hotpatcher.apply_config": _task_spec("hotpatcher.apply_config", hotpatcher_apply_config, "Apply hotpatcher config locally."),
        "hotpatcher.runtime_start": _task_spec("hotpatcher.runtime_start", hotpatcher_runtime_start, "Start hotpatcher runtime host."),
        "hotpatcher.runtime_stop": _task_spec("hotpatcher.runtime_stop", hotpatcher_runtime_stop, "Stop hotpatcher runtime host."),
        "hotpatcher.runtime_apply_remote": _task_spec("hotpatcher.runtime_apply_remote", hotpatcher_runtime_apply_remote, "Apply config to remote hotpatcher runtime."),
    }
