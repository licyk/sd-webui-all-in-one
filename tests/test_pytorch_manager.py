import json
import subprocess

import pytest

from sd_webui_all_in_one.pytorch_manager import gpu_detector
from sd_webui_all_in_one.pytorch_manager import mirror_selector
from sd_webui_all_in_one.pytorch_manager import version_manager as torch_versions


def _gpu(name, vendor):
    return {
        "Name": name,
        "AdapterCompatibility": vendor,
        "AdapterRAM": None,
        "DriverVersion": None,
    }


def test_cuda_capability_and_version_parse_subprocess(monkeypatch):
    def fake_run(command, **_kwargs):
        if "--query-gpu=compute_cap" in command:
            return subprocess.CompletedProcess(command, 0, stdout="8.9\n7.5\n", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="Driver Info\nCUDA Version                      : 12.4\n", stderr="")

    monkeypatch.setattr(gpu_detector.subprocess, "run", fake_run)

    assert gpu_detector.get_cuda_comp_cap() == 8.9
    assert gpu_detector.get_cuda_version() == 12.4


def test_cuda_version_parse_falls_back_to_umd_version(monkeypatch):
    def fake_run(command, **_kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="Driver Info\nCUDA UMD Version                  : 12.8\n", stderr="")

    monkeypatch.setattr(gpu_detector.subprocess, "run", fake_run)

    assert gpu_detector.get_cuda_version() == 12.8


def test_rocm_gfx_targets_return_empty_when_rocminfo_missing(monkeypatch):
    monkeypatch.setattr(gpu_detector.shutil, "which", lambda name: None if name == "rocminfo" else f"/usr/bin/{name}")

    assert gpu_detector.get_rocm_gfx_targets() == []


def test_rocm_gfx_targets_parse_unique_targets(monkeypatch):
    output = """
    Name:                    gfx1100
    Marketing Name:          AMD Radeon RX 7900 XTX
    Name:                    gfx1100
    Name:                    gfx1201
    """
    monkeypatch.setattr(gpu_detector.shutil, "which", lambda name: "/usr/bin/rocminfo" if name == "rocminfo" else None)
    monkeypatch.setattr(
        gpu_detector.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout=output, stderr=""),
    )

    assert gpu_detector.get_rocm_gfx_targets() == ["gfx1100", "gfx1201"]


def test_rocm_gfx_targets_return_empty_when_rocminfo_fails(monkeypatch):
    def fake_run(*_args, **_kwargs):
        raise subprocess.CalledProcessError(1, ["rocminfo"])

    monkeypatch.setattr(gpu_detector.shutil, "which", lambda name: "/usr/bin/rocminfo" if name == "rocminfo" else None)
    monkeypatch.setattr(gpu_detector.subprocess, "run", fake_run)

    assert gpu_detector.get_rocm_gfx_targets() == []


def test_windows_and_nvidia_smi_gpu_parsers(monkeypatch):
    windows_payload = {"Name": "NVIDIA RTX 4090", "AdapterCompatibility": "NVIDIA", "AdapterRAM": "123", "DriverVersion": "555"}

    monkeypatch.setattr(
        gpu_detector.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout=json.dumps(windows_payload), stderr=""),
    )
    assert gpu_detector.get_windows_gpu_list() == [windows_payload]

    monkeypatch.setattr(gpu_detector.shutil, "which", lambda name: "/usr/bin/nvidia-smi" if name == "nvidia-smi" else None)
    monkeypatch.setattr(
        gpu_detector.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, stdout="NVIDIA RTX 4090, 24576, 555.42\n", stderr=""),
    )
    assert gpu_detector.get_nvidia_smi_gpus() == [
        {
            "Name": "NVIDIA RTX 4090",
            "AdapterCompatibility": "NVIDIA",
            "AdapterRAM": str(24576 * 1024 * 1024),
            "DriverVersion": "555.42",
        }
    ]


def test_linux_gpu_list_deduplicates_and_merges(monkeypatch):
    monkeypatch.setattr(gpu_detector, "get_nvidia_smi_gpus", lambda: [_gpu("NVIDIA RTX", "NVIDIA")])
    monkeypatch.setattr(
        gpu_detector,
        "get_lshw_gpus",
        lambda: [{"Name": "nvidia rtx", "AdapterCompatibility": None, "AdapterRAM": "4096", "DriverVersion": "nvidia"}],
    )
    monkeypatch.setattr(gpu_detector, "get_lspci_gpus", lambda: [_gpu("AMD Radeon RX", "Advanced Micro Devices")])

    result = gpu_detector.get_linux_gpu_list()

    assert len(result) == 2
    assert result[0]["AdapterRAM"] == "4096"
    assert result[0]["DriverVersion"] == "nvidia"
    assert result[1]["Name"] == "AMD Radeon RX"


def test_gpu_classification_helpers():
    gpus = [
        _gpu("NVIDIA RTX 4090", "NVIDIA"),
        _gpu("Intel(R) Arc A770", "Intel"),
        _gpu("AMD Radeon RX 7900", "Advanced Micro Devices"),
    ]

    assert gpu_detector.has_gpus(gpus) is True
    assert gpu_detector.has_nvidia_gpu(gpus) is True
    assert gpu_detector.has_intel_xpu(gpus) is True
    assert gpu_detector.has_amd_gpu(gpus) is True


@pytest.mark.parametrize(
    ("platform", "gpus", "cuda_version", "cuda_cap", "expected_type", "expected_category"),
    [
        ("linux", [], 0.0, 0.0, "cpu", "cpu"),
        ("linux", [_gpu("NVIDIA RTX 4090", "NVIDIA")], 12.8, 8.9, "cu128", "cuda"),
        ("linux", [_gpu("Intel(R) Arc A770", "Intel")], 0.0, 0.0, "xpu", "xpu"),
        ("linux", [_gpu("AMD Radeon RX 7900", "Advanced Micro Devices")], 0.0, 0.0, "rocm_rdna3", "rocm"),
        ("linux", [_gpu("AMD Radeon RX 7600", "Advanced Micro Devices")], 0.0, 0.0, "cpu", "rocm"),
        ("win32", [_gpu("AMD Radeon RX 7900", "Advanced Micro Devices")], 0.0, 0.0, "rocm_win", "rocm"),
        ("darwin", [], 0.0, 0.0, "all", "mps"),
    ],
)
def test_auto_detect_pytorch_type_and_category(monkeypatch, platform, gpus, cuda_version, cuda_cap, expected_type, expected_category):
    monkeypatch.setattr(gpu_detector.sys, "platform", platform)
    monkeypatch.setattr(gpu_detector, "get_gpu_list", lambda: gpus)
    monkeypatch.setattr(gpu_detector, "get_cuda_version", lambda: cuda_version)
    monkeypatch.setattr(gpu_detector, "get_cuda_comp_cap", lambda: cuda_cap)
    monkeypatch.setattr(gpu_detector, "get_rocm_gfx_targets", lambda: [])

    assert gpu_detector.auto_detect_avaliable_pytorch_type() == expected_type
    assert gpu_detector.auto_detect_pytorch_device_category() == expected_category


@pytest.mark.parametrize(
    ("gfx_targets", "expected"),
    [
        (["gfx1201"], "rocm_rdna4"),
        (["gfx1151"], "rocm_rdna3.5"),
        (["gfx942"], "rocm7.2"),
        (["gfx906"], "cpu"),
        (["gfx1102"], "cpu"),
    ],
)
def test_auto_detect_amd_rocm_type_from_gfx_targets(monkeypatch, gfx_targets, expected):
    monkeypatch.setattr(gpu_detector.sys, "platform", "linux")
    monkeypatch.setattr(gpu_detector, "get_gpu_list", lambda: [_gpu("AMD Radeon Graphics", "Advanced Micro Devices")])
    monkeypatch.setattr(gpu_detector, "get_cuda_version", lambda: 0.0)
    monkeypatch.setattr(gpu_detector, "get_cuda_comp_cap", lambda: 0.0)
    monkeypatch.setattr(gpu_detector, "get_rocm_gfx_targets", lambda: gfx_targets)

    assert gpu_detector.auto_detect_avaliable_pytorch_type() == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("AMD Radeon RX 9070 XT", "rocm_rdna4"),
        ("AMD Radeon RX 9060 XT", "rocm_rdna4"),
        ("AMD Radeon RX 7900 XTX", "rocm_rdna3"),
        ("Navi 31 [Radeon RX 7900 XTX/XT]", "rocm_rdna3"),
        ("AMD Radeon RX 7800 XT", "rocm_rdna3"),
        ("AMD Radeon RX 7700 XT", "rocm_rdna3"),
        ("AMD Radeon PRO V710", "rocm_rdna3"),
        ("AMD Instinct MI300X", "rocm7.2"),
        ("AMD Instinct MI100", "rocm7.2"),
        ("AMD Radeon VII", "cpu"),
        ("AMD Radeon RX 7600", "cpu"),
        ("AMD Radeon Something", "cpu"),
    ],
)
def test_auto_detect_amd_rocm_type_from_gpu_name(monkeypatch, name, expected):
    monkeypatch.setattr(gpu_detector.sys, "platform", "linux")
    monkeypatch.setattr(gpu_detector, "get_gpu_list", lambda: [_gpu(name, "Advanced Micro Devices")])
    monkeypatch.setattr(gpu_detector, "get_cuda_version", lambda: 0.0)
    monkeypatch.setattr(gpu_detector, "get_cuda_comp_cap", lambda: 0.0)
    monkeypatch.setattr(gpu_detector, "get_rocm_gfx_targets", lambda: [])

    assert gpu_detector.auto_detect_avaliable_pytorch_type() == expected


def test_available_pytorch_types_only_include_detected_amd_rocm_type(monkeypatch):
    monkeypatch.setattr(gpu_detector.sys, "platform", "linux")
    monkeypatch.setattr(gpu_detector, "get_gpu_list", lambda: [_gpu("AMD Radeon RX 9070 XT", "Advanced Micro Devices")])
    monkeypatch.setattr(gpu_detector, "get_cuda_version", lambda: 0.0)
    monkeypatch.setattr(gpu_detector, "get_cuda_comp_cap", lambda: 0.0)
    monkeypatch.setattr(gpu_detector, "get_rocm_gfx_targets", lambda: [])

    result = gpu_detector.get_avaliable_pytorch_device_type()

    assert "rocm_rdna4" in result
    assert "rocm_rdna3" not in result
    assert "rocm7.2" not in result


def test_available_pytorch_types_skip_unknown_amd_rocm_type(monkeypatch):
    monkeypatch.setattr(gpu_detector.sys, "platform", "linux")
    monkeypatch.setattr(gpu_detector, "get_gpu_list", lambda: [_gpu("AMD Radeon RX 7600", "Advanced Micro Devices")])
    monkeypatch.setattr(gpu_detector, "get_cuda_version", lambda: 0.0)
    monkeypatch.setattr(gpu_detector, "get_cuda_comp_cap", lambda: 0.0)
    monkeypatch.setattr(gpu_detector, "get_rocm_gfx_targets", lambda: [])

    result = gpu_detector.get_avaliable_pytorch_device_type()

    assert all(not dtype.startswith("rocm") for dtype in result)


@pytest.mark.parametrize(
    ("cuda_version", "expected"),
    [
        (11.8, "cu118"),
        (12.1, "cu121"),
        (12.4, "cu124"),
        (12.6, "cu126"),
        (12.8, "cu128"),
        (12.9, "cu129"),
        (13.0, "cu130"),
    ],
)
def test_auto_detect_cuda_thresholds(monkeypatch, cuda_version, expected):
    monkeypatch.setattr(gpu_detector.sys, "platform", "linux")
    monkeypatch.setattr(gpu_detector, "get_gpu_list", lambda: [_gpu("NVIDIA RTX", "NVIDIA")])
    monkeypatch.setattr(gpu_detector, "get_cuda_version", lambda: cuda_version)
    monkeypatch.setattr(gpu_detector, "get_cuda_comp_cap", lambda: 8.9)

    assert gpu_detector.auto_detect_avaliable_pytorch_type() == expected


def test_auto_detect_blackwell_falls_back_to_modern_cuda(monkeypatch):
    monkeypatch.setattr(gpu_detector.sys, "platform", "linux")
    monkeypatch.setattr(gpu_detector, "get_gpu_list", lambda: [_gpu("NVIDIA RTX 5090", "NVIDIA")])
    monkeypatch.setattr(gpu_detector, "get_cuda_version", lambda: 11.0)
    monkeypatch.setattr(gpu_detector, "get_cuda_comp_cap", lambda: 10.0)

    assert gpu_detector.auto_detect_avaliable_pytorch_type() == "cu130"


def test_pytorch_mirror_type_boundaries(monkeypatch):
    monkeypatch.setattr(mirror_selector, "get_cuda_comp_cap", lambda: 8.9)
    monkeypatch.setattr(mirror_selector, "get_cuda_version", lambda: 12.4)
    monkeypatch.setattr(mirror_selector.sys, "platform", "linux")

    assert mirror_selector.get_pytorch_mirror_type_cuda("1.13.1") == "all"
    assert mirror_selector.get_pytorch_mirror_type_cuda("2.4.1") == "cu124"
    assert mirror_selector.get_pytorch_mirror_type("2.7.0", "cuda") == "cu128"
    assert mirror_selector.get_pytorch_mirror_type_rocm("2.4.0") == "rocm6.1"
    assert mirror_selector.get_pytorch_mirror_type_rocm("2.10.0") == "rocm7.1"
    monkeypatch.setattr(mirror_selector.sys, "platform", "win32")
    assert mirror_selector.get_pytorch_mirror_type_rocm("2.4.0") == "rocm_win"
    assert mirror_selector.get_pytorch_mirror_type_ipex("2.0.0") == "ipex_legacy_arc"
    assert mirror_selector.get_pytorch_mirror_type_cpu("2.9.0") == "cpu"


def test_get_pytorch_mirror_and_query_library(monkeypatch):
    monkeypatch.setattr(mirror_selector, "PYTORCH_MIRROR_DICT", {"cpu": ("official-cpu", "index_url")})
    monkeypatch.setattr(mirror_selector, "PYTORCH_MIRROR_NJU_DICT", {"cpu": ("cn-cpu", "index_url")})
    monkeypatch.setattr(mirror_selector, "PYTORCH_ROCM_MIRROR_DICT", {"rocm_win": ("rocm-win", "find_links")})

    assert mirror_selector.get_pytorch_mirror("cpu") == ("official-cpu", "index_url")
    assert mirror_selector.get_pytorch_mirror("cpu", use_cn_mirror=True) == ("cn-cpu", "index_url")
    assert mirror_selector.get_pytorch_mirror("rocm_win") == ("rocm-win", "find_links")
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
