"""package_analyzer 包名规范测试

参考:
    - https://packaging.python.org/en/latest/specifications/name-normalization/
"""

import pytest

from sd_webui_all_in_one.package_analyzer.errors import (
    PackageAnalyzerError,
)
from sd_webui_all_in_one.package_analyzer.names import (
    is_valid_name,
    normalize_extra,
    normalize_name,
)


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
