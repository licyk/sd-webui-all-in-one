import os
from pathlib import Path

import pytest

from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.base_manager import comfyui_base
from sd_webui_all_in_one.base_manager import fooocus_base
from sd_webui_all_in_one.base_manager import qwen_tts_webui_base


@pytest.mark.parametrize(
    ("module", "function_name", "target_file", "resource_type", "expected_source_attr"),
    [
        (fooocus_base, "install_fooocus_config", "presets/sd_webui_all_in_one.json", "huggingface", "FOOOCUS_PRESET_HF_PATH"),
        (fooocus_base, "install_fooocus_config", "presets/sd_webui_all_in_one.json", "modelscope", "FOOOCUS_PRESET_MS_PATH"),
        (qwen_tts_webui_base, "install_qwen_tts_webui_config", "config.json", "huggingface", "QWEN_TTS_WEBUI_PRESET_HF_PATH"),
        (qwen_tts_webui_base, "install_qwen_tts_webui_config", "config.json", "modelscope", "QWEN_TTS_WEBUI_PRESET_MS_PATH"),
    ],
)
def test_product_config_installers_copy_expected_preset(monkeypatch, tmp_path, module, function_name, target_file, resource_type, expected_source_attr):
    calls = []
    monkeypatch.setattr(module, "copy_files", lambda src, dst: calls.append((src, dst)))

    getattr(module, function_name)(tmp_path, resource_type)

    assert calls[0] == (getattr(module, expected_source_attr), tmp_path / target_file)


def test_product_config_installers_skip_existing_and_reject_unknown(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(fooocus_base, "copy_files", lambda src, dst: calls.append((src, dst)))
    (tmp_path / "presets").mkdir()
    (tmp_path / "presets" / "sd_webui_all_in_one.json").write_text("existing", encoding="utf-8")

    fooocus_base.install_fooocus_config(tmp_path, "modelscope")
    assert calls == [(fooocus_base.FOOOCUS_TRANSLATE_ZH_PATH, tmp_path / "language" / "zh.json")]

    (tmp_path / "language").mkdir()
    (tmp_path / "language" / "zh.json").write_text("{}", encoding="utf-8")
    (tmp_path / "presets" / "sd_webui_all_in_one.json").unlink()
    with pytest.raises(ValueError):
        fooocus_base.install_fooocus_config(tmp_path, "unknown")

    with pytest.raises(ValueError):
        qwen_tts_webui_base.install_qwen_tts_webui_config(tmp_path, "unknown")


def test_comfyui_config_installs_once(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(comfyui_base, "copy_files", lambda src, dst: calls.append((src, dst)))

    comfyui_base.install_comfyui_config(tmp_path)
    assert calls == [(comfyui_base.COMFYUI_CONFIG_PATH, tmp_path / "user" / "default" / "comfy.settings.json")]

    (tmp_path / "user" / "default").mkdir(parents=True)
    (tmp_path / "user" / "default" / "comfy.settings.json").write_text("{}", encoding="utf-8")
    calls.clear()
    comfyui_base.install_comfyui_config(tmp_path)
    assert calls == []


def test_install_qwen_tts_webui_orchestrates_without_external_side_effects(monkeypatch, tmp_path):
    calls = []
    (tmp_path / "requirements.txt").write_text("demo\n", encoding="utf-8")

    monkeypatch.setattr(qwen_tts_webui_base, "prepare_pytorch_install_info", lambda **kwargs: ("torch", "xformers", {"TORCH": "env"}))
    monkeypatch.setattr(qwen_tts_webui_base, "get_pypi_mirror_config", lambda use_cn_mirror=True: {"PIP": str(use_cn_mirror)})
    monkeypatch.setattr(
        qwen_tts_webui_base,
        "apply_git_base_config_and_github_mirror",
        lambda **kwargs: {"GIT_CONFIG_GLOBAL": "/tmp/gitconfig", **kwargs["origin_env"]},
    )
    monkeypatch.setattr(qwen_tts_webui_base, "clone_repo", lambda **kwargs: calls.append(("clone", kwargs)))
    monkeypatch.setattr(qwen_tts_webui_base, "install_pytorch_for_webui", lambda **kwargs: calls.append(("pytorch", kwargs)))
    monkeypatch.setattr(qwen_tts_webui_base, "install_requirements", lambda **kwargs: calls.append(("requirements", kwargs)))
    monkeypatch.setattr(qwen_tts_webui_base, "install_qwen_tts_webui_config", lambda **kwargs: calls.append(("config", kwargs)))

    qwen_tts_webui_base.install_qwen_tts_webui(
        tmp_path,
        use_pypi_mirror=False,
        use_uv=False,
        use_github_mirror=True,
        custom_github_mirror="https://mirror.example",
        model_download_resource_type="huggingface",
    )

    assert os.environ["GIT_CONFIG_GLOBAL"] == "/tmp/gitconfig"
    assert calls[0] == ("clone", {"repo": qwen_tts_webui_base.QWEN_TTS_WEBUI_REPO, "path": tmp_path})
    assert calls[1] == (
        "pytorch",
        {"pytorch_package": "torch", "xformers_package": "xformers", "custom_env": {"TORCH": "env"}, "use_uv": False},
    )
    assert calls[2][0] == "requirements"
    assert calls[2][1]["path"] == tmp_path / "requirements.txt"
    assert calls[2][1]["cwd"] == tmp_path
    assert calls[3] == ("config", {"qwen_tts_webui_path": tmp_path, "download_resource_type": "huggingface"})


def test_install_comfyui_orchestrates_extensions_models_and_missing_requirements(monkeypatch, tmp_path):
    calls = []
    (tmp_path / "requirements.txt").write_text("demo\n", encoding="utf-8")

    monkeypatch.setattr(comfyui_base, "COMFYUI_CUSTOM_NODES_INFO_DICT", [{"name": "Node", "url": "https://github.com/example/node", "save_dir": "custom_nodes/node"}])
    monkeypatch.setattr(comfyui_base, "prepare_pytorch_install_info", lambda **kwargs: ("torch", None, {"TORCH": "env"}))
    monkeypatch.setattr(comfyui_base, "get_pypi_mirror_config", lambda use_cn_mirror=True: {"PIP": str(use_cn_mirror)})
    monkeypatch.setattr(comfyui_base, "apply_git_base_config_and_github_mirror", lambda **kwargs: {"GIT_CONFIG_GLOBAL": "gitconfig", **kwargs["origin_env"]})
    monkeypatch.setattr(comfyui_base, "clone_repo", lambda **kwargs: calls.append(("clone", kwargs)))
    monkeypatch.setattr(comfyui_base, "install_pytorch_for_webui", lambda **kwargs: calls.append(("pytorch", kwargs)))
    monkeypatch.setattr(comfyui_base, "install_requirements", lambda **kwargs: calls.append(("requirements", kwargs)))
    monkeypatch.setattr(comfyui_base, "pre_download_model_for_webui", lambda **kwargs: calls.append(("model", kwargs)))
    monkeypatch.setattr(comfyui_base, "install_comfyui_config", lambda path: calls.append(("config", path)))

    comfyui_base.install_comfyui(tmp_path, no_pre_download_extension=False, no_pre_download_model=False, use_uv=False)

    assert calls[0] == ("clone", {"repo": comfyui_base.COMFYUI_REPO_URL, "path": tmp_path})
    assert calls[1] == ("clone", {"repo": "https://github.com/example/node", "path": tmp_path / "custom_nodes/node"})
    assert calls[3][0] == "requirements"
    assert calls[4][0] == "model"
    assert calls[4][1]["dtype"] == "comfyui"
    assert calls[-1] == ("config", tmp_path)

    with pytest.raises(FileNotFoundError):
        comfyui_base.install_comfyui(tmp_path / "missing", no_pre_download_extension=True)


def test_comfyui_custom_node_lifecycle(monkeypatch, tmp_path):
    custom_nodes = tmp_path / "custom_nodes"
    custom_nodes.mkdir()
    (custom_nodes / "installed").mkdir()
    (custom_nodes / "disabled.disabled").mkdir()
    (custom_nodes / "file.py").write_text("pass", encoding="utf-8")

    monkeypatch.setattr(comfyui_base.git_warpper, "get_current_branch_remote_url", lambda path: f"https://example.test/{path.name}")
    monkeypatch.setattr(comfyui_base.git_warpper, "get_current_commit", lambda _path: "abc123")
    monkeypatch.setattr(comfyui_base.git_warpper, "get_current_branch", lambda _path: "main")

    nodes = sorted(comfyui_base.list_comfyui_custom_nodes(tmp_path), key=lambda item: item["name"])
    assert [node["name"] for node in nodes] == ["disabled.disabled", "installed"]
    assert nodes[0]["status"] is False

    moves = []
    monkeypatch.setattr(comfyui_base, "move_files", lambda src, dst: moves.append((src, dst)))
    comfyui_base.set_comfyui_custom_node_status(tmp_path, "disabled", True)
    comfyui_base.set_comfyui_custom_node_status(tmp_path, "installed", False)
    assert moves == [
        (custom_nodes / "disabled.disabled", custom_nodes / "disabled"),
        (custom_nodes / "installed", custom_nodes / "installed.disabled"),
    ]

    removed = []
    monkeypatch.setattr(comfyui_base, "remove_files", lambda path: removed.append(path))
    comfyui_base.uninstall_comfyui_custom_node(tmp_path, "installed")
    assert removed == [custom_nodes / "installed"]

    with pytest.raises(FileNotFoundError):
        comfyui_base.set_comfyui_custom_node_status(tmp_path, "missing", True)


def test_comfyui_custom_node_install_and_update_aggregate_errors(monkeypatch, tmp_path):
    custom_nodes = tmp_path / "custom_nodes"
    (custom_nodes / "ok" / ".git").mkdir(parents=True)
    (custom_nodes / "bad" / ".git").mkdir(parents=True)

    monkeypatch.setattr(comfyui_base, "list_comfyui_custom_nodes", lambda _path: [{"name": "existing"}])
    monkeypatch.setattr(comfyui_base, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])

    cloned = []

    def fake_clone(repo, path):
        cloned.append((repo, path))
        if "fail" in repo:
            raise RuntimeError("clone bad")

    monkeypatch.setattr(comfyui_base, "clone_repo", fake_clone)

    with pytest.raises(AggregateError) as exc:
        comfyui_base.install_comfyui_custom_node(tmp_path, ["https://github.com/example/existing", "https://github.com/example/new", "https://github.com/example/fail"])

    assert cloned == [
        ("https://github.com/example/new", custom_nodes / "new"),
        ("https://github.com/example/fail", custom_nodes / "fail"),
    ]
    assert len(exc.value.exceptions) == 1

    updates = []

    def fake_update(path):
        updates.append(path.name)
        if path.name == "bad":
            raise RuntimeError("update bad")

    monkeypatch.setattr(comfyui_base.git_warpper, "update", fake_update)
    with pytest.raises(AggregateError):
        comfyui_base.update_comfyui_custom_nodes(tmp_path)
    assert updates == ["ok", "bad"]


def test_launch_helpers_build_env_and_delegate(monkeypatch, tmp_path):
    calls = []

    def fake_git_config(**kwargs):
        return {"GIT_CONFIG_GLOBAL": "gitconfig", **kwargs["origin_env"]}

    def fake_hf(**kwargs):
        env = kwargs["origin_env"].copy()
        env["HF_ENDPOINT"] = "https://hf.example"
        return env

    for module in (comfyui_base, fooocus_base, qwen_tts_webui_base):
        monkeypatch.setattr(module, "apply_git_base_config_and_github_mirror", fake_git_config)
        monkeypatch.setattr(module, "apply_hf_mirror", fake_hf)
        monkeypatch.setattr(module, "get_pypi_mirror_config", lambda use_cn_mirror=False, origin_env=None: {"PIP": "1", **(origin_env or {})})
        monkeypatch.setattr(module, "get_cuda_malloc_var", lambda: "backend:cudaMallocAsync")
        monkeypatch.setattr(module, "apply_pytorch_alloc_conf", lambda config, origin_env=None: {"ALLOC": config, **(origin_env or {})})
        monkeypatch.setattr(module, "apply_hotpatcher_launch_env", lambda **kwargs: {"HOTPATCH": str(kwargs["enabled"]), **kwargs["origin_env"]})
        monkeypatch.setattr(module, "launch_webui", lambda **kwargs: calls.append((module.__name__, kwargs)))

    monkeypatch.setattr(fooocus_base.git_warpper, "get_current_branch_remote_url", lambda _path: "https://github.com/lllyasviel/Fooocus")

    comfyui_base.launch_comfyui(tmp_path / "comfy", launch_args=["--listen"], use_hf_mirror=True, use_cuda_malloc=True, enable_hotpatcher=True)
    fooocus_base.launch_fooocus(tmp_path / "fooocus", launch_args=["--preset", "x"], use_hf_mirror=True, use_cuda_malloc=True)
    qwen_tts_webui_base.launch_qwen_tts_webui(tmp_path / "qwen", launch_args=[], use_hf_mirror=True, use_cuda_malloc=True)

    assert calls[0][1]["launch_script"] == "main.py"
    assert calls[0][1]["webui_name"] == "ComfyUI"
    assert calls[0][1]["custom_env"]["HOTPATCH"] == "True"
    assert calls[1][1]["launch_args"] == ["--preset", "x", "--hf-mirror", "https://hf.example"]
    assert calls[2][1]["launch_script"] == "launch.py"
