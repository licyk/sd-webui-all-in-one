"""Product version-manager GUI launcher."""

from __future__ import annotations

from pathlib import Path

from .app import SDWebUiVersionManagerApp


def launch_sd_webui_version_gui(
    sd_webui_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """
    启动 Stable Diffusion WebUI 版本管理 GUI

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        use_github_mirror (bool):
            是否启用 GitHub 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源
    """
    app = SDWebUiVersionManagerApp(
        sd_webui_path=sd_webui_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )
    app.mainloop()
