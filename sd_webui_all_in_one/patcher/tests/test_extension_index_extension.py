import importlib
import importlib.util
import sys
import textwrap

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher_ext.extension_index import (
    A1111_EXTENSION_INDEX_URLS,
    COMFYUI_MANAGER_MIRROR_PREFIX,
    COMFYUI_MANAGER_RAW_PREFIX,
    apply_from_config,
    patch_extension_index_a1111,
    patch_extension_index_comfyui_manager,
)


@pytest.fixture(autouse=True)
def clean_import_state():
    uninstall_import_hook()
    monkey_zoo.clear()
    before_path = list(sys.path)
    yield
    uninstall_import_hook()
    monkey_zoo.clear()
    sys.path[:] = before_path
    for name in list(sys.modules):
        if (
            name == "modules"
            or name.startswith("modules.")
            or name in {"ComfyUI-Manager", "ComfyUI-Manager-main"}
        ):
            sys.modules.pop(name, None)


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def load_module_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_patch_extension_index_a1111_rewrites_known_urls(tmp_path):
    write_file(tmp_path / "modules" / "__init__.py", "")
    write_file(
        tmp_path / "modules" / "ui_extensions.py",
        f"""
        URLS = {list(A1111_EXTENSION_INDEX_URLS)!r}
        """,
    )
    sys.path.insert(0, str(tmp_path))

    patch_extension_index_a1111("https://mirror.example/extensions.json")
    module = importlib.import_module("modules.ui_extensions")

    assert module.URLS == ["https://mirror.example/extensions.json"] * len(A1111_EXTENSION_INDEX_URLS)


def test_patch_extension_index_comfyui_manager_rewrites_bytecode_and_get_data(tmp_path):
    module_path = tmp_path / "ComfyUI-Manager.py"
    write_file(
        module_path,
        f"""
        def default_cache_update():
            def get_cache():
                return {COMFYUI_MANAGER_RAW_PREFIX!r} + "custom-node-list.json"
            return get_cache()

        def get_data(uri):
            return uri
        """,
    )

    patch_extension_index_comfyui_manager()
    module = load_module_from_path("ComfyUI-Manager", module_path)

    assert module.default_cache_update() == COMFYUI_MANAGER_MIRROR_PREFIX + "custom-node-list.json"
    assert module.get_data(COMFYUI_MANAGER_RAW_PREFIX + "model-list.json") == (
        COMFYUI_MANAGER_MIRROR_PREFIX + "model-list.json"
    )


def test_patch_extension_index_comfyui_manager_supports_custom_prefixes(tmp_path):
    module_path = tmp_path / "ComfyUI-Manager-main.py"
    write_file(
        module_path,
        """
        def default_cache_update():
            def get_cache():
                return "https://source.example/main/" + "data.json"
            return get_cache()

        def get_data(uri):
            return uri
        """,
    )

    patch_extension_index_comfyui_manager(
        "https://mirror.example/main/",
        source_prefix="https://source.example/main/",
    )
    module = load_module_from_path("ComfyUI-Manager-main", module_path)

    assert module.default_cache_update() == "https://mirror.example/main/data.json"
    assert module.get_data("https://source.example/main/extra.json") == "https://mirror.example/main/extra.json"


def test_apply_from_config_enables_selected_extension_index_patches(tmp_path):
    write_file(tmp_path / "modules" / "__init__.py", "")
    write_file(
        tmp_path / "modules" / "ui_extensions.py",
        f"""
        URL = {A1111_EXTENSION_INDEX_URLS[0]!r}
        """,
    )
    comfyui_manager_path = tmp_path / "ComfyUI-Manager.py"
    write_file(
        comfyui_manager_path,
        f"""
        def default_cache_update():
            def get_cache():
                return {COMFYUI_MANAGER_RAW_PREFIX!r} + "data.json"
            return get_cache()

        def get_data(uri):
            return uri
        """,
    )
    sys.path.insert(0, str(tmp_path))

    apply_from_config(
        {
            "extension_index_url": "https://mirror.example/a1111.json",
            "comfyui_manager": True,
        }
    )

    ui_extensions = importlib.import_module("modules.ui_extensions")
    comfyui_manager = load_module_from_path("ComfyUI-Manager", comfyui_manager_path)

    assert ui_extensions.URL == "https://mirror.example/a1111.json"
    assert comfyui_manager.default_cache_update() == COMFYUI_MANAGER_MIRROR_PREFIX + "data.json"
