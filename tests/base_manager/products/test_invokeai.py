"""InvokeAI 管理器测试"""

import pytest

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager import invokeai_base
from sd_webui_all_in_one.custom_exceptions import AggregateError
from tests.base_manager.products.helpers import fail_old_git_info_reader, fake_repository_state, implementation_module, use_temp_git_config


def test_invokeai_dependency_selection_and_sync_fallback(monkeypatch):
    implementation = implementation_module(invokeai_base, "sync_invokeai_component")
    requirements = [
        "torch==2.4.1",
        "torchvision==0.19.1 ; python_version >= '3.10'",
        "torchaudio==2.4.1",
        "xformers==0.0.28",
    ]
    calls = []

    monkeypatch.setattr(implementation.importlib.metadata, "requires", lambda name: requirements if name == "invokeai" else [])
    monkeypatch.setattr(implementation.importlib.metadata, "version", lambda name: "4.2.0" if name == "invokeai" else (_ for _ in ()).throw(Exception("missing")))
    monkeypatch.setattr(implementation, "auto_detect_pytorch_device_category", lambda: "cuda")
    monkeypatch.setattr(implementation, "get_pytorch_mirror_type_for_ivnokeai", lambda device_type: "cu124")
    monkeypatch.setattr(implementation, "prepare_pytorch_install_info", lambda **kwargs: (None, None, {"TORCH": kwargs["pytorch_mirror_type"]}))
    monkeypatch.setattr(implementation, "get_pypi_mirror_config", lambda use_cn_mirror: {"PIP": str(use_cn_mirror)})

    def fake_install_pytorch(**kwargs):
        calls.append(("pytorch", kwargs))
        if kwargs["torch_package"].endswith("xformers==0.0.28"):
            raise RuntimeError("xformers bad")

    def fake_install_pytorch_with_fallback(**kwargs):
        calls.append(("pytorch_fallback", kwargs))

    monkeypatch.setattr(implementation, "install_pytorch", fake_install_pytorch)
    monkeypatch.setattr(implementation, "install_pytorch_with_fallback", fake_install_pytorch_with_fallback)
    monkeypatch.setattr(implementation, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))

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
            "force_reinstall": False,
        },
    )
    assert calls[2] == ("pip", ("invokeai==4.2.0",), {"use_uv": False, "custom_env": {"PIP": "True"}})


def test_check_invokeai_env_installs_core_then_checks_metadata(monkeypatch):
    calls = []
    implementation = implementation_module(invokeai_base, "check_invokeai_env")
    components = implementation_module(invokeai_base, "sync_invokeai_component")

    monkeypatch.setattr(implementation, "apply_git_base_config_and_github_mirror", lambda **_kwargs: {"GIT": "1"})

    def fake_pypi(use_cn_mirror, origin_env=None):
        env = dict(origin_env or {})
        env["PIP"] = str(use_cn_mirror)
        return env

    monkeypatch.setattr(implementation, "get_pypi_mirror_config", fake_pypi)
    monkeypatch.setattr(components, "get_package_version_from_library", lambda name: None if name == "invokeai" else "1.0.0")
    monkeypatch.setattr(components, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))
    monkeypatch.setattr(implementation, "py_package_metadata_dependency_checker", lambda **kwargs: calls.append(("metadata", kwargs)))
    monkeypatch.setattr(implementation, "fix_torch_libomp", lambda: calls.append(("fix_torch_libomp", {})))
    monkeypatch.setattr(implementation, "check_torch_version", lambda: calls.append(("check_torch_version", {})))
    monkeypatch.setattr(implementation, "check_onnxruntime_gpu", lambda **kwargs: calls.append(("check_onnxruntime_gpu", kwargs)))

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
    implementation = implementation_module(invokeai_base, "check_invokeai_env")
    components = implementation_module(invokeai_base, "sync_invokeai_component")

    monkeypatch.setattr(implementation, "apply_git_base_config_and_github_mirror", lambda **_kwargs: {})
    monkeypatch.setattr(implementation, "get_pypi_mirror_config", lambda use_cn_mirror, origin_env=None: dict(origin_env or {}))
    monkeypatch.setattr(components, "get_package_version_from_library", lambda _name: "5.0.0")
    monkeypatch.setattr(components, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))
    monkeypatch.setattr(implementation, "py_package_metadata_dependency_checker", lambda **kwargs: calls.append(("metadata", kwargs)))
    monkeypatch.setattr(implementation, "fix_torch_libomp", lambda: calls.append(("fix_torch_libomp", {})))
    monkeypatch.setattr(implementation, "check_torch_version", lambda: calls.append(("check_torch_version", {})))
    monkeypatch.setattr(implementation, "check_onnxruntime_gpu", lambda **kwargs: calls.append(("check_onnxruntime_gpu", kwargs)))

    invokeai_base.check_invokeai_env(use_uv=True, use_pypi_mirror=False)

    assert calls[0] == ("metadata", {"package_name": "invokeai", "name": "InvokeAI", "use_uv": True, "custom_env": {}})
    assert not any(call[0] == "pip" for call in calls)


def test_check_invokeai_env_aggregates_metadata_and_existing_errors(monkeypatch):
    implementation = implementation_module(invokeai_base, "check_invokeai_env")
    components = implementation_module(invokeai_base, "sync_invokeai_component")
    monkeypatch.setattr(implementation, "apply_git_base_config_and_github_mirror", lambda **_kwargs: {})
    monkeypatch.setattr(implementation, "get_pypi_mirror_config", lambda use_cn_mirror, origin_env=None: dict(origin_env or {}))
    monkeypatch.setattr(components, "get_package_version_from_library", lambda _name: "5.0.0")
    monkeypatch.setattr(components, "pip_install", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(implementation, "py_package_metadata_dependency_checker", lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("metadata bad")))
    monkeypatch.setattr(implementation, "fix_torch_libomp", lambda: (_ for _ in ()).throw(RuntimeError("torch fix bad")))
    monkeypatch.setattr(implementation, "check_torch_version", lambda: None)
    monkeypatch.setattr(implementation, "check_onnxruntime_gpu", lambda **_kwargs: None)

    with pytest.raises(AggregateError) as exc_info:
        invokeai_base.check_invokeai_env()

    assert [str(exc) for exc in exc_info.value.exceptions] == ["metadata bad", "torch fix bad"]


def test_invokeai_custom_node_lifecycle_and_model_download(monkeypatch, tmp_path):
    extension_implementation = implementation_module(invokeai_base, "list_invokeai_custom_nodes")
    model_implementation = implementation_module(invokeai_base, "install_invokeai_model_from_library")
    nodes = tmp_path / "nodes"
    (nodes / "enabled" / ".git").mkdir(parents=True)
    (nodes / "enabled" / "__init__.py").write_text("", encoding="utf-8")
    (nodes / "disabled").mkdir()
    (nodes / "disabled" / "__init__.py.bak").write_text("", encoding="utf-8")
    (nodes / "file.py").write_text("pass", encoding="utf-8")
    calls = []

    monkeypatch.setattr(extension_implementation, "inspect_repository", fake_repository_state)
    monkeypatch.setattr(git_warpper, "get_current_branch_remote_url", fail_old_git_info_reader)
    monkeypatch.setattr(git_warpper, "get_current_commit", fail_old_git_info_reader)
    monkeypatch.setattr(git_warpper, "get_current_branch", fail_old_git_info_reader)

    infos = sorted(invokeai_base.list_invokeai_custom_nodes(tmp_path), key=lambda item: item["name"])
    assert [(item["name"], item["status"]) for item in infos] == [("disabled", False), ("enabled", True)]
    assert infos[0]["url"] is None
    assert infos[1]["url"] == "https://example.test/enabled"
    assert infos[1]["commit"] == "enabled-full-commit"
    assert infos[1]["branch"] == "main"

    monkeypatch.setattr(extension_implementation, "move_files", lambda src, dst: calls.append(("move", src, dst)))
    invokeai_base.set_invokeai_custom_nodes_status(tmp_path, "enabled", False)
    invokeai_base.set_invokeai_custom_nodes_status(tmp_path, "disabled", True)
    assert calls == [
        ("move", nodes / "enabled" / "__init__.py", nodes / "enabled" / "__init__.py.bak"),
        ("move", nodes / "disabled" / "__init__.py.bak", nodes / "disabled" / "__init__.py"),
    ]

    monkeypatch.setattr(model_implementation, "install_webui_model_from_library", lambda **kwargs: [tmp_path / "model.safetensors"])
    monkeypatch.setattr(model_implementation, "import_model_to_invokeai", lambda model_list, **_kwargs: calls.append(("import", model_list)))
    invokeai_base.install_invokeai_model_from_library(tmp_path, model_name="demo")
    assert calls[-1] == ("import", [tmp_path / "model.safetensors"])


def test_install_update_uninstall_invokeai_custom_nodes(monkeypatch, tmp_path):
    use_temp_git_config(monkeypatch, tmp_path)
    implementation = implementation_module(invokeai_base, "install_invokeai_custom_nodes")
    (tmp_path / "nodes" / "bad" / ".git").mkdir(parents=True)
    (tmp_path / "nodes" / "ok" / ".git").mkdir(parents=True)
    monkeypatch.setattr(implementation, "list_invokeai_custom_nodes", lambda _path: [{"name": "existing"}])
    monkeypatch.setattr(implementation, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])

    cloned = []

    def fake_clone(repo, path):
        cloned.append((repo, path))
        if "fail" in repo:
            raise RuntimeError("clone bad")

    monkeypatch.setattr(implementation, "clone_repo", fake_clone)
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

    def fake_update(path, live=True, fetch=True):
        updates.append(path.name)
        if path.name == "bad":
            raise RuntimeError("bad")

    monkeypatch.setattr(git_warpper, "update", fake_update)
    with pytest.raises(AggregateError):
        invokeai_base.update_invokeai_custom_nodes(tmp_path)
    assert sorted(updates) == ["bad", "ok"]

    removed = []
    monkeypatch.setattr(implementation, "remove_files", lambda path: removed.append(path))
    invokeai_base.uninstall_invokeai_custom_node(tmp_path, "ok")
    assert removed == [tmp_path / "nodes" / "ok"]
