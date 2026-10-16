"""Stable Diffusion WebUI 无效仓库地址修复测试"""

import importlib

import pytest

fix_repo = importlib.import_module("sd_webui_all_in_one.env_check.fix_sd_webui_invaild_repo.fixer")


def test_fix_stable_diffusion_invalid_repo_url(monkeypatch, tmp_path):
    stable_repo = tmp_path / "repositories" / "stable-diffusion-stability-ai"
    stable_repo.mkdir(parents=True)
    calls = []
    env = {"GIT_CONFIG_GLOBAL": "/tmp/global", "KEEP": "1"}
    original_env = env.copy()

    monkeypatch.setattr(fix_repo.git_warpper, "is_git_repo", lambda path: False)
    fix_repo.fix_stable_diffusion_invaild_repo_url(tmp_path, custom_env=env)
    assert calls == []
    assert env == original_env

    monkeypatch.setattr(fix_repo.git_warpper, "is_git_repo", lambda path: path == stable_repo)

    def fake_run_git(*args, path=None, custom_env=None, live=True):
        calls.append((args, path, custom_env, live))
        assert "GIT_CONFIG_GLOBAL" not in custom_env
        if args == ("remote", "get-url", "origin"):
            return "https://github.com/Stability-AI/stablediffusion.git"
        return ""

    monkeypatch.setattr(fix_repo.git_warpper, "run_git", fake_run_git)
    fix_repo.fix_stable_diffusion_invaild_repo_url(tmp_path, custom_env=env)
    assert env == original_env

    assert calls[0][:2] == (("remote", "get-url", "origin"), stable_repo)
    assert calls[1][:2] == (("remote", "set-url", "origin", "https://github.com/licyk/stablediffusion"), stable_repo)

    calls.clear()
    monkeypatch.setattr(
        fix_repo.git_warpper,
        "run_git",
        lambda *args, path=None, custom_env=None, live=True: calls.append((args, path)) or "https://github.com/licyk/stablediffusion",
    )
    fix_repo.fix_stable_diffusion_invaild_repo_url(tmp_path, custom_env=env)
    assert calls == [(("remote", "get-url", "origin"), stable_repo)]
    assert env == original_env

    monkeypatch.setattr(fix_repo.git_warpper, "run_git", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("git bad")))
    with pytest.raises(RuntimeError, match="无效的组件仓库源"):
        fix_repo.fix_stable_diffusion_invaild_repo_url(tmp_path, custom_env=env)
    assert env == original_env


def test_fix_stable_diffusion_invalid_repo_url_adds_missing_origin(monkeypatch, tmp_path):
    stable_repo = tmp_path / "repositories" / "stable-diffusion-stability-ai"
    stable_repo.mkdir(parents=True)
    env = {"GIT_CONFIG_GLOBAL": "/tmp/global", "KEEP": "1"}
    original_env = env.copy()
    calls = []

    monkeypatch.setattr(fix_repo.git_warpper, "is_git_repo", lambda path: path == stable_repo)

    def fake_run_git(*args, path=None, custom_env=None, live=True):
        calls.append((args, path, custom_env, live))
        assert "GIT_CONFIG_GLOBAL" not in custom_env
        if args == ("remote", "get-url", "origin"):
            raise RuntimeError("No such remote 'origin'")
        if args == ("remote",):
            return "upstream\n"
        return ""

    monkeypatch.setattr(fix_repo.git_warpper, "run_git", fake_run_git)
    fix_repo.fix_stable_diffusion_invaild_repo_url(tmp_path, custom_env=env)

    assert calls[0][:2] == (("remote", "get-url", "origin"), stable_repo)
    assert calls[1][:2] == (("remote",), stable_repo)
    assert calls[2][:2] == (("remote", "add", "origin", "https://github.com/licyk/stablediffusion"), stable_repo)
    assert env == original_env
