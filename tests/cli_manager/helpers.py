"""命令行测试辅助工具"""

import argparse


def single_command_parser(register_func):
    parser = argparse.ArgumentParser(prog="test")
    subparsers = parser.add_subparsers(dest="main_command", required=True)
    register_func(subparsers)
    return parser


def build_parser(*register_funcs):
    parser = argparse.ArgumentParser(prog="sd-webui-all-in-one")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for register in register_funcs:
        register(subparsers)
    return parser
