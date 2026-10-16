"""镜像源配置测试"""

import os
import subprocess

from sd_webui_all_in_one import mirror_manager
from sd_webui_all_in_one.pytorch_manager.types import (
    PYPI_INDEX_MIRROR_OFFICIAL,
    PYPI_INDEX_MIRROR_TENCENT,
)


def test_mirror_env_helpers_set_and_clear(monkeypatch):
    for key in [
        "PIP_INDEX_URL",
        "UV_DEFAULT_INDEX",
        "PIP_EXTRA_INDEX_URL",
        "UV_INDEX",
        "PIP_FIND_LINKS",
        "UV_FIND_LINKS",
        "HF_ENDPOINT",
    ]:
        monkeypatch.delenv(key, raising=False)

    mirror_manager.set_pypi_index_mirror("https://pypi.example/simple")
    mirror_manager.set_pypi_extra_index_mirror("https://extra.example/simple")
    mirror_manager.set_pypi_find_links_mirror(" https://wheel-a.example  https://wheel-b.example ")
    mirror_manager.set_huggingface_mirror("https://hf.example")

    assert os.environ["PIP_INDEX_URL"] == "https://pypi.example/simple"
    assert os.environ["UV_DEFAULT_INDEX"] == "https://pypi.example/simple"
    assert os.environ["PIP_EXTRA_INDEX_URL"] == "https://extra.example/simple"
    assert os.environ["UV_INDEX"] == "https://extra.example/simple"
    assert os.environ["PIP_FIND_LINKS"] == "https://wheel-a.example https://wheel-b.example"
    assert os.environ["UV_FIND_LINKS"] == "https://wheel-a.example,https://wheel-b.example"
    assert os.environ["HF_ENDPOINT"] == "https://hf.example"

    mirror_manager.set_pypi_index_mirror()
    mirror_manager.set_pypi_extra_index_mirror()
    mirror_manager.set_pypi_find_links_mirror()
    mirror_manager.set_huggingface_mirror()

    assert "PIP_INDEX_URL" not in os.environ
    assert "UV_DEFAULT_INDEX" not in os.environ
    assert "PIP_EXTRA_INDEX_URL" not in os.environ
    assert "UV_INDEX" not in os.environ
    assert "PIP_FIND_LINKS" not in os.environ
    assert "UV_FIND_LINKS" not in os.environ
    assert "HF_ENDPOINT" not in os.environ


def test_set_mirror_delegates_and_sets_git_config_env(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(mirror_manager, "set_pypi_index_mirror", lambda mirror=None: calls.append(("index", mirror)))
    monkeypatch.setattr(mirror_manager, "set_pypi_extra_index_mirror", lambda mirror=None: calls.append(("extra", mirror)))
    monkeypatch.setattr(mirror_manager, "set_pypi_find_links_mirror", lambda mirror=None: calls.append(("links", mirror)))
    monkeypatch.setattr(mirror_manager, "set_github_mirror", lambda mirror=None: calls.append(("github", mirror)) or (tmp_path / ".gitconfig"))
    monkeypatch.setattr(mirror_manager, "set_huggingface_mirror", lambda mirror=None: calls.append(("hf", mirror)))
    monkeypatch.delenv("GIT_CONFIG_GLOBAL", raising=False)

    mirror_manager.set_mirror(
        pypi_index_mirror="index-url",
        pypi_extra_index_mirror="extra-url",
        pypi_find_links_mirror="links-url",
        github_mirror=["gh"],
        huggingface_mirror="hf-url",
    )

    assert calls == [
        ("index", "index-url"),
        ("extra", "extra-url"),
        ("links", "links-url"),
        ("github", ["gh"]),
        ("hf", "hf-url"),
    ]
    assert os.environ["GIT_CONFIG_GLOBAL"] == (tmp_path / ".gitconfig").as_posix()


def test_set_github_mirror_writes_or_clears_config(monkeypatch, tmp_path):
    calls = []

    def fake_run_git(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(mirror_manager.git_warpper, "run_git", fake_run_git)
    config_path = tmp_path / ".gitconfig"

    result = mirror_manager.set_github_mirror("https://mirror.example/https://github.com", config_path=config_path)

    assert result == config_path
    assert calls == [
        (
            (
                "config",
                "--file",
                config_path.as_posix(),
                "url.https://mirror.example/https://github.com.insteadOf",
                "https://github.com",
            ),
            {},
        )
    ]

    config_path.write_text("old", encoding="utf-8")
    mirror_manager.set_github_mirror([], config_path=config_path)

    assert not config_path.exists()


def test_github_mirror_timeout_continues_to_next_mirror(monkeypatch):
    calls = []

    def fake_run_git(*args, **kwargs):
        calls.append((args, kwargs))
        if len(calls) == 1:
            raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    monkeypatch.setattr(mirror_manager.git_warpper, "run_git", fake_run_git)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/tmp/ignored-gitconfig")

    selected = mirror_manager.test_github_mirror(
        ["https://slow.example/github.com", "https://fast.example/github.com"],
        timeout=3.5,
    )

    assert selected == "https://fast.example/github.com"
    assert [call[0] for call in calls] == [
        ("ls-remote", "https://slow.example/github.com/licyk/empty"),
        ("ls-remote", "https://fast.example/github.com/licyk/empty"),
    ]
    for _, kwargs in calls:
        assert kwargs["live"] is False
        assert kwargs["shell"] is False
        assert kwargs["timeout"] == 3.5
        assert "GIT_CONFIG_GLOBAL" not in kwargs["custom_env"]


def test_github_mirror_returns_none_when_all_mirrors_timeout(monkeypatch):
    def fake_run_git(*args, **kwargs):
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    monkeypatch.setattr(mirror_manager.git_warpper, "run_git", fake_run_git)

    assert mirror_manager.test_github_mirror(["https://slow-a.example", "https://slow-b.example"], timeout=1.0) is None


def test_get_auto_pypi_mirror_config_selects_by_network(monkeypatch):
    monkeypatch.setattr(mirror_manager, "network_gfw_test", lambda: True)
    official = mirror_manager.get_auto_pypi_mirror_config({})
    assert official["PIP_INDEX_URL"] == PYPI_INDEX_MIRROR_OFFICIAL

    monkeypatch.setattr(mirror_manager, "network_gfw_test", lambda: False)
    cn = mirror_manager.get_auto_pypi_mirror_config({})
    assert cn["PIP_INDEX_URL"] == PYPI_INDEX_MIRROR_TENCENT
