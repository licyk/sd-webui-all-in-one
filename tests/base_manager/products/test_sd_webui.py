"""Stable Diffusion WebUI 管理器测试"""

import json
import os
from typing import Any, cast

import pytest

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager import (
    sd_webui_base,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError
from tests.base_manager.products.helpers import fail_old_git_info_reader, fake_repository_state, implementation_module, use_temp_git_config


def test_install_sd_webui_orchestrates_branch_extensions_repositories_and_models(monkeypatch, tmp_path):
    calls = []
    git_config_path = use_temp_git_config(monkeypatch, tmp_path)
    implementation = implementation_module(sd_webui_base, "install_sd_webui")
    (tmp_path / "requirements_versions.txt").write_text("demo\n", encoding="utf-8")
    branch_info = {
        "name": "Demo Branch",
        "dtype": "sd_webui_dev",
        "url": "https://github.com/example/webui",
        "branch": "dev",
        "use_submodule": True,
    }

    monkeypatch.setattr(implementation, "SD_WEBUI_BRANCH_INFO_DICT", [branch_info])
    monkeypatch.setattr(
        implementation,
        "SD_WEBUI_EXTENSION_INFO_DICT",
        [{"name": "Ext", "url": "https://github.com/example/ext", "save_dir": "extensions/ext", "supported_branch": ["sd_webui_dev"]}],
    )
    monkeypatch.setattr(
        implementation,
        "SD_WEBUI_REPOSITORY_INFO_DICT",
        [{"name": "Repo", "url": "https://github.com/example/repo", "save_dir": "repositories/repo", "supported_branch": ["sd_webui_dev"]}],
    )
    monkeypatch.setattr(implementation, "prepare_pytorch_install_info", lambda **kwargs: ("torch", "xformers", {"TORCH": "env"}))
    monkeypatch.setattr(implementation, "get_pypi_mirror_config", lambda use_cn_mirror=True: {"PIP": str(use_cn_mirror)})
    monkeypatch.setattr(implementation, "apply_git_base_config_and_github_mirror", lambda **kwargs: {**kwargs["origin_env"], "GIT_CONFIG_GLOBAL": git_config_path})
    monkeypatch.setattr(implementation, "clone_repo", lambda **kwargs: calls.append(("clone", kwargs)))
    monkeypatch.setattr(git_warpper, "switch_branch", lambda **kwargs: calls.append(("switch", kwargs)))
    monkeypatch.setattr(implementation, "install_pytorch_for_webui", lambda **kwargs: calls.append(("pytorch", kwargs)))
    monkeypatch.setattr(implementation, "install_clip_package", lambda **kwargs: calls.append(("clip", kwargs)))
    monkeypatch.setattr(implementation, "install_requirements", lambda **kwargs: calls.append(("requirements", kwargs)))
    monkeypatch.setattr(implementation, "pre_download_model_for_webui", lambda **kwargs: calls.append(("model", kwargs)))
    monkeypatch.setattr(implementation, "install_sd_webui_config", lambda path: calls.append(("config", path)))

    sd_webui_base.install_sd_webui(tmp_path, install_branch="sd_webui_dev", use_uv=False, no_pre_download_model=False)

    assert os.environ["GIT_CONFIG_GLOBAL"] == git_config_path
    assert calls[0] == ("clone", {"repo": "https://github.com/example/webui", "path": tmp_path})
    assert calls[1] == (
        "switch",
        {"path": tmp_path, "branch": "dev", "new_url": "https://github.com/example/webui", "recurse_submodules": True},
    )
    assert calls[2] == ("clone", {"repo": "https://github.com/example/repo", "path": tmp_path / "repositories/repo"})
    assert calls[3] == ("clone", {"repo": "https://github.com/example/ext", "path": tmp_path / "extensions/ext"})
    assert calls[4][0] == "pytorch"
    assert calls[6][0] == "requirements"
    assert [call[0] for call in calls[-3:]] == ["model", "model", "config"]

    with pytest.raises(ValueError):
        sd_webui_base.install_sd_webui(tmp_path, install_branch=cast(Any, "unknown"))


def test_check_sd_webui_env_aggregates_task_failures(monkeypatch, tmp_path):
    implementation = implementation_module(sd_webui_base, "check_sd_webui_env")
    git_config_path = use_temp_git_config(monkeypatch, tmp_path)
    req = tmp_path / "requirements.txt"
    req.write_text("demo\n", encoding="utf-8")
    calls = []

    def ok_task(**kwargs):
        calls.append((ok_task.__name__, kwargs))

    def bad_task(**kwargs):
        calls.append((bad_task.__name__, kwargs))
        raise RuntimeError("task bad")

    monkeypatch.setattr(implementation, "apply_git_base_config_and_github_mirror", lambda **kwargs: {**kwargs["origin_env"], "GIT_CONFIG_GLOBAL": git_config_path})
    monkeypatch.setattr(implementation, "get_pypi_mirror_config", lambda use_cn_mirror, origin_env=None: {"PIP": str(use_cn_mirror), **(origin_env or {})})
    monkeypatch.setattr(implementation, "fix_stable_diffusion_invaild_repo_url", ok_task)
    monkeypatch.setattr(implementation, "fix_forge_neo_alert", ok_task)
    monkeypatch.setattr(implementation, "py_dependency_checker", bad_task)
    monkeypatch.setattr(implementation, "install_extension_requirements", ok_task)
    monkeypatch.setattr(implementation, "fix_torch_libomp", ok_task)
    monkeypatch.setattr(implementation, "check_torch_version", ok_task)
    monkeypatch.setattr(implementation, "check_onnxruntime_gpu", ok_task)

    with pytest.raises(AggregateError) as exc:
        sd_webui_base.check_sd_webui_env(tmp_path, use_uv=False, use_pypi_mirror=True)

    assert len(exc.value.exceptions) == 1
    assert calls[2][0] == "bad_task"
    assert calls[2][1]["requirement_path"] == req
    assert calls[2][1]["name"] == "Stable Diffusion WebUI"
    assert calls[2][1]["use_uv"] is False
    assert calls[2][1]["custom_env"]["PIP"] == "True"
    assert calls[2][1]["custom_env"]["GIT_CONFIG_GLOBAL"] == git_config_path


def test_sd_webui_extension_lifecycle_and_model_uninstall(monkeypatch, tmp_path):
    extension_implementation = implementation_module(sd_webui_base, "list_sd_webui_extensions")
    model_implementation = implementation_module(sd_webui_base, "uninstall_sd_webui_model")
    extensions = tmp_path / "extensions"
    models = tmp_path / "models" / "Stable-diffusion"
    for folder in [extensions / "enabled" / ".git", extensions / "disabled" / ".git", models]:
        folder.mkdir(parents=True)
    (extensions / "plain").mkdir()
    (tmp_path / "config.json").write_text('{"disabled_extensions": ["disabled"]}', encoding="utf-8")
    (models / "demo.safetensors").write_text("model", encoding="utf-8")
    (models / "other.txt").write_text("other", encoding="utf-8")

    monkeypatch.setattr(extension_implementation, "inspect_repository", fake_repository_state)
    monkeypatch.setattr(git_warpper, "get_current_branch_remote_url", fail_old_git_info_reader)
    monkeypatch.setattr(git_warpper, "get_current_commit", fail_old_git_info_reader)
    monkeypatch.setattr(git_warpper, "get_current_branch", fail_old_git_info_reader)

    infos = sorted(sd_webui_base.list_sd_webui_extensions(tmp_path), key=lambda item: item["name"])
    assert [(item["name"], item["status"]) for item in infos] == [("disabled", False), ("enabled", True), ("plain", True)]
    assert infos[1]["url"] == "https://example.test/enabled"
    assert infos[1]["commit"] == "enabled-full-commit"
    assert infos[1]["branch"] == "main"
    assert infos[2]["url"] is None

    sd_webui_base.set_sd_webui_extensions_status(tmp_path, "disabled", True)
    sd_webui_base.set_sd_webui_extensions_status(tmp_path, "enabled", False)
    config = (tmp_path / "config.json").read_text(encoding="utf-8")
    assert '"disabled"' not in config
    assert '"enabled"' in config

    removed = []
    monkeypatch.setattr(extension_implementation, "remove_files", lambda path: removed.append(path))
    monkeypatch.setattr(model_implementation, "remove_files", lambda path: removed.append(path))
    sd_webui_base.uninstall_sd_webui_extension(tmp_path, "enabled")
    sd_webui_base.uninstall_sd_webui_model(tmp_path, "demo", model_type="Stable-diffusion")
    assert removed == [extensions / "enabled", models / "demo.safetensors"]

    with pytest.raises(FileNotFoundError):
        sd_webui_base.uninstall_sd_webui_model(tmp_path, "missing", model_type="Stable-diffusion")


def test_install_and_update_sd_webui_extensions_aggregate(monkeypatch, tmp_path):
    use_temp_git_config(monkeypatch, tmp_path)
    implementation = implementation_module(sd_webui_base, "install_sd_webui_extension")
    (tmp_path / "extensions" / "bad" / ".git").mkdir(parents=True)
    (tmp_path / "extensions" / "ok" / ".git").mkdir(parents=True)
    monkeypatch.setattr(implementation, "list_sd_webui_extensions", lambda _path: [{"name": "existing"}])
    monkeypatch.setattr(implementation, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])

    cloned = []

    def fake_clone(repo, path):
        cloned.append((repo, path))
        if "fail" in repo:
            raise RuntimeError("clone bad")

    monkeypatch.setattr(implementation, "clone_repo", fake_clone)
    with pytest.raises(AggregateError):
        sd_webui_base.install_sd_webui_extension(
            tmp_path,
            ["https://github.com/example/existing", "https://github.com/example/new", "https://github.com/example/fail"],
        )

    assert cloned == [
        ("https://github.com/example/new", tmp_path / "extensions" / "new"),
        ("https://github.com/example/fail", tmp_path / "extensions" / "fail"),
    ]

    updates = []

    def fake_update(path, live=True, fetch=True):
        updates.append(path.name)
        if path.name == "bad":
            raise RuntimeError("bad")

    monkeypatch.setattr(git_warpper, "update", fake_update)
    with pytest.raises(AggregateError):
        sd_webui_base.update_sd_webui_extensions(tmp_path)
    assert sorted(updates) == ["bad", "ok"]


def test_set_sd_webui_extension_status_without_config_file(tmp_path):
    from sd_webui_all_in_one.base_manager.sd_webui_base.extensions.service import set_sd_webui_extensions_status

    (tmp_path / "extensions" / "ext").mkdir(parents=True)

    set_sd_webui_extensions_status(tmp_path, "ext", False)

    assert json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))["disabled_extensions"] == ["ext"]
