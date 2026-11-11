"""Hotpatcher 管理界面 json / float 设置类型测试"""

import json

import pytest


class Variable:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def test_json_kind_round_trips_list_of_objects():
    from sd_webui_all_in_one.base_manager.gui.hotpatcher_manager_gui.config_values import (
        _metadata_field_kind,
        _value_to_text,
        _variable_to_value,
    )

    patch_sets = [{"source": "pkg.patch", "name": "fix, with comma", "config": {"level": 2}, "enabled": True}]

    assert _metadata_field_kind({"type": "json"}, []) == "json"
    text = _value_to_text(patch_sets, "json")
    assert json.loads(text) == patch_sets
    assert _variable_to_value(Variable(text), "json", []) == patch_sets
    assert _variable_to_value(Variable("  "), "json", []) == []
    assert _value_to_text([], "json") == "[]"
    with pytest.raises(ValueError):
        _variable_to_value(Variable("[{"), "json", [])


def test_float_kind_round_trips_and_falls_back_to_default():
    from sd_webui_all_in_one.base_manager.gui.hotpatcher_manager_gui.config_values import (
        _metadata_field_kind,
        _value_to_text,
        _variable_to_value,
    )

    assert _metadata_field_kind({"type": "float"}, 1.0) == "float"
    assert _metadata_field_kind({"type": "unknown"}, 1.5) == "float"
    assert _value_to_text(1.0, "float") == "1.0"
    assert _variable_to_value(Variable("0.25"), "float", 1.0) == 0.25
    assert _variable_to_value(Variable("abc"), "float", 1.0) == 1.0


def test_control_catalog_settings_round_trip_through_form():
    from sd_webui_all_in_one.base_manager.gui import hotpatcher_manager_gui
    from sd_webui_all_in_one.base_manager.gui.hotpatcher_manager_gui.config_values import (
        _metadata_field_kind,
        _value_by_path,
        _value_to_text,
    )
    from sd_webui_all_in_one.base_manager.hotpatcher_manager import get_hotpatcher_catalog

    settings = get_hotpatcher_catalog()["features"]["control"]["settings"]
    configured = {
        "control": {
            "allow_remote_load": False,
            "patch_sets": [{"source": "/tmp/fix.py", "config": {"a": [1, 2]}, "enabled": False}],
            "watch": {"enabled": True, "interval": 0.5},
            "forward_events": False,
        }
    }
    field_vars = {}
    for setting_name, metadata in settings.items():
        default_value = metadata.get("default")
        kind = _metadata_field_kind(metadata, default_value)
        value = _value_by_path(configured["control"], setting_name, default_value)
        text = value if kind == "bool" else _value_to_text(value, kind)
        field_vars[("control", setting_name)] = (Variable(text), kind, default_value, metadata)
    app = type("App", (), {"_schema_field_vars": field_vars})()

    result = hotpatcher_manager_gui.HotpatcherManagerApp._apply_form_to_config(app, {})

    assert field_vars[("control", "patch_sets")][1] == "json"
    assert field_vars[("control", "watch.interval")][1] == "float"
    assert result == configured
