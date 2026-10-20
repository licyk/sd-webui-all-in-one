"""启动参数目录构建与目录版本计算"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence

from sd_webui_all_in_one.base_manager.launch_arguments.models import (
    CATALOG_SCHEMA_VERSION,
    LaunchArgumentDiagnostic,
    LaunchArgumentDefinition,
    LaunchArgumentCatalog,
)
from sd_webui_all_in_one.base_manager.launch_arguments.parser_object import parse_argument_parser


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


def build_launch_argument_catalog(
    webui_type: str,
    arguments: Sequence[LaunchArgumentDefinition],
    diagnostics: Sequence[LaunchArgumentDiagnostic] = (),
    *,
    provider_identity: str,
    source_identity: str,
) -> LaunchArgumentCatalog:
    """由任意参数发现实现构建统一的启动参数目录。

    Args:
        webui_type (str): WebUI 类型。
        arguments (Sequence[LaunchArgumentDefinition]): 规范化参数定义。
        diagnostics (Sequence[LaunchArgumentDiagnostic]): 参数发现诊断。
        provider_identity (str): 调用方提供的稳定解析器标识。
        source_identity (str): 被解析参数源的稳定标识。

    Returns:
        LaunchArgumentCatalog: 包含稳定修订值的启动参数目录。
    """
    normalized_arguments = list(arguments)
    return LaunchArgumentCatalog(
        schema_version=CATALOG_SCHEMA_VERSION,
        webui_type=webui_type,
        catalog_revision=_contract_revision(
            webui_type,
            provider_identity,
            source_identity,
            normalized_arguments,
        ),
        arguments=normalized_arguments,
        diagnostics=list(diagnostics),
    )


def build_launch_argument_catalog_from_parser(
    webui_type: str,
    parser: argparse.ArgumentParser,
    *,
    provider_identity: str,
    source_identity: str,
) -> LaunchArgumentCatalog:
    """解析实际 ``ArgumentParser`` 对象并构建统一目录。

    Args:
        webui_type (str): WebUI 类型。
        parser (argparse.ArgumentParser): 已完成参数注册的解析器对象。
        provider_identity (str): 调用方提供的稳定解析器标识。
        source_identity (str): 被解析参数源的稳定标识。

    Returns:
        LaunchArgumentCatalog: 规范化的启动参数目录。
    """
    arguments, diagnostics = parse_argument_parser(parser)
    return build_launch_argument_catalog(
        webui_type,
        arguments,
        diagnostics,
        provider_identity=provider_identity,
        source_identity=source_identity,
    )
