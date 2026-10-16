"""自管理命令: 整合包列表与上传测试"""

from sd_webui_all_in_one.cli_manager import utils as cli_utils
from tests.cli_manager.helpers import single_command_parser


def test_self_manager_portable_list_cli_parse_smoke(monkeypatch, tmp_path):
    monkeypatch.setattr(cli_utils, "SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH", tmp_path / "launch")
    parser = single_command_parser(cli_utils.register_manager)
    calls = []

    monkeypatch.setattr(cli_utils, "portable_list_cli", lambda **kwargs: calls.append(kwargs))

    args = parser.parse_args(["self-manager", "portable", "list"])
    args.func(args)

    args = parser.parse_args(
        [
            "self-manager",
            "portable",
            "list",
            "--output",
            str(tmp_path / "portable.json"),
            "--hf-repo-id",
            "arg-hf/repo",
            "--hf-repo-type",
            "model",
            "--ms-repo-id",
            "arg-ms/repo",
            "--ms-repo-type",
            "dataset",
            "--revision",
            "main",
            "--path-in-repo",
            "release/nightly",
            "--hf-token",
            "hf",
            "--ms-token",
            "ms",
        ]
    )
    args.func(args)

    assert calls == [
        {
            "output": tmp_path / "launch" / "portable_list.json",
            "hf_repo_id": None,
            "hf_repo_type": "model",
            "ms_repo_id": None,
            "ms_repo_type": "model",
            "revision": None,
            "path_in_repo": "portable",
            "hf_token": None,
            "ms_token": None,
        },
        {
            "output": tmp_path / "portable.json",
            "hf_repo_id": "arg-hf/repo",
            "hf_repo_type": "model",
            "ms_repo_id": "arg-ms/repo",
            "ms_repo_type": "dataset",
            "revision": "main",
            "path_in_repo": "release/nightly",
            "hf_token": "hf",
            "ms_token": "ms",
        },
    ]


def test_self_manager_portable_upload_cli_parse_smoke(monkeypatch, tmp_path):
    parser = single_command_parser(cli_utils.register_manager)
    calls = []

    monkeypatch.setattr(cli_utils, "portable_upload_cli", lambda **kwargs: calls.append(kwargs))

    args = parser.parse_args(["self-manager", "portable", "upload", str(tmp_path / "sdnote")])
    args.func(args)

    args = parser.parse_args(
        [
            "self-manager",
            "portable",
            "upload",
            str(tmp_path / "custom-upload"),
            "--hf-repo-id",
            "arg-hf/repo",
            "--hf-repo-type",
            "dataset",
            "--ms-repo-id",
            "arg-ms/repo",
            "--ms-repo-type",
            "model",
            "--revision",
            "main",
            "--path-in-repo",
            "portable/nightly",
            "--public",
            "--threads",
            "4",
            "--target-workers",
            "2",
            "--hf-token",
            "hf",
            "--ms-token",
            "ms",
        ]
    )
    args.func(args)

    assert calls == [
        {
            "upload_path": tmp_path / "sdnote",
            "path_in_repo": None,
            "hf_repo_id": None,
            "hf_repo_type": "model",
            "ms_repo_id": None,
            "ms_repo_type": "model",
            "revision": None,
            "visibility": False,
            "num_threads": 1,
            "target_workers": None,
            "hf_token": None,
            "ms_token": None,
        },
        {
            "upload_path": tmp_path / "custom-upload",
            "path_in_repo": "portable/nightly",
            "hf_repo_id": "arg-hf/repo",
            "hf_repo_type": "dataset",
            "ms_repo_id": "arg-ms/repo",
            "ms_repo_type": "model",
            "revision": "main",
            "visibility": True,
            "num_threads": 4,
            "target_workers": 2,
            "hf_token": "hf",
            "ms_token": "ms",
        },
    ]


def test_self_manager_portable_list_cli_handler(monkeypatch, tmp_path):
    instances = []
    build_calls = []
    save_calls = []

    class FakeCliRepoManager:
        def __init__(self, hf_token=None, ms_token=None):
            self.hf_token = hf_token
            self.ms_token = ms_token
            instances.append(self)

    def fake_build_portable_list_from_repositories(**kwargs):
        build_calls.append(kwargs)
        return {"update_time": "2026-06-16T00:00:00Z", "resources": {}}

    def fake_save_portable_list(data, output):
        save_calls.append((data, output))

    monkeypatch.setenv("HF_TOKEN", "env-hf")
    monkeypatch.setenv("MODELSCOPE_API_TOKEN", "env-ms")
    monkeypatch.setattr(cli_utils, "RepoManager", FakeCliRepoManager)
    monkeypatch.setattr(cli_utils, "build_portable_list_from_repositories", fake_build_portable_list_from_repositories)
    monkeypatch.setattr(cli_utils, "save_portable_list", fake_save_portable_list)

    cli_utils.portable_list_cli(
        output=tmp_path / "portable_list.json",
        hf_repo_id="hf/repo",
        hf_repo_type="dataset",
        ms_repo_id=None,
        ms_repo_type="model",
        revision="main",
        path_in_repo="release/nightly",
    )

    assert instances[-1].hf_token == "env-hf"
    assert instances[-1].ms_token == "env-ms"
    assert build_calls == [
        {
            "manager": instances[-1],
            "sources": [{"source": "huggingface", "repo_id": "hf/repo", "repo_type": "dataset"}],
            "revision": "main",
            "path_in_repo": "release/nightly",
        }
    ]
    assert save_calls == [
        (
            {"update_time": "2026-06-16T00:00:00Z", "resources": {}},
            tmp_path / "portable_list.json",
        )
    ]


def test_self_manager_portable_upload_cli_handler(monkeypatch, tmp_path):
    instances = []
    upload_calls = []

    class FakeCliRepoManager:
        def __init__(self, hf_token=None, ms_token=None):
            self.hf_token = hf_token
            self.ms_token = ms_token
            instances.append(self)

    def fake_upload_portable_package_to_repositories(**kwargs):
        upload_calls.append(kwargs)

    monkeypatch.setenv("HF_TOKEN", "env-hf")
    monkeypatch.setenv("MODELSCOPE_API_TOKEN", "env-ms")
    monkeypatch.setattr(cli_utils, "RepoManager", FakeCliRepoManager)
    monkeypatch.setattr(cli_utils, "upload_portable_package_to_repositories", fake_upload_portable_package_to_repositories)

    cli_utils.portable_upload_cli(
        upload_path=tmp_path / "sdnote",
        path_in_repo="portable/nightly",
        hf_repo_id=None,
        hf_repo_type="model",
        ms_repo_id="ms/repo",
        ms_repo_type="dataset",
        revision="main",
        visibility=True,
        num_threads=4,
        target_workers=2,
        hf_token="arg-hf",
    )

    assert instances[-1].hf_token == "arg-hf"
    assert instances[-1].ms_token == "env-ms"
    assert upload_calls == [
        {
            "manager": instances[-1],
            "upload_path": tmp_path / "sdnote",
            "targets": [{"source": "modelscope", "repo_id": "ms/repo", "repo_type": "dataset"}],
            "path_in_repo": "portable/nightly",
            "revision": "main",
            "visibility": True,
            "num_threads": 4,
            "target_workers": 2,
        }
    ]
