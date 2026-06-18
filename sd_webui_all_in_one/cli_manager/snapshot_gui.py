"""CLI 快照管理 GUI 工具"""

import argparse
from pathlib import Path

from sd_webui_all_in_one.cli_manager.auto_mirror import add_auto_mirror_argument
from sd_webui_all_in_one.config import SD_WEBUI_ALL_IN_ONE_SNAPSHOT_DIR
from sd_webui_all_in_one.utils import normalized_filepath


def add_snapshot_gui_arguments(
    parser: argparse.ArgumentParser,
    path_argument: str,
    path_dest: str,
    default_path: Path,
) -> None:
    """为 WebUI snapshot-manager GUI 子命令添加通用参数"""
    parser.add_argument(path_argument, type=normalized_filepath, required=False, default=default_path, dest=path_dest, help="WebUI 根目录")
    parser.add_argument("--snapshot-dir", type=normalized_filepath, default=SD_WEBUI_ALL_IN_ONE_SNAPSHOT_DIR, dest="snapshot_dir", help="快照目录")
    parser.add_argument("--no-uv", action="store_false", dest="use_uv", help="不使用 uv 安装 Python 软件包")
    parser.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    parser.add_argument("--no-github-mirror", action="store_false", dest="use_github_mirror", help="不使用 Github 镜像源")
    parser.add_argument("--custom-github-mirror", type=str, dest="custom_github_mirror", help="自定义 Github 镜像源")
    add_auto_mirror_argument(parser)
