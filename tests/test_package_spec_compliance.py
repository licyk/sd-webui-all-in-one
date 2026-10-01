"""package_analyzer 规范符合性测试

覆盖版本标识符规范, 依赖声明规范与分发文件名规范, 并在可用时以 ``packaging`` 库作为对照.

参考:
    - https://packaging.python.org/en/latest/specifications/version-specifiers/
    - https://packaging.python.org/en/latest/specifications/dependency-specifiers/
    - https://packaging.python.org/en/latest/specifications/binary-distribution-format/
"""

import itertools
import random

import pytest

from sd_webui_all_in_one.package_analyzer.errors import (
    InvalidMarker,
    InvalidRequirement,
    InvalidSdistFilename,
    InvalidSpecifier,
    InvalidVersion,
    InvalidWheelFilename,
    PackageAnalyzerError,
    UndefinedEnvironmentName,
)
from sd_webui_all_in_one.package_analyzer.filenames import (
    SdistFilename,
    WheelFilename,
    WheelTag,
    is_archive_filename,
)
from sd_webui_all_in_one.package_analyzer.markers import (
    Marker,
    default_environment,
)
from sd_webui_all_in_one.package_analyzer.names import (
    is_valid_name,
    normalize_extra,
    normalize_name,
)
from sd_webui_all_in_one.package_analyzer.requirement import Requirement
from sd_webui_all_in_one.package_analyzer.specifiers import (
    Specifier,
    SpecifierSet,
)
from sd_webui_all_in_one.package_analyzer.version import Version


VERSION_SAMPLES = [
    "1.0",
    "1.0.0",
    "1",
    "1.1",
    "1.0a1",
    "1.0b2",
    "1.0rc1",
    "1.0.dev1",
    "1.0a1.dev1",
    "1.0.post1",
    "1.0.post1.dev2",
    "1.0+local",
    "1.0+abc.5",
    "1.0+5",
    "1.0+abc",
    "1!0.5",
    "2.3.0+cu118",
    "2.3.0",
    "2.3.1",
    "1.0-1",
    "v1.0",
    "1.0alpha",
    "1.0.0.0",
    "0.9",
    "1.4.5",
    "1.4.6",
    "1.5",
    "2.0",
    "2.0rc1",
    "1.0.post0",
    "1.0+ubuntu-1",
    "1.0C1",
    "1.0_PRE1",
    "1.4.5a4",
    "1.4",
    "1.4.5.post1",
    "2.2.post3",
    "2.2",
    "1.0rc1.post1",
    "1.0a1.post2.dev1",
    "0.9.post1",
    "2.0.dev3",
]

LINUX_ENV = {
    "implementation_name": "cpython",
    "implementation_version": "3.11.9",
    "os_name": "posix",
    "platform_machine": "x86_64",
    "platform_python_implementation": "CPython",
    "platform_release": "6.8.0-111-generic",
    "platform_system": "Linux",
    "platform_version": "#111-Ubuntu SMP PREEMPT_DYNAMIC",
    "python_full_version": "3.11.9",
    "python_version": "3.11",
    "sys_platform": "linux",
}


# ============================================================================
# 名称规范化
# ============================================================================


class TestNames:
    @pytest.mark.parametrize("name", ["a", "A1", "my-package", "my.package", "my_package", "a-._b"])
    def test_valid_names(self, name):
        assert is_valid_name(name) is True

    @pytest.mark.parametrize("name", ["", "-a", "a-", "_a", "a.", "pâckage", "a b", "a/b"])
    def test_invalid_names(self, name):
        assert is_valid_name(name) is False

    def test_normalization_collapses_separators(self):
        assert normalize_name("Friendly-Bard") == "friendly-bard"
        assert normalize_name("FRIENDLY.._--bard") == "friendly-bard"
        assert normalize_extra("Foo_Bar") == "foo-bar"

    def test_normalization_is_idempotent(self):
        for name in ["Typing.Extensions", "a__b", "A-.-B"]:
            assert normalize_name(normalize_name(name)) == normalize_name(name)

    def test_validate_rejects_invalid_name(self):
        with pytest.raises(PackageAnalyzerError):
            normalize_name("-bad", validate=True)


# ============================================================================
# 版本号
# ============================================================================


class TestVersion:
    @pytest.mark.parametrize(
        ("text", "normalized"),
        [
            ("1.0", "1.0"),
            ("v1.0", "1.0"),
            (" 1.0 ", "1.0"),
            ("1.0ALPHA1", "1.0a1"),
            ("1.0-beta.2", "1.0b2"),
            ("1.0c1", "1.0rc1"),
            ("1.0pre", "1.0rc0"),
            ("1.0preview3", "1.0rc3"),
            ("1.0-1", "1.0.post1"),
            ("1.0.post", "1.0.post0"),
            ("1.0-r4", "1.0.post4"),
            ("1.0.rev2", "1.0.post2"),
            ("1.0DEV", "1.0.dev0"),
            ("1!2.0", "1!2.0"),
            ("2.3.0+CU118", "2.3.0+cu118"),
            ("1.0+ubuntu-1_2", "1.0+ubuntu.1.2"),
            ("1.0.0", "1.0.0"),
            ("01.02", "1.2"),
        ],
    )
    def test_normalization(self, text, normalized):
        assert str(Version.parse(text)) == normalized

    @pytest.mark.parametrize("text", ["", "abc", "1.0.", "1..0", "1.0+", "1.0+a..b", "1.0 0", "1.0.*", "1.0a1b2", "not-a-version"])
    def test_invalid_versions(self, text):
        with pytest.raises(InvalidVersion):
            Version.parse(text)
        assert Version.try_parse(text) is None

    def test_ordering_from_specification(self):
        # 版本标识符规范 "Summary of permitted suffixes and relative ordering" 中的排序示例
        ordered = [
            "1.dev0",
            "1.0.dev456",
            "1.0a1",
            "1.0a2.dev456",
            "1.0a12.dev456",
            "1.0a12",
            "1.0b1.dev456",
            "1.0b2",
            "1.0b2.post345.dev456",
            "1.0b2.post345",
            "1.0rc1.dev456",
            "1.0rc1",
            "1.0",
            "1.0+abc.5",
            "1.0+abc.7",
            "1.0+5",
            "1.0.post456.dev34",
            "1.0.post456",
            "1.0.15",
            "1.1.dev1",
        ]
        versions = [Version.parse(text) for text in ordered]
        shuffled = versions[:]
        random.Random(0).shuffle(shuffled)
        assert sorted(shuffled) == versions
        for lower, higher in zip(versions, versions[1:]):
            assert lower < higher

    def test_equality_ignores_trailing_zeros_and_spelling(self):
        assert Version.parse("1.0") == Version.parse("1.0.0") == Version.parse("v1")
        assert hash(Version.parse("1.0")) == hash(Version.parse("1.0.0"))
        assert Version.parse("1.0alpha1") == Version.parse("1.0a1")
        assert Version.parse("1!1.0") > Version.parse("2.0")

    def test_properties(self):
        version = Version.parse("1!2.3rc1.post4.dev5+local.7")
        assert version.epoch == 1
        assert version.release == (2, 3)
        assert version.pre == ("rc", 1)
        assert version.post == 4
        assert version.dev == 5
        assert version.local == "local.7"
        assert version.public == "1!2.3rc1.post4.dev5"
        assert version.base_version == "1!2.3"
        assert version.is_prerelease and version.is_postrelease and version.is_devrelease
        assert Version.parse("1.0.post1").is_prerelease is False
        assert Version.parse("1.0+cu118").without_local() == Version.parse("1.0")

    def test_comparison_with_other_types(self):
        assert Version.parse("1.0") != "1.0"
        with pytest.raises(TypeError):
            _ = Version.parse("1.0") < "2.0"


# ============================================================================
# 版本约束
# ============================================================================


class TestSpecifier:
    @pytest.mark.parametrize(
        "text",
        ["~=1", "~=1.0+local", ">=1.*", "<1.0.*", "~=1.0.*", ">=1.0+local", "<1.0+local", "==1.0a1.*", "==1.0.dev1.*", "==1.0+l.*", "==", ">=abc", "1.0", "=>1.0", "=== a b"],
    )
    def test_invalid_specifiers(self, text):
        with pytest.raises(InvalidSpecifier):
            Specifier.parse(text)

    @pytest.mark.parametrize("text", ["==1.0", "== 1.0", "==1.*", "!=1.0.*", "~=1.0", "~=1.4.5a4", "==1.0+local", "!=1.0+local", "===anything-goes", ">=1!2.0", "<1.0.post1"])
    def test_valid_specifiers(self, text):
        assert Specifier.parse(text) is not None

    @pytest.mark.parametrize(
        ("spec", "version", "expected"),
        [
            # 版本匹配
            ("==1.1", "1.1", True),
            ("==1.1", "1.1.0", True),
            ("==1.1", "1.1.post1", False),
            ("==1.1", "1.1a1", False),
            ("==1.1", "1.1+local", True),
            ("==1.1+local", "1.1", False),
            ("==1.1+local", "1.1+LOCAL", True),
            ("==1.1.*", "1.1.post1", True),
            ("==1.1.*", "1.1a1", True),
            ("==1.1.*", "1.2", False),
            ("==1.*", "1", True),
            ("==2.1.*", "2.1.5+local", True),
            # 版本排除
            ("!=1.1", "1.1", False),
            ("!=1.1", "1.1.post1", True),
            ("!=1.1.*", "1.1.post1", False),
            # 兼容版本
            ("~=2.2", "2.3", True),
            ("~=2.2", "3.0", False),
            ("~=2.2", "2.1", False),
            ("~=1.4.5", "1.4.9", True),
            ("~=1.4.5", "1.5.0", False),
            ("~=2.2.post3", "2.9", True),
            ("~=2.2.post3", "2.2.post2", False),
            ("~=1.4.5a4", "1.4.9", True),
            ("~=1.4.5a4", "1.5", False),
            # 包含性有序比较
            (">=1.0", "1.0+local", True),
            ("<=1.0", "1.0+local", True),
            (">=1.0", "1.0rc1", False),
            # 排他性有序比较
            (">1.7", "1.7.1", True),
            (">1.7", "1.7.0.post1", False),
            (">1.7.post2", "1.7.post3", True),
            (">1.7", "1.7.0+local", False),
            (">1.0rc1", "1.0.post1", True),
            ("<1.7", "1.7rc1", False),
            ("<1.7", "1.6.9", True),
            ("<1.7rc2", "1.7rc1", True),
            ("<1.0.post1", "1.0a1", True),
            ("<1.0.post1", "1.0.post1.dev2", False),
            # 任意相等
            ("===1.0-FOO", "1.0-foo", True),
            ("===1.0", "1.0.0", False),
            ("===legacy-build", "legacy-build", True),
        ],
    )
    def test_matching(self, spec, version, expected):
        assert Specifier.parse(spec).matches(version) is expected

    def test_candidate_that_is_not_a_version_only_matches_arbitrary_equality(self):
        assert Specifier.parse(">=0").matches("not-a-version") is False
        assert Specifier.parse("!=1.0").matches("not-a-version") is False
        assert Specifier.parse("===not-a-version").matches("not-a-version") is True

    def test_specifier_equality_uses_normalized_version(self):
        assert Specifier.parse("==1.0alpha1") == Specifier.parse("== 1.0a1")
        assert Specifier.parse("==1.0") != Specifier.parse(">=1.0")
        assert str(Specifier.parse("== 1.0alpha1")) == "==1.0alpha1"


class TestSpecifierSet:
    def test_comma_is_logical_and(self):
        specs = SpecifierSet.parse(">=4.25.3,<5")
        assert specs.contains("4.26.0") is True
        assert specs.contains("5.0") is False
        assert specs.contains("4.25.2") is False
        assert len(specs) == 2
        assert str(specs) == ">=4.25.3,<5"

    def test_empty_set_matches_everything(self):
        specs = SpecifierSet.parse("")
        assert not specs
        assert specs.contains("0.0.1") is True
        assert specs.contains("1.0rc1") is True

    def test_single_candidate_prerelease_is_accepted_unless_disabled(self):
        specs = SpecifierSet.parse(">=1.0")
        assert specs.contains("2.0rc1") is True
        assert specs.contains("2.0rc1", prereleases=False) is False

    def test_filter_prefers_final_releases(self):
        specs = SpecifierSet.parse(">=1.0")
        assert specs.filter(["0.9", "1.0", "2.0rc1", "2.0"]) == ["1.0", "2.0"]
        # 没有任何正式版本满足约束时才返回预发布版本
        assert specs.filter(["0.9", "2.0rc1"]) == ["2.0rc1"]
        assert specs.filter(["0.9", "2.0rc1"], prereleases=False) == []
        # 约束自身指向预发布版本时允许预发布版本
        assert SpecifierSet.parse(">=1.0rc1").filter(["1.0rc2", "1.0"]) == ["1.0rc2", "1.0"]

    def test_equality_ignores_order(self):
        assert SpecifierSet.parse(">=1,<2") == SpecifierSet.parse("<2, >=1")
        assert hash(SpecifierSet.parse(">=1,<2")) == hash(SpecifierSet.parse("<2,>=1"))

    def test_invalid_member_raises(self):
        with pytest.raises(InvalidSpecifier):
            SpecifierSet.parse(">=1.0,~=1")


# ============================================================================
# 环境标记
# ============================================================================


class TestMarker:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            # String 字段: 区分大小写
            ('sys_platform == "linux"', True),
            ('platform_system == "Linux"', True),
            ('platform_system == "linux"', False),
            ('os_name != "nt"', True),
            ('platform_machine in "x86_64 AMD64"', True),
            ('"SMP" in platform_version', True),
            ('"win" not in sys_platform', True),
            # String 字段的有序比较: >= / <= 等同于 ==, > / < 恒为 False
            ('sys_platform >= "linux"', True),
            ('sys_platform <= "linux"', True),
            ('sys_platform >= "aaa"', False),
            ('sys_platform > "aaa"', False),
            ('sys_platform < "zzz"', False),
            # Version 字段: 按版本比较而不是字符串比较
            ('python_version >= "3.9"', True),
            ('python_version >= "3.10"', True),
            ('python_version < "3.9"', False),
            ('python_version == "3.*"', True),
            ('python_full_version ~= "3.11.0"', True),
            ('python_version in "3.10 3.11"', True),
            ('python_version not in "3.8 3.9"', True),
            ('implementation_version >= "3"', True),
            # Version | String 字段: 无法按版本比较时回退到字符串规则
            ('platform_release >= "5.0"', False),
            ('platform_release == "6.8.0-111-generic"', True),
            # 逻辑运算与优先级
            ('os_name == "nt" or os_name == "posix" and python_version >= "3"', True),
            ('(os_name == "nt" or os_name == "posix") and python_version < "3"', False),
            ('os_name == "nt" and python_version >= "3" or sys_platform == "linux"', True),
            # 旧字段名
            ("os.name == 'posix'", True),
            ("python_implementation == 'CPython'", True),
            # 常量可以位于左侧
            ('"3.9" <= python_version', True),
        ],
    )
    def test_evaluation(self, text, expected):
        assert Marker.parse(text).evaluate(LINUX_ENV) is expected

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "python_version",
            "python_version >=",
            "sys_platform == win32",
            'unknown_field == "x"',
            'python_version >= "3" and',
            'python_version >= "3" extra',
            '(python_version >= "3"',
            "python_version >= '3",
            'python_version notin "3"',
            '"3.4" < python_version < "3.9"',
        ],
    )
    def test_invalid_markers(self, text):
        with pytest.raises(InvalidMarker):
            Marker.parse(text)

    def test_extra_is_normalized_and_must_be_defined(self):
        marker = Marker.parse('extra == "Foo_Bar"')
        assert marker.evaluate({"extra": "foo-bar"}) is True
        assert marker.evaluate({"extra": "FOO.BAR"}) is True
        assert marker.evaluate({"extra": ""}) is False
        with pytest.raises(UndefinedEnvironmentName):
            marker.evaluate()
        assert marker.extra_names() == {"foo-bar"}

    def test_set_fields_only_support_containment(self):
        marker = Marker.parse('"gui" in extras and "dev" not in dependency_groups')
        assert marker.evaluate({"extras": {"GUI"}, "dependency_groups": set()}) is True
        assert marker.evaluate({"extras": set(), "dependency_groups": set()}) is False
        assert Marker.parse('extras == "gui"').evaluate({"extras": {"gui"}}) is False

    def test_marker_keeps_field_names_and_round_trips(self):
        marker = Marker.parse("python_version>='3.8' and (os_name=='nt' or os_name=='posix')")
        assert marker.fields() == {"python_version", "os_name"}
        assert str(marker) == 'python_version >= "3.8" and (os_name == "nt" or os_name == "posix")'
        assert Marker.parse(str(marker)) == marker

    def test_same_marker_evaluates_differently_per_environment(self):
        marker = Marker.parse('sys_platform == "win32"')
        assert marker.evaluate({"sys_platform": "win32"}) is True
        assert marker.evaluate({"sys_platform": "linux"}) is False

    def test_local_python_build_version(self):
        assert Marker.parse('python_full_version >= "3.13"').evaluate({"python_full_version": "3.13.0+"}) is True

    def test_default_environment_has_all_standard_fields(self):
        environment = default_environment()
        assert {"os_name", "sys_platform", "python_version", "python_full_version", "platform_machine"} <= set(environment)
        assert "extra" not in environment


# ============================================================================
# 依赖声明
# ============================================================================


class TestRequirement:
    def test_full_requirement(self):
        requirement = Requirement.parse('requests [security,tests] >= 2.8.1, == 2.8.* ; python_version < "2.7"')
        assert requirement.name == "requests"
        assert requirement.extras == ("security", "tests")
        assert str(requirement.specifier) == ">=2.8.1,==2.8.*"
        assert requirement.url is None
        assert str(requirement.marker) == 'python_version < "2.7"'
        assert str(requirement) == 'requests[security,tests]>=2.8.1,==2.8.*; python_version < "2.7"'

    def test_url_requirement(self):
        requirement = Requirement.parse("pip @ https://github.com/pypa/pip/archive/1.3.1.zip#sha1=da9234 ; os_name == 'posix'")
        assert requirement.name == "pip"
        assert requirement.url == "https://github.com/pypa/pip/archive/1.3.1.zip#sha1=da9234"
        assert not requirement.specifier
        assert str(requirement.marker) == 'os_name == "posix"'

    def test_url_swallows_semicolon_without_whitespace(self):
        requirement = Requirement.parse("a @ https://e.com/a.whl;python_version<'3'")
        assert requirement.url == "https://e.com/a.whl;python_version<'3'"
        assert requirement.marker is None

    @pytest.mark.parametrize(
        "text",
        [
            "A",
            "A.B-C_D",
            "name<=1.0",
            "name>=3,<2",
            "name@http://foo.com",
            "name [fred,bar] @ http://foo.com ; python_version=='2.7'",
            "name[quux, strange];python_version<'2.7' and platform_version=='2'",
            "name; os_name=='a' or os_name=='b'",
            "name; os_name=='a' and os_name=='b' or os_name=='c'",
            "name; os_name=='a' and (os_name=='b' or os_name=='c')",
            "name (>=1.0,<2)",
            "name[]",
            " name   >=  1.0  ,  < 2  ",
            "name===1.0+foo",
            "torch==2.3.0+cu118",
        ],
    )
    def test_valid_requirements_round_trip(self, text):
        requirement = Requirement.parse(text)
        assert Requirement.parse(str(requirement)) == requirement

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "requests>=1.0 garbage here",
            "pâckage>=1.0",
            "-a",
            "a-",
            "a..b==",
            "a~=1",
            "a>=1.*",
            "a>=",
            "a==1.0a1.*",
            "a>=1.0+local",
            "a(>=1.0",
            "a[x,]",
            "a[,x]",
            "a[x y]",
            "a @",
            "a;",
            "a; sys_platform == win32",
            "a; unknown == 'x'",
            "a >= 1.0 # comment",
            "a==1.0 --hash=sha256:abc",
            "a==not_canonical",
        ],
    )
    def test_invalid_requirements(self, text):
        with pytest.raises(InvalidRequirement):
            Requirement.parse(text)

    def test_error_reports_position(self):
        with pytest.raises(InvalidRequirement) as error:
            Requirement.parse("requests>=1.0 garbage")
        assert error.value.position == 14
        assert error.value.text == "requests>=1.0 garbage"
        assert "^" in str(error.value)
        assert isinstance(error.value, ValueError)

    def test_normalized_accessors(self):
        requirement = Requirement.parse("Foo_Bar[Dev_Tools]")
        assert requirement.normalized_name == "foo-bar"
        assert requirement.normalized_extras == {"dev-tools"}

    def test_applies_to_treats_missing_extra_as_not_requested(self):
        assert Requirement.parse("a; extra == 'gpu'").applies_to() is False
        assert Requirement.parse("a; extra == 'gpu'").applies_to({"extra": "gpu"}) is True
        assert Requirement.parse("a").applies_to() is True


# ============================================================================
# 分发文件名
# ============================================================================


class TestFilenames:
    def test_wheel_filename(self):
        wheel = WheelFilename.parse("typing_extensions-4.12.2-py3-none-any.whl")
        assert wheel.distribution == "typing_extensions"
        assert wheel.name == "typing-extensions"
        assert wheel.version == Version.parse("4.12.2")
        assert wheel.build is None
        assert wheel.tags == {WheelTag("py3", "none", "any")}

    def test_wheel_filename_with_build_tag_and_compressed_tags(self):
        wheel = WheelFilename.parse("torch-2.3.0+cu118-1local-cp311.cp312-cp311-manylinux_2_28_x86_64.manylinux2014_x86_64.whl")
        assert wheel.version == Version.parse("2.3.0+cu118")
        assert wheel.build == (1, "local")
        assert len(wheel.tags) == 4
        assert WheelTag("cp312", "cp311", "manylinux2014_x86_64") in wheel.tags

    @pytest.mark.parametrize(
        "filename",
        [
            "not_a_wheel.tar.gz",
            "pkg-1.0.whl",
            "pkg-1.0-py3-none.whl",
            "pkg-1.0-1-2-py3-none-any.whl",
            "pkg-notaversion-py3-none-any.whl",
            "pkg-1.0-build-py3-none-any.whl",
            "bad__name-1.0-py3-none-any.whl",
        ],
    )
    def test_invalid_wheel_filenames(self, filename):
        with pytest.raises(InvalidWheelFilename):
            WheelFilename.parse(filename)

    def test_sdist_filename(self):
        sdist = SdistFilename.parse("my_package-1.0.tar.gz")
        assert sdist.name == "my-package"
        assert sdist.version == Version.parse("1.0")
        assert SdistFilename.parse("old-0.1.zip").distribution == "old"

    @pytest.mark.parametrize("filename", ["pkg-1.0.whl", "pkg.tar.gz", "pkg-main.tar.gz", "-1.0.tar.gz"])
    def test_invalid_sdist_filenames(self, filename):
        with pytest.raises(InvalidSdistFilename):
            SdistFilename.parse(filename)

    def test_archive_detection(self):
        assert is_archive_filename("a-1.0-py3-none-any.whl") is True
        assert is_archive_filename("A-1.0.TAR.GZ") is True
        assert is_archive_filename("requirements.txt") is False


# ============================================================================
# 与 packaging 库对照
# ============================================================================


class TestPackagingOracle:
    """以 packaging 库作为对照, 未安装 packaging 时跳过"""

    # 与 packaging 的已知差异:
    #   - 名称以 '-' / '_' / '.' 结尾时 (如 "a_"), 本实现按规范拒绝, packaging 接受
    #   - 比较表达式两侧均为常量时 (如 '"a" == "a"'), 本实现照常求值, packaging 抛出异常

    def test_version_ordering_and_normalization(self):
        packaging_version = pytest.importorskip("packaging.version")
        for text in VERSION_SAMPLES:
            mine = Version.parse(text)
            theirs = packaging_version.Version(text)
            assert str(mine) == str(theirs)
            assert mine.public == theirs.public
            assert mine.base_version == theirs.base_version
            assert mine.is_prerelease == theirs.is_prerelease
        for left, right in itertools.product(VERSION_SAMPLES, repeat=2):
            assert (Version.parse(left) < Version.parse(right)) == (packaging_version.Version(left) < packaging_version.Version(right)), (left, right)
            assert (Version.parse(left) == Version.parse(right)) == (packaging_version.Version(left) == packaging_version.Version(right)), (left, right)

    def test_specifier_validity_and_matching(self):
        packaging_specifiers = pytest.importorskip("packaging.specifiers")
        operators = ["==", "!=", "~=", ">=", "<=", ">", "<", "==="]
        specs = [operator + version for operator in operators for version in VERSION_SAMPLES]
        specs += [operator + prefix + ".*" for operator in operators for prefix in ["1", "1.0", "1.4", "2", "1!0", "1.0a1", "1.0+l"]]
        for text in specs:
            try:
                mine = Specifier.parse(text)
            except InvalidSpecifier:
                mine = None
            try:
                theirs = packaging_specifiers.Specifier(text)
            except packaging_specifiers.InvalidSpecifier:
                theirs = None
            assert (mine is None) == (theirs is None), text
            if mine is None:
                continue
            for version in VERSION_SAMPLES:
                for prereleases in (None, True, False):
                    assert mine.contains(version, prereleases=prereleases) == theirs.contains(version, prereleases=prereleases), (text, version, prereleases)

    def test_specifier_set_contains_and_filter(self):
        packaging_specifiers = pytest.importorskip("packaging.specifiers")
        operators = ["==", "!=", "~=", ">=", "<=", ">", "<"]
        specs = [operator + version for operator in operators for version in VERSION_SAMPLES if "+" not in version or operator in ("==", "!=")]
        generator = random.Random(20261001)
        for _ in range(400):
            text = ",".join(generator.sample(specs, generator.randint(0, 3)))
            try:
                mine = SpecifierSet.parse(text)
            except InvalidSpecifier:
                mine = None
            try:
                theirs = packaging_specifiers.SpecifierSet(text)
            except packaging_specifiers.InvalidSpecifier:
                theirs = None
            assert (mine is None) == (theirs is None), text
            if mine is None:
                continue
            for version in VERSION_SAMPLES:
                for prereleases in (None, True, False):
                    assert mine.contains(version, prereleases=prereleases) == theirs.contains(version, prereleases=prereleases), (text, version, prereleases)
            assert [str(version) for version in mine.filter(VERSION_SAMPLES)] == list(theirs.filter(VERSION_SAMPLES)), text

    def test_requirement_parsing_and_marker_evaluation(self):
        packaging_requirements = pytest.importorskip("packaging.requirements")
        cases = [
            "requests",
            'requests [security,tests] >= 2.8.1, == 2.8.* ; python_version < "2.7"',
            "name@http://foo.com",
            "name [fred,bar] @ http://foo.com ; python_version=='2.7'",
            "name[quux, strange];python_version<'2.7' and platform_version=='2'",
            "name; os_name=='a' and os_name=='b' or os_name=='c'",
            "name; (os_name=='a' or os_name=='b') and os_name=='c'",
            "requests>=1.0 garbage here",
            "pâckage>=1.0",
            "a; sys_platform == win32",
            "a; os.name == 'nt'",
            "a @ https://e.com/a.whl;python_version<'3'",
            "a~=1",
            "a>=1.*",
            "a==1.0.*,!=1.0.3",
            "a (>=1.0,<2)",
            "a(>=1.0",
            "a[x,]",
            "a..b",
            "a>=1.0+local",
            "a; python_version",
            'a; "3" <= python_version',
            'a; python_version >= "3" and',
            'a; extra == "Foo_Bar"',
            "a; 'x' in extras",
            'a; python_version in "3.10 3.11"',
            "a; python_version not  in '3.10'",
            'a; python_full_version ~= "3.11.0"',
            'a; platform_release >= "5.0"',
            'a; sys_platform >= "linux"',
            'a; sys_platform > "a"',
            'a; platform_system == "linux"',
            'a; python_version == "3.*"',
            'a; python_version >= "abc"',
            'a; unknown_field == "x"',
            "torch == 2.3.0 ; platform_machine != 'aarch64' and sys_platform == 'linux'",
            "name >= 1.0 # comment",
            "name==1.0 --hash=sha256:abc",
        ]
        environment = {"extra": "foo-bar", "extras": {"x"}, "dependency_groups": set()}
        for text in cases:
            try:
                mine = Requirement.parse(text)
            except InvalidRequirement:
                mine = None
            try:
                theirs = packaging_requirements.Requirement(text)
            except packaging_requirements.InvalidRequirement:
                theirs = None
            assert (mine is None) == (theirs is None), text
            if mine is None:
                continue
            assert mine.name == theirs.name, text
            assert set(mine.extras) == theirs.extras, text
            assert mine.url == theirs.url, text
            assert {str(spec) for spec in mine.specifier} == {str(spec) for spec in theirs.specifier}, text
            assert (mine.marker is None) == (theirs.marker is None), text
            if mine.marker is not None:
                assert mine.marker.evaluate(environment) == theirs.marker.evaluate(environment), text
