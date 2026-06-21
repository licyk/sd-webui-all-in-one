from pathlib import Path

import pytest

from sd_webui_all_in_one import portable_manager


def test_parse_portable_filename_stable_and_nightly():
    stable = portable_manager.parse_portable_filename("sd_webui-licyk-v1.2.3.7z")
    nightly = portable_manager.parse_portable_filename("comfyui_rocm-licyk-20250616-nightly.tar.gz")

    assert stable == {
        "software": "sd_webui",
        "signature": "licyk",
        "channel": "stable",
        "build_date": None,
        "version": "1.2.3",
        "extension": "7z",
    }
    assert nightly == {
        "software": "comfyui_rocm",
        "signature": "licyk",
        "channel": "nightly",
        "build_date": "20250616",
        "version": None,
        "extension": "tar.gz",
    }

    with pytest.raises(ValueError):
        portable_manager.parse_portable_filename("invalid-name.7z")


def test_filter_portable_paths_skips_non_portable_and_invalid_files():
    assert portable_manager.filter_portable_paths(
        [
            "portable/sd_webui-licyk-v1.0.0.7z",
            "portable/not-a-portable.7z",
            "models/model.bin",
        ]
    ) == ["portable/sd_webui-licyk-v1.0.0.7z"]


def test_filter_portable_paths_supports_custom_repo_path():
    paths = [
        "portable/sd_webui-licyk-v1.0.0.7z",
        "release/nightly/comfyui-licyk-20250616-nightly.7z",
        "release/nightly/not-a-portable.7z",
    ]

    assert portable_manager.filter_portable_paths(paths, path_in_repo="/release\\nightly/") == ["release/nightly/comfyui-licyk-20250616-nightly.7z"]
    assert portable_manager.filter_portable_paths(paths, path_in_repo="") == [
        "portable/sd_webui-licyk-v1.0.0.7z",
        "release/nightly/comfyui-licyk-20250616-nightly.7z",
    ]

    with pytest.raises(ValueError, match="不能包含"):
        portable_manager.filter_portable_paths(paths, path_in_repo="../portable")


def test_build_portable_source_resources_groups_and_sorts_versions():
    files = [
        portable_manager.build_portable_file_resource("portable/sd_webui-licyk-v1.2.0.7z", "https://example.test/v1.2")[1],
        portable_manager.build_portable_file_resource("portable/sd_webui-licyk-v1.10.0.7z", "https://example.test/v1.10")[1],
        portable_manager.build_portable_file_resource("portable/sd_webui-licyk-20250101-nightly.7z", "https://example.test/20250101")[1],
        portable_manager.build_portable_file_resource("portable/sd_webui-licyk-20250616-nightly.7z", "https://example.test/20250616")[1],
        portable_manager.build_portable_file_resource("portable/custom_app-abc-v1.0.0.zip", "https://example.test/custom")[1],
    ]

    resources = portable_manager.build_portable_source_resources(files)

    assert list(resources) == ["custom_app", "sd_webui"]
    assert resources["sd_webui"]["display_name"] == "Stable Diffusion WebUI (NVIDIA)"
    assert resources["sd_webui"]["description"] == "Stable Diffusion WebUI 的 NVIDIA 显卡整合包，上手简单，操作方便，适合入门使用。"
    assert [item["filename"] for item in resources["sd_webui"]["stable"]] == [
        "sd_webui-licyk-v1.10.0.7z",
        "sd_webui-licyk-v1.2.0.7z",
    ]
    assert [item["filename"] for item in resources["sd_webui"]["nightly"]] == [
        "sd_webui-licyk-20250616-nightly.7z",
        "sd_webui-licyk-20250101-nightly.7z",
    ]
    assert resources["custom_app"]["display_name"] == "custom_app"
    assert resources["custom_app"]["description"] == ""


def test_build_portable_source_resources_uses_gpu_variant_metadata():
    files = [
        portable_manager.build_portable_file_resource("portable/sd_webui_rocm-licyk-v1.0.0.7z", "https://example.test/sd-webui-rocm")[1],
        portable_manager.build_portable_file_resource("portable/fooocus_xpu-licyk-v1.0.0.7z", "https://example.test/fooocus-xpu")[1],
    ]

    resources = portable_manager.build_portable_source_resources(files)

    assert resources["sd_webui_rocm"]["display_name"] == "Stable Diffusion WebUI (ROCm)"
    assert resources["sd_webui_rocm"]["description"] == "Stable Diffusion WebUI 的 AMD 显卡整合包，上手简单，操作方便，适合入门使用。"
    assert resources["fooocus_xpu"]["display_name"] == "Fooocus (XPU)"
    assert resources["fooocus_xpu"]["description"] == "Fooocus 的 Intel 显卡整合包，化繁为简，更专注于提示词书写。"


def test_build_portable_list_data_uses_new_resources_shape():
    file_resource = portable_manager.build_portable_file_resource(
        "portable/fooocus-licyk-v2.0.0.7z",
        "https://example.test/fooocus",
    )[1]

    data = portable_manager.build_portable_list_data(
        resources={"modelscope": [file_resource]},
        update_time="2026-06-16T00:00:00Z",
    )

    assert data == {
        "update_time": "2026-06-16T00:00:00Z",
        "resources": {
            "modelscope": {
                "fooocus": {
                    "display_name": "Fooocus (NVIDIA)",
                    "description": "Fooocus 的 NVIDIA 显卡整合包，化繁为简，更专注于提示词书写。",
                    "stable": [
                        {
                            "filename": "fooocus-licyk-v2.0.0.7z",
                            "path": "portable/fooocus-licyk-v2.0.0.7z",
                            "url": "https://example.test/fooocus",
                            "signature": "licyk",
                            "channel": "stable",
                            "version": "2.0.0",
                            "build_date": None,
                            "extension": "7z",
                        }
                    ],
                    "nightly": [],
                }
            }
        },
    }


def test_build_portable_list_from_repositories_collects_only_valid_portables():
    class FakeRepoManager:
        def __init__(self):
            self.url_calls = []

        def get_repo_file(self, **kwargs):
            assert kwargs == {
                "api_type": "huggingface",
                "repo_id": "owner/repo",
                "repo_type": "model",
                "revision": "main",
            }
            return [
                "portable/sd_webui-licyk-v1.0.0.7z",
                "portable/invalid.7z",
                "models/model.bin",
            ]

        def get_repo_file_download_url(self, **kwargs):
            self.url_calls.append(kwargs)
            return f"https://example.test/{Path(kwargs['file_path']).name}"

    manager = FakeRepoManager()
    data = portable_manager.build_portable_list_from_repositories(
        manager=manager,  # type: ignore[arg-type]
        sources=[{"source": "huggingface", "repo_id": "owner/repo", "repo_type": "model"}],
        revision="main",
        update_time="2026-06-16T00:00:00Z",
    )

    assert manager.url_calls == [
        {
            "api_type": "huggingface",
            "repo_id": "owner/repo",
            "file_path": "portable/sd_webui-licyk-v1.0.0.7z",
            "repo_type": "model",
            "revision": "main",
        }
    ]
    assert data["resources"]["huggingface"]["sd_webui"]["stable"][0]["url"] == "https://example.test/sd_webui-licyk-v1.0.0.7z"


def test_build_portable_list_from_repositories_uses_custom_repo_path():
    class FakeRepoManager:
        def __init__(self):
            self.url_calls = []

        def get_repo_file(self, **_kwargs):
            return [
                "portable/sd_webui-licyk-v1.0.0.7z",
                "release/nightly/comfyui-licyk-20250616-nightly.7z",
            ]

        def get_repo_file_download_url(self, **kwargs):
            self.url_calls.append(kwargs)
            return f"https://example.test/{kwargs['file_path']}"

    manager = FakeRepoManager()
    data = portable_manager.build_portable_list_from_repositories(
        manager=manager,  # type: ignore[arg-type]
        sources=[{"source": "modelscope", "repo_id": "owner/repo", "repo_type": "model"}],
        path_in_repo="release/nightly",
    )

    assert manager.url_calls == [
        {
            "api_type": "modelscope",
            "repo_id": "owner/repo",
            "file_path": "release/nightly/comfyui-licyk-20250616-nightly.7z",
            "repo_type": "model",
            "revision": None,
        }
    ]
    assert list(data["resources"]["modelscope"]) == ["comfyui"]


def test_build_portable_list_from_repositories_requires_source():
    with pytest.raises(ValueError, match="至少需要配置"):
        portable_manager.build_portable_list_from_repositories(
            manager=object(),  # type: ignore[arg-type]
            sources=[],
        )


def test_upload_portable_package_requires_directory_and_target(tmp_path):
    upload_root = tmp_path / "upload"
    target = {"source": "huggingface", "repo_id": "owner/repo", "repo_type": "model"}

    with pytest.raises(FileNotFoundError, match="整合包上传目录不存在"):
        portable_manager.upload_portable_package_to_repositories(
            manager=object(),  # type: ignore[arg-type]
            upload_path=upload_root,
            targets=[target],
        )

    upload_root.mkdir()
    with pytest.raises(ValueError, match="至少需要配置"):
        portable_manager.upload_portable_package_to_repositories(
            manager=object(),  # type: ignore[arg-type]
            upload_path=upload_root,
            targets=[],
        )


def test_upload_portable_package_uploads_targets_with_config(tmp_path):
    upload_root = tmp_path / "sdnote"
    upload_root.mkdir()
    calls = []

    class FakeRepoManager:
        def upload_files_to_repo(self, **kwargs):
            calls.append(kwargs)

    portable_manager.upload_portable_package_to_repositories(
        manager=FakeRepoManager(),  # type: ignore[arg-type]
        upload_path=upload_root,
        targets=[
            {"source": "huggingface", "repo_id": "hf/repo", "repo_type": "model"},
            {"source": "modelscope", "repo_id": "ms/repo", "repo_type": "dataset"},
        ],
        path_in_repo="portable/nightly",
        revision="main",
        visibility=True,
        num_threads=3,
        target_workers=1,
    )

    assert calls == [
        {
            "api_type": "huggingface",
            "repo_id": "hf/repo",
            "upload_path": upload_root,
            "path_in_repo": "portable/nightly",
            "repo_type": "model",
            "visibility": True,
            "num_threads": 3,
            "revision": "main",
        },
        {
            "api_type": "modelscope",
            "repo_id": "ms/repo",
            "upload_path": upload_root,
            "path_in_repo": "portable/nightly",
            "repo_type": "dataset",
            "visibility": True,
            "num_threads": 3,
            "revision": "main",
        },
    ]


def test_upload_portable_package_aggregates_target_failures(tmp_path):
    upload_root = tmp_path / "sdnote"
    upload_root.mkdir()

    class FakeRepoManager:
        def upload_files_to_repo(self, **kwargs):
            if kwargs["api_type"] == "modelscope":
                raise RuntimeError("boom")

    with pytest.raises(portable_manager.AggregateError) as exc:
        portable_manager.upload_portable_package_to_repositories(
            manager=FakeRepoManager(),  # type: ignore[arg-type]
            upload_path=upload_root,
            targets=[
                {"source": "huggingface", "repo_id": "hf/repo", "repo_type": "model"},
                {"source": "modelscope", "repo_id": "ms/repo", "repo_type": "model"},
            ],
            target_workers=1,
        )

    assert len(exc.value.exceptions) == 1
    assert "modelscope:ms/repo (model) 上传失败: boom" == str(exc.value.exceptions[0])
