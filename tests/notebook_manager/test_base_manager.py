"""Notebook 基础管理器测试"""

import pytest

from sd_webui_all_in_one.notebook_manager import base_manager as notebook_base


class FakeRepoManager:
    def __init__(self, hf_token=None, ms_token=None):
        self.hf_token = hf_token
        self.ms_token = ms_token
        self.calls = []

    def upload_files_to_repo(self, **kwargs):
        self.calls.append(("upload", kwargs))

    def download_files_from_repo(self, **kwargs):
        self.calls.append(("download", kwargs))

    def get_repo_files_metadata(self, **kwargs):
        self.calls.append(("metadata", kwargs))
        return [{"path": "weights/a.bin"}]

    def get_repo_file_download_url(self, **kwargs):
        self.calls.append(("download_url", kwargs))
        return "https://example.test/download.bin"

    def mirror_repo_files(self, **kwargs):
        self.calls.append(("mirror", kwargs))


class FakeTunnelManager:
    def __init__(self, workspace, port):
        self.workspace = workspace
        self.port = port
        self.calls = []

    def start_tunnel(self, **kwargs):
        self.calls.append(kwargs)
        return {"local_url": "http://127.0.0.1:7860", "cloudflare": "https://cf.example"}

    def stop_all(self):
        self.calls.append(("stop_all", {}))


class FakeTCMalloc:
    def __init__(self, workspace):
        self.workspace = workspace


@pytest.fixture
def notebook_manager(monkeypatch, tmp_path):
    monkeypatch.setattr(notebook_base, "RepoManager", FakeRepoManager)
    monkeypatch.setattr(notebook_base, "TunnelManager", FakeTunnelManager)
    monkeypatch.setattr(notebook_base, "TCMalloc", FakeTCMalloc)
    return notebook_base.BaseManager(tmp_path / "workspace", "webui", hf_token="hf", ms_token="ms", port=9000)


def test_notebook_base_manager_initializes_and_parses_commands(notebook_manager, tmp_path):
    assert notebook_manager.workspace == tmp_path / "workspace"
    assert notebook_manager.workspace.is_dir()
    assert notebook_manager.repo_manager.hf_token == "hf"
    assert notebook_manager.tun_manager.port == 9000
    assert notebook_manager.parse_cmd_str_to_list('--theme "dark mode"') == ["--theme", "dark mode"]
    assert notebook_manager.parse_cmd_list_to_str(["--theme", "dark mode"]) == "--theme 'dark mode'"


def test_notebook_get_model_from_list_downloads_enabled_items(notebook_manager):
    calls = []

    def fake_get_model(url, path, filename=None, tool="aria2"):
        calls.append((url, path, filename, tool))

    notebook_manager.get_model = fake_get_model
    notebook_manager.get_model_from_list("/models", [["skip", 0], ["a", 1], ["b", 2, "b.bin"], ["bad"]])

    assert calls == [
        ("a", "/models", None, "aria2"),
        ("b", "/models", "b.bin", "aria2"),
    ]


def test_notebook_gpu_check_and_delegates(monkeypatch, notebook_manager, tmp_path):
    monkeypatch.setattr(notebook_base, "get_gpu_list", lambda: [])
    monkeypatch.setattr(notebook_base, "is_colab_environment", lambda: False)

    with pytest.raises(RuntimeError):
        notebook_manager.check_avaliable_gpu()

    download_calls = []
    monkeypatch.setattr(notebook_base, "download_archive_and_unpack", lambda **kwargs: download_calls.append(kwargs))
    notebook_manager.download_and_extract("https://example.test/a.zip", tmp_path / "out", name="a.zip")
    assert download_calls == [{"url": "https://example.test/a.zip", "local_dir": tmp_path / "out", "name": "a.zip"}]

    notebook_manager.upload_files_to_repo(
        "huggingface",
        "owner/repo",
        tmp_path / "upload",
        path_in_repo="outputs",
        visibility=True,
        num_threads=2,
        revision="hf-rev",
    )
    notebook_manager.download_files_from_repo(
        "modelscope",
        "owner/repo",
        tmp_path / "download",
        folder="aa",
        num_threads=3,
        revision="ms-rev",
    )
    assert notebook_manager.repo_manager.calls[0][0] == "upload"
    assert notebook_manager.repo_manager.calls[1][0] == "download"
    assert notebook_manager.repo_manager.calls[0][1]["revision"] == "hf-rev"
    assert notebook_manager.repo_manager.calls[0][1]["path_in_repo"] == "outputs"
    assert notebook_manager.repo_manager.calls[1][1]["revision"] == "ms-rev"
    url = notebook_manager.get_repo_file_download_url(
        "huggingface",
        "owner/repo",
        "weights/a.bin",
        revision="hf-rev",
    )
    assert url == "https://example.test/download.bin"
    assert notebook_manager.repo_manager.calls[2] == (
        "download_url",
        {
            "api_type": "huggingface",
            "repo_id": "owner/repo",
            "file_path": "weights/a.bin",
            "repo_type": "model",
            "revision": "hf-rev",
        },
    )
    metadata = notebook_manager.get_repo_files_metadata(
        "modelscope",
        "owner/repo",
        repo_type="dataset",
        include_dirs=True,
        include_raw=True,
    )
    assert metadata == [{"path": "weights/a.bin"}]
    assert notebook_manager.repo_manager.calls[3] == (
        "metadata",
        {
            "api_type": "modelscope",
            "repo_id": "owner/repo",
            "repo_type": "dataset",
            "include_dirs": True,
            "include_raw": True,
        },
    )
    notebook_manager.mirror_repo_files(
        "huggingface",
        "modelscope",
        "owner/src",
        "owner/dst",
        dst_repo_type="dataset",
        visibility=True,
        revision="mirror-rev",
        num_threads=4,
        retry_times=2,
        use_fast_download=True,
        download_tool="aria2",
        download_split=16,
        download_progress=False,
    )
    assert notebook_manager.repo_manager.calls[4] == (
        "mirror",
        {
            "src_api_type": "huggingface",
            "dst_api_type": "modelscope",
            "src_repo_id": "owner/src",
            "dst_repo_id": "owner/dst",
            "src_repo_type": "model",
            "dst_repo_type": "dataset",
            "visibility": True,
            "num_threads": 4,
            "use_fast_download": True,
            "download_tool": "aria2",
            "download_split": 16,
            "download_progress": False,
            "revision": "mirror-rev",
            "retry_times": 2,
        },
    )

    tunnel = notebook_manager.get_tunnel_url(use_cloudflare=True, webui_name="Demo")
    assert tunnel["cloudflare"] == "https://cf.example"
    assert notebook_manager.tun_manager.calls[0]["check"] is False
