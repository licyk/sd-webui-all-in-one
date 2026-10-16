"""WebUI 基础管理器仓库, Git 配置与镜像地址测试"""

from typing import Any, cast

import pytest

from sd_webui_all_in_one.base_manager import base as base_module
from sd_webui_all_in_one.base_manager.base import apply_github_raw_file_mirror
from sd_webui_all_in_one.base_manager.base import repositories as base_repositories


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/AUTOMATIC1111/stable-diffusion-webui.git", "stable-diffusion-webui"),
        ("https://github.com/AUTOMATIC1111/stable-diffusion-webui/", "stable-diffusion-webui"),
        ("git@github.com:AUTOMATIC1111/stable-diffusion-webui.git", "stable-diffusion-webui"),
        ("ssh://git@github.com/AUTOMATIC1111/stable-diffusion-webui.git", "stable-diffusion-webui"),
    ],
)
def test_get_repo_name_from_url(url, expected):
    assert base_module.get_repo_name_from_url(url) == expected


def test_clone_repo_rejects_file_and_skips_non_empty_directory(monkeypatch, tmp_path):
    target_file = tmp_path / "target"
    target_file.write_text("file", encoding="utf-8")

    with pytest.raises(FileExistsError):
        base_module.clone_repo("https://github.com/example/repo", target_file)

    target_dir = tmp_path / "repo"
    target_dir.mkdir()
    (target_dir / "existing.txt").write_text("existing", encoding="utf-8")
    monkeypatch.setattr(base_repositories.git_warpper, "clone", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should skip clone")))

    base_module.clone_repo("https://github.com/example/repo", target_dir)


def test_clone_repo_clones_into_empty_directory(monkeypatch, tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    calls = []

    def fake_remove_files(path):
        calls.append(("remove", path))
        path.rmdir()

    def fake_clone(repo, path):
        calls.append(("clone", repo, path))
        cloned = path / "repo"
        cloned.mkdir()
        (cloned / "file.txt").write_text("content", encoding="utf-8")
        return cloned

    def fake_copy_files(src, dst):
        calls.append(("copy", src, dst))
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "file.txt").write_text((src / "file.txt").read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setattr(base_repositories, "remove_files", fake_remove_files)
    monkeypatch.setattr(base_repositories.git_warpper, "clone", fake_clone)
    monkeypatch.setattr(base_repositories, "copy_files", fake_copy_files)

    base_module.clone_repo("https://github.com/example/repo", target)

    assert calls[0] == ("remove", target)
    assert calls[1][0] == "clone"
    assert calls[2][0] == "copy"
    assert (target / "file.txt").read_text(encoding="utf-8") == "content"


def test_apply_github_raw_file_mirror_selects_first_working_list_entry(monkeypatch):
    class FakeResponse:
        def __init__(self, code):
            self.code = code

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def getcode(self):
            return self.code

    calls = []

    def fake_urlopen(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise OSError("down")
        return FakeResponse(200)

    monkeypatch.setattr(base_repositories.urllib.request, "urlopen", fake_urlopen)

    result = base_module.apply_github_raw_file_mirror(
        "owner/repo/main/index.json",
        custom_github_mirror=["https://bad.example/github.com", "https://good.example/https://github.com"],
    )

    assert result == "https://good.example/https://raw.githubusercontent.com/owner/repo/main/index.json"
    assert len(calls) == 2


def test_apply_git_base_config_uses_env_config_and_does_not_mutate_origin(monkeypatch, tmp_path):
    calls = []
    origin = {"GIT_CONFIG_GLOBAL": (tmp_path / "nested" / ".gitconfig").as_posix(), "KEEP": "1"}

    monkeypatch.setattr(base_repositories, "set_github_mirror", lambda mirror, config_path: calls.append(("mirror", mirror, config_path)))
    monkeypatch.setattr(base_repositories, "set_git_base_config", lambda config_path: calls.append(("base", config_path)))

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


def test_apply_git_config_global_to_process(monkeypatch, tmp_path):
    monkeypatch.delenv("GIT_CONFIG_GLOBAL", raising=False)
    config_path = (tmp_path / ".gitconfig").as_posix()

    result = base_module.apply_git_config_global_to_process({"GIT_CONFIG_GLOBAL": config_path})

    assert result == config_path
    assert base_repositories.os.environ["GIT_CONFIG_GLOBAL"] == config_path

    result = base_module.apply_git_config_global_to_process({"KEEP": "1"})

    assert result is None
    assert base_repositories.os.environ["GIT_CONFIG_GLOBAL"] == config_path


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

    monkeypatch.setattr(base_repositories.urllib.request, "urlopen", fake_urlopen)
    result = base_module.apply_hf_mirror(use_hf_mirror=True, custom_hf_mirror=["https://bad.example", "https://good.example"], origin_env={"KEEP": "1"})
    assert result["HF_ENDPOINT"] == "https://good.example"
    assert opened == [
        "https://bad.example/api/models?limit=1",
        "https://good.example/api/models?limit=1",
    ]

    with pytest.raises(ValueError):
        base_module.apply_hf_mirror(use_hf_mirror=True, custom_hf_mirror=cast(Any, {"bad": "type"}), origin_env={})


def test_apply_github_raw_file_mirror_with_direct_json_url():
    url = apply_github_raw_file_mirror(
        raw_file_path="owner/repo/main/index.json",
        custom_github_mirror="https://example.com/index.json",
    )

    assert url == "https://example.com/index.json"


def test_apply_github_raw_file_mirror_with_prefix_url():
    url = apply_github_raw_file_mirror(
        raw_file_path="owner/repo/main/index.json",
        custom_github_mirror="https://mirror.example.com/github.com",
    )

    assert url == "https://mirror.example.com/raw.githubusercontent.com/owner/repo/main/index.json"
