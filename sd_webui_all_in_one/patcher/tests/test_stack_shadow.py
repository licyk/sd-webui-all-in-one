import importlib
import sys
import textwrap
import traceback
import zipfile

import pytest

from sd_webui_all_in_one_hotpatcher.bootstrap import configure_from_env
from sd_webui_all_in_one_hotpatcher.stack_shadow import (
    install_stack_shadower,
    is_stack_shadower_installed,
    uninstall_stack_shadower,
)


@pytest.fixture(autouse=True)
def clean_stack_shadow_state():
    uninstall_stack_shadower()
    before_path = list(sys.path)
    yield
    uninstall_stack_shadower()
    sys.path[:] = before_path
    for name in list(sys.modules):
        if name.startswith("shadow_"):
            sys.modules.pop(name, None)


def test_source_module_traceback_uses_hidden_filename(tmp_path):
    module_path = tmp_path / "shadow_source_target.py"
    module_path.write_text(
        textwrap.dedent(
            """
            def boom():
                raise RuntimeError("shadow source")
            """
        ),
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))

    install_stack_shadower("shadow_source_target", "<hidden {name}>")
    module = importlib.import_module("shadow_source_target")

    with pytest.raises(RuntimeError) as exc_info:
        module.boom()

    formatted = "".join(traceback.format_exception(exc_info.type, exc_info.value, exc_info.tb))
    assert "<hidden shadow_source_target>" in formatted
    assert str(module_path) not in formatted


def test_zip_module_traceback_uses_hidden_filename(tmp_path):
    zip_path = tmp_path / "shadow_package.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(
            "shadow_zip_target.py",
            "def boom():\n    raise RuntimeError('shadow zip')\n",
        )
    sys.path.insert(0, str(zip_path))

    install_stack_shadower("shadow_zip_target", "<hidden {name}>")
    module = importlib.import_module("shadow_zip_target")

    with pytest.raises(RuntimeError) as exc_info:
        module.boom()

    formatted = "".join(traceback.format_exception(exc_info.type, exc_info.value, exc_info.tb))
    assert "<hidden shadow_zip_target>" in formatted
    assert str(zip_path) not in formatted


def test_bootstrap_installs_stack_shadower_from_env(monkeypatch):
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW", "1")
    monkeypatch.setenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW_PREFIXES", "shadow_env_target")

    state = configure_from_env()

    assert state.stack_shadower_installed is True
    assert is_stack_shadower_installed() is True
