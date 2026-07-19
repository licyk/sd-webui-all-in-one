"""只读发现已安装 WebUI 支持的启动参数。"""

from __future__ import annotations

import argparse
import atexit
import hashlib
import importlib.metadata
import json
import os
import re
import signal
import subprocess
import sys
import threading
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol, TypedDict


CATALOG_SCHEMA_VERSION = 2
DEFAULT_DISCOVERY_TIMEOUT_SECONDS = 15.0
MAX_DIAGNOSTIC_OUTPUT = 4096


class LaunchArgumentValueKind(str, Enum):
    """启动参数值类型。"""

    BOOLEAN = "boolean"
    VALUE = "value"
    OPTIONAL_VALUE = "optional_value"
    MULTI_VALUE = "multi_value"


@dataclass(frozen=True, slots=True)
class LaunchArgumentDiagnostic:
    """启动参数发现诊断。"""

    severity: str
    code: str
    message: str
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class LaunchArgumentDefinition:
    """一个规范化的启动参数定义。"""

    name: str
    flags: list[str]
    value_kind: LaunchArgumentValueKind
    min_values: int
    max_values: int | None
    help: str
    category: str
    metavar: str | None
    choices: list[str]
    required: bool
    repeatable: bool
    exclusive_group: str | None
    exclusive_group_required: bool


@dataclass(frozen=True, slots=True)
class LaunchArgumentCatalog:
    """指定 WebUI 的启动参数目录。"""

    schema_version: int
    webui_type: str
    catalog_revision: str
    arguments: list[LaunchArgumentDefinition] = field(default_factory=list)
    diagnostics: list[LaunchArgumentDiagnostic] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """按稳定的蛇形命名 API 结构序列化。

        Returns:
            dict[str, object]: 可序列化的参数目录。
        """
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LaunchArgumentDiscoveryContext:
    """启动参数发现上下文。"""

    webui_type: str
    webui_path: Path
    python_executable: Path = Path(sys.executable)
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS


class LaunchArgumentProvider(Protocol):
    """启动参数提供器协议。"""

    def provider_identity(self) -> str:
        """返回规范化提供器契约的稳定标识。

        Returns:
            str: 稳定提供器标识。
        """

    def get_catalog(self, context: LaunchArgumentDiscoveryContext) -> LaunchArgumentCatalog:
        """发现并规范化当前安装实例的参数契约。

        Args:
            context (LaunchArgumentDiscoveryContext): 参数发现上下文。

        Returns:
            LaunchArgumentCatalog: 规范化后的参数目录。
        """


@dataclass(frozen=True, slots=True)
class HelpCommand:
    """用于提取帮助文档的子进程命令。"""

    argv: list[str]
    source_identity: str
    env: dict[str, str] | None = None


class _UsageFrame(TypedDict):
    opening: str
    flags: list[str]
    has_pipe: bool


_ACTIVE_PROCESSES: set[subprocess.Popen[str]] = set()
_ACTIVE_PROCESSES_LOCK = threading.Lock()


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=1)
    except (OSError, subprocess.TimeoutExpired):
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            pass


def cancel_launch_argument_discovery() -> None:
    """在 API 或进程关闭时终止所有进行中的发现子进程。"""
    with _ACTIVE_PROCESSES_LOCK:
        processes = list(_ACTIVE_PROCESSES)
    for process in processes:
        _terminate_process(process)


atexit.register(cancel_launch_argument_discovery)


def _normalize_process_output(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def _run_help(
    command: HelpCommand,
    context: LaunchArgumentDiscoveryContext,
) -> tuple[str, str, LaunchArgumentDiagnostic | None]:
    try:
        process = subprocess.Popen(
            command.argv,
            cwd=context.webui_path,
            env=command.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=os.name == "posix",
        )
    except OSError as error:
        return "", "", LaunchArgumentDiagnostic("error", "discovery_unavailable", "Unable to start WebUI help discovery", str(error))
    with _ACTIVE_PROCESSES_LOCK:
        _ACTIVE_PROCESSES.add(process)
    try:
        try:
            stdout, stderr = process.communicate(timeout=context.timeout_seconds)
        except subprocess.TimeoutExpired:
            _terminate_process(process)
            stdout, stderr = process.communicate()
            detail = (stdout + "\n" + stderr).strip()[-MAX_DIAGNOSTIC_OUTPUT:] or None
            return "", "", LaunchArgumentDiagnostic(
                "error",
                "discovery_timeout",
                f"WebUI help discovery exceeded {context.timeout_seconds:g} seconds",
                detail,
            )
    finally:
        with _ACTIVE_PROCESSES_LOCK:
            _ACTIVE_PROCESSES.discard(process)
    stdout = _normalize_process_output(stdout)
    stderr = _normalize_process_output(stderr)
    if process.returncode not in (0, None) and not stdout and not stderr:
        return "", "", LaunchArgumentDiagnostic("error", "discovery_failed", f"WebUI help discovery exited with code {process.returncode}")
    return stdout, stderr, None


_HEADING = re.compile(r"^(?P<name>\S[^:\n]*):\s*$")
_FLAG = re.compile(r"-{1,2}[A-Za-z0-9][A-Za-z0-9_-]*")
_CHOICES = re.compile(r"\{([^{}]+)\}")


def _category(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    if normalized in {"options", "optional_arguments", "arguments"}:
        return "general"
    return normalized or "other"


def _canonical_name(flags: list[str]) -> str:
    selected = next((flag for flag in flags if flag.startswith("--")), flags[0])
    return selected.lstrip("-").replace("-", "_")


def _normalized_flags(flags: Sequence[str]) -> list[str]:
    return sorted(
        set(flags),
        key=lambda flag: (0 if flag.startswith("-") and not flag.startswith("--") else 1, flag),
    )


def _value_shape(
    spec: str,
    help_text: str,
) -> tuple[LaunchArgumentValueKind, int, int | None, str | None, list[str], bool]:
    flags = list(_FLAG.finditer(spec))
    tail = spec[flags[-1].end():].strip(" ,") if flags else ""
    choices_match = _CHOICES.search(tail)
    choices = sorted({item.strip() for item in choices_match.group(1).split(",") if item.strip()}) if choices_match else []
    metavar = choices_match.group(0) if choices_match else (tail or None)
    if not tail:
        kind = LaunchArgumentValueKind.BOOLEAN
        min_values, max_values = 0, 0
    elif "..." in tail or tail in {"*", "+"}:
        kind = LaunchArgumentValueKind.MULTI_VALUE
        min_values = 0 if tail == "*" or (tail.startswith("[") and tail.endswith("]")) else 1
        max_values = None
    elif tail.startswith("[") and tail.endswith("]"):
        kind = LaunchArgumentValueKind.OPTIONAL_VALUE
        min_values, max_values = 0, 1
    else:
        kind = LaunchArgumentValueKind.VALUE
        min_values, max_values = 1, 1
    repeatable = bool(re.search(r"repeat|multiple times|more than once", help_text, re.I))
    return kind, min_values, max_values, metavar, choices, repeatable


def _argument_value_shape(
    action: argparse.Action,
) -> tuple[LaunchArgumentValueKind, int, int | None]:
    """将 argparse action 的 ``nargs`` 转换为统一值形态。"""
    nargs = action.nargs
    if nargs == 0:
        return LaunchArgumentValueKind.BOOLEAN, 0, 0
    if nargs in (None, 1):
        return LaunchArgumentValueKind.VALUE, 1, 1
    if nargs == argparse.OPTIONAL:
        return LaunchArgumentValueKind.OPTIONAL_VALUE, 0, 1
    if nargs in (argparse.ZERO_OR_MORE, argparse.REMAINDER):
        return LaunchArgumentValueKind.MULTI_VALUE, 0, None
    if nargs in (argparse.ONE_OR_MORE, argparse.PARSER):
        return LaunchArgumentValueKind.MULTI_VALUE, 1, None
    if isinstance(nargs, int):
        return LaunchArgumentValueKind.MULTI_VALUE, nargs, nargs
    return LaunchArgumentValueKind.MULTI_VALUE, 0, None


def _argument_metavar(
    parser: argparse.ArgumentParser,
    action: argparse.Action,
) -> str | None:
    """取得与 argparse 帮助声明一致的完整 metavar。"""
    if action.nargs == 0:
        return None
    formatter = parser._get_formatter()
    default = formatter._get_default_metavar_for_optional(action)
    formatted = formatter._format_args(action, default).strip()
    choices = _CHOICES.search(formatted)
    return choices.group(0) if choices else formatted


def _argument_help_text(
    parser: argparse.ArgumentParser,
    action: argparse.Action,
) -> str:
    """展开 argparse 帮助占位符并规范化空白。"""
    if action.help is None:
        return ""
    formatter = parser._get_formatter()
    return " ".join(formatter._expand_help(action).split())


def _argument_choices(action: argparse.Action) -> list[str]:
    """将 action choices 转换为稳定的字符串列表。"""
    if action.choices is None:
        return []
    return sorted({str(choice.value if isinstance(choice, Enum) else choice) for choice in action.choices})


def _argument_categories(parser: argparse.ArgumentParser) -> dict[int, str]:
    """建立 action 到规范化参数组标题的映射。"""
    categories: dict[int, str] = {}
    for group in parser._action_groups:
        category = _category(group.title or "other")
        for action in group._group_actions:
            categories[id(action)] = category
    return categories


def _argument_exclusive_groups(
    parser: argparse.ArgumentParser,
) -> dict[int, tuple[str, bool]]:
    """建立 action 到稳定互斥组标识的映射。"""
    result: dict[int, tuple[str, bool]] = {}
    for group in parser._mutually_exclusive_groups:
        actions = [action for action in group._group_actions if action.option_strings and action.help != argparse.SUPPRESS]
        if len(actions) < 2:
            continue
        flags = sorted({flag for action in actions for flag in action.option_strings})
        opening = "(" if group.required else "["
        stable_members = "\0".join(flags)
        group_name = "exclusive_" + hashlib.sha256(f"{opening}\0{stable_members}".encode()).hexdigest()[:16]
        for action in actions:
            result[id(action)] = (group_name, group.required)
    return result


def _argument_is_repeatable(action: argparse.Action, help_text: str) -> bool:
    """识别 append/count/extend action 及帮助文本声明的可重复参数。"""
    repeatable_actions = {
        "_AppendAction",
        "_AppendConstAction",
        "_CountAction",
        "_ExtendAction",
    }
    return type(action).__name__ in repeatable_actions or bool(re.search(r"repeat|multiple times|more than once", help_text, re.I))


def parse_argument_parser(
    parser: argparse.ArgumentParser,
) -> tuple[list[LaunchArgumentDefinition], list[LaunchArgumentDiagnostic]]:
    """直接解析实际的 ``ArgumentParser`` 对象。

    Args:
        parser (argparse.ArgumentParser): 已完成参数注册的解析器对象。

    Returns:
        tuple[list[LaunchArgumentDefinition], list[LaunchArgumentDiagnostic]]:
            规范化参数定义和解析诊断，数据模型与
            :func:`parse_argparse_help` 的返回值相同。
    """
    categories = _argument_categories(parser)
    exclusive_groups = _argument_exclusive_groups(parser)
    arguments: list[LaunchArgumentDefinition] = []

    for action in parser._actions:
        if not action.option_strings or action.help == argparse.SUPPRESS:
            continue
        flags = _normalized_flags(action.option_strings)
        value_kind, min_values, max_values = _argument_value_shape(action)
        help_text = _argument_help_text(parser, action)
        exclusive_group, exclusive_group_required = exclusive_groups.get(
            id(action),
            (None, False),
        )
        arguments.append(
            LaunchArgumentDefinition(
                name=_canonical_name(flags),
                flags=flags,
                value_kind=value_kind,
                min_values=min_values,
                max_values=max_values,
                help=help_text,
                category=categories.get(id(action), "other"),
                metavar=_argument_metavar(parser, action),
                choices=_argument_choices(action),
                required=bool(action.required and exclusive_group is None),
                repeatable=_argument_is_repeatable(action, help_text),
                exclusive_group=exclusive_group,
                exclusive_group_required=exclusive_group_required,
            )
        )

    diagnostics: list[LaunchArgumentDiagnostic] = []
    arguments, conflict_diagnostics = _coalesce_definitions(arguments)
    diagnostics.extend(conflict_diagnostics)
    if not arguments:
        diagnostics.append(
            LaunchArgumentDiagnostic(
                "error",
                "parse_empty",
                "ArgumentParser contained no recognizable options",
            )
        )
    return arguments, diagnostics


def _split_option_declaration(line: str) -> tuple[str, str] | None:
    """拆分 argparse 参数声明及同一行中的帮助文本。"""
    stripped = line.lstrip()
    if not stripped.startswith("-") or _FLAG.match(stripped) is None:
        return None
    match = re.search(r"\s{2,}", stripped)
    if match is None:
        spec, help_text = stripped.rstrip(), ""
    else:
        spec, help_text = stripped[: match.start()].rstrip(), stripped[match.end() :].strip()
    if "|" in spec:
        return None
    flags = list(_FLAG.finditer(spec))
    if not flags or spec[: flags[0].start()].strip():
        return None
    for previous, current in zip(flags, flags[1:]):
        if re.fullmatch(r"\s*,\s*", spec[previous.end() : current.start()]) is None:
            return None
    return spec, help_text


def _usage_block(lines: list[str]) -> tuple[str, set[int]]:
    indices: set[int] = set()
    usage_lines: list[str] = []
    for start, line in enumerate(lines):
        if not line.lstrip().startswith("usage:"):
            continue
        for index in range(start, len(lines)):
            current = lines[index]
            if index > start and (not current.strip() or _HEADING.match(current)):
                break
            indices.add(index)
            usage_lines.append(current.strip())
        break
    return " ".join(usage_lines), indices


def _semantic_key(argument: LaunchArgumentDefinition) -> tuple[object, ...]:
    return (
        argument.name,
        tuple(argument.flags),
        argument.value_kind,
        argument.min_values,
        argument.max_values,
        tuple(argument.choices),
        argument.required,
        argument.repeatable,
        argument.exclusive_group,
        argument.exclusive_group_required,
    )


def _coalesce_definitions(
    arguments: list[LaunchArgumentDefinition],
) -> tuple[list[LaunchArgumentDefinition], list[LaunchArgumentDiagnostic]]:
    normalized: list[LaunchArgumentDefinition] = []
    diagnostics: list[LaunchArgumentDiagnostic] = []
    by_name: dict[str, int] = {}
    by_flag: dict[str, int] = {}
    for argument in arguments:
        conflict_index = by_name.get(argument.name)
        if conflict_index is None:
            conflict_index = next((by_flag[flag] for flag in argument.flags if flag in by_flag), None)
        if conflict_index is None:
            index = len(normalized)
            normalized.append(argument)
            by_name[argument.name] = index
            for flag in argument.flags:
                by_flag[flag] = index
            continue
        existing = normalized[conflict_index]
        if _semantic_key(existing) != _semantic_key(argument):
            diagnostics.append(
                LaunchArgumentDiagnostic(
                    "error",
                    "parse_conflict",
                    f"Conflicting launch option definitions for {argument.name}",
                    ", ".join(sorted(set(existing.flags) | set(argument.flags))),
                )
            )
            continue
        merged_help = max((existing.help, argument.help), key=lambda value: (len(value), value))
        merged_category = min(existing.category, argument.category)
        merged_metavar = min(
            (value for value in (existing.metavar, argument.metavar) if value is not None),
            default=None,
        )
        normalized[conflict_index] = LaunchArgumentDefinition(
            name=existing.name,
            flags=existing.flags,
            value_kind=existing.value_kind,
            min_values=existing.min_values,
            max_values=existing.max_values,
            help=merged_help,
            category=merged_category,
            metavar=merged_metavar,
            choices=existing.choices,
            required=existing.required,
            repeatable=existing.repeatable,
            exclusive_group=existing.exclusive_group,
            exclusive_group_required=existing.exclusive_group_required,
        )
    normalized.sort(key=lambda argument: (argument.name, tuple(argument.flags)))
    return normalized, diagnostics


def _usage_metadata(usage: str) -> tuple[dict[str, tuple[str, bool]], set[str]]:
    """扫描嵌套用法分隔符，同时避免混淆可选元变量。"""
    stack: list[_UsageFrame] = []
    groups: list[tuple[str, list[str]]] = []
    required_flags: set[str] = set()
    index = 0
    while index < len(usage):
        character = usage[index]
        if character in "[(":
            stack.append({"opening": character, "flags": [], "has_pipe": False})
            index += 1
            continue
        if character in ")]":
            expected = "(" if character == ")" else "["
            if stack and stack[-1]["opening"] == expected:
                frame = stack.pop()
                flags = list(dict.fromkeys(frame["flags"]))
                if frame["has_pipe"] and len(flags) >= 2:
                    groups.append((str(frame["opening"]), flags))
            index += 1
            continue
        if character == "|":
            if stack:
                stack[-1]["has_pipe"] = True
            index += 1
            continue
        flag = _FLAG.match(usage, index)
        if flag is not None:
            value = flag.group(0)
            for frame in stack:
                frame["flags"].append(value)
            if not any(frame["opening"] == "[" for frame in stack):
                required_flags.add(value)
            index = flag.end()
            continue
        index += 1

    group_by_flag: dict[str, tuple[str, bool]] = {}
    for opening, flags in groups:
        stable_members = "\0".join(sorted(set(flags)))
        group_name = "exclusive_" + hashlib.sha256(f"{opening}\0{stable_members}".encode()).hexdigest()[:16]
        for flag in flags:
            group_by_flag[flag] = (group_name, opening == "(")
    return group_by_flag, required_flags


def parse_argparse_help(
    help_output: str,
) -> tuple[list[LaunchArgumentDefinition], list[LaunchArgumentDiagnostic]]:
    """解析 argparse 风格帮助格式共有的稳定子集。

    Args:
        help_output (str): argparse 风格的帮助文本。

    Returns:
        tuple[list[LaunchArgumentDefinition], list[LaunchArgumentDiagnostic]]:
            规范化参数定义和解析诊断。
    """
    lines = help_output.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    usage, usage_indices = _usage_block(lines)
    parsed: list[tuple[str, str, str]] = []
    diagnostics: list[LaunchArgumentDiagnostic] = []
    unrecognized_declarations = 0
    section_starts = [
        index
        for index, line in enumerate(lines)
        if index not in usage_indices and (heading := _HEADING.match(line)) and not heading.group("name").startswith("usage")
    ]
    for section_position, start in enumerate(section_starts):
        end = section_starts[section_position + 1] if section_position + 1 < len(section_starts) else len(lines)
        heading = _HEADING.match(lines[start])
        assert heading is not None
        category = _category(heading.group("name"))
        candidates = [
            (index, len(lines[index]) - len(lines[index].lstrip()))
            for index in range(start + 1, end)
            if index not in usage_indices and _split_option_declaration(lines[index]) is not None
        ]
        if not candidates:
            unrecognized_declarations += sum(
                1
                for index in range(start + 1, end)
                if index not in usage_indices and lines[index].lstrip().startswith("-")
            )
            continue
        declaration_indent = min(indent for _, indent in candidates)
        current: int | None = None
        for index in range(start + 1, end):
            if index in usage_indices:
                current = None
                continue
            line = lines[index]
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if not stripped:
                current = None
                continue
            if indent == declaration_indent:
                declaration = _split_option_declaration(line)
                if declaration is None:
                    if stripped.startswith("-"):
                        unrecognized_declarations += 1
                    current = None
                    continue
                spec, help_text = declaration
                parsed.append((spec, help_text, category))
                current = len(parsed) - 1
                continue
            if indent > declaration_indent and current is not None:
                item = parsed[current]
                parsed[current] = (
                    item[0],
                    " ".join((item[1], stripped)).strip(),
                    item[2],
                )
            elif indent <= declaration_indent:
                current = None

    group_by_flag, required_flags = _usage_metadata(usage)

    arguments: list[LaunchArgumentDefinition] = []
    for spec, help_text, item_category in parsed:
        flags = _normalized_flags(_FLAG.findall(spec))
        kind, min_values, max_values, metavar, choices, repeatable = _value_shape(spec, help_text)
        group = next((group_by_flag[flag] for flag in flags if flag in group_by_flag), (None, False))
        required = any(flag in required_flags for flag in flags) and group[0] is None
        arguments.append(
            LaunchArgumentDefinition(
                name=_canonical_name(flags),
                flags=flags,
                value_kind=kind,
                min_values=min_values,
                max_values=max_values,
                help=help_text,
                category=item_category or "other",
                metavar=metavar,
                choices=choices,
                required=required,
                repeatable=repeatable,
                exclusive_group=group[0],
                exclusive_group_required=group[1],
            )
        )
    if not arguments:
        diagnostics.append(LaunchArgumentDiagnostic("error", "parse_empty", "WebUI help output contained no recognizable options", help_output[-MAX_DIAGNOSTIC_OUTPUT:] or None))
    elif not usage:
        diagnostics.append(LaunchArgumentDiagnostic("warning", "usage_missing", "Options were parsed, but the help output did not expose a usage line"))
    if unrecognized_declarations:
        diagnostics.append(
            LaunchArgumentDiagnostic(
                "warning",
                "parse_partial",
                f"Skipped {unrecognized_declarations} unrecognized option declaration(s)",
            )
        )
    arguments, conflict_diagnostics = _coalesce_definitions(arguments)
    diagnostics.extend(conflict_diagnostics)
    return arguments, diagnostics


def _has_option_section(document: str) -> bool:
    lines = document.split("\n")
    return any(
        _HEADING.match(line)
        and any(
            _split_option_declaration(candidate) is not None
            for candidate in lines[index + 1 :]
        )
        for index, line in enumerate(lines)
    )


def _select_help_document(
    stdout: str,
    stderr: str,
) -> tuple[list[LaunchArgumentDefinition], list[LaunchArgumentDiagnostic]]:
    documents = [("stdout", stdout), ("stderr", stderr)]
    parsed = []
    for name, document in documents:
        arguments, diagnostics = parse_argparse_help(document)
        viable = bool(arguments) and "usage:" in document and _has_option_section(document)
        parsed.append((name, document, arguments, diagnostics, viable))

    viable = [item for item in parsed if item[4]]
    if len(viable) == 2:
        stdout_result, stderr_result = viable
        stdout_contract = tuple(_semantic_key(argument) for argument in stdout_result[2])
        stderr_contract = tuple(_semantic_key(argument) for argument in stderr_result[2])
        if stdout_contract != stderr_contract:
            diagnostics = list(stdout_result[3])
            diagnostics.append(
                LaunchArgumentDiagnostic(
                    "error",
                    "discovery_conflict",
                    "stdout and stderr exposed conflicting launch-argument contracts",
                )
            )
            return stdout_result[2], diagnostics
        return stdout_result[2], stdout_result[3]
    if len(viable) == 1:
        selected = viable[0]
        diagnostics = list(selected[3])
        other = parsed[1] if selected[0] == "stdout" else parsed[0]
        if other[1]:
            diagnostics.append(
                LaunchArgumentDiagnostic(
                    "warning",
                    "discovery_other_stream",
                    f"Ignored non-help process output from {other[0]}",
                    other[1][-MAX_DIAGNOSTIC_OUTPUT:],
                )
            )
        return selected[2], diagnostics

    selected = max(
        parsed,
        key=lambda item: (
            bool(item[2]),
            "usage:" in item[1],
            len(item[2]),
            item[0] == "stdout",
        ),
    )
    diagnostics = list(selected[3])
    if not any(diagnostic.severity == "error" for diagnostic in diagnostics):
        diagnostics.append(
            LaunchArgumentDiagnostic(
                "error",
                "parse_empty",
                "Neither stdout nor stderr contained a viable argparse help document",
            )
        )
    return selected[2], diagnostics


class ScriptHelpProvider:
    """通过 WebUI 启动脚本的帮助输出发现参数。"""

    def __init__(self, scripts: tuple[str, ...]) -> None:
        self.scripts = scripts

    def provider_identity(self) -> str:
        """返回脚本提供器的稳定标识。

        Returns:
            str: 包含脚本列表的稳定标识。
        """
        return json.dumps(
            {
                "provider": type(self).__name__,
                "scripts": list(self.scripts),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def help_command(self, context: LaunchArgumentDiscoveryContext) -> HelpCommand | None:
        """构建用于提取脚本帮助文本的命令。

        Args:
            context (LaunchArgumentDiscoveryContext): 参数发现上下文。

        Returns:
            HelpCommand | None: 帮助命令；未找到脚本时返回 ``None``。
        """
        script = next((context.webui_path / item for item in self.scripts if (context.webui_path / item).is_file()), None)
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

    def get_catalog(self, context: LaunchArgumentDiscoveryContext) -> LaunchArgumentCatalog:
        """发现并规范化脚本支持的启动参数。

        Args:
            context (LaunchArgumentDiscoveryContext): 参数发现上下文。

        Returns:
            LaunchArgumentCatalog: 启动参数目录及诊断。
        """
        command = self.help_command(context)
        if command is None:
            source_identity = "missing:" + "|".join(self.scripts)
            revision = _contract_revision(
                context.webui_type,
                self.provider_identity(),
                source_identity,
                [],
            )
            return LaunchArgumentCatalog(
                CATALOG_SCHEMA_VERSION,
                context.webui_type,
                revision,
                diagnostics=[LaunchArgumentDiagnostic("error", "discovery_unavailable", "No supported WebUI launch script exists in the installed core")],
            )
        stdout, stderr, failure = _run_help(command, context)
        if failure is not None:
            return LaunchArgumentCatalog(
                CATALOG_SCHEMA_VERSION,
                context.webui_type,
                _contract_revision(
                    context.webui_type,
                    self.provider_identity(),
                    command.source_identity,
                    [],
                ),
                diagnostics=[failure],
            )
        arguments, diagnostics = _select_help_document(stdout, stderr)
        return LaunchArgumentCatalog(
            CATALOG_SCHEMA_VERSION,
            context.webui_type,
            _contract_revision(
                context.webui_type,
                self.provider_identity(),
                command.source_identity,
                arguments,
            ),
            arguments,
            diagnostics,
        )


class InvokeAiHelpProvider(ScriptHelpProvider):
    """通过 InvokeAI 内部参数解析器发现启动参数。"""

    def __init__(self) -> None:
        super().__init__(())

    def help_command(self, context: LaunchArgumentDiscoveryContext) -> HelpCommand:
        """构建 InvokeAI 参数解析器帮助命令。

        Args:
            context (LaunchArgumentDiscoveryContext): 参数发现上下文。

        Returns:
            HelpCommand: InvokeAI 参数解析器帮助命令。
        """
        try:
            version = importlib.metadata.version("invokeai")
        except importlib.metadata.PackageNotFoundError:
            version = "unavailable"
        source = f"invokeai.frontend.cli.arg_parser:_parser:{version}"
        code = "from invokeai.frontend.cli.arg_parser import _parser; _parser.print_help()"
        env = os.environ.copy()
        env["INVOKEAI_ROOT"] = str(context.webui_path)
        return HelpCommand([str(context.python_executable), "-c", code], source, env)


PROVIDERS: dict[str, LaunchArgumentProvider] = {
    "sd_webui": ScriptHelpProvider(("launch.py",)),
    "comfyui": ScriptHelpProvider(("main.py",)),
    "fooocus": ScriptHelpProvider(("launch.py",)),
    "invokeai": InvokeAiHelpProvider(),
    "sd_trainer": ScriptHelpProvider(("gui.py", "kohya_gui.py")),
    "qwen_tts_webui": ScriptHelpProvider(("launch.py",)),
}


def _contract_revision(
    webui_type: str,
    provider_identity: str,
    source_identity: str,
    arguments: list[LaunchArgumentDefinition],
) -> str:
    canonical_arguments = [
        {
            "name": argument.name,
            "flags": sorted(argument.flags),
            "value_kind": argument.value_kind.value,
            "min_values": argument.min_values,
            "max_values": argument.max_values,
            "metavar": argument.metavar,
            "choices": sorted(argument.choices),
            "category": argument.category,
            "required": argument.required,
            "repeatable": argument.repeatable,
            "exclusive_group": argument.exclusive_group,
            "exclusive_group_required": argument.exclusive_group_required,
        }
        for argument in sorted(arguments, key=lambda item: (item.name, tuple(sorted(item.flags))))
    ]
    payload = json.dumps(
        {
            "schema_version": CATALOG_SCHEMA_VERSION,
            "webui_type": webui_type.strip().lower(),
            "provider_identity": provider_identity,
            "source_identity": source_identity,
            "arguments": canonical_arguments,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def get_launch_argument_catalog(
    webui_type: str,
    webui_path: str | Path,
    *,
    python_executable: str | Path | None = None,
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
) -> LaunchArgumentCatalog:
    """在不持久化用户数据的情况下发现当前安装实例的参数目录。

    Args:
        webui_type (str): WebUI 类型。
        webui_path (str | Path): WebUI 安装路径。
        python_executable (str | Path | None): 用于执行帮助命令的 Python。
        timeout_seconds (float): 帮助命令超时秒数。

    Returns:
        LaunchArgumentCatalog: 当前安装实例的启动参数目录。

    Raises:
        ValueError: WebUI 类型不受支持时抛出。
    """
    provider = PROVIDERS.get(webui_type)
    if provider is None:
        raise ValueError(f"Unsupported webui_type: {webui_type}")
    path = Path(webui_path)
    context = LaunchArgumentDiscoveryContext(
        webui_type=webui_type,
        webui_path=path,
        python_executable=Path(python_executable or sys.executable),
        timeout_seconds=max(0.1, min(float(timeout_seconds), 30.0)),
    )
    return provider.get_catalog(context)


__all__ = [
    "CATALOG_SCHEMA_VERSION",
    "LaunchArgumentCatalog",
    "LaunchArgumentDefinition",
    "LaunchArgumentDiagnostic",
    "LaunchArgumentDiscoveryContext",
    "LaunchArgumentProvider",
    "LaunchArgumentValueKind",
    "PROVIDERS",
    "cancel_launch_argument_discovery",
    "get_launch_argument_catalog",
    "parse_argparse_help",
    "parse_argument_parser",
]
