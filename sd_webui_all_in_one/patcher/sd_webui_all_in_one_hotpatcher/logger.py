"""Hotpatcher 日志工具。"""

from __future__ import annotations

import logging

_FALLBACK_LOGGER_NAME = "sd_webui_all_in_one_hotpatcher"


def get_hotpatcher_logger(name: str | None = None) -> logging.Logger:
    """
    获取接入主包配置的 Hotpatcher 日志器。

    优先复用 ``sd_webui_all_in_one.logger.get_logger`` 和主包 ``LOGGER_*`` 配置。
    如果主包在当前启动阶段不可用，则回退到标准库日志器，避免日志接入影响
    hotpatcher bootstrap。

    参数:
        name (str | None):
            回退到标准库日志器时使用的日志器名称。

    返回:
        logging.Logger:
            日志器对象。
    """

    try:
        from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
        from sd_webui_all_in_one.logger import get_logger

        return get_logger(
            name=LOGGER_NAME,
            level=LOGGER_LEVEL,
            color=LOGGER_COLOR,
        )
    except Exception:
        return logging.getLogger(name or _FALLBACK_LOGGER_NAME)
