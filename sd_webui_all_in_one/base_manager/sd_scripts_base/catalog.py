"""Implementation grouped from the former ``sd_scripts_base.py`` module."""

from __future__ import annotations

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
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
)
from sd_webui_all_in_one.ansi_color import ANSIColor

from sd_webui_all_in_one.base_manager.sd_scripts_base.shared import logger

SDScriptsBranchType: TypeAlias = Literal[
    "sd_scripts_main",
    "sd_scripts_dev",
    "sd_scripts_sd3",
    "ai_toolkit_main",
    "finetrainers_main",
    "diffusion_pipe_main",
    "musubi_tuner_main",
]

SD_SCRIPTS_BRANCH_LIST: list[SDScriptsBranchType] = cast(list[SDScriptsBranchType], list(get_args(SDScriptsBranchType)))


class SDScriptsBranchInfo(TypedDict):
    """SD Scripts 分支信息"""

    name: str
    """SD Scripts 分支名称"""

    dtype: SDScriptsBranchType
    """SD Scripts 分支类型"""

    url: str
    """SD Scripts 分支的 Git 仓库地址"""

    branch: str
    """SD Scripts 的 Git 分支名称"""

    use_submodule: bool
    """SD Scripts 分支中是否包含 Git 子模块"""


SD_SCRIPTS_BRANCH_INFO_DICT: list[SDScriptsBranchInfo] = [
    {
        "name": "kohya-ss - sd-scripts 主分支",
        "dtype": "sd_scripts_main",
        "url": "https://github.com/kohya-ss/sd-scripts",
        "branch": "main",
        "use_submodule": False,
    },
    {
        "name": "kohya-ss - sd-scripts 测试分支",
        "dtype": "sd_scripts_dev",
        "url": "https://github.com/kohya-ss/sd-scripts",
        "branch": "dev",
        "use_submodule": False,
    },
    {
        "name": "kohya-ss - sd-scripts SD3 分支",
        "dtype": "sd_scripts_sd3",
        "url": "https://github.com/kohya-ss/sd-scripts",
        "branch": "sd3",
        "use_submodule": False,
    },
    {
        "name": "ostris - ai-toolkit 分支",
        "dtype": "ai_toolkit_main",
        "url": "https://github.com/ostris/ai-toolkit",
        "branch": "main",
        "use_submodule": True,
    },
    {
        "name": "a-r-r-o-w - finetrainers 分支",
        "dtype": "finetrainers_main",
        "url": "https://github.com/a-r-r-o-w/finetrainers",
        "branch": "main",
        "use_submodule": False,
    },
    {
        "name": "tdrussell - diffusion-pipe 分支",
        "dtype": "diffusion_pipe_main",
        "url": "https://github.com/tdrussell/diffusion-pipe",
        "branch": "main",
        "use_submodule": True,
    },
    {
        "name": "kohya-ss - musubi-tuner 分支",
        "dtype": "musubi_tuner_main",
        "url": "https://github.com/kohya-ss/musubi-tuner",
        "branch": "main",
        "use_submodule": False,
    },
]


def display_sd_scripts_branch_list(
    branch_list: list[SDScriptsBranchInfo],
) -> None:
    """显示 SD Scripts 分支列表

    Args:
        branch_list (list[SDScriptsBranchInfo]):
            SD Scripts 分支信息列表
    """
    for index, info in enumerate(branch_list, start=1):
        name = info["name"]
        dtype = info["dtype"]
        print(f"- {ANSIColor.GOLD}{index}{ANSIColor.RESET}、{ANSIColor.WHITE}{name}{ANSIColor.RESET} ({ANSIColor.BLUE}{dtype}{ANSIColor.RESET})")


def switch_sd_scripts_branch(
    sd_scripts_path: Path,
    branch: SDScriptsBranchType | None = None,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    interactive_mode: bool = False,
    list_only: bool = False,
) -> None:
    """切换 SD Scripts 分支

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录
        branch (SDScriptsBranchType | None):
            要切换的 SD Scripts 分支
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
            传入未知的 SD Scripts 分支时
    """

    def _switch(
        input_branch: SDScriptsBranchType | None = None,
        input_index: int | None = None,
    ) -> None:
        nonlocal branch
        if input_index is not None:
            if not 0 < input_index <= len(SD_SCRIPTS_BRANCH_INFO_DICT):
                raise ValueError(f"索引值 {input_index} 超出范围, 有效范围为: 1 ~ {len(SD_SCRIPTS_BRANCH_INFO_DICT)}")
            branch_info = SD_SCRIPTS_BRANCH_INFO_DICT[input_index - 1]
        elif input_branch is not None:
            if input_branch not in SD_SCRIPTS_BRANCH_LIST:
                raise ValueError(f"未知的 SD Scripts 分支: '{input_branch}'")
            branch_info = [x for x in SD_SCRIPTS_BRANCH_INFO_DICT if input_branch == x["dtype"]][0]
        else:
            raise ValueError("需要提供 `branch` 或 `index` 才能进行分支切换")

        # 准备 Git 配置
        custom_env = apply_git_base_config_and_github_mirror(
            use_github_mirror=use_github_mirror,
            custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
            origin_env=os.environ.copy(),
        )
        apply_git_config_global_to_process(custom_env)

        logger.info("切换 SD Scripts 分支到 %s", branch_info["name"])
        git_warpper.switch_branch(
            path=sd_scripts_path,
            branch=branch_info["branch"],
            new_url=branch_info["url"],
            recurse_submodules=branch_info["use_submodule"],
        )
        logger.info("切换 SD Scripts 分支完成")

    if list_only:
        print_divider("=")
        display_sd_scripts_branch_list(SD_SCRIPTS_BRANCH_INFO_DICT)
        print_divider("=")
        return

    if interactive_mode:
        input_err = (0, None)
        while True:
            print_divider("=")
            display_sd_scripts_branch_list(SD_SCRIPTS_BRANCH_INFO_DICT)
            print_divider("=")

            i, m = input_err
            if i == 1:
                logger.warning("输入有误, 请重试")
            elif i == 2:
                logger.warning("输入的数字有误, %s, 请重新输入", m)
            input_err = (0, None)

            print(
                "请选择要切换的 SD Scripts 分支\n提示:\n1. 输入数字后回车即可选择切换到指定的分支\n2. 输入 exit 后回车退出分支切换",
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
