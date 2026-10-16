"""自动镜像源设置测试"""

from sd_webui_all_in_one.base_manager import base as base_module
from sd_webui_all_in_one.base_manager.base import mirrors as base_mirrors


def test_resolve_auto_mirror_settings_uses_official_sources(monkeypatch):
    monkeypatch.setattr(base_mirrors, "network_gfw_test", lambda: True)

    resolved = base_module.resolve_auto_mirror_settings(
        auto_mirror=True,
        use_pypi_mirror=True,
        use_github_mirror=True,
        use_hf_mirror=True,
        custom_github_mirror="https://github.example",
        custom_hf_mirror="https://hf.example",
        model_download_resource_type="modelscope",
    )

    assert resolved == {
        "use_pypi_mirror": False,
        "use_github_mirror": False,
        "custom_github_mirror": None,
        "use_hf_mirror": False,
        "custom_hf_mirror": None,
        "model_download_resource_type": "huggingface",
    }


def test_resolve_auto_mirror_settings_uses_mirror_sources(monkeypatch):
    monkeypatch.setattr(base_mirrors, "network_gfw_test", lambda: False)

    resolved = base_module.resolve_auto_mirror_settings(
        auto_mirror=True,
        use_pypi_mirror=False,
        use_github_mirror=False,
        use_hf_mirror=False,
        custom_github_mirror=["https://github.example"],
        custom_hf_mirror=["https://hf.example"],
        model_download_resource_type="huggingface",
    )

    assert resolved == {
        "use_pypi_mirror": True,
        "use_github_mirror": True,
        "custom_github_mirror": None,
        "use_hf_mirror": True,
        "custom_hf_mirror": None,
        "model_download_resource_type": "modelscope",
    }


def test_resolve_auto_mirror_settings_can_be_disabled(monkeypatch):
    def fail_network_probe():
        raise AssertionError("network probe should not run")

    monkeypatch.setattr(base_mirrors, "network_gfw_test", fail_network_probe)

    resolved = base_module.resolve_auto_mirror_settings(
        auto_mirror=False,
        use_pypi_mirror=False,
        use_github_mirror=True,
        custom_github_mirror="https://github.example",
        use_hf_mirror=False,
        custom_hf_mirror=None,
        model_download_resource_type="huggingface",
    )

    assert resolved == {
        "use_pypi_mirror": False,
        "use_github_mirror": True,
        "custom_github_mirror": "https://github.example",
        "use_hf_mirror": False,
        "custom_hf_mirror": None,
        "model_download_resource_type": "huggingface",
    }
