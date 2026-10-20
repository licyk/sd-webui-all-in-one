"""只读发现已安装 WebUI 支持的启动参数"""

from __future__ import annotations

import argparse
import hashlib
import sys
import threading
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from pathlib import Path

from sd_webui_all_in_one.base_manager.launch_arguments.models import (
    DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    LaunchArgumentDiagnostic,
    LaunchArgumentCatalog,
    LaunchArgumentDiscoveryContext,
    HelpCommand,
)
from sd_webui_all_in_one.base_manager.launch_arguments.process import _run_help
from sd_webui_all_in_one.base_manager.launch_arguments.help_parser import _select_help_document
from sd_webui_all_in_one.base_manager.launch_arguments.catalog import (
    build_launch_argument_catalog,
    build_launch_argument_catalog_from_parser,
)


_PARSER_LOAD_LOCK = threading.RLock()


@contextmanager
def _temporary_parser_argv() -> Generator[None, None, None]:
    """加载第三方参数模块时隐藏宿主进程的命令行参数。"""
    original_argv = sys.argv
    program = original_argv[0] if original_argv else str(sys.executable)
    sys.argv = [program]
    try:
        yield
    finally:
        sys.argv = original_argv


def build_script_help_command(
    context: LaunchArgumentDiscoveryContext,
    scripts: Sequence[str],
) -> HelpCommand | None:
    """为候选启动脚本构建通用 ``--help`` 命令。

    Args:
        context (LaunchArgumentDiscoveryContext): 参数发现上下文。
        scripts (Sequence[str]): 按优先级排列的启动脚本相对路径。

    Returns:
        HelpCommand | None: 帮助命令；没有候选脚本时返回 ``None``。
    """
    script = next((context.webui_path / item for item in scripts if (context.webui_path / item).is_file()), None)
    if script is None:
        return None
    digest = hashlib.sha256(script.read_bytes()).hexdigest()[:16]
    source_parts = [script.name, digest]
    head_path = context.webui_path / ".git" / "HEAD"
    try:
        head = head_path.read_text(encoding="utf-8").strip()
        source_parts.append(head)
        if head.startswith("ref: "):
            source_parts.append((context.webui_path / ".git" / head[5:]).read_text(encoding="utf-8").strip())
    except OSError:
        pass
    return HelpCommand([str(context.python_executable), str(script), "--help"], ":".join(source_parts))


def _catalog_from_help_command(
    context: LaunchArgumentDiscoveryContext,
    command: HelpCommand,
    provider_identity: str,
) -> LaunchArgumentCatalog:
    stdout, stderr, failure = _run_help(command, context)
    if failure is not None:
        return build_launch_argument_catalog(
            context.webui_type,
            [],
            [failure],
            provider_identity=provider_identity,
            source_identity=command.source_identity,
        )
    arguments, diagnostics = _select_help_document(stdout, stderr)
    return build_launch_argument_catalog(
        context.webui_type,
        arguments,
        diagnostics,
        provider_identity=provider_identity,
        source_identity=command.source_identity,
    )


def discover_launch_argument_catalog(
    webui_type: str,
    webui_path: str | Path,
    *,
    provider_identity: str,
    help_command_factory: Callable[[LaunchArgumentDiscoveryContext], HelpCommand | None],
    parser_loader: Callable[[], argparse.ArgumentParser] | None = None,
    parser_source_identity: str | None = None,
    use_parser_object: bool = True,
    python_executable: str | Path | None = None,
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
) -> LaunchArgumentCatalog:
    """使用对象优先、失败回退帮助文本的策略发现参数目录。

    Args:
        webui_type (str): WebUI 类型。
        webui_path (str | Path): WebUI 安装路径。
        provider_identity (str): 调用方定义的稳定发现器标识。
        help_command_factory (Callable[[LaunchArgumentDiscoveryContext], HelpCommand | None]):
            通用帮助命令构造函数。
        parser_loader (Callable[[], argparse.ArgumentParser] | None):
            实际 ``ArgumentParser`` 对象加载函数。
        parser_source_identity (str | None): 参数对象来源的稳定标识。
        use_parser_object (bool): 是否优先解析实际参数对象。
        python_executable (str | Path | None): 用于执行帮助命令的 Python。
        timeout_seconds (float): 帮助命令超时秒数。

    Returns:
        LaunchArgumentCatalog: 当前安装实例的启动参数目录。
    """
    context = LaunchArgumentDiscoveryContext(
        webui_type=webui_type,
        webui_path=Path(webui_path),
        python_executable=Path(python_executable or sys.executable),
        timeout_seconds=max(0.1, min(float(timeout_seconds), 30.0)),
    )
    parser_failure: LaunchArgumentDiagnostic | None = None
    if use_parser_object:
        if parser_loader is None:
            parser_failure = LaunchArgumentDiagnostic("warning", "object_discovery_unavailable", "No ArgumentParser object loader was provided")
        else:
            try:
                with _PARSER_LOAD_LOCK, _temporary_parser_argv():
                    parser = parser_loader()
                catalog = build_launch_argument_catalog_from_parser(
                    webui_type,
                    parser,
                    provider_identity=f"{provider_identity}:object",
                    source_identity=parser_source_identity or provider_identity,
                )
                errors = [diagnostic for diagnostic in catalog.diagnostics if diagnostic.severity == "error"]
                if not errors:
                    return catalog
                parser_failure = LaunchArgumentDiagnostic(
                    "warning",
                    "object_discovery_failed",
                    "ArgumentParser object parsing failed; falling back to --help",
                    "; ".join(diagnostic.message for diagnostic in errors),
                )
            except SystemExit as error:
                parser_failure = LaunchArgumentDiagnostic(
                    "warning",
                    "object_discovery_failed",
                    "ArgumentParser loader exited; falling back to --help",
                    f"exit code: {error.code!r}",
                )
            except Exception as error:
                parser_failure = LaunchArgumentDiagnostic(
                    "warning",
                    "object_discovery_failed",
                    "Unable to load ArgumentParser object; falling back to --help",
                    str(error),
                )

    try:
        command = help_command_factory(context)
    except Exception as error:
        diagnostics = [diagnostic for diagnostic in [parser_failure] if diagnostic is not None]
        diagnostics.append(LaunchArgumentDiagnostic("error", "discovery_failed", "Unable to build WebUI help command", str(error)))
        return build_launch_argument_catalog(
            webui_type,
            [],
            diagnostics,
            provider_identity=f"{provider_identity}:help",
            source_identity="help-command:failed",
        )
    if command is None:
        diagnostics = [diagnostic for diagnostic in [parser_failure] if diagnostic is not None]
        diagnostics.append(LaunchArgumentDiagnostic("error", "discovery_unavailable", "No supported WebUI help command is available"))
        return build_launch_argument_catalog(
            webui_type,
            [],
            diagnostics,
            provider_identity=f"{provider_identity}:help",
            source_identity="help-command:missing",
        )

    catalog = _catalog_from_help_command(context, command, f"{provider_identity}:help")
    if parser_failure is None:
        return catalog
    return build_launch_argument_catalog(
        webui_type,
        catalog.arguments,
        [parser_failure, *catalog.diagnostics],
        provider_identity=f"{provider_identity}:help-fallback",
        source_identity=command.source_identity,
    )
