"""WebUI PyTorch 版本检查与安装测试"""

import sys
from pathlib import Path

import pytest

from sd_webui_all_in_one.base_manager import base as base_module
from sd_webui_all_in_one.base_manager.base import pytorch as base_pytorch
from sd_webui_all_in_one.pytorch_manager import version_manager


def _patch_update_detection(monkeypatch, recommended="cpu"):
    """隔离更新检查中的硬件检测, 返回记录 find_pytorch_update_target 调用的列表"""
    monkeypatch.setattr(base_pytorch, "get_gpu_list", lambda: [])
    monkeypatch.setattr(base_pytorch, "auto_detect_available_pytorch_type", lambda _gpu_list=None: recommended)
    monkeypatch.setattr(base_pytorch, "export_pytorch_list", lambda _gpu_list=None: [])


def test_install_pytorch_for_webui_only_installs_missing_packages(monkeypatch):
    calls = []

    def fake_version(name):
        if name == "torch":
            return "2.0.0"
        return None

    monkeypatch.setattr(base_pytorch, "get_package_version_from_library", fake_version)
    monkeypatch.setattr(base_pytorch, "install_pytorch", lambda **kwargs: calls.append(kwargs))

    base_pytorch.install_pytorch_for_webui("torch==2.0.0", "xformers==0.0.1", {"PIP_INDEX_URL": "x"}, use_uv=False)

    assert calls == [
        {
            "torch_package": "torch==2.0.0",
            "xformers_package": "xformers==0.0.1",
            "custom_env": {"PIP_INDEX_URL": "x"},
            "use_uv": False,
        }
    ]

    calls.clear()
    monkeypatch.setattr(base_pytorch, "get_package_version_from_library", lambda _name: "installed")
    base_pytorch.install_pytorch_for_webui("torch", "xformers")
    assert calls == []


@pytest.mark.parametrize(
    ("current_version", "latest_spec", "expected_dtype", "expected"),
    [
        ("2.7.0+cu128", "torch==2.8.0+cu128 torchvision==0.23.0+cu128", "cu128", True),
        ("2.8.0+cu128", "torch==2.8.0+cu128 torchvision==0.23.0+cu128", "cu128", False),
        ("2.9.0", "torch==2.8.0 torchvision==0.23.0", "all", False),
        ("2.7.0+custom", "torch==2.8.0 torchvision==0.23.0", "all", True),
    ],
)
def test_check_pytorch_version(monkeypatch, current_version, latest_spec, expected_dtype, expected):
    calls = []
    _patch_update_detection(monkeypatch)
    monkeypatch.setattr(base_pytorch, "get_package_version_from_library", lambda name: current_version if name == "torch" else "")
    monkeypatch.setattr(
        base_pytorch,
        "find_pytorch_update_target",
        lambda dtype, _recommended, pytorch_list=None: calls.append(dtype) or {"dtype": dtype, "torch_ver": latest_spec},
    )

    assert base_module.check_pytorch_version() is expected
    assert calls == [expected_dtype]


def test_check_pytorch_version_treats_missing_torch_as_needing_update(monkeypatch):
    def missing_torch(_name):
        return None

    _patch_update_detection(monkeypatch)
    monkeypatch.setattr(base_pytorch, "get_package_version_from_library", missing_torch)
    monkeypatch.setattr(base_pytorch, "find_pytorch_update_target", lambda dtype, _recommended, pytorch_list=None: {"dtype": dtype, "torch_ver": "torch==2.8.0"})

    assert base_module.check_pytorch_version() is True


def test_check_pytorch_version_rejects_unversioned_latest_entry(monkeypatch):
    _patch_update_detection(monkeypatch)
    monkeypatch.setattr(base_pytorch, "get_package_version_from_library", lambda _name: "2.8.0+cpu")
    monkeypatch.setattr(base_pytorch, "find_pytorch_update_target", lambda dtype, _recommended, pytorch_list=None: {"dtype": dtype, "torch_ver": "torch torchvision"})

    with pytest.raises(ValueError, match="缺少可比较的 torch 版本"):
        base_module.check_pytorch_version()


def test_prepare_pytorch_install_info_auto_and_custom_packages(monkeypatch):
    calls = []
    latest = {
        "dtype": "cu128",
        "torch_ver": "torch==2.8.0+cu128 torchvision==0.23.0+cu128",
        "xformers_ver": "xformers==0.0.32",
        "index_mirror": {"mirror": "index-mirror", "official": "index-official"},
        "extra_index_mirror": {"mirror": "extra-mirror", "official": "extra-official"},
        "find_links": {"mirror": "links-mirror", "official": "links-official"},
    }

    monkeypatch.setattr(base_pytorch, "auto_detect_available_pytorch_type", lambda: "cu128")
    monkeypatch.setattr(base_pytorch, "find_latest_pytorch_info", lambda dtype: calls.append(("latest", dtype)) or latest)
    monkeypatch.setattr(base_pytorch, "get_pytorch_mirror", lambda dtype, use_cn_mirror=False: calls.append(("mirror", dtype, use_cn_mirror)) or (f"{dtype}-url", "extra_index_url"))

    torch_pkg, xformers_pkg, env = base_pytorch.prepare_pytorch_install_info(use_cn_mirror=True)
    assert (torch_pkg, xformers_pkg) == (latest["torch_ver"], latest["xformers_ver"])
    assert calls == [("latest", "cu128"), ("mirror", "cu128", True)]
    assert env["PIP_INDEX_URL"] == "index-mirror"
    assert env["PIP_EXTRA_INDEX_URL"].splitlines()[-1] == "cu128-url"
    assert env["PIP_FIND_LINKS"] == "links-mirror"

    calls.clear()
    monkeypatch.setattr(base_pytorch, "auto_detect_pytorch_device_category", lambda: "cuda")
    monkeypatch.setattr(base_pytorch, "get_pytorch_mirror_type", lambda torch_ver, device_type: calls.append(("type", torch_ver, device_type)) or "cu124")
    torch_pkg, xformers_pkg, env = base_pytorch.prepare_pytorch_install_info(
        custom_pytorch_package="torch==2.4.1 torchvision==0.19.1",
        custom_xformers_package="xformers==0.0.28",
        use_cn_mirror=False,
    )
    assert torch_pkg == "torch==2.4.1 torchvision==0.19.1"
    assert xformers_pkg == "xformers==0.0.28"
    assert calls == [("type", "2.4.1", "cuda"), ("mirror", "cu124", False)]
    assert env["PIP_EXTRA_INDEX_URL"] == "cu124-url"

    calls.clear()
    torch_pkg, _xformers_pkg, env = base_pytorch.prepare_pytorch_install_info(
        custom_pytorch_package="torch==2.6.0+cu126 torchvision==0.21.0+cu126",
        use_cn_mirror=True,
    )
    assert torch_pkg is not None
    assert torch_pkg.startswith("torch==2.6.0+cu126")
    assert calls == [("mirror", "cu126", True)]
    assert env["PIP_EXTRA_INDEX_URL"] == "cu126-url"

    calls.clear()
    monkeypatch.setattr(sys, "platform", "linux")
    torch_pkg, _xformers_pkg, env = base_pytorch.prepare_pytorch_install_info(
        custom_pytorch_package="torch[device-all]==2.12.0+rocm7.14.0 torchvision[device-all]==0.27.0+rocm7.14.0",
        use_cn_mirror=False,
    )
    assert torch_pkg is not None
    assert torch_pkg.startswith("torch[device-all]==2.12.0+rocm7.14.0")
    assert calls == [("mirror", "rocm7", False)]
    assert "UV_PRERELEASE" not in env

    calls.clear()
    torch_pkg, _xformers_pkg, env = base_pytorch.prepare_pytorch_install_info(
        custom_pytorch_package="torch[device-all]==2.13.0+rocm10.0.0 torchvision[device-all]==0.28.0+rocm10.0.0",
        use_cn_mirror=False,
    )
    assert calls == [("mirror", "rocm10", False)]

    # 带有 extras 且固定为预发布版本的软件包需要允许 uv 使用预发布版本
    calls.clear()
    torch_pkg, _xformers_pkg, env = base_pytorch.prepare_pytorch_install_info(
        custom_pytorch_package="torch[device-all]==2.8.0+rocm7.13.0 torchvision[device-all]==0.23.0a0+rocm7.13.0 torchaudio==2.8.0a0+rocm7.13.0",
        use_cn_mirror=False,
    )
    assert calls == [("mirror", "rocm7", False)]
    assert env["UV_PRERELEASE"] == "allow"

    calls.clear()
    torch_pkg, _xformers_pkg, env = base_pytorch.prepare_pytorch_install_info(
        custom_pytorch_package="torch==2.4.1+custom torchvision==0.19.1",
        use_cn_mirror=False,
    )
    assert calls == [("type", "2.4.1", "cuda"), ("mirror", "cu124", False)]


@pytest.mark.parametrize(
    ("platform", "torch_version", "expected_dtype"),
    [
        ("linux", "2.12.0+rocm7.14.0", "rocm7"),
        ("win32", "2.12.0+rocm7.14.0", "rocm7"),
        ("linux", "2.12.0+rocm10.0.0", "rocm10"),
        ("win32", "2.12.0+rocm10.0.0", "rocm10"),
    ],
)
def test_check_pytorch_version_normalizes_amd_multi_arch_suffix(monkeypatch, platform, torch_version, expected_dtype):
    calls = []
    _patch_update_detection(monkeypatch, recommended="rocm10")
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(base_pytorch, "get_package_version_from_library", lambda name: torch_version if name == "torch" else "")
    monkeypatch.setattr(
        base_pytorch,
        "find_pytorch_update_target",
        lambda dtype, _recommended, pytorch_list=None: calls.append(dtype) or {"dtype": dtype, "torch_ver": f"torch[device-all]=={torch_version} torchaudio==2.11.0"},
    )

    assert base_module.check_pytorch_version() is False
    assert calls == [expected_dtype]


def _torch_entry(name, dtype, torch_ver, xformers_ver=None, platform=("linux", "win32")):
    return {"name": name, "dtype": dtype, "platform": list(platform), "torch_ver": torch_ver, "xformers_ver": xformers_ver}


CROSS_VARIANT_PYTORCH_LIST = [
    _torch_entry("Torch 2.14.1 (CUDA 13.0) + xFormers", "cu130", "torch==2.14.1+cu130", "xformers==0.0.35"),
    _torch_entry("Torch 2.14.1 (CUDA 13.2)", "cu132", "torch==2.14.1+cu132"),
    _torch_entry("Torch 2.15.0 (CUDA 13.2)", "cu132", "torch==2.15.0+cu132"),
    _torch_entry("Torch 2.15.0 (CUDA 13.4)", "cu134", "torch==2.15.0+cu134"),
    _torch_entry("Torch 2.15.0 (CPU)", "cpu", "torch==2.15.0+cpu"),
    _torch_entry("Torch 2.14.1 (ROCm 7.2)", "rocm7.2", "torch==2.14.1+rocm7.2", platform=("linux",)),
    _torch_entry("Torch 2.13.0 (ROCm 7)", "rocm7", "torch[device-all]==2.13.0+rocm7.14.0"),
    _torch_entry("Torch 2.14.0 (ROCm 10)", "rocm10", "torch[device-all]==2.14.0+rocm10.1.0"),
]

CUDA_132 = ["all", "cpu", "cu126", "cu128", "cu130", "cu132"]
AMD_LINUX = ["all", "cpu", "rocm10", "rocm7", "rocm7.2"]


@pytest.mark.parametrize(
    ("installed", "available", "recommended", "has_update", "latest_version", "latest_dtype"),
    [
        # cu130 停止更新, 推荐的 cu132 存在更新的版本
        ("2.14.1+cu130", CUDA_132, "cu132", True, "2.15.0+cu132", "cu132"),
        # 已安装类型和推荐类型都有更新时选择更新的版本
        ("2.14.0+cu130", CUDA_132, "cu132", True, "2.15.0+cu132", "cu132"),
        # 推荐类型与已安装类型相同时保持原有行为
        ("2.14.1+cu130", ["all", "cpu", "cu130"], "cu130", False, "2.14.1+cu130", "cu130"),
        # 公共版本相同时不切换设备类型, 也不因本地版本号 (+cu132 < +cu134) 误报更新
        ("2.15.0+cu132", [*CUDA_132, "cu134"], "cu134", False, "2.15.0+cu132", "cu132"),
        # 推荐类型属于其他设备分类时 (如显卡检测失败) 不跨类型迁移
        ("2.14.1+cu130", CUDA_132, "cpu", False, "2.14.1+cu130", "cu130"),
        # PyTorch 官方 ROCm wheel 不迁移到 AMD 多架构 wheel
        ("2.14.1+rocm7.2", AMD_LINUX, "rocm10", False, "2.14.1+rocm7.2", "rocm7.2"),
        # AMD 多架构 wheel 内部可以迁移
        ("2.13.0+rocm7.14.0", AMD_LINUX, "rocm10", True, "2.14.0+rocm10.1.0", "rocm10"),
        # 已安装类型不受当前设备支持时回退到推荐类型, 不再报错
        ("2.15.0+cu134", CUDA_132, "cu132", False, "2.15.0+cu132", "cu132"),
    ],
)
def test_get_pytorch_update_status_considers_recommended_device_type(monkeypatch, installed, available, recommended, has_update, latest_version, latest_dtype):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(version_manager, "PYTORCH_DOWNLOAD_DICT", CROSS_VARIANT_PYTORCH_LIST)
    monkeypatch.setattr(version_manager, "SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY", False)
    monkeypatch.setattr(version_manager, "get_available_pytorch_device_type", lambda _gpu_list=None: available)
    monkeypatch.setattr(base_pytorch, "get_gpu_list", lambda: [])
    monkeypatch.setattr(base_pytorch, "auto_detect_available_pytorch_type", lambda _gpu_list=None: recommended)
    monkeypatch.setattr(base_pytorch, "get_package_version_from_library", lambda name: installed if name == "torch" else "")

    status = base_module.get_pytorch_update_status()

    installed_dtype = base_pytorch.normalize_pytorch_version_suffix(installed.partition("+")[2])
    assert status.error is None
    assert status.device_type == installed_dtype
    assert status.has_update is has_update
    assert status.latest_version == latest_version
    assert status.latest_device_type == latest_dtype
    assert status.recommended_device_type == recommended
    assert status.device_type_changed is (latest_dtype != installed_dtype)
    assert base_module.check_pytorch_version() is has_update


def test_get_pytorch_update_status_detects_gpus_once(monkeypatch):
    calls = []
    monkeypatch.setattr(base_pytorch, "get_gpu_list", lambda: calls.append("gpu_list") or ["gpu"])
    monkeypatch.setattr(base_pytorch, "auto_detect_available_pytorch_type", lambda gpu_list=None: calls.append(("auto", gpu_list)) or "cu132")
    monkeypatch.setattr(base_pytorch, "export_pytorch_list", lambda gpu_list=None: calls.append(("export", gpu_list)) or ["list"])
    monkeypatch.setattr(
        base_pytorch,
        "find_pytorch_update_target",
        lambda dtype, recommended, pytorch_list=None: calls.append(("target", dtype, recommended, pytorch_list)) or {"dtype": "cu132", "torch_ver": "torch==2.15.0+cu132"},
    )
    monkeypatch.setattr(base_pytorch, "get_package_version_from_library", lambda _name: "2.14.1+cu130")

    status = base_module.get_pytorch_update_status()

    assert calls == ["gpu_list", ("auto", ["gpu"]), ("export", ["gpu"]), ("target", "cu130", "cu132", ["list"])]
    assert status.has_update is True
    assert status.device_type_changed is True


def test_reinstall_pytorch_list_install_and_interactive_auto(monkeypatch):
    info = {
        "torch_ver": "torch==2.8.0",
        "xformers_ver": "xformers==0.0.32",
        "index_mirror": {"mirror": "index-mirror", "official": "index-official"},
        "extra_index_mirror": {"mirror": "extra-mirror", "official": "extra-official"},
        "find_links": {"mirror": "links-mirror", "official": "links-official"},
    }
    calls = []
    monkeypatch.setattr(base_pytorch, "export_pytorch_list", lambda: [info])
    monkeypatch.setattr(base_pytorch, "display_pytorch_config", lambda data: calls.append(("display", data)))
    monkeypatch.setattr(base_pytorch, "print_divider", lambda char: calls.append(("divider", char)))
    monkeypatch.setattr(base_pytorch, "query_pytorch_info_from_library", lambda pytorch_name=None, pytorch_index=None: calls.append(("query", pytorch_name, pytorch_index)) or info)
    monkeypatch.setattr(base_pytorch, "install_pytorch", lambda **kwargs: calls.append(("install", kwargs)))
    monkeypatch.setattr(base_pytorch, "uninstall_stale_pytorch_packages", lambda *packages: calls.append(("stale", packages)))

    base_module.reinstall_pytorch(list_only=True)
    assert calls[:3] == [("divider", "="), ("display", [info]), ("divider", "=")]

    calls.clear()
    base_module.reinstall_pytorch(pytorch_name="Torch CUDA", use_pypi_mirror=False, use_uv=False)
    assert calls[0] == ("query", "Torch CUDA", None)
    assert calls[1][0] == "install"
    assert calls[1][1]["torch_package"] == "torch==2.8.0"
    assert calls[1][1]["custom_env"]["PIP_INDEX_URL"] == "index-official"
    assert calls[1][1]["use_uv"] is False
    assert not any(call[0] == "stale" for call in calls)

    calls.clear()
    inputs = iter(["auto", "y"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(inputs))
    monkeypatch.setattr(base_pytorch, "get_package_version_from_library", lambda _name: "installed")
    monkeypatch.setattr(base_pytorch, "prepare_pytorch_install_info", lambda use_cn_mirror=True: ("torch-auto", "xformers-auto", {"AUTO": str(use_cn_mirror)}))
    base_module.reinstall_pytorch(interactive_mode=True, use_pypi_mirror=True, use_uv=True)

    assert calls[-2] == (
        "install",
        {
            "torch_package": ["torch-auto", "--force-reinstall"],
            "xformers_package": ["xformers-auto", "--no-deps", "--force-reinstall"],
            "custom_env": {"AUTO": "True"},
            "use_uv": True,
        },
    )
    assert calls[-1] == ("stale", ("torch-auto", "xformers-auto"))

    calls.clear()
    base_module.reinstall_pytorch(pytorch_index=1, use_uv=True, force_reinstall=True)
    assert calls[-2][1]["torch_package"] == ["torch==2.8.0", "--force-reinstall"]
    assert calls[-2][1]["xformers_package"] == ["xformers==0.0.32", "--no-deps", "--force-reinstall"]
    assert calls[-1] == ("stale", ("torch==2.8.0", "xformers==0.0.32"))


def test_uninstall_stale_pytorch_packages_only_removes_installed_unrequested_packages(monkeypatch):
    calls = []
    installed = {"torchvision", "torchaudio", "xformers"}

    def fake_version(name):
        if name not in installed:
            return None
        return "1.0"

    monkeypatch.setattr(base_pytorch, "get_package_version_from_library", fake_version)
    monkeypatch.setattr(base_pytorch, "run_cmd", lambda command: calls.append(command))

    base_pytorch.uninstall_stale_pytorch_packages("torch[device-all]==2.8.0+cu128 torchvision==0.23.0+cu128 --no-deps", None)
    assert calls == [[Path(sys.executable).as_posix(), "-m", "pip", "uninstall", "torchaudio", "xformers", "-y"]]

    calls.clear()
    installed.clear()
    base_pytorch.uninstall_stale_pytorch_packages(["torch==2.8.0"])
    assert calls == []

    installed.update({"torchvision", "torchaudio", "xformers"})
    base_pytorch.uninstall_stale_pytorch_packages("torch==2.8.0 torchvision torchaudio", ["xformers==0.0.32"])
    assert calls == []


def test_install_pytorch_with_fallback_force_reinstall_skips_dependency_completion(monkeypatch):
    install_calls = []

    def fake_install_pytorch(**kwargs):
        install_calls.append(kwargs)
        if len(install_calls) == 1:
            raise RuntimeError("first failed")

    monkeypatch.setattr(base_pytorch, "install_pytorch", fake_install_pytorch)
    monkeypatch.setattr(base_pytorch, "get_auto_pypi_mirror_config", lambda custom_env=None: {"AUTO": "1"})

    base_pytorch.install_pytorch_with_fallback(
        torch_package="torch==2.8.0+cu128",
        xformers_package=None,
        custom_env={},
        use_uv=False,
        force_reinstall=True,
    )

    assert install_calls[0]["torch_package"] == ["torch==2.8.0+cu128", "--force-reinstall"]
    assert install_calls[0]["xformers_package"] is None
    assert install_calls[1]["torch_package"] == ["torch==2.8.0+cu128", "--no-deps", "--force-reinstall"]
    # 补全依赖时不再强制重装, 避免从 PyPI 镜像源重新获取 PyTorch
    assert install_calls[2]["torch_package"] == ["torch==2.8.0+cu128"]
    assert len(install_calls) == 3


def test_install_pytorch_with_fallback_preserves_env_and_package_inputs(monkeypatch):
    calls = []
    torch_package = ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128"]
    xformers_package = ["xformers==0.0.32"]
    custom_env = {"PIP_INDEX_URL": "https://torch.example/simple", "KEEP": "1"}

    def fake_install_pytorch(**kwargs):
        calls.append(("install", kwargs))
        if len(calls) == 1:
            raise RuntimeError("first failed")

    def fake_get_auto_pypi_mirror_config(custom_env=None):
        calls.append(("mirror", custom_env))
        return {"AUTO": "1", **(custom_env or {})}

    monkeypatch.setattr(base_pytorch, "install_pytorch", fake_install_pytorch)
    monkeypatch.setattr(base_pytorch, "get_auto_pypi_mirror_config", fake_get_auto_pypi_mirror_config)

    base_pytorch.install_pytorch_with_fallback(
        torch_package=torch_package,
        xformers_package=xformers_package,
        custom_env=custom_env,
        use_uv=False,
    )

    assert torch_package == ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128"]
    assert xformers_package == ["xformers==0.0.32"]
    assert calls[1] == (
        "install",
        {
            "torch_package": ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128", "--no-deps"],
            "xformers_package": ["xformers==0.0.32", "--no-deps"],
            "custom_env": custom_env,
            "use_uv": False,
        },
    )
    assert calls[2] == ("mirror", custom_env)
    assert calls[3] == (
        "install",
        {
            "torch_package": ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128"],
            "xformers_package": ["xformers==0.0.32"],
            "custom_env": {"AUTO": "1", **custom_env},
            "use_uv": False,
        },
    )
    assert len(calls) == 4


def test_install_pytorch_with_fallback_merges_mirror_env_after_existing_fallback_fails(monkeypatch):
    install_calls = []
    mirror_calls = []
    torch_package = ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128"]
    xformers_package = ["xformers==0.0.32"]
    custom_env = {
        "PIP_INDEX_URL": "https://custom-index.example/simple",
        "PIP_EXTRA_INDEX_URL": "https://custom-extra.example/simple https://shared-extra.example/simple",
        "UV_INDEX": "https://custom-uv-extra.example/simple https://shared-extra.example/simple",
        "PIP_FIND_LINKS": "https://custom-wheels.example https://shared-wheels.example",
        "UV_FIND_LINKS": "https://custom-uv-wheels.example,https://shared-wheels.example",
        "KEEP": "1",
    }

    def fake_install_pytorch(**kwargs):
        install_calls.append(kwargs)
        if len(install_calls) in [1, 3]:
            raise RuntimeError("install failed")

    def fake_get_auto_pypi_mirror_config(custom_env=None):
        mirror_calls.append(custom_env)
        return {
            **(custom_env or {}),
            "PIP_INDEX_URL": "https://auto-index.example/simple",
            "UV_DEFAULT_INDEX": "https://auto-index.example/simple",
            "PIP_EXTRA_INDEX_URL": "https://shared-extra.example/simple https://auto-extra.example/simple",
            "UV_INDEX": "https://auto-uv-extra.example/simple https://custom-extra.example/simple",
            "PIP_FIND_LINKS": "https://shared-wheels.example https://auto-wheels.example",
            "UV_FIND_LINKS": "https://auto-uv-wheels.example,https://custom-uv-wheels.example",
        }

    monkeypatch.setattr(base_pytorch, "install_pytorch", fake_install_pytorch)
    monkeypatch.setattr(base_pytorch, "get_auto_pypi_mirror_config", fake_get_auto_pypi_mirror_config)

    base_pytorch.install_pytorch_with_fallback(
        torch_package=torch_package,
        xformers_package=xformers_package,
        custom_env=custom_env,
        use_uv=False,
    )

    assert torch_package == ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128"]
    assert xformers_package == ["xformers==0.0.32"]
    assert len(mirror_calls) == 1
    assert mirror_calls[0] is custom_env
    assert len(install_calls) == 4
    assert install_calls[1]["torch_package"] == ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128", "--no-deps"]
    assert install_calls[1]["xformers_package"] == ["xformers==0.0.32", "--no-deps"]
    assert install_calls[3]["torch_package"] == ["torch==2.8.0+cu128", "torchvision==0.23.0+cu128"]
    assert install_calls[3]["xformers_package"] == ["xformers==0.0.32"]
    assert "--no-deps" not in install_calls[3]["torch_package"]
    assert "--no-deps" not in install_calls[3]["xformers_package"]

    merged_env = install_calls[3]["custom_env"]
    assert merged_env["KEEP"] == "1"
    assert merged_env["PIP_INDEX_URL"] == "https://custom-index.example/simple"
    assert merged_env["UV_DEFAULT_INDEX"] == "https://custom-index.example/simple"
    assert (
        merged_env["PIP_EXTRA_INDEX_URL"]
        == "https://custom-extra.example/simple https://shared-extra.example/simple https://custom-uv-extra.example/simple https://auto-extra.example/simple https://auto-uv-extra.example/simple"
    )
    assert (
        merged_env["UV_INDEX"]
        == "https://custom-extra.example/simple https://shared-extra.example/simple https://custom-uv-extra.example/simple https://auto-extra.example/simple https://auto-uv-extra.example/simple"
    )
    assert merged_env["PIP_FIND_LINKS"] == "https://custom-wheels.example https://shared-wheels.example https://custom-uv-wheels.example https://auto-wheels.example https://auto-uv-wheels.example"
    assert merged_env["UV_FIND_LINKS"] == "https://custom-wheels.example,https://shared-wheels.example,https://custom-uv-wheels.example,https://auto-wheels.example,https://auto-uv-wheels.example"


def test_install_pytorch_with_fallback_uses_first_custom_extra_index_when_no_index(monkeypatch):
    install_calls = []
    custom_env = {
        "PIP_EXTRA_INDEX_URL": "https://custom-extra-a.example/simple https://custom-extra-b.example/simple",
        "UV_INDEX": "https://custom-extra-c.example/simple",
    }

    def fake_install_pytorch(**kwargs):
        install_calls.append(kwargs)
        if len(install_calls) in [1, 3]:
            raise RuntimeError("install failed")

    def fake_get_auto_pypi_mirror_config(custom_env=None):
        return {
            **(custom_env or {}),
            "PIP_EXTRA_INDEX_URL": "https://auto-extra.example/simple",
            "PIP_FIND_LINKS": "https://auto-wheels.example",
        }

    monkeypatch.setattr(base_pytorch, "install_pytorch", fake_install_pytorch)
    monkeypatch.setattr(base_pytorch, "get_auto_pypi_mirror_config", fake_get_auto_pypi_mirror_config)

    base_pytorch.install_pytorch_with_fallback(
        torch_package=["torch==2.8.0+cu128"],
        xformers_package=["xformers==0.0.32"],
        custom_env=custom_env,
        use_uv=True,
    )

    merged_env = install_calls[3]["custom_env"]
    assert merged_env["PIP_INDEX_URL"] == "https://custom-extra-a.example/simple"
    assert merged_env["UV_DEFAULT_INDEX"] == "https://custom-extra-a.example/simple"
