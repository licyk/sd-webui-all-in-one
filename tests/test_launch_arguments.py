from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

import pytest

import sd_webui_all_in_one.launch_arguments as launch_arguments_module
from sd_webui_all_in_one.api_server import registry
from sd_webui_all_in_one.launch_arguments import (
    CATALOG_SCHEMA_VERSION,
    InvokeAiHelpProvider,
    LaunchArgumentDiscoveryContext,
    LaunchArgumentValueKind,
    PROVIDERS,
    ScriptHelpProvider,
    cancel_launch_argument_discovery,
    get_launch_argument_catalog,
    parse_argparse_help,
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


def test_catalog_models_serialize_stable_snake_case_shape(tmp_path: Path) -> None:
    script = tmp_path / "launch.py"
    script.write_text("print('''" + HELP_LF + "''')", encoding="utf-8")
    catalog = get_launch_argument_catalog("sd_webui", tmp_path, python_executable=sys.executable)
    payload = catalog.to_dict()
    assert payload["schema_version"] == CATALOG_SCHEMA_VERSION
    assert payload["webui_type"] == "sd_webui"
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


def test_every_desktop_family_has_provider_and_selects_expected_help_command(tmp_path: Path) -> None:
    expected_scripts = {
        "sd_webui": "launch.py",
        "comfyui": "main.py",
        "fooocus": "launch.py",
        "sd_trainer": "gui.py",
        "qwen_tts_webui": "launch.py",
    }
    assert set(PROVIDERS) == {*expected_scripts, "invokeai"}
    for webui_type, script_name in expected_scripts.items():
        family = tmp_path / webui_type
        family.mkdir()
        (family / script_name).write_text("", encoding="utf-8")
        provider = PROVIDERS[webui_type]
        assert isinstance(provider, ScriptHelpProvider)
        command = provider.help_command(LaunchArgumentDiscoveryContext(webui_type, family))
        assert command is not None
        assert command.argv[-2:] == [str(family / script_name), "--help"]

    invoke = PROVIDERS["invokeai"]
    assert isinstance(invoke, InvokeAiHelpProvider)
    command = invoke.help_command(LaunchArgumentDiscoveryContext("invokeai", tmp_path))
    assert command.argv[1] == "-c"
    assert "invokeai.frontend.cli.arg_parser" in command.argv[2]
    assert command.env and command.env["INVOKEAI_ROOT"] == str(tmp_path)


def test_sd_trainer_provider_falls_back_to_kohya_script(tmp_path: Path) -> None:
    (tmp_path / "kohya_gui.py").write_text("", encoding="utf-8")
    provider = PROVIDERS["sd_trainer"]
    assert isinstance(provider, ScriptHelpProvider)
    command = provider.help_command(LaunchArgumentDiscoveryContext("sd_trainer", tmp_path))
    assert command is not None
    assert command.argv[-2:] == [str(tmp_path / "kohya_gui.py"), "--help"]


def test_discovery_timeout_terminates_child_and_never_returns_empty_success(tmp_path: Path) -> None:
    marker = tmp_path / "completed"
    (tmp_path / "launch.py").write_text(
        "import time, pathlib\ntime.sleep(5)\npathlib.Path(r'%s').write_text('bad')\n" % marker,
        encoding="utf-8",
    )
    started = time.monotonic()
    catalog = get_launch_argument_catalog(
        "sd_webui",
        tmp_path,
        python_executable=sys.executable,
        timeout_seconds=0.1,
    )
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
            get_launch_argument_catalog(
                "sd_webui",
                tmp_path,
                python_executable=sys.executable,
                timeout_seconds=10,
            )
        )
    )
    worker.start()
    time.sleep(0.2)
    cancel_launch_argument_discovery()
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert result and result[0].diagnostics[0].code == "discovery_failed"
    assert not marker.exists()


def test_missing_script_returns_explicit_unavailable_catalog(tmp_path: Path) -> None:
    catalog = get_launch_argument_catalog("comfyui", tmp_path)
    assert catalog.arguments == []
    assert catalog.diagnostics[0].code == "discovery_unavailable"


def test_api_registry_exposes_structured_catalog_and_validates_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('''" + HELP_LF + "''')", encoding="utf-8")
    result = registry.launch_arguments_catalog({"webui_type": "comfyui", "webui_path": str(tmp_path)})
    assert result["catalog"]["webui_type"] == "comfyui"
    assert result["catalog"]["arguments"]
    assert result["catalog"]["arguments"][0]["min_values"] == 0
    assert result["catalog"]["arguments"][0]["max_values"] == 0
    assert "launch.arguments.catalog" in registry.get_default_methods()
    with pytest.raises(ValueError, match="timeout"):
        registry.launch_arguments_catalog({"webui_type": "comfyui", "webui_path": str(tmp_path), "options": {"timeout": "forever"}})


def test_catalog_revision_changes_with_source_contract(tmp_path: Path) -> None:
    script = tmp_path / "launch.py"
    script.write_text("print('''" + HELP_LF + "''')", encoding="utf-8")
    first = get_launch_argument_catalog("sd_webui", tmp_path, python_executable=sys.executable)
    script.write_text("print('''" + HELP_LF.replace("--port PORT", "--port-number PORT") + "''')", encoding="utf-8")
    second = get_launch_argument_catalog("sd_webui", tmp_path, python_executable=sys.executable)
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
        get_launch_argument_catalog("sd_webui", tmp_path, python_executable=sys.executable).catalog_revision
        for _ in range(4)
    ]
    assert revisions[0] == revisions[1] == revisions[2]
    assert revisions[3] != revisions[0]
