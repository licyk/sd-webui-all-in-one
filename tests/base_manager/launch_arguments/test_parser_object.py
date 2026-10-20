"""启动参数 ArgumentParser 对象解析测试"""

from __future__ import annotations

import argparse

from sd_webui_all_in_one.base_manager.launch_arguments import (
    LaunchArgumentDiagnostic,
    LaunchArgumentValueKind,
    parse_argument_parser,
)


def test_argument_parser_object_normalizes_actions_groups_and_categories() -> None:
    parser = argparse.ArgumentParser(prog="demo")
    network = parser.add_argument_group("Network options")
    network.add_argument("-l", "--listen", nargs="?", metavar="IP")
    network.add_argument(
        "--tag",
        nargs="+",
        action="append",
        choices=("fast", "safe"),
        help="Select one or more tags.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8188,
        required=True,
        help="Server port (default: %(default)s).",
    )
    backends = parser.add_mutually_exclusive_group(required=True)
    backends.add_argument("--cpu", action="store_true")
    backends.add_argument("--cuda", action="store_true")
    parser.add_argument("--hidden", help=argparse.SUPPRESS)
    parser.add_argument("input")

    arguments, diagnostics = parse_argument_parser(parser)

    assert diagnostics == []
    by_name = {argument.name: argument for argument in arguments}
    assert "hidden" not in by_name
    assert "input" not in by_name
    assert by_name["help"].flags == ["-h", "--help"]
    assert by_name["listen"].category == "network_options"
    assert by_name["listen"].value_kind is LaunchArgumentValueKind.OPTIONAL_VALUE
    assert (by_name["listen"].min_values, by_name["listen"].max_values) == (0, 1)
    assert by_name["listen"].metavar == "[IP]"
    assert by_name["tag"].value_kind is LaunchArgumentValueKind.MULTI_VALUE
    assert (by_name["tag"].min_values, by_name["tag"].max_values) == (1, None)
    assert by_name["tag"].choices == ["fast", "safe"]
    assert by_name["tag"].repeatable
    assert by_name["port"].required
    assert by_name["port"].help == "Server port (default: 8188)."
    assert by_name["cpu"].exclusive_group == by_name["cuda"].exclusive_group
    assert by_name["cpu"].exclusive_group_required


def test_argument_parser_object_reports_empty_parser() -> None:
    arguments, diagnostics = parse_argument_parser(argparse.ArgumentParser(add_help=False))

    assert arguments == []
    assert diagnostics == [
        LaunchArgumentDiagnostic(
            "error",
            "parse_empty",
            "ArgumentParser contained no recognizable options",
        )
    ]


def test_argument_parser_object_reports_normalized_name_conflicts() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--foo-bar")
    parser.add_argument("--foo_bar", nargs="?")

    arguments, diagnostics = parse_argument_parser(parser)

    assert len(arguments) == 1
    assert diagnostics[0].severity == "error"
    assert diagnostics[0].code == "parse_conflict"
