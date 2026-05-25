import importlib
import sys
from pathlib import Path

import pytest

onnx_check = importlib.import_module("sd_webui_all_in_one.env_check.onnxruntime_gpu_check")
fix_repo = importlib.import_module("sd_webui_all_in_one.env_check.fix_sd_webui_invaild_repo")


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
    monkeypatch.setattr(onnx_check, "get_torch_cuda_ver_fast", lambda: (torch_info[0], torch_info[1]))
    monkeypatch.setattr(onnx_check, "get_torch_cuda_ver", lambda: torch_info)
    monkeypatch.setattr(onnx_check, "get_onnxruntime_support_cuda_version", lambda: ort_info)
    monkeypatch.setattr(onnx_check.sys, "platform", platform)

    def fake_version(name):
        if name == "onnxruntime-gpu" and installed_ort:
            return "1.20.0"
        raise onnx_check.importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(onnx_check.importlib.metadata, "version", fake_version)

    assert onnx_check.need_install_ort_ver(skip_if_missing=skip_if_missing) == expected


def test_need_install_ort_ver_reads_cudnn_lazily(monkeypatch):
    monkeypatch.setattr(onnx_check, "get_torch_cuda_ver_fast", lambda: ("2.9.0", "13.0"))
    monkeypatch.setattr(onnx_check, "get_torch_cuda_ver", lambda: (_ for _ in ()).throw(AssertionError("cuDNN should not be read")))
    monkeypatch.setattr(onnx_check, "get_onnxruntime_support_cuda_version", lambda: ("13.0", "9"))

    assert onnx_check.need_install_ort_ver() is None

    calls = []
    monkeypatch.setattr(onnx_check, "get_torch_cuda_ver_fast", lambda: ("2.5.0", "12.1"))
    monkeypatch.setattr(onnx_check, "get_torch_cuda_ver", lambda: calls.append("cudnn") or ("2.5.0", "12.1", "9000"))
    monkeypatch.setattr(onnx_check, "get_onnxruntime_support_cuda_version", lambda: ("12.1", "8"))

    assert onnx_check.need_install_ort_ver() == onnx_check.OrtType.CU121CUDNN9
    assert calls == ["cudnn"]


@pytest.mark.parametrize(
    ("ort_type", "expected_spec", "expected_index"),
    [
        (onnx_check.OrtType.CU118, "onnxruntime-gpu>=1.18.1", "onnxruntime-cuda-11"),
        (onnx_check.OrtType.CU121CUDNN8, "onnxruntime-gpu==1.17.1", "onnxruntime-cuda-12"),
        (onnx_check.OrtType.CU121CUDNN9, "onnxruntime-gpu>=1.19.0,<=1.24.2", None),
        (onnx_check.OrtType.CU130, "onnxruntime-gpu>=1.24.2", "onnxruntime-cuda-13"),
    ],
)
def test_check_onnxruntime_gpu_installs_expected_package_and_env(monkeypatch, ort_type, expected_spec, expected_index):
    custom_env = {
        "PIP_EXTRA_INDEX_URL": "old-extra",
        "UV_INDEX": "old-uv-index",
        "PIP_FIND_LINKS": "old-links",
        "UV_FIND_LINKS": "old-uv-links",
        "KEEP": "1",
    }
    calls = []

    monkeypatch.setattr(onnx_check, "need_install_ort_ver", lambda skip_if_missing: ort_type)
    monkeypatch.setattr(onnx_check, "run_cmd", lambda command: calls.append(("run", command)))
    monkeypatch.setattr(onnx_check, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))

    onnx_check.check_onnxruntime_gpu(use_uv=False, skip_if_missing=True, custom_env=custom_env)

    assert calls[0] == ("run", [Path(sys.executable).as_posix(), "-m", "pip", "uninstall", "onnxruntime-gpu", "-y"])
    assert calls[1][0] == "pip"
    assert calls[1][1] == (expected_spec, "--no-cache-dir", "--no-deps")
    assert calls[1][2]["use_uv"] is False
    assert calls[1][2]["custom_env"]["KEEP"] == "1"
    assert calls[2] == ("pip", (expected_spec,), {"use_uv": False, "custom_env": {"PIP_EXTRA_INDEX_URL": "old-extra", "UV_INDEX": "old-uv-index", "PIP_FIND_LINKS": "old-links", "UV_FIND_LINKS": "old-uv-links", "KEEP": "1"}})

    if expected_index is None:
        assert "PIP_INDEX_URL" not in custom_env
        assert custom_env["PIP_EXTRA_INDEX_URL"] == "old-extra"
    else:
        assert expected_index in custom_env["PIP_INDEX_URL"]
        assert expected_index in custom_env["UV_DEFAULT_INDEX"]
        assert "PIP_EXTRA_INDEX_URL" not in custom_env
        assert "UV_INDEX" not in custom_env
        assert "PIP_FIND_LINKS" not in custom_env
        assert "UV_FIND_LINKS" not in custom_env


def test_check_onnxruntime_gpu_skips_and_wraps_install_errors(monkeypatch):
    monkeypatch.setattr(onnx_check, "need_install_ort_ver", lambda skip_if_missing: None)
    monkeypatch.setattr(onnx_check, "pip_install", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should skip")))
    onnx_check.check_onnxruntime_gpu()

    monkeypatch.setattr(onnx_check, "need_install_ort_ver", lambda skip_if_missing: onnx_check.OrtType.CU130)
    monkeypatch.setattr(onnx_check, "run_cmd", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(onnx_check, "pip_install", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("pip bad")))
    with pytest.raises(RuntimeError, match="Onnxrunime GPU"):
        onnx_check.check_onnxruntime_gpu()


def test_fix_stable_diffusion_invalid_repo_url(monkeypatch, tmp_path):
    stable_repo = tmp_path / "repositories" / "stable-diffusion-stability-ai"
    stable_repo.mkdir(parents=True)
    calls = []
    env = {"GIT_CONFIG_GLOBAL": "/tmp/global", "KEEP": "1"}

    monkeypatch.setattr(fix_repo.git_warpper, "is_git_repo", lambda path: False)
    fix_repo.fix_stable_diffusion_invaild_repo_url(tmp_path, custom_env=env.copy())
    assert calls == []

    monkeypatch.setattr(fix_repo.git_warpper, "is_git_repo", lambda path: path == stable_repo)

    def fake_run_cmd(command, custom_env=None, live=True):
        calls.append((command, custom_env, live))
        assert "GIT_CONFIG_GLOBAL" not in custom_env
        if command[-3:] == ["remote", "get-url", "origin"]:
            return "https://github.com/Stability-AI/stablediffusion.git"
        return ""

    monkeypatch.setattr(fix_repo, "run_cmd", fake_run_cmd)
    fix_repo.fix_stable_diffusion_invaild_repo_url(tmp_path, custom_env=env.copy())

    assert calls[0][0] == ["git", "-C", stable_repo.as_posix(), "remote", "get-url", "origin"]
    assert calls[1][0] == ["git", "-C", stable_repo.as_posix(), "remote", "set-url", "origin", "https://github.com/licyk/stablediffusion"]

    calls.clear()
    monkeypatch.setattr(fix_repo, "run_cmd", lambda command, custom_env=None, live=True: calls.append(command) or "https://github.com/licyk/stablediffusion")
    fix_repo.fix_stable_diffusion_invaild_repo_url(tmp_path, custom_env=env.copy())
    assert calls == [["git", "-C", stable_repo.as_posix(), "remote", "get-url", "origin"]]

    monkeypatch.setattr(fix_repo, "run_cmd", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("git bad")))
    with pytest.raises(RuntimeError, match="无效的组件仓库源"):
        fix_repo.fix_stable_diffusion_invaild_repo_url(tmp_path, custom_env=env.copy())
