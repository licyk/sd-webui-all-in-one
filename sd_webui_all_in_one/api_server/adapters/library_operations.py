"""稳定的 PyTorch 与内置模型库 API 操作。"""

from __future__ import annotations

import hashlib
import importlib.metadata
from pathlib import Path
from typing import Any, Callable, Literal, cast

from sd_webui_all_in_one.api_server.server import ApiTaskContext
from sd_webui_all_in_one.base_manager import (
    comfyui_base,
    fooocus_base,
    invokeai_base,
    sd_scripts_base,
    sd_trainer_base,
    sd_webui_base,
)
from sd_webui_all_in_one.base_manager.base import reinstall_pytorch
from sd_webui_all_in_one.downloader import DOWNLOAD_TOOL_TYPE_LIST, DownloadToolType
from sd_webui_all_in_one.env_check import check_torch_version_status
from sd_webui_all_in_one.model_downloader import SupportedWebUiType, export_model_list
from sd_webui_all_in_one.pytorch_manager import (
    PYTORCH_DEVICE_CATEGORY_LIST,
    PyTorchVersionInfo,
    auto_detect_available_pytorch_type,
    auto_detect_pytorch_device_category,
    export_pytorch_list,
    find_latest_pytorch_info,
    get_available_pytorch_device_type,
)


MODEL_INSTALLERS: dict[str, Callable[..., object]] = {
    "sd_webui": sd_webui_base.install_sd_webui_model_from_library,
    "comfyui": comfyui_base.install_comfyui_model_from_library,
    "invokeai": invokeai_base.install_invokeai_model_from_library,
    "fooocus": fooocus_base.install_fooocus_model_from_library,
    "sd_trainer": sd_trainer_base.install_sd_trainer_model_from_library,
    "sd_scripts": sd_scripts_base.install_sd_scripts_model_from_library,
}

PYTORCH_CLI_PATHS: dict[str, list[str]] = {
    "sd_webui": ["sd-webui", "reinstall-pytorch"],
    "comfyui": ["comfyui", "reinstall-pytorch"],
    "invokeai": ["invokeai", "reinstall-pytorch"],
    "fooocus": ["fooocus", "reinstall-pytorch"],
    "sd_trainer": ["sd-trainer", "reinstall-pytorch"],
    "sd_scripts": ["sd-scripts", "reinstall-pytorch"],
    "qwen_tts_webui": ["qwen-tts-webui", "reinstall-pytorch"],
}

MODEL_CLI_PATHS: dict[str, list[str]] = {
    "sd_webui": ["sd-webui", "model", "install-library"],
    "comfyui": ["comfyui", "model", "install-library"],
    "invokeai": ["invokeai", "model", "install-library"],
    "fooocus": ["fooocus", "model", "install-library"],
    "sd_trainer": ["sd-trainer", "model", "install-library"],
    "sd_scripts": ["sd-scripts", "model", "install-library"],
}


def _stable_id(namespace: str, *parts: object) -> str:
    digest = hashlib.sha256("\0".join(str(part) for part in parts).encode()).hexdigest()[:20]
    return f"{namespace}:{digest}"


def _package_versions() -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for name in ("torch", "torchvision", "torchaudio", "xformers"):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def _unique(items: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    for item in items:
        item_id = item["id"]
        if item_id in seen:
            raise ValueError(f"Duplicate {kind} catalog id: {item_id}")
        seen.add(item_id)
    return items


def _pytorch_item(webui_type: str, raw: PyTorchVersionInfo, recommended_id: str | None) -> dict[str, Any]:
    item_id = _stable_id(
        "pytorch-combination",
        webui_type,
        raw["name"],
        raw["dtype"],
        raw.get("torch_ver"),
        raw.get("xformers_ver"),
    )
    return {
        "id": item_id,
        "name": raw["name"],
        "description": raw.get("description") or "",
        "device_type": raw["dtype"],
        "device_category": None,
        "torch_declaration": raw.get("torch_ver"),
        "xformers_declaration": raw.get("xformers_ver"),
        "supported": bool(raw.get("supported")),
        "recommended": item_id == recommended_id,
        "details": {"platforms": list(raw.get("platform") or [])},
    }


def pytorch_catalog(webui_type: str) -> dict[str, Any]:
    """构建面向图形界面的完整 PyTorch 目录。

    Args:
        webui_type (str): WebUI 类型。
    Returns:
        dict[str, Any]: PyTorch 环境、自动选择结果与可用组合。
    """
    versions = _package_versions()
    try:
        compatibility = check_torch_version_status()
    except Exception as error:
        compatibility = {
            "available_types": [],
            "gpu_list": [],
            "has_gpu": False,
            "installed_version": versions["torch"],
            "installed_type": None,
            "status": "check_failed",
            "is_compatible": False,
            "message": f"PyTorch compatibility inspection failed: {error}",
        }
    if webui_type == "invokeai":
        detected = auto_detect_pytorch_device_category()
        items = [
            {
                "id": f"invokeai-category:{category}",
                "name": category.upper(),
                "description": f"InvokeAI {category} package category",
                "device_type": None,
                "device_category": category,
                "torch_declaration": None,
                "xformers_declaration": None,
                "supported": True,
                "recommended": category == detected,
                "details": {},
            }
            for category in PYTORCH_DEVICE_CATEGORY_LIST
        ]
        preview_id = f"invokeai-category:{detected}"
        available = list(PYTORCH_DEVICE_CATEGORY_LIST)
        detected_type = None
    else:
        detected_type = auto_detect_available_pytorch_type()
        selected = find_latest_pytorch_info(detected_type)
        preview_id = _stable_id(
            "pytorch-combination",
            webui_type,
            selected["name"],
            selected["dtype"],
            selected.get("torch_ver"),
            selected.get("xformers_ver"),
        )
        items = [_pytorch_item(webui_type, item, preview_id) for item in export_pytorch_list()]
        available = get_available_pytorch_device_type()
        detected = None
    return {
        "webui_type": webui_type,
        "current": {
            "versions": versions,
            "installed_type": compatibility["installed_type"],
            "compatibility": compatibility,
        },
        "detected_device_type": detected_type,
        "detected_device_category": detected,
        "available_device_types": available if webui_type != "invokeai" else [],
        "available_device_categories": available if webui_type == "invokeai" else [],
        "automatic_selection_available": True,
        "automatic_selection_preview": {
            "selection_id": preview_id,
            "explanation": f"Detected {'InvokeAI category' if webui_type == 'invokeai' else 'device type'} {detected or detected_type}",
        },
        "items": _unique(items, "PyTorch"),
        "details": {},
    }


def reinstall_from_catalog(
    webui_type: str,
    mode: Literal["auto", "manual"],
    context: ApiTaskContext,
    selection_id: str | None = None,
    use_uv: bool = True,
    use_pypi_mirror: bool = True,
    force_reinstall: bool = False,
) -> dict[str, Any]:
    """解析并执行非交互式 PyTorch 重装。

    Args:
        webui_type (str): WebUI 类型。
        mode (Literal["auto", "manual"]): 自动或手动选择模式。
        context (ApiTaskContext): 后台任务上下文。
        selection_id (str | None): 手动选择时的稳定标识。
        use_uv (bool): 是否使用 uv。
        use_pypi_mirror (bool): 是否使用 PyPI 镜像。
        force_reinstall (bool): 是否强制重装。

    Returns:
        dict[str, Any]: 重装选择、版本变化与验证结果。

    Raises:
        ValueError: 选择模式、目标或选项无效时抛出。
    """
    context.check_canceled()
    previous = _package_versions()
    context.log("Inspecting hardware and refreshing the PyTorch catalog")
    catalog = pytorch_catalog(webui_type)
    explanation: str | None = None
    if mode == "auto":
        preview = catalog["automatic_selection_preview"]
        selected_id = preview["selection_id"]
        explanation = preview["explanation"]
    elif mode == "manual":
        selected_id = selection_id
        if not selected_id:
            raise ValueError("Manual PyTorch selection requires selection_id")
    else:
        raise ValueError("PyTorch selection mode must be 'auto' or 'manual'")
    matches = [item for item in catalog["items"] if item["id"] == selected_id]
    if len(matches) != 1:
        raise ValueError(f"Unknown or ambiguous PyTorch selection_id for {webui_type}: {selected_id}")
    item = matches[0]
    if not item["supported"]:
        raise ValueError(f"PyTorch selection is unsupported on this platform: {selected_id}")
    context.log(f"Selected {item['name']} ({selected_id})")
    if explanation:
        context.log(explanation)
    context.check_canceled()
    context.set_progress(20, "installing")
    if webui_type == "invokeai":
        if force_reinstall:
            raise ValueError("force_reinstall is not supported by InvokeAI")
        invokeai_base.reinstall_invokeai_pytorch(
            device_type=item["device_category"],
            use_pypi_mirror=use_pypi_mirror,
            use_uv=use_uv,
            interactive_mode=False,
            list_only=False,
        )
    else:
        reinstall_pytorch(
            pytorch_name=item["name"],
            use_pypi_mirror=use_pypi_mirror,
            use_uv=use_uv,
            interactive_mode=False,
            list_only=False,
            force_reinstall=force_reinstall,
        )
    context.check_canceled()
    context.set_progress(90, "validating")
    resulting = _package_versions()
    validation = check_torch_version_status()
    context.set_progress(100, "done")
    return {
        "webui_type": webui_type,
        "requested_mode": mode,
        "selected_id": selected_id,
        "selection_explanation": explanation,
        "previous_versions": previous,
        "resulting_versions": resulting,
        "warnings": [],
        "validation": validation,
    }


def resolve_pytorch_selection(
    webui_type: str,
    mode: Literal["auto", "manual"],
    selection_id: str | None = None,
) -> dict[str, Any]:
    """在不执行修改的情况下解析稳定的 PyTorch 操作意图。

    Args:
        webui_type (str): WebUI 类型。
        mode (Literal["auto", "manual"]): 自动或手动选择模式。
        selection_id (str | None): 手动选择时的稳定标识。

    Returns:
        dict[str, Any]: 可供命令行执行的闭合业务描述。

    Raises:
        ValueError: WebUI 类型或选择信息无效时抛出。
    """
    if webui_type not in PYTORCH_CLI_PATHS:
        raise ValueError(f"Unsupported PyTorch webui_type: {webui_type}")
    catalog = pytorch_catalog(webui_type)
    explanation: str | None = None
    if mode == "auto":
        if not catalog["automatic_selection_available"]:
            raise ValueError(f"Automatic PyTorch selection is unavailable for {webui_type}")
        preview = catalog["automatic_selection_preview"]
        if not isinstance(preview, dict):
            raise ValueError(f"Automatic PyTorch selection returned no candidate for {webui_type}")
        selected_id = preview["selection_id"]
        explanation = preview["explanation"]
    elif mode == "manual":
        selected_id = selection_id
        if not selected_id:
            raise ValueError("Manual PyTorch selection requires selection_id")
    else:
        raise ValueError("PyTorch selection mode must be 'auto' or 'manual'")
    matches = [item for item in catalog["items"] if item["id"] == selected_id]
    if len(matches) != 1:
        raise ValueError(f"Unknown or ambiguous PyTorch selection_id for {webui_type}: {selected_id}")
    item = matches[0]
    if not item["supported"]:
        raise ValueError(f"PyTorch selection is unsupported on this platform: {selected_id}")
    invokeai = webui_type == "invokeai"
    value = item["device_category"] if invokeai else item["name"]
    if not isinstance(value, str) or not value:
        raise ValueError(f"PyTorch selection has no CLI value: {selected_id}")
    return {
        "webui_type": webui_type,
        "requested_mode": mode,
        "selected_id": selected_id,
        "selection_kind": "device_category" if invokeai else "name",
        "selection_value": value,
        "device_type": item.get("device_type"),
        "device_category": item.get("device_category"),
        "explanation": explanation,
        "cli_command_path": list(PYTORCH_CLI_PATHS[webui_type]),
    }


def model_library_catalog(webui_type: str) -> dict[str, Any]:
    """导出模型库公共元数据。

    Args:
        webui_type (str): WebUI 类型。

    Returns:
        dict[str, Any]: 不暴露内部目标路径的模型目录。

    Raises:
        ValueError: WebUI 类型不支持内置模型库时抛出。
    """
    if webui_type not in MODEL_INSTALLERS:
        raise ValueError(f"Unsupported model library webui_type: {webui_type}")
    raw_items = export_model_list(cast(SupportedWebUiType, webui_type))
    items: list[dict[str, Any]] = []
    for raw in raw_items:
        sources = [source for source in ("modelscope", "huggingface") if raw.get("url", {}).get(source)]
        item_id = _stable_id("model-library", webui_type, raw["dtype"], raw["name"], raw["filename"])
        installable = bool(sources and raw.get("save_dir", {}).get(webui_type))
        items.append(
            {
                "id": item_id,
                "name": raw["name"],
                "webui_type": webui_type,
                "model_type": raw["dtype"],
                "description": raw.get("description") or "",
                "tags": list(raw.get("tags") or [raw["dtype"]]),
                "size": raw.get("size"),
                "preview": raw.get("preview"),
                "sources": sources,
                "downloaders": list(DOWNLOAD_TOOL_TYPE_LIST),
                "installable": installable,
                "non_installable_reason": None if installable else "No source or destination is configured for this family",
                "details": {"filename": raw["filename"]},
            }
        )
    return {"webui_type": webui_type, "count": len(items), "models": _unique(items, "model")}


def install_model_from_catalog(
    webui_type: str,
    webui_path: Path,
    model_id: str,
    context: ApiTaskContext,
    source: str | None = None,
    downloader: DownloadToolType = "requests",
) -> dict[str, Any]:
    """解析稳定模型标识并调用对应系列的安装器。

    Args:
        webui_type (str): WebUI 类型。
        webui_path (Path): WebUI 路径。
        model_id (str): 稳定模型标识。
        context (ApiTaskContext): 后台任务上下文。
        source (str | None): 下载来源；为空时选择首个可用来源。
        downloader (DownloadToolType): 下载器。

    Returns:
        dict[str, Any]: 模型安装结果。

    Raises:
        ValueError: 模型、来源或下载器无效时抛出。
    """
    context.check_canceled()
    catalog = model_library_catalog(webui_type)
    matches = [item for item in catalog["models"] if item["id"] == model_id]
    if len(matches) != 1:
        raise ValueError(f"Unknown or ambiguous model_id for {webui_type}: {model_id}")
    item = matches[0]
    if not item["installable"]:
        raise ValueError(item["non_installable_reason"] or "Model is not installable")
    source = source or item["sources"][0]
    if source not in item["sources"]:
        raise ValueError(f"Source is not available for {model_id}: {source}")
    if downloader not in item["downloaders"]:
        raise ValueError(f"Downloader is not supported for {model_id}: {downloader}")
    context.log(f"Installing {item['name']} from {source} with {downloader}")
    context.set_progress(10, "downloading")
    context.check_canceled()
    before_registration_ids: set[str] = set()
    if webui_type == "invokeai":
        before_registration_ids = {str(model["id"]) for model in invokeai_base.get_invokeai_model_list(webui_path) if model.get("id")}
    MODEL_INSTALLERS[webui_type](
        **{f"{webui_type}_path" if webui_type != "sd_webui" else "sd_webui_path": webui_path},
        download_resource_type=source,
        model_name=item["name"],
        downloader=downloader,
        interactive_mode=False,
        list_only=False,
    )
    context.check_canceled()
    registration_ids: list[str] = []
    if webui_type == "invokeai":
        after_ids = {str(model["id"]) for model in invokeai_base.get_invokeai_model_list(webui_path) if model.get("id")}
        registration_ids = sorted(after_ids - before_registration_ids)
    context.set_progress(100, "done")
    return {
        "webui_type": webui_type,
        "model_id": model_id,
        "source": source,
        "downloader": downloader,
        "installed_files": [item["details"]["filename"]],
        "registration_ids": registration_ids,
        "warnings": [],
        "completed": True,
    }


def resolve_model_library_install(
    webui_type: str,
    model_id: str,
    source: str | None = None,
    downloader: DownloadToolType = "requests",
    automatic_mirror: bool = False,
) -> dict[str, Any]:
    """在不下载或注册文件的情况下解析稳定模型操作意图。

    Args:
        webui_type (str): WebUI 类型。
        model_id (str): 稳定模型标识。
        source (str | None): 下载来源。
        downloader (DownloadToolType): 下载器。
        automatic_mirror (bool): 是否允许自动选择下载源。

    Returns:
        dict[str, Any]: 可供命令行执行的闭合业务描述。

    Raises:
        ValueError: 模型、来源或下载器无效时抛出。
    """
    if webui_type not in MODEL_CLI_PATHS:
        raise ValueError(f"Unsupported model library webui_type: {webui_type}")
    catalog = model_library_catalog(webui_type)
    matches = [item for item in catalog["models"] if item["id"] == model_id]
    if len(matches) != 1:
        raise ValueError(f"Unknown or ambiguous model_id for {webui_type}: {model_id}")
    item = matches[0]
    if not item["installable"]:
        raise ValueError(item["non_installable_reason"] or "Model is not installable")
    available_sources = list(item["sources"])
    if not available_sources:
        raise ValueError(f"No source is available for {model_id}")
    if not automatic_mirror and source not in available_sources:
        raise ValueError(f"Source is not available for {model_id}: {source}")
    if downloader not in item["downloaders"]:
        raise ValueError(f"Downloader is not supported for {model_id}: {downloader}")
    validation_source = source if source in available_sources else available_sources[0]
    return {
        "webui_type": webui_type,
        "model_id": model_id,
        "model_name": item["name"],
        "source": validation_source,
        "configured_source": source,
        "available_sources": available_sources,
        "automatic_mirror": automatic_mirror,
        "downloader": downloader,
        "cli_command_path": list(MODEL_CLI_PATHS[webui_type]),
    }
