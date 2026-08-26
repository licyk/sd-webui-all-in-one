"""Implementation grouped from the former ``sd_trainer_base.py`` module."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import (
    cast,
    TypeAlias,
    Literal,
    TypedDict,
    get_args,
)
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
    print_divider,
)
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
)
from sd_webui_all_in_one.ansi_color import ANSIColor
from sd_webui_all_in_one.launch_arguments import (
    DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    LaunchArgumentCatalog,
    build_script_help_command,
    discover_launch_argument_catalog,
)
from sd_webui_all_in_one.utils import TemporaryModulePath

from .shared import logger

SD_TRAINER_LAUNCH_ARGUMENT_PROVIDER_IDENTITY = "gui:parser"
KOHYA_GUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY = "kohya_gui:initialize_arg_parser"


def get_sd_trainer_launch_argument_catalog(
    sd_trainer_path: str | Path,
    use_parser_object: bool = True,
    *,
    python_executable: str | Path | None = None,
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
) -> LaunchArgumentCatalog:
    """发现 SD Trainer 系列参数，对象解析失败时回退到 ``--help``。

    Args:
        sd_trainer_path (str | Path): SD Trainer 系列 WebUI 根目录。
        use_parser_object (bool): 是否优先解析实际参数对象。
        python_executable (str | Path | None): 执行 ``--help`` 的 Python。
        timeout_seconds (float): ``--help`` 命令超时秒数。

    Returns:
        LaunchArgumentCatalog: 规范化的启动参数目录。
    """
    path = Path(sd_trainer_path)
    gui_source = path / "gui.py"
    if gui_source.is_file():
        module_name = "gui"
        provider_identity = SD_TRAINER_LAUNCH_ARGUMENT_PROVIDER_IDENTITY
    else:
        module_name = "kohya_gui"
        provider_identity = KOHYA_GUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY

    def load_parser():
        with TemporaryModulePath(path):
            module = importlib.import_module(module_name)
            return module.parser if module_name == "gui" else module.initialize_arg_parser()

    return discover_launch_argument_catalog(
        "sd_trainer",
        path,
        provider_identity=provider_identity,
        help_command_factory=lambda context: build_script_help_command(context, ("gui.py", "kohya_gui.py")),
        parser_loader=load_parser,
        parser_source_identity=provider_identity,
        use_parser_object=use_parser_object,
        python_executable=python_executable,
        timeout_seconds=timeout_seconds,
    )


SDTrainerBranchType: TypeAlias = Literal[
    "sd_trainer_main",
    "sd_trainer_next_main",
    "kohya_gui_main",
]

SD_TRAINER_BRANCH_LIST: list[SDTrainerBranchType] = cast(list[SDTrainerBranchType], list(get_args(SDTrainerBranchType)))


class SDTrainerBranchInfo(TypedDict):
    """SD Trainer 分支信息"""

    name: str
    """SD Trainer 分支名称"""

    dtype: SDTrainerBranchType
    """SD Trainer 分支类型"""

    url: str
    """SD Trainer 分支的 Git 仓库地址"""

    branch: str
    """SD Trainer 的 Git 分支名称"""

    use_submodule: bool
    """SD Trainer 分支中是否包含 Git 子模块"""


SD_TRAINER_BRANCH_INFO_DICT: list[SDTrainerBranchInfo] = [
    {
        "name": "Akegarasu - SD-Trainer 分支",
        "dtype": "sd_trainer_main",
        "url": "https://github.com/Akegarasu/lora-scripts",
        "branch": "main",
        "use_submodule": True,
    },
    {
        "name": "wochenlong - SD Trainer Next 分支",
        "dtype": "sd_trainer_next_main",
        "url": "https://github.com/wochenlong/lora-scripts-next",
        "branch": "main",
        "use_submodule": True,
    },
    {
        "name": "bmaltais - Kohya GUI 分支",
        "dtype": "kohya_gui_main",
        "url": "https://github.com/bmaltais/kohya_ss",
        "branch": "master",
        "use_submodule": True,
    },
]


def get_sd_trainer_branch_presets() -> dict[str, object]:
    """返回 SD Trainer 内置分支预设。

    Returns:
        dict[str, object]: 包含可用 SD Trainer 分支列表和类型列表的字典。
    """
    return {"branches": list(SD_TRAINER_BRANCH_INFO_DICT), "types": list(SD_TRAINER_BRANCH_LIST)}


def display_sd_trainer_branch_list(
    branch_list: list[SDTrainerBranchInfo],
) -> None:
    """显示 SD Trainer 分支列表

    Args:
        branch_list (list[SDTrainerBranchInfo]):
            SD Trainer 分支信息列表
    """
    for index, info in enumerate(branch_list, start=1):
        name = info["name"]
        dtype = info["dtype"]
        print(f"- {ANSIColor.GOLD}{index}{ANSIColor.RESET}、{ANSIColor.WHITE}{name}{ANSIColor.RESET} ({ANSIColor.BLUE}{dtype}{ANSIColor.RESET})")


def switch_sd_trainer_branch(
    sd_trainer_path: Path,
    branch: SDTrainerBranchType | None = None,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    interactive_mode: bool = False,
    list_only: bool = False,
) -> None:
    """切换 SD Trainer 分支

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        branch (SDTrainerBranchType | None):
            要切换的 SD Trainer 分支
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        interactive_mode (bool):
            是否启用交互模式
        list_only (bool):
            是否仅列出分支列表并退出

    Raises:
        ValueError:
            传入未知的 SD Trainer 分支时
    """

    def _switch(
        input_branch: SDTrainerBranchType | None = None,
        input_index: int | None = None,
    ) -> None:
        nonlocal branch
        if input_index is not None:
            if not 0 < input_index <= len(SD_TRAINER_BRANCH_INFO_DICT):
                raise ValueError(f"索引值 {input_index} 超出范围, 有效范围为: 1 ~ {len(SD_TRAINER_BRANCH_INFO_DICT)}")
            branch_info = SD_TRAINER_BRANCH_INFO_DICT[input_index - 1]
        elif input_branch is not None:
            if input_branch not in SD_TRAINER_BRANCH_LIST:
                raise ValueError(f"未知的 SD Trainer 分支: '{input_branch}'")
            branch_info = [x for x in SD_TRAINER_BRANCH_INFO_DICT if input_branch == x["dtype"]][0]
        else:
            raise ValueError("需要提供 `branch` 或 `index` 才能进行分支切换")

        # 准备 Git 配置
        custom_env = apply_git_base_config_and_github_mirror(
            use_github_mirror=use_github_mirror,
            custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
            origin_env=os.environ.copy(),
        )
        apply_git_config_global_to_process(custom_env)

        logger.info("切换 SD Trainer 分支到 %s", branch_info["name"])
        git_warpper.switch_branch(
            path=sd_trainer_path,
            branch=branch_info["branch"],
            new_url=branch_info["url"],
            recurse_submodules=branch_info["use_submodule"],
        )
        logger.info("切换 SD Trainer 分支完成")

    if list_only:
        print_divider("=")
        display_sd_trainer_branch_list(SD_TRAINER_BRANCH_INFO_DICT)
        print_divider("=")
        return

    if interactive_mode:
        input_err = (0, None)
        while True:
            print_divider("=")
            display_sd_trainer_branch_list(SD_TRAINER_BRANCH_INFO_DICT)
            print_divider("=")

            i, m = input_err
            if i == 1:
                logger.warning("输入有误, 请重试")
            elif i == 2:
                logger.warning("输入的数字有误, %s, 请重新输入", m)
            input_err = (0, None)

            print(
                "请选择要切换的 SD Trainer 分支\n提示:\n1. 输入数字后回车即可选择切换到指定的分支\n2. 输入 exit 后回车退出分支切换",
            )
            user_input = input("==> ").strip()

            if user_input == "exit":
                return

            try:
                index = int(user_input)
            except Exception:
                input_err = (1, None)
                continue

            try:
                _switch(input_index=index)
                return
            except ValueError as e:
                input_err = (2, str(e))
                continue
    else:
        _switch(input_branch=branch)
