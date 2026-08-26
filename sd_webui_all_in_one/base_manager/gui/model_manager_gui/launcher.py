"""Implementation grouped from the former ``model_manager_gui.py`` module."""

from __future__ import annotations

from pathlib import Path
from sd_webui_all_in_one.base_manager.model_manager import (
    FILE_MODEL_ROOT_DIRS,
    WebUiModelType,
)

from .file_app import FileModelManagerApp
from .invokeai_app import InvokeAIModelManagerApp


def launch_model_manager_gui(
    webui_type: WebUiModelType,
    webui_path: Path,
    title: str,
) -> None:
    """启动模型管理 GUI

    Args:
        webui_type (WebUiModelType):
            要管理模型的 WebUI 类型。
        webui_path (Path):
            WebUI 根目录路径。
        title (str):
            窗口标题。

    Raises:
        ValueError:
            传入不支持的 WebUI 类型时抛出。
    """
    if webui_type == "invokeai":
        app = InvokeAIModelManagerApp(invokeai_path=webui_path, title=title)
    else:
        if webui_type not in FILE_MODEL_ROOT_DIRS:
            raise ValueError(f"不支持的 WebUI 类型: {webui_type}")
        app = FileModelManagerApp(webui_type=webui_type, webui_path=webui_path, title=title)  # type: ignore[arg-type]
    app.mainloop()
