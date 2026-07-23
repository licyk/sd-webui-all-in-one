import pytest

from sd_webui_all_in_one.base_manager import library_catalog as catalog


def test_pytorch_catalog_stable_ids_and_family_identity(monkeypatch):
    raw = {
        "name": "CPU build",
        "dtype": "cpu",
        "torch_ver": "torch==1",
        "xformers_ver": None,
        "platform": ["linux"],
        "supported": True,
    }
    monkeypatch.setattr(catalog, "export_pytorch_list", lambda: [raw])
    monkeypatch.setattr(catalog, "auto_detect_available_pytorch_type", lambda: "cpu")
    monkeypatch.setattr(catalog, "find_latest_pytorch_info", lambda _dtype: raw)
    monkeypatch.setattr(catalog, "get_available_pytorch_device_type", lambda: ["cpu"])
    monkeypatch.setattr(catalog, "check_torch_version_status", lambda: {"installed_type": "cu121"})
    monkeypatch.setattr(catalog, "_package_versions", lambda: {name: None for name in ("torch", "torchvision", "torchaudio", "xformers")})

    comfy = catalog.pytorch_catalog("comfyui")
    comfy_again = catalog.pytorch_catalog("comfyui")
    fooocus = catalog.pytorch_catalog("fooocus")

    assert comfy["items"][0]["id"] == comfy_again["items"][0]["id"]
    assert comfy["items"][0]["id"] != fooocus["items"][0]["id"]
    assert comfy["automatic_selection_preview"]["selection_id"] == comfy["items"][0]["id"]
    assert comfy["current"]["installed_type"] == "cu121"


def test_invokeai_catalog_keeps_installed_type_separate_from_detected_category(monkeypatch):
    monkeypatch.setattr(catalog, "check_torch_version_status", lambda: {"installed_type": "cu124"})
    monkeypatch.setattr(catalog, "auto_detect_pytorch_device_category", lambda: "cpu")
    monkeypatch.setattr(catalog, "_package_versions", lambda: {name: None for name in ("torch", "torchvision", "torchaudio", "xformers")})

    result = catalog.pytorch_catalog("invokeai")

    assert result["current"]["installed_type"] == "cu124"
    assert result["detected_device_type"] is None
    assert result["detected_device_category"] == "cpu"


def test_duplicate_catalog_id_rejected():
    with pytest.raises(ValueError, match="Duplicate model"):
        catalog._unique([{"id": "same"}, {"id": "same"}], "model")


def test_model_catalog_metadata_has_no_install_authority():
    result = catalog.model_library_catalog("comfyui")
    item = result["models"][0]

    assert item["id"].startswith("model-library:")
    assert item["sources"]
    assert item["downloaders"]
    assert "save_dir" not in item["details"]
    assert "url" not in item["details"]


def test_pytorch_resolution_is_read_only_and_uses_closed_command_path(monkeypatch):
    item = {
        "id": "pytorch-combination:test",
        "name": "CPU",
        "supported": True,
        "device_type": "cpu",
        "device_category": None,
    }
    monkeypatch.setattr(
        catalog,
        "pytorch_catalog",
        lambda *_args: {
            "items": [item],
            "automatic_selection_available": True,
            "automatic_selection_preview": {"selection_id": item["id"], "explanation": "fresh detection"},
        },
    )

    result = catalog.resolve_pytorch_selection("comfyui", "auto")

    assert result["selection_value"] == "CPU"
    assert result["device_type"] == "cpu"
    assert result["cli_command_path"] == ["comfyui", "reinstall-pytorch"]


def test_invokeai_resolution_preserves_category_semantics(monkeypatch):
    item = {
        "id": "invokeai-category:cpu",
        "name": "CPU",
        "supported": True,
        "device_type": None,
        "device_category": "cpu",
    }
    monkeypatch.setattr(
        catalog,
        "pytorch_catalog",
        lambda *_args: {
            "items": [item],
            "automatic_selection_available": True,
            "automatic_selection_preview": None,
        },
    )

    result = catalog.resolve_pytorch_selection("invokeai", "manual", selection_id=item["id"])

    assert result["selection_kind"] == "device_category"
    assert result["selection_value"] == "cpu"


def test_model_resolution_manual_policy_is_strict_and_read_only(monkeypatch):
    item = {
        "id": "model-library:test",
        "name": "demo",
        "sources": ["modelscope"],
        "downloaders": ["requests"],
        "installable": True,
        "non_installable_reason": None,
    }
    monkeypatch.setattr(
        catalog,
        "model_library_catalog",
        lambda family: {"webui_type": family, "count": 1, "models": [item] if family == "comfyui" else []},
    )

    result = catalog.resolve_model_library_install("comfyui", item["id"], source="modelscope")

    assert result["model_name"] == "demo"
    assert result["source"] == "modelscope"
    assert result["cli_command_path"] == ["comfyui", "model", "install-library"]
    assert "url" not in result and "path" not in result
    with pytest.raises(ValueError, match="Unknown or ambiguous"):
        catalog.resolve_model_library_install("fooocus", item["id"], source="modelscope")
    with pytest.raises(ValueError, match="Source is not available"):
        catalog.resolve_model_library_install("comfyui", item["id"], source="huggingface")


def test_model_resolution_automatic_policy_uses_catalog_fallback(monkeypatch):
    item = {
        "id": "model-library:test",
        "name": "demo",
        "sources": ["modelscope"],
        "downloaders": ["requests"],
        "installable": True,
        "non_installable_reason": None,
    }
    monkeypatch.setattr(
        catalog,
        "model_library_catalog",
        lambda family: {"webui_type": family, "count": 1, "models": [item]},
    )

    result = catalog.resolve_model_library_install(
        "comfyui",
        item["id"],
        source="huggingface",
        automatic_mirror=True,
    )

    assert result["source"] == "modelscope"
    assert result["configured_source"] == "huggingface"
