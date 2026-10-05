import argparse
import os

import pytest

from sd_webui_all_in_one.base_manager import rvc_next_webui_base
from sd_webui_all_in_one.base_manager.rvc_next_webui_base import lifecycle, runtime
from sd_webui_all_in_one.cli_manager import rvc_next_webui_cli


def _parser():
    parser = argparse.ArgumentParser(prog="sd-webui-all-in-one")
    subparsers = parser.add_subparsers(dest="command", required=True)
    rvc_next_webui_cli.register_rvc_next_webui(subparsers)
    return parser


def _use_temp_git_config(monkeypatch, tmp_path):
    config_path = tmp_path / ".gitconfig"
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", config_path.as_posix())
    return config_path.as_posix()


def test_install_rvc_next_webui_orchestrates_without_xformers(monkeypatch, tmp_path):
    calls = []
    git_config_path = _use_temp_git_config(monkeypatch, tmp_path)
    (tmp_path / "requirements.txt").write_text("rvc-next\n", encoding="utf-8")

    monkeypatch.setattr(lifecycle, "prepare_pytorch_install_info", lambda **kwargs: ("torch==2.9.0+cu128", "xformers", {"TORCH": "env"}))
    monkeypatch.setattr(lifecycle, "get_pypi_mirror_config", lambda use_cn_mirror=True: {"PIP": str(use_cn_mirror)})
    monkeypatch.setattr(
        lifecycle,
        "apply_git_base_config_and_github_mirror",
        lambda **kwargs: {**kwargs["origin_env"], "GIT_CONFIG_GLOBAL": git_config_path},
    )
    monkeypatch.setattr(lifecycle, "clone_repo", lambda **kwargs: calls.append(("clone", kwargs)))
    monkeypatch.setattr(lifecycle, "install_pytorch_for_webui", lambda **kwargs: calls.append(("pytorch", kwargs)))
    monkeypatch.setattr(lifecycle, "install_requirements", lambda **kwargs: calls.append(("requirements", kwargs)))

    rvc_next_webui_base.install_rvc_next_webui(
        tmp_path,
        use_pypi_mirror=False,
        use_uv=False,
        use_github_mirror=True,
        custom_github_mirror="https://mirror.example",
    )

    assert os.environ["GIT_CONFIG_GLOBAL"] == git_config_path
    assert calls[0] == ("clone", {"repo": rvc_next_webui_base.RVC_NEXT_WEBUI_REPO, "path": tmp_path})
    assert calls[1] == (
        "pytorch",
        {"pytorch_package": "torch==2.9.0+cu128", "xformers_package": None, "custom_env": {"TORCH": "env"}, "use_uv": False},
    )
    assert calls[2][0] == "requirements"
    assert calls[2][1]["path"] == tmp_path / "requirements.txt"
    assert calls[2][1]["cwd"] == tmp_path
    assert len(calls) == 3


def test_install_rvc_next_webui_rejects_unsupported_pytorch_before_cloning(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(lifecycle, "prepare_pytorch_install_info", lambda **kwargs: ("torch==2.4.1+cu118", None, {}))
    monkeypatch.setattr(lifecycle, "clone_repo", lambda **kwargs: calls.append(kwargs))

    with pytest.raises(ValueError, match="2.7.1"):
        rvc_next_webui_base.install_rvc_next_webui(tmp_path)

    assert calls == []


@pytest.mark.parametrize(
    ("pytorch_package", "pytorch_mirror_type"),
    [
        ("torch==2.4.1+cu118 torchvision==0.19.1+cu118", None),
        ("torch==2.3.1 torchvision==0.18.1 torch-directml==0.2.3.dev240715", None),
        ("torch==2.9.0+cpu", "directml"),
    ],
)
def test_check_rvc_next_pytorch_package_rejects_unsupported(pytorch_package, pytorch_mirror_type):
    with pytest.raises(ValueError):
        lifecycle.check_rvc_next_pytorch_package(pytorch_package, pytorch_mirror_type)


@pytest.mark.parametrize("pytorch_package", ["torch==2.7.1+cu128", "torch==2.9.0+rocm6.4 torchvision==0.24.0+rocm6.4", "torch torchvision", None])
def test_check_rvc_next_pytorch_package_accepts_supported(pytorch_package):
    lifecycle.check_rvc_next_pytorch_package(pytorch_package)


def _patch_dependency_state(monkeypatch, *, torch_ok=True, requirements_ok=True, missing=None):
    installs = []
    monkeypatch.setattr(lifecycle, "is_package_installed", lambda requirement: torch_ok)
    monkeypatch.setattr(lifecycle, "validate_requirements", lambda path: requirements_ok)
    monkeypatch.setattr(lifecycle, "get_missing_package_metadata_dependencies", lambda name: list(missing or []))
    monkeypatch.setattr(lifecycle, "install_requirements", lambda **kwargs: installs.append(kwargs))
    return installs


def test_dependency_check_refuses_to_install_without_supported_pytorch(monkeypatch, tmp_path):
    requirement_path = tmp_path / "requirements.txt"
    requirement_path.write_text("rvc-next\n", encoding="utf-8")
    installs = _patch_dependency_state(monkeypatch, torch_ok=False, requirements_ok=False)

    with pytest.raises(RuntimeError, match="PyTorch"):
        lifecycle.check_rvc_next_webui_dependencies(requirement_path)

    assert installs == []


@pytest.mark.parametrize(
    ("requirements_ok", "missing", "should_install"),
    [
        (True, [], False),
        (True, ["torchaudio>=2.7"], False),
        (True, ["librosa>=0.10.2,<2"], True),
        (False, [], True),
    ],
)
def test_dependency_check_installs_requirements_for_missing_rvc_next_dependencies(monkeypatch, tmp_path, requirements_ok, missing, should_install):
    requirement_path = tmp_path / "requirements.txt"
    requirement_path.write_text("rvc-next\n", encoding="utf-8")
    installs = _patch_dependency_state(monkeypatch, requirements_ok=requirements_ok, missing=missing)

    lifecycle.check_rvc_next_webui_dependencies(requirement_path, use_uv=False, custom_env={"PIP": "1"})

    if should_install:
        assert installs == [{"path": requirement_path, "use_uv": False, "cwd": tmp_path, "custom_env": {"PIP": "1"}}]
    else:
        assert installs == []


@pytest.mark.parametrize(
    ("launch_args", "expected"),
    [
        (None, ["--skip-check", "--disable-proxy"]),
        (["--port", "7870"], ["--port", "7870", "--skip-check", "--disable-proxy"]),
        (["--disable-proxy", "--skip-check"], ["--disable-proxy", "--skip-check"]),
    ],
)
def test_managed_launch_args_are_added_once(launch_args, expected):
    assert runtime.apply_rvc_next_managed_launch_args(launch_args) == expected


def test_hf_mirror_maps_to_rvc_next_download_settings():
    assert runtime.apply_rvc_next_hf_mirror({}) == {}
    assert runtime.apply_rvc_next_hf_mirror({"HF_ENDPOINT": "https://hf.example"}) == {
        "HF_ENDPOINT": "https://hf.example",
        "RVC_NEXT_DOWNLOADS__SOURCE": "custom",
        "RVC_NEXT_DOWNLOADS__ENDPOINT": "https://hf.example",
    }
    user_env = {"HF_ENDPOINT": "https://hf.example", "RVC_NEXT_DOWNLOADS__SOURCE": "huggingface"}
    assert runtime.apply_rvc_next_hf_mirror(user_env) == user_env


def test_prepare_launch_applies_mirror_and_managed_args(monkeypatch, tmp_path):
    _use_temp_git_config(monkeypatch, tmp_path)
    monkeypatch.setattr(runtime, "apply_git_config_global_to_process", lambda env: None)
    monkeypatch.setattr(runtime, "apply_hf_mirror", lambda **kwargs: {**kwargs["origin_env"], "HF_ENDPOINT": kwargs["custom_hf_mirror"]})
    monkeypatch.delenv("RVC_NEXT_DOWNLOADS__SOURCE", raising=False)
    monkeypatch.delenv("RVC_NEXT_DOWNLOADS__ENDPOINT", raising=False)

    info = rvc_next_webui_base.prepare_rvc_next_webui_launch(
        tmp_path,
        launch_args=["--no-browser"],
        use_hf_mirror=True,
        custom_hf_mirror="https://hf.example",
        use_cuda_malloc=False,
    )

    assert info.launch_script == "launch.py"
    assert info.launch_args == ["--no-browser", "--skip-check", "--disable-proxy"]
    assert info.custom_env["RVC_NEXT_DOWNLOADS__SOURCE"] == "custom"
    assert info.custom_env["RVC_NEXT_DOWNLOADS__ENDPOINT"] == "https://hf.example"

    info = rvc_next_webui_base.prepare_rvc_next_webui_launch(tmp_path, use_hf_mirror=False, use_cuda_malloc=False)
    assert "RVC_NEXT_DOWNLOADS__SOURCE" not in info.custom_env


def test_cli_install_forwards_pytorch_options_without_model_or_xformers_options(monkeypatch, tmp_path):
    parser = _parser()
    calls = []
    monkeypatch.setattr(rvc_next_webui_cli, "install", lambda **kwargs: calls.append(kwargs))

    args = parser.parse_args(
        [
            "rvc-next-webui",
            "install",
            "--rvc-next-webui-path",
            str(tmp_path),
            "--no-auto-mirror",
            "--pytorch-mirror-type",
            "cu128",
        ]
    )
    args.func(args)

    assert calls[-1]["rvc_next_webui_path"] == tmp_path
    assert calls[-1]["pytorch_mirror_type"] == "cu128"
    assert "custom_xformers_package" not in calls[-1]
    for option in ("--custom-xformers-package", "--no-pre-download-model", "--model-resource"):
        with pytest.raises(SystemExit):
            parser.parse_args(["rvc-next-webui", "install", option, "x"])
