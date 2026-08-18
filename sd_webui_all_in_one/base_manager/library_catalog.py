"""PyTorch 与内置模型库的只读目录查询。"""

from __future__ import annotations

import hashlib
import importlib.metadata
from typing import Any

from sd_webui_all_in_one.downloader import DOWNLOAD_TOOL_TYPE_LIST
from sd_webui_all_in_one.env_check import check_torch_version_status
from sd_webui_all_in_one.model_downloader import SUPPORTED_WEBUI_LIST, export_model_list
from sd_webui_all_in_one.pytorch_manager import (
    PYTORCH_DEVICE_CATEGORY_LIST,
    PyTorchVersionInfo,
    auto_detect_available_pytorch_type,
    auto_detect_pytorch_device_category,
    export_pytorch_list,
    find_latest_pytorch_info,
    get_available_pytorch_device_type,
)
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


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
        logger.debug("检测到包 %s 的版本：%s", name, result[name])
    return result


def _unique(items: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    for item in items:
        item_id = item["id"]
        if item_id in seen:
            logger.error("检测到重复的 %s 目录 id：%s", kind, item_id)
            raise ValueError(f"Duplicate {kind} catalog id: {item_id}")
        seen.add(item_id)
    logger.debug("目录去重完成，%s 条目数量：%s", kind, len(items))
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
    logger.debug(
        "构建 PyTorch 组合条目 %s：名称=%s，dtype=%s，torch=%s，xformers=%s",
        item_id,
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
    """构建完整的 PyTorch 只读目录。

    Args:
        webui_type (str): WebUI 类型。

    Returns:
        dict[str, Any]: PyTorch 环境、自动选择结果与可用组合。
    """
    logger.info("开始构建 PyTorch 目录，WebUI 类型：%s", webui_type)
    versions = _package_versions()
    try:
        compatibility = check_torch_version_status()
    except Exception as error:
        logger.error("PyTorch 兼容性检查失败：%s", error)
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
        logger.debug("检测到 InvokeAI 设备类别：%s，可用类别数量：%s", detected, len(available))
    else:
        detected_type = auto_detect_available_pytorch_type()
        logger.debug("检测到 PyTorch 设备类型：%s", detected_type)
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
        logger.debug("可用 PyTorch 设备类型：%s", available)
    logger.info("PyTorch 目录构建完成，WebUI 类型：%s，组合条目数量：%s", webui_type, len(items))
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


def model_library_catalog(webui_type: str) -> dict[str, Any]:
    """导出模型库公共元数据。

    Args:
        webui_type (str): WebUI 类型。

    Returns:
        dict[str, Any]: 模型目录，安装路径为相对 WebUI 根目录的路径，不包含主机绝对路径。

    Raises:
        ValueError: WebUI 类型不支持内置模型库。
    """
    if webui_type not in SUPPORTED_WEBUI_LIST:
        logger.error("不支持的模型库 WebUI 类型：%s", webui_type)
        raise ValueError(f"Unsupported model library webui_type: {webui_type}")
    logger.info("开始构建模型库目录，WebUI 类型：%s", webui_type)
    raw_items = export_model_list(webui_type)
    items: list[dict[str, Any]] = []
    for raw in raw_items:
        sources = [source for source in ("modelscope", "huggingface") if raw.get("url", {}).get(source)]
        item_id = _stable_id("model-library", webui_type, raw["dtype"], raw["name"], raw["filename"])
        install_path = raw.get("save_dir", {}).get(webui_type)
        installable = bool(sources and install_path)
        items.append(
            {
                "id": item_id,
                "name": raw["name"],
                "webui_type": webui_type,
                "model_type": raw["dtype"],
                "install_path": install_path,
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
        logger.debug("模型库条目 %s：名称=%s，dtype=%s，可安装=%s", item_id, raw["name"], raw["dtype"], installable)
    logger.info("模型库目录构建完成，WebUI 类型：%s，模型数量：%s", webui_type, len(items))
    return {"webui_type": webui_type, "count": len(items), "models": _unique(items, "model")}
