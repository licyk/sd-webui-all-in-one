"""ComfyUI 禁用冲突组件选项在环境检查, CLI 与 Notebook 中的传递测试"""

import argparse

import pytest

from sd_webui_all_in_one.base_manager.comfyui_base import lifecycle
from sd_webui_all_in_one.cli_manager import comfyui_cli
from sd_webui_all_in_one.notebook_manager import comfyui_manager
from tests.env_check.comfyui_env_analyze.helpers import make_comfyui


# ============================================================================
# 参数传递
# ============================================================================
def test_check_comfyui_env_passes_disable_option(monkeypatch, tmp_path):
    comfyui = make_comfyui(tmp_path, "torch\n", {"outlier": "numpy<2\n"})
    captured = {}

    def fake_run_env_check_tasks(tasks, **_kwargs):
        captured.update({task.name: task.kwargs for task in tasks})

    monkeypatch.setattr(lifecycle, "run_env_check_tasks", fake_run_env_check_tasks)
    monkeypatch.setattr(lifecycle, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(lifecycle, "apply_git_config_global_to_process", lambda _env: None)

    lifecycle.check_comfyui_env(comfyui, disable_conflict_component=True)

    kwargs = captured[lifecycle.ComfyUIEnvCheckName.COMFYUI_CONFLICTS]
    assert kwargs["disable_conflict_component"] is True
    kwargs["disable_component_callback"]("outlier")
    assert (comfyui / "custom_nodes" / "outlier.disabled").is_dir()


@pytest.mark.parametrize("command", ["check-env", "launch"])
def test_cli_disable_conflict_flag(monkeypatch, tmp_path, command):
    parser = argparse.ArgumentParser(prog="sd-webui-all-in-one")
    comfyui_cli.register_comfyui(parser.add_subparsers(dest="command", required=True))
    calls: list[dict] = []
    target = "check_env" if command == "check-env" else "launch"
    monkeypatch.setattr(comfyui_cli, target, lambda **kwargs: calls.append(kwargs))

    for extra, expected in (([], False), (["--disable-conflict"], True)):
        args = parser.parse_args(["comfyui", command, "--comfyui-path", str(tmp_path), "--no-auto-mirror", *extra])
        args.func(args)
        assert calls[-1]["disable_conflict_component"] is expected


def test_notebook_check_env_passes_disable_option(monkeypatch, tmp_path):
    calls: list[dict] = []
    monkeypatch.setattr(comfyui_manager, "check_comfyui_env", lambda **kwargs: calls.append(kwargs))

    comfyui_manager.ComfyUIManager(tmp_path, "app").check_env(disable_conflict_component=True)

    assert calls[0]["disable_conflict_component"] is True
    assert calls[0]["install_conflict_component_requirement"] is True
