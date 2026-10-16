"""本地项目名称识别测试"""

import io
import sys

import pytest

from sd_webui_all_in_one import toml_parser
from sd_webui_all_in_one.package_analyzer import local_project
from sd_webui_all_in_one.package_analyzer.local_project import (
    file_url_path_to_local_path,
    get_local_project_name,
    is_installable_dir,
)
from tests.package_analyzer.reqfile.helpers import make_project


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
        make_project(tmp_path, "My.Project")
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
