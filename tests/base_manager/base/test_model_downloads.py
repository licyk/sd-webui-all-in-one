"""WebUI 模型预下载与模型库安装测试"""

from sd_webui_all_in_one.base_manager import base as base_module
from sd_webui_all_in_one.base_manager.base import model_downloads as base_model_downloads


def test_pre_download_model_for_webui_skips_existing_or_missing_and_downloads_empty(monkeypatch, tmp_path):
    calls = []

    def fake_download_model(**kwargs):
        calls.append(kwargs)
        return [kwargs["base_path"] / "models/model.safetensors"]

    monkeypatch.setattr(base_model_downloads, "download_model", fake_download_model)
    webui = tmp_path / "webui"
    webui.mkdir()

    assert base_module.pre_download_model_for_webui("sd_webui", tmp_path / "missing", webui, "alpha", "modelscope") is None

    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "model.safetensors").write_text("model", encoding="utf-8")
    assert base_module.pre_download_model_for_webui("sd_webui", existing, webui, "alpha", "modelscope") is None

    empty = tmp_path / "empty"
    empty.mkdir()
    result = base_module.pre_download_model_for_webui("sd_webui", empty, webui, ["alpha", "beta"], "huggingface")

    assert result == webui / "models/model.safetensors"
    assert calls == [
        {
            "dtype": "sd_webui",
            "base_path": webui,
            "download_resource_type": "huggingface",
            "model_name": ["alpha", "beta"],
        }
    ]


def test_install_webui_model_from_library_interactive_direct_search(monkeypatch, tmp_path):
    models = [
        {
            "name": "alpha",
            "filename": "alpha.safetensors",
            "url": {"modelscope": "https://modelscope.example/alpha"},
            "dtype": "checkpoint",
            "supported_webui": ["sd_webui"],
            "save_dir": {"sd_webui": "models/Stable-diffusion"},
        },
        {
            "name": "beta",
            "filename": "beta.safetensors",
            "url": {"modelscope": "https://modelscope.example/beta"},
            "dtype": "checkpoint",
            "supported_webui": ["sd_webui"],
            "save_dir": {"sd_webui": "models/Stable-diffusion"},
        },
    ]
    calls = []
    inputs = iter(["search beta", "2"])

    monkeypatch.setattr(base_model_downloads, "export_model_list", lambda dtype: models)
    monkeypatch.setattr(base_model_downloads, "display_model_table", lambda model_list: calls.append(("display", model_list)))
    monkeypatch.setattr(base_model_downloads, "print_divider", lambda char: calls.append(("divider", char)))
    monkeypatch.setattr(base_model_downloads, "search_models_from_library", lambda query, models: calls.append(("search", query, models)) or [2])
    monkeypatch.setattr(base_model_downloads, "download_model", lambda **kwargs: calls.append(("download", kwargs)) or [tmp_path / "beta.safetensors"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    result = base_module.install_webui_model_from_library(
        webui_path=tmp_path,
        dtype="sd_webui",
        interactive_mode=True,
        downloader="urllib",
    )

    assert result == [tmp_path / "beta.safetensors"]
    assert ("search", "beta", models) in calls
    assert calls[-1] == (
        "download",
        {
            "dtype": "sd_webui",
            "base_path": tmp_path,
            "download_resource_type": "modelscope",
            "model_index": [2],
            "downloader": "urllib",
        },
    )


def test_install_webui_model_from_library_interactive_search_prompt(monkeypatch, tmp_path):
    models = [
        {
            "name": "alpha",
            "filename": "alpha.safetensors",
            "url": {"modelscope": "https://modelscope.example/alpha"},
            "dtype": "checkpoint",
            "supported_webui": ["sd_webui"],
            "save_dir": {"sd_webui": "models/Stable-diffusion"},
        }
    ]
    calls = []
    inputs = iter(["search", "alpha", "1"])

    monkeypatch.setattr(base_model_downloads, "export_model_list", lambda dtype: models)
    monkeypatch.setattr(base_model_downloads, "display_model_table", lambda model_list: calls.append(("display", model_list)))
    monkeypatch.setattr(base_model_downloads, "print_divider", lambda char: calls.append(("divider", char)))
    monkeypatch.setattr(base_model_downloads, "search_models_from_library", lambda query, models: calls.append(("search", query, models)) or [1])
    monkeypatch.setattr(base_model_downloads, "download_model", lambda **kwargs: calls.append(("download", kwargs)) or [tmp_path / "alpha.safetensors"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    result = base_module.install_webui_model_from_library(
        webui_path=tmp_path,
        dtype="sd_webui",
        interactive_mode=True,
    )

    assert result == [tmp_path / "alpha.safetensors"]
    assert ("search", "alpha", models) in calls
