from __future__ import annotations

from pathlib import Path

import pytest

from sd_webui_all_in_one.base_manager import invokeai_base
from sd_webui_all_in_one.base_manager import model_manager as model_manager_module
from sd_webui_all_in_one.base_manager.model_manager import FileModelManager, InvokeAIModelManager


def test_file_model_manager_resolves_roots_and_rejects_escape(tmp_path: Path) -> None:
    manager = FileModelManager("sd_webui", tmp_path / "webui")

    assert manager.root_path == tmp_path / "webui" / "models"
    assert manager.resolve_path(".") == manager.root_path.resolve()
    assert manager.list_entries(".") == []

    with pytest.raises(ValueError):
        manager.resolve_path("../outside")


def test_file_model_manager_file_operations(tmp_path: Path) -> None:
    manager = FileModelManager("sd_trainer", tmp_path / "trainer")
    manager.create_folder(".", "checkpoints")
    manager.create_folder(".", "loras")
    model = manager.root_path / "checkpoints" / "a.safetensors"
    model.write_text("model", encoding="utf-8")

    entries = manager.list_entries("checkpoints")
    assert [entry.name for entry in entries] == ["a.safetensors"]
    assert entries[0].relative_path == "checkpoints/a.safetensors"

    manager.copy_entry("checkpoints/a.safetensors", "loras")
    copied = manager.root_path / "loras" / "a.safetensors"
    assert copied.read_text(encoding="utf-8") == "model"

    with pytest.raises(FileExistsError):
        manager.copy_entry("checkpoints/a.safetensors", "loras")

    model.write_text("new", encoding="utf-8")
    manager.copy_entry("checkpoints/a.safetensors", "loras", overwrite=True)
    assert copied.read_text(encoding="utf-8") == "new"

    manager.move_entry("loras/a.safetensors", "checkpoints", new_name="b.safetensors")
    assert not copied.exists()
    assert (manager.root_path / "checkpoints" / "b.safetensors").read_text(encoding="utf-8") == "new"

    manager.delete_entry("checkpoints/b.safetensors")
    assert not (manager.root_path / "checkpoints" / "b.safetensors").exists()


def test_file_model_manager_import_copies_and_download_passes_save_name(monkeypatch, tmp_path: Path) -> None:
    manager = FileModelManager("comfyui", tmp_path / "comfy")
    manager.create_folder(".", "checkpoints")

    source = tmp_path / "source.safetensors"
    source.write_text("source", encoding="utf-8")
    imported = manager.import_paths([source], "checkpoints")

    assert source.read_text(encoding="utf-8") == "source"
    assert imported == [manager.root_path / "checkpoints" / "source.safetensors"]
    assert imported[0].read_text(encoding="utf-8") == "source"

    calls = []

    def fake_download_file(url, path, save_name=None, tool=None):
        calls.append((url, path, save_name, tool))
        output = path / (save_name or "download")
        output.write_text("downloaded", encoding="utf-8")
        return output

    monkeypatch.setattr(model_manager_module, "download_file", fake_download_file)

    downloaded = manager.download_url(
        "https://example.test/model.safetensors",
        "checkpoints",
        save_name="custom.safetensors",
        downloader="urllib",
    )

    assert downloaded == manager.root_path / "checkpoints" / "custom.safetensors"
    assert calls == [("https://example.test/model.safetensors", manager.root_path / "checkpoints", "custom.safetensors", "urllib")]


def test_invokeai_model_manager_delegates_to_invokeai_helpers(monkeypatch, tmp_path: Path) -> None:
    manager = InvokeAIModelManager(tmp_path / "InvokeAI")
    calls = []

    def fake_list(invokeai_path=None):
        calls.append(("list", invokeai_path))
        return [{"id": "model-1", "name": "Alpha"}]

    def fake_install(invokeai_path, source):
        calls.append(("install", invokeai_path, source))
        return True

    def fake_uninstall(model_identifiers, delete_files=False, invokeai_path=None):
        calls.append(("uninstall", model_identifiers, delete_files, invokeai_path))
        return True

    monkeypatch.setattr(invokeai_base, "get_invokeai_model_list", fake_list)
    monkeypatch.setattr(invokeai_base, "install_invokeai_model_from_source", fake_install)
    monkeypatch.setattr(invokeai_base, "uninstall_model_from_invokeai", fake_uninstall)

    assert manager.list_models() == [{"id": "model-1", "name": "Alpha"}]
    assert manager.install_from_url("https://example.test/model.safetensors") is True
    assert manager.unregister("model-1") is True
    assert manager.delete("model-1") is True

    assert calls == [
        ("list", tmp_path / "InvokeAI"),
        ("install", tmp_path / "InvokeAI", "https://example.test/model.safetensors"),
        ("uninstall", ["model-1"], True, tmp_path / "InvokeAI"),
        ("uninstall", ["model-1"], True, tmp_path / "InvokeAI"),
    ]


def test_invokeai_import_local_paths_copies_before_import(monkeypatch, tmp_path: Path) -> None:
    manager = InvokeAIModelManager(tmp_path / "InvokeAI")
    source = tmp_path / "external.safetensors"
    source.write_text("model", encoding="utf-8")
    calls = []

    def fake_import(model_list, install_model_to_local=False, invokeai_path=None):
        calls.append((model_list, install_model_to_local, invokeai_path))
        assert model_list[0] != source
        assert model_list[0].read_text(encoding="utf-8") == "model"
        return True

    monkeypatch.setattr(invokeai_base, "import_model_to_invokeai", fake_import)

    assert manager.import_local_paths([source]) is True
    copied = manager.import_cache_path / source.name

    assert source.exists()
    assert copied.exists()
    assert calls == [([copied], False, tmp_path / "InvokeAI")]
