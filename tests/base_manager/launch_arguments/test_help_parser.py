"""启动参数帮助文本解析测试"""

from __future__ import annotations

import pytest

import sd_webui_all_in_one.base_manager.launch_arguments.help_parser as help_parser_module
from sd_webui_all_in_one.base_manager.launch_arguments import (
    LaunchArgumentValueKind,
    parse_argparse_help,
)
from tests.base_manager.launch_arguments.helpers import HELP_LF

COMFYUI_HELP = """usage: main.py [-h] [--listen [IP]] [--port PORT]
               [--extra-model-paths-config PATH [PATH ...]]
               [--cache-classic | --cache-lru CACHE_LRU | --cache-ram [GB ...]]
               [--highvram | --normalvram | --lowvram | --novram | --cpu]

options:
  -h, --help            show this help message and exit
  --listen [IP]
                        Specify the IP address to listen on (default: 127.0.0.1).
  --port PORT           Set the listen port.
  --extra-model-paths-config PATH [PATH ...]
                        Load one or more extra_model_paths.yaml files.
                        This declaration is intentionally long and wrapped.
  --cache-classic       Use the classic caching system.
  --cache-lru CACHE_LRU
                        Use LRU caching with a maximum of N results.
  --cache-ram [GB ...]
                        Keep models in memory until the RAM threshold is reached.
  --highvram            Keep models in GPU memory.
  --normalvram          Use the normal VRAM strategy.
  --lowvram             Split models to use less VRAM.
  --novram              Minimize VRAM use.
  --cpu                 Use CPU for everything.
"""


LIVE_COMFYUI_HELP = """usage: main.py [-h] [--listen [IP]]
               [--cache-classic |
                --cache-lru CACHE_LRU |
                --cache-none |
                --cache-ram [GB ...]]
               [--high-ram]

options:
  -h, --help            show this help message and exit
  --listen [IP]
                        Specify the IP address to listen on.
  --disable-all-custom-nodes
                        Disable custom nodes when
                        --disable-all-custom-nodes is enabled.
  --enable-manager
                        Enable the manager when using
                        --enable-manager.

Performance options:
  --cache-classic       Use classic caching.
  --cache-lru CACHE_LRU
                        Cache at most N results.
  --cache-none          Disable caching.
  --cache-ram [GB ...]
                        Keep models cached in RAM.
  --high-ram            Prefer RAM for model caching.
                        Current valid optimizations:
                        fp16_accumulation and scaled_mm.
"""


@pytest.mark.parametrize("line_ending", ["\n", "\r\n"])
def test_argparse_parser_normalizes_value_kinds_choices_groups_and_categories(line_ending: str) -> None:
    arguments, diagnostics = parse_argparse_help(HELP_LF.replace("\n", line_ending))
    by_name = {argument.name: argument for argument in arguments}
    assert not diagnostics
    assert by_name["help"].value_kind is LaunchArgumentValueKind.BOOLEAN
    assert by_name["listen"].value_kind is LaunchArgumentValueKind.OPTIONAL_VALUE
    assert (by_name["listen"].min_values, by_name["listen"].max_values) == (0, 1)
    assert by_name["port"].value_kind is LaunchArgumentValueKind.VALUE
    assert (by_name["port"].min_values, by_name["port"].max_values) == (1, 1)
    assert by_name["mode"].choices == ["auto", "fast"]
    assert by_name["tag"].value_kind is LaunchArgumentValueKind.MULTI_VALUE
    assert (by_name["tag"].min_values, by_name["tag"].max_values) == (1, None)
    assert by_name["tag"].repeatable
    assert by_name["cpu"].exclusive_group == by_name["cuda"].exclusive_group
    assert by_name["cpu"].exclusive_group_required
    assert by_name["port"].category == "network_options"


def test_help_aliases_are_exposed_as_normal_arguments() -> None:
    arguments, _ = parse_argparse_help(HELP_LF)
    help_argument = next(argument for argument in arguments if argument.name == "help")
    assert help_argument.flags == ["-h", "--help"]


@pytest.mark.parametrize("line_ending", ["\n", "\r\n"])
def test_realistic_comfyui_wrapped_help_and_nested_exclusive_groups(line_ending: str) -> None:
    arguments, diagnostics = parse_argparse_help(COMFYUI_HELP.replace("\n", line_ending))
    assert diagnostics == []
    by_name = {argument.name: argument for argument in arguments}
    assert by_name["listen"].value_kind is LaunchArgumentValueKind.OPTIONAL_VALUE
    assert by_name["listen"].help.startswith("Specify the IP address")
    assert by_name["extra_model_paths_config"].value_kind is LaunchArgumentValueKind.MULTI_VALUE
    assert (by_name["extra_model_paths_config"].min_values, by_name["extra_model_paths_config"].max_values) == (1, None)
    assert by_name["extra_model_paths_config"].metavar == "PATH [PATH ...]"
    assert "intentionally long and wrapped" in by_name["extra_model_paths_config"].help
    assert by_name["cache_lru"].value_kind is LaunchArgumentValueKind.VALUE
    assert by_name["cache_ram"].value_kind is LaunchArgumentValueKind.MULTI_VALUE
    assert (by_name["cache_ram"].min_values, by_name["cache_ram"].max_values) == (0, None)
    assert by_name["cache_ram"].metavar == "[GB ...]"
    assert by_name["cache_classic"].exclusive_group == by_name["cache_lru"].exclusive_group
    assert by_name["cache_lru"].exclusive_group == by_name["cache_ram"].exclusive_group
    assert by_name["cache_ram"].exclusive_group_required is False
    assert by_name["highvram"].exclusive_group == by_name["cpu"].exclusive_group
    assert by_name["highvram"].exclusive_group != by_name["cache_ram"].exclusive_group


def test_required_nested_exclusive_group_uses_outer_delimiter() -> None:
    help_text = """usage: demo (--backend-a | --backend-b [MODE ...])

options:
  --backend-a
                        Use backend A.
  --backend-b [MODE ...]
                        Use backend B with optional modes.
"""
    arguments, diagnostics = parse_argparse_help(help_text)
    assert diagnostics == []
    by_name = {argument.name: argument for argument in arguments}
    assert by_name["backend_a"].exclusive_group == by_name["backend_b"].exclusive_group
    assert by_name["backend_a"].exclusive_group_required is True
    assert by_name["backend_b"].value_kind is LaunchArgumentValueKind.MULTI_VALUE
    assert (by_name["backend_b"].min_values, by_name["backend_b"].max_values) == (0, None)


def test_live_comfyui_shape_never_parses_usage_or_help_prose_as_declarations() -> None:
    arguments, diagnostics = parse_argparse_help(LIVE_COMFYUI_HELP)
    assert not [diagnostic for diagnostic in diagnostics if diagnostic.severity == "error"]
    names = [argument.name for argument in arguments]
    flags = [flag for argument in arguments for flag in argument.flags]
    assert len(names) == len(set(names))
    assert len(flags) == len(set(flags))
    for name in ["cache_classic", "disable_all_custom_nodes", "enable_manager", "high_ram"]:
        assert names.count(name) == 1
    by_name = {argument.name: argument for argument in arguments}
    cache_group = by_name["cache_classic"].exclusive_group
    assert cache_group
    assert {
        by_name["cache_lru"].exclusive_group,
        by_name["cache_none"].exclusive_group,
        by_name["cache_ram"].exclusive_group,
    } == {cache_group}
    assert by_name["cache_ram"].value_kind is LaunchArgumentValueKind.MULTI_VALUE
    assert (by_name["cache_ram"].min_values, by_name["cache_ram"].max_values) == (0, None)
    assert "--disable-all-custom-nodes is enabled." in by_name["disable_all_custom_nodes"].help
    assert "--enable-manager." in by_name["enable_manager"].help
    assert "Current valid optimizations:" in by_name["high_ram"].help
    assert {argument.category for argument in arguments} == {"general", "performance_options"}
    assert not {"|", ".", "]", "is enabled."} & {argument.metavar for argument in arguments if argument.metavar}


def test_duplicate_semantic_conflicts_are_blocking_diagnostics() -> None:
    help_text = """usage: demo [--port PORT]

options:
  --port PORT           scalar port
  --port [PORT]         conflicting optional port
"""
    arguments, diagnostics = parse_argparse_help(help_text)
    assert len(arguments) == 1
    assert any(diagnostic.severity == "error" and diagnostic.code == "parse_conflict" for diagnostic in diagnostics)


def test_help_document_selection_is_stream_aware_and_conflict_safe() -> None:
    arguments, diagnostics = help_parser_module._select_help_document(
        LIVE_COMFYUI_HELP,
        "warning: optional import failed",
    )
    assert arguments
    assert any(diagnostic.code == "discovery_other_stream" for diagnostic in diagnostics)

    equivalent, diagnostics = help_parser_module._select_help_document(
        LIVE_COMFYUI_HELP,
        LIVE_COMFYUI_HELP,
    )
    assert equivalent == arguments
    assert not any(diagnostic.code == "discovery_conflict" for diagnostic in diagnostics)

    conflicting = LIVE_COMFYUI_HELP.replace("--listen [IP]", "--listen IP")
    _, diagnostics = help_parser_module._select_help_document(
        LIVE_COMFYUI_HELP,
        conflicting,
    )
    assert any(diagnostic.severity == "error" and diagnostic.code == "discovery_conflict" for diagnostic in diagnostics)

    stderr_only, _ = help_parser_module._select_help_document(
        "ordinary stdout noise",
        LIVE_COMFYUI_HELP,
    )
    assert stderr_only == arguments


def test_variadic_choice_arity_distinguishes_zero_or_more_from_one_or_more() -> None:
    help_text = """usage: demo [--optional-colors [{red,green,blue} ...]]
            [--required-colors {red,green,blue} [{red,green,blue} ...]]

options:
  --optional-colors [{red,green,blue} ...]
                        Optional color filters.
  --required-colors {red,green,blue} [{red,green,blue} ...]
                        One or more required color filters.
"""
    arguments, diagnostics = parse_argparse_help(help_text)
    assert diagnostics == []
    by_name = {argument.name: argument for argument in arguments}
    assert by_name["optional_colors"].choices == ["blue", "green", "red"]
    assert (by_name["optional_colors"].min_values, by_name["optional_colors"].max_values) == (0, None)
    assert (by_name["required_colors"].min_values, by_name["required_colors"].max_values) == (1, None)


def test_unrecognized_declaration_never_corrupts_previous_help() -> None:
    help_text = """usage: demo [--first VALUE]

options:
  --first VALUE
                        First help line.
  ---not-an-option ???
                        Must not attach to first.
  --second VALUE
                        Second help line.
"""
    arguments, diagnostics = parse_argparse_help(help_text)
    by_name = {argument.name: argument for argument in arguments}
    assert by_name["first"].help == "First help line."
    assert by_name["second"].help == "Second help line."
    assert diagnostics[0].code == "parse_partial"


def test_section_with_only_malformed_declarations_reports_partial_parse() -> None:
    arguments, diagnostics = parse_argparse_help("usage: demo\n\noptions:\n  ---not-an-option ???\n")
    assert arguments == []
    assert {diagnostic.code for diagnostic in diagnostics} == {"parse_empty", "parse_partial"}


def test_missing_usage_and_malformed_help_return_typed_diagnostics() -> None:
    partial, diagnostics = parse_argparse_help("options:\n  --foo VALUE  partial")
    assert partial[0].category == "general"
    assert diagnostics[0].code == "usage_missing"
    empty, diagnostics = parse_argparse_help("not argparse output")
    assert empty == []
    assert diagnostics[0].severity == "error"
    assert diagnostics[0].code == "parse_empty"
