"""SD WebUI 版本管理界面辅助函数测试"""

import pytest


def test_sd_webui_version_gui_does_not_overwrite_corrupted_config(tmp_path):
    from sd_webui_all_in_one.base_manager.gui.sd_webui_version_gui import helpers as sd_webui_gui_helpers

    config_path = tmp_path / "config.json"
    config_path.write_text("{broken", encoding="utf-8")

    assert sd_webui_gui_helpers._sd_webui_extension_enabled(tmp_path, "ext", tmp_path / "extensions" / "ext") is True
    with pytest.raises(ValueError):
        sd_webui_gui_helpers._set_sd_webui_extension_enabled(tmp_path, "ext", False)
    assert config_path.read_text(encoding="utf-8") == "{broken"
