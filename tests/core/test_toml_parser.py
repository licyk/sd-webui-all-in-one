"""TOML 解析器测试"""

import io
import math
from datetime import date, datetime, time, timezone

import pytest

from sd_webui_all_in_one import toml_parser


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
