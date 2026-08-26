"""Product-specific version GUI helpers."""

from __future__ import annotations

import json
from pathlib import Path


def _load_sd_webui_config(sd_webui_path: Path) -> dict:
    config_path = sd_webui_path / "config.json"
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _save_sd_webui_config(
    sd_webui_path: Path,
    data: dict,
) -> None:
    config_path = sd_webui_path / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def _sd_webui_extension_enabled(sd_webui_path: Path, name: str, _path: Path) -> bool:
    settings = _load_sd_webui_config(sd_webui_path)
    disabled_extensions = set(settings.get("disabled_extensions", []))
    disable_all_extensions = settings.get("disable_all_extensions", "none")
    if disable_all_extensions == "all":
        return False
    if disable_all_extensions == "extra":
        return True
    return name not in disabled_extensions


def _set_sd_webui_extension_enabled(
    sd_webui_path: Path,
    name: str,
    enabled: bool,
) -> None:
    settings = _load_sd_webui_config(sd_webui_path)
    disabled_extensions = settings.setdefault("disabled_extensions", [])
    if not isinstance(disabled_extensions, list):
        disabled_extensions = []
        settings["disabled_extensions"] = disabled_extensions
    if enabled and name in disabled_extensions:
        disabled_extensions.remove(name)
    elif not enabled and name not in disabled_extensions:
        disabled_extensions.append(name)
    _save_sd_webui_config(sd_webui_path, settings)
