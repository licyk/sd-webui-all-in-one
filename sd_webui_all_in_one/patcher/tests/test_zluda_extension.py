import importlib
import sys
import textwrap

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher_ext.zluda import (
    apply_from_config,
    apply_torch_zluda_timer_hotfix,
    apply_zluda_compat,
)


@pytest.fixture(autouse=True)
def clean_import_state():
    uninstall_import_hook()
    monkey_zoo.clear()
    before_path = list(sys.path)
    yield
    uninstall_import_hook()
    monkey_zoo.clear()
    sys.path[:] = before_path
    for name in list(sys.modules):
        if name == "torch" or name.startswith("torch."):
            sys.modules.pop(name, None)


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def make_fake_torch(tmp_path):
    write_file(
        tmp_path / "torch" / "__init__.py",
        """
        from . import backends
        """,
    )
    write_file(tmp_path / "torch" / "backends" / "__init__.py", "from . import cuda, cudnn\n")
    write_file(tmp_path / "torch" / "backends" / "cudnn.py", "enabled = True\n")
    write_file(
        tmp_path / "torch" / "backends" / "cuda.py",
        """
        calls = []

        def enable_flash_sdp(enabled):
            calls.append(("flash", enabled))
            return enabled

        def enable_math_sdp(enabled):
            calls.append(("math", enabled))
            return enabled

        def enable_mem_efficient_sdp(enabled):
            calls.append(("mem", enabled))
            return enabled
        """,
    )
    importlib.invalidate_caches()


def test_apply_zluda_compat_patches_torch_backend_flags(tmp_path):
    make_fake_torch(tmp_path)
    sys.path.insert(0, str(tmp_path))

    apply_zluda_compat()
    torch = importlib.import_module("torch")

    assert torch.backends.cudnn.enabled is False
    assert ("flash", False) in torch.backends.cuda.calls  # ty: ignore[unresolved-attribute]
    assert ("math", True) in torch.backends.cuda.calls  # ty: ignore[unresolved-attribute]
    assert ("mem", False) in torch.backends.cuda.calls  # ty: ignore[unresolved-attribute]


def test_apply_zluda_compat_forces_cuda_sdp_toggles_false(tmp_path):
    make_fake_torch(tmp_path)
    sys.path.insert(0, str(tmp_path))

    apply_zluda_compat()
    cuda = importlib.import_module("torch.backends.cuda")

    cuda.enable_flash_sdp(True)
    cuda.enable_mem_efficient_sdp(True)

    assert cuda.calls[-2:] == [("flash", False), ("mem", False)]  # ty: ignore[unresolved-attribute]


def test_apply_torch_zluda_timer_hotfix_rewrites_cpp_extension_source(tmp_path):
    write_file(tmp_path / "torch" / "__init__.py", "")
    write_file(tmp_path / "torch" / "utils" / "__init__.py", "")
    write_file(
        tmp_path / "torch" / "utils" / "cpp_extension.py",
        """
        ROCM_HOME = "rocm"
        IS_WINDOWS = True
        HIP_HOME = _join_rocm_home('hip') if ROCM_HOME else None

        def check():
            if False:
                pass
            elif IS_WINDOWS:
                raise RuntimeError("windows")
            return HIP_HOME

        def _join_rocm_home(name):
            return ROCM_HOME + "/" + name
        """,
    )
    sys.path.insert(0, str(tmp_path))

    apply_torch_zluda_timer_hotfix()
    module = importlib.import_module("torch.utils.cpp_extension")

    assert module.HIP_HOME == "rocm"
    assert module.check() == "rocm"  # ty: ignore[unresolved-attribute]


def test_apply_from_config_enables_selected_zluda_patches(tmp_path):
    make_fake_torch(tmp_path)
    sys.path.insert(0, str(tmp_path))

    apply_from_config({"compat": True})
    torch = importlib.import_module("torch")

    assert torch.backends.cudnn.enabled is False
