"""Implementation grouped from the former ``hotpatcher_manager_gui.py`` module."""

from __future__ import annotations

from pathlib import Path
from sd_webui_all_in_one.base_manager.hotpatcher_manager import (
    DEFAULT_HOTPATCHER_CONFIG_PATH,
    DEFAULT_RUNTIME_HOST,
    DEFAULT_RUNTIME_PORT,
)

from sd_webui_all_in_one.base_manager.gui.hotpatcher_manager_gui.app import HotpatcherManagerApp


def launch_hotpatcher_manager_gui(
    config_path: str | Path | None = DEFAULT_HOTPATCHER_CONFIG_PATH,
    host: str = DEFAULT_RUNTIME_HOST,
    port: int = DEFAULT_RUNTIME_PORT,
    token: str = "",
) -> None:
    """启动 Hotpatcher 配置管理 GUI

    Args:
        config_path (str | Path | None):
            配置文件路径
        host (str):
            runtime host 监听地址
        port (int):
            runtime host 监听端口
        token (str):
            runtime host 访问令牌
    """

    app = HotpatcherManagerApp(config_path=config_path, host=host, port=port, token=token)
    app.mainloop()
