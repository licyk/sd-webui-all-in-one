"""argparse 解析器辅助函数。"""

import argparse


def add_subparsers_with_help(
    parser: argparse.ArgumentParser,
    *,
    dest: str,
) -> "argparse._SubParsersAction":
    """添加在未选择子命令时打印当前层帮助的子解析器。

    Args:
        parser (argparse.ArgumentParser): 当前层级的参数解析器。
        dest (str): 用于存储所选子命令名称的属性名。

    Returns:
        argparse._SubParsersAction: 新创建的子解析器操作。
    """
    parser.set_defaults(func=lambda _args: parser.print_help())
    return parser.add_subparsers(dest=dest, required=False)
