"""依赖文件条目解析测试"""

import pytest

from sd_webui_all_in_one.package_analyzer.errors import (
    RequirementsFileError,
    UnsupportedOption,
)
from sd_webui_all_in_one.package_analyzer.reqfile import (
    EntryKind,
)
from sd_webui_all_in_one.package_analyzer.version import Version
from tests.package_analyzer.reqfile.helpers import make_project, parse_lines


# ============================================================================
# 条目分类
# ============================================================================
class TestEntries:
    def test_named_requirement_with_hashes(self, tmp_path):
        parsed = parse_lines("requests[security] >= 2.8.1, \\\n    < 3 --hash=sha256:abc --hash sha256:def\n", tmp_path)
        (entry,) = parsed.entries
        assert entry.kind == EntryKind.NAMED
        assert entry.name == "requests"
        assert entry.extras == ("security",)
        assert str(entry.requirement) == "requests[security]>=2.8.1,<3"
        assert entry.hashes == ("sha256:abc", "sha256:def")
        assert entry.source.lineno == 1
        assert parsed.diagnostics == []

    def test_wildcard_and_non_canonical_versions_are_kept(self, tmp_path):
        parsed = parse_lines("torch==2.3.*\nbar==1.0-1\nbaz==2.3.0+CU118\n", tmp_path)
        assert [str(entry.requirement) for entry in parsed.entries] == ["torch==2.3.*", "bar==1.0-1", "baz==2.3.0+CU118"]
        assert parsed.entries[1].requirement.specifier.contains("1.0.post1")

    def test_marker_and_skip_verify_directive(self, tmp_path):
        parsed = parse_lines('triton-windows<3.4; sys_platform == "win32" # skip_verify\nonnx; sys_platform == "win32"\n', tmp_path)
        first, second = parsed.entries
        assert first.skip_verify is True
        assert second.skip_verify is False
        assert second.applies_to({"sys_platform": "win32"}) is True
        assert second.applies_to({"sys_platform": "linux"}) is False

    def test_direct_reference_with_env_variable(self, tmp_path):
        parsed = parse_lines('pkg @ https://${HOST}/pkg-1.0-py3-none-any.whl ; os_name == "posix"\n', tmp_path, environ={"HOST": "h.example"})
        (entry,) = parsed.entries
        assert entry.kind == EntryKind.NAMED
        assert entry.url == "https://h.example/pkg-1.0-py3-none-any.whl"
        assert str(entry.marker) == 'os_name == "posix"'

    def test_vcs_url_fragments(self, tmp_path):
        parsed = parse_lines("git+https://user:tok@github.com/user/Repo.git@v1.0#egg=RealName[extra]&subdirectory=src\n", tmp_path)
        (entry,) = parsed.entries
        assert entry.kind == EntryKind.URL
        assert entry.name == "RealName"
        assert entry.extras == ("extra",)
        assert entry.vcs == "git"
        assert entry.revision == "v1.0"
        assert entry.subdirectory == "src"

    def test_vcs_url_without_egg_has_no_name(self, tmp_path):
        parsed = parse_lines('git+ssh://git@github.com:user/sshrepo.git@main ; python_version > "3"\n', tmp_path)
        (entry,) = parsed.entries
        assert entry.name is None
        assert entry.revision == "main"
        assert str(entry.marker) == 'python_version > "3"'
        assert parsed.diagnostics == []

    def test_wheel_url_provides_name_version_and_hash(self, tmp_path):
        parsed = parse_lines("https://example.com/pkgs/demo_pkg-1.2.3-py3-none-any.whl#sha256=deadbeef\n", tmp_path)
        (entry,) = parsed.entries
        assert entry.kind == EntryKind.URL
        assert (entry.name, entry.version) == ("demo_pkg", Version.parse("1.2.3"))
        assert entry.hashes == ("sha256:deadbeef",)

    def test_sdist_url_is_kept_without_name(self, tmp_path):
        parsed = parse_lines("https://example.com/foo-1.0.tar.gz\n", tmp_path)
        (entry,) = parsed.entries
        assert entry.kind == EntryKind.URL
        assert entry.name is None
        assert parsed.diagnostics == []

    def test_invalid_wheel_url_is_an_error(self, tmp_path):
        parsed = parse_lines("https://example.com/broken.whl\nnumpy\n", tmp_path)
        assert [entry.name for entry in parsed.entries] == ["numpy"]
        assert len(parsed.errors) == 1

    def test_local_directory_and_editable(self, tmp_path):
        make_project(tmp_path / "proj")
        parsed = parse_lines("./proj\n-e ./proj[dev,test]\n--editable=proj\n", tmp_path)
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
        parsed = parse_lines("-e .\nnumpy\n", tmp_path, strict=True)
        editable, numpy = parsed.entries
        assert editable.kind == EntryKind.PATH
        assert editable.editable is True
        assert editable.name is None
        assert editable.path == tmp_path
        assert numpy.name == "numpy"
        assert [diagnostic.severity for diagnostic in parsed.diagnostics] == ["warning"]

    def test_editable_missing_path_is_a_warning(self, tmp_path):
        parsed = parse_lines("-e ./missing\n", tmp_path, strict=True)
        assert parsed.entries[0].path == tmp_path / "missing"
        assert [diagnostic.severity for diagnostic in parsed.diagnostics] == ["warning"]

    def test_editable_vcs_and_invalid_editable_url(self, tmp_path):
        parsed = parse_lines("-e git+https://github.com/user/pkg.git@main#egg=Pkg-Extra\n-e https://example.com/x.whl\n", tmp_path)
        (entry,) = parsed.entries
        assert (entry.kind, entry.editable, entry.name, entry.vcs) == (EntryKind.URL, True, "Pkg-Extra", "git")
        assert len(parsed.errors) == 1

    def test_local_wheel_and_file_url(self, tmp_path):
        (tmp_path / "demo-1.0-py3-none-any.whl").write_bytes(b"")
        make_project(tmp_path / "proj")
        parsed = parse_lines(f"./demo-1.0-py3-none-any.whl\ndemo-1.0-py3-none-any.whl\n{(tmp_path / 'proj').as_uri()}\n", tmp_path)
        first, second, third = parsed.entries
        assert (first.kind, first.name, first.version) == (EntryKind.PATH, "demo", Version.parse("1.0"))
        assert (second.kind, second.name) == (EntryKind.PATH, "demo")
        assert (third.kind, third.name, third.path) == (EntryKind.PATH, "Local_Proj", tmp_path / "proj")

    def test_plain_name_is_not_mistaken_for_a_directory(self, tmp_path):
        (tmp_path / "requests").mkdir()
        parsed = parse_lines("requests\n", tmp_path)
        assert parsed.entries[0].kind == EntryKind.NAMED

    def test_missing_path_and_invalid_requirement_are_errors(self, tmp_path):
        parsed = parse_lines("./missing-dir\ninvalid !!!\nfoo==1.0 garbage\nbad; python_version >\nnumpy\n", tmp_path)
        assert [entry.name for entry in parsed.entries] == ["numpy"]
        assert [(diagnostic.severity, diagnostic.lineno) for diagnostic in parsed.diagnostics] == [("error", 1), ("error", 2), ("error", 3), ("error", 4)]
        assert "<string>:2" in str(parsed.diagnostics[1])

    def test_strict_mode_raises_on_first_error(self, tmp_path):
        with pytest.raises(RequirementsFileError) as error:
            parse_lines("numpy\ninvalid !!!\n", tmp_path, strict=True)
        assert error.value.lineno == 2
        with pytest.raises(UnsupportedOption):
            parse_lines("--bogus-option x\n", tmp_path, strict=True)
