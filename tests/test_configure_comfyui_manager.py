import configparser
import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / ".github" / "configure_comfyui_manager.py"


def load_module():
    spec = importlib.util.spec_from_file_location("configure_comfyui_manager", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_config(path: Path) -> configparser.ConfigParser:
    config = configparser.ConfigParser(allow_no_value=True, interpolation=None)
    config.read(path, encoding="utf-8")
    return config


def test_configure_comfyui_manager_overwrites_target_values(tmp_path):
    module = load_module()
    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "\n".join(
            [
                "[default]",
                "channel_url = https://example.com/channel",
                "share_option = all",
                "security_level = normal",
                "network_mode = public",
                "db_mode = cache",
                "",
            ]
        ),
        encoding="utf-8",
    )

    module.configure_comfyui_manager(config_path)

    config = read_config(config_path)
    assert config["default"]["network_mode"] == "personal_cloud"
    assert config["default"]["security_level"] == "weak"
    assert config["default"]["channel_url"] == "https://example.com/channel"
    assert config["default"]["share_option"] == "all"
    assert config["default"]["db_mode"] == "cache"


def test_configure_comfyui_manager_adds_missing_target_values(tmp_path):
    module = load_module()
    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "\n".join(
            [
                "[default]",
                "channel_url = https://example.com/channel",
                "db_mode = cache",
                "",
            ]
        ),
        encoding="utf-8",
    )

    module.configure_comfyui_manager(config_path)

    config = read_config(config_path)
    assert config["default"]["network_mode"] == "personal_cloud"
    assert config["default"]["security_level"] == "weak"
    assert config["default"]["channel_url"] == "https://example.com/channel"
    assert config["default"]["db_mode"] == "cache"


def test_configure_comfyui_manager_creates_default_section(tmp_path):
    module = load_module()
    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "\n".join(
            [
                "[other]",
                "value = keep",
                "",
            ]
        ),
        encoding="utf-8",
    )

    module.configure_comfyui_manager(config_path)

    config = read_config(config_path)
    assert config["default"]["network_mode"] == "personal_cloud"
    assert config["default"]["security_level"] == "weak"
    assert config["other"]["value"] == "keep"


def test_configure_comfyui_manager_requires_existing_config(tmp_path):
    module = load_module()

    with pytest.raises(FileNotFoundError, match="ComfyUI Manager config not found"):
        module.configure_comfyui_manager(tmp_path / "missing.ini")
