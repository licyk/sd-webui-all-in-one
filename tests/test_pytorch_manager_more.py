import pytest

from sd_webui_all_in_one.pytorch_manager import mirror_selector
from sd_webui_all_in_one.pytorch_manager import version_manager


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
        ("2.8.0", "win32", "rocm_win"),
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


def test_export_and_find_latest_pytorch_info(monkeypatch):
    data = [
        {
            "name": "CPU unpinned",
            "dtype": "cpu",
            "platform": ["linux"],
            "torch_ver": "torch torchvision torchaudio",
        },
        {"name": "CPU old", "dtype": "cpu", "platform": ["linux"], "torch_ver": "torch==2.0.0"},
        {"name": "CPU new unsupported device", "dtype": "cpu", "platform": ["linux"], "torch_ver": "torch==2.9.0"},
        {"name": "CUDA win", "dtype": "cu128", "platform": ["win32"], "torch_ver": "torch==2.0.0"},
        {"name": "CUDA linux", "dtype": "cu128", "platform": ["linux"], "torch_ver": "torch==2.7.0"},
    ]
    monkeypatch.setattr(version_manager, "PYTORCH_DOWNLOAD_DICT", data)
    monkeypatch.setattr(version_manager.sys, "platform", "linux")
    monkeypatch.setattr(version_manager, "get_avaliable_pytorch_device_type", lambda: ["cu128"])
    monkeypatch.setattr(version_manager, "SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY", False)

    exported = version_manager.export_pytorch_list()
    assert [item["supported"] for item in exported] == [False, False, False, False, True]
    assert all("supported" not in item for item in data)
    assert version_manager.find_latest_pytorch_info("cu128")["name"] == "CUDA linux"
    with pytest.raises(ValueError, match="当前平台不支持 PyTorch 类型"):
        version_manager.find_latest_pytorch_info("cpu")

    monkeypatch.setattr(version_manager, "get_avaliable_pytorch_device_type", lambda: ["cpu"])
    assert version_manager.find_latest_pytorch_info("cpu")["name"] == "CPU new unsupported device"

    monkeypatch.setattr(version_manager, "SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY", True)
    assert [item["supported"] for item in version_manager.export_pytorch_list()] == [True, True, True, False, True]

    with pytest.raises(ValueError, match="PyTorch 类型不存在"):
        version_manager.find_latest_pytorch_info("missing")


@pytest.mark.parametrize(
    ("dtype", "expected"),
    [
        ("ipex_legacy_arc", "Torch 2.1.0 post"),
        ("cu132", "Torch 2.12.0 CUDA"),
    ],
)
def test_find_latest_pytorch_info_parses_pep440_torch_versions(monkeypatch, dtype, expected):
    data = [
        {
            "name": "Torch 2.0.0 alpha",
            "dtype": "ipex_legacy_arc",
            "platform": ["linux"],
            "torch_ver": "torch==2.0.0a0+gite9ebda2 torchvision==0.15.2a0",
        },
        {
            "name": "Torch 2.0.1 alpha",
            "dtype": "ipex_legacy_arc",
            "platform": ["linux"],
            "torch_ver": "torch==2.0.1a0 torchvision==0.15.2a0",
        },
        {
            "name": "Torch 2.1.0 post",
            "dtype": "ipex_legacy_arc",
            "platform": ["linux"],
            "torch_ver": "torch==2.1.0.post0 torchvision==0.16.0.post0",
        },
        {
            "name": "Torch 2.11.0 CUDA",
            "dtype": "cu132",
            "platform": ["linux"],
            "torch_ver": "torch==2.11.0+cu132 torchvision==0.26.0+cu132",
        },
        {
            "name": "Torch 2.12.0 CUDA",
            "dtype": "cu132",
            "platform": ["linux"],
            "torch_ver": "torch==2.12.0+cu132 torchvision==0.27.0+cu132",
        },
    ]
    monkeypatch.setattr(version_manager, "PYTORCH_DOWNLOAD_DICT", data)
    monkeypatch.setattr(version_manager.sys, "platform", "linux")
    monkeypatch.setattr(version_manager, "get_avaliable_pytorch_device_type", lambda: [dtype])
    monkeypatch.setattr(version_manager, "SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY", False)

    assert version_manager.find_latest_pytorch_info(dtype)["name"] == expected


def test_query_pytorch_info_index_boundaries(monkeypatch):
    data = [
        {"name": "one", "dtype": "cpu", "platform": ["linux"], "torch_ver": "torch==1.0.0"},
        {"name": "two", "dtype": "cpu", "platform": ["linux"], "torch_ver": "torch==2.0.0"},
    ]
    monkeypatch.setattr(version_manager, "PYTORCH_DOWNLOAD_DICT", data)

    assert version_manager.query_pytorch_info_from_library(pytorch_index=1) is data[0]
    assert version_manager.query_pytorch_info_from_library(pytorch_name="two") is data[1]
    with pytest.raises(ValueError, match="超出范围"):
        version_manager.query_pytorch_info_from_library(pytorch_index=3)
    with pytest.raises(FileNotFoundError):
        version_manager.query_pytorch_info_from_library(pytorch_name="missing")
