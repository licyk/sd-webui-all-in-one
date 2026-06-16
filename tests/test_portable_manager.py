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
    assert resources["sd_webui"]["display_name"] == "Stable Diffusion WebUI"
    assert resources["sd_webui"]["description"] == "上手简单，操作方便，适合入门使用。"
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
                    "display_name": "Fooocus",
                    "description": "化繁为简，更专注于提示词书写。",
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


def test_build_portable_list_from_repositories_requires_source():
    with pytest.raises(ValueError, match="至少需要配置"):
        portable_manager.build_portable_list_from_repositories(
            manager=object(),  # type: ignore[arg-type]
            sources=[],
        )
