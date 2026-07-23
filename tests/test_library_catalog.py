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
