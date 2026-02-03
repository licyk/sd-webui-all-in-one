import argparse
from typing import Optional, Callable
from sd_webui_all_in_one.cli_manager.sd_webui_cli import register_sd_webui
from sd_webui_all_in_one.cli_manager.sd_trainer_cli import register_sd_trainer
from sd_webui_all_in_one.cli_manager.sd_scripts_cli import register_sd_scripts
from sd_webui_all_in_one.cli_manager.invokeai_cli import register_invokeai


class ParsedArgs(argparse.Namespace):
    func: Optional[Callable[[argparse.Namespace], None]]
    main_command: str


def main() -> None:
    # 根解析器
    parser = argparse.ArgumentParser(prog="sd-webui-all-in-one", description="SD WebUI All in One CLI 管理器")

    # 根层级的子命令容器
    subparsers = parser.add_subparsers(dest="main_command", help="选择要操作的模块", required=True)

    # 注册各模块的子命令
    register_sd_webui(subparsers)
    register_sd_trainer(subparsers)
    register_sd_scripts(subparsers)
    register_invokeai(subparsers)

    # 执行解析
    args: ParsedArgs = parser.parse_args()  # type: ignore

    # 执行绑定的函数
    if hasattr(args, "func") and args.func:
        args.func(args)
    else:
        parser.print_help()
