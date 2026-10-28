"""PyTorch 版本表查询测试"""

import pytest

from sd_webui_all_in_one.pytorch_manager import version_manager


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
    monkeypatch.setattr(version_manager, "get_available_pytorch_device_type", lambda: ["cu128"])
    monkeypatch.setattr(version_manager, "SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY", False)

    exported = version_manager.export_pytorch_list()
    assert [item["supported"] for item in exported] == [False, False, False, False, True]
    assert all("supported" not in item for item in data)
    exported[0]["platform"].append("darwin")
    assert data[0]["platform"] == ["linux"]
    assert version_manager.find_latest_pytorch_info("cu128")["name"] == "CUDA linux"
    with pytest.raises(ValueError, match="当前平台不支持 PyTorch 类型"):
        version_manager.find_latest_pytorch_info("cpu")

    monkeypatch.setattr(version_manager, "get_available_pytorch_device_type", lambda: ["cpu"])
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
    monkeypatch.setattr(version_manager, "get_available_pytorch_device_type", lambda: [dtype])
    monkeypatch.setattr(version_manager, "SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY", False)

    assert version_manager.find_latest_pytorch_info(dtype)["name"] == expected


def test_query_pytorch_info_index_boundaries(monkeypatch):
    data = [
        {"name": "one", "dtype": "cpu", "platform": ["linux"], "torch_ver": "torch==1.0.0"},
        {"name": "two", "dtype": "cpu", "platform": ["linux"], "torch_ver": "torch==2.0.0"},
    ]
    monkeypatch.setattr(version_manager, "PYTORCH_DOWNLOAD_DICT", data)

    first = version_manager.query_pytorch_info_from_library(pytorch_index=1)
    second = version_manager.query_pytorch_info_from_library(pytorch_name="two")
    assert first == data[0]
    assert first is not data[0]
    first["platform"].append("win32")
    assert data[0]["platform"] == ["linux"]
    assert second == data[1]
    assert second is not data[1]
    with pytest.raises(ValueError, match="超出范围"):
        version_manager.query_pytorch_info_from_library(pytorch_index=3)
    with pytest.raises(FileNotFoundError):
        version_manager.query_pytorch_info_from_library(pytorch_name="missing")


@pytest.mark.parametrize(
    ("platform", "dtype", "expected_name", "expected_torch_ver", "expected_index"),
    [
        (
            "linux",
            "rocm7",
            "Torch 2.13.0 (ROCm 7.14.0 Linux)",
            "torch[device-all]==2.13.0+rocm7.14.0 torchvision[device-all]==0.28.0+rocm7.14.0 torchaudio==2.11.0.2+rocm7.14.0",
            "https://repo.amd.com/rocm/whl-multi-arch",
        ),
        (
            "win32",
            "rocm7",
            "Torch 2.12.0 (ROCm 7.14.1)",
            "torch[device-all]==2.12.0+rocm7.14.1 torchvision[device-all]==0.27.0+rocm7.14.1 torchaudio==2.11.0+rocm7.14.1",
            "https://repo.amd.com/rocm/whl-multi-arch",
        ),
        (
            "linux",
            "rocm10",
            "Torch 2.14.0 (ROCm 10.1.0)",
            "torch[device-all]==2.14.0+rocm10.1.0 torchvision[device-all]==0.29.0a0+rocm10.1.0 torchaudio==2.11.0.3+rocm10.1.0",
            "https://stable.repo.amd.com/rocm/whl-next",
        ),
        (
            "win32",
            "rocm10",
            "Torch 2.14.0 (ROCm 10.1.0)",
            "torch[device-all]==2.14.0+rocm10.1.0 torchvision[device-all]==0.29.0a0+rocm10.1.0 torchaudio==2.11.0.3+rocm10.1.0",
            "https://stable.repo.amd.com/rocm/whl-next",
        ),
        # 旧版类型名称等价于 rocm10
        (
            "linux",
            "rocm_linux",
            "Torch 2.14.0 (ROCm 10.1.0)",
            "torch[device-all]==2.14.0+rocm10.1.0 torchvision[device-all]==0.29.0a0+rocm10.1.0 torchaudio==2.11.0.3+rocm10.1.0",
            "https://stable.repo.amd.com/rocm/whl-next",
        ),
        (
            "win32",
            "rocm_win",
            "Torch 2.14.0 (ROCm 10.1.0)",
            "torch[device-all]==2.14.0+rocm10.1.0 torchvision[device-all]==0.29.0a0+rocm10.1.0 torchaudio==2.11.0.3+rocm10.1.0",
            "https://stable.repo.amd.com/rocm/whl-next",
        ),
    ],
)
def test_find_latest_amd_multi_arch_pytorch_info(monkeypatch, platform, dtype, expected_name, expected_torch_ver, expected_index):
    monkeypatch.setattr(version_manager.sys, "platform", platform)
    monkeypatch.setattr(version_manager, "get_available_pytorch_device_type", lambda: ["all", "rocm7", "rocm10"])

    info = version_manager.find_latest_pytorch_info(dtype)

    assert info["name"] == expected_name
    assert info["torch_ver"] == expected_torch_ver
    assert info["index_mirror"]["official"] == [expected_index]
    assert info["extra_index_mirror"]["official"] == ["https://pypi.python.org/simple"]
    assert info["find_links"]["official"] == []


@pytest.mark.parametrize(
    ("dtype", "expected_name", "expected_torch_ver"),
    [
        ("cpu", "Torch 2.15.0 (CPU)", "torch==2.15.0+cpu torchvision==0.29.2+cpu torchaudio==2.11.1+cpu"),
        ("rocm7.14", "Torch 2.15.0 (ROCm 7.14)", "torch==2.15.0+rocm7.14 torchvision==0.29.2+rocm7.14 torchaudio==2.11.1+rocm7.14"),
        ("rocm10.0", "Torch 2.15.0 (ROCm 10.0)", "torch==2.15.0+rocm10.0 torchvision==0.29.2+rocm10.0 torchaudio==2.11.1+rocm10.0"),
        ("xpu", "Torch 2.15.0 (XPU)", "torch==2.15.0+xpu torchvision==0.29.2+xpu torchaudio==2.11.1+xpu"),
        ("cu132", "Torch 2.15.0 (CUDA 13.2)", "torch==2.15.0+cu132 torchvision==0.29.2+cu132 torchaudio==2.11.1+cu132"),
        ("cu134", "Torch 2.15.0 (CUDA 13.4)", "torch==2.15.0+cu134 torchvision==0.29.2+cu134 torchaudio==2.11.1+cu134"),
    ],
)
def test_find_latest_pytorch_2_15_info(monkeypatch, dtype, expected_name, expected_torch_ver):
    from sd_webui_all_in_one.pytorch_manager.mirror_data import PYTORCH_MIRROR_DICT, PYTORCH_MIRROR_NJU_DICT

    monkeypatch.setattr(version_manager.sys, "platform", "linux")
    monkeypatch.setattr(version_manager, "get_available_pytorch_device_type", lambda: ["all", dtype])

    info = version_manager.find_latest_pytorch_info(dtype)

    assert info["name"] == expected_name
    assert info["torch_ver"] == expected_torch_ver
    assert info["xformers_ver"] is None
    assert info["index_mirror"]["official"] == [f"https://download.pytorch.org/whl/{dtype}"]
    assert info["index_mirror"]["official"] == [PYTORCH_MIRROR_DICT[dtype][0]]
    assert info["index_mirror"]["mirror"] == [PYTORCH_MIRROR_NJU_DICT[dtype][0]]


AMD_MULTI_ARCH_VERSION_TABLE = {
    # (dtype, torch 版本): (torchvision 版本, torchaudio 版本, ROCm 版本, 支持的平台)
    ("rocm7", "2.8.0"): ("0.23.0a0", "2.8.0a0", "7.13.0", ["linux"]),
    ("rocm7", "2.9.1"): ("0.24.0", "2.9.0", "7.13.0", ["win32"]),
    ("rocm7", "2.10.0"): ("0.25.0", "2.10.0", "7.14.1", ["win32", "linux"]),
    ("rocm7", "2.11.0"): ("0.26.0", "2.11.0", "7.14.1", ["win32", "linux"]),
    ("rocm7", "2.12.0"): ("0.27.0", "2.11.0", "7.14.1", ["win32", "linux"]),
    ("rocm7", "2.13.0"): ("0.28.0", "2.11.0.2", "7.14.0", ["linux"]),
    ("rocm10", "2.11.0"): ("0.26.0", "2.11.0", "10.0.0", ["win32", "linux"]),
    ("rocm10", "2.12.0"): ("0.27.0", "2.11.0", "10.0.0", ["win32", "linux"]),
    ("rocm10", "2.13.0"): ("0.28.0", "2.11.0.2", "10.0.0", ["win32", "linux"]),
    ("rocm10", "2.14.0"): ("0.29.0a0", "2.11.0.3", "10.1.0", ["win32", "linux"]),
}


def test_amd_multi_arch_version_table_covers_rocm7_and_rocm10():
    from sd_webui_all_in_one.pytorch_manager.mirror_data import PYTORCH_ROCM_MIRROR_DICT
    from sd_webui_all_in_one.pytorch_manager.version_data import PYTORCH_DOWNLOAD_DICT

    pinned = {}
    for info in PYTORCH_DOWNLOAD_DICT:
        if info["dtype"] not in ("rocm7", "rocm10") or "[device-all]==" not in info["torch_ver"]:
            continue
        torch_spec = info["torch_ver"].split()[0]
        torch_ver = torch_spec.split("==")[1].split("+")[0]
        pinned[(info["dtype"], torch_ver)] = info

    assert set(pinned) == set(AMD_MULTI_ARCH_VERSION_TABLE)
    for (dtype, torch_ver), (vision_ver, audio_ver, rocm_ver, platform) in AMD_MULTI_ARCH_VERSION_TABLE.items():
        info = pinned[(dtype, torch_ver)]
        assert info["torch_ver"] == f"torch[device-all]=={torch_ver}+rocm{rocm_ver} torchvision[device-all]=={vision_ver}+rocm{rocm_ver} torchaudio=={audio_ver}+rocm{rocm_ver}"
        assert info["platform"] == platform
        assert info["xformers_ver"] is None
        assert info["index_mirror"]["official"] == info["index_mirror"]["mirror"] == [PYTORCH_ROCM_MIRROR_DICT[dtype][0]]


def test_amd_multi_arch_types_only_use_device_all_packages():
    from sd_webui_all_in_one.pytorch_manager.version_data import PYTORCH_DOWNLOAD_DICT

    legacy = "Torch 2.9.1 (ROCm 7.2.1 Windows)"
    entries = [info for info in PYTORCH_DOWNLOAD_DICT if info["dtype"] in ("rocm7", "rocm10") and info["name"] != legacy]

    assert {"Torch (ROCm 7)", "Torch (ROCm 10)"} <= {info["name"] for info in entries}
    assert not any(info["dtype"] in ("rocm_linux", "rocm_win") for info in PYTORCH_DOWNLOAD_DICT)
    for info in entries:
        packages = info["torch_ver"].split()
        assert packages[0].startswith("torch[device-all]")
        assert packages[1].startswith("torchvision[device-all]")


def test_unpinned_amd_multi_arch_entries_do_not_mix_in_pypi():
    # 未固定版本时若混入 PyPI 镜像源, uv 的 unsafe-best-match 策略会选中 PyPI 上版本号更高的非 ROCm 版 PyTorch
    for name in ("Torch (ROCm 7)", "Torch (ROCm 10)"):
        info = version_manager.query_pytorch_info_from_library(pytorch_name=name)
        assert info["torch_ver"] == "torch[device-all] torchvision[device-all] torchaudio"
        assert info["extra_index_mirror"] == {"official": [], "mirror": []}


def test_removed_rdna_pytorch_types_are_absent():
    from sd_webui_all_in_one.pytorch_manager.types import PYTORCH_DEVICE_LIST
    from sd_webui_all_in_one.pytorch_manager.version_data import PYTORCH_DOWNLOAD_DICT

    removed = {"rocm_rdna3", "rocm_rdna3.5", "rocm_rdna4"}
    assert removed.isdisjoint(PYTORCH_DEVICE_LIST)
    assert removed.isdisjoint(item["dtype"] for item in PYTORCH_DOWNLOAD_DICT)
    assert {"rocm7", "rocm10", "rocm_linux", "rocm_win"} <= set(PYTORCH_DEVICE_LIST)


def test_legacy_rocm_windows_entry_keeps_radeon_find_links():
    info = version_manager.query_pytorch_info_from_library(pytorch_name="Torch 2.9.1 (ROCm 7.2.1 Windows)")

    assert info["dtype"] == "rocm7"
    assert info["find_links"]["official"] == ["https://repo.radeon.com/rocm/windows/rocm-rel-7.2.1"]


def _torch_entry(name, dtype, torch_ver, xformers_ver=None, platform=("linux", "win32")):
    return {"name": name, "dtype": dtype, "platform": list(platform), "torch_ver": torch_ver, "xformers_ver": xformers_ver}


def test_find_pytorch_info_for_torch_requirement_ranks_table_entries(monkeypatch):
    data = [
        _torch_entry("Torch (CUDA)", "cu130", "torch torchvision"),
        _torch_entry("Torch 2.7.1 (CUDA 12.6)", "cu126", "torch==2.7.1+cu126"),
        _torch_entry("Torch 2.7.1 (CUDA 12.8) + xFormers", "cu128", "torch==2.7.1+cu128", "xformers==0.0.31.post1"),
        _torch_entry("Torch 2.14.0 (CUDA 12.6) + xFormers", "cu126", "torch==2.14.0+cu126", "xformers==0.0.35"),
        _torch_entry("Torch 2.14.0 (CUDA 13.0) + xFormers", "cu130", "torch==2.14.0+cu130", "xformers==0.0.35"),
        _torch_entry("Torch 2.14.0 (CUDA 13.2)", "cu132", "torch==2.14.0+cu132"),
        _torch_entry("Torch 2.15.0 (CUDA 13.2)", "cu132", "torch==2.15.0+cu132"),
        _torch_entry("Torch 2.14.0 (CPU)", "cpu", "torch==2.14.0+cpu"),
    ]
    monkeypatch.setattr(version_manager.sys, "platform", "linux")
    monkeypatch.setattr(version_manager, "PYTORCH_DOWNLOAD_DICT", data)
    monkeypatch.setattr(version_manager, "get_available_pytorch_device_type", lambda: ["all", "cpu", "cu126", "cu128", "cu130", "cu132"])

    def find(specs, preferred="cu130", category="cuda"):
        info = version_manager.find_pytorch_info_for_torch_requirement(category, specs, preferred)
        return None if info is None else info["name"]

    # 首选类型优先于更新的 torch 版本
    assert find([("<", "3.0"), (">=", "2.7.0")]) == "Torch 2.14.0 (CUDA 13.0) + xFormers"
    # 首选类型无匹配时选择最新 torch 版本, 同版本优先包含 xFormers 的组合
    assert find([("~=", "2.7.0")]) == "Torch 2.7.1 (CUDA 12.8) + xFormers"
    assert find([("<", "3.0"), (">=", "2.7.0")], preferred=None) == "Torch 2.15.0 (CUDA 13.2)"
    assert find([("==", "2.14.0")], preferred=None) == "Torch 2.14.0 (CUDA 13.0) + xFormers"
    # 按设备分类过滤, 未固定 torch 版本的条目不参与匹配
    assert find([(">=", "2.7.0")], category="cpu") == "Torch 2.14.0 (CPU)"
    assert find([(">=", "3.0")]) is None


def test_find_pytorch_info_for_torch_requirement_skips_unsupported_entries(monkeypatch):
    data = [
        _torch_entry("Torch 2.14.0 (CUDA 13.0) + xFormers", "cu130", "torch==2.14.0+cu130", "xformers==0.0.35"),
        _torch_entry("Torch 2.11.0 (CUDA 12.8)", "cu128", "torch==2.11.0+cu128"),
    ]
    monkeypatch.setattr(version_manager.sys, "platform", "linux")
    monkeypatch.setattr(version_manager, "PYTORCH_DOWNLOAD_DICT", data)
    monkeypatch.setattr(version_manager, "SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY", False)
    monkeypatch.setattr(version_manager, "get_available_pytorch_device_type", lambda: ["all", "cpu", "cu128"])

    info = version_manager.find_pytorch_info_for_torch_requirement("cuda", [(">=", "2.7.0")], "cu128")

    assert info is not None
    assert info["name"] == "Torch 2.11.0 (CUDA 12.8)"


def test_pytorch_package_extras_come_from_version_table(monkeypatch):
    data = [
        _torch_entry("Torch (ROCm 7)", "rocm7", "torch[device-all] torchvision[device-all] torchaudio"),
        _torch_entry("Torch 2.12.0 (ROCm 7.14.1)", "rocm7", "torch[device-all]==2.12.0+rocm7.14.1 torchvision[device-all]==0.27.0+rocm7.14.1"),
        _torch_entry("Torch 2.9.1 (ROCm 7.2.1 Windows)", "rocm7", "torch==2.9.1+rocm7.2.1"),
        _torch_entry("Torch 2.13.0 (ROCm 10.0.0)", "rocm10", "torch[device-all]==2.13.0+rocm10.0.0 torchvision[device-all]==0.28.0+rocm10.0.0"),
        _torch_entry("Torch 2.14.0 (CUDA 13.0)", "cu130", "torch==2.14.0+cu130"),
    ]
    monkeypatch.setattr(version_manager, "PYTORCH_DOWNLOAD_DICT", data)

    assert version_manager.get_pytorch_package_extras("rocm7") == {"torch": ["device-all"], "torchvision": ["device-all"]}
    assert version_manager.get_pytorch_package_extras("rocm_win") == {"torch": ["device-all"], "torchvision": ["device-all"]}
    assert version_manager.get_pytorch_package_extras("cu130") == {}
    assert version_manager.add_pytorch_package_extras("torch<3.0,>=2.7.0 torchvision", "rocm7") == "torch[device-all]<3.0,>=2.7.0 torchvision[device-all]"
    assert version_manager.add_pytorch_package_extras("Torch[foo]~=2.7.0 torchaudio numpy", "rocm_win") == "Torch[foo,device-all]~=2.7.0 torchaudio numpy"
    assert version_manager.add_pytorch_package_extras("torch<3.0,>=2.7.0 torchvision", "cu130") == "torch<3.0,>=2.7.0 torchvision"


def test_real_version_table_declares_device_all_for_amd_multi_arch_types():
    for dtype in ("rocm7", "rocm10", "rocm_win", "rocm_linux"):
        assert version_manager.add_pytorch_package_extras("torch<3.0,>=2.7.0 torchvision", dtype) == "torch[device-all]<3.0,>=2.7.0 torchvision[device-all]"


def test_has_pytorch_xformers_support_uses_version_table(monkeypatch):
    data = [
        _torch_entry("Torch 2.14.0 (CUDA 13.0) + xFormers", "cu130", "torch==2.14.0+cu130", "xformers==0.0.35"),
        _torch_entry("Torch 2.14.0 (CUDA 13.2)", "cu132", "torch==2.14.0+cu132"),
    ]
    monkeypatch.setattr(version_manager, "PYTORCH_DOWNLOAD_DICT", data)

    assert version_manager.has_pytorch_xformers_support("cu130") is True
    assert version_manager.has_pytorch_xformers_support("cu132") is False
    assert version_manager.has_pytorch_xformers_support("rocm7") is False
    assert version_manager.has_pytorch_xformers_support("rocm_win") is False
