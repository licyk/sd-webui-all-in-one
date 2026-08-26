"""Product version-manager GUI launcher."""

from __future__ import annotations

from pathlib import Path

from sd_webui_all_in_one.base_manager.gui.invokeai_version_gui.app import InvokeAiVersionManagerApp


def launch_invokeai_version_gui(
    invokeai_path: Path,
    use_pypi_mirror: bool = False,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """
    启动 InvokeAI 版本管理 GUI

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        use_pypi_mirror (bool):
            是否启用 PyPI 镜像源
        use_uv (bool):
            是否使用 uv 安装软件包
        use_github_mirror (bool):
            是否启用 GitHub 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源
    """
    app = InvokeAiVersionManagerApp(
        invokeai_path=invokeai_path,
        use_pypi_mirror=use_pypi_mirror,
        use_uv=use_uv,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )
    app.mainloop()
