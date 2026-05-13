import os
import sys
from pathlib import Path

import pytest

from sd_webui_all_in_one.base_manager import base as base_module


def test_prepare_pytorch_install_info_auto_and_custom_packages(monkeypatch):
    calls = []
    latest = {
        "dtype": "cu128",
        "torch_ver": "torch==2.8.0+cu128 torchvision==0.23.0+cu128",
        "xformers_ver": "xformers==0.0.32",
        "index_mirror": {"mirror": "index-mirror", "official": "index-official"},
        "extra_index_mirror": {"mirror": "extra-mirror", "official": "extra-official"},
        "find_links": {"mirror": "links-mirror", "official": "links-official"},
    }

    monkeypatch.setattr(base_module, "auto_detect_avaliable_pytorch_type", lambda: "cu128")
    monkeypatch.setattr(base_module, "find_latest_pytorch_info", lambda dtype: calls.append(("latest", dtype)) or latest)
    monkeypatch.setattr(base_module, "get_pytorch_mirror", lambda dtype, use_cn_mirror=False: calls.append(("mirror", dtype, use_cn_mirror)) or (f"{dtype}-url", "extra_index_url"))

    torch_pkg, xformers_pkg, env = base_module.prepare_pytorch_install_info(use_cn_mirror=True)
    assert (torch_pkg, xformers_pkg) == (latest["torch_ver"], latest["xformers_ver"])
    assert calls == [("latest", "cu128"), ("mirror", "cu128", True)]
    assert env["PIP_INDEX_URL"] == "index-mirror"
    assert env["PIP_EXTRA_INDEX_URL"].splitlines()[-1] == "cu128-url"
    assert env["PIP_FIND_LINKS"] == "links-mirror"

    calls.clear()
    monkeypatch.setattr(base_module, "auto_detect_pytorch_device_category", lambda: "cuda")
    monkeypatch.setattr(base_module, "get_pytorch_mirror_type", lambda torch_ver, device_type: calls.append(("type", torch_ver, device_type)) or "cu124")
    torch_pkg, xformers_pkg, env = base_module.prepare_pytorch_install_info(
        custom_pytorch_package="torch==2.4.1 torchvision==0.19.1",
        custom_xformers_package="xformers==0.0.28",
        use_cn_mirror=False,
    )
    assert torch_pkg == "torch==2.4.1 torchvision==0.19.1"
    assert xformers_pkg == "xformers==0.0.28"
    assert calls == [("type", "2.4.1", "cuda"), ("mirror", "cu124", False)]
    assert env["PIP_EXTRA_INDEX_URL"] == "cu124-url"

    calls.clear()
    torch_pkg, _xformers_pkg, env = base_module.prepare_pytorch_install_info(
        custom_pytorch_package="torch==2.6.0+cu126 torchvision==0.21.0+cu126",
        use_cn_mirror=True,
    )
    assert torch_pkg.startswith("torch==2.6.0+cu126")
    assert calls == [("mirror", "cu126", True)]
    assert env["PIP_EXTRA_INDEX_URL"] == "cu126-url"


def test_reinstall_pytorch_list_install_and_interactive_auto(monkeypatch):
    info = {
        "torch_ver": "torch==2.8.0",
        "xformers_ver": "xformers==0.0.32",
        "index_mirror": {"mirror": "index-mirror", "official": "index-official"},
        "extra_index_mirror": {"mirror": "extra-mirror", "official": "extra-official"},
        "find_links": {"mirror": "links-mirror", "official": "links-official"},
    }
    calls = []
    monkeypatch.setattr(base_module, "export_pytorch_list", lambda: [info])
    monkeypatch.setattr(base_module, "display_pytorch_config", lambda data: calls.append(("display", data)))
    monkeypatch.setattr(base_module, "print_divider", lambda char: calls.append(("divider", char)))
    monkeypatch.setattr(base_module, "query_pytorch_info_from_library", lambda pytorch_name=None, pytorch_index=None: calls.append(("query", pytorch_name, pytorch_index)) or info)
    monkeypatch.setattr(base_module, "install_pytorch", lambda **kwargs: calls.append(("install", kwargs)))
    monkeypatch.setattr(base_module, "run_cmd", lambda command: calls.append(("run", command)))

    base_module.reinstall_pytorch(list_only=True)
    assert calls[:3] == [("divider", "="), ("display", [info]), ("divider", "=")]

    calls.clear()
    base_module.reinstall_pytorch(pytorch_name="Torch CUDA", use_pypi_mirror=False, use_uv=False)
    assert calls[0] == ("query", "Torch CUDA", None)
    assert calls[1][0] == "install"
    assert calls[1][1]["torch_package"] == "torch==2.8.0"
    assert calls[1][1]["custom_env"]["PIP_INDEX_URL"] == "index-official"
    assert calls[1][1]["use_uv"] is False

    calls.clear()
    inputs = iter(["auto", "y"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
    monkeypatch.setattr(base_module.importlib.metadata, "version", lambda _name: "installed")
    monkeypatch.setattr(base_module, "prepare_pytorch_install_info", lambda use_cn_mirror=True: ("torch-auto", "xformers-auto", {"AUTO": str(use_cn_mirror)}))
    base_module.reinstall_pytorch(interactive_mode=True, use_pypi_mirror=True, use_uv=True)

    assert ("run", [Path(sys.executable).as_posix(), "-m", "pip", "uninstall", "torch", "torchvision", "torchaudio", "xformers", "-y"]) in calls
    assert calls[-1] == (
        "install",
        {"torch_package": "torch-auto", "xformers_package": "xformers-auto", "custom_env": {"AUTO": "True"}, "use_uv": True},
    )


def test_apply_git_base_config_uses_env_config_and_does_not_mutate_origin(monkeypatch, tmp_path):
    calls = []
    origin = {"GIT_CONFIG_GLOBAL": (tmp_path / "nested" / ".gitconfig").as_posix(), "KEEP": "1"}

    monkeypatch.setattr(base_module, "set_github_mirror", lambda mirror, config_path: calls.append(("mirror", mirror, config_path)))
    monkeypatch.setattr(base_module, "set_git_base_config", lambda config_path: calls.append(("base", config_path)))

    result = base_module.apply_git_base_config_and_github_mirror(
        use_github_mirror=True,
        custom_github_mirror=["https://mirror.example/github.com"],
        origin_env=origin,
    )

    assert origin == {"GIT_CONFIG_GLOBAL": (tmp_path / "nested" / ".gitconfig").as_posix(), "KEEP": "1"}
    assert result["GIT_CONFIG_GLOBAL"] == origin["GIT_CONFIG_GLOBAL"]
    assert result["KEEP"] == "1"
    assert calls == [
        ("mirror", ["https://mirror.example/github.com"], tmp_path / "nested" / ".gitconfig"),
        ("base", tmp_path / "nested" / ".gitconfig"),
    ]

    calls.clear()
    result = base_module.apply_git_base_config_and_github_mirror(use_github_mirror=False, origin_env={"KEEP": "2"})
    assert result["GIT_CONFIG_GLOBAL"].endswith(".gitconfig")
    assert calls[0][0] == "mirror"
    assert calls[0][1] is None


def test_apply_hf_mirror_string_list_disabled_and_invalid(monkeypatch):
    origin = {"HF_ENDPOINT": "old", "KEEP": "1"}

    result = base_module.apply_hf_mirror(use_hf_mirror=False, origin_env=origin)
    assert result == origin
    assert result is not origin

    result = base_module.apply_hf_mirror(use_hf_mirror=True, custom_hf_mirror="https://hf.example", origin_env=origin)
    assert result["HF_ENDPOINT"] == "https://hf.example"
    assert origin["HF_ENDPOINT"] == "old"

    class FakeResponse:
        def __init__(self, code):
            self.code = code

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def getcode(self):
            return self.code

    opened = []

    def fake_urlopen(request, timeout):
        opened.append(request.full_url)
        if len(opened) == 1:
            raise OSError("down")
        return FakeResponse(200)

    monkeypatch.setattr(base_module.urllib.request, "urlopen", fake_urlopen)
    result = base_module.apply_hf_mirror(use_hf_mirror=True, custom_hf_mirror=["https://bad.example", "https://good.example"], origin_env={"KEEP": "1"})
    assert result["HF_ENDPOINT"] == "https://good.example"
    assert opened == [
        "https://bad.example/licyk/sd-model/resolve/main/README.md",
        "https://good.example/licyk/sd-model/resolve/main/README.md",
    ]

    with pytest.raises(ValueError):
        base_module.apply_hf_mirror(use_hf_mirror=True, custom_hf_mirror={"bad": "type"}, origin_env={})
