"""Hotpatcher 管理界面测试"""

import types


def test_hotpatcher_gui_module_importable():
    from sd_webui_all_in_one.base_manager.gui import hotpatcher_manager_gui

    assert hotpatcher_manager_gui.HotpatcherManagerApp is not None


def test_hotpatcher_gui_schema_helpers():
    from sd_webui_all_in_one.base_manager.gui.hotpatcher_manager_gui.config_values import (
        _metadata_field_kind,
        _value_to_text,
    )

    assert _metadata_field_kind({"type": "choice"}, "safe") == "choice"
    assert _metadata_field_kind({"type": "list[str]"}, []) == "list"
    assert _metadata_field_kind({"type": "object"}, False) == "object"
    assert _value_to_text({"enabled": True}, "object") == '{"enabled":true}'


def test_hotpatcher_gui_apply_form_does_not_mutate_input_config():
    from sd_webui_all_in_one.base_manager.gui import hotpatcher_manager_gui

    class Variable:
        def __init__(self, value):
            self.value = value

        def get(self):
            return self.value

    original = {
        "core": {
            "import_hook": {
                "enabled": False,
                "metadata": {"tags": ["existing"]},
            }
        }
    }
    app = types.SimpleNamespace(
        _schema_field_vars={
            ("core.import_hook", "enabled"): (Variable(True), "bool", False, {}),
        }
    )

    result = hotpatcher_manager_gui.HotpatcherManagerApp._apply_form_to_config(app, original)

    assert result["core"]["import_hook"]["enabled"] is True
    assert original["core"]["import_hook"]["enabled"] is False
    result["core"]["import_hook"]["metadata"]["tags"].append("changed")
    assert original["core"]["import_hook"]["metadata"]["tags"] == ["existing"]
