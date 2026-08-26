"""WebUI 环境信息采集和导出测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sd_webui_all_in_one.base_manager import base as base_module
from sd_webui_all_in_one.base_manager.base import environment as base_environment
from sd_webui_all_in_one.base_manager import environment_info as environment_info_module
from sd_webui_all_in_one.base_manager import (
    comfyui_base,
    fooocus_base,
    invokeai_base,
    qwen_tts_webui_base,
    sd_scripts_base,
    sd_trainer_base,
    sd_webui_base,
)
from sd_webui_all_in_one.base_manager.base import (
    CpuEnvironmentInfo,
    HostEnvironmentInfo,
    ManagerEnvironmentInfo,
    OperatingSystemEnvironmentInfo,
    PyTorchEnvironmentInfo,
)
from sd_webui_all_in_one.base_manager.environment_info import WebUiEnvironmentInfo
from sd_webui_all_in_one.base_manager.snapshot import (
    PythonSnapshot,
    SystemSnapshot,
    WebUiIdentitySnapshot,
    WebUiSnapshot,
)


def _host_environment() -> HostEnvironmentInfo:
    return HostEnvironmentInfo(
        manager=ManagerEnvironmentInfo(name="sd-webui-all-in-one", version="test"),
        operating_system=OperatingSystemEnvironmentInfo(
            platform="TestOS-1",
            system="TestOS",
            release="1",
            version="1.0",
            machine="x86_64",
        ),
        cpu=CpuEnvironmentInfo(name="Test CPU", logical_cores=8),
        gpus=[],
        pytorch=PyTorchEnvironmentInfo(
            installed_version="2.7.0+cu128",
            installed_type="cu128",
            available_types=["all", "cpu", "cu128"],
            status="compatible",
            is_compatible=True,
            message="ok",
        ),
        collection_errors=[],
    )


def _snapshot(path: Path) -> WebUiSnapshot:
    return WebUiSnapshot(
        schema_version=1,
        created_at="2026-08-04T00:00:00Z",
        webui=WebUiIdentitySnapshot(name="Demo", type="demo", path=path),
        python=PythonSnapshot(version="3.11.0", implementation="CPython", executable=Path("/python"), platform="linux"),
        system=SystemSnapshot(system="Linux", architecture="x86_64"),
    )


def test_collect_host_environment_info_normalizes_hardware(monkeypatch):
    monkeypatch.setattr(base_environment.platform, "platform", lambda: "TestOS-1")
    monkeypatch.setattr(base_environment.platform, "system", lambda: "TestOS")
    monkeypatch.setattr(base_environment.platform, "release", lambda: "1")
    monkeypatch.setattr(base_environment.platform, "version", lambda: "1.0")
    monkeypatch.setattr(base_environment.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(base_environment.platform, "processor", lambda: "Test CPU")
    monkeypatch.setattr(base_environment.os, "cpu_count", lambda: 16)
    monkeypatch.setattr(
        base_environment,
        "get_gpu_list",
        lambda: [
            {
                "Name": "Test GPU",
                "AdapterCompatibility": "Vendor",
                "AdapterRAM": "8589934592",
                "DriverVersion": "1.2.3",
            }
        ],
    )
    monkeypatch.setattr(
        base_environment,
        "check_torch_version_status",
        lambda: {
            "available_types": ["all", "cpu", "cu128"],
            "gpu_list": [],
            "has_gpu": True,
            "installed_version": "2.7.0+cu128",
            "installed_type": "cu128",
            "status": "compatible",
            "is_compatible": True,
            "message": "ok",
        },
    )

    info = base_module.collect_host_environment_info()

    assert info.operating_system.platform == "TestOS-1"
    assert info.cpu == CpuEnvironmentInfo(name="Test CPU", logical_cores=16)
    assert info.gpus[0].name == "Test GPU"
    assert info.gpus[0].memory_bytes == 8 * 1024**3
    assert info.pytorch.installed_type == "cu128"
    assert info.collection_errors == []


def test_collect_host_environment_info_keeps_partial_results(monkeypatch):
    monkeypatch.setattr(base_environment, "get_gpu_list", lambda: (_ for _ in ()).throw(RuntimeError("gpu failed")))
    monkeypatch.setattr(base_environment, "check_torch_version_status", lambda: (_ for _ in ()).throw(RuntimeError("torch failed")))

    info = base_module.collect_host_environment_info()

    assert info.gpus == []
    assert info.pytorch.status == "unknown"
    assert info.pytorch.is_compatible is None
    assert [(item.component, item.message) for item in info.collection_errors] == [
        ("gpu", "gpu failed"),
        ("pytorch", "torch failed"),
    ]


def test_environment_info_build_and_save_contract(monkeypatch, tmp_path):
    snapshot = _snapshot(tmp_path / "webui")
    monkeypatch.setattr(environment_info_module, "collect_host_environment_info", _host_environment)

    info = environment_info_module.build_webui_environment_info(snapshot)
    output = tmp_path / "reports" / "environment.json"

    assert info.schema_version == 1
    assert info.created_at == snapshot.created_at
    assert environment_info_module.save_webui_environment_info(info, output) == output
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["environment"]["manager"]["version"] == "test"
    assert data["snapshot"]["webui"]["path"] == (tmp_path / "webui").as_posix()

    with pytest.raises(FileExistsError):
        environment_info_module.save_webui_environment_info(info, output)
    assert environment_info_module.save_webui_environment_info(info, output, overwrite=True) == output

    with pytest.raises(IsADirectoryError):
        environment_info_module.save_webui_environment_info(info, tmp_path)


@pytest.mark.parametrize(
    ("module", "function_name", "snapshot_name"),
    [
        (sd_webui_base, "get_sd_webui_environment_info", "get_sd_webui_snapshot"),
        (comfyui_base, "get_comfyui_environment_info", "get_comfyui_snapshot"),
        (fooocus_base, "get_fooocus_environment_info", "get_fooocus_snapshot"),
        (invokeai_base, "get_invokeai_environment_info", "get_invokeai_snapshot"),
        (sd_trainer_base, "get_sd_trainer_environment_info", "get_sd_trainer_snapshot"),
        (sd_scripts_base, "get_sd_scripts_environment_info", "get_sd_scripts_snapshot"),
        (qwen_tts_webui_base, "get_qwen_tts_webui_environment_info", "get_qwen_tts_webui_snapshot"),
    ],
)
def test_product_environment_info_combines_own_snapshot(monkeypatch, tmp_path, module, function_name, snapshot_name):
    snapshot = _snapshot(tmp_path)
    calls = []
    result = WebUiEnvironmentInfo(
        schema_version=1,
        created_at=snapshot.created_at,
        environment=_host_environment(),
        snapshot=snapshot,
    )
    monkeypatch.setattr(module, snapshot_name, lambda path, include_packages: calls.append((path, include_packages)) or snapshot)
    monkeypatch.setattr(module, "build_webui_environment_info", lambda value: calls.append(value) or result)

    actual = getattr(module, function_name)(tmp_path, include_packages=False)

    assert actual is result
    assert calls == [(tmp_path, False), snapshot]
