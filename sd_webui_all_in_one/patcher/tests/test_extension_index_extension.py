import asyncio
import importlib
import sys
import textwrap

import pytest

import sd_webui_all_in_one_hotpatcher_ext.extension_index as extension_index_module
from sd_webui_all_in_one_hotpatcher import monkey_zoo, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher_ext.extension_index import (
    A1111_EXTENSION_INDEX_RAW_FILE_PATH,
    A1111_EXTENSION_INDEX_URLS,
    COMFYUI_MANAGER_RAW_FILE_PATH,
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
            or name
            in {
                "ComfyUI-Manager",
                "ComfyUI-Manager-main",
                "manager_core",
                "manager_server",
                "manager_util",
            }
        ):
            sys.modules.pop(name, None)


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def write_manager_core_module(path, source_prefix=COMFYUI_MANAGER_RAW_PREFIX):
    write_file(
        path,
        f"""
        DEFAULT_CHANNEL = {source_prefix!r}
        channel_dict = None
        valid_channels = {{"default", "local"}}

        def get_channel_dict():
            global channel_dict
            if channel_dict is None:
                channel_dict = {{
                    "default": {source_prefix!r},
                    "recent": {source_prefix!r} + "/node_db/new",
                    "other": "https://raw.githubusercontent.com/another/project/main",
                    "similar": {source_prefix + "-fork"!r},
                }}
                for url in channel_dict.values():
                    valid_channels.add(url)
            return channel_dict

        async def get_data_by_mode(mode, filename, channel_url=None):
            return {{
                "mode": mode,
                "filename": filename,
                "channel_url": channel_url,
            }}
        """,
    )


def write_manager_server_module(path, source_prefix=COMFYUI_MANAGER_RAW_PREFIX):
    write_file(
        path,
        f"""
        import manager_core as core

        async def get_risky_level(files, pip_packages):
            return await core.get_data_by_mode(
                "cache",
                "custom-node-list.json",
                channel_url={source_prefix!r},
            )
        """,
    )


def write_manager_util_module(path):
    write_file(
        path,
        """
        async def get_data(uri, silent=False):
            return {
                "uri": uri,
                "silent": silent,
            }
        """,
    )


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


def test_apply_from_config_auto_a1111_keeps_original_when_github_accessible(monkeypatch, tmp_path):
    write_file(tmp_path / "modules" / "__init__.py", "")
    write_file(
        tmp_path / "modules" / "ui_extensions.py",
        f"""
        URL = {A1111_EXTENSION_INDEX_URLS[1]!r}
        """,
    )
    sys.path.insert(0, str(tmp_path))
    monkeypatch.setattr(extension_index_module, "_github_direct_accessible", lambda: True)
    monkeypatch.setattr(
        extension_index_module,
        "_apply_github_raw_file_mirror",
        lambda raw_file_path: pytest.fail("mirror should not be resolved when GitHub is accessible"),
    )

    apply_from_config({"webui": {"enabled": True, "url": "auto"}})
    module = importlib.import_module("modules.ui_extensions")

    assert module.URL == A1111_EXTENSION_INDEX_URLS[1]


def test_apply_from_config_auto_a1111_uses_mirror_when_github_blocked(monkeypatch, tmp_path):
    write_file(tmp_path / "modules" / "__init__.py", "")
    write_file(
        tmp_path / "modules" / "ui_extensions.py",
        f"""
        URL = {A1111_EXTENSION_INDEX_URLS[1]!r}
        """,
    )
    sys.path.insert(0, str(tmp_path))
    calls = []
    monkeypatch.setattr(extension_index_module, "_github_direct_accessible", lambda: False)
    monkeypatch.setattr(
        extension_index_module,
        "_apply_github_raw_file_mirror",
        lambda raw_file_path: calls.append(raw_file_path) or "https://mirror.example/auto-index.json",
    )

    apply_from_config({"webui": {"enabled": True, "url": "auto"}})
    module = importlib.import_module("modules.ui_extensions")

    assert calls == [A1111_EXTENSION_INDEX_RAW_FILE_PATH]
    assert module.URL == "https://mirror.example/auto-index.json"


def test_apply_from_config_auto_a1111_keeps_original_without_available_mirror(monkeypatch, tmp_path):
    write_file(tmp_path / "modules" / "__init__.py", "")
    write_file(
        tmp_path / "modules" / "ui_extensions.py",
        f"""
        URL = {A1111_EXTENSION_INDEX_URLS[1]!r}
        """,
    )
    sys.path.insert(0, str(tmp_path))
    monkeypatch.setattr(extension_index_module, "_github_direct_accessible", lambda: False)
    monkeypatch.setattr(extension_index_module, "_apply_github_raw_file_mirror", lambda raw_file_path: None)

    apply_from_config({"webui": {"enabled": True, "url": "auto"}})
    module = importlib.import_module("modules.ui_extensions")

    assert module.URL == A1111_EXTENSION_INDEX_URLS[1]


def test_patch_extension_index_comfyui_manager_rewrites_manager_core_channel_urls(monkeypatch, tmp_path):
    source_prefix = COMFYUI_MANAGER_RAW_PREFIX
    destination_prefix = "https://mirror.example/comfyui-manager/main"
    write_manager_core_module(tmp_path / "manager_core.py", source_prefix)
    sys.path.insert(0, str(tmp_path))
    calls = []
    monkeypatch.setattr(extension_index_module, "_github_direct_accessible", lambda: False)
    monkeypatch.setattr(
        extension_index_module,
        "_apply_github_raw_file_mirror",
        lambda raw_file_path: calls.append(raw_file_path) or destination_prefix,
    )

    patch_extension_index_comfyui_manager()
    module = importlib.import_module("manager_core")
    channels = module.get_channel_dict()

    assert calls == [COMFYUI_MANAGER_RAW_FILE_PATH]
    assert module.DEFAULT_CHANNEL == destination_prefix
    assert channels["default"] == destination_prefix
    assert channels["recent"] == destination_prefix + "/node_db/new"
    assert channels["other"] == "https://raw.githubusercontent.com/another/project/main"
    assert channels["similar"] == source_prefix + "-fork"
    assert destination_prefix in module.valid_channels
    assert destination_prefix + "/node_db/new" in module.valid_channels


def test_patch_extension_index_comfyui_manager_rewrites_manager_server_risky_level_url(
    monkeypatch,
    tmp_path,
):
    source_prefix = COMFYUI_MANAGER_RAW_PREFIX
    destination_prefix = "https://mirror.example/comfyui-manager/main"
    write_manager_core_module(tmp_path / "manager_core.py", source_prefix)
    write_manager_server_module(tmp_path / "manager_server.py", source_prefix)
    sys.path.insert(0, str(tmp_path))
    calls = []
    monkeypatch.setattr(extension_index_module, "_github_direct_accessible", lambda: False)
    monkeypatch.setattr(
        extension_index_module,
        "_apply_github_raw_file_mirror",
        lambda raw_file_path: calls.append(raw_file_path) or destination_prefix,
    )

    patch_extension_index_comfyui_manager()
    manager_server = importlib.import_module("manager_server")
    result = asyncio.run(manager_server.get_risky_level([], []))

    assert calls == [COMFYUI_MANAGER_RAW_FILE_PATH]
    assert result["channel_url"] == destination_prefix


def test_patch_extension_index_comfyui_manager_rewrites_manager_util_get_data_github_urls(
    monkeypatch,
    tmp_path,
):
    source_prefix = COMFYUI_MANAGER_RAW_PREFIX
    destination_prefix = "https://mirror.example/raw/ltdrdata/ComfyUI-Manager/main"
    write_manager_core_module(tmp_path / "manager_core.py", source_prefix)
    write_manager_util_module(tmp_path / "manager_util.py")
    sys.path.insert(0, str(tmp_path))
    calls = []
    monkeypatch.setattr(extension_index_module, "_github_direct_accessible", lambda: False)
    monkeypatch.setattr(
        extension_index_module,
        "_apply_github_raw_file_mirror",
        lambda raw_file_path: calls.append(raw_file_path) or destination_prefix,
    )

    patch_extension_index_comfyui_manager()
    manager_util = importlib.import_module("manager_util")

    raw_result = asyncio.run(
        manager_util.get_data(
            "https://raw.githubusercontent.com/example/repo/main/data.json?download=1#section",
            silent=True,
        )
    )
    github_raw_result = asyncio.run(manager_util.get_data("https://github.com/example/repo/raw/refs/heads/main/node.py"))
    github_blob_result = asyncio.run(manager_util.get_data("https://github.com/example/repo/blob/main/readme.json"))
    other_result = asyncio.run(manager_util.get_data("https://example.com/data.json"))

    assert calls == [COMFYUI_MANAGER_RAW_FILE_PATH]
    assert raw_result == {
        "uri": "https://mirror.example/raw/example/repo/main/data.json?download=1#section",
        "silent": True,
    }
    assert github_raw_result["uri"] == "https://mirror.example/raw/example/repo/refs/heads/main/node.py"
    assert github_blob_result["uri"] == "https://mirror.example/raw/example/repo/main/readme.json"
    assert other_result["uri"] == "https://example.com/data.json"


def test_patch_extension_index_comfyui_manager_supports_custom_prefixes(tmp_path):
    source_prefix = "https://source.example/main"
    destination_prefix = "https://mirror.example/main"
    write_manager_core_module(tmp_path / "manager_core.py", source_prefix)
    write_manager_server_module(tmp_path / "manager_server.py", source_prefix)
    write_manager_util_module(tmp_path / "manager_util.py")
    sys.path.insert(0, str(tmp_path))

    patch_extension_index_comfyui_manager(
        destination_prefix + "/",
        source_prefix=source_prefix + "/",
    )
    module = importlib.import_module("manager_core")
    manager_server = importlib.import_module("manager_server")
    manager_util = importlib.import_module("manager_util")
    channels = module.get_channel_dict()
    risky_level_data = asyncio.run(manager_server.get_risky_level([], []))
    get_data_result = asyncio.run(manager_util.get_data(source_prefix + "/custom-node-list.json"))

    assert module.DEFAULT_CHANNEL == destination_prefix
    assert channels["default"] == destination_prefix
    assert channels["recent"] == destination_prefix + "/node_db/new"
    assert channels["similar"] == source_prefix + "-fork"
    assert destination_prefix in module.valid_channels
    assert risky_level_data["channel_url"] == destination_prefix
    assert get_data_result["uri"] == destination_prefix + "/custom-node-list.json"


def test_apply_from_config_enables_selected_extension_index_patches(monkeypatch, tmp_path):
    write_file(tmp_path / "modules" / "__init__.py", "")
    write_file(
        tmp_path / "modules" / "ui_extensions.py",
        f"""
        URL = {A1111_EXTENSION_INDEX_URLS[0]!r}
        """,
    )
    write_manager_core_module(tmp_path / "manager_core.py")
    write_manager_server_module(tmp_path / "manager_server.py")
    sys.path.insert(0, str(tmp_path))
    calls = []
    mirrors = {
        A1111_EXTENSION_INDEX_RAW_FILE_PATH: "https://mirror.example/a1111-auto.json",
        COMFYUI_MANAGER_RAW_FILE_PATH: "https://mirror.example/comfyui-manager/main",
    }
    monkeypatch.setattr(extension_index_module, "_github_direct_accessible", lambda: False)
    monkeypatch.setattr(
        extension_index_module,
        "_apply_github_raw_file_mirror",
        lambda raw_file_path: calls.append(raw_file_path) or mirrors[raw_file_path],
    )

    apply_from_config(
        {
            "webui": {"enabled": True, "url": "auto"},
            "comfyui_manager": {"enabled": True, "url": "auto"},
        }
    )

    ui_extensions = importlib.import_module("modules.ui_extensions")
    manager_core = importlib.import_module("manager_core")
    manager_server = importlib.import_module("manager_server")
    channels = manager_core.get_channel_dict()
    risky_level_data = asyncio.run(manager_server.get_risky_level([], []))

    assert calls == [A1111_EXTENSION_INDEX_RAW_FILE_PATH, COMFYUI_MANAGER_RAW_FILE_PATH]
    assert ui_extensions.URL == "https://mirror.example/a1111-auto.json"
    assert manager_core.DEFAULT_CHANNEL == "https://mirror.example/comfyui-manager/main"
    assert channels["default"] == "https://mirror.example/comfyui-manager/main"
    assert risky_level_data["channel_url"] == "https://mirror.example/comfyui-manager/main"


def test_apply_from_config_can_enable_webui_without_comfyui_manager(monkeypatch, tmp_path):
    write_file(tmp_path / "modules" / "__init__.py", "")
    write_file(
        tmp_path / "modules" / "ui_extensions.py",
        f"""
        URL = {A1111_EXTENSION_INDEX_URLS[0]!r}
        """,
    )
    write_manager_core_module(tmp_path / "manager_core.py")
    sys.path.insert(0, str(tmp_path))
    monkeypatch.setattr(extension_index_module, "_github_direct_accessible", lambda: False)
    monkeypatch.setattr(
        extension_index_module,
        "_apply_github_raw_file_mirror",
        lambda raw_file_path: "https://mirror.example/a1111-auto.json",
    )

    apply_from_config(
        {
            "webui": {"enabled": True, "url": "auto"},
            "comfyui_manager": {"enabled": False, "url": "auto"},
        }
    )

    ui_extensions = importlib.import_module("modules.ui_extensions")
    manager_core = importlib.import_module("manager_core")

    assert ui_extensions.URL == "https://mirror.example/a1111-auto.json"
    assert manager_core.DEFAULT_CHANNEL == COMFYUI_MANAGER_RAW_PREFIX


def test_apply_from_config_can_enable_comfyui_manager_without_webui(monkeypatch, tmp_path):
    write_file(tmp_path / "modules" / "__init__.py", "")
    write_file(
        tmp_path / "modules" / "ui_extensions.py",
        f"""
        URL = {A1111_EXTENSION_INDEX_URLS[0]!r}
        """,
    )
    write_manager_core_module(tmp_path / "manager_core.py")
    sys.path.insert(0, str(tmp_path))
    monkeypatch.setattr(extension_index_module, "_github_direct_accessible", lambda: False)
    monkeypatch.setattr(
        extension_index_module,
        "_apply_github_raw_file_mirror",
        lambda raw_file_path: "https://mirror.example/comfyui-manager/main",
    )

    apply_from_config(
        {
            "webui": {"enabled": False, "url": "auto"},
            "comfyui_manager": {"enabled": True, "url": "auto"},
        }
    )

    ui_extensions = importlib.import_module("modules.ui_extensions")
    manager_core = importlib.import_module("manager_core")
    channels = manager_core.get_channel_dict()

    assert ui_extensions.URL == A1111_EXTENSION_INDEX_URLS[0]
    assert manager_core.DEFAULT_CHANNEL == "https://mirror.example/comfyui-manager/main"
    assert channels["default"] == "https://mirror.example/comfyui-manager/main"
