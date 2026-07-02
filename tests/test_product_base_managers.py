import os
from pathlib import Path
from typing import Any, cast

import pytest

from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.base_manager import comfyui_base
from sd_webui_all_in_one.base_manager import fooocus_base
from sd_webui_all_in_one.base_manager import invokeai_base
from sd_webui_all_in_one.base_manager import qwen_tts_webui_base
from sd_webui_all_in_one.base_manager import sd_webui_base
from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryState
from sd_webui_all_in_one.base_manager.version_manager import ManagedExtension


def _fake_repository_state(path: Path) -> RepositoryState:
    is_git_repo = (path / ".git").exists()
    return RepositoryState(
        path=path,
        is_git_repo=is_git_repo,
        name=path.name,
        url=f"https://example.test/{path.name}" if is_git_repo else None,
        branch="main" if is_git_repo else None,
        commit=f"{path.name}-full-commit" if is_git_repo else None,
    )


def _fail_old_git_info_reader(*_args):
    raise AssertionError("extension lists should use inspect_repository()")


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
        fooocus_base.install_fooocus_config(tmp_path, cast(Any, "unknown"))

    with pytest.raises(ValueError):
        qwen_tts_webui_base.install_qwen_tts_webui_config(tmp_path, cast(Any, "unknown"))


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
    (custom_nodes / "installed" / ".git").mkdir(parents=True)
    (custom_nodes / "disabled.disabled").mkdir()
    (custom_nodes / ".disabled" / "registry-node").mkdir(parents=True)
    (custom_nodes / ".disabled" / "registry-node" / ".tracking").write_text("pyproject.toml\n", encoding="utf-8")
    (custom_nodes / ".disabled" / "registry-node" / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "registry-node"',
                'version = "1.0.0"',
            ]
        ),
        encoding="utf-8",
    )
    (custom_nodes / "file.py").write_text("pass", encoding="utf-8")

    monkeypatch.setattr(comfyui_base, "inspect_repository", _fake_repository_state)
    monkeypatch.setattr(comfyui_base.git_warpper, "get_current_branch_remote_url", _fail_old_git_info_reader)
    monkeypatch.setattr(comfyui_base.git_warpper, "get_current_commit", _fail_old_git_info_reader)
    monkeypatch.setattr(comfyui_base.git_warpper, "get_current_branch", _fail_old_git_info_reader)

    nodes = sorted(comfyui_base.list_comfyui_custom_nodes(tmp_path), key=lambda item: item["name"])
    assert [node["name"] for node in nodes] == ["disabled.disabled", "installed", "registry-node"]
    assert nodes[0]["status"] is False
    assert nodes[0]["url"] is None
    assert nodes[1]["url"] == "https://example.test/installed"
    assert nodes[1]["commit"] == "installed-full-commit"
    assert nodes[1]["branch"] == "main"
    assert nodes[2]["status"] is False
    assert nodes[2]["source_type"] == "comfy-registry"
    assert nodes[2]["registry_version"] == "1.0.0"

    moves = []
    monkeypatch.setattr(comfyui_base, "move_files", lambda src, dst: moves.append((src, dst)))
    comfyui_base.set_comfyui_custom_node_status(tmp_path, "disabled", True)
    comfyui_base.set_comfyui_custom_node_status(tmp_path, "installed", False)
    comfyui_base.set_comfyui_custom_node_status(tmp_path, "registry-node", True)
    assert moves == [
        (custom_nodes / "disabled.disabled", custom_nodes / "disabled"),
        (custom_nodes / "installed", custom_nodes / "installed.disabled"),
        (custom_nodes / ".disabled" / "registry-node", custom_nodes / "registry-node"),
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
    assert sorted(updates) == ["bad", "ok"]


def test_comfyui_extension_manager_update_all_reuses_extension_scan(monkeypatch, tmp_path):
    manager = comfyui_base.ComfyUiExtensionManager(tmp_path)
    git_path = tmp_path / "custom_nodes" / "git-node"
    registry_path = tmp_path / "custom_nodes" / "registry-node"
    file_path = tmp_path / "custom_nodes" / "file.py"
    extensions = [
        ManagedExtension(
            name="git-node",
            path=git_path,
            enabled=True,
            is_git_repo=True,
            source_type="git",
        ),
        ManagedExtension(
            name="registry-node",
            path=registry_path,
            enabled=True,
            is_git_repo=False,
            source_type="comfy-registry",
            registry_id="registry-node",
        ),
        ManagedExtension(
            name="file.py",
            path=file_path,
            enabled=True,
            is_git_repo=False,
            source_type="file",
        ),
    ]
    scan_count = 0

    def fake_list_extensions():
        nonlocal scan_count
        scan_count += 1
        return extensions

    git_updates = []
    registry_updates = []

    def fake_registry_update(comfyui_path, *, node_id, version, target_path):
        registry_updates.append((comfyui_path, node_id, version, target_path))

    monkeypatch.setattr(manager, "list_extensions", fake_list_extensions)
    monkeypatch.setattr(comfyui_base.git_warpper, "update", lambda path: git_updates.append(path))
    monkeypatch.setattr(comfyui_base, "switch_comfy_registry_node_version", fake_registry_update)

    manager.update_all()

    assert scan_count == 1
    assert git_updates == [git_path]
    assert registry_updates == [(tmp_path, "registry-node", None, registry_path)]


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

    monkeypatch.setattr(fooocus_base, "check_fooocus_hf_mirror_arg", lambda _path: True)
    monkeypatch.setattr(
        fooocus_base.git_warpper,
        "get_current_branch_remote_url",
        lambda _path: (_ for _ in ()).throw(AssertionError("should not inspect git remote")),
    )

    comfyui_base.launch_comfyui(tmp_path / "comfy", launch_args=["--listen"], use_hf_mirror=True, use_cuda_malloc=True, enable_hotpatcher=True)
    fooocus_base.launch_fooocus(tmp_path / "fooocus", launch_args=["--preset", "x"], use_hf_mirror=True, use_cuda_malloc=True)
    qwen_tts_webui_base.launch_qwen_tts_webui(tmp_path / "qwen", launch_args=[], use_hf_mirror=True, use_cuda_malloc=True)

    assert calls[0][1]["launch_script"] == "main.py"
    assert calls[0][1]["webui_name"] == "ComfyUI"
    assert calls[0][1]["custom_env"]["HOTPATCH"] == "True"
    assert calls[1][1]["launch_args"] == ["--preset", "x", "--hf-mirror", "https://hf.example"]
    assert calls[2][1]["launch_script"] == "launch.py"


def test_fooocus_launch_skips_hf_mirror_arg_when_parser_does_not_support_it(monkeypatch, tmp_path):
    calls = []

    def fake_hf(**kwargs):
        env = kwargs["origin_env"].copy()
        env["HF_ENDPOINT"] = "https://hf.example"
        return env

    monkeypatch.setattr(fooocus_base, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(fooocus_base, "apply_hf_mirror", fake_hf)
    monkeypatch.setattr(fooocus_base, "check_fooocus_hf_mirror_arg", lambda _path: False)
    monkeypatch.setattr(fooocus_base, "get_pypi_mirror_config", lambda use_cn_mirror=False, origin_env=None: origin_env or {})
    monkeypatch.setattr(fooocus_base, "get_cuda_malloc_var", lambda: None)
    monkeypatch.setattr(fooocus_base, "apply_hotpatcher_launch_env", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(fooocus_base, "launch_webui", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(
        fooocus_base.git_warpper,
        "get_current_branch_remote_url",
        lambda _path: (_ for _ in ()).throw(AssertionError("should not inspect git remote")),
    )

    fooocus_base.launch_fooocus(tmp_path, launch_args=["--preset", "x"], use_hf_mirror=True)

    assert calls[0]["launch_args"] == ["--preset", "x"]
    assert calls[0]["custom_env"]["HF_ENDPOINT"] == "https://hf.example"


@pytest.mark.parametrize(
    "launch_args",
    [
        ["--preset", "x", "--hf-mirror", "https://custom.example"],
        ["--preset", "x", "--hf-mirror=https://custom.example"],
    ],
)
def test_fooocus_launch_does_not_duplicate_user_hf_mirror_arg(monkeypatch, tmp_path, launch_args):
    calls = []

    def fake_hf(**kwargs):
        env = kwargs["origin_env"].copy()
        env["HF_ENDPOINT"] = "https://hf.example"
        return env

    monkeypatch.setattr(fooocus_base, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(fooocus_base, "apply_hf_mirror", fake_hf)
    monkeypatch.setattr(
        fooocus_base,
        "check_fooocus_hf_mirror_arg",
        lambda _path: (_ for _ in ()).throw(AssertionError("should not check parser")),
    )
    monkeypatch.setattr(fooocus_base, "get_pypi_mirror_config", lambda use_cn_mirror=False, origin_env=None: origin_env or {})
    monkeypatch.setattr(fooocus_base, "get_cuda_malloc_var", lambda: None)
    monkeypatch.setattr(fooocus_base, "apply_hotpatcher_launch_env", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(fooocus_base, "launch_webui", lambda **kwargs: calls.append(kwargs))

    fooocus_base.launch_fooocus(tmp_path, launch_args=launch_args, use_hf_mirror=True)

    assert calls[0]["launch_args"] == launch_args
    assert calls[0]["custom_env"]["HF_ENDPOINT"] == "https://hf.example"


def test_install_sd_webui_orchestrates_branch_extensions_repositories_and_models(monkeypatch, tmp_path):
    calls = []
    (tmp_path / "requirements_versions.txt").write_text("demo\n", encoding="utf-8")
    branch_info = {
        "name": "Demo Branch",
        "dtype": "sd_webui_dev",
        "url": "https://github.com/example/webui",
        "branch": "dev",
        "use_submodule": True,
    }

    monkeypatch.setattr(sd_webui_base, "SD_WEBUI_BRANCH_INFO_DICT", [branch_info])
    monkeypatch.setattr(
        sd_webui_base,
        "SD_WEBUI_EXTENSION_INFO_DICT",
        [{"name": "Ext", "url": "https://github.com/example/ext", "save_dir": "extensions/ext", "supported_branch": ["sd_webui_dev"]}],
    )
    monkeypatch.setattr(
        sd_webui_base,
        "SD_WEBUI_REPOSITORY_INFO_DICT",
        [{"name": "Repo", "url": "https://github.com/example/repo", "save_dir": "repositories/repo", "supported_branch": ["sd_webui_dev"]}],
    )
    monkeypatch.setattr(sd_webui_base, "prepare_pytorch_install_info", lambda **kwargs: ("torch", "xformers", {"TORCH": "env"}))
    monkeypatch.setattr(sd_webui_base, "get_pypi_mirror_config", lambda use_cn_mirror=True: {"PIP": str(use_cn_mirror)})
    monkeypatch.setattr(sd_webui_base, "apply_git_base_config_and_github_mirror", lambda **kwargs: {"GIT_CONFIG_GLOBAL": "gitconfig", **kwargs["origin_env"]})
    monkeypatch.setattr(sd_webui_base, "clone_repo", lambda **kwargs: calls.append(("clone", kwargs)))
    monkeypatch.setattr(sd_webui_base.git_warpper, "switch_branch", lambda **kwargs: calls.append(("switch", kwargs)))
    monkeypatch.setattr(sd_webui_base, "install_pytorch_for_webui", lambda **kwargs: calls.append(("pytorch", kwargs)))
    monkeypatch.setattr(sd_webui_base, "install_clip_package", lambda **kwargs: calls.append(("clip", kwargs)))
    monkeypatch.setattr(sd_webui_base, "install_requirements", lambda **kwargs: calls.append(("requirements", kwargs)))
    monkeypatch.setattr(sd_webui_base, "pre_download_model_for_webui", lambda **kwargs: calls.append(("model", kwargs)))
    monkeypatch.setattr(sd_webui_base, "install_sd_webui_config", lambda path: calls.append(("config", path)))

    sd_webui_base.install_sd_webui(tmp_path, install_branch="sd_webui_dev", use_uv=False, no_pre_download_model=False)

    assert os.environ["GIT_CONFIG_GLOBAL"] == "gitconfig"
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
    req = tmp_path / "requirements.txt"
    req.write_text("demo\n", encoding="utf-8")
    calls = []

    def ok_task(**kwargs):
        calls.append((ok_task.__name__, kwargs))

    def bad_task(**kwargs):
        calls.append((bad_task.__name__, kwargs))
        raise RuntimeError("task bad")

    monkeypatch.setattr(sd_webui_base, "apply_git_base_config_and_github_mirror", lambda **kwargs: {"GIT_CONFIG_GLOBAL": "gitconfig", **kwargs["origin_env"]})
    monkeypatch.setattr(sd_webui_base, "get_pypi_mirror_config", lambda use_cn_mirror, origin_env=None: {"PIP": str(use_cn_mirror), **(origin_env or {})})
    monkeypatch.setattr(sd_webui_base, "fix_stable_diffusion_invaild_repo_url", ok_task)
    monkeypatch.setattr(sd_webui_base, "fix_forge_neo_alert", ok_task)
    monkeypatch.setattr(sd_webui_base, "py_dependency_checker", bad_task)
    monkeypatch.setattr(sd_webui_base, "install_extension_requirements", ok_task)
    monkeypatch.setattr(sd_webui_base, "fix_torch_libomp", ok_task)
    monkeypatch.setattr(sd_webui_base, "check_torch_version", ok_task)
    monkeypatch.setattr(sd_webui_base, "check_onnxruntime_gpu", ok_task)

    with pytest.raises(AggregateError) as exc:
        sd_webui_base.check_sd_webui_env(tmp_path, use_uv=False, use_pypi_mirror=True)

    assert len(exc.value.exceptions) == 1
    assert calls[2][0] == "bad_task"
    assert calls[2][1]["requirement_path"] == req
    assert calls[2][1]["name"] == "Stable Diffusion WebUI"
    assert calls[2][1]["use_uv"] is False
    assert calls[2][1]["custom_env"]["PIP"] == "True"
    assert calls[2][1]["custom_env"]["GIT_CONFIG_GLOBAL"] == "gitconfig"


def test_sd_webui_extension_lifecycle_and_model_uninstall(monkeypatch, tmp_path):
    extensions = tmp_path / "extensions"
    models = tmp_path / "models" / "Stable-diffusion"
    for folder in [extensions / "enabled" / ".git", extensions / "disabled" / ".git", models]:
        folder.mkdir(parents=True)
    (extensions / "plain").mkdir()
    (tmp_path / "config.json").write_text('{"disabled_extensions": ["disabled"]}', encoding="utf-8")
    (models / "demo.safetensors").write_text("model", encoding="utf-8")
    (models / "other.txt").write_text("other", encoding="utf-8")

    monkeypatch.setattr(sd_webui_base, "inspect_repository", _fake_repository_state)
    monkeypatch.setattr(sd_webui_base.git_warpper, "get_current_branch_remote_url", _fail_old_git_info_reader)
    monkeypatch.setattr(sd_webui_base.git_warpper, "get_current_commit", _fail_old_git_info_reader)
    monkeypatch.setattr(sd_webui_base.git_warpper, "get_current_branch", _fail_old_git_info_reader)

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
    monkeypatch.setattr(sd_webui_base, "remove_files", lambda path: removed.append(path))
    sd_webui_base.uninstall_sd_webui_extension(tmp_path, "enabled")
    sd_webui_base.uninstall_sd_webui_model(tmp_path, "demo", model_type="Stable-diffusion")
    assert removed == [extensions / "enabled", models / "demo.safetensors"]

    with pytest.raises(FileNotFoundError):
        sd_webui_base.uninstall_sd_webui_model(tmp_path, "missing", model_type="Stable-diffusion")


def test_install_and_update_sd_webui_extensions_aggregate(monkeypatch, tmp_path):
    (tmp_path / "extensions" / "bad" / ".git").mkdir(parents=True)
    (tmp_path / "extensions" / "ok" / ".git").mkdir(parents=True)
    monkeypatch.setattr(sd_webui_base, "list_sd_webui_extensions", lambda _path: [{"name": "existing"}])
    monkeypatch.setattr(sd_webui_base, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])

    cloned = []

    def fake_clone(repo, path):
        cloned.append((repo, path))
        if "fail" in repo:
            raise RuntimeError("clone bad")

    monkeypatch.setattr(sd_webui_base, "clone_repo", fake_clone)
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

    def fake_update(path):
        updates.append(path.name)
        if path.name == "bad":
            raise RuntimeError("bad")

    monkeypatch.setattr(sd_webui_base.git_warpper, "update", fake_update)
    with pytest.raises(AggregateError):
        sd_webui_base.update_sd_webui_extensions(tmp_path)
    assert sorted(updates) == ["bad", "ok"]


def test_invokeai_dependency_selection_and_sync_fallback(monkeypatch):
    requirements = [
        "torch==2.4.1",
        "torchvision==0.19.1 ; python_version >= '3.10'",
        "torchaudio==2.4.1",
        "xformers==0.0.28",
    ]
    calls = []

    monkeypatch.setattr(invokeai_base.importlib.metadata, "requires", lambda name: requirements if name == "invokeai" else [])
    monkeypatch.setattr(invokeai_base.importlib.metadata, "version", lambda name: "4.2.0" if name == "invokeai" else (_ for _ in ()).throw(Exception("missing")))
    monkeypatch.setattr(invokeai_base, "auto_detect_pytorch_device_category", lambda: "cuda")
    monkeypatch.setattr(invokeai_base, "get_pytorch_mirror_type_for_ivnokeai", lambda device_type: "cu124")
    monkeypatch.setattr(invokeai_base, "prepare_pytorch_install_info", lambda **kwargs: (None, None, {"TORCH": kwargs["pytorch_mirror_type"]}))
    monkeypatch.setattr(invokeai_base, "get_pypi_mirror_config", lambda use_cn_mirror: {"PIP": str(use_cn_mirror)})

    def fake_install_pytorch(**kwargs):
        calls.append(("pytorch", kwargs))
        if kwargs["torch_package"].endswith("xformers==0.0.28"):
            raise RuntimeError("xformers bad")

    def fake_install_pytorch_with_fallback(**kwargs):
        calls.append(("pytorch_fallback", kwargs))

    monkeypatch.setattr(invokeai_base, "install_pytorch", fake_install_pytorch)
    monkeypatch.setattr(invokeai_base, "install_pytorch_with_fallback", fake_install_pytorch_with_fallback)
    monkeypatch.setattr(invokeai_base, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))

    assert invokeai_base.get_invokeai_require_torch_version() == "2.4.1"
    assert invokeai_base.get_pytorch_for_invokeai() == "torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1"
    assert invokeai_base.get_xformers_for_invokeai() == "xformers==0.0.28"

    invokeai_base.sync_invokeai_component(use_pypi_mirror=True, use_uv=False)

    assert calls[0] == (
        "pytorch",
        {
            "torch_package": "torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 xformers==0.0.28",
            "custom_env": {"TORCH": "cu124"},
            "use_uv": False,
        },
    )
    assert calls[1] == (
        "pytorch_fallback",
        {
            "torch_package": "torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1",
            "custom_env": {"TORCH": "cu124"},
            "use_uv": False,
        },
    )
    assert calls[2] == ("pip", ("invokeai==4.2.0",), {"use_uv": False, "custom_env": {"PIP": "True"}})


def test_check_invokeai_env_installs_core_then_checks_metadata(monkeypatch):
    calls = []

    monkeypatch.setattr(invokeai_base, "apply_git_base_config_and_github_mirror", lambda **_kwargs: {"GIT": "1"})

    def fake_pypi(use_cn_mirror, origin_env=None):
        env = dict(origin_env or {})
        env["PIP"] = str(use_cn_mirror)
        return env

    monkeypatch.setattr(invokeai_base, "get_pypi_mirror_config", fake_pypi)
    monkeypatch.setattr(invokeai_base, "get_package_version_from_library", lambda name: None if name == "invokeai" else "1.0.0")
    monkeypatch.setattr(invokeai_base, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))
    monkeypatch.setattr(invokeai_base, "py_package_metadata_dependency_checker", lambda **kwargs: calls.append(("metadata", kwargs)))
    monkeypatch.setattr(invokeai_base, "fix_torch_libomp", lambda: calls.append(("fix_torch_libomp", {})))
    monkeypatch.setattr(invokeai_base, "check_torch_version", lambda: calls.append(("check_torch_version", {})))
    monkeypatch.setattr(invokeai_base, "check_onnxruntime_gpu", lambda **kwargs: calls.append(("check_onnxruntime_gpu", kwargs)))

    invokeai_base.check_invokeai_env(use_uv=False, use_pypi_mirror=True)

    custom_env = {"GIT": "1", "PIP": "True"}
    assert calls == [
        ("pip", ("invokeai", "--no-deps"), {"use_uv": False, "custom_env": custom_env}),
        ("metadata", {"package_name": "invokeai", "name": "InvokeAI", "use_uv": False, "custom_env": custom_env}),
        ("fix_torch_libomp", {}),
        ("check_torch_version", {}),
        ("check_onnxruntime_gpu", {"use_uv": False, "skip_if_missing": True, "custom_env": custom_env}),
    ]


def test_check_invokeai_env_skips_core_install_when_installed(monkeypatch):
    calls = []

    monkeypatch.setattr(invokeai_base, "apply_git_base_config_and_github_mirror", lambda **_kwargs: {})
    monkeypatch.setattr(invokeai_base, "get_pypi_mirror_config", lambda use_cn_mirror, origin_env=None: dict(origin_env or {}))
    monkeypatch.setattr(invokeai_base, "get_package_version_from_library", lambda _name: "5.0.0")
    monkeypatch.setattr(invokeai_base, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))
    monkeypatch.setattr(invokeai_base, "py_package_metadata_dependency_checker", lambda **kwargs: calls.append(("metadata", kwargs)))
    monkeypatch.setattr(invokeai_base, "fix_torch_libomp", lambda: calls.append(("fix_torch_libomp", {})))
    monkeypatch.setattr(invokeai_base, "check_torch_version", lambda: calls.append(("check_torch_version", {})))
    monkeypatch.setattr(invokeai_base, "check_onnxruntime_gpu", lambda **kwargs: calls.append(("check_onnxruntime_gpu", kwargs)))

    invokeai_base.check_invokeai_env(use_uv=True, use_pypi_mirror=False)

    assert calls[0] == ("metadata", {"package_name": "invokeai", "name": "InvokeAI", "use_uv": True, "custom_env": {}})
    assert not any(call[0] == "pip" for call in calls)


def test_check_invokeai_env_aggregates_metadata_and_existing_errors(monkeypatch):
    monkeypatch.setattr(invokeai_base, "apply_git_base_config_and_github_mirror", lambda **_kwargs: {})
    monkeypatch.setattr(invokeai_base, "get_pypi_mirror_config", lambda use_cn_mirror, origin_env=None: dict(origin_env or {}))
    monkeypatch.setattr(invokeai_base, "get_package_version_from_library", lambda _name: "5.0.0")
    monkeypatch.setattr(invokeai_base, "pip_install", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(invokeai_base, "py_package_metadata_dependency_checker", lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("metadata bad")))
    monkeypatch.setattr(invokeai_base, "fix_torch_libomp", lambda: (_ for _ in ()).throw(RuntimeError("torch fix bad")))
    monkeypatch.setattr(invokeai_base, "check_torch_version", lambda: None)
    monkeypatch.setattr(invokeai_base, "check_onnxruntime_gpu", lambda **_kwargs: None)

    with pytest.raises(AggregateError) as exc_info:
        invokeai_base.check_invokeai_env()

    assert [str(exc) for exc in exc_info.value.exceptions] == ["metadata bad", "torch fix bad"]


def test_invokeai_custom_node_lifecycle_and_model_download(monkeypatch, tmp_path):
    nodes = tmp_path / "nodes"
    (nodes / "enabled" / ".git").mkdir(parents=True)
    (nodes / "enabled" / "__init__.py").write_text("", encoding="utf-8")
    (nodes / "disabled").mkdir()
    (nodes / "disabled" / "__init__.py.bak").write_text("", encoding="utf-8")
    (nodes / "file.py").write_text("pass", encoding="utf-8")
    calls = []

    monkeypatch.setattr(invokeai_base, "inspect_repository", _fake_repository_state)
    monkeypatch.setattr(invokeai_base.git_warpper, "get_current_branch_remote_url", _fail_old_git_info_reader)
    monkeypatch.setattr(invokeai_base.git_warpper, "get_current_commit", _fail_old_git_info_reader)
    monkeypatch.setattr(invokeai_base.git_warpper, "get_current_branch", _fail_old_git_info_reader)

    infos = sorted(invokeai_base.list_invokeai_custom_nodes(tmp_path), key=lambda item: item["name"])
    assert [(item["name"], item["status"]) for item in infos] == [("disabled", False), ("enabled", True)]
    assert infos[0]["url"] is None
    assert infos[1]["url"] == "https://example.test/enabled"
    assert infos[1]["commit"] == "enabled-full-commit"
    assert infos[1]["branch"] == "main"

    monkeypatch.setattr(invokeai_base, "move_files", lambda src, dst: calls.append(("move", src, dst)))
    invokeai_base.set_invokeai_custom_nodes_status(tmp_path, "enabled", False)
    invokeai_base.set_invokeai_custom_nodes_status(tmp_path, "disabled", True)
    assert calls == [
        ("move", nodes / "enabled" / "__init__.py", nodes / "enabled" / "__init__.py.bak"),
        ("move", nodes / "disabled" / "__init__.py.bak", nodes / "disabled" / "__init__.py"),
    ]

    monkeypatch.setattr(invokeai_base, "install_webui_model_from_library", lambda **kwargs: [tmp_path / "model.safetensors"])
    monkeypatch.setattr(invokeai_base, "import_model_to_invokeai", lambda model_list, **_kwargs: calls.append(("import", model_list)))
    invokeai_base.install_invokeai_model_from_library(tmp_path, model_name="demo")
    assert calls[-1] == ("import", [tmp_path / "model.safetensors"])


def test_install_update_uninstall_invokeai_custom_nodes(monkeypatch, tmp_path):
    (tmp_path / "nodes" / "bad" / ".git").mkdir(parents=True)
    (tmp_path / "nodes" / "ok" / ".git").mkdir(parents=True)
    monkeypatch.setattr(invokeai_base, "list_invokeai_custom_nodes", lambda _path: [{"name": "existing"}])
    monkeypatch.setattr(invokeai_base, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])

    cloned = []

    def fake_clone(repo, path):
        cloned.append((repo, path))
        if "fail" in repo:
            raise RuntimeError("clone bad")

    monkeypatch.setattr(invokeai_base, "clone_repo", fake_clone)
    with pytest.raises(AggregateError):
        invokeai_base.install_invokeai_custom_nodes(
            tmp_path,
            ["https://github.com/example/existing", "https://github.com/example/new", "https://github.com/example/fail"],
        )
    assert cloned == [
        ("https://github.com/example/new", tmp_path / "nodes" / "new"),
        ("https://github.com/example/fail", tmp_path / "nodes" / "fail"),
    ]

    updates = []

    def fake_update(path):
        updates.append(path.name)
        if path.name == "bad":
            raise RuntimeError("bad")

    monkeypatch.setattr(invokeai_base.git_warpper, "update", fake_update)
    with pytest.raises(AggregateError):
        invokeai_base.update_invokeai_custom_nodes(tmp_path)
    assert sorted(updates) == ["bad", "ok"]

    removed = []
    monkeypatch.setattr(invokeai_base, "remove_files", lambda path: removed.append(path))
    invokeai_base.uninstall_invokeai_custom_node(tmp_path, "ok")
    assert removed == [tmp_path / "nodes" / "ok"]
