import io
import runpy
import sys

import pytest

from sd_webui_all_in_one import toml_parser
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.simple_tqdm import SimpleTqdm


def test_simple_tqdm_disabled_iter_context_and_formatting(capsys):
    bar = SimpleTqdm([1, 2, 3], desc="items", disable=True)

    assert list(bar) == [1, 2, 3]
    assert bar.n == 0

    with SimpleTqdm(total=3, disable=True) as disabled_bar:
        disabled_bar.update(0)
        disabled_bar.update(2)
        assert disabled_bar.n == 2
        assert disabled_bar._format_time(65) == "01:05"

    assert capsys.readouterr().out == ""


def test_simple_tqdm_renders_known_total_and_clears(monkeypatch, capsys):
    SimpleTqdm._active_instances = 0
    SimpleTqdm._max_pos = -1
    times = iter([100.0, 100.0, 100.5, 101.0, 101.0])
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.time.time", lambda: next(times, 101.0))
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (50, 20))

    try:
        with SimpleTqdm(desc="demo", total=2, leave=False, bar_length=5) as bar:
            bar.update(1)
            bar.update(1)
            assert bar.n == 2
    finally:
        SimpleTqdm._active_instances = 0
        SimpleTqdm._max_pos = -1

    output = capsys.readouterr().out
    assert "demo" in output
    assert "100%" in output
    assert "\033[K" in output


def test_toml_parser_loads_nested_tables_arrays_and_binary_stream():
    content = """
    title = "Demo\\nName"
    enabled = true
    count = 3
    ratio = 1.5
    numbers = [
        1,
        2,
        [3, 4],
        { name = "inner", enabled = false },
    ]

    [owner]
    name = "Ada"

    [[products]]
    name = "Hammer"
    sku = 738594937

    [[products]]
    name = "Nail"
    color = "gray"
    """

    parsed = toml_parser.loads(content)
    assert parsed["title"] == "Demo\nName"
    assert parsed["enabled"] is True
    assert parsed["count"] == 3
    assert parsed["ratio"] == 1.5
    assert parsed["numbers"] == [1, 2, [3, 4], {"name": "inner", "enabled": False}]
    assert parsed["owner"] == {"name": "Ada"}
    assert parsed["products"][0]["name"] == "Hammer"
    assert parsed["products"][1]["color"] == "gray"

    assert toml_parser.load(io.BytesIO(b"name = \"binary\"")) == {"name": "binary"}
    with pytest.raises(TypeError, match="rb"):
        toml_parser.load(io.StringIO("name = \"text\""))  # type: ignore[arg-type]


def test_aggregate_error_formats_child_traceback():
    try:
        raise ValueError("inner")
    except ValueError as exc:
        aggregate = AggregateError("many failed", [exc])

    text = str(aggregate)
    assert "many failed" in text
    assert "ValueError" in text
    assert "inner" in text
    assert "test_aggregate_error_formats_child_traceback" in text


def test_module_main_delegates_to_cli_main(monkeypatch):
    from sd_webui_all_in_one.cli_manager import cli

    calls = []
    monkeypatch.setattr(cli, "main", lambda: calls.append("main"))

    runpy.run_module("sd_webui_all_in_one.__main__", run_name="__main__")

    assert calls == ["main"]


def test_cli_main_dispatches_registered_callback(monkeypatch):
    from sd_webui_all_in_one.cli_manager import cli

    calls = []

    def register_demo(subparsers):
        parser = subparsers.add_parser("demo")
        parser.set_defaults(func=lambda args: calls.append(args.main_command))

    def noop_register(_subparsers):
        return None

    for name in [
        "register_sd_trainer",
        "register_sd_scripts",
        "register_invokeai",
        "register_fooocus",
        "register_comfyui",
        "register_qwen_tts_webui",
        "register_manager",
    ]:
        monkeypatch.setattr(cli, name, noop_register)
    monkeypatch.setattr(cli, "register_sd_webui", register_demo)
    monkeypatch.setattr(sys, "argv", ["sd-webui-all-in-one", "demo"])

    cli.main()

    assert calls == ["demo"]


def test_cli_main_prints_help_without_subcommand(monkeypatch, capsys):
    from sd_webui_all_in_one.cli_manager import cli

    def noop_register(_subparsers):
        return None

    for name in [
        "register_sd_webui",
        "register_sd_trainer",
        "register_sd_scripts",
        "register_invokeai",
        "register_fooocus",
        "register_comfyui",
        "register_qwen_tts_webui",
        "register_manager",
    ]:
        monkeypatch.setattr(cli, name, noop_register)
    monkeypatch.setattr(sys, "argv", ["sd-webui-all-in-one"])

    cli.main()

    output = capsys.readouterr().out
    assert "SD WebUI All In One" in output
    assert "usage:" in output
