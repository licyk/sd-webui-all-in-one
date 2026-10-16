"""仓库管理器文件列表与元数据测试"""

import sys
import types

from tests.repo_manager.helpers import repo_manager_with_apis


def test_repo_manager_huggingface_file_listing_and_creation():
    manager = repo_manager_with_apis()
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

    manager = repo_manager_with_apis()
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


def test_repo_manager_modelscope_new_file_info_listing_and_metadata():
    manager = repo_manager_with_apis()
    calls = []

    class NewFileInfo:
        __slots__ = ("path", "type", "size", "blob_id", "is_lfs")

        def __init__(self, path, type, size, blob_id, is_lfs):
            self.path = path
            self.type = type
            self.size = size
            self.blob_id = blob_id
            self.is_lfs = is_lfs

    class ModernHubApi:
        def list_repo_files(self, **kwargs):
            calls.append(kwargs)
            return [
                NewFileInfo(
                    path="weights",
                    type="tree",
                    size=0,
                    blob_id="",
                    is_lfs=False,
                ),
                NewFileInfo(
                    path="weights/a.bin",
                    type="blob",
                    size=456,
                    blob_id="new-sha256",
                    is_lfs=True,
                ),
            ]

    class CompatibilityHubApi:
        def __init__(self):
            self._api = ModernHubApi()

        def get_model_files(self, **_kwargs):
            raise AssertionError("新版 SDK 应使用保留完整元数据的 list_repo_files")

    manager.ms_api = CompatibilityHubApi()

    assert manager.get_ms_repo_files("owner/model", revision="dev") == ["weights/a.bin"]
    assert calls[0] == {
        "repo_id": "owner/model",
        "repo_type": "model",
        "recursive": True,
        "revision": "dev",
    }

    assert manager.get_ms_repo_files_metadata(
        "owner/model",
        revision="dev",
        include_dirs=True,
        include_raw=True,
    ) == [
        {
            "path": "weights",
            "name": "weights",
            "type": "directory",
            "size": None,
            "sha256": None,
            "is_lfs": None,
            "object_id": None,
            "revision": "dev",
            "raw": {
                "path": "weights",
                "type": "tree",
                "size": 0,
                "blob_id": "",
                "is_lfs": False,
            },
        },
        {
            "path": "weights/a.bin",
            "name": "a.bin",
            "type": "file",
            "size": 456,
            "sha256": "new-sha256",
            "is_lfs": True,
            "object_id": "new-sha256",
            "revision": "dev",
            "raw": {
                "path": "weights/a.bin",
                "type": "blob",
                "size": 456,
                "blob_id": "new-sha256",
                "is_lfs": True,
            },
        },
    ]


def test_repo_manager_modelscope_new_lossy_model_listing_infers_directories():
    manager = repo_manager_with_apis()

    class CompatibilityHubApi:
        def get_model_files(self, model_id, recursive=True):
            assert model_id == "owner/model"
            assert recursive is True
            return [
                {"Path": "weights", "Size": 0},
                {"Path": "weights/a.bin", "Size": 123},
                {"Path": "empty.bin", "Size": 0},
            ]

    manager.ms_api = CompatibilityHubApi()

    assert manager.get_ms_repo_files("owner/model") == ["weights/a.bin", "empty.bin"]
    assert manager.get_ms_repo_files_metadata("owner/model", include_dirs=True) == [
        {
            "path": "weights",
            "name": "weights",
            "type": "directory",
            "size": None,
            "sha256": None,
            "is_lfs": None,
            "object_id": None,
            "revision": None,
        },
        {
            "path": "weights/a.bin",
            "name": "a.bin",
            "type": "file",
            "size": 123,
            "sha256": None,
            "is_lfs": None,
            "object_id": None,
            "revision": None,
        },
        {
            "path": "empty.bin",
            "name": "empty.bin",
            "type": "file",
            "size": 0,
            "sha256": None,
            "is_lfs": None,
            "object_id": None,
            "revision": None,
        },
    ]


def test_repo_manager_files_metadata_normalizes_huggingface_and_modelscope():
    manager = repo_manager_with_apis()
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
    manager = repo_manager_with_apis()
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

    assert manager.get_hf_repo_file_download_url("owner/repo", "weights/a.bin", revision="main") == "https://hf.example/owner/repo/resolve/main/weights/a.bin"
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

    assert manager.get_ms_repo_file_download_url("owner/model", "weights/a.bin", revision="v1") == "https://ms.example/model/v1/weights/a.bin"
    assert manager.get_repo_file_download_url("modelscope", "owner/dataset", "data/a.txt", repo_type="dataset") == "https://ms.example/dataset/master/data/a.txt"
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
