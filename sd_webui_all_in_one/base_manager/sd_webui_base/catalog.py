"""Implementation grouped from the former ``sd_webui_base.py`` module."""

from __future__ import annotations

import importlib
import os
import importlib.metadata
from typing import (
    cast,
    TypedDict,
    Literal,
    TypeAlias,
    get_args,
)
from pathlib import Path
from sd_webui_all_in_one.ansi_color import ANSIColor
from sd_webui_all_in_one.launch_arguments import (
    DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    LaunchArgumentCatalog,
    build_script_help_command,
    discover_launch_argument_catalog,
)
from sd_webui_all_in_one.config import (
    ROOT_PATH,
)
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
    print_divider,
)
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
)
from sd_webui_all_in_one.utils import TemporaryModulePath

from sd_webui_all_in_one.base_manager.sd_webui_base.shared import logger

SD_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY = "modules.cmd_args:parser"


def get_sd_webui_launch_argument_catalog(
    sd_webui_path: str | Path,
    use_parser_object: bool = True,
    *,
    python_executable: str | Path | None = None,
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
) -> LaunchArgumentCatalog:
    """发现 SD WebUI 启动参数，对象解析失败时回退到 ``--help``。

    Args:
        sd_webui_path (str | Path): Stable Diffusion WebUI 根目录。
        use_parser_object (bool): 是否优先解析实际参数对象。
        python_executable (str | Path | None): 执行 ``--help`` 的 Python。
        timeout_seconds (float): ``--help`` 命令超时秒数。

    Returns:
        LaunchArgumentCatalog: 规范化的启动参数目录。
    """
    path = Path(sd_webui_path)

    def load_parser():
        with TemporaryModulePath(path):
            return importlib.import_module("modules.cmd_args").parser

    return discover_launch_argument_catalog(
        "sd_webui",
        path,
        provider_identity=SD_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
        help_command_factory=lambda context: build_script_help_command(context, ("launch.py",)),
        parser_loader=load_parser,
        parser_source_identity="modules.cmd_args:parser",
        use_parser_object=use_parser_object,
        python_executable=python_executable,
        timeout_seconds=timeout_seconds,
    )


SDWebUiBranchType: TypeAlias = Literal[
    "sd_webui_forge_neo",
    "sd_webui_forge_classic",
    "sd_webui_main",
    "sd_webui_dev",
    "sd_webui_forge",
    "sd_webui_reforge_main",
    "sd_webui_reforge_dev",
    "sd_webui_amdgpu",
    "sd_next_main",
    "sd_next_dev",
]

SD_WEBUI_BRANCH_LIST: list[SDWebUiBranchType] = cast(list[SDWebUiBranchType], list(get_args(SDWebUiBranchType)))


class SDWebUiBranchInfo(TypedDict):
    """Stable Diffusion WebUI 分支信息"""

    name: str
    """Stable Diffusion WebUI 分支名称"""

    dtype: SDWebUiBranchType
    """Stable Diffusion WebUI 分支类型"""

    url: str
    """Stable Diffusion WebUI 分支的 Git 仓库地址"""

    branch: str
    """Stable Diffusion WebUI 的 Git 分支名称"""

    use_submodule: bool
    """Stable Diffusion WebUI 分支中是否包含 Git 子模块"""


SD_WEBUI_BRANCH_INFO_DICT: list[SDWebUiBranchInfo] = [
    {
        "name": "Haoming02 - Stable-Diffusion-WebUI-Forge-Neo 分支",
        "dtype": "sd_webui_forge_neo",
        "url": "https://github.com/Haoming02/sd-webui-forge-classic",
        "branch": "neo",
        "use_submodule": False,
    },
    {
        "name": "Haoming02 - Stable-Diffusion-WebUI-Forge-Classic 分支",
        "dtype": "sd_webui_forge_classic",
        "url": "https://github.com/Haoming02/sd-webui-forge-classic",
        "branch": "classic",
        "use_submodule": False,
    },
    {
        "name": "AUTOMATIC1111 - Stable-Diffusion-WebUI 主分支",
        "dtype": "sd_webui_main",
        "url": "https://github.com/AUTOMATIC1111/stable-diffusion-webui",
        "branch": "master",
        "use_submodule": False,
    },
    {
        "name": "AUTOMATIC1111 - Stable-Diffusion-WebUI 测试分支",
        "dtype": "sd_webui_dev",
        "url": "https://github.com/AUTOMATIC1111/stable-diffusion-webui",
        "branch": "dev",
        "use_submodule": False,
    },
    {
        "name": "lllyasviel - Stable-Diffusion-WebUI-Forge 分支",
        "dtype": "sd_webui_forge",
        "url": "https://github.com/lllyasviel/stable-diffusion-webui-forge",
        "branch": "main",
        "use_submodule": False,
    },
    {
        "name": "Panchovix - Stable-Diffusion-WebUI-reForge 主分支",
        "dtype": "sd_webui_reforge_main",
        "url": "https://github.com/Panchovix/stable-diffusion-webui-reForge",
        "branch": "main",
        "use_submodule": False,
    },
    {
        "name": "Panchovix - Stable-Diffusion-WebUI-reForge 测试分支",
        "dtype": "sd_webui_reforge_dev",
        "url": "https://github.com/Panchovix/stable-diffusion-webui-reForge",
        "branch": "dev",
        "use_submodule": False,
    },
    {
        "name": "lshqqytiger - Stable-Diffusion-WebUI-AMDGPU 分支",
        "dtype": "sd_webui_amdgpu",
        "url": "https://github.com/lshqqytiger/stable-diffusion-webui-amdgpu",
        "branch": "master",
        "use_submodule": False,
    },
    {
        "name": "vladmandic - SD.NEXT 主分支",
        "dtype": "sd_next_main",
        "url": "https://github.com/vladmandic/sdnext",
        "branch": "master",
        "use_submodule": True,
    },
    {
        "name": "vladmandic - SD.NEXT 测试分支",
        "dtype": "sd_next_dev",
        "url": "https://github.com/vladmandic/sdnext",
        "branch": "dev",
        "use_submodule": True,
    },
]


def get_sd_webui_branch_presets() -> dict[str, object]:
    """返回 Stable Diffusion WebUI 内置分支预设。

    Returns:
        dict[str, object]: 包含可用 Stable Diffusion WebUI 分支列表和类型列表的字典。
    """
    return {"branches": list(SD_WEBUI_BRANCH_INFO_DICT), "types": list(SD_WEBUI_BRANCH_LIST)}


SD_WEBUI_CONFIG_PATH = ROOT_PATH / "base_manager" / "config" / "sd_webui_config.json"


def display_sd_webui_branch_list(
    branch_list: list[SDWebUiBranchInfo],
) -> None:
    """显示 Stable Diffusion WebUI 分支列表

    Args:
        branch_list (list[SDWebUiBranchInfo]):
            Stable Diffusion WebUI 分支信息列表
    """
    for index, info in enumerate(branch_list, start=1):
        name = info["name"]
        dtype = info["dtype"]
        print(f"- {ANSIColor.GOLD}{index}{ANSIColor.RESET}、{ANSIColor.WHITE}{name}{ANSIColor.RESET} ({ANSIColor.BLUE}{dtype}{ANSIColor.RESET})")


def switch_sd_webui_branch(
    sd_webui_path: Path,
    branch: SDWebUiBranchType | None = None,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    interactive_mode: bool = False,
    list_only: bool = False,
) -> None:
    """切换 Stable Diffusion WebUI 分支

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        branch (SDWebUiBranchType | None):
            要切换的 Stable Diffusion WebUI 分支
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
            传入未知的 Stable Diffusion WebUI 分支时
    """

    def _switch(
        input_branch: SDWebUiBranchType | None = None,
        input_index: int | None = None,
    ) -> None:
        nonlocal branch
        if input_index is not None:
            if not 0 < input_index <= len(SD_WEBUI_BRANCH_INFO_DICT):
                raise ValueError(f"索引值 {input_index} 超出范围, 有效范围为: 1 ~ {len(SD_WEBUI_BRANCH_INFO_DICT)}")
            branch_info = SD_WEBUI_BRANCH_INFO_DICT[input_index - 1]
        elif input_branch is not None:
            if input_branch not in SD_WEBUI_BRANCH_LIST:
                raise ValueError(f"未知的 Stable Diffusion WebUI 分支: '{input_branch}'")
            branch_info = [x for x in SD_WEBUI_BRANCH_INFO_DICT if input_branch == x["dtype"]][0]
        else:
            raise ValueError("需要提供 `branch` 或 `index` 才能进行分支切换")

        # 准备 Git 配置
        custom_env = apply_git_base_config_and_github_mirror(
            use_github_mirror=use_github_mirror,
            custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
            origin_env=os.environ.copy(),
        )
        apply_git_config_global_to_process(custom_env)

        logger.info("切换 Stable Diffusion WebUI 分支到 %s", branch_info["name"])
        git_warpper.switch_branch(
            path=sd_webui_path,
            branch=branch_info["branch"],
            new_url=branch_info["url"],
            recurse_submodules=branch_info["use_submodule"],
        )
        logger.info("切换 Stable Diffusion WebUI 分支完成")

    if list_only:
        print_divider("=")
        display_sd_webui_branch_list(SD_WEBUI_BRANCH_INFO_DICT)
        print_divider("=")
        return

    if interactive_mode:
        input_err = (0, None)
        while True:
            print_divider("=")
            display_sd_webui_branch_list(SD_WEBUI_BRANCH_INFO_DICT)
            print_divider("=")

            i, m = input_err
            if i == 1:
                logger.warning("输入有误, 请重试")
            elif i == 2:
                logger.warning("输入的数字有误, %s, 请重新输入", m)
            input_err = (0, None)

            print(
                "请选择要切换的 Stable Diffusion WebUI 分支\n提示:\n1. 输入数字后回车即可选择切换到指定的分支\n2. 输入 exit 后回车退出分支切换",
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
