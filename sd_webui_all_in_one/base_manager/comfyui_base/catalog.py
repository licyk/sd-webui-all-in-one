"""Implementation grouped from the former ``comfyui_base.py`` module."""

from __future__ import annotations

import importlib
from pathlib import Path
from sd_webui_all_in_one.launch_arguments import (
    DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    LaunchArgumentCatalog,
    build_script_help_command,
    discover_launch_argument_catalog,
)
from sd_webui_all_in_one.config import (
    ROOT_PATH,
)
from sd_webui_all_in_one.utils import TemporaryModulePath

COMFYUI_REPO_URL = "https://github.com/Comfy-Org/ComfyUI"
COMFYUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY = "comfy.cli_args:parser"

COMFYUI_CONFIG_PATH = ROOT_PATH / "base_manager" / "config" / "comfy.settings.json"


def get_comfyui_launch_argument_catalog(
    comfyui_path: str | Path,
    use_parser_object: bool = True,
    *,
    python_executable: str | Path | None = None,
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
) -> LaunchArgumentCatalog:
    """发现 ComfyUI 启动参数，对象解析失败时回退到 ``--help``。

    Args:
        comfyui_path (str | Path): ComfyUI 根目录。
        use_parser_object (bool): 是否优先解析实际参数对象。
        python_executable (str | Path | None): 执行 ``--help`` 的 Python。
        timeout_seconds (float): ``--help`` 命令超时秒数。

    Returns:
        LaunchArgumentCatalog: 规范化的 ComfyUI 启动参数目录。
    """
    path = Path(comfyui_path)

    def load_parser():
        with TemporaryModulePath(path):
            return importlib.import_module("comfy.cli_args").parser

    return discover_launch_argument_catalog(
        "comfyui",
        path,
        provider_identity=COMFYUI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
        help_command_factory=lambda context: build_script_help_command(context, ("main.py",)),
        parser_loader=load_parser,
        parser_source_identity="comfy.cli_args:parser",
        use_parser_object=use_parser_object,
        python_executable=python_executable,
        timeout_seconds=timeout_seconds,
    )
