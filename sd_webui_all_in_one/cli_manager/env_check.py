"""环境检查 CLI 参数工具。"""

import argparse


def add_env_check_selection_arguments(parser: argparse.ArgumentParser) -> None:
    """添加环境检查任务选择参数。

    Args:
        parser (argparse.ArgumentParser): 要添加参数的解析器。
    """
    parser.add_argument("--include-check", action="append", default=None, dest="include_checks", help="仅执行指定环境检查任务, 可重复传入")
    parser.add_argument("--exclude-check", action="append", default=None, dest="exclude_checks", help="跳过指定环境检查任务, 可重复传入")
