"""依赖满足状态检查测试

在临时目录中构造 ``.dist-info`` 元数据来模拟已安装的软件包.
"""

import json

import pytest

from sd_webui_all_in_one.package_analyzer import checker
from sd_webui_all_in_one.package_analyzer.checker import (
    CheckStatus,
    check_entry,
    check_requirement,
    check_requirements_file,
)
from sd_webui_all_in_one.package_analyzer.installed import (
    InstalledDistribution,
    get_installed_distribution,
    get_package_version_from_library,
)
from sd_webui_all_in_one.package_analyzer.reqfile import (
    parse_requirements_file,
    parse_requirements_text,
)
from sd_webui_all_in_one.package_analyzer.requirement import Requirement


@pytest.fixture
def site(tmp_path, monkeypatch):
    """返回用于安装模拟软件包的函数, 软件包安装在仅对当前测试可见的目录中"""
    site_dir = tmp_path / "site-packages"
    site_dir.mkdir()
    monkeypatch.syspath_prepend(str(site_dir))

    def install(name, version, requires=(), direct_url=None):
        dist_info = site_dir / f"{name.replace('-', '_')}-{version}.dist-info"
        dist_info.mkdir()
        lines = ["Metadata-Version: 2.1", f"Name: {name}", f"Version: {version}"]
        lines += [f"Requires-Dist: {requirement}" for requirement in requires]
        (dist_info / "METADATA").write_text("\n".join(lines) + "\n", encoding="utf-8")
        if direct_url is not None:
            (dist_info / "direct_url.json").write_text(json.dumps(direct_url), encoding="utf-8")
        return dist_info

    return install


def _check(text, **kwargs):
    return check_requirement(Requirement.parse(text), **kwargs)


def _entries(text, tmp_path):
    return parse_requirements_text(text, base_dir=tmp_path, environ={})


# ============================================================================
# 已安装分发
# ============================================================================


class TestInstalled:
    def test_lookup_normalizes_name(self, site):
        site("Demo_Check.Pkg", "1.2.3")
        for spelling in ("demo-check-pkg", "Demo_Check.Pkg", "DEMO.CHECK_PKG"):
            installed = get_installed_distribution(spelling)
            assert installed is not None and installed.version == "1.2.3"
        assert get_installed_distribution("sdaio-not-installed-pkg") is None
        assert get_installed_distribution("  ") is None
        assert get_package_version_from_library("demo_check.pkg") == "1.2.3"
        assert get_package_version_from_library("sdaio-not-installed-pkg") is None
        assert get_package_version_from_library("") is None

    def test_direct_url_and_requires(self, site):
        site("sdaio-plain", "1.0", requires=["sdaio-dep>=1"])
        site("sdaio-editable", "0.1", direct_url={"url": "file:///src/proj", "dir_info": {"editable": True}})
        plain = get_installed_distribution("sdaio-plain")
        editable = get_installed_distribution("sdaio-editable")
        assert plain.direct_url is None and plain.editable is False
        assert plain.requires == ["sdaio-dep>=1"]
        assert editable.direct_url["url"] == "file:///src/proj"
        assert editable.editable is True

    def test_corrupt_direct_url_is_ignored(self, site):
        dist_info = site("sdaio-corrupt", "1.0")
        (dist_info / "direct_url.json").write_text("{not json", encoding="utf-8")
        assert get_installed_distribution("sdaio-corrupt").direct_url is None


# ============================================================================
# 依赖声明检查
# ============================================================================


class TestCheckRequirement:
    def test_version_constraints(self, site):
        site("sdaio-demo", "1.4.2")
        assert _check("sdaio-demo").status == CheckStatus.SATISFIED
        assert _check("SDAIO_Demo>=1.0,<2").status == CheckStatus.SATISFIED
        assert _check("sdaio-demo==1.4.*").status == CheckStatus.SATISFIED
        assert _check("sdaio-demo~=1.4").status == CheckStatus.SATISFIED
        result = _check("sdaio-demo>=2.0")
        assert result.status == CheckStatus.UNSATISFIED
        assert "1.4.2" in result.reason
        assert result.ok is False

    def test_not_installed(self, site):
        result = _check("sdaio-not-installed-pkg>=1")
        assert result.status == CheckStatus.UNSATISFIED
        assert result.reason == "未安装"

    def test_marker_not_applicable_is_skipped(self, site):
        result = _check('sdaio-not-installed-pkg; sys_platform == "no-such-platform"')
        assert result.status == CheckStatus.SKIPPED
        assert result.ok is True
        assert _check('sdaio-not-installed-pkg; sys_platform == "win32"', environment={"sys_platform": "win32"}).status == CheckStatus.UNSATISFIED

    def test_installed_prerelease_and_local_version(self, site):
        site("sdaio-pre", "2.0.0rc1")
        site("sdaio-local", "2.3.0+cu118")
        assert _check("sdaio-pre>=1.0").status == CheckStatus.SATISFIED
        assert _check("sdaio-local==2.3.0").status == CheckStatus.SATISFIED
        assert _check("sdaio-local==2.3.0+cu118").status == CheckStatus.SATISFIED
        assert _check("sdaio-local==2.3.0+cu121").status == CheckStatus.UNSATISFIED
        assert _check("sdaio-local>2.3.0").status == CheckStatus.UNSATISFIED

    def test_installed_version_that_is_not_pep440(self, site):
        site("sdaio-legacy", "legacy-build")
        assert _check("sdaio-legacy").status == CheckStatus.SATISFIED
        assert _check("sdaio-legacy>=1.0").status == CheckStatus.UNSATISFIED
        assert _check("sdaio-legacy===legacy-build").status == CheckStatus.SATISFIED

    def test_extras_dependencies_are_checked(self, site):
        site(
            "sdaio-main",
            "1.0",
            requires=[
                "sdaio-base>=1",
                'sdaio-gpu-dep>=2.0 ; extra == "gpu"',
                'sdaio-win-only ; extra == "gpu" and sys_platform == "no-such-platform"',
                'sdaio-ui-dep ; extra == "ui"',
            ],
        )
        # 无条件依赖不在 extras 检查范围内, 因此 sdaio-base 未安装不影响结果
        assert _check("sdaio-main").status == CheckStatus.SATISFIED

        result = _check("sdaio-main[gpu]")
        assert result.status == CheckStatus.UNSATISFIED
        assert "sdaio-gpu-dep" in result.reason

        site("sdaio-gpu-dep", "1.0")
        assert _check("sdaio-main[gpu]").status == CheckStatus.UNSATISFIED

        assert _check("sdaio-main[ui]").status == CheckStatus.UNSATISFIED
        # 未提供的 extra 不引入任何依赖
        assert _check("sdaio-main[unknown]").status == CheckStatus.SATISFIED

    def test_extras_satisfied_and_cyclic(self, site):
        site("sdaio-a", "1.0", requires=['sdaio-b[x] ; extra == "x"'])
        site("sdaio-b", "1.0", requires=['sdaio-a[x] ; extra == "x"'])
        assert _check("sdaio-a[X]").status == CheckStatus.SATISFIED

    def test_direct_reference(self, site):
        site("sdaio-url", "1.0", direct_url={"url": "https://example.com/pkgs/sdaio_url-1.0.tar.gz", "archive_info": {}})
        site("sdaio-index", "1.0")
        assert _check("sdaio-url @ https://example.com/pkgs/sdaio_url-1.0.tar.gz").status == CheckStatus.SATISFIED
        # 已安装但来源无法确认: 无法验证, 按已满足处理
        for text in ("sdaio-url @ https://other.example/sdaio_url-1.0.tar.gz", "sdaio-index @ https://example.com/sdaio_index-1.0.tar.gz"):
            result = _check(text)
            assert result.status == CheckStatus.UNKNOWN
            assert result.ok is True
        assert _check("sdaio-not-installed-pkg @ https://example.com/x.tar.gz").status == CheckStatus.UNSATISFIED

    def test_name_alias(self):
        installed = {"SAM-2": InstalledDistribution("SAM-2", "1.0")}
        assert _check("sam2", lookup=installed.get).status == CheckStatus.SATISFIED
        assert _check("sam3", lookup=installed.get).status == CheckStatus.UNSATISFIED


# ============================================================================
# 依赖文件条目检查
# ============================================================================


class TestCheckEntry:
    def test_skip_verify_and_marker(self, site, tmp_path):
        parsed = _entries('sdaio-not-installed-pkg # skip_verify\nsdaio-not-installed-pkg; sys_platform == "no-such-platform"\n', tmp_path)
        assert [check_entry(entry).status for entry in parsed.entries] == [CheckStatus.SKIPPED, CheckStatus.SKIPPED]

    def test_editable_and_local_path(self, site, tmp_path):
        project = tmp_path / "proj"
        project.mkdir()
        (project / "pyproject.toml").write_text('[project]\nname = "sdaio-local-proj"\nversion = "0.1"\n', encoding="utf-8")
        parsed = _entries("-e ./proj\n./proj\n", tmp_path)
        editable, plain = parsed.entries

        assert check_entry(editable).status == CheckStatus.UNSATISFIED

        site("sdaio-local-proj", "0.1", direct_url={"url": project.as_uri(), "dir_info": {"editable": True}})
        assert check_entry(editable).status == CheckStatus.SATISFIED
        # 以可编辑模式安装, 而条目为普通本地路径: 来源不一致, 无法验证
        assert check_entry(plain).status == CheckStatus.UNKNOWN

    def test_editable_installed_from_elsewhere_is_unknown(self, site, tmp_path):
        project = tmp_path / "proj"
        project.mkdir()
        (project / "pyproject.toml").write_text('[project]\nname = "sdaio-moved"\n', encoding="utf-8")
        site("sdaio-moved", "0.1", direct_url={"url": (tmp_path / "elsewhere").as_uri(), "dir_info": {"editable": True}})
        (entry,) = _entries("-e ./proj\n", tmp_path).entries
        assert check_entry(entry).status == CheckStatus.UNKNOWN

    def test_entry_without_name_is_unknown(self, site, tmp_path):
        parsed = _entries("-e .\n./missing.tar.gz\nhttps://example.com/foo-1.0.tar.gz\ngit+https://example.com/user/repo.git\n", tmp_path)
        results = [check_entry(entry) for entry in parsed.entries]
        assert [result.status for result in results] == [CheckStatus.UNKNOWN] * 4
        assert all(result.ok for result in results)
        assert str(results[0]).startswith("<string>:1: -e .")

    def test_wheel_url_compares_version(self, site, tmp_path):
        site("sdaio-wheel", "1.2.3")
        parsed = _entries(
            "https://example.com/sdaio_wheel-1.2.3-py3-none-any.whl\nhttps://example.com/sdaio_wheel-1.3.0-py3-none-any.whl\nhttps://example.com/sdaio_absent-1.0-py3-none-any.whl\n",
            tmp_path,
        )
        assert [check_entry(entry).status for entry in parsed.entries] == [CheckStatus.SATISFIED, CheckStatus.UNSATISFIED, CheckStatus.UNSATISFIED]

    def test_vcs_url_compares_recorded_origin(self, site, tmp_path):
        site(
            "sdaio-vcs",
            "0.5",
            direct_url={"url": "https://github.com/user/sdaio-vcs.git", "vcs_info": {"vcs": "git", "requested_revision": "main", "commit_id": "abcdef1234567890"}},
        )
        parsed = _entries(
            "\n".join(
                [
                    "git+https://token@github.com/user/sdaio-vcs.git@main#egg=sdaio-vcs",
                    "git+https://github.com/user/sdaio-vcs@abcdef1#egg=sdaio-vcs",
                    "git+https://github.com/user/sdaio-vcs.git#egg=sdaio-vcs",
                    "git+https://github.com/user/sdaio-vcs.git@v2#egg=sdaio-vcs",
                    "git+https://github.com/fork/sdaio-vcs.git#egg=sdaio-vcs",
                    "git+https://github.com/user/absent.git#egg=sdaio-absent",
                ]
            ),
            tmp_path,
        )
        assert [check_entry(entry).status for entry in parsed.entries] == [
            CheckStatus.SATISFIED,
            CheckStatus.SATISFIED,
            CheckStatus.SATISFIED,
            CheckStatus.UNKNOWN,
            CheckStatus.UNKNOWN,
            CheckStatus.UNSATISFIED,
        ]

    def test_constraints_only_apply_to_installed_packages(self, site, tmp_path):
        site("sdaio-pinned", "2.0")
        (tmp_path / "main.txt").write_text("-c cons.txt\n", encoding="utf-8")
        (tmp_path / "cons.txt").write_text("sdaio-pinned<2\nsdaio-not-installed-pkg<2\n", encoding="utf-8")
        results = check_requirements_file(parse_requirements_file(tmp_path / "main.txt"))
        assert [result.status for result in results] == [CheckStatus.UNSATISFIED, CheckStatus.SKIPPED]


# ============================================================================
# 字符串接口
# ============================================================================


class TestStringInterface:
    def test_is_package_installed(self, site):
        site("sdaio-demo", "1.4.2", requires=['sdaio-extra-dep ; extra == "gpu"'])
        assert checker.is_package_installed("sdaio-demo>=1.0,<2") is True
        assert checker.is_package_installed("sdaio-demo>=2") is False
        assert checker.is_package_installed("sdaio-demo[gpu]") is False
        assert checker.is_package_installed("sdaio-not-installed-pkg") is False
        assert checker.is_package_installed('sdaio-not-installed-pkg; sys_platform == "no-such-platform"') is True
        assert checker.is_package_installed("sdaio-demo @ https://example.com/sdaio_demo-1.4.2.tar.gz") is True
        assert checker.is_package_installed("sdaio-demo==not_a_version") is False

    def test_validate_requirements_with_options_and_unverifiable_entries(self, site, tmp_path):
        site("sdaio-demo", "1.4.2")
        requirement = tmp_path / "requirements.txt"
        (tmp_path / "more.txt").write_text("sdaio-demo~=1.4\n", encoding="utf-8")
        requirement.write_text(
            "\n".join(
                [
                    "--extra-index-url https://example.com/simple",
                    "--pre",
                    "sdaio-demo==1.4.*",
                    "-r more.txt",
                    "-e .",
                    "invalid !!!",
                    "sdaio-not-installed-pkg # skip_verify",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        # "-e ." 无法验证, "invalid !!!" 无法解析: 均只产生警告, 不视为缺失依赖
        assert checker.validate_requirements(requirement) is True

        requirement.write_text("sdaio-demo==1.4.*\n-r more.txt\n-e .\nsdaio-not-installed-pkg\n", encoding="utf-8")
        assert checker.validate_requirements(requirement) is False

    def test_validate_requirements_follows_nested_file(self, site, tmp_path):
        site("sdaio-demo", "1.4.2")
        (tmp_path / "requirements.txt").write_text("sdaio-demo\n-r more.txt\n", encoding="utf-8")
        (tmp_path / "more.txt").write_text("sdaio-not-installed-pkg\n", encoding="utf-8")
        assert checker.validate_requirements(tmp_path / "requirements.txt") is False

    def test_validate_requirements_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            checker.validate_requirements(tmp_path / "missing.txt")
