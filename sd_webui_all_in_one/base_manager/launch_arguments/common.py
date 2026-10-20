"""启动参数解析器共用的正则与定义合并工具"""

from __future__ import annotations

import re
from collections.abc import Sequence

from sd_webui_all_in_one.base_manager.launch_arguments.models import (
    LaunchArgumentDiagnostic,
    LaunchArgumentDefinition,
)


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
