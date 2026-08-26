"""Implementation grouped from the former ``qwen_tts_webui_base.py`` module."""

from __future__ import annotations

from pathlib import Path

from .catalog import QWEN_TTS_WEBUI_REPO
from .reporting import get_qwen_tts_webui_snapshot


def launch_qwen_tts_webui_version_gui(
    qwen_tts_webui_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """启动 Qwen TTS WebUI 版本管理 GUI

    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源

    Raises:
        RuntimeError:
            环境未安装 tkinter 或者导入 GUI 模块失败时
    """
    try:
        from sd_webui_all_in_one.base_manager.gui.git_kernel_version_gui import launch_git_kernel_version_gui
    except ModuleNotFoundError as e:
        if e.name == "tkinter":
            raise RuntimeError("当前 Python 环境未安装 tkinter, 无法启动版本管理 GUI") from e
        raise RuntimeError(f"导入 GUI 管理模块发生错误: {e}") from e

    launch_git_kernel_version_gui(
        title="Qwen TTS WebUI",
        root_path=qwen_tts_webui_path,
        branch_presets=[{"name": "licyk - Qwen TTS WebUI", "url": QWEN_TTS_WEBUI_REPO, "branch": "main", "use_submodule": False}],
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def launch_qwen_tts_webui_snapshot_gui(
    qwen_tts_webui_path: Path,
    snapshot_dir: Path | None = None,
    use_uv: bool = True,
    use_pypi_mirror: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """启动 Qwen TTS WebUI 快照管理 GUI

    Args:
        qwen_tts_webui_path (Path):
            Qwen TTS WebUI 根目录。
        snapshot_dir (Path | None):
            快照文件目录。
        use_uv (bool):
            是否使用 uv 执行 Python 包安装。
        use_pypi_mirror (bool):
            是否使用 PyPI 镜像源。
        use_github_mirror (bool):
            是否使用 GitHub 镜像源。
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源。

    Raises:
        RuntimeError:
            当恢复或 GUI 启动无法安全继续时抛出。
    """
    try:
        from sd_webui_all_in_one.base_manager.gui.snapshot_gui import launch_snapshot_manager_gui
    except ModuleNotFoundError as e:
        if e.name == "tkinter":
            raise RuntimeError("当前 Python 环境未安装 tkinter, 无法启动快照管理 GUI") from e
        raise RuntimeError(f"导入 GUI 管理模块发生错误: {e}") from e

    launch_snapshot_manager_gui(
        title="Qwen TTS WebUI",
        webui_type="qwen_tts_webui",
        webui_path=qwen_tts_webui_path,
        snapshot_factory=lambda include_packages: get_qwen_tts_webui_snapshot(qwen_tts_webui_path, include_packages=include_packages),
        snapshot_dir=snapshot_dir,
        use_uv=use_uv,
        use_pypi_mirror=use_pypi_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )
