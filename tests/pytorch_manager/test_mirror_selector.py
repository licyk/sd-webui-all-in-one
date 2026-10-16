"""PyTorch 镜像源选择测试"""

import pytest

from sd_webui_all_in_one.pytorch_manager import mirror_selector
from sd_webui_all_in_one.pytorch_manager import version_manager as torch_versions


def test_pytorch_mirror_type_boundaries(monkeypatch):
    monkeypatch.setattr(mirror_selector, "get_cuda_comp_cap", lambda: 8.9)
    monkeypatch.setattr(mirror_selector, "get_cuda_version", lambda: 12.4)
    monkeypatch.setattr(mirror_selector.sys, "platform", "linux")

    assert mirror_selector.get_pytorch_mirror_type_cuda("1.13.1") == "all"
    assert mirror_selector.get_pytorch_mirror_type_cuda("2.4.1") == "cu124"
    assert mirror_selector.get_pytorch_mirror_type("2.7.0", "cuda") == "cu128"
    assert mirror_selector.get_pytorch_mirror_type_rocm("2.4.0") == "rocm6.1"
    assert mirror_selector.get_pytorch_mirror_type_rocm("2.10.0") == "rocm7.1"
    assert mirror_selector.get_pytorch_mirror_type_rocm("2.12.0") == "rocm7.2"
    monkeypatch.setattr(mirror_selector.sys, "platform", "win32")
    assert mirror_selector.get_pytorch_mirror_type_rocm("2.4.0") == "all"
    assert mirror_selector.get_pytorch_mirror_type_rocm("2.8.0") == "rocm7"
    assert mirror_selector.get_pytorch_mirror_type_rocm("2.12.0") == "rocm7"
    assert mirror_selector.get_pytorch_mirror_type_ipex("2.0.0") == "ipex_legacy_arc"
    assert mirror_selector.get_pytorch_mirror_type_cpu("2.9.0") == "cpu"


def test_get_pytorch_mirror_and_query_library(monkeypatch):
    monkeypatch.setattr(mirror_selector, "PYTORCH_MIRROR_DICT", {"cpu": ("official-cpu", "index_url")})
    monkeypatch.setattr(mirror_selector, "PYTORCH_MIRROR_NJU_DICT", {"cpu": ("cn-cpu", "index_url")})
    monkeypatch.setattr(mirror_selector, "PYTORCH_ROCM_MIRROR_DICT", {"rocm7": ("rocm-7", "find_links"), "rocm10": ("rocm-10", "index_url")})

    assert mirror_selector.get_pytorch_mirror("cpu") == ("official-cpu", "index_url")
    assert mirror_selector.get_pytorch_mirror("cpu", use_cn_mirror=True) == ("cn-cpu", "index_url")
    assert mirror_selector.get_pytorch_mirror("rocm7") == ("rocm-7", "find_links")
    assert mirror_selector.get_pytorch_mirror("rocm10") == ("rocm-10", "index_url")
    # 旧版类型名称等价于 rocm10
    assert mirror_selector.get_pytorch_mirror("rocm_win") == ("rocm-10", "index_url")
    assert mirror_selector.get_pytorch_mirror("rocm_linux") == ("rocm-10", "index_url")
    with pytest.raises(ValueError):
        mirror_selector.get_pytorch_mirror("missing")

    data = [
        {"name": "Torch CPU", "dtype": "cpu", "platform": ["linux"], "torch_ver": "torch==2.0.0"},
        {"name": "Torch CUDA", "dtype": "cu128", "platform": ["linux"], "torch_ver": "torch==2.8.0"},
    ]
    monkeypatch.setattr(torch_versions, "PYTORCH_DOWNLOAD_DICT", data)

    cpu_info = torch_versions.query_pytorch_info_from_library(pytorch_name="Torch CPU")
    cuda_info = torch_versions.query_pytorch_info_from_library(pytorch_index=2)
    assert cpu_info == data[0]
    assert cpu_info is not data[0]
    assert cuda_info == data[1]
    assert cuda_info is not data[1]
    with pytest.raises(ValueError):
        torch_versions.query_pytorch_info_from_library()
    with pytest.raises(FileNotFoundError):
        torch_versions.query_pytorch_info_from_library(pytorch_name="missing")


@pytest.mark.parametrize(
    ("suffix", "platform_tag", "expected"),
    [
        (" CU128 ", "linux", "cu128"),
        ("rocm6.4", "win32", "rocm7"),
        ("rocm_win", "linux", "rocm10"),
        ("rocm_linux", "win32", "rocm10"),
        ("rocm7", "linux", "rocm7"),
        ("rocm10", "win32", "rocm10"),
        ("rocm7.14.0", "win32", "rocm7"),
        ("rocm7.2.1", "win32", "rocm7"),
        ("rocm10.0.0", "win32", "rocm10"),
        ("rocm7.2", "linux", "rocm7.2"),
        ("rocm7.14", "linux", "rocm7.14"),
        ("rocm7.14.1", "linux", "rocm7"),
        ("rocm7.13.0", "linux", "rocm7"),
        ("rocm10.0.0", "linux", "rocm10"),
        ("ROCm7.10.0a20251015", "linux", "rocm7"),
        ("git7bcf7da", "linux", None),
    ],
)
def test_normalize_pytorch_version_suffix(suffix, platform_tag, expected):
    assert mirror_selector.normalize_pytorch_version_suffix(suffix, platform_tag) == expected


def test_infer_pytorch_device_type_from_versions():
    versions = ["1.0.0", "2.9.0+rocm6.4"]

    assert mirror_selector.infer_pytorch_device_type(versions, "linux") == "rocm6.4"
    assert mirror_selector.infer_pytorch_device_type(["2.12.0+rocm7.14.1"], "linux") == "rocm7"
    assert mirror_selector.infer_pytorch_device_type(["2.12.0+rocm7.14.1"], "win32") == "rocm7"
    assert mirror_selector.infer_pytorch_device_type(["2.13.0+rocm10.0.0"], "linux") == "rocm10"
    assert mirror_selector.infer_pytorch_device_type(["2.13.0+rocm10.0.0"], "win32") == "rocm10"


@pytest.mark.parametrize(
    ("torch_ver", "cuda_version", "cuda_cap", "expected"),
    [
        ("2.3.0", 12.1, 8.9, "cu121"),
        ("2.3.1", 12.2, 8.9, "cu121"),
        ("2.4.0", 12.1, 8.9, "cu121"),
        ("2.4.1", 12.4, 8.9, "cu124"),
        ("2.6.0", 12.4, 8.9, "cu124"),
        ("2.6.0", 12.8, 10.1, "cu128"),
        ("2.7.0", 12.7, 8.9, "cu126"),
        ("2.7.0", 12.8, 8.9, "cu128"),
        ("2.8.0", 12.6, 8.9, "cu126"),
        ("2.8.0", 12.8, 8.9, "cu128"),
        ("2.8.0", 12.9, 8.9, "cu129"),
        ("2.9.0", 12.6, 8.9, "cu126"),
        ("2.9.0", 12.8, 8.9, "cu128"),
        ("2.9.0", 13.0, 8.9, "cu130"),
        ("2.10.0", 12.8, 8.9, "cu128"),
        ("2.10.0", 13.0, 8.9, "cu130"),
    ],
)
def test_cuda_mirror_type_version_capability_matrix(monkeypatch, torch_ver, cuda_version, cuda_cap, expected):
    monkeypatch.setattr(mirror_selector, "get_cuda_version", lambda: cuda_version)
    monkeypatch.setattr(mirror_selector, "get_cuda_comp_cap", lambda: cuda_cap)

    assert mirror_selector.get_pytorch_mirror_type_cuda(torch_ver) == expected


@pytest.mark.parametrize(
    ("torch_ver", "platform", "expected"),
    [
        ("2.3.9", "linux", "all"),
        ("2.4.0", "linux", "rocm6.1"),
        ("2.5.0", "linux", "rocm6.2"),
        ("2.6.0", "linux", "rocm6.2.4"),
        ("2.7.0", "linux", "rocm6.3"),
        ("2.8.0", "linux", "rocm6.4"),
        ("2.10.0", "linux", "rocm7.1"),
        ("2.12.0", "linux", "rocm7.2"),
        ("2.3.9", "win32", "all"),
        ("2.7.1", "win32", "all"),
        ("2.8.0", "win32", "rocm7"),
        ("2.12.0", "win32", "rocm7"),
    ],
)
def test_rocm_mirror_type_platform_and_version_boundaries(monkeypatch, torch_ver, platform, expected):
    monkeypatch.setattr(mirror_selector.sys, "platform", platform)

    assert mirror_selector.get_pytorch_mirror_type_rocm(torch_ver) == expected


@pytest.mark.parametrize(
    ("torch_ver", "expected"),
    [
        ("1.13.1", "all"),
        ("2.0.0", "ipex_legacy_arc"),
        ("2.0.1", "all"),
        ("2.1.0", "ipex_legacy_arc"),
        ("2.5.1", "xpu"),
        ("2.6.0", "xpu"),
    ],
)
def test_ipex_mirror_type_legacy_boundaries(torch_ver, expected):
    assert mirror_selector.get_pytorch_mirror_type_ipex(torch_ver) == expected


@pytest.mark.parametrize(
    ("torch_data", "platform", "expected"),
    [
        ({}, "linux", "cuda"),
        ({"__version__": "2.8.0+cu128"}, "linux", "cuda"),
        ({"__version__": "2.8.0+rocm6.4"}, "linux", "rocm"),
        ({"__version__": "2.8.0+xpu"}, "linux", "xpu"),
        ({"__version__": "2.8.0+cpu"}, "linux", "cpu"),
        ({"__version__": "2.8.0"}, "darwin", "mps"),
        ({"__version__": "2.1.0.post0"}, "linux", "xpu"),
        ({"__version__": "2.8.0"}, "linux", "cuda"),
    ],
)
def test_get_env_pytorch_type_from_torch_version(monkeypatch, torch_data, platform, expected):
    monkeypatch.setattr(mirror_selector, "load_source_directly", lambda name: torch_data if name == "torch.version" else {})
    monkeypatch.setattr(mirror_selector.sys, "platform", platform)

    assert mirror_selector.get_env_pytorch_type() == expected


def test_get_pytorch_mirror_prefers_requested_source_and_rocm_fallback(monkeypatch):
    monkeypatch.setattr(mirror_selector, "PYTORCH_MIRROR_DICT", {"cpu": ("official", "index_url")})
    monkeypatch.setattr(mirror_selector, "PYTORCH_MIRROR_NJU_DICT", {"cpu": ("cn", "index_url")})
    monkeypatch.setattr(mirror_selector, "PYTORCH_ROCM_MIRROR_DICT", {"rocm6.4": ("rocm", "find_links")})

    assert mirror_selector.get_pytorch_mirror("cpu") == ("official", "index_url")
    assert mirror_selector.get_pytorch_mirror("cpu", use_cn_mirror=True) == ("cn", "index_url")
    assert mirror_selector.get_pytorch_mirror("rocm6.4", use_cn_mirror=True) == ("rocm", "find_links")

    with pytest.raises(ValueError, match="missing"):
        mirror_selector.get_pytorch_mirror("missing")
