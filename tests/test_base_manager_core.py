import os

import pytest

from sd_webui_all_in_one.base_manager import base as base_module
from sd_webui_all_in_one.custom_exceptions import WebUiRuntimeError


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
    monkeypatch.setattr(base_module.git_warpper, "clone", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should skip clone")))

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

    monkeypatch.setattr(base_module, "remove_files", fake_remove_files)
    monkeypatch.setattr(base_module.git_warpper, "clone", fake_clone)
    monkeypatch.setattr(base_module, "copy_files", fake_copy_files)

    base_module.clone_repo("https://github.com/example/repo", target)

    assert calls[0] == ("remove", target)
    assert calls[1][0] == "clone"
    assert calls[2][0] == "copy"
    assert (target / "file.txt").read_text(encoding="utf-8") == "content"


def test_launch_webui_builds_command_env_and_wraps_runtime_errors(monkeypatch, tmp_path):
    webui = tmp_path / "webui"
    webui.mkdir()
    (webui / "launch.py").write_text("print('ok')", encoding="utf-8")
    captured = {}

    def fake_run_cmd(command, custom_env=None, cwd=None):
        captured["command"] = command
        captured["custom_env"] = custom_env
        captured["cwd"] = cwd

    monkeypatch.setattr(base_module, "run_cmd", fake_run_cmd)
    base_module.launch_webui(webui, "launch.py", launch_args=["--api"], custom_env={"PYTHONPATH": "existing"})

    assert captured["command"][-2:] == [(webui / "launch.py").as_posix(), "--api"]
    assert captured["cwd"] == webui
    assert captured["custom_env"]["PYTHONPATH"].split(os.pathsep)[:2] == [webui.as_posix(), "existing"]

    def fail_run_cmd(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(base_module, "run_cmd", fail_run_cmd)

    with pytest.raises(WebUiRuntimeError) as exc:
        base_module.launch_webui(webui, "launch.py", webui_name="Demo")

    assert "Demo" in str(exc.value)
    assert "boom" in str(exc.value)


def test_pre_download_model_for_webui_skips_existing_or_missing_and_downloads_empty(monkeypatch, tmp_path):
    calls = []

    def fake_download_model(**kwargs):
        calls.append(kwargs)
        return [kwargs["base_path"] / "models/model.safetensors"]

    monkeypatch.setattr(base_module, "download_model", fake_download_model)
    webui = tmp_path / "webui"
    webui.mkdir()

    assert base_module.pre_download_model_for_webui("sd_webui", tmp_path / "missing", webui, "alpha", "modelscope") is None

    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "model.safetensors").write_text("model", encoding="utf-8")
    assert base_module.pre_download_model_for_webui("sd_webui", existing, webui, "alpha", "modelscope") is None

    empty = tmp_path / "empty"
    empty.mkdir()
    result = base_module.pre_download_model_for_webui("sd_webui", empty, webui, ["alpha", "beta"], "huggingface")

    assert result == webui / "models/model.safetensors"
    assert calls == [
        {
            "dtype": "sd_webui",
            "base_path": webui,
            "download_resource_type": "huggingface",
            "model_name": ["alpha", "beta"],
        }
    ]


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

    monkeypatch.setattr(base_module.urllib.request, "urlopen", fake_urlopen)

    result = base_module.apply_github_raw_file_mirror(
        "owner/repo/main/index.json",
        custom_github_mirror=["https://bad.example/github.com", "https://good.example/https://github.com"],
    )

    assert result == "https://good.example/https://raw.githubusercontent.com/owner/repo/main/index.json"
    assert len(calls) == 2


def test_install_pytorch_for_webui_only_installs_missing_packages(monkeypatch):
    calls = []

    def fake_version(name):
        if name == "torch":
            return "2.0.0"
        raise base_module.importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(base_module.importlib.metadata, "version", fake_version)
    monkeypatch.setattr(base_module, "install_pytorch", lambda **kwargs: calls.append(kwargs))

    base_module.install_pytorch_for_webui("torch==2.0.0", "xformers==0.0.1", {"PIP_INDEX_URL": "x"}, use_uv=False)

    assert calls == [
        {
            "torch_package": "torch==2.0.0",
            "xformers_package": "xformers==0.0.1",
            "custom_env": {"PIP_INDEX_URL": "x"},
            "use_uv": False,
        }
    ]

    calls.clear()
    monkeypatch.setattr(base_module.importlib.metadata, "version", lambda _name: "installed")
    base_module.install_pytorch_for_webui("torch", "xformers")
    assert calls == []
