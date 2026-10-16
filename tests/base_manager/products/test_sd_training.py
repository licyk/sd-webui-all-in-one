"""SD Trainer / SD Scripts 管理器测试"""

import pytest

from sd_webui_all_in_one.base_manager import sd_scripts_base, sd_trainer_base
from tests.base_manager.products.helpers import implementation_module, patch_common_install_deps


def test_sd_trainer_next_branch_metadata():
    assert "sd_trainer_next_main" in sd_trainer_base.SD_TRAINER_BRANCH_LIST

    branch_info = [x for x in sd_trainer_base.SD_TRAINER_BRANCH_INFO_DICT if x["dtype"] == "sd_trainer_next_main"][0]

    assert branch_info == {
        "name": "wochenlong - SD Trainer Next 分支",
        "dtype": "sd_trainer_next_main",
        "url": "https://github.com/wochenlong/lora-scripts-next",
        "branch": "main",
        "use_submodule": True,
    }


@pytest.mark.parametrize(
    ("module", "install_func", "branch_list_attr", "branch_info_attr", "branch_name", "root_file", "expected_dtype"),
    [
        (sd_scripts_base, "install_sd_scripts", "SD_SCRIPTS_BRANCH_LIST", "SD_SCRIPTS_BRANCH_INFO_DICT", "sd_scripts_demo", "requirements.txt", "sd_scripts"),
        (sd_trainer_base, "install_sd_trainer", "SD_TRAINER_BRANCH_LIST", "SD_TRAINER_BRANCH_INFO_DICT", "sd_trainer_demo", "requirements.txt", "sd_trainer"),
    ],
)
def test_install_sd_training_products_orchestrate_common_flow(monkeypatch, tmp_path, module, install_func, branch_list_attr, branch_info_attr, branch_name, root_file, expected_dtype):
    calls = []
    implementation = implementation_module(module, install_func)
    (tmp_path / root_file).write_text("demo\n", encoding="utf-8")
    branch_info = {"name": "Demo", "dtype": branch_name, "url": "https://github.com/example/product", "branch": "demo", "use_submodule": True}
    monkeypatch.setattr(implementation, branch_list_attr, [branch_name])
    monkeypatch.setattr(implementation, branch_info_attr, [branch_info])
    git_config_path = patch_common_install_deps(monkeypatch, implementation, calls, tmp_path)

    getattr(module, install_func)(tmp_path, install_branch=branch_name, use_uv=False, no_pre_download_model=False)

    assert calls[0] == ("clone", {"repo": branch_info["url"], "path": tmp_path})
    assert calls[1] == ("submodule", tmp_path)
    assert calls[2] == ("switch", {"path": tmp_path, "branch": "demo", "new_url": branch_info["url"], "recurse_submodules": True})
    assert calls[3][0] == "pytorch"
    assert calls[4] == ("requirements", {"path": tmp_path / root_file, "use_uv": False, "custom_env": {"PIP": "True", "GIT_CONFIG_GLOBAL": git_config_path}, "cwd": tmp_path})
    assert calls[5][0] == "model"
    assert calls[5][1]["dtype"] == expected_dtype

    with pytest.raises(ValueError):
        getattr(module, install_func)(tmp_path, install_branch="missing")


def test_sd_scripts_install_exports_requirements_from_pyproject(monkeypatch, tmp_path):
    calls = []
    implementation = implementation_module(sd_scripts_base, "install_sd_scripts")
    (tmp_path / "pyproject.toml").write_text("[project]\ndependencies=['demo']\n", encoding="utf-8")
    branch_info = {"name": "Demo", "dtype": "sd_scripts_demo", "url": "https://github.com/example/product", "branch": "demo", "use_submodule": False}
    monkeypatch.setattr(implementation, "SD_SCRIPTS_BRANCH_LIST", ["sd_scripts_demo"])
    monkeypatch.setattr(implementation, "SD_SCRIPTS_BRANCH_INFO_DICT", [branch_info])
    patch_common_install_deps(monkeypatch, implementation, calls, tmp_path)
    monkeypatch.setattr(
        implementation, "export_requirements_from_toml_config", lambda toml_path, save_path: calls.append(("export", toml_path, save_path)) or save_path.write_text("demo\n", encoding="utf-8")
    )

    sd_scripts_base.install_sd_scripts(tmp_path, install_branch="sd_scripts_demo", no_pre_download_model=True)

    assert any(call[0] == "export" for call in calls)
    requirement_call = [call for call in calls if call[0] == "requirements"][0]
    assert requirement_call[1]["path"].name == "requirements.txt"
    assert requirement_call[1]["path"].parent != tmp_path
