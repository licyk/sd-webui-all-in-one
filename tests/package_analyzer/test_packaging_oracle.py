"""package_analyzer 与 ``packaging`` 库的对照测试 (``packaging`` 不可用时跳过)"""

import itertools
import random

import pytest

from sd_webui_all_in_one.package_analyzer.errors import (
    InvalidRequirement,
    InvalidSpecifier,
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
