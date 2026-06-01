import sys
from pathlib import Path
from typing import Any, cast

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
    assert torch_pkg is not None
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


def test_install_pytorch_with_fallback_preserves_env_and_package_inputs(monkeypatch):
    calls = []
    torch_package = ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128"]
    xformers_package = ["xformers==0.0.32"]
    custom_env = {"PIP_INDEX_URL": "https://torch.example/simple", "KEEP": "1"}

    def fake_install_pytorch(**kwargs):
        calls.append(("install", kwargs))
        if len(calls) == 1:
            raise RuntimeError("first failed")

    def fake_get_auto_pypi_mirror_config(custom_env=None):
        calls.append(("mirror", custom_env))
        return {"AUTO": "1", **(custom_env or {})}

    monkeypatch.setattr(base_module, "install_pytorch", fake_install_pytorch)
    monkeypatch.setattr(base_module, "get_auto_pypi_mirror_config", fake_get_auto_pypi_mirror_config)

    base_module.install_pytorch_with_fallback(
        torch_package=torch_package,
        xformers_package=xformers_package,
        custom_env=custom_env,
        use_uv=False,
    )

    assert torch_package == ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128"]
    assert xformers_package == ["xformers==0.0.32"]
    assert calls[1] == (
        "install",
        {
            "torch_package": ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128", "--no-deps"],
            "xformers_package": ["xformers==0.0.32", "--no-deps"],
            "custom_env": custom_env,
            "use_uv": False,
        },
    )
    assert calls[2] == ("mirror", custom_env)
    assert calls[3] == (
        "install",
        {
            "torch_package": ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128"],
            "xformers_package": ["xformers==0.0.32"],
            "custom_env": {"AUTO": "1", **custom_env},
            "use_uv": False,
        },
    )
    assert len(calls) == 4


def test_install_pytorch_with_fallback_merges_mirror_env_after_existing_fallback_fails(monkeypatch):
    install_calls = []
    mirror_calls = []
    torch_package = ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128"]
    xformers_package = ["xformers==0.0.32"]
    custom_env = {
        "PIP_INDEX_URL": "https://custom-index.example/simple",
        "PIP_EXTRA_INDEX_URL": "https://custom-extra.example/simple https://shared-extra.example/simple",
        "UV_INDEX": "https://custom-uv-extra.example/simple https://shared-extra.example/simple",
        "PIP_FIND_LINKS": "https://custom-wheels.example https://shared-wheels.example",
        "UV_FIND_LINKS": "https://custom-uv-wheels.example,https://shared-wheels.example",
        "KEEP": "1",
    }

    def fake_install_pytorch(**kwargs):
        install_calls.append(kwargs)
        if len(install_calls) in [1, 3]:
            raise RuntimeError("install failed")

    def fake_get_auto_pypi_mirror_config(custom_env=None):
        mirror_calls.append(custom_env)
        return {
            **(custom_env or {}),
            "PIP_INDEX_URL": "https://auto-index.example/simple",
            "UV_DEFAULT_INDEX": "https://auto-index.example/simple",
            "PIP_EXTRA_INDEX_URL": "https://shared-extra.example/simple https://auto-extra.example/simple",
            "UV_INDEX": "https://auto-uv-extra.example/simple https://custom-extra.example/simple",
            "PIP_FIND_LINKS": "https://shared-wheels.example https://auto-wheels.example",
            "UV_FIND_LINKS": "https://auto-uv-wheels.example,https://custom-uv-wheels.example",
        }

    monkeypatch.setattr(base_module, "install_pytorch", fake_install_pytorch)
    monkeypatch.setattr(base_module, "get_auto_pypi_mirror_config", fake_get_auto_pypi_mirror_config)

    base_module.install_pytorch_with_fallback(
        torch_package=torch_package,
        xformers_package=xformers_package,
        custom_env=custom_env,
        use_uv=False,
    )

    assert torch_package == ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128"]
    assert xformers_package == ["xformers==0.0.32"]
    assert len(mirror_calls) == 1
    assert mirror_calls[0] is custom_env
    assert len(install_calls) == 4
    assert install_calls[1]["torch_package"] == ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128", "--no-deps"]
    assert install_calls[1]["xformers_package"] == ["xformers==0.0.32", "--no-deps"]
    assert install_calls[3]["torch_package"] == ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128"]
    assert install_calls[3]["xformers_package"] == ["xformers==0.0.32"]
    assert "--no-deps" not in install_calls[3]["torch_package"]
    assert "--no-deps" not in install_calls[3]["xformers_package"]

    merged_env = install_calls[3]["custom_env"]
    assert merged_env["KEEP"] == "1"
    assert merged_env["PIP_INDEX_URL"] == "https://custom-index.example/simple"
    assert merged_env["UV_DEFAULT_INDEX"] == "https://custom-index.example/simple"
    assert (
        merged_env["PIP_EXTRA_INDEX_URL"]
        == "https://custom-extra.example/simple https://shared-extra.example/simple https://custom-uv-extra.example/simple https://auto-extra.example/simple https://auto-uv-extra.example/simple"
    )
    assert (
        merged_env["UV_INDEX"]
        == "https://custom-extra.example/simple https://shared-extra.example/simple https://custom-uv-extra.example/simple https://auto-extra.example/simple https://auto-uv-extra.example/simple"
    )
    assert merged_env["PIP_FIND_LINKS"] == "https://custom-wheels.example https://shared-wheels.example https://custom-uv-wheels.example https://auto-wheels.example https://auto-uv-wheels.example"
    assert merged_env["UV_FIND_LINKS"] == "https://custom-wheels.example,https://shared-wheels.example,https://custom-uv-wheels.example,https://auto-wheels.example,https://auto-uv-wheels.example"


def test_install_pytorch_with_fallback_uses_first_custom_extra_index_when_no_index(monkeypatch):
    install_calls = []
    custom_env = {
        "PIP_EXTRA_INDEX_URL": "https://custom-extra-a.example/simple https://custom-extra-b.example/simple",
        "UV_INDEX": "https://custom-extra-c.example/simple",
    }

    def fake_install_pytorch(**kwargs):
        install_calls.append(kwargs)
        if len(install_calls) in [1, 3]:
            raise RuntimeError("install failed")

    def fake_get_auto_pypi_mirror_config(custom_env=None):
        return {
            **(custom_env or {}),
            "PIP_EXTRA_INDEX_URL": "https://auto-extra.example/simple",
            "PIP_FIND_LINKS": "https://auto-wheels.example",
        }

    monkeypatch.setattr(base_module, "install_pytorch", fake_install_pytorch)
    monkeypatch.setattr(base_module, "get_auto_pypi_mirror_config", fake_get_auto_pypi_mirror_config)

    base_module.install_pytorch_with_fallback(
        torch_package=["torch==2.8.0+cu128"],
        xformers_package=["xformers==0.0.32"],
        custom_env=custom_env,
        use_uv=True,
    )

    merged_env = install_calls[3]["custom_env"]
    assert merged_env["PIP_INDEX_URL"] == "https://custom-extra-a.example/simple"
    assert merged_env["UV_DEFAULT_INDEX"] == "https://custom-extra-a.example/simple"


def test_install_webui_model_from_library_interactive_direct_search(monkeypatch, tmp_path):
    models = [
        {
            "name": "alpha",
            "filename": "alpha.safetensors",
            "url": {"modelscope": "https://modelscope.example/alpha"},
            "dtype": "checkpoint",
            "supported_webui": ["sd_webui"],
            "save_dir": {"sd_webui": "models/Stable-diffusion"},
        },
        {
            "name": "beta",
            "filename": "beta.safetensors",
            "url": {"modelscope": "https://modelscope.example/beta"},
            "dtype": "checkpoint",
            "supported_webui": ["sd_webui"],
            "save_dir": {"sd_webui": "models/Stable-diffusion"},
        },
    ]
    calls = []
    inputs = iter(["search beta", "2"])

    monkeypatch.setattr(base_module, "export_model_list", lambda dtype: models)
    monkeypatch.setattr(base_module, "display_model_table", lambda model_list: calls.append(("display", model_list)))
    monkeypatch.setattr(base_module, "print_divider", lambda char: calls.append(("divider", char)))
    monkeypatch.setattr(base_module, "search_models_from_library", lambda query, models: calls.append(("search", query, models)) or [2])
    monkeypatch.setattr(base_module, "download_model", lambda **kwargs: calls.append(("download", kwargs)) or [tmp_path / "beta.safetensors"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    result = base_module.install_webui_model_from_library(
        webui_path=tmp_path,
        dtype="sd_webui",
        interactive_mode=True,
        downloader="urllib",
    )

    assert result == [tmp_path / "beta.safetensors"]
    assert ("search", "beta", models) in calls
    assert calls[-1] == (
        "download",
        {
            "dtype": "sd_webui",
            "base_path": tmp_path,
            "download_resource_type": "modelscope",
            "model_index": [2],
            "downloader": "urllib",
        },
    )


def test_install_webui_model_from_library_interactive_search_prompt(monkeypatch, tmp_path):
    models = [
        {
            "name": "alpha",
            "filename": "alpha.safetensors",
            "url": {"modelscope": "https://modelscope.example/alpha"},
            "dtype": "checkpoint",
            "supported_webui": ["sd_webui"],
            "save_dir": {"sd_webui": "models/Stable-diffusion"},
        }
    ]
    calls = []
    inputs = iter(["search", "alpha", "1"])

    monkeypatch.setattr(base_module, "export_model_list", lambda dtype: models)
    monkeypatch.setattr(base_module, "display_model_table", lambda model_list: calls.append(("display", model_list)))
    monkeypatch.setattr(base_module, "print_divider", lambda char: calls.append(("divider", char)))
    monkeypatch.setattr(base_module, "search_models_from_library", lambda query, models: calls.append(("search", query, models)) or [1])
    monkeypatch.setattr(base_module, "download_model", lambda **kwargs: calls.append(("download", kwargs)) or [tmp_path / "alpha.safetensors"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))

    result = base_module.install_webui_model_from_library(
        webui_path=tmp_path,
        dtype="sd_webui",
        interactive_mode=True,
    )

    assert result == [tmp_path / "alpha.safetensors"]
    assert ("search", "alpha", models) in calls


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
        "https://bad.example/api/models?limit=1",
        "https://good.example/api/models?limit=1",
    ]

    with pytest.raises(ValueError):
        base_module.apply_hf_mirror(use_hf_mirror=True, custom_hf_mirror=cast(Any, {"bad": "type"}), origin_env={})
