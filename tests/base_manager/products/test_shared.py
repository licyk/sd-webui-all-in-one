"""各 WebUI 管理器的共同行为测试"""

import sys
from typing import Any, cast

import pytest

from sd_webui_all_in_one.base_manager import (
    comfyui_base,
    fooocus_base,
    invokeai_base,
    mizuoto_tts_webui_base,
    qwen_tts_webui_base,
    rvc_next_webui_base,
    sd_scripts_base,
    sd_trainer_base,
    sd_webui_base,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError
from tests.base_manager.products.helpers import implementation_module, use_temp_git_config


@pytest.mark.parametrize(
    ("module", "function_name", "webui_type", "display_name", "supports_extensions", "kernel_package"),
    [
        (sd_webui_base, "check_sd_webui_updates", "sd_webui", "Stable Diffusion WebUI", True, None),
        (comfyui_base, "check_comfyui_updates", "comfyui", "ComfyUI", True, None),
        (fooocus_base, "check_fooocus_updates", "fooocus", "Fooocus", False, None),
        (invokeai_base, "check_invokeai_updates", "invokeai", "InvokeAI", True, "invokeai"),
        (sd_trainer_base, "check_sd_trainer_updates", "sd_trainer", "SD Trainer", False, None),
        (sd_scripts_base, "check_sd_scripts_updates", "sd_scripts", "SD Scripts", False, None),
        (qwen_tts_webui_base, "check_qwen_tts_webui_updates", "qwen_tts_webui", "Qwen TTS WebUI", False, None),
        (rvc_next_webui_base, "check_rvc_next_webui_updates", "rvc_next_webui", "RVC Next WebUI", False, None),
        (mizuoto_tts_webui_base, "check_mizuoto_tts_webui_updates", "mizuoto_tts_webui", "Mizuoto TTS WebUI", False, None),
    ],
)
def test_product_update_checkers_delegate_with_product_capabilities(
    monkeypatch,
    tmp_path,
    module,
    function_name,
    webui_type,
    display_name,
    supports_extensions,
    kernel_package,
):
    calls = []
    sentinel = object()

    def fake_check(*args, **kwargs):
        calls.append((args, kwargs))
        return sentinel

    monkeypatch.setattr(implementation_module(module, function_name), "check_webui_updates", fake_check)
    result = getattr(module, function_name)(tmp_path)

    assert result is sentinel
    args, kwargs = calls[0]
    assert args == (webui_type, display_name, tmp_path)
    assert (kwargs.get("extension_loader") is not None) is supports_extensions
    assert kwargs.get("kernel_package_name") == kernel_package


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
    monkeypatch.setattr(implementation_module(module, function_name), "copy_files", lambda src, dst: calls.append((src, dst)))

    getattr(module, function_name)(tmp_path, resource_type)

    assert calls[0] == (getattr(module, expected_source_attr), tmp_path / target_file)


def test_product_config_installers_skip_existing_and_reject_unknown(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(implementation_module(fooocus_base, "install_fooocus_config"), "copy_files", lambda src, dst: calls.append((src, dst)))
    (tmp_path / "presets").mkdir()
    (tmp_path / "presets" / "sd_webui_all_in_one.json").write_text("existing", encoding="utf-8")

    fooocus_base.install_fooocus_config(tmp_path, "modelscope")
    assert calls == [(fooocus_base.FOOOCUS_TRANSLATE_ZH_PATH, tmp_path / "language" / "zh.json")]

    (tmp_path / "language").mkdir()
    (tmp_path / "language" / "zh.json").write_text("{}", encoding="utf-8")
    (tmp_path / "presets" / "sd_webui_all_in_one.json").unlink()
    with pytest.raises(ValueError):
        fooocus_base.install_fooocus_config(tmp_path, cast(Any, "unknown"))

    qwen_tts_webui_base.install_qwen_tts_webui_config(tmp_path, False)

    with pytest.raises(ValueError):
        qwen_tts_webui_base.install_qwen_tts_webui_config(tmp_path, cast(Any, "unknown"))


def test_launch_helpers_build_env_and_delegate(monkeypatch, tmp_path):
    calls = []
    git_config_path = use_temp_git_config(monkeypatch, tmp_path)

    def fake_git_config(**kwargs):
        return {**kwargs["origin_env"], "GIT_CONFIG_GLOBAL": git_config_path}

    def fake_hf(**kwargs):
        env = kwargs["origin_env"].copy()
        env["HF_ENDPOINT"] = "https://hf.example"
        return env

    for module in (comfyui_base, fooocus_base, qwen_tts_webui_base):
        implementation = implementation_module(module, f"launch_{module.__name__.rsplit('.', 1)[-1].removesuffix('_base')}")
        monkeypatch.setattr(implementation, "apply_git_base_config_and_github_mirror", fake_git_config)
        monkeypatch.setattr(implementation, "apply_hf_mirror", fake_hf)
        monkeypatch.setattr(implementation, "get_pypi_mirror_config", lambda use_cn_mirror=False, origin_env=None: {"PIP": "1", **(origin_env or {})})
        monkeypatch.setattr(implementation, "get_cuda_malloc_var", lambda: "backend:cudaMallocAsync")
        monkeypatch.setattr(implementation, "apply_pytorch_alloc_conf", lambda config, origin_env=None: {"ALLOC": config, **(origin_env or {})})
        monkeypatch.setattr(implementation, "apply_hotpatcher_launch_env", lambda **kwargs: {"HOTPATCH": str(kwargs["enabled"]), **kwargs["origin_env"]})
        monkeypatch.setattr(implementation, "launch_webui", lambda **kwargs: calls.append((module.__name__, kwargs)))

    fooocus_runtime = implementation_module(fooocus_base, "launch_fooocus")
    monkeypatch.setattr(fooocus_runtime, "check_fooocus_hf_mirror_arg", lambda _path: True)

    comfyui_base.launch_comfyui(tmp_path / "comfy", launch_args=["--listen"], use_hf_mirror=True, use_cuda_malloc=True, enable_hotpatcher=True)
    fooocus_base.launch_fooocus(tmp_path / "fooocus", launch_args=["--preset", "x"], use_hf_mirror=True, use_cuda_malloc=True)
    qwen_tts_webui_base.launch_qwen_tts_webui(tmp_path / "qwen", launch_args=[], use_hf_mirror=True, use_cuda_malloc=True)
    info = comfyui_base.prepare_comfyui_launch(tmp_path / "comfy", launch_args=["--listen"], use_hf_mirror=True, use_cuda_malloc=True, enable_hotpatcher=True)

    assert calls[0][1]["launch_script"] == "main.py"
    assert calls[0][1]["webui_name"] == "ComfyUI"
    assert calls[0][1]["custom_env"]["HOTPATCH"] == "True"
    assert calls[1][1]["launch_args"] == ["--preset", "x", "--hf-mirror", "https://hf.example"]
    assert calls[2][1]["launch_script"] == "launch.py"
    assert info.launch_script == "main.py"
    assert info.launch_args == ["--listen"]
    assert info.custom_env["HOTPATCH"] == "True"


@pytest.mark.parametrize(
    ("module", "check_func", "req_name", "missing_message"),
    [
        (fooocus_base, "check_fooocus_env", "Fooocus", "Fooocus"),
        (sd_scripts_base, "check_sd_scripts_env", "SD Scripts", "SD Scripts"),
        (sd_trainer_base, "check_sd_trainer_env", "SD Trainer", "SD Trainer"),
    ],
)
def test_product_env_checks_aggregate_failures(monkeypatch, tmp_path, module, check_func, req_name, missing_message):
    implementation = implementation_module(module, check_func)
    git_config_path = (tmp_path / ".gitconfig").as_posix()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", git_config_path)
    (tmp_path / "requirements.txt").write_text("demo\n", encoding="utf-8")
    calls = []

    def ok_task(**kwargs):
        calls.append(("ok", kwargs))

    def bad_task(**kwargs):
        calls.append(("bad", kwargs))
        raise RuntimeError("task bad")

    monkeypatch.setattr(implementation, "apply_git_base_config_and_github_mirror", lambda **kwargs: {**kwargs["origin_env"], "GIT_CONFIG_GLOBAL": git_config_path})
    monkeypatch.setattr(implementation, "get_pypi_mirror_config", lambda use_cn_mirror, origin_env=None: {"PIP": str(use_cn_mirror), **(origin_env or {})})
    monkeypatch.setattr(implementation, "py_dependency_checker", bad_task)
    monkeypatch.setattr(implementation, "fix_torch_libomp", ok_task)
    monkeypatch.setattr(implementation, "check_torch_version", ok_task)
    monkeypatch.setattr(implementation, "check_onnxruntime_gpu", ok_task)
    monkeypatch.setattr(implementation, "check_numpy", ok_task)
    if hasattr(implementation, "check_accelerate_bin"):
        monkeypatch.setattr(implementation, "check_accelerate_bin", ok_task)

    with pytest.raises(AggregateError) as exc:
        getattr(module, check_func)(tmp_path, use_uv=False, use_pypi_mirror=True)

    assert len(exc.value.exceptions) == 1
    assert calls[0][0] == "bad"
    assert calls[0][1]["requirement_path"].name == "requirements.txt"
    assert calls[0][1]["name"] == req_name
    assert calls[0][1]["custom_env"]["GIT_CONFIG_GLOBAL"] == git_config_path

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
    git_config_path = (tmp_path / ".gitconfig").as_posix()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", git_config_path)
    switch_implementation = implementation_module(module, switch_func)
    update_func = getattr(module, switch_func.replace("switch_", "update_").replace("_branch", ""))
    update_implementation = sys.modules[update_func.__module__]
    branch_info = {"name": "Demo", "dtype": branch_name, "url": "https://github.com/example/product", "branch": "demo", "use_submodule": True}
    monkeypatch.setattr(switch_implementation, branch_list_attr, [branch_name])
    monkeypatch.setattr(switch_implementation, branch_info_attr, [branch_info])
    monkeypatch.setattr(switch_implementation, "apply_git_base_config_and_github_mirror", lambda **kwargs: {**kwargs["origin_env"], "GIT_CONFIG_GLOBAL": git_config_path})
    monkeypatch.setattr(switch_implementation.git_warpper, "switch_branch", lambda **kwargs: calls.append(("switch", kwargs)))
    monkeypatch.setattr(update_implementation.git_warpper, "update", lambda path: calls.append(("update", path)))

    getattr(module, switch_func)(tmp_path, branch=branch_name, use_github_mirror=True, custom_github_mirror="mirror")
    assert calls[0] == ("switch", {"path": tmp_path, "branch": "demo", "new_url": "https://github.com/example/product", "recurse_submodules": True})

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
    implementation = implementation_module(module, library_func)
    model_file = tmp_path / model_root / "checkpoints" / "demo.safetensors"
    model_file.parent.mkdir(parents=True)
    model_file.write_text("model", encoding="utf-8")

    monkeypatch.setattr(implementation, "install_webui_model_from_library", lambda **kwargs: calls.append(("library", kwargs)))
    monkeypatch.setattr(implementation, "download_file", lambda **kwargs: calls.append(("download", kwargs)))
    monkeypatch.setattr(implementation, "get_file_list", lambda path: calls.append(("list", path)) or [model_file])
    monkeypatch.setattr(implementation, "remove_files", lambda path: calls.append(("remove", path)))

    getattr(module, library_func)(tmp_path, model_name="demo", downloader="urllib")
    getattr(module, url_func)(tmp_path, "https://example.test/model.safetensors", "checkpoints", downloader="requests")
    getattr(module, uninstall_func)(tmp_path, "demo", model_type="checkpoints")

    assert calls[0] == (
        "library",
        {
            "webui_path": tmp_path,
            "dtype": dtype,
            "download_resource_type": "modelscope",
            "model_name": "demo",
            "model_index": None,
            "downloader": "urllib",
            "interactive_mode": False,
            "list_only": False,
        },
    )
    assert calls[1] == ("download", {"url": "https://example.test/model.safetensors", "path": tmp_path / model_root / "checkpoints", "tool": "requests"})
    assert calls[2] == ("list", tmp_path / model_root / "checkpoints")
    assert calls[3] == ("remove", model_file)

    monkeypatch.setattr(implementation, "get_file_list", lambda _path: [])
    with pytest.raises(FileNotFoundError):
        getattr(module, uninstall_func)(tmp_path, "missing", model_type="checkpoints")
