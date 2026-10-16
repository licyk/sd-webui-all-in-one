"""命令行自动镜像源测试"""

import argparse

from sd_webui_all_in_one.base_manager.base import mirrors as base_mirrors
from sd_webui_all_in_one.cli_manager import (
    auto_mirror,
    comfyui_cli,
)
from tests.cli_manager.helpers import build_parser


def test_apply_auto_mirror_uses_official_sources(monkeypatch):
    monkeypatch.setattr(base_mirrors, "network_gfw_test", lambda: True)
    args = argparse.Namespace(
        auto_mirror=True,
        use_pypi_mirror=True,
        use_github_mirror=True,
        use_hf_mirror=True,
        custom_github_mirror="https://github.example",
        custom_hf_mirror="https://hf.example",
        model_download_resource_type="modelscope",
        source="modelscope",
    )

    auto_mirror.apply_auto_mirror(args)

    assert args.use_pypi_mirror is False
    assert args.use_github_mirror is False
    assert args.use_hf_mirror is False
    assert args.custom_github_mirror is None
    assert args.custom_hf_mirror is None
    assert args.model_download_resource_type == "huggingface"
    assert args.source == "huggingface"


def test_apply_auto_mirror_uses_mirror_sources(monkeypatch):
    monkeypatch.setattr(base_mirrors, "network_gfw_test", lambda: False)
    args = argparse.Namespace(
        auto_mirror=True,
        use_pypi_mirror=False,
        use_github_mirror=False,
        use_hf_mirror=False,
        custom_github_mirror="https://github.example",
        custom_hf_mirror="https://hf.example",
        model_download_resource_type="huggingface",
        source="huggingface",
    )

    auto_mirror.apply_auto_mirror(args)

    assert args.use_pypi_mirror is True
    assert args.use_github_mirror is True
    assert args.use_hf_mirror is True
    assert args.custom_github_mirror is None
    assert args.custom_hf_mirror is None
    assert args.model_download_resource_type == "modelscope"
    assert args.source == "modelscope"


def test_apply_auto_mirror_can_be_disabled(monkeypatch):
    def fail_network_probe():
        raise AssertionError("network probe should not run")

    monkeypatch.setattr(base_mirrors, "network_gfw_test", fail_network_probe)
    args = argparse.Namespace(
        auto_mirror=False,
        use_pypi_mirror=False,
        use_github_mirror=True,
        custom_github_mirror="https://github.example",
        source="huggingface",
    )

    auto_mirror.apply_auto_mirror(args)

    assert args.use_pypi_mirror is False
    assert args.use_github_mirror is True
    assert args.custom_github_mirror == "https://github.example"
    assert args.source == "huggingface"


def test_product_cli_auto_mirror_overrides_install_options(monkeypatch, tmp_path):
    parser = build_parser(comfyui_cli.register_comfyui)
    calls = []

    monkeypatch.setattr(base_mirrors, "network_gfw_test", lambda: False)
    monkeypatch.setattr(comfyui_cli, "install", lambda **kwargs: calls.append(kwargs))

    args = parser.parse_args(
        [
            "comfyui",
            "install",
            "--comfyui-path",
            str(tmp_path),
            "--no-pypi-mirror",
            "--no-github-mirror",
            "--custom-github-mirror",
            "https://mirror.example",
            "--model-resource",
            "huggingface",
        ]
    )
    args.func(args)

    assert calls[-1]["use_pypi_mirror"] is True
    assert calls[-1]["use_github_mirror"] is True
    assert calls[-1]["custom_github_mirror"] is None
    assert calls[-1]["model_download_resource_type"] == "modelscope"


def test_product_cli_auto_mirror_overrides_launch_options(monkeypatch, tmp_path):
    parser = build_parser(comfyui_cli.register_comfyui)
    calls = []

    monkeypatch.setattr(base_mirrors, "network_gfw_test", lambda: True)
    monkeypatch.setattr(comfyui_cli, "launch", lambda **kwargs: calls.append(kwargs))

    args = parser.parse_args(
        [
            "comfyui",
            "launch",
            "--comfyui-path",
            str(tmp_path),
            "--no-hf-mirror",
            "--custom-hf-mirror",
            "https://hf.example",
            "--no-github-mirror",
            "--custom-github-mirror",
            "https://github.example",
            "--no-pypi-mirror",
        ]
    )
    args.func(args)

    assert calls[-1]["use_hf_mirror"] is False
    assert calls[-1]["custom_hf_mirror"] is None
    assert calls[-1]["use_github_mirror"] is False
    assert calls[-1]["custom_github_mirror"] is None
    assert calls[-1]["use_pypi_mirror"] is False
