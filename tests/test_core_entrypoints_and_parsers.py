import io
import math
import runpy
import sys
from datetime import date, datetime, time, timezone

import pytest

from sd_webui_all_in_one import toml_parser
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.simple_tqdm import SimpleTqdm


def _reset_simple_tqdm_state():
    SimpleTqdm._active_instances = 0
    SimpleTqdm._max_pos = -1
    SimpleTqdm._instances.clear()


def test_simple_tqdm_disabled_iter_context_and_formatting(capsys):
    bar = SimpleTqdm([1, 2, 3], desc="items", disable=True)

    assert list(bar) == [1, 2, 3]
    assert bar.n == 3

    with SimpleTqdm(total=3, disable=True) as disabled_bar:
        disabled_bar.update(0)
        disabled_bar.update(2)
        assert disabled_bar.n == 2
        assert disabled_bar._format_time(65) == "01:05"

    with SimpleTqdm(total=2048, unit="B", unit_scale=True, disable=True) as bytes_bar:
        bytes_bar.update(1024)
        assert bytes_bar._format_amount(bytes_bar.n) == "1KB"

    assert capsys.readouterr().out == ""


def test_simple_tqdm_renders_known_total_and_clears(monkeypatch, capsys):
    _reset_simple_tqdm_state()
    times = iter([100.0, 100.0, 100.5, 101.0, 101.0])
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.time.time", lambda: next(times, 101.0))
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (50, 20))

    try:
        with SimpleTqdm(desc="demo", total=2, leave=False, bar_length=5) as bar:
            bar.update(1)
            bar.update(1)
            assert bar.n == 2
    finally:
        _reset_simple_tqdm_state()

    output = capsys.readouterr().out
    assert "demo" in output
    assert "100%" in output
    assert "\033[K" in output


def test_simple_tqdm_initial_unit_divisor_file_and_idempotent_close(monkeypatch):
    _reset_simple_tqdm_state()
    output = io.StringIO()
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (60, 20))

    bar = SimpleTqdm(total=2048, initial=512, unit="B", unit_scale=True, unit_divisor=1024, file=output, mininterval=0)

    assert bar.n == 512
    assert bar._format_amount(1536) == "1.5KB"
    assert bar._format_time(3661) == "1:01:01"

    bar.update(512)
    bar.update(0)
    bar.set_description("download")
    bar.set_postfix({"status": "ok"}, speed="fast")
    bar.set_postfix_str("done")
    bar.close()
    bar.close()

    rendered = output.getvalue()
    assert "download" in rendered
    assert "done" in rendered
    assert SimpleTqdm._active_instances == 0


def test_simple_tqdm_reset_clear_write_and_falsey_iterable(monkeypatch):
    class FalseyIterable:
        def __bool__(self):
            return False

        def __iter__(self):
            return iter([1, 2])

    _reset_simple_tqdm_state()
    output = io.StringIO()
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (40, 20))

    bar = SimpleTqdm(FalseyIterable(), total=2, file=output, ncols=40)

    assert list(bar) == [1, 2]
    assert bar.n == 2
    assert SimpleTqdm._active_instances == 0

    with SimpleTqdm(total=3, file=output, leave=False) as manual_bar:
        manual_bar.update(2)
        manual_bar.reset(total=5)
        assert manual_bar.n == 0
        assert manual_bar.total == 5
        manual_bar.clear()

    SimpleTqdm.write("message", file=output)
    rendered = output.getvalue()
    assert "\033[K" in rendered
    assert "message\n" in rendered


def test_simple_tqdm_colour_is_applied_only_to_known_bar_colours(monkeypatch):
    _reset_simple_tqdm_state()
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (80, 20))

    output = io.StringIO()
    with SimpleTqdm(total=2, colour="red", bar_length=4, file=output, mininterval=0) as bar:
        bar.update(1)

    rendered = output.getvalue()
    assert "\033[31m" in rendered
    assert "\033[0m" in rendered
    assert ": 50%|" in rendered

    output = io.StringIO()
    with SimpleTqdm(total=2, colour="unknown", bar_length=4, file=output, mininterval=0) as bar:
        bar.update(1)

    assert "\033[31m" not in output.getvalue()


def test_simple_tqdm_smoothing_controls_display_rate(monkeypatch):
    _reset_simple_tqdm_state()
    clock = {"now": 0.0}
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.time.time", lambda: clock["now"])
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (100, 20))

    output = io.StringIO()
    bar = SimpleTqdm(total=20, file=output, mininterval=0, smoothing=0.25)
    clock["now"] = 1.0
    bar.update(1)
    clock["now"] = 2.0
    bar.update(9)

    assert "3it/s" in output.getvalue()

    bar.reset(total=4)
    assert bar._ema_rate is None
    bar.close()

    output = io.StringIO()
    clock["now"] = 0.0
    bar = SimpleTqdm(total=20, file=output, mininterval=0, smoothing=0)
    clock["now"] = 1.0
    bar.update(1)
    clock["now"] = 2.0
    bar.update(9)
    bar.close()

    assert "5it/s" in output.getvalue()


def test_simple_tqdm_bar_format_subset_preserves_unknown_fields(monkeypatch):
    _reset_simple_tqdm_state()
    clock = {"now": 0.0}
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.time.time", lambda: clock["now"])
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (100, 20))

    output = io.StringIO()
    bar = SimpleTqdm(
        desc="fmt",
        total=4,
        file=output,
        mininterval=0,
        bar_length=4,
        bar_format="{desc}|{bar}|{n_fmt}/{total_fmt}|{postfix}|{elapsed}|{rate_fmt}|{unknown}",
    )
    bar.set_postfix_str("phase=1", refresh=False)
    clock["now"] = 2.0
    bar.update(2)
    bar.close()

    rendered = output.getvalue()
    assert "fmt|██--|2it/4it|phase=1|00:02|1it/s|{unknown}" in rendered


def test_simple_tqdm_truncates_ansi_and_wide_text_by_visible_width():
    bar = SimpleTqdm(total=1, disable=True, ncols=8)
    rendered = bar._truncate_visible("\033[36m下载任务进度\033[0m", 8)

    assert bar._visible_len(rendered) <= 8
    assert rendered.endswith("\033[0m")
    assert "..." in rendered


def test_simple_tqdm_write_clears_and_refreshes_active_bars(monkeypatch):
    _reset_simple_tqdm_state()
    monkeypatch.setattr("sd_webui_all_in_one.simple_tqdm.shutil.get_terminal_size", lambda fallback: (80, 20))

    output = io.StringIO()
    bar_one = SimpleTqdm(desc="one", total=2, file=output, position=0, mininterval=0)
    bar_two = SimpleTqdm(desc="two", total=2, file=output, position=1, mininterval=0)

    SimpleTqdm.write("log message", file=output)
    bar_two.close()
    bar_one.close()

    rendered = output.getvalue()
    assert "log message\n" in rendered
    assert rendered.count("\033[K") >= 4
    assert rendered.count("one") >= 2
    assert rendered.count("two") >= 2


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

    assert toml_parser.load(io.BytesIO(b'name = "binary"')) == {"name": "binary"}
    with pytest.raises(TypeError, match="rb"):
        toml_parser.load(io.StringIO('name = "text"'))  # type: ignore[arg-type]


def test_toml_parser_supports_toml_1_1_values_keys_and_inline_tables():
    content = (
        'url = "https://example.com/#anchor"\n'
        'escape = "line\\e\\x21"\n'
        "literal = 'C:\\Users\\nodejs\\templates'\n"
        'multiline_basic = """\\\n'
        "       The quick brown \\\n"
        '       fox jumps."""\n'
        "multiline_literal = '''\n"
        "first newline trimmed\n"
        "'''\n"
        "hex = 0xdead_beef\n"
        "oct = 0o755\n"
        "bin = 0b11010110\n"
        "plus = +99\n"
        "neg_zero = -0\n"
        "float_us = 224_617.445_991_228\n"
        "exp = 1e06\n"
        "pos_inf = +inf\n"
        "neg_nan = -nan\n"
        "odt = 1979-05-27 07:32Z\n"
        "ldt = 1979-05-27T07:32\n"
        "ld = 1979-05-27\n"
        "lt = 07:32\n"
        'physical.color = "orange"\n'
        'site."google.com" = true\n'
        "inline = {\n"
        '  type.name = "pug",\n'
        '  contact = { email = "dog@example.test", },\n'
        "}\n"
        'mixed = [1, "two", true, { x = 1, y = 2, },]\n'
    )

    parsed = toml_parser.loads(content)

    assert parsed["url"] == "https://example.com/#anchor"
    assert parsed["escape"] == "line\x1b!"
    assert parsed["literal"] == "C:\\Users\\nodejs\\templates"
    assert parsed["multiline_basic"] == "The quick brown fox jumps."
    assert parsed["multiline_literal"] == "first newline trimmed\n"
    assert parsed["hex"] == 0xDEADBEEF
    assert parsed["oct"] == 0o755
    assert parsed["bin"] == 0b11010110
    assert parsed["plus"] == 99
    assert parsed["neg_zero"] == 0
    assert parsed["float_us"] == 224_617.445_991_228
    assert parsed["exp"] == 1_000_000.0
    assert math.isinf(parsed["pos_inf"])
    assert math.isnan(parsed["neg_nan"])
    assert parsed["odt"] == datetime(1979, 5, 27, 7, 32, tzinfo=timezone.utc)
    assert parsed["ldt"] == datetime(1979, 5, 27, 7, 32)
    assert parsed["ld"] == date(1979, 5, 27)
    assert parsed["lt"] == time(7, 32)
    assert parsed["physical"] == {"color": "orange"}
    assert parsed["site"] == {"google.com": True}
    assert parsed["inline"] == {
        "type": {"name": "pug"},
        "contact": {"email": "dog@example.test"},
    }
    assert parsed["mixed"] == [1, "two", True, {"x": 1, "y": 2}]


def test_toml_parser_supports_nested_array_tables_on_latest_parent():
    content = """
    [[fruits]]
    name = "apple"

    [fruits.physical]
    color = "red"

    [[fruits.varieties]]
    name = "red delicious"

    [[fruits]]
    name = "banana"

    [[fruits.varieties]]
    name = "plantain"
    """

    parsed = toml_parser.loads(content)

    assert parsed["fruits"] == [
        {
            "name": "apple",
            "physical": {"color": "red"},
            "varieties": [{"name": "red delicious"}],
        },
        {
            "name": "banana",
            "varieties": [{"name": "plantain"}],
        },
    ]


@pytest.mark.parametrize(
    "content",
    [
        'name = "a"\nname = "b"\n',
        "[fruit]\n[fruit]\n",
        'fruit.apple.color = "red"\n[fruit]\n',
        "fruit.apple = 1\nfruit.apple.smooth = true\n",
        '[product]\ntype = { name = "Nail" }\ntype.edible = false\n',
        "fruits = []\n[[fruits]]\n",
        "[[fruits]]\n[fruits]\n",
        "enabled = True\n",
        "num = 01\n",
        "num = 1__0\n",
        "flt = .7\n",
        "birthday = 1979-13-27\n",
    ],
)
def test_toml_parser_rejects_invalid_documents(content):
    with pytest.raises(toml_parser.TomlDecodeError):
        toml_parser.loads(content)


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
