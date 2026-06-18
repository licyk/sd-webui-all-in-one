"""CLI 快照恢复工具"""

import argparse
from pathlib import Path

from sd_webui_all_in_one.base_manager import SnapshotRestoreOptions, restore_webui_snapshot
from sd_webui_all_in_one.cli_manager.auto_mirror import add_auto_mirror_argument
from sd_webui_all_in_one.utils import normalized_filepath


def restore_snapshot(
    snapshot_path: Path,
    webui_path: Path,
    expected_webui_type: str,
    prune_packages: bool = False,
    prune_extensions: bool = False,
    force_git_reset: bool = False,
    use_uv: bool = True,
    use_pypi_mirror: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """恢复 WebUI 环境快照"""
    restore_webui_snapshot(
        snapshot_path=snapshot_path,
        webui_path=webui_path,
        expected_webui_type=expected_webui_type,
        options=SnapshotRestoreOptions(
            prune_packages=prune_packages,
            prune_extensions=prune_extensions,
            force_git_reset=force_git_reset,
            use_uv=use_uv,
            use_pypi_mirror=use_pypi_mirror,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
        ),
    )


def add_restore_arguments(
    parser: argparse.ArgumentParser,
    path_argument: str,
    path_dest: str,
    default_path: Path,
) -> None:
    """为 WebUI restore 子命令添加通用参数"""
    parser.add_argument("snapshot_path", type=normalized_filepath, help="环境快照 JSON 文件路径")
    parser.add_argument(path_argument, type=normalized_filepath, required=False, default=default_path, dest=path_dest, help="WebUI 根目录")
    parser.add_argument("--prune-packages", action="store_true", dest="prune_packages", help="卸载快照外 Python 软件包")
    parser.add_argument("--prune-extensions", action="store_true", dest="prune_extensions", help="删除快照外扩展")
    parser.add_argument("--force-git-reset", action="store_true", dest="force_git_reset", help="允许覆盖 Git 仓库未提交变更")
    parser.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv 安装 Python 软件包")
    parser.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    parser.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    parser.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    add_auto_mirror_argument(parser)
