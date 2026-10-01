import ast
import importlib
from pathlib import Path

import pytest

import sd_webui_all_in_one_hotpatcher_ext

EXT_ROOT = Path(sd_webui_all_in_one_hotpatcher_ext.__file__).resolve().parent

# 各扩展包对外导出的符号。新增或调整公开 API 时需要同步更新这里。
EXPECTED_EXPORTS = {
    "comfyui_auto_port": {
        "TARGET_MODULE",
        "adjust_comfyui_default_port",
        "apply_from_config",
        "is_comfyui_auto_port_patch_registered",
        "patch_comfyui_auto_port",
    },
    "extension_index": {
        "A1111_EXTENSION_INDEX_AUTO",
        "A1111_EXTENSION_INDEX_RAW_FILE_PATH",
        "A1111_EXTENSION_INDEX_URLS",
        "COMFYUI_MANAGER_RAW_FILE_PATH",
        "COMFYUI_MANAGER_RAW_PREFIX",
        "apply_from_config",
        "patch_extension_index_a1111",
        "patch_extension_index_comfyui_manager",
        "resolve_a1111_extension_index_url",
        "resolve_comfyui_manager_channel_prefix",
    },
    "hf_endpoint_mirror": {
        "HUGGINGFACE_URL_PATTERN",
        "apply_from_config",
        "apply_mirror",
        "compare_sha256",
        "load_file_from_url",
        "patch_comfyui_manager_model_downloads",
        "patch_comfyui_wd14_tagger",
        "patch_sd_webui_load_file_from_url",
        "patch_torchhub",
        "patch_torchvision",
        "rewrite_huggingface_url",
    },
    "sd_trainer_browser_order": {
        "BrowserRequest",
        "DEFAULT_MAIN_WAIT_TIMEOUT",
        "DEFAULT_MONITOR_DELAY",
        "TARGET_FUNCTION",
        "TARGET_MODULE",
        "apply_from_config",
        "is_sd_trainer_browser_order_patch_registered",
        "is_sd_trainer_next_application",
        "order_browser_requests",
        "patch_sd_trainer_browser_order",
        "replay_browser_requests",
    },
    "uv_pip": {
        "apply_from_config",
        "is_uv_patch_installed",
        "patch_uv_to_subprocess",
        "preprocess_command",
        "unpatch_uv_to_subprocess",
    },
    "xformers_cutlass": {
        "TARGET_CAPABILITY",
        "apply_cutlass_cuda_capability_patch",
        "apply_from_config",
        "is_xformers_cutlass_patch_active",
        "patch_xformers_cutlass_cuda_capability",
        "should_patch_xformers_cutlass",
    },
    "zluda": {
        "apply_from_config",
        "apply_torch_zluda_timer_hotfix",
        "apply_zluda_compat",
        "apply_zluda_library",
    },
}


def _extension_names():
    return sorted(path.parent.name for path in EXT_ROOT.glob("*/__init__.py"))


def test_every_extension_has_pinned_exports():
    assert _extension_names() == sorted(EXPECTED_EXPORTS)


@pytest.mark.parametrize("name", sorted(EXPECTED_EXPORTS))
def test_extension_init_only_reexports(name):
    tree = ast.parse((EXT_ROOT / name / "__init__.py").read_text(encoding="utf-8"))
    body = tree.body
    if ast.get_docstring(tree) is not None:
        body = body[1:]

    for node in body:
        if isinstance(node, ast.ImportFrom):
            assert node.level == 1, f"{name}/__init__.py 只能从同包子模块导入"
            continue
        is_all = isinstance(node, ast.Assign) and [getattr(target, "id", None) for target in node.targets] == ["__all__"]
        assert is_all, f"{name}/__init__.py 第 {node.lineno} 行包含实现代码, 应移入子模块"


@pytest.mark.parametrize("name", sorted(EXPECTED_EXPORTS))
def test_extension_exports_are_unchanged(name):
    module = importlib.import_module(f"sd_webui_all_in_one_hotpatcher_ext.{name}")

    assert set(module.__all__) == EXPECTED_EXPORTS[name]
    assert len(module.__all__) == len(set(module.__all__))
    for export in module.__all__:
        assert hasattr(module, export)
