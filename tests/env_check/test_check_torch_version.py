"""PyTorch 版本兼容性检查测试"""

import importlib
import importlib.metadata
import sys

import pytest

check_torch_version = importlib.import_module("sd_webui_all_in_one.env_check.check_torch_version")


check_torch_version_checker = importlib.import_module("sd_webui_all_in_one.env_check.check_torch_version.checker")


check_torch_version_compatibility = importlib.import_module("sd_webui_all_in_one.env_check.check_torch_version.compatibility")


gpu_detector = importlib.import_module("sd_webui_all_in_one.pytorch_manager.gpu_detector")


mirror_selector = importlib.import_module("sd_webui_all_in_one.pytorch_manager.mirror_selector")


def test_torch_version_compatibility_helpers(monkeypatch):
    assert check_torch_version_compatibility._is_rocm_version_compatible("rocm7.2.1", ["rocm7.2"]) is True
    assert check_torch_version_compatibility._is_rocm_version_compatible("rocm6.3", ["rocm6.2"]) is False

    monkeypatch.setattr(sys, "platform", "linux")
    assert check_torch_version_compatibility._is_rocm_version_compatible("rocm7.14.1", ["rocm7", "rocm10", "rocm7.2"]) is True
    assert check_torch_version_compatibility._is_rocm_version_compatible("rocm10.0.0", ["rocm7", "rocm10", "rocm7.2"]) is True
    assert check_torch_version_compatibility._is_rocm_version_compatible("rocm10.0.0", ["rocm7", "rocm7.2"]) is False
    assert check_torch_version_compatibility._is_rocm_version_compatible("rocm10.0.0", ["rocm_linux", "rocm7.2"]) is True
    assert check_torch_version_compatibility._is_rocm_version_compatible("rocm7.14.0", ["rocm_linux", "rocm7.2"]) is False
    assert check_torch_version_compatibility._is_rocm_version_compatible("rocm7.14.0", ["rocm7.2"]) is False
    assert check_torch_version_compatibility._is_rocm_version_compatible("rocm6.3", ["rocm7"]) is False

    monkeypatch.setattr(sys, "platform", "win32")
    assert check_torch_version_compatibility._is_rocm_version_compatible("rocm6.3", ["rocm7"]) is True
    assert check_torch_version_compatibility._is_rocm_version_compatible("rocm10.0.0", ["rocm_win"]) is True
    assert check_torch_version_compatibility._is_rocm_version_compatible("rocm6.3", ["rocm_win"]) is False
    assert check_torch_version_compatibility._is_rocm_version_compatible("rocm10.0.0", ["rocm7"]) is False

    assert check_torch_version_compatibility._is_ipex_version("gite9ebda2", ["xpu", "ipex_legacy_arc"]) is True
    assert check_torch_version_compatibility._is_ipex_version("gite9ebda2", ["xpu"]) is False


def test_check_torch_version_handles_missing_cpu_and_compatible_gpu(monkeypatch):
    monkeypatch.setattr(check_torch_version_checker, "get_available_pytorch_device_type", lambda _gpu_list=None: ["rocm7.2", "xpu", "ipex_legacy_arc"])
    monkeypatch.setattr(check_torch_version_checker, "auto_detect_available_pytorch_type", lambda _gpu_list=None: "xpu")
    monkeypatch.setattr(check_torch_version_checker, "get_gpu_list", lambda: ["gpu"])
    monkeypatch.setattr(check_torch_version_checker, "has_gpus", lambda _gpu_list: True)

    monkeypatch.setattr(check_torch_version_checker, "load_source_directly", lambda _name: {})
    check_torch_version.check_torch_version()

    monkeypatch.setattr(check_torch_version_checker, "load_source_directly", lambda _name: {"__version__": "2.4.0+cpu"})
    check_torch_version.check_torch_version()

    monkeypatch.setattr(check_torch_version_checker, "load_source_directly", lambda _name: {"__version__": "2.7.0+rocm7.2.1"})
    check_torch_version.check_torch_version()

    monkeypatch.setattr(check_torch_version_checker, "load_source_directly", lambda _name: {"__version__": "2.1.0+gite9ebda2"})
    check_torch_version.check_torch_version()


def test_check_torch_version_status_reports_structured_result(monkeypatch):
    monkeypatch.setattr(check_torch_version_checker, "get_available_pytorch_device_type", lambda _gpu_list=None: ["cu128"])
    monkeypatch.setattr(check_torch_version_checker, "auto_detect_available_pytorch_type", lambda _gpu_list=None: "cu128")
    monkeypatch.setattr(check_torch_version_checker, "get_gpu_list", lambda: ["gpu"])
    monkeypatch.setattr(check_torch_version_checker, "has_gpus", lambda _gpu_list: True)
    monkeypatch.setattr(check_torch_version_checker, "load_source_directly", lambda _name: {"__version__": "2.7.0+cu121"})

    result = check_torch_version.check_torch_version_status()

    assert result["available_types"] == ["cu128"]
    assert result["gpu_list"] == ["gpu"]
    assert result["has_gpu"] is True
    assert result["installed_version"] == "2.7.0+cu121"
    assert result["installed_type"] == "cu121"
    assert result["status"] == "unsupported_type"
    assert result["is_compatible"] is False


def test_check_torch_version_warning_reports_supported_type_before_installed_type(monkeypatch):
    warnings = []
    monkeypatch.setattr(check_torch_version_checker, "get_available_pytorch_device_type", lambda _gpu_list=None: ["cu128"])
    monkeypatch.setattr(check_torch_version_checker, "auto_detect_available_pytorch_type", lambda _gpu_list=None: "cu128")
    monkeypatch.setattr(check_torch_version_checker, "get_gpu_list", lambda: ["gpu"])
    monkeypatch.setattr(check_torch_version_checker, "has_gpus", lambda _gpu_list: True)
    monkeypatch.setattr(check_torch_version_checker, "load_source_directly", lambda _name: {"__version__": "2.7.0+cu121"})
    monkeypatch.setattr(check_torch_version.logger, "warning", lambda *args: warnings.append(args))

    check_torch_version.check_torch_version()

    assert "当前设备支持的 PyTorch 类型有 %s, 而当前环境安装的 PyTorch 类型为 %s" in warnings[-1][0]
    assert warnings[-1][1:] == (["cu128"], "cu121")


def _gpu(name, vendor):
    return {"Name": name, "AdapterCompatibility": vendor, "AdapterRAM": None, "DriverVersion": None}


UNSUPPORTED_INTEL_GPU = [_gpu("Intel(R) UHD Graphics 630", "Intel Corporation")]


SUPPORTED_INTEL_GPU = [_gpu("Intel(R) Arc(TM) A770 Graphics", "Intel Corporation")]


NVIDIA_GPU = [_gpu("NVIDIA GeForce RTX 4090", "NVIDIA")]


AMD_GPU = [_gpu("AMD Radeon RX 7900 XTX", "Advanced Micro Devices")]


def _patch_device(monkeypatch, platform, gpus, cuda_version=0.0, cuda_cap=0.0):
    """模拟设备环境, 环境检查和自动选择 PyTorch 类型使用同一套真实的检测逻辑"""
    monkeypatch.setattr(gpu_detector.sys, "platform", platform)
    monkeypatch.setattr(mirror_selector.sys, "platform", platform)
    monkeypatch.setattr(gpu_detector, "get_cuda_version", lambda: cuda_version)
    monkeypatch.setattr(gpu_detector, "get_cuda_comp_cap", lambda: cuda_cap)
    monkeypatch.setattr(check_torch_version_checker, "get_gpu_list", lambda: gpus)


@pytest.mark.parametrize(
    ("platform", "gpus", "cuda_version", "torch_version", "expected_status"),
    [
        # 不受支持的显卡: 自动选择 CPU 类型, 环境检查也应视 CPU 类型为适合当前设备
        ("win32", UNSUPPORTED_INTEL_GPU, 0.0, "2.7.0+cpu", "compatible"),
        ("linux", UNSUPPORTED_INTEL_GPU, 0.0, "2.7.0+cpu", "compatible"),
        ("linux", UNSUPPORTED_INTEL_GPU, 0.0, "2.7.0", "compatible"),
        # CUDA 版本过低的 NVIDIA 显卡同样自动选择 CPU 类型
        ("linux", NVIDIA_GPU, 10.2, "2.7.0+cpu", "compatible"),
        ("linux", [], 0.0, "2.7.0+cpu", "compatible"),
        # 受支持的显卡使用 CPU 类型时提示重装
        ("linux", SUPPORTED_INTEL_GPU, 0.0, "2.7.0+cpu", "cpu_with_gpu"),
        ("linux", NVIDIA_GPU, 12.8, "2.7.0+cpu", "cpu_with_gpu"),
        ("linux", AMD_GPU, 0.0, "2.7.0+cpu", "cpu_with_gpu"),
        ("win32", AMD_GPU, 0.0, "2.7.0+cpu", "cpu_with_gpu"),
        # 不受支持的显卡安装了 GPU 类型的 PyTorch
        ("linux", UNSUPPORTED_INTEL_GPU, 0.0, "2.7.0+cu128", "unsupported_type"),
        ("linux", NVIDIA_GPU, 12.8, "2.7.0+cu128", "compatible"),
        ("linux", AMD_GPU, 0.0, "2.13.0+rocm10.0.0", "compatible"),
    ],
)
def test_check_torch_version_status_matches_auto_detection_rules(monkeypatch, platform, gpus, cuda_version, torch_version, expected_status):
    _patch_device(monkeypatch, platform, gpus, cuda_version=cuda_version)
    monkeypatch.setattr(check_torch_version_checker, "load_source_directly", lambda _name: {"__version__": torch_version})

    result = check_torch_version.check_torch_version_status()

    assert result["status"] == expected_status
    assert result["is_compatible"] is (expected_status == "compatible")


@pytest.mark.parametrize(
    ("platform", "gpus", "cuda_version", "cuda_cap"),
    [
        ("linux", [], 0.0, 0.0),
        ("win32", UNSUPPORTED_INTEL_GPU, 0.0, 0.0),
        ("linux", UNSUPPORTED_INTEL_GPU, 0.0, 0.0),
        ("win32", SUPPORTED_INTEL_GPU, 0.0, 0.0),
        ("linux", NVIDIA_GPU, 10.2, 6.1),
        ("linux", NVIDIA_GPU, 11.8, 8.6),
        ("linux", NVIDIA_GPU, 12.8, 8.9),
        ("win32", NVIDIA_GPU, 13.0, 12.0),
        ("linux", NVIDIA_GPU, 13.2, 8.9),
        ("win32", NVIDIA_GPU, 13.4, 12.0),
        ("linux", AMD_GPU, 0.0, 0.0),
        ("win32", AMD_GPU, 0.0, 0.0),
        ("linux", UNSUPPORTED_INTEL_GPU + AMD_GPU, 0.0, 0.0),
        ("darwin", [], 0.0, 0.0),
    ],
)
def test_auto_selected_pytorch_type_always_passes_environment_check(monkeypatch, platform, gpus, cuda_version, cuda_cap):
    _patch_device(monkeypatch, platform, gpus, cuda_version=cuda_version, cuda_cap=cuda_cap)
    selected_type = gpu_detector.auto_detect_available_pytorch_type(gpus)
    # AMD 多架构 wheel 的版本后缀为具体的 ROCm 版本号
    suffix = {"rocm10": "rocm10.0.0", "rocm7": "rocm7.14.1"}.get(selected_type, selected_type)
    torch_version = "2.13.0" if selected_type == "all" else f"2.13.0+{suffix}"
    monkeypatch.setattr(check_torch_version_checker, "load_source_directly", lambda _name: {"__version__": torch_version})

    result = check_torch_version.check_torch_version_status()

    assert result["status"] == "compatible", (selected_type, result)
