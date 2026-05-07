"""基于 PYTHONPATH=src 的可选自动启动入口"""

from __future__ import annotations

import os

_BOOTSTRAPPED_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_BOOTSTRAPPED"
_HOTPATCHER_ENV_PREFIX = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_"


def _should_bootstrap() -> bool:
    if os.getenv(_BOOTSTRAPPED_ENV) == "1":
        return False
    return any(key.startswith(_HOTPATCHER_ENV_PREFIX) for key in os.environ)


if _should_bootstrap():
    os.environ[_BOOTSTRAPPED_ENV] = "1"
    try:
        from sd_webui_all_in_one_hotpatcher.bootstrap import configure_from_env

        configure_from_env()
    except Exception:
        if os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_DEBUG") == "1":
            import traceback

            traceback.print_exc()
