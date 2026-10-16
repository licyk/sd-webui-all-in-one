"""模型库导出, 查询与下载测试"""

import pytest

from sd_webui_all_in_one.model_downloader import model_utils

MODEL_FIXTURES = [
    {
        "name": "alpha",
        "filename": "alpha.safetensors",
        "url": {"modelscope": "https://modelscope.example/alpha", "huggingface": "https://hf.example/alpha"},
        "dtype": "checkpoint",
        "supported_webui": ["sd_webui", "comfyui"],
        "save_dir": {"sd_webui": "models/Stable-diffusion", "comfyui": "models/checkpoints"},
    },
    {
        "name": "beta",
        "filename": "beta.safetensors",
        "url": {"modelscope": "https://modelscope.example/beta", "huggingface": "https://hf.example/beta"},
        "dtype": "checkpoint",
        "supported_webui": ["sd_webui"],
        "save_dir": {"sd_webui": "models/Stable-diffusion"},
    },
]


def test_model_library_export_query_search_and_download(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(model_utils, "MODEL_DOWNLOAD_DICT", MODEL_FIXTURES)

    exported_models = model_utils.export_model_list("sd_webui")
    assert [m["name"] for m in exported_models] == ["alpha", "beta"]
    assert exported_models[0] == MODEL_FIXTURES[0]
    assert exported_models[0] is not MODEL_FIXTURES[0]
    assert exported_models[0]["url"] is not MODEL_FIXTURES[0]["url"]
    exported_models[0]["url"]["huggingface"] = "changed"
    exported_models[0]["supported_webui"].append("invokeai")
    assert MODEL_FIXTURES[0]["url"]["huggingface"] == "https://hf.example/alpha"
    assert MODEL_FIXTURES[0]["supported_webui"] == ["sd_webui", "comfyui"]

    assert [m["name"] for m in model_utils.export_model_list("comfyui")] == ["alpha"]
    with pytest.raises(ValueError):
        model_utils.export_model_list("unknown")

    queried_alpha = model_utils.query_model_info("sd_webui", model_name="alpha")
    assert queried_alpha == [MODEL_FIXTURES[0]]
    assert queried_alpha[0] is not MODEL_FIXTURES[0]
    queried_alpha[0]["save_dir"]["sd_webui"] = "changed"
    assert MODEL_FIXTURES[0]["save_dir"]["sd_webui"] == "models/Stable-diffusion"
    assert model_utils.query_model_info("sd_webui", model_name="alpha", model_index=2) == [MODEL_FIXTURES[1]]
    queried_all = model_utils.query_model_info("sd_webui", model_index=[1, 2])
    assert queried_all == MODEL_FIXTURES
    assert queried_all[0] is not MODEL_FIXTURES[0]
    with pytest.raises(FileNotFoundError):
        model_utils.query_model_info("sd_webui", model_name="missing")
    with pytest.raises(ValueError):
        model_utils.query_model_info("sd_webui", model_index=99)

    assert model_utils.search_models_from_library("alp", MODEL_FIXTURES) == [1]
    assert "alpha.safetensors" in capsys.readouterr().out
    assert model_utils.search_models_from_library("alpha safe", MODEL_FIXTURES) == [1]
    assert model_utils.search_models_from_library("sd-webui beta", MODEL_FIXTURES) == [2]
    assert model_utils.search_models_from_library("check point beta", MODEL_FIXTURES) == [2]

    calls = []

    def fake_download_file(url, path, save_name, tool):
        calls.append((url, path, save_name, tool))
        return path / save_name

    monkeypatch.setattr(model_utils, "download_file", fake_download_file)
    paths = model_utils.download_model("sd_webui", tmp_path, download_resource_type="huggingface", model_index=[1, 2], downloader="urllib")

    assert paths == [
        tmp_path / "models/Stable-diffusion/alpha.safetensors",
        tmp_path / "models/Stable-diffusion/beta.safetensors",
    ]
    assert calls[0] == ("https://hf.example/alpha", tmp_path / "models/Stable-diffusion", "alpha.safetensors", "urllib")

    def failing_download_file(**_kwargs):
        raise RuntimeError("download failed")

    monkeypatch.setattr(model_utils, "download_file", failing_download_file)
    with pytest.raises(RuntimeError) as exc:
        model_utils.download_model("sd_webui", tmp_path, model_index=1)
    assert "alpha" in str(exc.value)
