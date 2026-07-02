import hashlib
import os
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


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def _repo_manager_with_apis():
    manager = RepoManager.__new__(RepoManager)
    manager.hf_token = None
    manager.ms_token = "ms-token"
    return manager


def test_repo_manager_init_defers_optional_api_imports(monkeypatch):
    import_calls = []

    def fake_import_module(name):
        import_calls.append(name)
        raise AssertionError(f"{name} should not be imported during RepoManager init")

    monkeypatch.setattr(repo_module.importlib, "import_module", fake_import_module)

    manager = RepoManager(hf_token="hf-token", ms_token="ms-token")

    assert import_calls == []
    assert manager.hf_token == "hf-token"
    assert manager.ms_token == "ms-token"


def test_repo_manager_huggingface_api_lazy_init_and_cache(monkeypatch):
    import_calls = []
    init_calls = []

    class FakeHfApi:
        def __init__(self, token=None):
            init_calls.append(token)

    hf_module = types.ModuleType("huggingface_hub")
    hf_module.HfApi = FakeHfApi
    monkeypatch.setitem(sys.modules, "huggingface_hub", hf_module)

    def fake_import_module(name):
        import_calls.append(name)
        assert name == "huggingface_hub"
        return hf_module

    monkeypatch.setattr(repo_module.importlib, "import_module", fake_import_module)

    manager = RepoManager(hf_token="hf-token")
    assert import_calls == []

    first_api = manager.hf_api
    second_api = manager.hf_api

    assert first_api is second_api
    assert isinstance(first_api, FakeHfApi)
    assert init_calls == ["hf-token"]
    assert import_calls == ["huggingface_hub"]


def test_repo_manager_modelscope_api_lazy_init_login_and_cache(monkeypatch):
    import_calls = []
    init_calls = []
    login_calls = []

    class FakeMsApi:
        def __init__(self):
            init_calls.append("init")

        def login(self, access_token):
            login_calls.append(access_token)

    modelscope_module = types.ModuleType("modelscope")
    modelscope_module.HubApi = FakeMsApi
    monkeypatch.setitem(sys.modules, "modelscope", modelscope_module)

    def fake_import_module(name):
        import_calls.append(name)
        assert name == "modelscope"
        return modelscope_module

    monkeypatch.setattr(repo_module.importlib, "import_module", fake_import_module)

    manager = RepoManager(ms_token="ms-token")
    assert import_calls == []

    first_api = manager.ms_api
    second_api = manager.ms_api

    assert first_api is second_api
    assert isinstance(first_api, FakeMsApi)
    assert init_calls == ["init"]
    assert login_calls == ["ms-token"]
    assert import_calls == ["modelscope"]


def test_repo_manager_modelscope_api_prefers_constructor_token(monkeypatch):
    import_calls = []
    init_calls = []
    login_calls = []

    class FakeMsApi:
        def __init__(self, token=None):
            init_calls.append(token)

        def login(self, access_token):
            login_calls.append(access_token)

    modelscope_module = types.ModuleType("modelscope")
    modelscope_module.HubApi = FakeMsApi
    monkeypatch.setitem(sys.modules, "modelscope", modelscope_module)

    def fake_import_module(name):
        import_calls.append(name)
        assert name == "modelscope"
        return modelscope_module

    monkeypatch.setattr(repo_module.importlib, "import_module", fake_import_module)

    manager = RepoManager(ms_token="ms-token")

    first_api = manager.ms_api
    second_api = manager.ms_api

    assert first_api is second_api
    assert isinstance(first_api, FakeMsApi)
    assert init_calls == ["ms-token"]
    assert login_calls == []
    assert import_calls == ["modelscope"]


def test_repo_manager_configure_tokens_updates_environment_and_invalidates_cached_apis(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("MODELSCOPE_API_TOKEN", raising=False)
    manager = RepoManager()
    hf_api = object()
    ms_api = object()
    manager.hf_api = hf_api
    manager.ms_api = ms_api

    manager.configure_tokens(hf_token="hf-token", ms_token="ms-token")

    assert manager.hf_token == "hf-token"
    assert manager.ms_token == "ms-token"
    assert manager._hf_api is repo_module._API_NOT_INITIALIZED
    assert manager._ms_api is repo_module._API_NOT_INITIALIZED
    assert os.environ["HF_TOKEN"] == "hf-token"
    assert os.environ["MODELSCOPE_API_TOKEN"] == "ms-token"


def test_repo_manager_configure_tokens_keeps_existing_tokens_for_none(monkeypatch):
    manager = RepoManager(hf_token="hf-token", ms_token="ms-token")
    hf_api = object()
    ms_api = object()
    manager.hf_api = hf_api
    manager.ms_api = ms_api
    monkeypatch.setenv("HF_TOKEN", "hf-token")
    monkeypatch.setenv("MODELSCOPE_API_TOKEN", "ms-token")

    manager.configure_tokens(hf_token=None, ms_token=None)

    assert manager.hf_token == "hf-token"
    assert manager.ms_token == "ms-token"
    assert manager._hf_api is hf_api
    assert manager._ms_api is ms_api
    assert os.environ["HF_TOKEN"] == "hf-token"
    assert os.environ["MODELSCOPE_API_TOKEN"] == "ms-token"


def test_repo_manager_huggingface_api_installs_missing_dependency_before_reimport(monkeypatch):
    installed = False
    import_calls = []
    install_calls = []

    class FakeHfApi:
        def __init__(self, token=None):
            self.token = token

    hf_module = types.ModuleType("huggingface_hub")
    hf_module.HfApi = FakeHfApi

    def fake_import_module(name):
        import_calls.append(name)
        assert name == "huggingface_hub"
        if not installed:
            raise ImportError("huggingface_hub missing")
        monkeypatch.setitem(sys.modules, "huggingface_hub", hf_module)
        return hf_module

    def fake_install_optional_dependency(package_name, display_name=None):
        nonlocal installed
        installed = True
        install_calls.append((package_name, display_name))

    monkeypatch.setattr(repo_module.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(repo_module, "install_optional_dependency", fake_install_optional_dependency)

    manager = RepoManager(hf_token="hf-token")

    assert manager.hf_api.token == "hf-token"
    assert import_calls == ["huggingface_hub", "huggingface_hub"]
    assert install_calls == [("huggingface_hub", "huggingface_hub")]


def test_repo_manager_modelscope_api_installs_missing_dependency_before_reimport(monkeypatch):
    installed = False
    import_calls = []
    install_calls = []
    login_calls = []

    class FakeMsApi:
        def login(self, access_token):
            login_calls.append(access_token)

    modelscope_module = types.ModuleType("modelscope")
    modelscope_module.HubApi = FakeMsApi

    def fake_import_module(name):
        import_calls.append(name)
        assert name == "modelscope"
        if not installed:
            raise ImportError("modelscope missing")
        monkeypatch.setitem(sys.modules, "modelscope", modelscope_module)
        return modelscope_module

    def fake_install_optional_dependency(package_name, display_name=None):
        nonlocal installed
        installed = True
        install_calls.append((package_name, display_name))

    monkeypatch.setattr(repo_module.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(repo_module, "install_optional_dependency", fake_install_optional_dependency)

    manager = RepoManager(ms_token="ms-token")

    assert manager.ms_api is manager.ms_api
    assert import_calls == ["modelscope", "modelscope"]
    assert install_calls == [("modelscope", "modelscope")]
    assert login_calls == ["ms-token"]


@pytest.mark.parametrize("install_fails", [False, True])
def test_repo_manager_lazy_import_failure_raises_runtime_error(monkeypatch, install_fails):
    def fake_import_module(name):
        assert name == "huggingface_hub"
        raise ImportError("huggingface_hub missing")

    def fake_install_optional_dependency(package_name, display_name=None):
        assert package_name == "huggingface_hub"
        assert display_name == "huggingface_hub"
        if install_fails:
            raise RuntimeError("install failed")

    monkeypatch.setattr(repo_module.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(repo_module, "install_optional_dependency", fake_install_optional_dependency)

    manager = RepoManager()

    with pytest.raises(RuntimeError, match="huggingface_hub"):
        manager.hf_api


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

    assert manager.get_hf_repo_files("owner/repo", "model", revision="dev") == ["a.txt"]
    assert calls[0] == ("list", {"repo_id": "owner/repo", "repo_type": "model", "revision": "dev"})
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

    assert manager.get_ms_repo_files("owner/model", "model", revision="v1") == ["weights/a.bin"]
    assert calls[0] == ("model_files", {"model_id": "owner/model", "recursive": True, "revision": "v1"})
    assert manager.get_ms_repo_files("owner/dataset", "dataset", revision="v2") == ["data/a.txt"]
    assert calls[2][0] == "dataset_files"
    assert calls[2][1]["revision"] == "v2"
    assert manager.check_ms_repo("owner/model", "model", visibility=False) is True
    assert calls[-1][1]["visibility"] == "private"


def test_repo_manager_files_metadata_normalizes_huggingface_and_modelscope():
    manager = _repo_manager_with_apis()
    hf_calls = []

    class FakeHfApi:
        def list_repo_tree(self, **kwargs):
            hf_calls.append(kwargs)
            return [
                types.SimpleNamespace(
                    path="weights/a.bin",
                    size=123,
                    blob_id="blob-id",
                    lfs=types.SimpleNamespace(sha256="hf-sha256"),
                    last_commit=types.SimpleNamespace(oid="hf-commit"),
                ),
                types.SimpleNamespace(
                    path="weights",
                    tree_id="tree-id",
                    last_commit=types.SimpleNamespace(oid="tree-commit"),
                ),
            ]

    manager.hf_api = FakeHfApi()

    assert manager.get_hf_repo_files_metadata("owner/repo", revision="main") == [
        {
            "path": "weights/a.bin",
            "name": "a.bin",
            "type": "file",
            "size": 123,
            "sha256": "hf-sha256",
            "is_lfs": True,
            "object_id": "blob-id",
            "revision": "hf-commit",
        }
    ]
    assert hf_calls[0] == {"repo_id": "owner/repo", "repo_type": "model", "recursive": True, "revision": "main"}

    hf_with_dirs = manager.get_hf_repo_files_metadata(
        "owner/repo",
        revision="main",
        include_dirs=True,
        include_raw=True,
    )
    assert hf_with_dirs[1] == {
        "path": "weights",
        "name": "weights",
        "type": "directory",
        "size": None,
        "sha256": None,
        "is_lfs": None,
        "object_id": "tree-id",
        "revision": "tree-commit",
        "raw": {
            "path": "weights",
            "tree_id": "tree-id",
            "last_commit": types.SimpleNamespace(oid="tree-commit"),
        },
    }

    ms_calls = []

    class FakeMsApi:
        def get_model_files(self, **kwargs):
            ms_calls.append(("model_files", kwargs))
            return [
                {
                    "Path": "weights/a.bin",
                    "Name": "a.bin",
                    "Type": "blob",
                    "Size": 456,
                    "Sha256": "ms-sha256",
                    "IsLFS": False,
                    "Revision": "ms-commit",
                },
                {
                    "Path": "weights",
                    "Name": "weights",
                    "Type": "tree",
                    "Size": 0,
                },
            ]

        def get_dataset_id_and_type(self, **kwargs):
            ms_calls.append(("dataset_id", kwargs))
            return "dataset-id", "dataset"

        def get_dataset_files(self, **kwargs):
            ms_calls.append(("dataset_files", kwargs))
            return [
                {
                    "Path": "data/a.txt",
                    "Type": "blob",
                    "Size": 10,
                    "Sha256": "dataset-sha256",
                    "Revision": "dataset-commit",
                }
            ]

    manager.ms_api = FakeMsApi()

    assert manager.get_ms_repo_files_metadata("owner/model", revision="v1", include_dirs=True) == [
        {
            "path": "weights/a.bin",
            "name": "a.bin",
            "type": "file",
            "size": 456,
            "sha256": "ms-sha256",
            "is_lfs": False,
            "object_id": "ms-sha256",
            "revision": "ms-commit",
        },
        {
            "path": "weights",
            "name": "weights",
            "type": "directory",
            "size": None,
            "sha256": None,
            "is_lfs": None,
            "object_id": None,
            "revision": "v1",
        },
    ]
    assert ms_calls[0] == ("model_files", {"model_id": "owner/model", "recursive": True, "revision": "v1"})

    assert manager.get_repo_files_metadata("modelscope", "owner/dataset", repo_type="dataset") == [
        {
            "path": "data/a.txt",
            "name": "a.txt",
            "type": "file",
            "size": 10,
            "sha256": "dataset-sha256",
            "is_lfs": None,
            "object_id": "dataset-sha256",
            "revision": "dataset-commit",
        }
    ]


def test_repo_manager_file_download_urls(monkeypatch):
    manager = _repo_manager_with_apis()
    hf_calls = []

    hf_module = types.ModuleType("huggingface_hub")

    def fake_hf_hub_url(**kwargs):
        hf_calls.append(("url", kwargs))
        return "https://hf.example/owner/repo/resolve/main/weights/a.bin"

    def fake_get_hf_file_metadata(**kwargs):
        hf_calls.append(("module_metadata", kwargs))
        return types.SimpleNamespace(location="https://cdn.example/fallback.bin")

    hf_module.hf_hub_url = fake_hf_hub_url
    hf_module.get_hf_file_metadata = fake_get_hf_file_metadata
    monkeypatch.setitem(sys.modules, "huggingface_hub", hf_module)

    class FakeHfApi:
        endpoint = "https://hf.example"

        def get_hf_file_metadata(self, **kwargs):
            hf_calls.append(("api_metadata", kwargs))
            return types.SimpleNamespace(location="https://cdn.example/a.bin")

    manager.hf_api = FakeHfApi()
    manager.hf_token = "hf-token"

    assert (
        manager.get_hf_repo_file_download_url("owner/repo", "weights/a.bin", revision="main")
        == "https://hf.example/owner/repo/resolve/main/weights/a.bin"
    )
    assert hf_calls == [
        (
            "url",
            {
                "repo_id": "owner/repo",
                "filename": "weights/a.bin",
                "repo_type": "model",
                "endpoint": "https://hf.example",
                "revision": "main",
            },
        ),
        (
            "api_metadata",
            {"url": "https://hf.example/owner/repo/resolve/main/weights/a.bin", "token": "hf-token"},
        ),
    ]

    ms_calls = []
    modelscope_module = types.ModuleType("modelscope")
    hub_module = types.ModuleType("modelscope.hub")
    utils_module = types.ModuleType("modelscope.utils")
    constants_module = types.ModuleType("modelscope.utils.constant")
    constants_module.DEFAULT_MODEL_REVISION = "master"
    constants_module.DEFAULT_DATASET_REVISION = "master"
    file_download_module = types.ModuleType("modelscope.hub.file_download")

    def fake_get_file_download_url(**kwargs):
        ms_calls.append(("model_url", kwargs))
        return f"https://ms.example/model/{kwargs['revision']}/{kwargs['file_path']}"

    file_download_module.get_file_download_url = fake_get_file_download_url
    monkeypatch.setitem(sys.modules, "modelscope", modelscope_module)
    monkeypatch.setitem(sys.modules, "modelscope.hub", hub_module)
    monkeypatch.setitem(sys.modules, "modelscope.hub.file_download", file_download_module)
    monkeypatch.setitem(sys.modules, "modelscope.utils", utils_module)
    monkeypatch.setitem(sys.modules, "modelscope.utils.constant", constants_module)

    class FakeMsApi:
        def get_dataset_file_url(self, **kwargs):
            ms_calls.append(("dataset_url", kwargs))
            return f"https://ms.example/dataset/{kwargs['revision']}/{kwargs['file_name']}"

    manager.ms_api = FakeMsApi()

    assert (
        manager.get_ms_repo_file_download_url("owner/model", "weights/a.bin", revision="v1")
        == "https://ms.example/model/v1/weights/a.bin"
    )
    assert (
        manager.get_repo_file_download_url("modelscope", "owner/dataset", "data/a.txt", repo_type="dataset")
        == "https://ms.example/dataset/master/data/a.txt"
    )
    assert ms_calls == [
        ("model_url", {"model_id": "owner/model", "file_path": "weights/a.bin", "revision": "v1"}),
        (
            "dataset_url",
            {
                "file_name": "data/a.txt",
                "dataset_name": "dataset",
                "namespace": "owner",
                "revision": "master",
            },
        ),
    ]


def test_repo_manager_upload_skips_matching_hash_and_aggregates_failures(monkeypatch, tmp_path):
    monkeypatch.setattr(repo_module, "RETRY_TIMES", 1)
    upload_root = tmp_path / "upload"
    upload_root.mkdir()
    (upload_root / "existing.txt").write_text("old", encoding="utf-8")
    (upload_root / "changed.txt").write_text("changed-local", encoding="utf-8")
    (upload_root / "new.txt").write_text("new", encoding="utf-8")
    nested_dir = upload_root / "nested"
    nested_dir.mkdir()
    (nested_dir / "keep.txt").write_text("nested", encoding="utf-8")

    manager = _repo_manager_with_apis()
    uploaded = []
    list_calls = []
    upload_log_indexes = []

    def fake_log_info(message, *args, **_kwargs):
        if message == "[%s/%s] 上传 %s 到 %s (类型: %s) 仓库中":
            upload_log_indexes.append(args[:2])

    monkeypatch.setattr(repo_module.logger, "info", fake_log_info)

    class FakeHfApi:
        def upload_file(self, **kwargs):
            uploaded.append(kwargs)

    manager.hf_api = FakeHfApi()
    manager.get_repo_files_metadata = lambda **kwargs: list_calls.append(kwargs) or [
        {"path": "remote/existing.txt", "type": "file", "sha256": _sha256("old")},
        {"path": "remote/changed.txt", "type": "file", "sha256": _sha256("changed-remote")},
        {"path": "remote/nested/keep.txt", "type": "file", "sha256": _sha256("nested")},
    ]

    manager.upload_files_to_huggingface("owner/repo", upload_root, path_in_repo="/remote/", num_threads=1, revision="upload-branch")

    assert list_calls[0]["revision"] == "upload-branch"
    assert {kwargs["path_in_repo"] for kwargs in uploaded} == {"remote/changed.txt", "remote/new.txt"}
    assert {kwargs["revision"] for kwargs in uploaded} == {"upload-branch"}
    assert upload_log_indexes == [(1, 2), (2, 2)]

    ms_uploaded = []
    upload_log_indexes.clear()

    class FakeMsApi:
        def upload_file(self, **kwargs):
            ms_uploaded.append(kwargs)

    manager.ms_api = FakeMsApi()
    manager.get_repo_files_metadata = lambda **_kwargs: [
        {"path": "ms-root/existing.txt", "type": "file", "sha256": _sha256("old")},
        {"path": "ms-root/changed.txt", "type": "file", "sha256": _sha256("changed-remote")},
        {"path": "ms-root/nested/keep.txt", "type": "file", "sha256": _sha256("nested")},
    ]

    manager.upload_files_to_modelscope("owner/repo", upload_root, path_in_repo="ms-root", num_threads=1, revision="ms-branch")

    assert {kwargs["path_in_repo"] for kwargs in ms_uploaded} == {"ms-root/changed.txt", "ms-root/new.txt"}
    assert {kwargs["revision"] for kwargs in ms_uploaded} == {"ms-branch"}
    assert upload_log_indexes == [(1, 2), (2, 2)]

    class FailingHfApi:
        def upload_file(self, **_kwargs):
            raise ValueError("boom")

    manager.hf_api = FailingHfApi()
    manager.get_repo_files_metadata = lambda **_kwargs: []
    upload_log_indexes.clear()

    with pytest.raises(AggregateError) as exc:
        manager.upload_files_to_huggingface("owner/repo", upload_root, num_threads=1)

    assert len(exc.value.exceptions) == 4
    assert upload_log_indexes == [(1, 4), (2, 4), (3, 4), (4, 4)]


def test_repo_manager_upload_rejects_parent_path_in_repo(tmp_path):
    upload_root = tmp_path / "upload"
    upload_root.mkdir()

    manager = _repo_manager_with_apis()

    with pytest.raises(ValueError, match="仓库路径不能包含"):
        manager.upload_files_to_repo(
            api_type="huggingface",
            repo_id="owner/repo",
            upload_path=upload_root,
            path_in_repo="../bad",
        )


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
    manager.hf_api = types.SimpleNamespace(hf_hub_download="hf-download")
    manager.get_repo_file = lambda **_kwargs: ["aa/a.txt", "bb/b.txt", "aa/nested/c.txt"]

    manager.download_files_from_huggingface(
        "owner/repo",
        tmp_path,
        folder="aa/",
        num_threads=3,
        revision="hf-rev",
    )
    assert captured[0] == (
        "hf-download",
        [
            {
                "repo_id": "owner/repo",
                "repo_type": "model",
                "local_dir": tmp_path,
                "filename": "aa/a.txt",
                "revision": "hf-rev",
            },
            {
                "repo_id": "owner/repo",
                "repo_type": "model",
                "local_dir": tmp_path,
                "filename": "aa/nested/c.txt",
                "revision": "hf-rev",
            },
        ],
    )
    assert captured[1] == ("start", 3)

    captured.clear()
    manager.download_files_from_modelscope(
        "owner/repo",
        tmp_path,
        repo_type="dataset",
        folder="bb/",
        num_threads=2,
        revision="ms-rev",
    )
    assert captured[0] == (
        "ms-download",
        [
            {
                "repo_id": "owner/repo",
                "repo_type": "dataset",
                "local_dir": tmp_path,
                "allow_patterns": "bb/b.txt",
                "revision": "ms-rev",
            }
        ],
    )
    assert captured[1] == ("start", 2)


def test_repo_manager_mirror_repo_files_uses_metadata_and_revision(monkeypatch):
    manager = _repo_manager_with_apis()
    check_calls = []
    metadata_calls = []
    download_calls = []
    uploaded = []
    mirror_log_indexes = []

    def fake_log_info(message, *args, **_kwargs):
        if message == "[%s/%s] 镜像 %s":
            mirror_log_indexes.append(args[:2])

    monkeypatch.setattr(repo_module.logger, "info", fake_log_info)

    def fake_check_repo(**kwargs):
        check_calls.append(kwargs)
        return True

    def fake_get_repo_files_metadata(**kwargs):
        metadata_calls.append(kwargs)
        if kwargs["api_type"] == "huggingface":
            return [
                {"path": "same.bin", "type": "file", "sha256": _sha256("same")},
                {"path": "changed.bin", "type": "file", "sha256": _sha256("changed-local")},
                {"path": "missing.bin", "type": "file", "sha256": _sha256("missing")},
                {"path": "folder", "type": "directory", "sha256": None},
            ]
        return [
            {"path": "same.bin", "type": "file", "sha256": _sha256("same")},
            {"path": "changed.bin", "type": "file", "sha256": _sha256("changed-remote")},
        ]

    def fake_hf_hub_download(**kwargs):
        download_calls.append(kwargs)
        file_path = Path(kwargs["local_dir"]) / kwargs["filename"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(kwargs["filename"], encoding="utf-8")
        return file_path

    class FakeMsApi:
        def upload_file(self, **kwargs):
            assert kwargs["path_or_fileobj"].exists()
            uploaded.append(kwargs)

    manager.check_repo = fake_check_repo
    manager.get_repo_files_metadata = fake_get_repo_files_metadata
    manager.hf_api = types.SimpleNamespace(hf_hub_download=fake_hf_hub_download)
    manager.ms_api = FakeMsApi()
    monkeypatch.setitem(sys.modules, "huggingface_hub", types.SimpleNamespace(hf_hub_download=fake_hf_hub_download))

    manager.mirror_repo_files(
        src_api_type="huggingface",
        dst_api_type="modelscope",
        src_repo_id="owner/src",
        dst_repo_id="owner/dst",
        src_repo_type="model",
        dst_repo_type="dataset",
        visibility=True,
        revision="mirror-rev",
        num_threads=1,
        retry_times=1,
    )

    assert check_calls == [
        {
            "api_type": "modelscope",
            "repo_id": "owner/dst",
            "repo_type": "dataset",
            "visibility": True,
        }
    ]
    assert metadata_calls == [
        {
            "api_type": "huggingface",
            "repo_id": "owner/src",
            "repo_type": "model",
            "revision": "mirror-rev",
        },
        {
            "api_type": "modelscope",
            "repo_id": "owner/dst",
            "repo_type": "dataset",
            "revision": "mirror-rev",
        },
    ]
    assert {kwargs["filename"] for kwargs in download_calls} == {"changed.bin", "missing.bin"}
    assert {kwargs["revision"] for kwargs in download_calls} == {"mirror-rev"}
    assert {kwargs["path_in_repo"] for kwargs in uploaded} == {"changed.bin", "missing.bin"}
    assert {kwargs["repo_type"] for kwargs in uploaded} == {"dataset"}
    assert {kwargs["revision"] for kwargs in uploaded} == {"mirror-rev"}
    assert {kwargs["token"] for kwargs in uploaded} == {"ms-token"}
    assert mirror_log_indexes == [(1, 2), (2, 2)]


def test_repo_manager_mirror_repo_files_can_use_fast_download(monkeypatch):
    manager = _repo_manager_with_apis()
    download_url_calls = []
    download_calls = []
    uploaded = []

    class FakeHfApi:
        def upload_file(self, **kwargs):
            assert kwargs["path_or_fileobj"].exists()
            uploaded.append(kwargs)

    manager.hf_api = FakeHfApi()
    manager.check_repo = lambda **_kwargs: True
    manager.get_repo_files_metadata = lambda **kwargs: [
        {"path": "nested/file.bin", "type": "file", "sha256": _sha256("src")}
    ] if kwargs["api_type"] == "modelscope" else []

    def fake_get_repo_file_download_url(**kwargs):
        download_url_calls.append(kwargs)
        return "https://example.test/nested/file.bin"

    def fake_download_file(**kwargs):
        download_calls.append(kwargs)
        file_path = Path(kwargs["path"]) / kwargs["save_name"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("downloaded", encoding="utf-8")
        return file_path

    manager.get_repo_file_download_url = fake_get_repo_file_download_url
    monkeypatch.setattr(repo_module, "download_file", fake_download_file)

    manager.mirror_repo_files(
        src_api_type="modelscope",
        dst_api_type="huggingface",
        src_repo_id="owner/src",
        dst_repo_id="owner/dst",
        revision="fast-rev",
        use_fast_download=True,
        download_tool="aria2",
        download_split=16,
        download_progress=False,
        num_threads=1,
        retry_times=1,
    )

    assert download_url_calls == [
        {
            "api_type": "modelscope",
            "repo_id": "owner/src",
            "file_path": "nested/file.bin",
            "repo_type": "model",
            "revision": "fast-rev",
        }
    ]
    assert len(download_calls) == 1
    assert download_calls[0]["url"] == "https://example.test/nested/file.bin"
    assert download_calls[0]["path"].name == "nested"
    assert download_calls[0]["save_name"] == "file.bin"
    assert download_calls[0]["tool"] == "aria2"
    assert download_calls[0]["split"] == 16
    assert download_calls[0]["progress"] is False
    assert uploaded[0]["path_in_repo"] == "nested/file.bin"
    assert uploaded[0]["revision"] == "fast-rev"
