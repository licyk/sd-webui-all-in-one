"""Implementation grouped from the former ``invokeai_base.py`` module."""

from __future__ import annotations

import importlib
import importlib.metadata
from pathlib import Path
from sd_webui_all_in_one.launch_arguments import (
    DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    LaunchArgumentCatalog,
    discover_launch_argument_catalog,
)

from .components import _invokeai_help_command, _temporary_invokeai_root

INVOKEAI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY = "invokeai.frontend.cli.arg_parser:_parser"


def get_invokeai_launch_argument_catalog(
    invokeai_path: str | Path,
    use_parser_object: bool = True,
    *,
    python_executable: str | Path | None = None,
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
) -> LaunchArgumentCatalog:
    """发现 InvokeAI 启动参数，对象解析失败时回退到帮助输出。

    Args:
        invokeai_path (str | Path): InvokeAI 根目录。
        use_parser_object (bool): 是否优先解析实际参数对象。
        python_executable (str | Path | None): 执行帮助命令的 Python。
        timeout_seconds (float): 帮助命令超时秒数。

    Returns:
        LaunchArgumentCatalog: 规范化的启动参数目录。
    """
    path = Path(invokeai_path)

    def load_parser():
        with _temporary_invokeai_root(path):
            return importlib.import_module("invokeai.frontend.cli.arg_parser")._parser

    return discover_launch_argument_catalog(
        "invokeai",
        path,
        provider_identity=INVOKEAI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
        help_command_factory=_invokeai_help_command,
        parser_loader=load_parser,
        parser_source_identity=INVOKEAI_LAUNCH_ARGUMENT_PROVIDER_IDENTITY,
        use_parser_object=use_parser_object,
        python_executable=python_executable,
        timeout_seconds=timeout_seconds,
    )
