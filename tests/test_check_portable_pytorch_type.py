import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT_PATH = Path(__file__).parents[1] / ".github" / "check_portable_pytorch_type.py"
SPEC = importlib.util.spec_from_file_location("check_portable_pytorch_type", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
check_portable_pytorch_type = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_portable_pytorch_type)


def _fake_torch(
    version,
    *,
    cuda=None,
    hip=None,
    mps_built=False,
):
    return SimpleNamespace(
        __version__=version,
        version=SimpleNamespace(__version__=version, cuda=cuda, hip=hip),
        backends=SimpleNamespace(mps=SimpleNamespace(is_built=lambda: mps_built)),
    )


@pytest.mark.parametrize(
    ("software_name", "expected"),
    [
        ("comfyui_cuda", "cuda"),
        ("comfyui_rocm", "rocm"),
        ("comfyui_xpu", "xpu"),
        ("comfyui_mps", "mps"),
    ],
)
def test_get_expected_pytorch_type(software_name, expected):
    assert check_portable_pytorch_type.get_expected_pytorch_type(software_name) == expected


@pytest.mark.parametrize(
    ("torch_module", "platform", "expected"),
    [
        (_fake_torch("2.9.1+cu130", cuda="13.0"), "win32", "cuda"),
        (_fake_torch("2.9.1+rocm7.2.1", hip="7.2.1"), "win32", "rocm"),
        (_fake_torch("2.9.1+xpu"), "win32", "xpu"),
        (_fake_torch("2.9.1", mps_built=True), "darwin", "mps"),
        (_fake_torch("2.9.1+cpu"), "linux", "cpu"),
        (_fake_torch("2.9.1"), "linux", "unknown"),
    ],
)
def test_detect_pytorch_type(torch_module, platform, expected):
    info = check_portable_pytorch_type.detect_pytorch_type(torch_module, platform=platform)

    assert info.detected_type == expected


def test_validate_pytorch_type_rejects_mismatch():
    with pytest.raises(RuntimeError, match="expected rocm, detected cuda"):
        check_portable_pytorch_type.validate_pytorch_type(
            "comfyui_rocm",
            _fake_torch("2.9.1+cu130", cuda="13.0"),
            platform="win32",
        )


def test_get_expected_pytorch_type_rejects_unknown_suffix():
    with pytest.raises(ValueError, match="must end with"):
        check_portable_pytorch_type.get_expected_pytorch_type("comfyui")


def test_finalize_action_checks_pytorch_before_archive():
    action_path = Path(__file__).parents[1] / ".github" / "actions" / "finalize-portable" / "action.yml"
    action = action_path.read_text(encoding="utf-8")

    check_index = action.index("- name: Check portable PyTorch type")
    docs_index = action.index("- name: Make docs")
    archive_index = action.index("- name: Archive")

    assert check_index < docs_index < archive_index
