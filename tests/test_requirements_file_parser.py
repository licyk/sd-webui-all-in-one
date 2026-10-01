"""依赖文件解析器测试

行为以 pip 的 requirements 文件格式为准, 并在可用时以 pip 自身的解析器作为对照.

参考:
    - https://pip.pypa.io/en/stable/reference/requirements-file-format/
"""

import io
import sys
from pathlib import Path

import pytest

from sd_webui_all_in_one import toml_parser
from sd_webui_all_in_one.env_check.comfyui_env_analyze.environment import read_requirement_declarations
from sd_webui_all_in_one.package_analyzer import local_project
from sd_webui_all_in_one.package_analyzer.errors import (
    NestedFileNotFound,
    RecursiveInclude,
    RequirementsFileError,
    UnsupportedOption,
)
from sd_webui_all_in_one.package_analyzer.local_project import (
    file_url_path_to_local_path,
    get_local_project_name,
    is_installable_dir,
)
from sd_webui_all_in_one.package_analyzer.reqfile import (
    EntryKind,
    decode_requirements,
    expand_env_variables,
    iter_logical_lines,
    parse_options,
    parse_requirements_file,
    parse_requirements_text,
    split_args_and_options,
)
from sd_webui_all_in_one.package_analyzer.version import Version


def _parse(text, tmp_path, **kwargs):
    """在空目录下解析依赖文件文本"""
    kwargs.setdefault("base_dir", tmp_path)
    kwargs.setdefault("environ", {})
    return parse_requirements_text(text, **kwargs)


def _make_project(path, name="Local_Proj"):
    path.mkdir(parents=True, exist_ok=True)
    (path / "pyproject.toml").write_text(f'[project]\nname = "{name}"\nversion = "1.0"\n', encoding="utf-8")
    return path


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


# ============================================================================
# 条目分类
# ============================================================================


class TestEntries:
    def test_named_requirement_with_hashes(self, tmp_path):
        parsed = _parse("requests[security] >= 2.8.1, \\\n    < 3 --hash=sha256:abc --hash sha256:def\n", tmp_path)
        (entry,) = parsed.entries
        assert entry.kind == EntryKind.NAMED
        assert entry.name == "requests"
        assert entry.extras == ("security",)
        assert str(entry.requirement) == "requests[security]>=2.8.1,<3"
        assert entry.hashes == ("sha256:abc", "sha256:def")
        assert entry.source.lineno == 1
        assert parsed.diagnostics == []

    def test_wildcard_and_non_canonical_versions_are_kept(self, tmp_path):
        parsed = _parse("torch==2.3.*\nbar==1.0-1\nbaz==2.3.0+CU118\n", tmp_path)
        assert [str(entry.requirement) for entry in parsed.entries] == ["torch==2.3.*", "bar==1.0-1", "baz==2.3.0+CU118"]
        assert parsed.entries[1].requirement.specifier.contains("1.0.post1")

    def test_marker_and_skip_verify_directive(self, tmp_path):
        parsed = _parse('triton-windows<3.4; sys_platform == "win32" # skip_verify\nonnx; sys_platform == "win32"\n', tmp_path)
        first, second = parsed.entries
        assert first.skip_verify is True
        assert second.skip_verify is False
        assert second.applies_to({"sys_platform": "win32"}) is True
        assert second.applies_to({"sys_platform": "linux"}) is False

    def test_direct_reference_with_env_variable(self, tmp_path):
        parsed = _parse('pkg @ https://${HOST}/pkg-1.0-py3-none-any.whl ; os_name == "posix"\n', tmp_path, environ={"HOST": "h.example"})
        (entry,) = parsed.entries
        assert entry.kind == EntryKind.NAMED
        assert entry.url == "https://h.example/pkg-1.0-py3-none-any.whl"
        assert str(entry.marker) == 'os_name == "posix"'

    def test_vcs_url_fragments(self, tmp_path):
        parsed = _parse("git+https://user:tok@github.com/user/Repo.git@v1.0#egg=RealName[extra]&subdirectory=src\n", tmp_path)
        (entry,) = parsed.entries
        assert entry.kind == EntryKind.URL
        assert entry.name == "RealName"
        assert entry.extras == ("extra",)
        assert entry.vcs == "git"
        assert entry.revision == "v1.0"
        assert entry.subdirectory == "src"

    def test_vcs_url_without_egg_has_no_name(self, tmp_path):
        parsed = _parse('git+ssh://git@github.com:user/sshrepo.git@main ; python_version > "3"\n', tmp_path)
        (entry,) = parsed.entries
        assert entry.name is None
        assert entry.revision == "main"
        assert str(entry.marker) == 'python_version > "3"'
        assert parsed.diagnostics == []

    def test_wheel_url_provides_name_version_and_hash(self, tmp_path):
        parsed = _parse("https://example.com/pkgs/demo_pkg-1.2.3-py3-none-any.whl#sha256=deadbeef\n", tmp_path)
        (entry,) = parsed.entries
        assert entry.kind == EntryKind.URL
        assert (entry.name, entry.version) == ("demo_pkg", Version.parse("1.2.3"))
        assert entry.hashes == ("sha256:deadbeef",)

    def test_sdist_url_is_kept_without_name(self, tmp_path):
        parsed = _parse("https://example.com/foo-1.0.tar.gz\n", tmp_path)
        (entry,) = parsed.entries
        assert entry.kind == EntryKind.URL
        assert entry.name is None
        assert parsed.diagnostics == []

    def test_invalid_wheel_url_is_an_error(self, tmp_path):
        parsed = _parse("https://example.com/broken.whl\nnumpy\n", tmp_path)
        assert [entry.name for entry in parsed.entries] == ["numpy"]
        assert len(parsed.errors) == 1

    def test_local_directory_and_editable(self, tmp_path):
        _make_project(tmp_path / "proj")
        parsed = _parse("./proj\n-e ./proj[dev,test]\n--editable=proj\n", tmp_path)
        plain, editable, long_form = parsed.entries
        assert plain.kind == EntryKind.PATH
        assert plain.name == "Local_Proj"
        assert plain.path == tmp_path / "proj"
        assert plain.editable is False
        assert editable.editable is True
        assert editable.extras == ("dev", "test")
        assert long_form.editable is True and long_form.name == "Local_Proj"
        assert parsed.editables == [editable, long_form]
        assert parsed.diagnostics == []

    def test_editable_dot_is_a_warning_not_an_error(self, tmp_path):
        # 目录中没有 pyproject.toml / setup.py: 条目保留, 只产生警告, 严格模式下也不抛出异常
        parsed = _parse("-e .\nnumpy\n", tmp_path, strict=True)
        editable, numpy = parsed.entries
        assert editable.kind == EntryKind.PATH
        assert editable.editable is True
        assert editable.name is None
        assert editable.path == tmp_path
        assert numpy.name == "numpy"
        assert [diagnostic.severity for diagnostic in parsed.diagnostics] == ["warning"]

    def test_editable_missing_path_is_a_warning(self, tmp_path):
        parsed = _parse("-e ./missing\n", tmp_path, strict=True)
        assert parsed.entries[0].path == tmp_path / "missing"
        assert [diagnostic.severity for diagnostic in parsed.diagnostics] == ["warning"]

    def test_editable_vcs_and_invalid_editable_url(self, tmp_path):
        parsed = _parse("-e git+https://github.com/user/pkg.git@main#egg=Pkg-Extra\n-e https://example.com/x.whl\n", tmp_path)
        (entry,) = parsed.entries
        assert (entry.kind, entry.editable, entry.name, entry.vcs) == (EntryKind.URL, True, "Pkg-Extra", "git")
        assert len(parsed.errors) == 1

    def test_local_wheel_and_file_url(self, tmp_path):
        (tmp_path / "demo-1.0-py3-none-any.whl").write_bytes(b"")
        _make_project(tmp_path / "proj")
        parsed = _parse(f"./demo-1.0-py3-none-any.whl\ndemo-1.0-py3-none-any.whl\n{(tmp_path / 'proj').as_uri()}\n", tmp_path)
        first, second, third = parsed.entries
        assert (first.kind, first.name, first.version) == (EntryKind.PATH, "demo", Version.parse("1.0"))
        assert (second.kind, second.name) == (EntryKind.PATH, "demo")
        assert (third.kind, third.name, third.path) == (EntryKind.PATH, "Local_Proj", tmp_path / "proj")

    def test_plain_name_is_not_mistaken_for_a_directory(self, tmp_path):
        (tmp_path / "requests").mkdir()
        parsed = _parse("requests\n", tmp_path)
        assert parsed.entries[0].kind == EntryKind.NAMED

    def test_missing_path_and_invalid_requirement_are_errors(self, tmp_path):
        parsed = _parse("./missing-dir\ninvalid !!!\nfoo==1.0 garbage\nbad; python_version >\nnumpy\n", tmp_path)
        assert [entry.name for entry in parsed.entries] == ["numpy"]
        assert [(diagnostic.severity, diagnostic.lineno) for diagnostic in parsed.diagnostics] == [("error", 1), ("error", 2), ("error", 3), ("error", 4)]
        assert "<string>:2" in str(parsed.diagnostics[1])

    def test_strict_mode_raises_on_first_error(self, tmp_path):
        with pytest.raises(RequirementsFileError) as error:
            _parse("numpy\ninvalid !!!\n", tmp_path, strict=True)
        assert error.value.lineno == 2
        with pytest.raises(UnsupportedOption):
            _parse("--bogus-option x\n", tmp_path, strict=True)


class TestGlobalOptions:
    def test_all_global_options(self, tmp_path):
        parsed = _parse(
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
        parsed = _parse("--no-binary numpy,scipy\n--only-binary numpy\n--no-binary :none:\n--no-require-hashes\n", tmp_path)
        assert parsed.options.only_binary == {"numpy"}
        assert parsed.options.no_binary == set()
        assert parsed.options.require_hashes is False

    def test_unknown_option_is_reported_and_parsing_continues(self, tmp_path):
        parsed = _parse("--bogus-option x\nnumpy\nscipy --bogus\n", tmp_path)
        assert [entry.name for entry in parsed.entries] == ["numpy", "scipy"]
        assert [(diagnostic.severity, diagnostic.lineno) for diagnostic in parsed.diagnostics] == [("error", 1), ("error", 3)]

    def test_global_option_on_requirement_line_is_ignored_with_warning(self, tmp_path):
        parsed = _parse("numpy --pre\n", tmp_path)
        assert parsed.entries[0].name == "numpy"
        assert parsed.options.pre is False
        assert [diagnostic.severity for diagnostic in parsed.diagnostics] == ["warning"]


# ============================================================================
# 嵌套文件
# ============================================================================


class TestNestedFiles:
    def test_nested_requirements_and_constraints(self, tmp_path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "main.txt").write_text("torch\n-r sub/more.txt\n-c cons.txt\nlast\n", encoding="utf-8")
        (tmp_path / "sub" / "more.txt").write_text("nested>=1\n-r deeper.txt\n", encoding="utf-8")
        (tmp_path / "sub" / "deeper.txt").write_text("deepest\n", encoding="utf-8")
        (tmp_path / "cons.txt").write_text("numpy<2\n-r from-constraint.txt\n", encoding="utf-8")
        (tmp_path / "from-constraint.txt").write_text("extra-req\n", encoding="utf-8")

        parsed = parse_requirements_file(tmp_path / "main.txt")

        # 嵌套文件的相对路径相对于引用它的文件解析; 约束文件中的 -r 引入的是普通依赖 (与 pip 一致)
        assert [entry.name for entry in parsed.entries] == ["torch", "nested", "deepest", "extra-req", "last"]
        assert [(entry.name, entry.constraint) for entry in parsed.constraints] == [("numpy", True)]
        assert [Path(path).name for path in parsed.includes] == ["more.txt", "deeper.txt", "cons.txt", "from-constraint.txt"]
        assert parsed.entries[2].source.path.endswith("deeper.txt")
        assert parsed.diagnostics == []
        assert parsed.path == str(tmp_path / "main.txt")

    def test_constraint_restrictions(self, tmp_path):
        _make_project(tmp_path / "proj")
        (tmp_path / "cons.txt").write_text("numpy<2\n-e ./proj\npkg[extra]==1\ngit+https://example.com/x.git\nok @ https://example.com/ok-1.0.tar.gz\n", encoding="utf-8")
        parsed = parse_requirements_file(tmp_path / "cons.txt", constraint=True)
        assert [entry.name for entry in parsed.constraints] == ["numpy", "ok"]
        assert parsed.entries == []
        assert len(parsed.errors) == 3

    def test_cycle_is_reported(self, tmp_path):
        (tmp_path / "a.txt").write_text("one\n-r b.txt\n", encoding="utf-8")
        (tmp_path / "b.txt").write_text("two\n-r a.txt\n", encoding="utf-8")

        parsed = parse_requirements_file(tmp_path / "a.txt")
        assert [entry.name for entry in parsed.entries] == ["one", "two"]
        assert len(parsed.errors) == 1
        assert "a.txt" in parsed.errors[0].message and "b.txt" in parsed.errors[0].message

        with pytest.raises(RecursiveInclude):
            parse_requirements_file(tmp_path / "a.txt", strict=True)

    def test_missing_nested_file(self, tmp_path):
        (tmp_path / "main.txt").write_text("-r nope.txt\nnumpy\n", encoding="utf-8")
        parsed = parse_requirements_file(tmp_path / "main.txt")
        assert [entry.name for entry in parsed.entries] == ["numpy"]
        assert [(diagnostic.severity, diagnostic.lineno) for diagnostic in parsed.diagnostics] == [("error", 1)]
        with pytest.raises(NestedFileNotFound):
            parse_requirements_file(tmp_path / "main.txt", strict=True)

    def test_missing_root_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_requirements_file(tmp_path / "missing.txt")

    def test_remote_nested_file_is_not_fetched(self, tmp_path):
        parsed = _parse("-r https://example.com/requirements.txt\nnumpy\n", tmp_path, strict=True)
        assert [entry.name for entry in parsed.entries] == ["numpy"]
        assert [diagnostic.severity for diagnostic in parsed.diagnostics] == ["warning"]

    def test_follow_includes_can_be_disabled(self, tmp_path):
        (tmp_path / "other.txt").write_text("other\n", encoding="utf-8")
        parsed = _parse("-r other.txt\nnumpy\n", tmp_path, follow_includes=False)
        assert [entry.name for entry in parsed.entries] == ["numpy"]
        assert parsed.includes == []

    def test_relative_paths_default_to_root_file_directory(self, tmp_path):
        _make_project(tmp_path / "proj")
        (tmp_path / "sub").mkdir()
        (tmp_path / "main.txt").write_text("-r sub/more.txt\n", encoding="utf-8")
        (tmp_path / "sub" / "more.txt").write_text("-e ./proj\n", encoding="utf-8")
        parsed = parse_requirements_file(tmp_path / "main.txt")
        assert parsed.entries[0].path == tmp_path / "proj"
        assert parsed.entries[0].name == "Local_Proj"


# ============================================================================
# 本地项目元数据与 TOML 解析器
# ============================================================================


class TestLocalProject:
    @pytest.mark.parametrize(
        ("url_path", "windows", "expected"),
        [
            ("/workspace/demo%20pkg/req.txt", False, "/workspace/demo pkg/req.txt"),
            ("/C:/Users/demo%20pkg/req.txt", True, "C:\\Users\\demo pkg\\req.txt"),
            ("/C|/Users/demo", True, "C:\\Users\\demo"),
            ("//server/share/req.txt", True, "\\\\server\\share\\req.txt"),
            ("/relative/root", True, "\\relative\\root"),
        ],
    )
    def test_file_url_path_to_local_path(self, url_path, windows, expected):
        assert file_url_path_to_local_path(url_path, windows=windows) == expected

    def test_reads_static_name_from_pyproject(self, tmp_path):
        _make_project(tmp_path, "My.Project")
        assert is_installable_dir(tmp_path) is True
        assert get_local_project_name(tmp_path) == "My.Project"

    def test_dynamic_name_is_unknown(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[project]\ndynamic = ["name", "version"]\n', encoding="utf-8")
        assert get_local_project_name(tmp_path) is None

    def test_falls_back_to_setup_cfg(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text('[build-system]\nrequires = ["setuptools"]\n', encoding="utf-8")
        (tmp_path / "setup.cfg").write_text("[metadata]\nname = cfg-name\n", encoding="utf-8")
        assert get_local_project_name(tmp_path) == "cfg-name"

    def test_setup_cfg_directive_is_unknown(self, tmp_path):
        (tmp_path / "setup.cfg").write_text("[metadata]\nname = attr: pkg.__name__\n", encoding="utf-8")
        assert get_local_project_name(tmp_path) is None

    def test_broken_pyproject_is_not_fatal(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project\nname = ", encoding="utf-8")
        assert get_local_project_name(tmp_path) is None
        (tmp_path / "setup.py").write_text("", encoding="utf-8")
        assert is_installable_dir(tmp_path) is True
        assert is_installable_dir(tmp_path / "nope") is False

    def test_uses_builtin_tomllib_when_available(self):
        if sys.version_info >= (3, 11):
            import tomllib

            assert local_project.tomllib is tomllib
        else:
            assert local_project.tomllib is toml_parser

    @pytest.mark.skipif(sys.version_info < (3, 11), reason="需要标准库 tomllib 作为对照")
    def test_project_toml_parser_matches_tomllib(self):
        import tomllib

        document = (
            '[build-system]\nrequires = ["setuptools>=61", "wheel"]\nbuild-backend = "setuptools.build_meta"\n\n'
            '[project]\nname = "demo-pkg"\ndynamic = ["version"]\nrequires-python = ">=3.10"\n'
            'dependencies = [\n    "requests>=2",\n    \'tomli; python_version < "3.11"\',\n]\n\n'
            '[project.optional-dependencies]\ndev = ["pytest", "ruff"]\n\n'
            '[dependency-groups]\ntest = ["pytest", {include-group = "lint"}]\nlint = ["ruff"]\n\n'
            '[tool.setuptools.dynamic]\nversion = {attr = "demo.__version__"}\n'
        )
        assert toml_parser.loads(document) == tomllib.loads(document)
        assert toml_parser.load(io.BytesIO(document.encode("utf-8"))) == tomllib.loads(document)


# ============================================================================
# ComfyUI 环境分析使用的软件包声明列表
# ============================================================================


class TestRequirementDeclarations:
    def test_declarations_cover_file_syntax(self, tmp_path):
        requirement = tmp_path / "requirements.txt"
        requirement.write_text(
            "\n".join(
                [
                    "Torch==2.3.*",
                    "diffusers[torch]==0.33.1",
                    "protobuf>=4.25.3, \\",
                    "    <5",
                    "triton-windows<3.4 # skip_verify",
                    "never; python_version < '0'",
                    "git+https://github.com/user/repo.git@main#egg=RealName",
                    "git+https://gitlab.example/group/subgroup/Fancy-Package.git@main",
                    "git+ssh://git@github.com:user/sshrepo.git@main",
                    "https://example.test/packages/demo_pkg-1.2.3-py3-none-any.whl",
                    "direct @ https://example.com/direct-1.0.tar.gz",
                    "https://example.com/foo-1.0.tar.gz",
                    "invalid !!!",
                    "--pre",
                    "--extra-index-url=https://x/simple",
                    "numpy",
                    "",
                ]
            ),
            encoding="utf-8-sig",
        )

        assert read_requirement_declarations(requirement) == [
            "torch==2.3.*",
            "diffusers==0.33.1",
            "protobuf>=4.25.3,<5",
            "realname",
            "fancy-package",
            "sshrepo",
            "demo_pkg==1.2.3",
            "direct",
            "numpy",
        ]

    def test_declarations_follow_nested_files_and_editables(self, tmp_path):
        _make_project(tmp_path / "proj")
        (tmp_path / "main.txt").write_text("torch==2.3.0\n-r more.txt\n-c cons.txt\n-e ./proj\n-e .\n", encoding="utf-8")
        (tmp_path / "more.txt").write_text("numpy<2\n", encoding="utf-8")
        (tmp_path / "cons.txt").write_text("scipy<2\n", encoding="utf-8")
        # 约束条目不是依赖; 无法确定软件包名的 "-e ." 只产生警告
        assert read_requirement_declarations(tmp_path / "main.txt") == ["torch==2.3.0", "numpy<2", "local_proj"]

    def test_declarations_raise_for_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_requirement_declarations(tmp_path / "missing.txt")


# ============================================================================
# 与 pip 对照
# ============================================================================


class TestPipOracle:
    """以 pip 自身的依赖文件解析器作为对照, pip 内部接口不可用时跳过"""

    def test_lines_match_pip(self, tmp_path, monkeypatch):
        req_file = pytest.importorskip("pip._internal.req.req_file")
        session_module = pytest.importorskip("pip._internal.network.session")
        monkeypatch.setenv("REQ_HOST", "h.example")
        monkeypatch.delenv("REQ_UNDEFINED", raising=False)

        (tmp_path / "sub").mkdir()
        (tmp_path / "main.txt").write_text(
            "\n".join(
                [
                    "# comment",
                    'torch==2.3.* ; sys_platform != "nope"   # trailing comment',
                    "requests[security] >= 2.8.1, \\",
                    "    < 3 --hash=sha256:abc --hash sha256:def",
                    "-e ./proj[dev]",
                    "--editable=other",
                    "./demo-1.0-py3-none-any.whl",
                    "git+https://github.com/user/Repo.git@main#egg=RealName&subdirectory=src",
                    "https://example.com/pkgs/demo_pkg-1.2.3-py3-none-any.whl#sha256=deadbeef",
                    "pkg @ https://${REQ_HOST}/${REQ_UNDEFINED}/pkg-1.0-py3-none-any.whl",
                    "-r sub/more.txt",
                    "-c cons.txt",
                    "--index-url https://a/simple --extra-index-url=https://b/simple",
                    "-f https://links --pre --no-binary :all:",
                    "last  ",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (tmp_path / "sub" / "more.txt").write_text("nested>=1\n-r deeper.txt\n", encoding="utf-8")
        (tmp_path / "sub" / "deeper.txt").write_text("deepest # note\n", encoding="utf-8")
        (tmp_path / "cons.txt").write_text("numpy<2\n-r from-constraint.txt\n", encoding="utf-8")
        (tmp_path / "from-constraint.txt").write_text("extra-req\n", encoding="utf-8")

        def pip_hashes(item):
            hashes = (item.options or {}).get("hashes") or {}
            return sorted(f"{algorithm}:{digest}" for algorithm, digests in hashes.items() for digest in digests)

        expected = sorted(
            (item.requirement, item.is_editable, item.constraint, pip_hashes(item)) for item in req_file.parse_requirements(str(tmp_path / "main.txt"), session=session_module.PipSession())
        )

        parsed = parse_requirements_file(tmp_path / "main.txt")
        actual = sorted((entry.raw, entry.editable, entry.constraint, sorted(entry.hashes) if entry.kind == EntryKind.NAMED else []) for entry in [*parsed.entries, *parsed.constraints])

        assert actual == expected
        assert parsed.errors == []
