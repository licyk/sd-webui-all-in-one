"""API v2 真实 callable 注册表。

注册表只描述公开名称、真实调用目标和需要预绑定的命名空间参数。参数类型、
必填状态、默认值和 JSON Schema 均由服务器从目标函数签名生成。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sd_webui_all_in_one.base_manager.library_catalog import (
    model_library_catalog,
    pytorch_catalog,
)
from sd_webui_all_in_one.api_server.server import ApiMethodRegistry, ApiMethodSpec
from sd_webui_all_in_one.base_manager import comfyui_base, fooocus_base, invokeai_base, qwen_tts_webui_base, sd_scripts_base, sd_trainer_base, sd_webui_base
from sd_webui_all_in_one.base_manager.comfy_registry import fetch_comfy_registry_versions
from sd_webui_all_in_one.base_manager.hotpatcher_manager import (
    apply_hotpatcher_config,
    build_hotpatcher_runtime_env,
    export_hotpatcher_default_config,
    get_hotpatcher_catalog,
    get_hotpatcher_default_config,
    load_hotpatcher_config,
    normalize_hotpatcher_config,
    save_hotpatcher_config,
)
from sd_webui_all_in_one.base_manager.model_manager import FILE_MODEL_ROOT_DIRS, FileModelManager
from sd_webui_all_in_one.base_manager.repository_inspector import inspect_repository
from sd_webui_all_in_one.base_manager.snapshot import (
    create_webui_snapshot,
    delete_snapshot,
    list_webui_snapshots,
    load_snapshot,
)
from sd_webui_all_in_one.base_manager.snapshot_restore import preview_webui_snapshot_restore, restore_webui_snapshot
from sd_webui_all_in_one.base_manager.version_manager import (
    fetch_pypi_versions,
    list_branches,
    list_commits,
    switch_repository_branch,
    switch_repository_commit,
    update_repository,
)
from sd_webui_all_in_one.env_check import check_torch_version_status
from sd_webui_all_in_one.proxy import clean_proxy, get_system_proxy_address, set_proxy, test_proxy_connectivity
from sd_webui_all_in_one.pytorch_manager import auto_detect_pytorch_device_category, export_pytorch_list, get_available_pytorch_device_type


_LAUNCH_ARGUMENT_CATALOGS: dict[str, Callable[..., Any]] = {
    "sd_webui": sd_webui_base.get_sd_webui_launch_argument_catalog,
    "comfyui": comfyui_base.get_comfyui_launch_argument_catalog,
    "fooocus": fooocus_base.get_fooocus_launch_argument_catalog,
    "invokeai": invokeai_base.get_invokeai_launch_argument_catalog,
    "sd_trainer": sd_trainer_base.get_sd_trainer_launch_argument_catalog,
    "qwen_tts_webui": qwen_tts_webui_base.get_qwen_tts_webui_launch_argument_catalog,
}

_WEBUI_BASE_METHODS: dict[str, dict[str, Callable[..., Any]]] = {
    "sd_webui": {
        "version.branch_presets": sd_webui_base.get_sd_webui_branch_presets,
        "version.update": sd_webui_base.update_sd_webui,
        "version.check_updates": sd_webui_base.check_sd_webui_updates,
        "snapshot.collect": sd_webui_base.get_sd_webui_snapshot,
        "launch.prepare": sd_webui_base.prepare_sd_webui_launch,
        "extension.list": sd_webui_base.list_sd_webui_extensions,
        "extension.set_enabled": sd_webui_base.set_sd_webui_extensions_status,
        "extension.install": sd_webui_base.install_sd_webui_extension,
        "extension.update_all": sd_webui_base.update_sd_webui_extensions,
        "extension.uninstall": sd_webui_base.uninstall_sd_webui_extension,
    },
    "comfyui": {
        "version.update": comfyui_base.update_comfyui,
        "version.check_updates": comfyui_base.check_comfyui_updates,
        "snapshot.collect": comfyui_base.get_comfyui_snapshot,
        "launch.prepare": comfyui_base.prepare_comfyui_launch,
        "extension.list": comfyui_base.list_comfyui_custom_nodes,
        "extension.set_enabled": comfyui_base.set_comfyui_custom_node_status,
        "extension.install": comfyui_base.install_comfyui_custom_node,
        "extension.update_all": comfyui_base.update_comfyui_custom_nodes,
        "extension.uninstall": comfyui_base.uninstall_comfyui_custom_node,
        "environment.dependencies": comfyui_base.check_comfyui_custom_node_dependencies,
    },
    "fooocus": {
        "version.branch_presets": fooocus_base.get_fooocus_branch_presets,
        "version.update": fooocus_base.update_fooocus,
        "version.check_updates": fooocus_base.check_fooocus_updates,
        "snapshot.collect": fooocus_base.get_fooocus_snapshot,
        "launch.prepare": fooocus_base.prepare_fooocus_launch,
    },
    "invokeai": {
        "version.update": invokeai_base.update_invokeai,
        "version.check_updates": invokeai_base.check_invokeai_updates,
        "snapshot.collect": invokeai_base.get_invokeai_snapshot,
        "launch.prepare": invokeai_base.prepare_invokeai_launch,
        "extension.list": invokeai_base.list_invokeai_custom_nodes,
        "extension.set_enabled": invokeai_base.set_invokeai_custom_nodes_status,
        "extension.install": invokeai_base.install_invokeai_custom_nodes,
        "extension.update_all": invokeai_base.update_invokeai_custom_nodes,
        "extension.uninstall": invokeai_base.uninstall_invokeai_custom_node,
        "version.install": invokeai_base.install_invokeai_component,
    },
    "sd_trainer": {
        "version.branch_presets": sd_trainer_base.get_sd_trainer_branch_presets,
        "version.update": sd_trainer_base.update_sd_trainer,
        "version.check_updates": sd_trainer_base.check_sd_trainer_updates,
        "snapshot.collect": sd_trainer_base.get_sd_trainer_snapshot,
        "launch.prepare": sd_trainer_base.prepare_sd_trainer_launch,
    },
    "sd_scripts": {
        "version.update": sd_scripts_base.update_sd_scripts,
        "version.check_updates": sd_scripts_base.check_sd_scripts_updates,
        "snapshot.collect": sd_scripts_base.get_sd_scripts_snapshot,
    },
    "qwen_tts_webui": {
        "version.update": qwen_tts_webui_base.update_qwen_tts_webui,
        "version.check_updates": qwen_tts_webui_base.check_qwen_tts_webui_updates,
        "snapshot.collect": qwen_tts_webui_base.get_qwen_tts_webui_snapshot,
        "launch.prepare": qwen_tts_webui_base.prepare_qwen_tts_webui_launch,
    },
}

_EXTENSION_WEBUIS = frozenset({"sd_webui", "comfyui", "invokeai"})
_MODEL_LIBRARY_WEBUIS = frozenset({"sd_webui", "comfyui", "invokeai", "fooocus", "sd_trainer", "sd_scripts"})


def _bound(target: Callable[..., Any], /, **arguments: Any) -> ApiMethodSpec:
    """创建只预绑定真实函数参数、不包装调用的注册项。"""
    return ApiMethodSpec(handler=target, bound_arguments=arguments)


def _add(methods: dict[str, Callable[..., Any] | ApiMethodSpec], name: str, target: Callable[..., Any] | ApiMethodSpec) -> None:
    if name in methods:
        raise ValueError(f"Duplicate API method: {name}")
    methods[name] = target


def _register_webui_methods(methods: dict[str, Callable[..., Any] | ApiMethodSpec]) -> None:
    for webui_type, base_methods in _WEBUI_BASE_METHODS.items():
        prefix = webui_type
        direct_methods: dict[str, Callable[..., Any]] = {
            "version.status": inspect_repository,
            "version.branches": list_branches,
            "version.commits": list_commits,
            "version.switch_branch": switch_repository_branch,
            "version.switch_commit": switch_repository_commit,
            "snapshot.list": list_webui_snapshots,
            "snapshot.read": load_snapshot,
            "snapshot.delete": delete_snapshot,
        }
        for suffix, target in direct_methods.items():
            _add(methods, f"{prefix}.{suffix}", target)
        _add(
            methods,
            f"{prefix}.snapshot.create",
            _bound(create_webui_snapshot, snapshot_factory=base_methods["snapshot.collect"]),
        )

        for suffix, target in base_methods.items():
            _add(methods, f"{prefix}.{suffix}", target)

        _add(
            methods,
            f"{prefix}.snapshot.preview_restore",
            _bound(preview_webui_snapshot_restore, expected_webui_type=webui_type),
        )
        _add(
            methods,
            f"{prefix}.snapshot.restore",
            _bound(restore_webui_snapshot, expected_webui_type=webui_type),
        )

        catalog_target = _LAUNCH_ARGUMENT_CATALOGS.get(webui_type)
        if catalog_target is not None:
            _add(methods, f"{prefix}.launch.arguments_catalog", catalog_target)

        if webui_type in _EXTENSION_WEBUIS:
            extension_methods: dict[str, Callable[..., Any]] = {
                "extension.branches": list_branches,
                "extension.commits": list_commits,
                "extension.update": update_repository,
                "extension.switch_branch": switch_repository_branch,
                "extension.switch_commit": switch_repository_commit,
            }
            for suffix, target in extension_methods.items():
                _add(methods, f"{prefix}.{suffix}", target)

        if webui_type == "sd_webui":
            _add(methods, "sd_webui.extension.index", sd_webui_base.fetch_sd_webui_extension_index)
            _add(
                methods,
                "sd_webui.extension.install_index_item",
                sd_webui_base.install_sd_webui_extension_index_item,
            )
        elif webui_type == "comfyui":
            _add(methods, "comfyui.extension.index", comfyui_base.fetch_comfyui_extension_index)
            _add(
                methods,
                "comfyui.extension.install_index_item",
                comfyui_base.install_comfyui_extension_index_item,
            )
            _add(methods, "comfyui.extension.versions", fetch_comfy_registry_versions)
            _add(
                methods,
                "comfyui.extension.switch_registry_version",
                comfyui_base.switch_comfyui_registry_extension_version,
            )
        elif webui_type == "invokeai":
            _add(
                methods,
                "invokeai.extension.install_index_item",
                invokeai_base.install_invokeai_extension_index_item,
            )

        _add(methods, f"{prefix}.pytorch.catalog", _bound(pytorch_catalog, webui_type=webui_type))

        if webui_type in _MODEL_LIBRARY_WEBUIS:
            _add(methods, f"{prefix}.model.library", _bound(model_library_catalog, webui_type=webui_type))


def _register_model_methods(methods: dict[str, Callable[..., Any] | ApiMethodSpec]) -> None:
    for webui_type in FILE_MODEL_ROOT_DIRS:
        manager = FileModelManager(webui_type)
        targets: dict[str, Callable[..., Any]] = {
            "model.root": manager.root,
            "model.directories": manager.list_directories,
            "model.entries": manager.list_entries,
            "model.create_folder": manager.create_folder,
            "model.copy": manager.copy_entry,
            "model.move": manager.move_entry,
            "model.delete": manager.delete_entry,
            "model.import": manager.import_paths,
            "model.download": manager.download_url,
        }
        for suffix, target in targets.items():
            _add(methods, f"{webui_type}.{suffix}", target)

    invokeai_targets: dict[str, Callable[..., Any] | ApiMethodSpec] = {
        "invokeai.model.list": invokeai_base.get_invokeai_model_list,
        "invokeai.model.install_url": invokeai_base.install_invokeai_model_from_source,
        "invokeai.model.import": invokeai_base.import_model_to_invokeai,
        "invokeai.model.unregister": _bound(invokeai_base.uninstall_model_from_invokeai, delete_files=False),
        "invokeai.model.delete": _bound(invokeai_base.uninstall_model_from_invokeai, delete_files=True),
    }
    for name, target in invokeai_targets.items():
        _add(methods, name, target)


def _register_shared_methods(methods: dict[str, Callable[..., Any] | ApiMethodSpec]) -> None:
    shared: dict[str, Callable[..., Any]] = {
        "environment.pytorch_version": check_torch_version_status,
        "package.versions": fetch_pypi_versions,
        "pytorch.device_types": get_available_pytorch_device_type,
        "pytorch.device_category": auto_detect_pytorch_device_category,
        "pytorch.library": export_pytorch_list,
        "system.proxy.get": get_system_proxy_address,
        "system.proxy.test": test_proxy_connectivity,
        "system.proxy.set": set_proxy,
        "system.proxy.clear": clean_proxy,
        "hotpatcher.default_config": get_hotpatcher_default_config,
        "hotpatcher.catalog": get_hotpatcher_catalog,
        "hotpatcher.load_config": load_hotpatcher_config,
        "hotpatcher.normalize_config": normalize_hotpatcher_config,
        "hotpatcher.save_config": save_hotpatcher_config,
        "hotpatcher.export_default_config": export_hotpatcher_default_config,
        "hotpatcher.apply_config": apply_hotpatcher_config,
        "hotpatcher.runtime_env": build_hotpatcher_runtime_env,
    }
    for name, target in shared.items():
        _add(methods, name, target)


def get_default_methods() -> ApiMethodRegistry:
    """返回 API v2 真实 callable 注册表。"""
    methods: dict[str, Callable[..., Any] | ApiMethodSpec] = {}
    _register_shared_methods(methods)
    _register_webui_methods(methods)
    _register_model_methods(methods)
    return methods
