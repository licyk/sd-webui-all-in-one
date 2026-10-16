import logging

from sd_webui_all_in_one import config
from sd_webui_all_in_one.logger import silence_logger_output


def test_silence_logger_output_uses_lazy_config(monkeypatch):
    monkeypatch.setattr(config, "LOGGER_NAME", "unit.silent")
    monkeypatch.setattr(config, "LOGGER_LEVEL", logging.INFO)

    root_logger = logging.getLogger()
    root_level = root_logger.level
    target_logger = logging.getLogger("unit.silent.child")
    target_logger.setLevel(logging.INFO)

    try:
        silence_logger_output()

        assert config.LOGGER_LEVEL == logging.CRITICAL
        assert target_logger.level == logging.CRITICAL
        assert root_logger.level == logging.CRITICAL
    finally:
        root_logger.setLevel(root_level)
        target_logger.setLevel(logging.NOTSET)
