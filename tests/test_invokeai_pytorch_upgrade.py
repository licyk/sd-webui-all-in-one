from pathlib import Path

from sd_webui_all_in_one.base_manager.invokeai_base import components, lifecycle

INVOKEAI_6_14_REQUIRES = [
    'torch<3.0,>=2.7.0; sys_platform != "darwin"',
    'torch<2.8.0,>=2.7.0; sys_platform == "darwin"',
    "torchsde",
    "torchvision",
    'xformers>=0.0.28.post1; sys_platform != "darwin" and extra == "xformers"',
    'torch==2.7.1+cu128; (sys_platform != "linux" or platform_machine != "aarch64") and extra == "cuda"',
]


def test_invokeai_torch_version_specs_only_keep_applicable_markers(monkeypatch):
    monkeypatch.setattr(lifecycle.importlib.metadata, "requires", lambda name: INVOKEAI_6_14_REQUIRES if name == "invokeai" else [])
    monkeypatch.setattr(lifecycle, "get_parse_bindings", lambda: {"sys_platform": "linux", "platform_machine": "x86_64"})

    assert lifecycle.get_invokeai_torch_version_specs() == [("<", "3.0"), (">=", "2.7.0")]
    assert lifecycle.get_invokeai_require_torch_version() == "2.7.0"

    monkeypatch.setattr(lifecycle, "get_parse_bindings", lambda: {"sys_platform": "darwin", "platform_machine": "arm64"})
    assert lifecycle.get_invokeai_torch_version_specs() == [("<", "2.8.0"), (">=", "2.7.0")]


def test_invokeai_torch_version_specs_return_none_when_missing(monkeypatch):
    def missing(_name):
        raise lifecycle.importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(lifecycle.importlib.metadata, "requires", missing)

    assert lifecycle.get_invokeai_torch_version_specs() is None
    assert lifecycle.get_invokeai_require_torch_version() == "2.2.2"


def test_invokeai_mirror_type_uses_pytorch_version_table(monkeypatch):
    calls = []
    monkeypatch.setattr(lifecycle, "get_invokeai_torch_version_specs", lambda: [("<", "3.0"), (">=", "2.7.0")])
    monkeypatch.setattr(components, "auto_detect_available_pytorch_type", lambda: "cu130")
    monkeypatch.setattr(
        components,
        "find_pytorch_info_for_torch_requirement",
        lambda **kwargs: calls.append(kwargs) or {"name": "Torch 2.14.0 (CUDA 13.0) + xFormers 0.0.35", "dtype": "cu130"},
    )
    monkeypatch.setattr(components, "get_pytorch_mirror_type", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("should not fall back")))

    assert components.get_pytorch_mirror_type_for_ivnokeai("cuda") == "cu130"
    assert calls == [{"device_category": "cuda", "torch_specs": [("<", "3.0"), (">=", "2.7.0")], "preferred_dtype": "cu130"}]


def test_invokeai_mirror_type_falls_back_when_table_has_no_match(monkeypatch):
    monkeypatch.setattr(lifecycle, "get_invokeai_torch_version_specs", lambda: [(">=", "9.0")])
    monkeypatch.setattr(lifecycle, "get_invokeai_require_torch_version", lambda: "9.0")
    monkeypatch.setattr(components, "auto_detect_available_pytorch_type", lambda: "cu130")
    monkeypatch.setattr(components, "find_pytorch_info_for_torch_requirement", lambda **_kwargs: None)
    monkeypatch.setattr(components, "get_pytorch_mirror_type", lambda torch_ver, device_type: f"{device_type}-{torch_ver}")

    assert components.get_pytorch_mirror_type_for_ivnokeai("cuda") == "cuda-9.0"


def _patch_sync(monkeypatch, calls, xformers_installed):
    monkeypatch.setattr(components.importlib.metadata, "version", lambda name: "6.14.2" if name == "invokeai" else "0")
    monkeypatch.setattr(lifecycle, "get_invokeai_require_torch_version", lambda: "2.7.0")
    monkeypatch.setattr(components, "get_pytorch_mirror_type_for_ivnokeai", lambda _device_type: "cu130")
    monkeypatch.setattr(components, "prepare_pytorch_install_info", lambda **kwargs: (None, None, {"TORCH": kwargs["pytorch_mirror_type"]}))
    monkeypatch.setattr(components, "get_pypi_mirror_config", lambda use_cn_mirror: {"PIP": str(use_cn_mirror)})
    monkeypatch.setattr(components, "get_pytorch_for_invokeai", lambda: "torch<3.0,>=2.7.0 torchvision")
    monkeypatch.setattr(components, "get_xformers_for_invokeai", lambda: "xformers>=0.0.28.post1")
    monkeypatch.setattr(components, "get_package_version_from_library", lambda name: "0.0.31.post1" if name == "xformers" and xformers_installed else None)
    monkeypatch.setattr(components, "pip_install", lambda *args, **kwargs: calls.append(("pip", args)))
    monkeypatch.setattr(components, "run_cmd", lambda command: calls.append(("run", command)))


def test_invokeai_sync_upgrade_passes_upgrade_to_pytorch_install(monkeypatch):
    calls = []
    _patch_sync(monkeypatch, calls, xformers_installed=True)
    monkeypatch.setattr(components, "install_pytorch", lambda **kwargs: calls.append(("pytorch", kwargs["torch_package"], kwargs["custom_env"])))

    components.sync_invokeai_component(device_type="cuda", upgrade=True, use_pypi_mirror=False, use_uv=True)

    assert calls[0] == ("pytorch", "torch<3.0,>=2.7.0 torchvision xformers>=0.0.28.post1 --upgrade", {"TORCH": "cu130"})
    assert calls[1] == ("pip", ("invokeai==6.14.2",))
    assert not any(call[0] == "run" for call in calls)


def test_invokeai_sync_without_upgrade_keeps_installed_pytorch(monkeypatch):
    calls = []
    _patch_sync(monkeypatch, calls, xformers_installed=True)
    monkeypatch.setattr(components, "install_pytorch", lambda **kwargs: calls.append(("pytorch", kwargs["torch_package"])))

    components.sync_invokeai_component(device_type="cuda", use_pypi_mirror=False, use_uv=True)

    assert calls[0] == ("pytorch", "torch<3.0,>=2.7.0 torchvision xformers>=0.0.28.post1")


def test_invokeai_sync_upgrade_removes_stale_xformers_when_xformers_install_fails(monkeypatch):
    calls = []
    _patch_sync(monkeypatch, calls, xformers_installed=True)

    def fake_install_pytorch(**_kwargs):
        raise RuntimeError("no matching xformers")

    monkeypatch.setattr(components, "install_pytorch", fake_install_pytorch)
    monkeypatch.setattr(components, "install_pytorch_with_fallback", lambda **kwargs: calls.append(("pytorch_fallback", kwargs["torch_package"])))

    components.sync_invokeai_component(device_type="cuda", upgrade=True, use_pypi_mirror=False, use_uv=True)

    assert calls[0] == ("pytorch_fallback", "torch<3.0,>=2.7.0 torchvision --upgrade")
    assert calls[1][0] == "run"
    assert calls[1][1][1:] == ["-m", "pip", "uninstall", "xformers", "-y"]
    assert Path(calls[1][1][0]).name.startswith("python")


def test_invokeai_update_forwards_upgrade_to_sync(monkeypatch):
    calls = []
    monkeypatch.setattr(components, "pip_install", lambda *args, **kwargs: calls.append(("pip", args)))
    monkeypatch.setattr(components, "sync_invokeai_component", lambda **kwargs: calls.append(("sync", kwargs)))
    monkeypatch.setattr(lifecycle, "get_env_pytorch_type", lambda: "cuda")

    lifecycle.update_invokeai(use_pypi_mirror=False, use_uv=True)

    assert calls == [
        ("pip", ("invokeai", "--no-deps", "--upgrade")),
        ("sync", {"device_type": "cuda", "upgrade": True, "use_pypi_mirror": False, "use_uv": True}),
    ]


def test_invokeai_sync_adds_device_all_and_skips_xformers_for_amd_multi_arch(monkeypatch):
    calls = []
    _patch_sync(monkeypatch, calls, xformers_installed=True)
    monkeypatch.setattr(components, "get_pytorch_mirror_type_for_ivnokeai", lambda _device_type: "rocm7")
    monkeypatch.setattr(components, "install_pytorch", lambda **_kwargs: (_ for _ in ()).throw(AssertionError("xformers should not be attempted")))
    monkeypatch.setattr(components, "install_pytorch_with_fallback", lambda **kwargs: calls.append(("pytorch_fallback", kwargs["torch_package"], kwargs["custom_env"])))

    components.sync_invokeai_component(device_type="rocm", upgrade=True, use_pypi_mirror=False, use_uv=True)

    assert calls[0] == ("pytorch_fallback", "torch[device-all]<3.0,>=2.7.0 torchvision[device-all] --upgrade", {"TORCH": "rocm7"})
    # 旧版 xFormers 与升级后的 PyTorch 不兼容, 需要卸载
    assert calls[1][0] == "run"
    assert calls[1][1][1:] == ["-m", "pip", "uninstall", "xformers", "-y"]
    assert calls[2] == ("pip", ("invokeai==6.14.2",))


def test_invokeai_sync_skips_xformers_without_removing_on_fresh_install(monkeypatch):
    calls = []
    _patch_sync(monkeypatch, calls, xformers_installed=False)
    monkeypatch.setattr(components, "get_pytorch_mirror_type_for_ivnokeai", lambda _device_type: "rocm10")
    monkeypatch.setattr(components, "install_pytorch_with_fallback", lambda **kwargs: calls.append(("pytorch_fallback", kwargs["torch_package"])))

    components.sync_invokeai_component(device_type="rocm", use_pypi_mirror=False, use_uv=True)

    assert calls == [
        ("pytorch_fallback", "torch[device-all]<3.0,>=2.7.0 torchvision[device-all]"),
        ("pip", ("invokeai==6.14.2",)),
    ]
