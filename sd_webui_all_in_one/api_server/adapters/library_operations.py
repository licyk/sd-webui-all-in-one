"""Stable PyTorch and built-in model-library API operations."""

from __future__ import annotations

import hashlib
import importlib.metadata
from pathlib import Path
from typing import Any, Callable, cast

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


def _pytorch_item(webui_type: str, raw: dict[str, Any], recommended_id: str | None) -> dict[str, Any]:
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


def pytorch_catalog(webui_type: str, _webui_path: Path) -> dict[str, Any]:
    """Build the complete GUI-oriented PyTorch catalog."""
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
    webui_path: Path,
    selection: dict[str, Any],
    options: dict[str, Any],
    context: ApiTaskContext,
) -> dict[str, Any]:
    """Resolve and execute a non-interactive PyTorch reinstall."""
    del webui_path  # The current family functions mutate the active standalone environment.
    context.check_canceled()
    previous = _package_versions()
    context.log("Inspecting hardware and refreshing the PyTorch catalog")
    catalog = pytorch_catalog(webui_type, Path("."))
    mode = selection.get("mode")
    explanation: str | None = None
    if mode == "auto":
        preview = catalog["automatic_selection_preview"]
        selected_id = preview["selection_id"]
        explanation = preview["explanation"]
    elif mode == "manual":
        selected_id = selection.get("selection_id")
        if not isinstance(selected_id, str) or not selected_id:
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
    use_uv = bool(options.get("use_uv", True))
    use_pypi_mirror = bool(options.get("use_pypi_mirror", True))
    force_reinstall = bool(options.get("force_reinstall", False))
    if webui_type == "invokeai":
        if force_reinstall:
            raise ValueError("force_reinstall is not supported by InvokeAI")
        invokeai_base.reinstall_invokeai_pytorch(
            device_type=cast(Any, item["device_category"]),
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
    webui_path: Path,
    selection: dict[str, Any],
) -> dict[str, Any]:
    """Resolve stable PyTorch intent without starting any mutation."""
    if webui_type not in PYTORCH_CLI_PATHS:
        raise ValueError(f"Unsupported PyTorch webui_type: {webui_type}")
    catalog = pytorch_catalog(webui_type, webui_path)
    mode = selection.get("mode")
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
        selected_id = selection.get("selection_id")
        if not isinstance(selected_id, str) or not selected_id:
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
    """Export public model metadata without URLs or destination paths."""
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
                # Backward-compatible fields remain available to existing Python API callers.
                "filename": raw["filename"],
                "url": dict(raw["url"]),
                "supported_webui": list(raw["supported_webui"]),
                "save_dir": dict(raw["save_dir"]),
            }
        )
    return {"webui_type": webui_type, "count": len(items), "models": _unique(items, "model")}


def install_model_from_catalog(
    webui_type: str,
    webui_path: Path,
    model_id: str,
    options: dict[str, Any],
    context: ApiTaskContext,
) -> dict[str, Any]:
    """Resolve a stable model ID and dispatch to the existing family installer."""
    context.check_canceled()
    catalog = model_library_catalog(webui_type)
    matches = [item for item in catalog["models"] if item["id"] == model_id]
    if len(matches) != 1:
        raise ValueError(f"Unknown or ambiguous model_id for {webui_type}: {model_id}")
    item = matches[0]
    if not item["installable"]:
        raise ValueError(item["non_installable_reason"] or "Model is not installable")
    source = options.get("source") or item["sources"][0]
    downloader = options.get("downloader") or "requests"
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
        downloader=cast(DownloadToolType, downloader),
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
    options: dict[str, Any],
) -> dict[str, Any]:
    """Resolve stable model intent without downloading or registering files."""
    if webui_type not in MODEL_CLI_PATHS:
        raise ValueError(f"Unsupported model library webui_type: {webui_type}")
    catalog = model_library_catalog(webui_type)
    matches = [item for item in catalog["models"] if item["id"] == model_id]
    if len(matches) != 1:
        raise ValueError(f"Unknown or ambiguous model_id for {webui_type}: {model_id}")
    item = matches[0]
    if not item["installable"]:
        raise ValueError(item["non_installable_reason"] or "Model is not installable")
    source = options.get("source")
    downloader = options.get("downloader")
    if source not in item["sources"]:
        raise ValueError(f"Source is not available for {model_id}: {source}")
    if downloader not in item["downloaders"]:
        raise ValueError(f"Downloader is not supported for {model_id}: {downloader}")
    return {
        "webui_type": webui_type,
        "model_id": model_id,
        "model_name": item["name"],
        "source": source,
        "downloader": downloader,
        "cli_command_path": list(MODEL_CLI_PATHS[webui_type]),
    }
