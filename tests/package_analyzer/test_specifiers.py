"""package_analyzer 版本约束规范测试

参考:
    - https://packaging.python.org/en/latest/specifications/version-specifiers/
"""

import pytest

from sd_webui_all_in_one.package_analyzer.errors import (
    InvalidSpecifier,
)
from sd_webui_all_in_one.package_analyzer.specifiers import (
    Specifier,
    SpecifierSet,
)


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
