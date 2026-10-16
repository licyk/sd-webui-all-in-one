"""依赖文件解码与逻辑行拆分测试"""

import pytest

from sd_webui_all_in_one.package_analyzer.reqfile import (
    decode_requirements,
    expand_env_variables,
    iter_logical_lines,
)


# ============================================================================
# 词法处理
# ============================================================================
class TestLexer:
    def test_decode_prefers_bom(self):
        assert decode_requirements("numpy\n".encode("utf-8-sig")) == "numpy\n"
        assert decode_requirements("numpy\n".encode("utf-16")) == "numpy\n"
        assert decode_requirements("numpy\n".encode("utf-32")) == "numpy\n"

    def test_decode_honours_coding_cookie(self):
        data = "# -*- coding: latin-1 -*-\n# caf\xe9\nnumpy\n".encode("latin-1")
        assert "caf\xe9" in decode_requirements(data)

    def test_decode_unknown_cookie_falls_back_to_utf8(self):
        assert decode_requirements(b"# coding: no-such-codec\nnumpy\n").endswith("numpy\n")

    def test_decode_invalid_utf8_raises(self):
        with pytest.raises(UnicodeDecodeError):
            decode_requirements(b"\xff\x00torch")

    def test_comment_needs_leading_whitespace(self):
        lines = [line.text for line in iter_logical_lines("a==1 # comment\nhttps://e.com/a.whl#sha256=abc\n# full line\n  \nb#notcomment\n")]
        assert lines == ["a==1", "https://e.com/a.whl#sha256=abc", "b#notcomment"]

    def test_line_continuation_keeps_first_line_number(self):
        lines = list(iter_logical_lines("first\nfoo>=1.0, \\\n    <2.0 \\\n    ; python_version > '3'\nlast\n"))
        assert [(line.lineno, line.text) for line in lines] == [
            (1, "first"),
            (2, "foo>=1.0,     <2.0     ; python_version > '3'"),
            (5, "last"),
        ]

    def test_comment_line_inside_continuation_is_dropped(self):
        lines = [line.text for line in iter_logical_lines("foo>=1.0 \\\n# explain\n")]
        assert lines == ["foo>=1.0"]

    def test_trailing_continuation_at_end_of_file(self):
        assert [line.text for line in iter_logical_lines("foo \\")] == ["foo"]

    def test_env_variables_are_expanded_only_when_defined(self):
        assert expand_env_variables("https://${USER}:${TOKEN}@host/${lower}/$PLAIN", {"USER": "me"}) == "https://me:${TOKEN}@host/${lower}/$PLAIN"
        lines = list(iter_logical_lines("a @ https://${HOST}/a.whl\n", environ={"HOST": "h"}, expand_env=False))
        assert lines[0].text == "a @ https://${HOST}/a.whl"

    def test_directive_is_read_from_comment(self):
        lines = list(iter_logical_lines("a<3.4 # skip_verify\nb # other\nc\n"))
        assert [(line.text, set(line.directives)) for line in lines] == [("a<3.4", {"skip_verify"}), ("b", set()), ("c", set())]
