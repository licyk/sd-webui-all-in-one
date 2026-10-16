"""依赖文件选项解析测试"""

import pytest

from sd_webui_all_in_one.package_analyzer.errors import (
    UnsupportedOption,
)
from sd_webui_all_in_one.package_analyzer.reqfile import (
    parse_options,
    split_args_and_options,
)
from tests.package_analyzer.reqfile.helpers import parse_lines


# ============================================================================
# 选项
# ============================================================================
class TestOptions:
    def test_split_args_and_options(self):
        assert split_args_and_options("foo==1.0 --hash=sha256:abc") == ("foo==1.0", "--hash=sha256:abc")
        assert split_args_and_options("-e ./local") == ("", "-e ./local")
        assert split_args_and_options('foo ; python_version < "3"') == ('foo ; python_version < "3"', "")

    def test_option_spellings(self):
        options, leftovers = parse_options("--index-url https://a --extra-index-url=https://b -f https://c -fhttps://d --pre")
        assert [(option.name, option.value) for option in options] == [
            ("--index-url", "https://a"),
            ("--extra-index-url", "https://b"),
            ("--find-links", "https://c"),
            ("--find-links", "https://d"),
            ("--pre", None),
        ]
        assert leftovers == []

    def test_quoted_values_and_abbreviations(self):
        options, _ = parse_options('--find-links "/path with spaces" --extra-index https://x')
        assert [(option.name, option.value) for option in options] == [("--find-links", "/path with spaces"), ("--extra-index-url", "https://x")]

    def test_leftover_arguments_are_reported(self):
        _, leftovers = parse_options("--pre extra tokens")
        assert leftovers == ["extra", "tokens"]

    @pytest.mark.parametrize("text", ["--bogus x", "-x", "--index-url", "--pre=1", '--find-links "unterminated', "--no", "--target dir"])
    def test_unsupported_options(self, text):
        with pytest.raises(UnsupportedOption):
            parse_options(text)


class TestGlobalOptions:
    def test_all_global_options(self, tmp_path):
        parsed = parse_lines(
            "\n".join(
                [
                    "--index-url https://a/simple --extra-index-url=https://b/simple",
                    "-i https://final/simple",
                    "-f https://links --pre --no-binary :all: --only-binary numpy,Foo_Bar",
                    "--trusted-host a --use-feature fast-deps --prefer-binary --require-hashes",
                    "--no-index",
                    "--all-releases torch --only-final :all:",
                ]
            ),
            tmp_path,
        )
        options = parsed.options
        assert options.index_url == "https://final/simple"
        assert options.extra_index_urls == ["https://b/simple"]
        assert options.find_links == ["https://links"]
        assert options.pre is True
        assert options.no_binary == {":all:"}
        assert options.only_binary == {"numpy", "foo-bar"}
        assert options.trusted_hosts == ["a"]
        assert options.features == ["fast-deps"]
        assert options.prefer_binary is True
        assert options.require_hashes is True
        assert options.no_index is True
        assert options.only_final == {":all:"}
        assert options.all_releases == set()
        assert parsed.entries == []
        assert parsed.diagnostics == []

    def test_binary_control_is_mutually_exclusive(self, tmp_path):
        parsed = parse_lines("--no-binary numpy,scipy\n--only-binary numpy\n--no-binary :none:\n--no-require-hashes\n", tmp_path)
        assert parsed.options.only_binary == {"numpy"}
        assert parsed.options.no_binary == set()
        assert parsed.options.require_hashes is False

    def test_unknown_option_is_reported_and_parsing_continues(self, tmp_path):
        parsed = parse_lines("--bogus-option x\nnumpy\nscipy --bogus\n", tmp_path)
        assert [entry.name for entry in parsed.entries] == ["numpy", "scipy"]
        assert [(diagnostic.severity, diagnostic.lineno) for diagnostic in parsed.diagnostics] == [("error", 1), ("error", 3)]

    def test_global_option_on_requirement_line_is_ignored_with_warning(self, tmp_path):
        parsed = parse_lines("numpy --pre\n", tmp_path)
        assert parsed.entries[0].name == "numpy"
        assert parsed.options.pre is False
        assert [diagnostic.severity for diagnostic in parsed.diagnostics] == ["warning"]
