"""自管理命令: 模型仓库操作测试"""

import json

from sd_webui_all_in_one.cli_manager import utils as cli_utils
from tests.cli_manager.helpers import single_command_parser


def test_self_manager_repo_cli_parse_smoke(monkeypatch, tmp_path):
    parser = single_command_parser(cli_utils.register_manager)
    calls = []

    monkeypatch.setattr(cli_utils, "repo_list_cli", lambda **kwargs: calls.append(("list", kwargs)))
    monkeypatch.setattr(cli_utils, "repo_metadata_cli", lambda **kwargs: calls.append(("metadata", kwargs)))
    monkeypatch.setattr(cli_utils, "repo_url_cli", lambda **kwargs: calls.append(("url", kwargs)))
    monkeypatch.setattr(cli_utils, "repo_check_cli", lambda **kwargs: calls.append(("check", kwargs)))
    monkeypatch.setattr(cli_utils, "repo_upload_cli", lambda **kwargs: calls.append(("upload", kwargs)))
    monkeypatch.setattr(cli_utils, "repo_download_cli", lambda **kwargs: calls.append(("download", kwargs)))
    monkeypatch.setattr(cli_utils, "repo_mirror_cli", lambda **kwargs: calls.append(("mirror", kwargs)))

    args = parser.parse_args(
        [
            "self-manager",
            "repo",
            "list",
            "huggingface",
            "owner/repo",
            "--repo-type",
            "dataset",
            "--revision",
            "main",
            "--format",
            "text",
            "--hf-token",
            "hf",
            "--ms-token",
            "ms",
        ]
    )
    args.func(args)

    args = parser.parse_args(
        [
            "self-manager",
            "repo",
            "metadata",
            "modelscope",
            "owner/repo",
            "--include-dirs",
            "--include-raw",
        ]
    )
    args.func(args)

    args = parser.parse_args(["self-manager", "repo", "url", "huggingface", "owner/repo", "weights/a.bin", "--revision", "url-rev"])
    args.func(args)

    args = parser.parse_args(["self-manager", "repo", "check", "modelscope", "owner/repo", "--repo-type", "dataset", "--public"])
    args.func(args)

    args = parser.parse_args(
        [
            "self-manager",
            "repo",
            "upload",
            "huggingface",
            "owner/repo",
            str(tmp_path / "upload"),
            "--threads",
            "4",
            "--path-in-repo",
            "artifacts/nightly",
            "--public",
            "--revision",
            "upload-rev",
        ]
    )
    args.func(args)

    args = parser.parse_args(
        [
            "self-manager",
            "repo",
            "download",
            "modelscope",
            "owner/repo",
            str(tmp_path / "download"),
            "--folder",
            "weights",
            "--threads",
            "7",
            "--revision",
            "download-rev",
        ]
    )
    args.func(args)

    args = parser.parse_args(
        [
            "self-manager",
            "repo",
            "mirror",
            "huggingface",
            "modelscope",
            "owner/src",
            "owner/dst",
            "--src-repo-type",
            "model",
            "--dst-repo-type",
            "dataset",
            "--public",
            "--revision",
            "mirror-rev",
            "--threads",
            "3",
            "--retry-times",
            "2",
            "--fast-download",
            "--download-tool",
            "aria2",
            "--download-split",
            "16",
            "--no-download-progress",
            "--hf-token",
            "hf",
            "--ms-token",
            "ms",
        ]
    )
    args.func(args)

    assert calls == [
        (
            "list",
            {
                "api_type": "huggingface",
                "repo_id": "owner/repo",
                "repo_type": "dataset",
                "revision": "main",
                "output_format": "text",
                "hf_token": "hf",
                "ms_token": "ms",
            },
        ),
        (
            "metadata",
            {
                "api_type": "modelscope",
                "repo_id": "owner/repo",
                "repo_type": "model",
                "revision": None,
                "include_dirs": True,
                "include_raw": True,
                "output_format": "json",
                "hf_token": None,
                "ms_token": None,
            },
        ),
        (
            "url",
            {
                "api_type": "huggingface",
                "repo_id": "owner/repo",
                "file_path": "weights/a.bin",
                "repo_type": "model",
                "revision": "url-rev",
                "hf_token": None,
                "ms_token": None,
            },
        ),
        (
            "check",
            {
                "api_type": "modelscope",
                "repo_id": "owner/repo",
                "repo_type": "dataset",
                "visibility": True,
                "hf_token": None,
                "ms_token": None,
            },
        ),
        (
            "upload",
            {
                "api_type": "huggingface",
                "repo_id": "owner/repo",
                "upload_path": tmp_path / "upload",
                "path_in_repo": "artifacts/nightly",
                "repo_type": "model",
                "visibility": True,
                "num_threads": 4,
                "revision": "upload-rev",
                "hf_token": None,
                "ms_token": None,
            },
        ),
        (
            "download",
            {
                "api_type": "modelscope",
                "repo_id": "owner/repo",
                "local_dir": tmp_path / "download",
                "repo_type": "model",
                "folder": "weights",
                "num_threads": 7,
                "revision": "download-rev",
                "hf_token": None,
                "ms_token": None,
            },
        ),
        (
            "mirror",
            {
                "src_api_type": "huggingface",
                "dst_api_type": "modelscope",
                "src_repo_id": "owner/src",
                "dst_repo_id": "owner/dst",
                "src_repo_type": "model",
                "dst_repo_type": "dataset",
                "visibility": True,
                "revision": "mirror-rev",
                "num_threads": 3,
                "retry_times": 2,
                "use_fast_download": True,
                "download_tool": "aria2",
                "download_split": 16,
                "download_progress": False,
                "hf_token": "hf",
                "ms_token": "ms",
            },
        ),
    ]


def test_self_manager_repo_cli_handlers_delegate_and_print(monkeypatch, capsys, tmp_path):
    instances = []

    class FakeCliRepoManager:
        def __init__(self, hf_token=None, ms_token=None):
            self.hf_token = hf_token
            self.ms_token = ms_token
            self.calls = []
            instances.append(self)

        def get_repo_file(self, **kwargs):
            self.calls.append(("list", kwargs))
            return ["a.bin", "folder/b.bin"]

        def get_repo_files_metadata(self, **kwargs):
            self.calls.append(("metadata", kwargs))
            return [{"path": "a.bin", "type": "file", "size": 123, "sha256": "sha", "revision": "rev"}]

        def get_repo_file_download_url(self, **kwargs):
            self.calls.append(("url", kwargs))
            return "https://example.test/a.bin"

        def check_repo(self, **kwargs):
            self.calls.append(("check", kwargs))

        def upload_files_to_repo(self, **kwargs):
            self.calls.append(("upload", kwargs))

        def download_files_from_repo(self, **kwargs):
            self.calls.append(("download", kwargs))

        def mirror_repo_files(self, **kwargs):
            self.calls.append(("mirror", kwargs))

    monkeypatch.setenv("HF_TOKEN", "env-hf")
    monkeypatch.setenv("MODELSCOPE_API_TOKEN", "env-ms")
    monkeypatch.setattr(cli_utils, "RepoManager", FakeCliRepoManager)

    cli_utils.repo_list_cli("huggingface", "owner/repo", repo_type="dataset", revision="main", output_format="json")
    assert json.loads(capsys.readouterr().out) == ["a.bin", "folder/b.bin"]
    assert instances[-1].hf_token == "env-hf"
    assert instances[-1].ms_token == "env-ms"
    assert instances[-1].calls == [
        (
            "list",
            {
                "api_type": "huggingface",
                "repo_id": "owner/repo",
                "repo_type": "dataset",
                "revision": "main",
            },
        )
    ]

    cli_utils.repo_metadata_cli(
        "modelscope",
        "owner/repo",
        include_dirs=True,
        include_raw=True,
        output_format="text",
        hf_token="arg-hf",
    )
    metadata_lines = capsys.readouterr().out.strip().splitlines()
    assert metadata_lines == [
        "path\ttype\tsize\tsha256\trevision",
        "a.bin\tfile\t123\tsha\trev",
    ]
    assert instances[-1].hf_token == "arg-hf"
    assert instances[-1].ms_token == "env-ms"
    assert instances[-1].calls == [
        (
            "metadata",
            {
                "api_type": "modelscope",
                "repo_id": "owner/repo",
                "repo_type": "model",
                "revision": None,
                "include_dirs": True,
                "include_raw": True,
            },
        )
    ]

    cli_utils.repo_url_cli("huggingface", "owner/repo", "a.bin", revision="url-rev")
    assert capsys.readouterr().out.strip() == "https://example.test/a.bin"
    assert instances[-1].calls == [
        (
            "url",
            {
                "api_type": "huggingface",
                "repo_id": "owner/repo",
                "file_path": "a.bin",
                "repo_type": "model",
                "revision": "url-rev",
            },
        )
    ]

    cli_utils.repo_check_cli("huggingface", "owner/repo", visibility=True, hf_token="hf", ms_token="ms")
    cli_utils.repo_upload_cli("huggingface", "owner/repo", tmp_path / "upload", path_in_repo="artifacts", num_threads=2, revision="upload-rev")
    cli_utils.repo_download_cli("modelscope", "owner/repo", tmp_path / "download", folder="weights", num_threads=3, revision="download-rev")
    cli_utils.repo_mirror_cli(
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

    assert instances[-4].calls == [
        (
            "check",
            {
                "api_type": "huggingface",
                "repo_id": "owner/repo",
                "repo_type": "model",
                "visibility": True,
            },
        )
    ]
    assert instances[-4].hf_token == "hf"
    assert instances[-4].ms_token == "ms"
    assert instances[-3].calls == [
        (
            "upload",
            {
                "api_type": "huggingface",
                "repo_id": "owner/repo",
                "upload_path": tmp_path / "upload",
                "path_in_repo": "artifacts",
                "repo_type": "model",
                "visibility": False,
                "num_threads": 2,
                "revision": "upload-rev",
            },
        )
    ]
    assert instances[-2].calls == [
        (
            "download",
            {
                "api_type": "modelscope",
                "repo_id": "owner/repo",
                "local_dir": tmp_path / "download",
                "repo_type": "model",
                "folder": "weights",
                "num_threads": 3,
                "revision": "download-rev",
            },
        )
    ]
    assert instances[-1].calls == [
        (
            "mirror",
            {
                "src_api_type": "huggingface",
                "dst_api_type": "modelscope",
                "src_repo_id": "owner/src",
                "dst_repo_id": "owner/dst",
                "src_repo_type": "model",
                "dst_repo_type": "dataset",
                "visibility": True,
                "revision": "mirror-rev",
                "num_threads": 4,
                "retry_times": 2,
                "use_fast_download": True,
                "download_tool": "aria2",
                "download_split": 16,
                "download_progress": False,
            },
        )
    ]
