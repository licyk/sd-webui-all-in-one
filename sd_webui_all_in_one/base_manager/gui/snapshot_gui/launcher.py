"""Implementation grouped from the former ``snapshot_gui.py`` module."""

from __future__ import annotations

from pathlib import Path

from .app import SnapshotManagerApp
from .formatters import SnapshotFactory


def launch_snapshot_manager_gui(
    title: str,
    webui_type: str,
    webui_path: Path,
    snapshot_factory: SnapshotFactory,
    use_uv: bool = True,
    use_pypi_mirror: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    snapshot_dir: Path | None = None,
) -> None:
    """启动 WebUI 快照管理 GUI

    Args:
        title (str):
            GUI 窗口标题。
        webui_type (str):
            WebUI 类型标识。
        webui_path (Path):
            WebUI 根目录。
        snapshot_factory (SnapshotFactory):
            创建快照对象的回调。
        use_uv (bool):
            是否使用 uv 执行 Python 包安装。
        use_pypi_mirror (bool):
            是否使用 PyPI 镜像源。
        use_github_mirror (bool):
            是否使用 GitHub 镜像源。
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源。
        snapshot_dir (Path | None):
            快照文件目录。
    """
    app = SnapshotManagerApp(
        title=title,
        webui_type=webui_type,
        webui_path=webui_path,
        snapshot_factory=snapshot_factory,
        use_uv=use_uv,
        use_pypi_mirror=use_pypi_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
        snapshot_dir=snapshot_dir,
    )
    app.mainloop()
