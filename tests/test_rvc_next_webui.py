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


def test_check_env_runs_qwen_style_tasks(monkeypatch, tmp_path):
    _use_temp_git_config(monkeypatch, tmp_path)
    (tmp_path / "requirements.txt").write_text("rvc-next\n", encoding="utf-8")
    captured = {}
    monkeypatch.setattr(lifecycle, "apply_git_config_global_to_process", lambda env: None)
    monkeypatch.setattr(lifecycle, "run_env_check_tasks", lambda tasks, **kwargs: captured.update(tasks=tasks, **kwargs))

    rvc_next_webui_base.check_rvc_next_webui_env(tmp_path, use_uv=False)

    tasks = captured["tasks"]
    assert [task.name for task in tasks] == list(lifecycle.RvcNextEnvCheckName)
    assert tasks[0].func is lifecycle.py_dependency_checker
    assert tasks[0].kwargs["requirement_path"] == tmp_path / "requirements.txt"
    assert tasks[0].kwargs["use_uv"] is False


def test_hf_mirror_maps_to_rvc_next_download_settings():
    assert runtime.apply_rvc_next_hf_mirror({}) == {}
    assert runtime.apply_rvc_next_hf_mirror({"HF_ENDPOINT": "https://hf.example"}) == {
        "HF_ENDPOINT": "https://hf.example",
        "RVC_NEXT_DOWNLOADS__SOURCE": "custom",
        "RVC_NEXT_DOWNLOADS__ENDPOINT": "https://hf.example",
    }
    user_env = {"HF_ENDPOINT": "https://hf.example", "RVC_NEXT_DOWNLOADS__SOURCE": "huggingface"}
    assert runtime.apply_rvc_next_hf_mirror(user_env) == user_env


def test_prepare_launch_applies_mirror_and_keeps_launch_args(monkeypatch, tmp_path):
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
    assert info.launch_args == ["--no-browser"]
    assert info.custom_env["RVC_NEXT_DOWNLOADS__SOURCE"] == "custom"
    assert info.custom_env["RVC_NEXT_DOWNLOADS__ENDPOINT"] == "https://hf.example"

    info = rvc_next_webui_base.prepare_rvc_next_webui_launch(tmp_path, use_hf_mirror=False, use_cuda_malloc=False)
    assert info.launch_args == []
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
