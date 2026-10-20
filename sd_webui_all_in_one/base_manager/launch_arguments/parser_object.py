"""从 argparse.ArgumentParser 对象解析启动参数"""

from __future__ import annotations

import argparse
import hashlib
import re
from enum import Enum

from sd_webui_all_in_one.base_manager.launch_arguments.models import (
    LaunchArgumentValueKind,
    LaunchArgumentDiagnostic,
    LaunchArgumentDefinition,
)
from sd_webui_all_in_one.base_manager.launch_arguments.common import (
    _CHOICES,
    _category,
    _canonical_name,
    _normalized_flags,
    _coalesce_definitions,
)


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
