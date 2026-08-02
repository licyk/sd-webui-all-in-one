"""API v2 真实 callable 注册表。

注册表只描述公开名称、真实调用目标和需要预绑定的命名空间参数。参数类型、
必填状态、默认值和 JSON Schema 均由服务器从目标函数签名生成。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

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
from sd_webui_all_in_one.base_manager.library_catalog import (
    model_library_catalog,
    pytorch_catalog,
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


def _bound(target: Callable[..., Any], /, **arguments: Any) -> ApiMethodSpec:
    """创建只预绑定真实函数参数、不包装调用的注册项。"""
    return ApiMethodSpec(handler=target, bound_arguments=arguments)


def _add(methods: dict[str, Callable[..., Any] | ApiMethodSpec], name: str, target: Callable[..., Any] | ApiMethodSpec) -> None:
    if name in methods:
        raise ValueError(f"Duplicate API method: {name}")
    methods[name] = target


def _register_sd_webui_methods(methods: dict[str, Callable[..., Any] | ApiMethodSpec]) -> None:
    _add(methods, "sd_webui.version.status", inspect_repository)
    _add(methods, "sd_webui.version.branches", list_branches)
    _add(methods, "sd_webui.version.commits", list_commits)
    _add(methods, "sd_webui.version.switch_branch", switch_repository_branch)
    _add(methods, "sd_webui.version.switch_commit", switch_repository_commit)
    _add(methods, "sd_webui.version.branch_presets", sd_webui_base.get_sd_webui_branch_presets)
    _add(methods, "sd_webui.version.update", sd_webui_base.update_sd_webui)
    _add(methods, "sd_webui.version.check_updates", sd_webui_base.check_sd_webui_updates)
    _add(methods, "sd_webui.snapshot.list", list_webui_snapshots)
    _add(methods, "sd_webui.snapshot.read", load_snapshot)
    _add(
        methods,
        "sd_webui.snapshot.create",
        _bound(create_webui_snapshot, snapshot_factory=sd_webui_base.get_sd_webui_snapshot),
    )
    _add(methods, "sd_webui.snapshot.delete", delete_snapshot)
    _add(methods, "sd_webui.snapshot.collect", sd_webui_base.get_sd_webui_snapshot)
    _add(
        methods,
        "sd_webui.snapshot.preview_restore",
        _bound(preview_webui_snapshot_restore, expected_webui_type="sd_webui"),
    )
    _add(
        methods,
        "sd_webui.snapshot.restore",
        _bound(restore_webui_snapshot, expected_webui_type="sd_webui"),
    )
    _add(methods, "sd_webui.launch.prepare", sd_webui_base.prepare_sd_webui_launch)
    _add(methods, "sd_webui.launch.arguments_catalog", sd_webui_base.get_sd_webui_launch_argument_catalog)
    _add(methods, "sd_webui.extension.list", sd_webui_base.list_sd_webui_extensions)
    _add(methods, "sd_webui.extension.set_enabled", sd_webui_base.set_sd_webui_extensions_status)
    _add(methods, "sd_webui.extension.install", sd_webui_base.install_sd_webui_extension)
    _add(methods, "sd_webui.extension.update_all", sd_webui_base.update_sd_webui_extensions)
    _add(methods, "sd_webui.extension.uninstall", sd_webui_base.uninstall_sd_webui_extension)
    _add(methods, "sd_webui.extension.branches", list_branches)
    _add(methods, "sd_webui.extension.commits", list_commits)
    _add(methods, "sd_webui.extension.update", update_repository)
    _add(methods, "sd_webui.extension.switch_branch", switch_repository_branch)
    _add(methods, "sd_webui.extension.switch_commit", switch_repository_commit)
    _add(methods, "sd_webui.extension.index", sd_webui_base.fetch_sd_webui_extension_index)
    _add(methods, "sd_webui.extension.install_index_item", sd_webui_base.install_sd_webui_extension_index_item)
    _add(methods, "sd_webui.pytorch.catalog", _bound(pytorch_catalog, webui_type="sd_webui"))
    _add(methods, "sd_webui.model.library", _bound(model_library_catalog, webui_type="sd_webui"))


def _register_comfyui_methods(methods: dict[str, Callable[..., Any] | ApiMethodSpec]) -> None:
    _add(methods, "comfyui.version.status", inspect_repository)
    _add(methods, "comfyui.version.branches", list_branches)
    _add(methods, "comfyui.version.commits", list_commits)
    _add(methods, "comfyui.version.switch_branch", switch_repository_branch)
    _add(methods, "comfyui.version.switch_commit", switch_repository_commit)
    _add(methods, "comfyui.version.update", comfyui_base.update_comfyui)
    _add(methods, "comfyui.version.check_updates", comfyui_base.check_comfyui_updates)
    _add(methods, "comfyui.snapshot.list", list_webui_snapshots)
    _add(methods, "comfyui.snapshot.read", load_snapshot)
    _add(
        methods,
        "comfyui.snapshot.create",
        _bound(create_webui_snapshot, snapshot_factory=comfyui_base.get_comfyui_snapshot),
    )
    _add(methods, "comfyui.snapshot.delete", delete_snapshot)
    _add(methods, "comfyui.snapshot.collect", comfyui_base.get_comfyui_snapshot)
    _add(
        methods,
        "comfyui.snapshot.preview_restore",
        _bound(preview_webui_snapshot_restore, expected_webui_type="comfyui"),
    )
    _add(
        methods,
        "comfyui.snapshot.restore",
        _bound(restore_webui_snapshot, expected_webui_type="comfyui"),
    )
    _add(methods, "comfyui.launch.prepare", comfyui_base.prepare_comfyui_launch)
    _add(methods, "comfyui.launch.arguments_catalog", comfyui_base.get_comfyui_launch_argument_catalog)
    _add(methods, "comfyui.extension.list", comfyui_base.list_comfyui_custom_nodes)
    _add(methods, "comfyui.extension.set_enabled", comfyui_base.set_comfyui_custom_node_status)
    _add(methods, "comfyui.extension.install", comfyui_base.install_comfyui_custom_node)
    _add(methods, "comfyui.extension.update_all", comfyui_base.update_comfyui_custom_nodes)
    _add(methods, "comfyui.extension.uninstall", comfyui_base.uninstall_comfyui_custom_node)
    _add(methods, "comfyui.environment.dependencies", comfyui_base.check_comfyui_custom_node_dependencies)
    _add(methods, "comfyui.extension.branches", list_branches)
    _add(methods, "comfyui.extension.commits", list_commits)
    _add(methods, "comfyui.extension.update", update_repository)
    _add(methods, "comfyui.extension.switch_branch", switch_repository_branch)
    _add(methods, "comfyui.extension.switch_commit", switch_repository_commit)
    _add(methods, "comfyui.extension.index", comfyui_base.fetch_comfyui_extension_index)
    _add(methods, "comfyui.extension.install_index_item", comfyui_base.install_comfyui_extension_index_item)
    _add(methods, "comfyui.extension.versions", fetch_comfy_registry_versions)
    _add(methods, "comfyui.extension.switch_registry_version", comfyui_base.switch_comfyui_registry_extension_version)
    _add(methods, "comfyui.pytorch.catalog", _bound(pytorch_catalog, webui_type="comfyui"))
    _add(methods, "comfyui.model.library", _bound(model_library_catalog, webui_type="comfyui"))


def _register_fooocus_methods(methods: dict[str, Callable[..., Any] | ApiMethodSpec]) -> None:
    _add(methods, "fooocus.version.status", inspect_repository)
    _add(methods, "fooocus.version.branches", list_branches)
    _add(methods, "fooocus.version.commits", list_commits)
    _add(methods, "fooocus.version.switch_branch", switch_repository_branch)
    _add(methods, "fooocus.version.switch_commit", switch_repository_commit)
    _add(methods, "fooocus.version.branch_presets", fooocus_base.get_fooocus_branch_presets)
    _add(methods, "fooocus.version.update", fooocus_base.update_fooocus)
    _add(methods, "fooocus.version.check_updates", fooocus_base.check_fooocus_updates)
    _add(methods, "fooocus.snapshot.list", list_webui_snapshots)
    _add(methods, "fooocus.snapshot.read", load_snapshot)
    _add(
        methods,
        "fooocus.snapshot.create",
        _bound(create_webui_snapshot, snapshot_factory=fooocus_base.get_fooocus_snapshot),
    )
    _add(methods, "fooocus.snapshot.delete", delete_snapshot)
    _add(methods, "fooocus.snapshot.collect", fooocus_base.get_fooocus_snapshot)
    _add(
        methods,
        "fooocus.snapshot.preview_restore",
        _bound(preview_webui_snapshot_restore, expected_webui_type="fooocus"),
    )
    _add(
        methods,
        "fooocus.snapshot.restore",
        _bound(restore_webui_snapshot, expected_webui_type="fooocus"),
    )
    _add(methods, "fooocus.launch.prepare", fooocus_base.prepare_fooocus_launch)
    _add(methods, "fooocus.launch.arguments_catalog", fooocus_base.get_fooocus_launch_argument_catalog)
    _add(methods, "fooocus.pytorch.catalog", _bound(pytorch_catalog, webui_type="fooocus"))
    _add(methods, "fooocus.model.library", _bound(model_library_catalog, webui_type="fooocus"))


def _register_invokeai_methods(methods: dict[str, Callable[..., Any] | ApiMethodSpec]) -> None:
    _add(methods, "invokeai.version.status", inspect_repository)
    _add(methods, "invokeai.version.branches", list_branches)
    _add(methods, "invokeai.version.commits", list_commits)
    _add(methods, "invokeai.version.switch_branch", switch_repository_branch)
    _add(methods, "invokeai.version.switch_commit", switch_repository_commit)
    _add(methods, "invokeai.version.update", invokeai_base.update_invokeai)
    _add(methods, "invokeai.version.check_updates", invokeai_base.check_invokeai_updates)
    _add(methods, "invokeai.version.install", invokeai_base.install_invokeai_component)
    _add(methods, "invokeai.snapshot.list", list_webui_snapshots)
    _add(methods, "invokeai.snapshot.read", load_snapshot)
    _add(
        methods,
        "invokeai.snapshot.create",
        _bound(create_webui_snapshot, snapshot_factory=invokeai_base.get_invokeai_snapshot),
    )
    _add(methods, "invokeai.snapshot.delete", delete_snapshot)
    _add(methods, "invokeai.snapshot.collect", invokeai_base.get_invokeai_snapshot)
    _add(
        methods,
        "invokeai.snapshot.preview_restore",
        _bound(preview_webui_snapshot_restore, expected_webui_type="invokeai"),
    )
    _add(
        methods,
        "invokeai.snapshot.restore",
        _bound(restore_webui_snapshot, expected_webui_type="invokeai"),
    )
    _add(methods, "invokeai.launch.prepare", invokeai_base.prepare_invokeai_launch)
    _add(methods, "invokeai.launch.arguments_catalog", invokeai_base.get_invokeai_launch_argument_catalog)
    _add(methods, "invokeai.extension.list", invokeai_base.list_invokeai_custom_nodes)
    _add(methods, "invokeai.extension.set_enabled", invokeai_base.set_invokeai_custom_nodes_status)
    _add(methods, "invokeai.extension.install", invokeai_base.install_invokeai_custom_nodes)
    _add(methods, "invokeai.extension.update_all", invokeai_base.update_invokeai_custom_nodes)
    _add(methods, "invokeai.extension.uninstall", invokeai_base.uninstall_invokeai_custom_node)
    _add(methods, "invokeai.extension.branches", list_branches)
    _add(methods, "invokeai.extension.commits", list_commits)
    _add(methods, "invokeai.extension.update", update_repository)
    _add(methods, "invokeai.extension.switch_branch", switch_repository_branch)
    _add(methods, "invokeai.extension.switch_commit", switch_repository_commit)
    _add(methods, "invokeai.extension.install_index_item", invokeai_base.install_invokeai_extension_index_item)
    _add(methods, "invokeai.pytorch.catalog", _bound(pytorch_catalog, webui_type="invokeai"))
    _add(methods, "invokeai.model.library", _bound(model_library_catalog, webui_type="invokeai"))


def _register_sd_trainer_methods(methods: dict[str, Callable[..., Any] | ApiMethodSpec]) -> None:
    _add(methods, "sd_trainer.version.status", inspect_repository)
    _add(methods, "sd_trainer.version.branches", list_branches)
    _add(methods, "sd_trainer.version.commits", list_commits)
    _add(methods, "sd_trainer.version.switch_branch", switch_repository_branch)
    _add(methods, "sd_trainer.version.switch_commit", switch_repository_commit)
    _add(methods, "sd_trainer.version.branch_presets", sd_trainer_base.get_sd_trainer_branch_presets)
    _add(methods, "sd_trainer.version.update", sd_trainer_base.update_sd_trainer)
    _add(methods, "sd_trainer.version.check_updates", sd_trainer_base.check_sd_trainer_updates)
    _add(methods, "sd_trainer.snapshot.list", list_webui_snapshots)
    _add(methods, "sd_trainer.snapshot.read", load_snapshot)
    _add(
        methods,
        "sd_trainer.snapshot.create",
        _bound(create_webui_snapshot, snapshot_factory=sd_trainer_base.get_sd_trainer_snapshot),
    )
    _add(methods, "sd_trainer.snapshot.delete", delete_snapshot)
    _add(methods, "sd_trainer.snapshot.collect", sd_trainer_base.get_sd_trainer_snapshot)
    _add(
        methods,
        "sd_trainer.snapshot.preview_restore",
        _bound(preview_webui_snapshot_restore, expected_webui_type="sd_trainer"),
    )
    _add(
        methods,
        "sd_trainer.snapshot.restore",
        _bound(restore_webui_snapshot, expected_webui_type="sd_trainer"),
    )
    _add(methods, "sd_trainer.launch.prepare", sd_trainer_base.prepare_sd_trainer_launch)
    _add(methods, "sd_trainer.launch.arguments_catalog", sd_trainer_base.get_sd_trainer_launch_argument_catalog)
    _add(methods, "sd_trainer.pytorch.catalog", _bound(pytorch_catalog, webui_type="sd_trainer"))
    _add(methods, "sd_trainer.model.library", _bound(model_library_catalog, webui_type="sd_trainer"))


def _register_sd_scripts_methods(methods: dict[str, Callable[..., Any] | ApiMethodSpec]) -> None:
    _add(methods, "sd_scripts.version.status", inspect_repository)
    _add(methods, "sd_scripts.version.branches", list_branches)
    _add(methods, "sd_scripts.version.commits", list_commits)
    _add(methods, "sd_scripts.version.switch_branch", switch_repository_branch)
    _add(methods, "sd_scripts.version.switch_commit", switch_repository_commit)
    _add(methods, "sd_scripts.version.update", sd_scripts_base.update_sd_scripts)
    _add(methods, "sd_scripts.version.check_updates", sd_scripts_base.check_sd_scripts_updates)
    _add(methods, "sd_scripts.snapshot.list", list_webui_snapshots)
    _add(methods, "sd_scripts.snapshot.read", load_snapshot)
    _add(
        methods,
        "sd_scripts.snapshot.create",
        _bound(create_webui_snapshot, snapshot_factory=sd_scripts_base.get_sd_scripts_snapshot),
    )
    _add(methods, "sd_scripts.snapshot.delete", delete_snapshot)
    _add(methods, "sd_scripts.snapshot.collect", sd_scripts_base.get_sd_scripts_snapshot)
    _add(
        methods,
        "sd_scripts.snapshot.preview_restore",
        _bound(preview_webui_snapshot_restore, expected_webui_type="sd_scripts"),
    )
    _add(
        methods,
        "sd_scripts.snapshot.restore",
        _bound(restore_webui_snapshot, expected_webui_type="sd_scripts"),
    )
    _add(methods, "sd_scripts.pytorch.catalog", _bound(pytorch_catalog, webui_type="sd_scripts"))
    _add(methods, "sd_scripts.model.library", _bound(model_library_catalog, webui_type="sd_scripts"))


def _register_qwen_tts_webui_methods(methods: dict[str, Callable[..., Any] | ApiMethodSpec]) -> None:
    _add(methods, "qwen_tts_webui.version.status", inspect_repository)
    _add(methods, "qwen_tts_webui.version.branches", list_branches)
    _add(methods, "qwen_tts_webui.version.commits", list_commits)
    _add(methods, "qwen_tts_webui.version.switch_branch", switch_repository_branch)
    _add(methods, "qwen_tts_webui.version.switch_commit", switch_repository_commit)
    _add(methods, "qwen_tts_webui.version.update", qwen_tts_webui_base.update_qwen_tts_webui)
    _add(methods, "qwen_tts_webui.version.check_updates", qwen_tts_webui_base.check_qwen_tts_webui_updates)
    _add(methods, "qwen_tts_webui.snapshot.list", list_webui_snapshots)
    _add(methods, "qwen_tts_webui.snapshot.read", load_snapshot)
    _add(
        methods,
        "qwen_tts_webui.snapshot.create",
        _bound(create_webui_snapshot, snapshot_factory=qwen_tts_webui_base.get_qwen_tts_webui_snapshot),
    )
    _add(methods, "qwen_tts_webui.snapshot.delete", delete_snapshot)
    _add(methods, "qwen_tts_webui.snapshot.collect", qwen_tts_webui_base.get_qwen_tts_webui_snapshot)
    _add(
        methods,
        "qwen_tts_webui.snapshot.preview_restore",
        _bound(preview_webui_snapshot_restore, expected_webui_type="qwen_tts_webui"),
    )
    _add(
        methods,
        "qwen_tts_webui.snapshot.restore",
        _bound(restore_webui_snapshot, expected_webui_type="qwen_tts_webui"),
    )
    _add(methods, "qwen_tts_webui.launch.prepare", qwen_tts_webui_base.prepare_qwen_tts_webui_launch)
    _add(methods, "qwen_tts_webui.launch.arguments_catalog", qwen_tts_webui_base.get_qwen_tts_webui_launch_argument_catalog)
    _add(methods, "qwen_tts_webui.pytorch.catalog", _bound(pytorch_catalog, webui_type="qwen_tts_webui"))


def _register_webui_methods(methods: dict[str, Callable[..., Any] | ApiMethodSpec]) -> None:
    _register_sd_webui_methods(methods)
    _register_comfyui_methods(methods)
    _register_fooocus_methods(methods)
    _register_invokeai_methods(methods)
    _register_sd_trainer_methods(methods)
    _register_sd_scripts_methods(methods)
    _register_qwen_tts_webui_methods(methods)


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
            "model.rename": manager.rename_entry,
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
    """返回 API v2 真实 callable 注册表。

    Returns:
        ApiMethodRegistry: 默认注册的 API 方法映射。
    """
    methods: dict[str, Callable[..., Any] | ApiMethodSpec] = {}
    _register_shared_methods(methods)
    _register_webui_methods(methods)
    _register_model_methods(methods)
    return methods
