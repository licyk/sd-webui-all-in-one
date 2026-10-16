"""package_analyzer 版本标识符规范测试

参考:
    - https://packaging.python.org/en/latest/specifications/version-specifiers/
"""

import random

import pytest

from sd_webui_all_in_one.package_analyzer.errors import (
    InvalidVersion,
)
from sd_webui_all_in_one.package_analyzer.version import Version


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
