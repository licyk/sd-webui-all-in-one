"""基于 PYTHONPATH=src 的可选自动启动入口"""

from __future__ import annotations

import os


def _should_bootstrap() -> bool:
    return any(key.startswith("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_") for key in os.environ)


if _should_bootstrap():
    try:
        from sd_webui_all_in_one_hotpatcher.bootstrap import configure_from_env

        configure_from_env()
    except Exception:
        if os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_DEBUG") == "1":
            import traceback

            traceback.print_exc()
