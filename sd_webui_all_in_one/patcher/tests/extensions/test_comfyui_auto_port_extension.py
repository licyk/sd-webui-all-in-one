import importlib
import sys
import textwrap

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher_ext import comfyui_auto_port


@pytest.fixture(autouse=True)
def clean_import_state(monkeypatch):
    uninstall_import_hook()
    monkey_zoo.clear()
    _clear_comfy_modules()
    before_path = list(sys.path)
    yield
    uninstall_import_hook()
    monkey_zoo.clear()
    sys.path[:] = before_path
    _clear_comfy_modules()


def test_patch_adjusts_comfyui_default_port_on_import(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        "sd_webui_all_in_one.utils.find_port",
        lambda port: calls.append(port) or 8190,
    )
    _create_fake_comfy_cli_args(monkeypatch, tmp_path)

    comfyui_auto_port.patch_comfyui_auto_port()
    module = importlib.import_module(comfyui_auto_port.TARGET_MODULE)

    assert calls == [8188]
    assert module.args.port == 8190


def test_patch_preserves_non_default_comfyui_port(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "sd_webui_all_in_one.utils.find_port",
        lambda _port: (_ for _ in ()).throw(AssertionError("find_port should not be called")),
    )
    _create_fake_comfy_cli_args(monkeypatch, tmp_path, port=9000)

    comfyui_auto_port.patch_comfyui_auto_port()
    module = importlib.import_module(comfyui_auto_port.TARGET_MODULE)

    assert module.args.port == 9000


def test_patch_adjusts_already_imported_comfyui_module(monkeypatch, tmp_path):
    monkeypatch.setattr("sd_webui_all_in_one.utils.find_port", lambda _port: 8189)
    _create_fake_comfy_cli_args(monkeypatch, tmp_path)
    module = importlib.import_module(comfyui_auto_port.TARGET_MODULE)

    comfyui_auto_port.patch_comfyui_auto_port()

    assert module.args.port == 8189


def test_patch_registration_is_deduplicated():
    comfyui_auto_port.patch_comfyui_auto_port()
    comfyui_auto_port.patch_comfyui_auto_port()

    monkey = monkey_zoo[comfyui_auto_port.TARGET_MODULE]
    assert monkey is not None
    assert len(monkey.module_patches) == 1
    assert comfyui_auto_port.is_comfyui_auto_port_patch_registered() is True


def test_apply_from_config_ignores_disabled_config():
    comfyui_auto_port.apply_from_config({"enabled": False})

    assert comfyui_auto_port.TARGET_MODULE not in monkey_zoo


def _create_fake_comfy_cli_args(monkeypatch, tmp_path, *, port=8188):
    package = tmp_path / "comfy"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "cli_args.py").write_text(
        textwrap.dedent(
            f"""
            import argparse

            parser = argparse.ArgumentParser()
            parser.add_argument("--port", type=int, default=8188)
            args = parser.parse_args([])
            args.port = {port}
            """
        ).lstrip(),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()


def _clear_comfy_modules():
    for module_name in list(sys.modules):
        if module_name == "comfy" or module_name.startswith("comfy."):
            sys.modules.pop(module_name, None)
