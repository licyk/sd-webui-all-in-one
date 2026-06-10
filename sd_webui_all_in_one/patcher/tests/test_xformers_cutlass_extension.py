import importlib
import sys
from importlib import metadata

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher_ext import xformers_cutlass


@pytest.fixture(autouse=True)
def clean_xformers_cutlass_patch():
    uninstall_import_hook()
    monkey_zoo.clear()
    _clear_xformers_modules()
    yield
    uninstall_import_hook()
    monkey_zoo.clear()
    _clear_xformers_modules()


def test_apply_from_config_patches_cutlass_on_import(monkeypatch, tmp_path):
    _create_fake_xformers(monkeypatch, tmp_path)
    _set_package_versions(monkeypatch, torch="2.9.0", xformers="0.0.33")

    assert xformers_cutlass.apply_from_config({"enabled": True}) is True

    module = importlib.import_module(xformers_cutlass.TARGET_MODULE)

    assert module.FwOp.CUDA_MAXIMUM_COMPUTE_CAPABILITY == xformers_cutlass.TARGET_CAPABILITY
    assert module.BwOp.CUDA_MAXIMUM_COMPUTE_CAPABILITY == xformers_cutlass.TARGET_CAPABILITY
    assert xformers_cutlass.is_xformers_cutlass_patch_active() is True


def test_version_gate_accepts_local_and_post_versions(monkeypatch):
    _set_package_versions(monkeypatch, torch="2.9.0+cu129", xformers="0.0.33.post1")

    assert xformers_cutlass.should_patch_xformers_cutlass() is True


@pytest.mark.parametrize(
    ("torch_version", "xformers_version"),
    [
        ("2.8.9", "0.0.33"),
        ("2.9.0", "0.0.32"),
    ],
)
def test_apply_from_config_skips_when_versions_are_too_old(monkeypatch, tmp_path, torch_version, xformers_version):
    _create_fake_xformers(monkeypatch, tmp_path)
    _set_package_versions(monkeypatch, torch=torch_version, xformers=xformers_version)

    assert xformers_cutlass.apply_from_config({"enabled": True}) is False

    module = importlib.import_module(xformers_cutlass.TARGET_MODULE)

    assert module.FwOp.CUDA_MAXIMUM_COMPUTE_CAPABILITY == (9, 0)
    assert module.BwOp.CUDA_MAXIMUM_COMPUTE_CAPABILITY == (9, 0)
    assert xformers_cutlass.is_xformers_cutlass_patch_active() is False


def test_apply_from_config_skips_when_package_version_is_missing(monkeypatch, tmp_path):
    _create_fake_xformers(monkeypatch, tmp_path)
    _set_package_versions(monkeypatch, torch="2.9.0", xformers=None)

    assert xformers_cutlass.apply_from_config({"enabled": True}) is False

    module = importlib.import_module(xformers_cutlass.TARGET_MODULE)

    assert module.FwOp.CUDA_MAXIMUM_COMPUTE_CAPABILITY == (9, 0)
    assert module.BwOp.CUDA_MAXIMUM_COMPUTE_CAPABILITY == (9, 0)


def test_apply_from_config_patches_already_imported_cutlass(monkeypatch, tmp_path):
    _create_fake_xformers(monkeypatch, tmp_path)
    module = importlib.import_module(xformers_cutlass.TARGET_MODULE)
    assert module.FwOp.CUDA_MAXIMUM_COMPUTE_CAPABILITY == (9, 0)
    assert module.BwOp.CUDA_MAXIMUM_COMPUTE_CAPABILITY == (9, 0)

    _set_package_versions(monkeypatch, torch="2.9.0", xformers="0.0.33")

    assert xformers_cutlass.apply_from_config({"enabled": True}) is True
    assert module.FwOp.CUDA_MAXIMUM_COMPUTE_CAPABILITY == xformers_cutlass.TARGET_CAPABILITY
    assert module.BwOp.CUDA_MAXIMUM_COMPUTE_CAPABILITY == xformers_cutlass.TARGET_CAPABILITY


def test_apply_from_config_deduplicates_registered_module_patch(monkeypatch, tmp_path):
    _create_fake_xformers(monkeypatch, tmp_path)
    _set_package_versions(monkeypatch, torch="2.9.0", xformers="0.0.33")

    assert xformers_cutlass.apply_from_config({"enabled": True}) is True
    assert xformers_cutlass.apply_from_config({"enabled": True}) is True

    monkey = monkey_zoo[xformers_cutlass.TARGET_MODULE]

    assert monkey is not None
    assert len(monkey.module_patches) == 1


def test_apply_from_config_ignores_disabled_config(monkeypatch):
    _set_package_versions(monkeypatch, torch="2.9.0", xformers="0.0.33")

    assert xformers_cutlass.apply_from_config({"enabled": False}) is False
    assert xformers_cutlass.TARGET_MODULE not in monkey_zoo


def _create_fake_xformers(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(tmp_path))
    for package in (
        tmp_path / "xformers",
        tmp_path / "xformers" / "ops",
        tmp_path / "xformers" / "ops" / "fmha",
    ):
        package.mkdir(parents=True, exist_ok=True)
        (package / "__init__.py").write_text("", encoding="utf-8")

    (tmp_path / "xformers" / "ops" / "fmha" / "cutlass.py").write_text(
        """
class FwOp:
    CUDA_MAXIMUM_COMPUTE_CAPABILITY = (9, 0)


class BwOp:
    CUDA_MAXIMUM_COMPUTE_CAPABILITY = FwOp.CUDA_MAXIMUM_COMPUTE_CAPABILITY
""".lstrip(),
        encoding="utf-8",
    )
    importlib.invalidate_caches()


def _set_package_versions(monkeypatch, *, torch: str | None, xformers: str | None) -> None:
    versions = {
        "torch": torch,
        "xformers": xformers,
    }

    def fake_version(package: str) -> str:
        version = versions.get(package)
        if version is None:
            raise metadata.PackageNotFoundError(package)
        return version

    monkeypatch.setattr(xformers_cutlass.metadata, "version", fake_version)


def _clear_xformers_modules() -> None:
    for module_name in list(sys.modules):
        if module_name == "xformers" or module_name.startswith("xformers."):
            sys.modules.pop(module_name, None)
