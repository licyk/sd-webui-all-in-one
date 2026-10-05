"""RVC Next WebUI 启动参数目录和常量。"""

from __future__ import annotations

import importlib
from pathlib import Path
from sd_webui_all_in_one.launch_arguments import (
    DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    LaunchArgumentCatalog,
    build_script_help_command,
    discover_launch_argument_catalog,
)
from sd_webui_all_in_one.utils import TemporaryModulePath

RVC_NEXT_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY = "rvc_next_webui.cmd_args:get_args_parser"


def get_rvc_next_webui_launch_argument_catalog(
    rvc_next_webui_path: str | Path,
    use_parser_object: bool = True,
    *,
    python_executable: str | Path | None = None,
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
) -> LaunchArgumentCatalog:
    """发现 RVC Next WebUI 启动参数，对象解析失败时回退到 ``--help``。

    Args:
        rvc_next_webui_path (str | Path): RVC Next WebUI 根目录。
        use_parser_object (bool): 是否优先解析实际参数对象。
        python_executable (str | Path | None): 执行 ``--help`` 的 Python。
        timeout_seconds (float): ``--help`` 命令超时秒数。

    Returns:
        LaunchArgumentCatalog: 规范化的启动参数目录。
    """
    path = Path(rvc_next_webui_path)

    def load_parser():
        with TemporaryModulePath(path):
            return importlib.import_module("rvc_next_webui.cmd_args").get_args_parser()

    return discover_launch_argument_catalog(
        "rvc_next_webui",
        path,
        provider_identity=RVC_NEXT_WEBUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
        help_command_factory=lambda context: build_script_help_command(context, ("launch.py",)),
        parser_loader=load_parser,
        parser_source_identity="rvc_next_webui.cmd_args:get_args_parser",
        use_parser_object=use_parser_object,
        python_executable=python_executable,
        timeout_seconds=timeout_seconds,
    )


RVC_NEXT_WEBUI_REPO = "https://github.com/licyk/rvc-next-webui"

RVC_NEXT_PACKAGE_NAME = "rvc-next"
"""RVC Next WebUI 依赖的 RVC Next 软件包名称"""

RVC_NEXT_TORCH_MIN_VERSION = "2.7.1"
"""RVC Next 需要的最低 PyTorch 版本"""

RVC_NEXT_WEBUI_MANAGED_LAUNCH_ARGS = ("--skip-check", "--disable-proxy")
"""启动时固定传入的参数, 运行环境检查和代理由 SD WebUI All In One 负责"""
