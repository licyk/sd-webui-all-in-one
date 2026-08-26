"""Implementation grouped from the former ``fooocus_base.py`` module."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import (
    cast,
    TypeAlias,
    TypedDict,
    Literal,
    get_args,
)
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
    print_divider,
)
from sd_webui_all_in_one.launch_arguments import (
    DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    LaunchArgumentCatalog,
    build_script_help_command,
    discover_launch_argument_catalog,
)
from sd_webui_all_in_one.config import (
    ROOT_PATH,
)
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
)
from sd_webui_all_in_one.ansi_color import ANSIColor
from sd_webui_all_in_one.utils import TemporaryModulePath

from sd_webui_all_in_one.base_manager.fooocus_base.shared import logger

FOOOCUS_LAUNCH_ARGUMENT_PROVIDER_IDENTITY = "args_manager:args_parser.parser"


def get_fooocus_launch_argument_catalog(
    fooocus_path: str | Path,
    use_parser_object: bool = True,
    *,
    python_executable: str | Path | None = None,
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
) -> LaunchArgumentCatalog:
    """发现 Fooocus 启动参数，对象解析失败时回退到 ``--help``。

    Args:
        fooocus_path (str | Path): Fooocus 根目录。
        use_parser_object (bool): 是否优先解析实际参数对象。
        python_executable (str | Path | None): 执行 ``--help`` 的 Python。
        timeout_seconds (float): ``--help`` 命令超时秒数。

    Returns:
        LaunchArgumentCatalog: 规范化的启动参数目录。
    """
    path = Path(fooocus_path)

    def load_parser():
        with TemporaryModulePath(path):
            return importlib.import_module("args_manager").args_parser.parser

    return discover_launch_argument_catalog(
        "fooocus",
        path,
        provider_identity=FOOOCUS_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
        help_command_factory=lambda context: build_script_help_command(context, ("launch.py",)),
        parser_loader=load_parser,
        parser_source_identity="args_manager:args_parser.parser",
        use_parser_object=use_parser_object,
        python_executable=python_executable,
        timeout_seconds=timeout_seconds,
    )


FooocusBranchType: TypeAlias = Literal[
    "fooocus_main",
    "ruined_fooocus_main",
    "fooocus_mre_main",
]

FOOOCUS_BRANCH_LIST: list[FooocusBranchType] = cast(list[FooocusBranchType], list(get_args(FooocusBranchType)))


class FooocusBranchInfo(TypedDict):
    """Fooocus 分支信息"""

    name: str
    """Fooocus 分支名称"""

    dtype: FooocusBranchType
    """Fooocus 分支类型"""

    url: str
    """Fooocus 分支的 Git 仓库地址"""

    branch: str
    """Fooocus 的 Git 分支名称"""

    use_submodule: bool
    """Fooocus 分支中是否包含 Git 子模块"""


FOOOCUS_BRANCH_INFO_DICT: list[FooocusBranchInfo] = [
    {
        "name": "lllyasviel - Fooocus 分支",
        "dtype": "fooocus_main",
        "url": "https://github.com/licyk/Fooocus",
        "branch": "licyk_dev",
        "use_submodule": False,
    },
    {
        "name": "runew0lf - RuinedFooocus 分支",
        "dtype": "ruined_fooocus_main",
        "url": "https://github.com/runew0lf/RuinedFooocus",
        "branch": "main",
        "use_submodule": False,
    },
    {
        "name": "MoonRide303 - Fooocus-MRE 分支",
        "dtype": "fooocus_mre_main",
        "url": "https://github.com/MoonRide303/Fooocus-MRE",
        "branch": "moonride-main",
        "use_submodule": False,
    },
]


def get_fooocus_branch_presets() -> dict[str, object]:
    """返回 Fooocus 内置分支预设。

    Returns:
        dict[str, object]: 包含可用 Fooocus 分支列表和类型列表的字典。
    """
    return {"branches": list(FOOOCUS_BRANCH_INFO_DICT), "types": list(FOOOCUS_BRANCH_LIST)}


FOOOCUS_PRESET_HF_PATH = ROOT_PATH / "base_manager" / "config" / "fooocus_config_huggingface.json"

FOOOCUS_PRESET_MS_PATH = ROOT_PATH / "base_manager" / "config" / "fooocus_config_modelscope.json"


def display_fooocus_branch_list(
    branch_list: list[FooocusBranchInfo],
) -> None:
    """显示 Fooocus 分支列表

    Args:
        branch_list (list[FooocusBranchInfo]):
            Fooocus 分支信息列表
    """
    for index, info in enumerate(branch_list, start=1):
        name = info["name"]
        dtype = info["dtype"]
        print(f"- {ANSIColor.GOLD}{index}{ANSIColor.RESET}、{ANSIColor.WHITE}{name}{ANSIColor.RESET} ({ANSIColor.BLUE}{dtype}{ANSIColor.RESET})")


def switch_fooocus_branch(
    fooocus_path: Path,
    branch: FooocusBranchType | None = None,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    interactive_mode: bool = False,
    list_only: bool = False,
) -> None:
    """切换 Fooocus 分支

    Args:
        fooocus_path (Path):
            Fooocus 根目录
        branch (FooocusBranchType | None):
            要切换的 Fooocus 分支
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
            传入未知的 Fooocus 分支时
    """

    def _switch(
        input_branch: FooocusBranchType | None = None,
        input_index: int | None = None,
    ) -> None:
        nonlocal branch
        if input_index is not None:
            if not 0 < input_index <= len(FOOOCUS_BRANCH_INFO_DICT):
                raise ValueError(f"索引值 {input_index} 超出范围, 有效范围为: 1 ~ {len(FOOOCUS_BRANCH_INFO_DICT)}")
            branch_info = FOOOCUS_BRANCH_INFO_DICT[input_index - 1]
        elif input_branch is not None:
            if input_branch not in FOOOCUS_BRANCH_LIST:
                raise ValueError(f"未知的 Fooocus 分支: '{input_branch}'")
            branch_info = [x for x in FOOOCUS_BRANCH_INFO_DICT if input_branch == x["dtype"]][0]
        else:
            raise ValueError("需要提供 `branch` 或 `index` 才能进行分支切换")

        # 准备 Git 配置
        custom_env = apply_git_base_config_and_github_mirror(
            use_github_mirror=use_github_mirror,
            custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
            origin_env=os.environ.copy(),
        )
        apply_git_config_global_to_process(custom_env)

        logger.info("切换 Fooocus 分支到 %s", branch_info["name"])
        git_warpper.switch_branch(
            path=fooocus_path,
            branch=branch_info["branch"],
            new_url=branch_info["url"],
            recurse_submodules=branch_info["use_submodule"],
        )
        logger.info("切换 Fooocus 分支完成")

    if list_only:
        print_divider("=")
        display_fooocus_branch_list(FOOOCUS_BRANCH_INFO_DICT)
        print_divider("=")
        return

    if interactive_mode:
        input_err = (0, None)
        while True:
            print_divider("=")
            display_fooocus_branch_list(FOOOCUS_BRANCH_INFO_DICT)
            print_divider("=")

            i, m = input_err
            if i == 1:
                logger.warning("输入有误, 请重试")
            elif i == 2:
                logger.warning("输入的数字有误, %s, 请重新输入", m)
            input_err = (0, None)

            print(
                "请选择要切换的 Fooocus 分支\n提示:\n1. 输入数字后回车即可选择切换到指定的分支\n2. 输入 exit 后回车退出分支切换",
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
