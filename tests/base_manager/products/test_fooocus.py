"""Fooocus 管理器测试"""

import os

import pytest

from sd_webui_all_in_one.base_manager import (
    fooocus_base,
)
from tests.base_manager.products.helpers import implementation_module, patch_common_install_deps


def test_fooocus_launch_skips_hf_mirror_arg_when_parser_does_not_support_it(monkeypatch, tmp_path):
    calls = []
    implementation = implementation_module(fooocus_base, "launch_fooocus")

    def fake_hf(**kwargs):
        env = kwargs["origin_env"].copy()
        env["HF_ENDPOINT"] = "https://hf.example"
        return env

    monkeypatch.setattr(implementation, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(implementation, "apply_hf_mirror", fake_hf)
    monkeypatch.setattr(implementation, "check_fooocus_hf_mirror_arg", lambda _path: False)
    monkeypatch.setattr(implementation, "get_pypi_mirror_config", lambda use_cn_mirror=False, origin_env=None: origin_env or {})
    monkeypatch.setattr(implementation, "get_cuda_malloc_var", lambda: None)
    monkeypatch.setattr(implementation, "apply_hotpatcher_launch_env", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(implementation, "launch_webui", lambda **kwargs: calls.append(kwargs))

    fooocus_base.launch_fooocus(tmp_path, launch_args=["--preset", "x"], use_hf_mirror=True)

    assert calls[0]["launch_args"] == ["--preset", "x"]
    assert calls[0]["custom_env"]["HF_ENDPOINT"] == "https://hf.example"


@pytest.mark.parametrize(
    "launch_args",
    [
        ["--preset", "x", "--hf-mirror", "https://custom.example"],
        ["--preset", "x", "--hf-mirror=https://custom.example"],
    ],
)
def test_fooocus_launch_does_not_duplicate_user_hf_mirror_arg(monkeypatch, tmp_path, launch_args):
    calls = []
    implementation = implementation_module(fooocus_base, "launch_fooocus")

    def fake_hf(**kwargs):
        env = kwargs["origin_env"].copy()
        env["HF_ENDPOINT"] = "https://hf.example"
        return env

    monkeypatch.setattr(implementation, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(implementation, "apply_hf_mirror", fake_hf)
    monkeypatch.setattr(
        implementation,
        "check_fooocus_hf_mirror_arg",
        lambda _path: (_ for _ in ()).throw(AssertionError("should not check parser")),
    )
    monkeypatch.setattr(implementation, "get_pypi_mirror_config", lambda use_cn_mirror=False, origin_env=None: origin_env or {})
    monkeypatch.setattr(implementation, "get_cuda_malloc_var", lambda: None)
    monkeypatch.setattr(implementation, "apply_hotpatcher_launch_env", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(implementation, "launch_webui", lambda **kwargs: calls.append(kwargs))

    fooocus_base.launch_fooocus(tmp_path, launch_args=launch_args, use_hf_mirror=True)

    assert calls[0]["launch_args"] == launch_args
    assert calls[0]["custom_env"]["HF_ENDPOINT"] == "https://hf.example"


def test_install_fooocus_orchestrates_branch_requirements_model_and_config(monkeypatch, tmp_path):
    calls = []
    implementation = implementation_module(fooocus_base, "install_fooocus")
    (tmp_path / "requirements_versions.txt").write_text("demo\n", encoding="utf-8")
    branch_info = {"name": "Demo Fooocus", "dtype": "fooocus_demo", "url": "https://github.com/example/fooocus", "branch": "demo", "use_submodule": False}
    monkeypatch.setattr(implementation, "FOOOCUS_BRANCH_LIST", ["fooocus_demo"])
    monkeypatch.setattr(implementation, "FOOOCUS_BRANCH_INFO_DICT", [branch_info])
    git_config_path = patch_common_install_deps(monkeypatch, implementation, calls, tmp_path)
    monkeypatch.setattr(implementation, "install_fooocus_config", lambda **kwargs: calls.append(("config", kwargs)))

    fooocus_base.install_fooocus(tmp_path, install_branch="fooocus_demo", use_uv=False, no_pre_download_model=False)

    assert os.environ["GIT_CONFIG_GLOBAL"] == git_config_path
    assert calls[0] == ("clone", {"repo": branch_info["url"], "path": tmp_path})
    assert calls[1] == ("switch", {"path": tmp_path, "branch": "demo", "new_url": branch_info["url"], "recurse_submodules": False})
    assert calls[2][0] == "pytorch"
    assert calls[3] == ("requirements", {"path": tmp_path / "requirements_versions.txt", "use_uv": False, "custom_env": {"PIP": "True", "GIT_CONFIG_GLOBAL": git_config_path}, "cwd": tmp_path})
    assert calls[4][0] == "model"
    assert calls[4][1]["dtype"] == "fooocus"
    assert calls[5] == ("config", {"fooocus_path": tmp_path, "download_resource_type": "modelscope"})

    with pytest.raises(ValueError):
        fooocus_base.install_fooocus(tmp_path, install_branch="missing")

    (tmp_path / "requirements_versions.txt").unlink()
    with pytest.raises(FileNotFoundError):
        fooocus_base.install_fooocus(tmp_path, install_branch="fooocus_demo")
