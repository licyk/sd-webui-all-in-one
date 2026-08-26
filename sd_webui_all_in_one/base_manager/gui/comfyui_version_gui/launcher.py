"""Product version-manager GUI launcher."""

from __future__ import annotations

from pathlib import Path

from .app import ComfyUiVersionManagerApp


def launch_comfyui_version_gui(
    comfyui_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """
    启动 ComfyUI 版本管理 GUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        use_github_mirror (bool):
            是否启用 GitHub 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源
    """
    app = ComfyUiVersionManagerApp(
        comfyui_path=comfyui_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )
    app.mainloop()
