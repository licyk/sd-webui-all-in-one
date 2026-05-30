import os

import pytest

from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.base_manager import fooocus_base
from sd_webui_all_in_one.base_manager import sd_scripts_base
from sd_webui_all_in_one.base_manager import sd_trainer_base


def _patch_common_install_deps(monkeypatch, module, calls):
    monkeypatch.setattr(module, "prepare_pytorch_install_info", lambda **kwargs: ("torch", "xformers", {"TORCH": "env"}))
    monkeypatch.setattr(module, "get_pypi_mirror_config", lambda use_cn_mirror=True, origin_env=None: {"PIP": str(use_cn_mirror), **(origin_env or {})})
    monkeypatch.setattr(module, "apply_git_base_config_and_github_mirror", lambda **kwargs: {"GIT_CONFIG_GLOBAL": "gitconfig", **kwargs["origin_env"]})
    monkeypatch.setattr(module, "clone_repo", lambda **kwargs: calls.append(("clone", kwargs)))
    monkeypatch.setattr(module.git_warpper, "switch_branch", lambda **kwargs: calls.append(("switch", kwargs)))
    monkeypatch.setattr(module.git_warpper, "update_submodule", lambda path: calls.append(("submodule", path)))
    monkeypatch.setattr(module, "install_pytorch_for_webui", lambda **kwargs: calls.append(("pytorch", kwargs)))
    monkeypatch.setattr(module, "install_requirements", lambda **kwargs: calls.append(("requirements", kwargs)))
    monkeypatch.setattr(module, "pre_download_model_for_webui", lambda **kwargs: calls.append(("model", kwargs)))


def test_install_fooocus_orchestrates_branch_requirements_model_and_config(monkeypatch, tmp_path):
    calls = []
    (tmp_path / "requirements_versions.txt").write_text("demo\n", encoding="utf-8")
    branch_info = {"name": "Demo Fooocus", "dtype": "fooocus_demo", "url": "https://github.com/example/fooocus", "branch": "demo", "use_submodule": False}
    monkeypatch.setattr(fooocus_base, "FOOOCUS_BRANCH_LIST", ["fooocus_demo"])
    monkeypatch.setattr(fooocus_base, "FOOOCUS_BRANCH_INFO_DICT", [branch_info])
    _patch_common_install_deps(monkeypatch, fooocus_base, calls)
    monkeypatch.setattr(fooocus_base, "install_fooocus_config", lambda **kwargs: calls.append(("config", kwargs)))

    fooocus_base.install_fooocus(tmp_path, install_branch="fooocus_demo", use_uv=False, no_pre_download_model=False)

    assert os.environ["GIT_CONFIG_GLOBAL"] == "gitconfig"
    assert calls[0] == ("clone", {"repo": branch_info["url"], "path": tmp_path})
    assert calls[1] == ("switch", {"path": tmp_path, "branch": "demo", "new_url": branch_info["url"], "recurse_submodules": False})
    assert calls[2][0] == "pytorch"
    assert calls[3] == ("requirements", {"path": tmp_path / "requirements_versions.txt", "use_uv": False, "custom_env": {"PIP": "True", "GIT_CONFIG_GLOBAL": "gitconfig"}, "cwd": tmp_path})
    assert calls[4][0] == "model"
    assert calls[4][1]["dtype"] == "fooocus"
    assert calls[5] == ("config", {"fooocus_path": tmp_path, "download_resource_type": "modelscope"})

    with pytest.raises(ValueError):
        fooocus_base.install_fooocus(tmp_path, install_branch="missing")

    (tmp_path / "requirements_versions.txt").unlink()
    with pytest.raises(FileNotFoundError):
        fooocus_base.install_fooocus(tmp_path, install_branch="fooocus_demo")


@pytest.mark.parametrize(
    ("module", "install_func", "branch_list_attr", "branch_info_attr", "branch_name", "root_file", "expected_dtype"),
    [
        (sd_scripts_base, "install_sd_scripts", "SD_SCRIPTS_BRANCH_LIST", "SD_SCRIPTS_BRANCH_INFO_DICT", "sd_scripts_demo", "requirements.txt", "sd_scripts"),
        (sd_trainer_base, "install_sd_trainer", "SD_TRAINER_BRANCH_LIST", "SD_TRAINER_BRANCH_INFO_DICT", "sd_trainer_demo", "requirements.txt", "sd_trainer"),
    ],
)
def test_install_sd_training_products_orchestrate_common_flow(monkeypatch, tmp_path, module, install_func, branch_list_attr, branch_info_attr, branch_name, root_file, expected_dtype):
    calls = []
    (tmp_path / root_file).write_text("demo\n", encoding="utf-8")
    branch_info = {"name": "Demo", "dtype": branch_name, "url": "https://github.com/example/product", "branch": "demo", "use_submodule": True}
    monkeypatch.setattr(module, branch_list_attr, [branch_name])
    monkeypatch.setattr(module, branch_info_attr, [branch_info])
    _patch_common_install_deps(monkeypatch, module, calls)

    getattr(module, install_func)(tmp_path, install_branch=branch_name, use_uv=False, no_pre_download_model=False)

    assert calls[0] == ("clone", {"repo": branch_info["url"], "path": tmp_path})
    assert calls[1] == ("submodule", tmp_path)
    assert calls[2] == ("switch", {"path": tmp_path, "branch": "demo", "new_url": branch_info["url"], "recurse_submodules": True})
    assert calls[3][0] == "pytorch"
    assert calls[4] == ("requirements", {"path": tmp_path / root_file, "use_uv": False, "custom_env": {"PIP": "True", "GIT_CONFIG_GLOBAL": "gitconfig"}, "cwd": tmp_path})
    assert calls[5][0] == "model"
    assert calls[5][1]["dtype"] == expected_dtype

    with pytest.raises(ValueError):
        getattr(module, install_func)(tmp_path, install_branch="missing")


def test_sd_scripts_install_exports_requirements_from_pyproject(monkeypatch, tmp_path):
    calls = []
    (tmp_path / "pyproject.toml").write_text("[project]\ndependencies=['demo']\n", encoding="utf-8")
    branch_info = {"name": "Demo", "dtype": "sd_scripts_demo", "url": "https://github.com/example/product", "branch": "demo", "use_submodule": False}
    monkeypatch.setattr(sd_scripts_base, "SD_SCRIPTS_BRANCH_LIST", ["sd_scripts_demo"])
    monkeypatch.setattr(sd_scripts_base, "SD_SCRIPTS_BRANCH_INFO_DICT", [branch_info])
    _patch_common_install_deps(monkeypatch, sd_scripts_base, calls)
    monkeypatch.setattr(sd_scripts_base, "export_requirements_from_toml_config", lambda toml_path, save_path: calls.append(("export", toml_path, save_path)) or save_path.write_text("demo\n", encoding="utf-8"))

    sd_scripts_base.install_sd_scripts(tmp_path, install_branch="sd_scripts_demo", no_pre_download_model=True)

    assert any(call[0] == "export" for call in calls)
    requirement_call = [call for call in calls if call[0] == "requirements"][0]
    assert requirement_call[1]["path"].name == "requirements.txt"
    assert requirement_call[1]["path"].parent != tmp_path


@pytest.mark.parametrize(
    ("module", "check_func", "req_name", "missing_message"),
    [
        (fooocus_base, "check_fooocus_env", "Fooocus", "Fooocus"),
        (sd_scripts_base, "check_sd_scripts_env", "SD Scripts", "SD Scripts"),
        (sd_trainer_base, "check_sd_trainer_env", "SD Trainer", "SD Trainer"),
    ],
)
def test_product_env_checks_aggregate_failures(monkeypatch, tmp_path, module, check_func, req_name, missing_message):
    (tmp_path / "requirements.txt").write_text("demo\n", encoding="utf-8")
    calls = []

    def ok_task(**kwargs):
        calls.append(("ok", kwargs))

    def bad_task(**kwargs):
        calls.append(("bad", kwargs))
        raise RuntimeError("task bad")

    monkeypatch.setattr(module, "apply_git_base_config_and_github_mirror", lambda **kwargs: {"GIT_CONFIG_GLOBAL": "gitconfig", **kwargs["origin_env"]})
    monkeypatch.setattr(module, "get_pypi_mirror_config", lambda use_cn_mirror, origin_env=None: {"PIP": str(use_cn_mirror), **(origin_env or {})})
    monkeypatch.setattr(module, "py_dependency_checker", bad_task)
    monkeypatch.setattr(module, "fix_torch_libomp", ok_task)
    monkeypatch.setattr(module, "check_torch_version", ok_task)
    monkeypatch.setattr(module, "check_onnxruntime_gpu", ok_task)
    monkeypatch.setattr(module, "check_numpy", ok_task)
    if hasattr(module, "check_accelerate_bin"):
        monkeypatch.setattr(module, "check_accelerate_bin", ok_task)

    with pytest.raises(AggregateError) as exc:
        getattr(module, check_func)(tmp_path, use_uv=False, use_pypi_mirror=True)

    assert len(exc.value.exceptions) == 1
    assert calls[0][0] == "bad"
    assert calls[0][1]["requirement_path"].name == "requirements.txt"
    assert calls[0][1]["name"] == req_name
    assert calls[0][1]["custom_env"]["GIT_CONFIG_GLOBAL"] == "gitconfig"

    (tmp_path / "requirements.txt").unlink()
    if module is not sd_scripts_base:
        with pytest.raises(FileNotFoundError, match=missing_message):
            getattr(module, check_func)(tmp_path)


@pytest.mark.parametrize(
    ("module", "switch_func", "branch_list_attr", "branch_info_attr", "branch_name"),
    [
        (fooocus_base, "switch_fooocus_branch", "FOOOCUS_BRANCH_LIST", "FOOOCUS_BRANCH_INFO_DICT", "fooocus_demo"),
        (sd_scripts_base, "switch_sd_scripts_branch", "SD_SCRIPTS_BRANCH_LIST", "SD_SCRIPTS_BRANCH_INFO_DICT", "sd_scripts_demo"),
        (sd_trainer_base, "switch_sd_trainer_branch", "SD_TRAINER_BRANCH_LIST", "SD_TRAINER_BRANCH_INFO_DICT", "sd_trainer_demo"),
    ],
)
def test_product_switch_and_update_delegate_to_git(monkeypatch, tmp_path, module, switch_func, branch_list_attr, branch_info_attr, branch_name):
    calls = []
    branch_info = {"name": "Demo", "dtype": branch_name, "url": "https://github.com/example/product", "branch": "demo", "use_submodule": True}
    monkeypatch.setattr(module, branch_list_attr, [branch_name])
    monkeypatch.setattr(module, branch_info_attr, [branch_info])
    monkeypatch.setattr(module, "apply_git_base_config_and_github_mirror", lambda **kwargs: {"GIT_CONFIG_GLOBAL": "gitconfig", **kwargs["origin_env"]})
    monkeypatch.setattr(module.git_warpper, "switch_branch", lambda **kwargs: calls.append(("switch", kwargs)))
    monkeypatch.setattr(module.git_warpper, "update", lambda path: calls.append(("update", path)))

    getattr(module, switch_func)(tmp_path, branch=branch_name, use_github_mirror=True, custom_github_mirror="mirror")
    assert calls[0] == ("switch", {"path": tmp_path, "branch": "demo", "new_url": "https://github.com/example/product", "recurse_submodules": True})

    update_func = getattr(module, switch_func.replace("switch_", "update_").replace("_branch", ""))
    update_func(tmp_path, use_github_mirror=True)
    assert calls[1] == ("update", tmp_path)

    with pytest.raises(ValueError):
        getattr(module, switch_func)(tmp_path, branch="missing")


@pytest.mark.parametrize(
    ("module", "library_func", "url_func", "uninstall_func", "dtype", "model_root"),
    [
        (fooocus_base, "install_fooocus_model_from_library", "install_fooocus_model_from_url", "uninstall_fooocus_model", "fooocus", "models"),
        (sd_scripts_base, "install_sd_scripts_model_from_library", "install_sd_scripts_model_from_url", "uninstall_sd_scripts_model", "sd_scripts", "sd-models"),
        (sd_trainer_base, "install_sd_trainer_model_from_library", "install_sd_trainer_model_from_url", "uninstall_sd_trainer_model", "sd_trainer", "sd-models"),
    ],
)
def test_product_model_install_and_uninstall_helpers(monkeypatch, tmp_path, module, library_func, url_func, uninstall_func, dtype, model_root):
    calls = []
    model_file = tmp_path / model_root / "checkpoints" / "demo.safetensors"
    model_file.parent.mkdir(parents=True)
    model_file.write_text("model", encoding="utf-8")

    monkeypatch.setattr(module, "install_webui_model_from_library", lambda **kwargs: calls.append(("library", kwargs)))
    monkeypatch.setattr(module, "download_file", lambda **kwargs: calls.append(("download", kwargs)))
    monkeypatch.setattr(module, "get_file_list", lambda path: calls.append(("list", path)) or [model_file])
    monkeypatch.setattr(module, "remove_files", lambda path: calls.append(("remove", path)))

    getattr(module, library_func)(tmp_path, model_name="demo", downloader="urllib")
    getattr(module, url_func)(tmp_path, "https://example.test/model.safetensors", "checkpoints", downloader="requests")
    getattr(module, uninstall_func)(tmp_path, "demo", model_type="checkpoints")

    assert calls[0] == (
        "library",
        {"webui_path": tmp_path, "dtype": dtype, "download_resource_type": "modelscope", "model_name": "demo", "model_index": None, "downloader": "urllib", "interactive_mode": False, "list_only": False},
    )
    assert calls[1] == ("download", {"url": "https://example.test/model.safetensors", "path": tmp_path / model_root / "checkpoints", "tool": "requests"})
    assert calls[2] == ("list", tmp_path / model_root / "checkpoints")
    assert calls[3] == ("remove", model_file)

    monkeypatch.setattr(module, "get_file_list", lambda _path: [])
    with pytest.raises(FileNotFoundError):
        getattr(module, uninstall_func)(tmp_path, "missing", model_type="checkpoints")
