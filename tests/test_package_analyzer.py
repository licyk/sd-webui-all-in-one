"""package_analyzer 通用版本比较器测试

版本标识符规范, 依赖声明规范的测试见 ``test_package_spec_compliance.py``.
"""

from sd_webui_all_in_one.package_analyzer.ver_cmp import (
    CommonVersionComparison,
    version_increment,
    version_decrement,
)


# ============================================================================
# CommonVersionComparison 测试
# ============================================================================


class TestCommonVersionComparison:
    def test_basic_comparison(self):
        assert CommonVersionComparison("1.0") < CommonVersionComparison("1.1")
        assert CommonVersionComparison("1.1") > CommonVersionComparison("1.0")
        assert CommonVersionComparison("1.0") == CommonVersionComparison("1.0")
        assert CommonVersionComparison("1.0") != CommonVersionComparison("1.1")

    def test_pre_release_less_than_final(self):
        assert CommonVersionComparison("1.0a") < CommonVersionComparison("1.0")


# ============================================================================
# version_increment / version_decrement 测试
# ============================================================================


class TestVersionIncrementDecrement:
    def test_increment_simple(self):
        assert version_increment("1.0.0") == "1.0.1"

    def test_increment_no_carry(self):
        # 不再进位: 1.0.9 -> 1.0.10 (不是 1.1.0)
        assert version_increment("1.0.9") == "1.0.10"

    def test_increment_large_number(self):
        assert version_increment("1.0.15") == "1.0.16"
        assert version_increment("1.0.99") == "1.0.100"

    def test_decrement_simple(self):
        assert version_decrement("1.0.1") == "1.0.0"

    def test_decrement_no_borrow(self):
        # 不再借位: 1.1.0 -> 1.1.-1 (调用者应处理边界)
        assert version_decrement("1.1.0") == "1.1.-1"

    def test_decrement_large_number(self):
        assert version_decrement("1.0.15") == "1.0.14"
        assert version_decrement("1.0.100") == "1.0.99"
