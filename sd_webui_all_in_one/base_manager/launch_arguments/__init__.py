"""WebUI 启动参数目录的解析与发现"""

from sd_webui_all_in_one.base_manager.launch_arguments.models import (
    CATALOG_SCHEMA_VERSION,
    DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    MAX_DIAGNOSTIC_OUTPUT,
    LaunchArgumentValueKind,
    LaunchArgumentDiagnostic,
    LaunchArgumentDefinition,
    LaunchArgumentCatalog,
    LaunchArgumentDiscoveryContext,
    HelpCommand,
)
from sd_webui_all_in_one.base_manager.launch_arguments.process import cancel_launch_argument_discovery
from sd_webui_all_in_one.base_manager.launch_arguments.parser_object import parse_argument_parser
from sd_webui_all_in_one.base_manager.launch_arguments.help_parser import parse_argparse_help
from sd_webui_all_in_one.base_manager.launch_arguments.catalog import (
    build_launch_argument_catalog,
    build_launch_argument_catalog_from_parser,
)
from sd_webui_all_in_one.base_manager.launch_arguments.discovery import (
    build_script_help_command,
    discover_launch_argument_catalog,
)

__all__ = [
    # 类型和常量
    "CATALOG_SCHEMA_VERSION",
    "DEFAULT_DISCOVERY_TIMEOUT_SECONDS",
    "MAX_DIAGNOSTIC_OUTPUT",
    "LaunchArgumentValueKind",
    "LaunchArgumentDiagnostic",
    "LaunchArgumentDefinition",
    "LaunchArgumentCatalog",
    "LaunchArgumentDiscoveryContext",
    "HelpCommand",
    # 解析
    "parse_argument_parser",
    "parse_argparse_help",
    # 目录构建
    "build_launch_argument_catalog",
    "build_launch_argument_catalog_from_parser",
    # 发现
    "build_script_help_command",
    "discover_launch_argument_catalog",
    "cancel_launch_argument_discovery",
]
