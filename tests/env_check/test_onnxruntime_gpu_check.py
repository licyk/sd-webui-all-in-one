"""onnxruntime-gpu 版本检查与修复测试"""

import importlib
import importlib.metadata
import sys
from pathlib import Path

import pytest

onnxruntime_gpu_check = importlib.import_module("sd_webui_all_in_one.env_check.onnxruntime_gpu_check")


onnxruntime_gpu_check_resolver = importlib.import_module("sd_webui_all_in_one.env_check.onnxruntime_gpu_check.resolver")


onnxruntime_gpu_check_fixer = importlib.import_module("sd_webui_all_in_one.env_check.onnxruntime_gpu_check.fixer")


def test_need_install_ort_ver_matrix(monkeypatch):
    def set_torch_info(torch_ver, cuda_ver, cudnn_ver):
        monkeypatch.setattr(onnxruntime_gpu_check_resolver, "get_torch_cuda_ver_fast", lambda: (torch_ver, cuda_ver))
        monkeypatch.setattr(onnxruntime_gpu_check_resolver, "get_torch_cuda_ver", lambda: (torch_ver, cuda_ver, cudnn_ver))

    monkeypatch.setattr(onnxruntime_gpu_check_resolver.importlib.metadata, "version", lambda _name: (_ for _ in ()).throw(importlib.metadata.PackageNotFoundError("onnxruntime-gpu")))
    set_torch_info(None, None, None)
    assert onnxruntime_gpu_check.need_install_ort_ver(skip_if_missing=False) == onnxruntime_gpu_check.OrtType.CU130

    set_torch_info("2.8.0", "13.0", "9000")
    monkeypatch.setattr(onnxruntime_gpu_check_resolver, "get_onnxruntime_support_cuda_version", lambda: ("12.8", "9"))
    assert onnxruntime_gpu_check.need_install_ort_ver() == onnxruntime_gpu_check.OrtType.CU130

    set_torch_info("2.5.0", "12.1", "9000")
    monkeypatch.setattr(onnxruntime_gpu_check_resolver, "get_onnxruntime_support_cuda_version", lambda: ("12.2", "8"))
    assert onnxruntime_gpu_check.need_install_ort_ver() == onnxruntime_gpu_check.OrtType.CU121CUDNN9

    set_torch_info("2.4.0", "12.1", "8000")
    monkeypatch.setattr(onnxruntime_gpu_check_resolver, "get_onnxruntime_support_cuda_version", lambda: ("11.8", "8"))
    assert onnxruntime_gpu_check.need_install_ort_ver() == onnxruntime_gpu_check.OrtType.CU121CUDNN8

    set_torch_info("2.1.0", "11.8", "8000")
    monkeypatch.setattr(onnxruntime_gpu_check_resolver, "get_onnxruntime_support_cuda_version", lambda: ("12.1", "8"))
    assert onnxruntime_gpu_check.need_install_ort_ver() == onnxruntime_gpu_check.OrtType.CU118

    monkeypatch.setattr(onnxruntime_gpu_check_resolver.sys, "platform", "win32")
    set_torch_info("2.5.0", "12.1", "9000")
    monkeypatch.setattr(onnxruntime_gpu_check_resolver, "get_onnxruntime_support_cuda_version", lambda: (None, None))
    assert onnxruntime_gpu_check.need_install_ort_ver(skip_if_missing=False) == onnxruntime_gpu_check.OrtType.CU121CUDNN9


def test_check_onnxruntime_gpu_installs_with_cleaned_env(monkeypatch):
    env = {
        "PIP_EXTRA_INDEX_URL": "extra",
        "UV_INDEX": "extra",
        "PIP_FIND_LINKS": "links",
        "UV_FIND_LINKS": "links",
    }
    original_env = env.copy()
    calls = []

    monkeypatch.setattr(onnxruntime_gpu_check_fixer, "need_install_ort_ver", lambda _skip: onnxruntime_gpu_check.OrtType.CU118)
    monkeypatch.setattr(onnxruntime_gpu_check_fixer, "run_cmd", lambda command: calls.append(("cmd", command)))
    monkeypatch.setattr(onnxruntime_gpu_check_fixer, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))

    onnxruntime_gpu_check.check_onnxruntime_gpu(use_uv=False, skip_if_missing=False, custom_env=env)

    assert env == original_env
    assert calls[0][0] == "cmd"
    assert calls[1][0] == "pip"
    assert calls[1][1] == ("onnxruntime-gpu>=1.18.1", "--no-cache-dir", "--no-deps")
    assert calls[1][2]["use_uv"] is False
    assert calls[1][2]["custom_env"] is not env
    assert calls[1][2]["custom_env"]["PIP_INDEX_URL"].endswith("/onnxruntime-cuda-11/pypi/simple/")
    assert "PIP_EXTRA_INDEX_URL" not in calls[1][2]["custom_env"]
    assert "UV_INDEX" not in calls[1][2]["custom_env"]
    assert "PIP_FIND_LINKS" not in calls[1][2]["custom_env"]
    assert "UV_FIND_LINKS" not in calls[1][2]["custom_env"]
    assert calls[2][0] == "pip"
    assert calls[2][2]["custom_env"]["PIP_EXTRA_INDEX_URL"] == "extra"


onnx_check = importlib.import_module("sd_webui_all_in_one.env_check.onnxruntime_gpu_check")


onnx_check_resolver = importlib.import_module("sd_webui_all_in_one.env_check.onnxruntime_gpu_check.resolver")


onnx_check_fixer = importlib.import_module("sd_webui_all_in_one.env_check.onnxruntime_gpu_check.fixer")


@pytest.mark.parametrize(
    ("torch_info", "ort_info", "skip_if_missing", "platform", "installed_ort", "expected"),
    [
        ((None, None, None), (None, None), True, "linux", False, None),
        ((None, None, None), (None, None), False, "linux", False, onnx_check.OrtType.CU130),
        (("2.9.0", "13.0", "9"), ("12.8", "9"), True, "linux", True, onnx_check.OrtType.CU130),
        (("2.9.0", "13.0", "9"), ("13.0", "9"), True, "linux", True, None),
        (("2.5.0", "12.1", "8"), ("12.1", "9"), True, "linux", True, onnx_check.OrtType.CU121CUDNN8),
        (("2.5.0", "12.1", "9"), ("12.1", "8"), True, "linux", True, onnx_check.OrtType.CU121CUDNN9),
        (("2.5.0", "12.1", "9"), ("12.1", "9"), True, "linux", True, None),
        (("2.5.0", "12.1", "9"), ("11.8", "8"), True, "linux", True, onnx_check.OrtType.CU121CUDNN9),
        (("2.0.0", "11.8", "8"), ("12.1", "9"), True, "linux", True, onnx_check.OrtType.CU118),
        (("2.0.0", "11.8", "8"), ("11.8", "8"), True, "linux", True, None),
        (("2.5.0", "12.1", "9"), (None, None), False, "linux", False, onnx_check.OrtType.CU130),
        (("2.5.0", "12.1", "9"), (None, None), False, "linux", True, None),
        (("2.5.0", "12.1", "8"), (None, None), False, "win32", False, onnx_check.OrtType.CU121CUDNN8),
        (("2.5.0", "12.1", "9"), (None, None), False, "win32", False, onnx_check.OrtType.CU121CUDNN9),
        (("2.0.0", "11.8", "8"), (None, None), False, "win32", False, onnx_check.OrtType.CU118),
    ],
)
def test_need_install_ort_ver_cuda_cudnn_matrix(monkeypatch, torch_info, ort_info, skip_if_missing, platform, installed_ort, expected):
    monkeypatch.setattr(onnx_check_resolver, "get_torch_cuda_ver_fast", lambda: (torch_info[0], torch_info[1]))
    monkeypatch.setattr(onnx_check_resolver, "get_torch_cuda_ver", lambda: torch_info)
    monkeypatch.setattr(onnx_check_resolver, "get_onnxruntime_support_cuda_version", lambda: ort_info)
    monkeypatch.setattr(onnx_check_resolver.sys, "platform", platform)

    def fake_version(name):
        if name == "onnxruntime-gpu" and installed_ort:
            return "1.20.0"
        raise onnx_check_resolver.importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(onnx_check_resolver.importlib.metadata, "version", fake_version)

    assert onnx_check.need_install_ort_ver(skip_if_missing=skip_if_missing) == expected


def test_need_install_ort_ver_reads_cudnn_lazily(monkeypatch):
    monkeypatch.setattr(onnx_check_resolver, "get_torch_cuda_ver_fast", lambda: ("2.9.0", "13.0"))
    monkeypatch.setattr(onnx_check_resolver, "get_torch_cuda_ver", lambda: (_ for _ in ()).throw(AssertionError("cuDNN should not be read")))
    monkeypatch.setattr(onnx_check_resolver, "get_onnxruntime_support_cuda_version", lambda: ("13.0", "9"))

    assert onnx_check.need_install_ort_ver() is None

    calls = []
    monkeypatch.setattr(onnx_check_resolver, "get_torch_cuda_ver_fast", lambda: ("2.5.0", "12.1"))
    monkeypatch.setattr(onnx_check_resolver, "get_torch_cuda_ver", lambda: calls.append("cudnn") or ("2.5.0", "12.1", "9000"))
    monkeypatch.setattr(onnx_check_resolver, "get_onnxruntime_support_cuda_version", lambda: ("12.1", "8"))

    assert onnx_check.need_install_ort_ver() == onnx_check.OrtType.CU121CUDNN9
    assert calls == ["cudnn"]


@pytest.mark.parametrize(
    ("ort_type", "expected_spec", "expected_index", "expected_clean_env"),
    [
        (onnx_check.OrtType.CU118, "onnxruntime-gpu>=1.18.1", "onnxruntime-cuda-11", True),
        (onnx_check.OrtType.CU121CUDNN8, "onnxruntime-gpu==1.17.1", "onnxruntime-cuda-12", True),
        (onnx_check.OrtType.CU121CUDNN9, "onnxruntime-gpu>=1.19.0,<=1.26.0", None, False),
        (onnx_check.OrtType.CU130, "onnxruntime-gpu>=1.27.0", None, False),
    ],
)
def test_check_onnxruntime_gpu_installs_expected_package_and_env(monkeypatch, ort_type, expected_spec, expected_index, expected_clean_env):
    custom_env = {
        "PIP_EXTRA_INDEX_URL": "old-extra",
        "UV_INDEX": "old-uv-index",
        "PIP_FIND_LINKS": "old-links",
        "UV_FIND_LINKS": "old-uv-links",
        "KEEP": "1",
    }
    original_env = custom_env.copy()
    calls = []

    monkeypatch.setattr(onnx_check_fixer, "need_install_ort_ver", lambda skip_if_missing: ort_type)
    monkeypatch.setattr(onnx_check_fixer, "run_cmd", lambda command: calls.append(("run", command)))
    monkeypatch.setattr(onnx_check_fixer, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))

    onnx_check.check_onnxruntime_gpu(use_uv=False, skip_if_missing=True, custom_env=custom_env)

    assert calls[0] == ("run", [Path(sys.executable).as_posix(), "-m", "pip", "uninstall", "onnxruntime-gpu", "-y"])
    assert calls[1][0] == "pip"
    assert calls[1][1] == (expected_spec, "--no-cache-dir", "--no-deps")
    assert calls[1][2]["use_uv"] is False
    assert calls[1][2]["custom_env"]["KEEP"] == "1"
    assert calls[1][2]["custom_env"] is not custom_env
    assert calls[2] == (
        "pip",
        (expected_spec,),
        {"use_uv": False, "custom_env": {"PIP_EXTRA_INDEX_URL": "old-extra", "UV_INDEX": "old-uv-index", "PIP_FIND_LINKS": "old-links", "UV_FIND_LINKS": "old-uv-links", "KEEP": "1"}},
    )
    assert calls[2][2]["custom_env"] is not custom_env
    assert custom_env == original_env

    if expected_index is None:
        assert "PIP_INDEX_URL" not in calls[1][2]["custom_env"]
    else:
        assert expected_index in calls[1][2]["custom_env"]["PIP_INDEX_URL"]
        assert expected_index in calls[1][2]["custom_env"]["UV_DEFAULT_INDEX"]

    if expected_clean_env:
        assert "PIP_EXTRA_INDEX_URL" not in calls[1][2]["custom_env"]
        assert "UV_INDEX" not in calls[1][2]["custom_env"]
        assert "PIP_FIND_LINKS" not in calls[1][2]["custom_env"]
        assert "UV_FIND_LINKS" not in calls[1][2]["custom_env"]
    else:
        assert calls[1][2]["custom_env"]["PIP_EXTRA_INDEX_URL"] == "old-extra"
        assert calls[1][2]["custom_env"]["UV_INDEX"] == "old-uv-index"
        assert calls[1][2]["custom_env"]["PIP_FIND_LINKS"] == "old-links"
        assert calls[1][2]["custom_env"]["UV_FIND_LINKS"] == "old-uv-links"


def test_check_onnxruntime_gpu_skips_and_wraps_install_errors(monkeypatch):
    monkeypatch.setattr(onnx_check_fixer, "need_install_ort_ver", lambda skip_if_missing: None)
    monkeypatch.setattr(onnx_check_fixer, "pip_install", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should skip")))
    onnx_check.check_onnxruntime_gpu()

    monkeypatch.setattr(onnx_check_fixer, "need_install_ort_ver", lambda skip_if_missing: onnx_check.OrtType.CU130)
    monkeypatch.setattr(onnx_check_fixer, "run_cmd", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(onnx_check_fixer, "pip_install", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("pip bad")))
    with pytest.raises(RuntimeError, match="Onnxrunime GPU"):
        onnx_check.check_onnxruntime_gpu()
