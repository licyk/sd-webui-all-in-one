from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from types import SimpleNamespace
from pathlib import Path

import pytest

import sd_webui_all_in_one.launch_arguments as launch_arguments_module
from sd_webui_all_in_one.api_server import registry
from sd_webui_all_in_one.base_manager import comfyui_base, fooocus_base, invokeai_base, qwen_tts_webui_base, sd_trainer_base, sd_webui_base
from sd_webui_all_in_one.launch_arguments import (
    CATALOG_SCHEMA_VERSION,
    LaunchArgumentValueKind,
    build_script_help_command,
    cancel_launch_argument_discovery,
    discover_launch_argument_catalog,
    parse_argparse_help,
    parse_argument_parser,
)


HELP_LF = """usage: demo [-h] [--listen [IP]] [--port PORT]
            [--mode {auto,fast}] [--tag TAG [TAG ...]] (--cpu | --cuda)

Network options:
  -h, --help            show this help message and exit
  --listen [IP]         bind address
  --port PORT           server port
  --mode {auto,fast}    preview mode
  --tag TAG [TAG ...]   tags; may be specified multiple times
  --cpu                 use CPU
  --cuda                use CUDA
"""


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


def _write_comfyui_argument_parser(path: Path) -> None:
    package = path / "comfy"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "cli_args.py").write_text(
        """import argparse
parser = argparse.ArgumentParser()
network = parser.add_argument_group("Network options")
network.add_argument("--listen", nargs="?", metavar="IP")
network.add_argument("--port", type=int, default=8188)
cache = parser.add_mutually_exclusive_group()
cache.add_argument("--cache-classic", action="store_true")
cache.add_argument("--cache-lru", type=int)
""",
        encoding="utf-8",
    )


def _get_script_catalog(
    webui_type: str,
    path: Path,
    *,
    timeout_seconds: float = 15.0,
):
    return discover_launch_argument_catalog(
        webui_type,
        path,
        provider_identity="test:script-help",
        help_command_factory=lambda context: build_script_help_command(context, ("launch.py",)),
        use_parser_object=False,
        python_executable=sys.executable,
        timeout_seconds=timeout_seconds,
    )


def test_catalog_models_serialize_stable_snake_case_shape(tmp_path: Path) -> None:
    script = tmp_path / "launch.py"
    script.write_text("print('''" + HELP_LF + "''')", encoding="utf-8")
    catalog = _get_script_catalog("demo", tmp_path)
    payload = catalog.to_dict()
    assert payload["schema_version"] == CATALOG_SCHEMA_VERSION
    assert payload["webui_type"] == "demo"
    assert len(payload["catalog_revision"]) == 64
    assert payload["arguments"][0]["value_kind"] == "boolean"
    assert payload["arguments"][0]["min_values"] == 0
    assert payload["arguments"][0]["max_values"] == 0
    assert "hidden" not in payload["arguments"][0]
    assert "catalogRevision" not in payload
    json.dumps(payload)


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
        launch_arguments_module.LaunchArgumentDiagnostic(
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
    assert not {"|", ".", "]", "is enabled."} & {
        argument.metavar for argument in arguments if argument.metavar
    }


def test_duplicate_semantic_conflicts_are_blocking_diagnostics() -> None:
    help_text = """usage: demo [--port PORT]

options:
  --port PORT           scalar port
  --port [PORT]         conflicting optional port
"""
    arguments, diagnostics = parse_argparse_help(help_text)
    assert len(arguments) == 1
    assert any(
        diagnostic.severity == "error" and diagnostic.code == "parse_conflict"
        for diagnostic in diagnostics
    )


def test_help_document_selection_is_stream_aware_and_conflict_safe() -> None:
    arguments, diagnostics = launch_arguments_module._select_help_document(
        LIVE_COMFYUI_HELP,
        "warning: optional import failed",
    )
    assert arguments
    assert any(diagnostic.code == "discovery_other_stream" for diagnostic in diagnostics)

    equivalent, diagnostics = launch_arguments_module._select_help_document(
        LIVE_COMFYUI_HELP,
        LIVE_COMFYUI_HELP,
    )
    assert equivalent == arguments
    assert not any(diagnostic.code == "discovery_conflict" for diagnostic in diagnostics)

    conflicting = LIVE_COMFYUI_HELP.replace("--listen [IP]", "--listen IP")
    _, diagnostics = launch_arguments_module._select_help_document(
        LIVE_COMFYUI_HELP,
        conflicting,
    )
    assert any(
        diagnostic.severity == "error" and diagnostic.code == "discovery_conflict"
        for diagnostic in diagnostics
    )

    stderr_only, _ = launch_arguments_module._select_help_document(
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
    arguments, diagnostics = parse_argparse_help(
        "usage: demo\n\noptions:\n  ---not-an-option ???\n"
    )
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


def test_discovery_timeout_terminates_child_and_never_returns_empty_success(tmp_path: Path) -> None:
    marker = tmp_path / "completed"
    (tmp_path / "launch.py").write_text(
        "import time, pathlib\ntime.sleep(5)\npathlib.Path(r'%s').write_text('bad')\n" % marker,
        encoding="utf-8",
    )
    started = time.monotonic()
    catalog = _get_script_catalog("demo", tmp_path, timeout_seconds=0.1)
    assert time.monotonic() - started < 3
    assert catalog.arguments == []
    assert catalog.diagnostics[0].code == "discovery_timeout"
    time.sleep(0.1)
    assert not marker.exists()


def test_discovery_shutdown_cancellation_terminates_child(tmp_path: Path) -> None:
    marker = tmp_path / "completed"
    (tmp_path / "launch.py").write_text(
        "import time, pathlib\ntime.sleep(5)\npathlib.Path(r'%s').write_text('bad')\n" % marker,
        encoding="utf-8",
    )
    result = []
    worker = threading.Thread(
        target=lambda: result.append(
            _get_script_catalog("demo", tmp_path, timeout_seconds=10)
        )
    )
    worker.start()
    time.sleep(0.2)
    cancel_launch_argument_discovery()
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert result and result[0].diagnostics[0].code == "discovery_failed"
    assert not marker.exists()


def test_missing_comfyui_parser_returns_explicit_unavailable_catalog(tmp_path: Path) -> None:
    catalog = comfyui_base.get_comfyui_launch_argument_catalog(tmp_path)
    assert catalog.arguments == []
    assert any(diagnostic.code == "discovery_unavailable" for diagnostic in catalog.diagnostics)


def test_api_registry_exposes_structured_catalog(tmp_path: Path) -> None:
    _write_comfyui_argument_parser(tmp_path)
    methods = registry.get_default_methods()
    target = methods["comfyui.launch.arguments_catalog"]
    assert callable(target)
    result = target(tmp_path)
    assert result.webui_type == "comfyui"
    assert result.arguments
    assert result.arguments[0].min_values == 0
    assert result.arguments[0].max_values == 0


def test_comfyui_base_parses_actual_argument_parser_object(tmp_path: Path) -> None:
    _write_comfyui_argument_parser(tmp_path)

    catalog = comfyui_base.get_comfyui_launch_argument_catalog(tmp_path)

    assert catalog.webui_type == "comfyui"
    assert len(catalog.catalog_revision) == 64
    assert catalog.diagnostics == []
    by_name = {argument.name: argument for argument in catalog.arguments}
    assert by_name["listen"].category == "network_options"
    assert by_name["listen"].value_kind is LaunchArgumentValueKind.OPTIONAL_VALUE
    assert by_name["cache_classic"].exclusive_group == by_name["cache_lru"].exclusive_group


def test_parser_loader_hides_host_arguments_and_restores_argv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sd_webui_path = tmp_path / "sd_webui"
    (sd_webui_path / "modules").mkdir(parents=True)
    (sd_webui_path / "modules" / "__init__.py").write_text("", encoding="utf-8")
    (sd_webui_path / "modules" / "cmd_args.py").write_text(
        """import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--api", action="store_true")
parser.parse_args()
""",
        encoding="utf-8",
    )
    original_argv = ["manager", "--desktop-only"]
    monkeypatch.setattr(sys, "argv", original_argv)

    catalog = sd_webui_base.get_sd_webui_launch_argument_catalog(sd_webui_path)

    assert not catalog.diagnostics
    assert {argument.name for argument in catalog.arguments} >= {"api", "help"}
    assert sys.argv is original_argv


def test_parser_loader_system_exit_falls_back_to_help(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "launch.py").write_text("print('''" + HELP_LF + "''')", encoding="utf-8")
    original_argv = ["manager", "--desktop-only"]
    monkeypatch.setattr(sys, "argv", original_argv)

    def load_parser():
        parser = argparse.ArgumentParser()
        parser.add_argument("--token", required=True)
        parser.parse_args()
        return parser

    catalog = discover_launch_argument_catalog(
        "demo",
        tmp_path,
        provider_identity="test:system-exit",
        help_command_factory=lambda context: build_script_help_command(context, ("launch.py",)),
        parser_loader=load_parser,
        python_executable=sys.executable,
    )

    assert catalog.arguments
    diagnostic = next(item for item in catalog.diagnostics if item.code == "object_discovery_failed")
    assert diagnostic.message == "ArgumentParser loader exited; falling back to --help"
    assert diagnostic.detail == "exit code: 2"
    assert sys.argv is original_argv


def test_parser_loaders_are_serialized(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original_argv = ["manager", "--desktop-only"]
    monkeypatch.setattr(sys, "argv", original_argv)
    barrier = threading.Barrier(3)
    state_lock = threading.Lock()
    active_loaders = 0
    max_active_loaders = 0
    seen_argv: list[list[str]] = []
    catalogs = []

    def load_parser():
        nonlocal active_loaders, max_active_loaders
        with state_lock:
            active_loaders += 1
            max_active_loaders = max(max_active_loaders, active_loaders)
            seen_argv.append(list(sys.argv))
        time.sleep(0.05)
        parser = argparse.ArgumentParser()
        parser.add_argument("--listen", action="store_true")
        with state_lock:
            active_loaders -= 1
        return parser

    def discover() -> None:
        barrier.wait()
        catalogs.append(
            discover_launch_argument_catalog(
                "demo",
                tmp_path,
                provider_identity="test:serialized-loader",
                help_command_factory=lambda _context: None,
                parser_loader=load_parser,
            )
        )

    workers = [threading.Thread(target=discover) for _ in range(2)]
    for worker in workers:
        worker.start()
    barrier.wait()
    for worker in workers:
        worker.join(timeout=2)

    assert all(not worker.is_alive() for worker in workers)
    assert len(catalogs) == 2
    assert all(not catalog.diagnostics for catalog in catalogs)
    assert max_active_loaders == 1
    assert seen_argv == [["manager"], ["manager"]]
    assert sys.argv is original_argv


def test_migrated_base_managers_parse_their_actual_parser_objects(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sd_webui_path = tmp_path / "sd_webui"
    (sd_webui_path / "modules").mkdir(parents=True)
    (sd_webui_path / "modules" / "__init__.py").write_text("", encoding="utf-8")
    (sd_webui_path / "modules" / "cmd_args.py").write_text(
        "import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--api', action='store_true')\n",
        encoding="utf-8",
    )

    fooocus_path = tmp_path / "fooocus"
    fooocus_path.mkdir()
    (fooocus_path / "args_manager.py").write_text(
        """import argparse
class ArgsParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("--preset")
args_parser = ArgsParser()
""",
        encoding="utf-8",
    )

    trainer_path = tmp_path / "trainer"
    trainer_path.mkdir()
    (trainer_path / "gui.py").write_text(
        "import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--listen', action='store_true')\n",
        encoding="utf-8",
    )

    kohya_path = tmp_path / "kohya"
    kohya_path.mkdir()
    (kohya_path / "kohya_gui.py").write_text(
        """import argparse
def initialize_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    return parser
""",
        encoding="utf-8",
    )

    qwen_path = tmp_path / "qwen"
    (qwen_path / "qwen_tts_webui").mkdir(parents=True)
    (qwen_path / "qwen_tts_webui" / "__init__.py").write_text("", encoding="utf-8")
    (qwen_path / "qwen_tts_webui" / "cmd_args.py").write_text(
        """import argparse
def get_args_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-port", type=int)
    return parser
""",
        encoding="utf-8",
    )

    invoke_parser = argparse.ArgumentParser()
    invoke_parser.add_argument("--invoke-model")
    original_import_module = invokeai_base.importlib.import_module
    monkeypatch.setattr(
        invokeai_base.importlib,
        "import_module",
        lambda name: SimpleNamespace(_parser=invoke_parser) if name == "invokeai.frontend.cli.arg_parser" else original_import_module(name),
    )

    catalogs = {
        "sd_webui": sd_webui_base.get_sd_webui_launch_argument_catalog(sd_webui_path),
        "fooocus": fooocus_base.get_fooocus_launch_argument_catalog(fooocus_path),
        "trainer": sd_trainer_base.get_sd_trainer_launch_argument_catalog(trainer_path),
        "kohya": sd_trainer_base.get_sd_trainer_launch_argument_catalog(kohya_path),
        "qwen": qwen_tts_webui_base.get_qwen_tts_webui_launch_argument_catalog(qwen_path),
        "invokeai": invokeai_base.get_invokeai_launch_argument_catalog(tmp_path / "invokeai"),
    }

    assert all(not catalog.diagnostics for catalog in catalogs.values())
    assert {argument.name for argument in catalogs["sd_webui"].arguments} >= {"api", "help"}
    assert {argument.name for argument in catalogs["fooocus"].arguments} >= {"preset", "help"}
    assert {argument.name for argument in catalogs["trainer"].arguments} >= {"listen", "help"}
    assert {argument.name for argument in catalogs["kohya"].arguments} >= {"headless", "help"}
    assert {argument.name for argument in catalogs["qwen"].arguments} >= {"server_port", "help"}
    assert {argument.name for argument in catalogs["invokeai"].arguments} >= {"invoke_model", "help"}
    methods = registry.get_default_methods()
    assert {
        "sd_webui.launch.arguments_catalog",
        "comfyui.launch.arguments_catalog",
        "fooocus.launch.arguments_catalog",
        "invokeai.launch.arguments_catalog",
        "sd_trainer.launch.arguments_catalog",
        "qwen_tts_webui.launch.arguments_catalog",
    }.issubset(methods)


def test_base_manager_object_failure_falls_back_to_help_and_switch_can_disable_object(tmp_path: Path) -> None:
    (tmp_path / "launch.py").write_text("print('''" + HELP_LF + "''')", encoding="utf-8")

    fallback = sd_webui_base.get_sd_webui_launch_argument_catalog(
        tmp_path,
        python_executable=sys.executable,
    )
    help_only = sd_webui_base.get_sd_webui_launch_argument_catalog(
        tmp_path,
        use_parser_object=False,
        python_executable=sys.executable,
    )

    assert fallback.arguments == help_only.arguments
    assert any(diagnostic.code == "object_discovery_failed" for diagnostic in fallback.diagnostics)
    assert not any(diagnostic.code.startswith("object_discovery") for diagnostic in help_only.diagnostics)

    unavailable = sd_webui_base.get_sd_webui_launch_argument_catalog(tmp_path / "missing")
    assert unavailable.arguments == []
    assert any(diagnostic.severity == "error" for diagnostic in unavailable.diagnostics)


def test_catalog_revision_changes_with_source_contract(tmp_path: Path) -> None:
    script = tmp_path / "launch.py"
    script.write_text("print('''" + HELP_LF + "''')", encoding="utf-8")
    first = _get_script_catalog("demo", tmp_path)
    script.write_text("print('''" + HELP_LF.replace("--port PORT", "--port-number PORT") + "''')", encoding="utf-8")
    second = _get_script_catalog("demo", tmp_path)
    assert first.catalog_revision != second.catalog_revision


def test_catalog_revision_is_stable_for_contract_and_ignores_transient_noise(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "launch.py").write_text("", encoding="utf-8")
    outputs = iter(
        [
            HELP_LF,
            HELP_LF,
            HELP_LF + "\nWARNING: imported from /tmp/example at 2026-01-01\n",
            HELP_LF.replace("--port PORT", "--port [PORT]"),
        ]
    )
    monkeypatch.setattr(
        launch_arguments_module,
        "_run_help",
        lambda _command, _context: (next(outputs), "", None),
    )
    revisions = [
        _get_script_catalog("demo", tmp_path).catalog_revision
        for _ in range(4)
    ]
    assert revisions[0] == revisions[1] == revisions[2]
    assert revisions[3] != revisions[0]
