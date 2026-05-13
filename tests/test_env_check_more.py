import importlib.metadata
import importlib
import sys
from pathlib import Path

import pytest

check_torch_version = importlib.import_module("sd_webui_all_in_one.env_check.check_torch_version")
fix_accelerate_bin = importlib.import_module("sd_webui_all_in_one.env_check.fix_accelerate_bin")
fix_numpy = importlib.import_module("sd_webui_all_in_one.env_check.fix_numpy")
onnxruntime_gpu_check = importlib.import_module("sd_webui_all_in_one.env_check.onnxruntime_gpu_check")


def test_torch_version_compatibility_helpers(monkeypatch):
    assert check_torch_version._is_rocm_version_compatible("rocm7.2.1", ["rocm7.2"]) is True
    assert check_torch_version._is_rocm_version_compatible("rocm6.3", ["rocm6.2"]) is False

    monkeypatch.setattr(check_torch_version.sys, "platform", "win32")
    assert check_torch_version._is_rocm_version_compatible("rocm6.3", ["rocm_win"]) is True

    assert check_torch_version._is_ipex_version("gite9ebda2", ["xpu", "ipex_legacy_arc"]) is True
    assert check_torch_version._is_ipex_version("gite9ebda2", ["xpu"]) is False


def test_check_torch_version_handles_missing_cpu_and_compatible_gpu(monkeypatch):
    monkeypatch.setattr(check_torch_version, "get_avaliable_pytorch_device_type", lambda: ["rocm7.2", "xpu", "ipex_legacy_arc"])
    monkeypatch.setattr(check_torch_version, "get_gpu_list", lambda: ["gpu"])
    monkeypatch.setattr(check_torch_version, "has_gpus", lambda _gpu_list: True)

    monkeypatch.setattr(check_torch_version, "load_source_directly", lambda _name: {})
    check_torch_version.check_torch_version()

    monkeypatch.setattr(check_torch_version, "load_source_directly", lambda _name: {"__version__": "2.4.0+cpu"})
    check_torch_version.check_torch_version()

    monkeypatch.setattr(check_torch_version, "load_source_directly", lambda _name: {"__version__": "2.7.0+rocm7.2.1"})
    check_torch_version.check_torch_version()

    monkeypatch.setattr(check_torch_version, "load_source_directly", lambda _name: {"__version__": "2.1.0+gite9ebda2"})
    check_torch_version.check_torch_version()


def test_check_numpy_installs_only_when_version_is_too_new(monkeypatch):
    calls = []
    monkeypatch.setattr(fix_numpy.importlib.metadata, "version", lambda _name: "2.0.0")
    monkeypatch.setattr(fix_numpy, "pip_install", lambda *args, **kwargs: calls.append((args, kwargs)))

    fix_numpy.check_numpy(use_uv=False, custom_env={"A": "B"})

    assert calls == [(("numpy==1.26.4",), {"use_uv": False, "custom_env": {"A": "B"}})]

    calls.clear()
    monkeypatch.setattr(fix_numpy.importlib.metadata, "version", lambda _name: "1.26.4")
    fix_numpy.check_numpy()
    assert calls == []

    monkeypatch.setattr(fix_numpy.importlib.metadata, "version", lambda _name: (_ for _ in ()).throw(importlib.metadata.PackageNotFoundError("numpy")))
    with pytest.raises(RuntimeError, match="Numpy"):
        fix_numpy.check_numpy()


def test_check_accelerate_bin_reinstalls_for_kohya_repo(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(fix_accelerate_bin.git_warpper, "get_current_branch_remote_url", lambda _path: "https://github.com/other/repo")
    fix_accelerate_bin.check_accelerate_bin(tmp_path)
    assert calls == []

    monkeypatch.setattr(fix_accelerate_bin.git_warpper, "get_current_branch_remote_url", lambda _path: "https://github.com/bmaltais/kohya_ss")

    def fake_run_cmd(command, **_kwargs):
        calls.append(("cmd", command))
        if command == ["accelerate", "--help"]:
            raise RuntimeError("missing")

    monkeypatch.setattr(fix_accelerate_bin, "run_cmd", fake_run_cmd)
    monkeypatch.setattr(fix_accelerate_bin.importlib.metadata, "version", lambda _name: "0.31.0")
    monkeypatch.setattr(fix_accelerate_bin, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))

    fix_accelerate_bin.check_accelerate_bin(tmp_path, use_uv=False, custom_env={"M": "1"})

    assert calls[0] == ("cmd", ["accelerate", "--help"])
    assert calls[1][0] == "cmd"
    assert calls[1][1] == [Path(sys.executable).as_posix(), "-m", "pip", "uninstall", "accelerate", "-y"]
    assert calls[2] == ("pip", ("accelerate==0.31.0", "--no-deps"), {"use_uv": False, "custom_env": {"M": "1"}})


def test_need_install_ort_ver_matrix(monkeypatch):
    monkeypatch.setattr(onnxruntime_gpu_check.importlib.metadata, "version", lambda _name: (_ for _ in ()).throw(importlib.metadata.PackageNotFoundError("onnxruntime-gpu")))
    monkeypatch.setattr(onnxruntime_gpu_check, "get_torch_cuda_ver_subprocess", lambda: (None, None, None))
    assert onnxruntime_gpu_check.need_install_ort_ver(skip_if_missing=False) == onnxruntime_gpu_check.OrtType.CU130

    monkeypatch.setattr(onnxruntime_gpu_check, "get_torch_cuda_ver_subprocess", lambda: ("2.8.0", "13.0", "9000"))
    monkeypatch.setattr(onnxruntime_gpu_check, "get_onnxruntime_support_cuda_version", lambda: ("12.8", "9"))
    assert onnxruntime_gpu_check.need_install_ort_ver() == onnxruntime_gpu_check.OrtType.CU130

    monkeypatch.setattr(onnxruntime_gpu_check, "get_torch_cuda_ver_subprocess", lambda: ("2.5.0", "12.1", "9000"))
    monkeypatch.setattr(onnxruntime_gpu_check, "get_onnxruntime_support_cuda_version", lambda: ("12.2", "8"))
    assert onnxruntime_gpu_check.need_install_ort_ver() == onnxruntime_gpu_check.OrtType.CU121CUDNN9

    monkeypatch.setattr(onnxruntime_gpu_check, "get_torch_cuda_ver_subprocess", lambda: ("2.4.0", "12.1", "8000"))
    monkeypatch.setattr(onnxruntime_gpu_check, "get_onnxruntime_support_cuda_version", lambda: ("11.8", "8"))
    assert onnxruntime_gpu_check.need_install_ort_ver() == onnxruntime_gpu_check.OrtType.CU121CUDNN8

    monkeypatch.setattr(onnxruntime_gpu_check, "get_torch_cuda_ver_subprocess", lambda: ("2.1.0", "11.8", "8000"))
    monkeypatch.setattr(onnxruntime_gpu_check, "get_onnxruntime_support_cuda_version", lambda: ("12.1", "8"))
    assert onnxruntime_gpu_check.need_install_ort_ver() == onnxruntime_gpu_check.OrtType.CU118

    monkeypatch.setattr(onnxruntime_gpu_check.sys, "platform", "win32")
    monkeypatch.setattr(onnxruntime_gpu_check, "get_torch_cuda_ver_subprocess", lambda: ("2.5.0", "12.1", "9000"))
    monkeypatch.setattr(onnxruntime_gpu_check, "get_onnxruntime_support_cuda_version", lambda: (None, None))
    assert onnxruntime_gpu_check.need_install_ort_ver(skip_if_missing=False) == onnxruntime_gpu_check.OrtType.CU121CUDNN9


def test_check_onnxruntime_gpu_installs_with_cleaned_env(monkeypatch):
    env = {
        "PIP_EXTRA_INDEX_URL": "extra",
        "UV_INDEX": "extra",
        "PIP_FIND_LINKS": "links",
        "UV_FIND_LINKS": "links",
    }
    calls = []

    monkeypatch.setattr(onnxruntime_gpu_check, "need_install_ort_ver", lambda _skip: onnxruntime_gpu_check.OrtType.CU118)
    monkeypatch.setattr(onnxruntime_gpu_check, "run_cmd", lambda command: calls.append(("cmd", command)))
    monkeypatch.setattr(onnxruntime_gpu_check, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))

    onnxruntime_gpu_check.check_onnxruntime_gpu(use_uv=False, skip_if_missing=False, custom_env=env)

    assert "PIP_EXTRA_INDEX_URL" not in env
    assert "UV_INDEX" not in env
    assert "PIP_FIND_LINKS" not in env
    assert "UV_FIND_LINKS" not in env
    assert env["PIP_INDEX_URL"].endswith("/onnxruntime-cuda-11/pypi/simple/")
    assert calls[0][0] == "cmd"
    assert calls[1] == ("pip", ("onnxruntime-gpu>=1.18.1", "--no-cache-dir", "--no-deps"), {"use_uv": False, "custom_env": env})
    assert calls[2][0] == "pip"
    assert calls[2][2]["custom_env"]["PIP_EXTRA_INDEX_URL"] == "extra"
