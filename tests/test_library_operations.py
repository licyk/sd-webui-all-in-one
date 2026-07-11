from pathlib import Path

import pytest

from sd_webui_all_in_one.api_server.adapters import library_operations as ops


class Context:
    def __init__(self, canceled=False):
        self.canceled = canceled
        self.logs = []
        self.progress = []

    def check_canceled(self):
        if self.canceled:
            raise RuntimeError("canceled")

    def log(self, message, level="info"):
        self.logs.append((level, message))

    def set_progress(self, value=None, message=""):
        self.progress.append((value, message))


def test_pytorch_catalog_stable_ids_and_family_identity(monkeypatch):
    raw = {"name": "CPU build", "dtype": "cpu", "torch_ver": "torch==1", "xformers_ver": None, "platform": ["linux"], "supported": True}
    monkeypatch.setattr(ops, "export_pytorch_list", lambda: [raw])
    monkeypatch.setattr(ops, "auto_detect_available_pytorch_type", lambda: "cpu")
    monkeypatch.setattr(ops, "find_latest_pytorch_info", lambda _dtype: raw)
    monkeypatch.setattr(ops, "get_available_pytorch_device_type", lambda: ["cpu"])
    monkeypatch.setattr(ops, "check_torch_version_status", lambda: {"compatible": True, "message": "ok"})
    monkeypatch.setattr(ops, "_package_versions", lambda: {name: None for name in ("torch", "torchvision", "torchaudio", "xformers")})

    comfy = ops.pytorch_catalog("comfyui", Path("/tmp/a"))
    comfy_again = ops.pytorch_catalog("comfyui", Path("/tmp/b"))
    fooocus = ops.pytorch_catalog("fooocus", Path("/tmp/a"))
    assert comfy["items"][0]["id"] == comfy_again["items"][0]["id"]
    assert comfy["items"][0]["id"] != fooocus["items"][0]["id"]
    assert comfy["automatic_selection_preview"]["selection_id"] == comfy["items"][0]["id"]


def test_duplicate_catalog_id_rejected():
    with pytest.raises(ValueError, match="Duplicate model"):
        ops._unique([{"id": "same"}, {"id": "same"}], "model")


def test_model_catalog_metadata_and_no_install_authority_in_details():
    catalog = ops.model_library_catalog("comfyui")
    item = catalog["models"][0]
    assert item["id"].startswith("model-library:")
    assert item["sources"]
    assert item["downloaders"]
    assert "save_dir" not in item["details"]
    assert "url" not in item["details"]


def test_model_install_requeries_validates_and_dispatches(monkeypatch):
    calls = []
    item = {"id": "model-library:test", "name": "demo", "webui_type": "comfyui", "model_type": "checkpoint", "description": "", "tags": [], "size": None, "preview": None, "sources": ["modelscope"], "downloaders": ["aria2"], "installable": True, "non_installable_reason": None, "details": {"filename": "demo.safetensors"}}
    monkeypatch.setattr(ops, "model_library_catalog", lambda _family: {"webui_type": "comfyui", "count": 1, "models": [item]})
    monkeypatch.setitem(ops.MODEL_INSTALLERS, "comfyui", lambda **kwargs: calls.append(kwargs))
    result = ops.install_model_from_catalog("comfyui", Path("/instance"), item["id"], {"source": "modelscope", "downloader": "aria2"}, Context())
    assert calls[0]["comfyui_path"] == Path("/instance")
    assert calls[0]["interactive_mode"] is False
    assert result["installed_files"] == ["demo.safetensors"]
    with pytest.raises(ValueError, match="Source is not available"):
        ops.install_model_from_catalog("comfyui", Path("/instance"), item["id"], {"source": "huggingface", "downloader": "aria2"}, Context())


def test_pytorch_reinstall_manual_is_noninteractive(monkeypatch):
    calls = []
    item = {"id": "pytorch-combination:test", "name": "CPU", "supported": True, "device_category": None}
    monkeypatch.setattr(ops, "pytorch_catalog", lambda *_args: {"items": [item], "automatic_selection_preview": {"selection_id": item["id"], "explanation": "cpu"}})
    monkeypatch.setattr(ops, "_package_versions", lambda: {name: "1" for name in ("torch", "torchvision", "torchaudio", "xformers")})
    monkeypatch.setattr(ops, "check_torch_version_status", lambda: {"compatible": True})
    monkeypatch.setattr(ops, "reinstall_pytorch", lambda **kwargs: calls.append(kwargs))
    result = ops.reinstall_from_catalog("comfyui", Path("/instance"), {"mode": "manual", "selection_id": item["id"]}, {"use_uv": False, "use_pypi_mirror": False, "force_reinstall": True}, Context())
    assert calls == [{"pytorch_name": "CPU", "use_pypi_mirror": False, "use_uv": False, "interactive_mode": False, "list_only": False, "force_reinstall": True}]
    assert result["selected_id"] == item["id"]


def test_pytorch_auto_uses_fresh_preview_and_logs_reason(monkeypatch):
    calls = []
    context = Context()
    item = {"id": "invokeai-category:cpu", "name": "CPU", "supported": True, "device_category": "cpu"}
    monkeypatch.setattr(ops, "pytorch_catalog", lambda *_args: {"items": [item], "automatic_selection_preview": {"selection_id": item["id"], "explanation": "fresh CPU detection"}})
    monkeypatch.setattr(ops, "_package_versions", lambda: {name: None for name in ("torch", "torchvision", "torchaudio", "xformers")})
    monkeypatch.setattr(ops, "check_torch_version_status", lambda: {"compatible": True})
    monkeypatch.setattr(ops.invokeai_base, "reinstall_invokeai_pytorch", lambda **kwargs: calls.append(kwargs))
    result = ops.reinstall_from_catalog("invokeai", Path("/instance"), {"mode": "auto"}, {}, context)
    assert calls[0]["device_type"] == "cpu"
    assert calls[0]["interactive_mode"] is False
    assert result["selection_explanation"] == "fresh CPU detection"
    assert any("fresh CPU detection" in message for _, message in context.logs)


def test_pytorch_resolution_is_read_only_and_uses_closed_command_path(monkeypatch):
    item = {"id": "pytorch-combination:test", "name": "CPU", "supported": True, "device_type": "cpu", "device_category": None}
    monkeypatch.setattr(ops, "pytorch_catalog", lambda *_args: {"items": [item], "automatic_selection_available": True, "automatic_selection_preview": {"selection_id": item["id"], "explanation": "fresh detection"}})
    monkeypatch.setattr(ops, "reinstall_pytorch", lambda **_kwargs: pytest.fail("resolver must not reinstall"))
    result = ops.resolve_pytorch_selection("comfyui", Path("/instance"), {"mode": "auto"})
    assert result == {
        "webui_type": "comfyui", "requested_mode": "auto", "selected_id": item["id"],
        "selection_kind": "name", "selection_value": "CPU", "device_type": "cpu",
        "device_category": None, "explanation": "fresh detection",
        "cli_command_path": ["comfyui", "reinstall-pytorch"],
    }


def test_invokeai_resolution_preserves_category_semantics(monkeypatch):
    item = {"id": "invokeai-category:cpu", "name": "CPU", "supported": True, "device_type": None, "device_category": "cpu"}
    monkeypatch.setattr(ops, "pytorch_catalog", lambda *_args: {"items": [item], "automatic_selection_available": True, "automatic_selection_preview": None})
    result = ops.resolve_pytorch_selection("invokeai", Path("/instance"), {"mode": "manual", "selection_id": item["id"]})
    assert result["selection_kind"] == "device_category"
    assert result["selection_value"] == "cpu"
    assert result["cli_command_path"] == ["invokeai", "reinstall-pytorch"]


def test_model_resolution_is_read_only_and_rejects_wrong_family(monkeypatch):
    item = {"id": "model-library:test", "name": "demo", "sources": ["modelscope"], "downloaders": ["aria2"], "installable": True, "non_installable_reason": None}
    monkeypatch.setattr(ops, "model_library_catalog", lambda family: {"webui_type": family, "count": 1, "models": [item] if family == "comfyui" else []})
    monkeypatch.setitem(ops.MODEL_INSTALLERS, "comfyui", lambda **_kwargs: pytest.fail("resolver must not install"))
    result = ops.resolve_model_library_install("comfyui", item["id"], {"source": "modelscope", "downloader": "aria2"})
    assert result["model_name"] == "demo"
    assert result["cli_command_path"] == ["comfyui", "model", "install-library"]
    assert "url" not in result and "path" not in result
    with pytest.raises(ValueError, match="Unknown or ambiguous"):
        ops.resolve_model_library_install("fooocus", item["id"], {"source": "modelscope", "downloader": "aria2"})
