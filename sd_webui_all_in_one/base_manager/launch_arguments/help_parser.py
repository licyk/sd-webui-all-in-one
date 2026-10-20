"""从 argparse 帮助文本解析启动参数"""

from __future__ import annotations

import hashlib
import re
from typing import TypedDict

from sd_webui_all_in_one.base_manager.launch_arguments.models import (
    MAX_DIAGNOSTIC_OUTPUT,
    LaunchArgumentValueKind,
    LaunchArgumentDiagnostic,
    LaunchArgumentDefinition,
)
from sd_webui_all_in_one.base_manager.launch_arguments.common import (
    _HEADING,
    _FLAG,
    _CHOICES,
    _category,
    _canonical_name,
    _normalized_flags,
    _semantic_key,
    _coalesce_definitions,
)


class _UsageFrame(TypedDict):
    opening: str
    flags: list[str]
    has_pipe: bool


def _value_shape(
    spec: str,
    help_text: str,
) -> tuple[LaunchArgumentValueKind, int, int | None, str | None, list[str], bool]:
    flags = list(_FLAG.finditer(spec))
    tail = spec[flags[-1].end() :].strip(" ,") if flags else ""
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
    section_starts = [index for index, line in enumerate(lines) if index not in usage_indices and (heading := _HEADING.match(line)) and not heading.group("name").startswith("usage")]
    for section_position, start in enumerate(section_starts):
        end = section_starts[section_position + 1] if section_position + 1 < len(section_starts) else len(lines)
        heading = _HEADING.match(lines[start])
        assert heading is not None
        category = _category(heading.group("name"))
        candidates = [(index, len(lines[index]) - len(lines[index].lstrip())) for index in range(start + 1, end) if index not in usage_indices and _split_option_declaration(lines[index]) is not None]
        if not candidates:
            unrecognized_declarations += sum(1 for index in range(start + 1, end) if index not in usage_indices and lines[index].lstrip().startswith("-"))
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
    return any(_HEADING.match(line) and any(_split_option_declaration(candidate) is not None for candidate in lines[index + 1 :]) for index, line in enumerate(lines))


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
