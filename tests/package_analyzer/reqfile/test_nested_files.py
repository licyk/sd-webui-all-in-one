"""嵌套依赖文件与约束文件测试"""

from pathlib import Path

import pytest

from sd_webui_all_in_one.package_analyzer.errors import (
    NestedFileNotFound,
    RecursiveInclude,
)
from sd_webui_all_in_one.package_analyzer.reqfile import (
    parse_requirements_file,
)
from tests.package_analyzer.reqfile.helpers import make_project, parse_lines


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
        make_project(tmp_path / "proj")
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
        parsed = parse_lines("-r https://example.com/requirements.txt\nnumpy\n", tmp_path, strict=True)
        assert [entry.name for entry in parsed.entries] == ["numpy"]
        assert [diagnostic.severity for diagnostic in parsed.diagnostics] == ["warning"]

    def test_follow_includes_can_be_disabled(self, tmp_path):
        (tmp_path / "other.txt").write_text("other\n", encoding="utf-8")
        parsed = parse_lines("-r other.txt\nnumpy\n", tmp_path, follow_includes=False)
        assert [entry.name for entry in parsed.entries] == ["numpy"]
        assert parsed.includes == []

    def test_relative_paths_default_to_root_file_directory(self, tmp_path):
        make_project(tmp_path / "proj")
        (tmp_path / "sub").mkdir()
        (tmp_path / "main.txt").write_text("-r sub/more.txt\n", encoding="utf-8")
        (tmp_path / "sub" / "more.txt").write_text("-e ./proj\n", encoding="utf-8")
        parsed = parse_requirements_file(tmp_path / "main.txt")
        assert parsed.entries[0].path == tmp_path / "proj"
        assert parsed.entries[0].name == "Local_Proj"
