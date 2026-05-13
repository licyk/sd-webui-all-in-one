import sys
import types
from pathlib import Path

import pytest

from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.model_downloader import model_utils
from sd_webui_all_in_one.repo_manager import RepoManager
from sd_webui_all_in_one import repo_manager as repo_module


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

    assert [m["name"] for m in model_utils.export_model_list("sd_webui")] == ["alpha", "beta"]
    assert [m["name"] for m in model_utils.export_model_list("comfyui")] == ["alpha"]
    with pytest.raises(ValueError):
        model_utils.export_model_list("unknown")

    assert model_utils.query_model_info("sd_webui", model_name="alpha") == [MODEL_FIXTURES[0]]
    assert model_utils.query_model_info("sd_webui", model_name="alpha", model_index=2) == [MODEL_FIXTURES[1]]
    assert model_utils.query_model_info("sd_webui", model_index=[1, 2]) == MODEL_FIXTURES
    with pytest.raises(FileNotFoundError):
        model_utils.query_model_info("sd_webui", model_name="missing")
    with pytest.raises(ValueError):
        model_utils.query_model_info("sd_webui", model_index=99)

    assert model_utils.search_models_from_library("alp", MODEL_FIXTURES) == [1]
    assert "alpha.safetensors" in capsys.readouterr().out

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


def _repo_manager_with_apis():
    manager = RepoManager.__new__(RepoManager)
    manager.hf_token = None
    manager.ms_token = "ms-token"
    return manager


def test_repo_manager_huggingface_file_listing_and_creation():
    manager = _repo_manager_with_apis()
    calls = []

    class FakeHfApi:
        def list_repo_files(self, **kwargs):
            calls.append(("list", kwargs))
            return ["a.txt"]

        def repo_exists(self, **kwargs):
            calls.append(("exists", kwargs))
            return False

        def create_repo(self, **kwargs):
            calls.append(("create", kwargs))

    manager.hf_api = FakeHfApi()

    assert manager.get_hf_repo_files("owner/repo", "model") == ["a.txt"]
    assert manager.check_hf_repo("owner/repo", "dataset", visibility=True) is True
    assert calls[-1] == ("create", {"repo_id": "owner/repo", "repo_type": "dataset", "private": False})


def test_repo_manager_modelscope_file_listing_and_creation(monkeypatch):
    constants = types.SimpleNamespace(Visibility=types.SimpleNamespace(PUBLIC="public", PRIVATE="private"))
    monkeypatch.setitem(sys.modules, "modelscope.hub.constants", constants)

    manager = _repo_manager_with_apis()
    calls = []

    class FakeMsApi:
        def get_model_files(self, **kwargs):
            calls.append(("model_files", kwargs))
            return [{"Path": "weights/a.bin", "Type": "blob"}, {"Path": "folder", "Type": "tree"}]

        def get_dataset_id_and_type(self, **kwargs):
            calls.append(("dataset_id", kwargs))
            return "dataset-id", "dataset"

        def get_dataset_files(self, **kwargs):
            calls.append(("dataset_files", kwargs))
            return [{"Path": "data/a.txt", "Type": "blob"}] if kwargs["page_number"] == 1 else []

        def repo_exists(self, **kwargs):
            calls.append(("exists", kwargs))
            return False

        def create_repo(self, **kwargs):
            calls.append(("create", kwargs))

    manager.ms_api = FakeMsApi()

    assert manager.get_ms_repo_files("owner/model", "model") == ["weights/a.bin"]
    assert manager.get_ms_repo_files("owner/dataset", "dataset") == ["data/a.txt"]
    assert manager.check_ms_repo("owner/model", "model", visibility=False) is True
    assert calls[-1][1]["visibility"] == "private"


def test_repo_manager_upload_skips_existing_and_aggregates_failures(monkeypatch, tmp_path):
    monkeypatch.setattr(repo_module, "RETRY_TIMES", 1)
    upload_root = tmp_path / "upload"
    upload_root.mkdir()
    (upload_root / "existing.txt").write_text("old", encoding="utf-8")
    (upload_root / "new.txt").write_text("new", encoding="utf-8")

    manager = _repo_manager_with_apis()
    uploaded = []

    class FakeHfApi:
        def upload_file(self, **kwargs):
            uploaded.append(kwargs["path_in_repo"])

    manager.hf_api = FakeHfApi()
    manager.get_repo_file = lambda **_kwargs: ["existing.txt"]

    manager.upload_files_to_huggingface("owner/repo", upload_root, num_threads=1)

    assert uploaded == ["new.txt"]

    class FailingHfApi:
        def upload_file(self, **_kwargs):
            raise ValueError("boom")

    manager.hf_api = FailingHfApi()
    manager.get_repo_file = lambda **_kwargs: []

    with pytest.raises(AggregateError) as exc:
        manager.upload_files_to_huggingface("owner/repo", upload_root, num_threads=1)

    assert len(exc.value.exceptions) == 2


def test_repo_manager_download_filters_huggingface_and_modelscope(monkeypatch, tmp_path):
    captured = []

    class FakeDownloader:
        def __init__(self, download_func, download_kwargs_list):
            captured.append((download_func, download_kwargs_list))

        def start(self, num_threads):
            captured.append(("start", num_threads))

    monkeypatch.setattr(repo_module, "MultiThreadDownloader", FakeDownloader)
    monkeypatch.setitem(sys.modules, "huggingface_hub", types.SimpleNamespace(hf_hub_download="hf-download"))
    monkeypatch.setitem(sys.modules, "modelscope", types.SimpleNamespace(snapshot_download="ms-download"))

    manager = _repo_manager_with_apis()
    manager.get_repo_file = lambda **_kwargs: ["aa/a.txt", "bb/b.txt", "aa/nested/c.txt"]

    manager.download_files_from_huggingface("owner/repo", tmp_path, folder="aa/", num_threads=3)
    assert captured[0] == (
        "hf-download",
        [
            {"repo_id": "owner/repo", "repo_type": "model", "local_dir": tmp_path, "filename": "aa/a.txt"},
            {"repo_id": "owner/repo", "repo_type": "model", "local_dir": tmp_path, "filename": "aa/nested/c.txt"},
        ],
    )
    assert captured[1] == ("start", 3)

    captured.clear()
    manager.download_files_from_modelscope("owner/repo", tmp_path, repo_type="dataset", folder="bb/", num_threads=2)
    assert captured[0] == (
        "ms-download",
        [{"repo_id": "owner/repo", "repo_type": "dataset", "local_dir": tmp_path, "allow_patterns": "bb/b.txt"}],
    )
    assert captured[1] == ("start", 2)
