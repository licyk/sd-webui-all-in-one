"""WebUI 管理器测试辅助工具"""

import sys
from pathlib import Path

from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryState


def implementation_module(module, function_name):
    return sys.modules[getattr(module, function_name).__module__]


def use_temp_git_config(monkeypatch, tmp_path):
    config_path = tmp_path / ".gitconfig"
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", config_path.as_posix())
    return config_path.as_posix()


def fake_repository_state(path: Path, details: bool = True) -> RepositoryState:
    is_git_repo = (path / ".git").exists()
    return RepositoryState(
        path=path,
        is_git_repo=is_git_repo,
        name=path.name,
        url=f"https://example.test/{path.name}" if is_git_repo else None,
        branch="main" if is_git_repo else None,
        commit=f"{path.name}-full-commit" if is_git_repo else None,
    )


def fail_old_git_info_reader(*_args):
    raise AssertionError("extension lists should use inspect_repository()")


def patch_common_install_deps(monkeypatch, module, calls, tmp_path):
    git_config_path = (tmp_path / ".gitconfig").as_posix()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", git_config_path)
    monkeypatch.setattr(module, "prepare_pytorch_install_info", lambda **kwargs: ("torch", "xformers", {"TORCH": "env"}))
    monkeypatch.setattr(module, "get_pypi_mirror_config", lambda use_cn_mirror=True, origin_env=None: {"PIP": str(use_cn_mirror), **(origin_env or {})})
    monkeypatch.setattr(module, "apply_git_base_config_and_github_mirror", lambda **kwargs: {**kwargs["origin_env"], "GIT_CONFIG_GLOBAL": git_config_path})
    monkeypatch.setattr(module, "clone_repo", lambda **kwargs: calls.append(("clone", kwargs)))
    monkeypatch.setattr(module.git_warpper, "switch_branch", lambda **kwargs: calls.append(("switch", kwargs)))
    monkeypatch.setattr(module.git_warpper, "update_submodule", lambda path: calls.append(("submodule", path)))
    monkeypatch.setattr(module, "install_pytorch_for_webui", lambda **kwargs: calls.append(("pytorch", kwargs)))
    monkeypatch.setattr(module, "install_requirements", lambda **kwargs: calls.append(("requirements", kwargs)))
    monkeypatch.setattr(module, "pre_download_model_for_webui", lambda **kwargs: calls.append(("model", kwargs)))
    return git_config_path
