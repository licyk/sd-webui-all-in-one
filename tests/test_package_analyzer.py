"""package_analyzer 模块测试

基于 PEP 440 和 PEP 508 规范编写的测试用例.
"""

import pytest

from sd_webui_all_in_one.package_analyzer.py_ver_cmp import (
    PyWhlVersionComparison,
    PyWhlVersionComponent,
)
from sd_webui_all_in_one.package_analyzer.py_whl_parse import (
    RequirementParser,
    get_parse_bindings,
)
from sd_webui_all_in_one.package_analyzer.installation_checker import (
    _parse_package_spec,
    _split_package_spec,
    _check_version_constraint,
)
from sd_webui_all_in_one.package_analyzer.requirement_parser import (
    parse_requirement,
    evaluate_marker,
    parse_requirement_to_list,
)
from sd_webui_all_in_one.package_analyzer.version_utils import (
    version_string_is_canonical,
    is_package_has_version,
    get_package_name,
    get_package_version,
    remove_optional_dependence_from_package,
)
from sd_webui_all_in_one.package_analyzer.wheel_parser import (
    parse_wheel_filename,
    parse_wheel_version,
    parse_wheel_to_package_name,
)
from sd_webui_all_in_one.package_analyzer.ver_cmp import (
    CommonVersionComparison,
    version_increment,
    version_decrement,
)


# ============================================================================
# PEP 440: 版本解析测试
# ============================================================================


class TestPEP440VersionParsing:
    """PEP 440 版本号解析测试"""

    def test_simple_release(self):
        cmp = PyWhlVersionComparison("1.0")
        v = cmp.parse_version("1.0")
        assert v.epoch == 0
        assert v.release == (1, 0)
        assert v.pre_l is None
        assert v.post_n is None
        assert v.dev_n is None
        assert v.local is None

    def test_three_component_release(self):
        cmp = PyWhlVersionComparison("1.2.3")
        v = cmp.parse_version("1.2.3")
        assert v.release == (1, 2, 3)

    def test_epoch(self):
        cmp = PyWhlVersionComparison("1!1.0")
        v = cmp.parse_version("1!1.0")
        assert v.epoch == 1
        assert v.release == (1, 0)

    def test_pre_release_alpha(self):
        cmp = PyWhlVersionComparison("1.0a1")
        v = cmp.parse_version("1.0a1")
        assert v.pre_l == "a"
        assert v.pre_n == 1

    def test_pre_release_beta(self):
        cmp = PyWhlVersionComparison("1.0b2")
        v = cmp.parse_version("1.0b2")
        assert v.pre_l == "b"
        assert v.pre_n == 2

    def test_pre_release_rc(self):
        cmp = PyWhlVersionComparison("1.0rc1")
        v = cmp.parse_version("1.0rc1")
        assert v.pre_l == "rc"
        assert v.pre_n == 1

    def test_pre_release_normalization_alpha(self):
        cmp = PyWhlVersionComparison("1.0")
        v = cmp.parse_version("1.0alpha1")
        assert v.pre_l == "a"

    def test_pre_release_normalization_c(self):
        cmp = PyWhlVersionComparison("1.0")
        v = cmp.parse_version("1.0c1")
        assert v.pre_l == "rc"

    def test_pre_release_normalization_preview(self):
        cmp = PyWhlVersionComparison("1.0")
        v = cmp.parse_version("1.0preview1")
        assert v.pre_l == "rc"

    def test_implicit_pre_release_number(self):
        cmp = PyWhlVersionComparison("1.0")
        v = cmp.parse_version("1.2a")
        assert v.pre_l == "a"
        assert v.pre_n == 0

    def test_post_release(self):
        cmp = PyWhlVersionComparison("1.0")
        v = cmp.parse_version("1.0.post1")
        assert v.post_n == 1

    def test_implicit_post_release(self):
        cmp = PyWhlVersionComparison("1.0")
        v = cmp.parse_version("1.0-1")
        assert v.post_n == 1

    def test_implicit_post_release_number(self):
        cmp = PyWhlVersionComparison("1.0")
        v = cmp.parse_version("1.0.post")
        assert v.post_n == 0

    def test_dev_release(self):
        cmp = PyWhlVersionComparison("1.0")
        v = cmp.parse_version("1.0.dev1")
        assert v.dev_n == 1

    def test_implicit_dev_release_number(self):
        cmp = PyWhlVersionComparison("1.0")
        v = cmp.parse_version("1.0.dev")
        assert v.dev_n == 0

    def test_local_version(self):
        cmp = PyWhlVersionComparison("1.0")
        v = cmp.parse_version("1.0+local1")
        assert v.local == "local1"

    def test_local_version_normalization(self):
        cmp = PyWhlVersionComparison("1.0")
        v = cmp.parse_version("1.0+ubuntu-1")
        assert v.local == "ubuntu.1"
        v2 = cmp.parse_version("1.0+ubuntu_1")
        assert v2.local == "ubuntu.1"

    def test_preceding_v(self):
        cmp = PyWhlVersionComparison("1.0")
        v = cmp.parse_version("v1.0")
        assert v.release == (1, 0)

    def test_wildcard_detection(self):
        cmp = PyWhlVersionComparison("1.0")
        v = cmp.parse_version("1.0.*")
        assert v.is_wildcard is True
        assert v.release == (1, 0)

    def test_invalid_version_raises(self):
        cmp = PyWhlVersionComparison("1.0")
        with pytest.raises(ValueError):
            cmp.parse_version("not_a_version!")


# ============================================================================
# PEP 440: 版本排序测试
# ============================================================================


class TestPEP440VersionOrdering:
    """排序规则: .devN < aN < bN < rcN < <no suffix> < .postN"""

    def test_dev_less_than_alpha(self):
        assert PyWhlVersionComparison("1.0.dev1") < PyWhlVersionComparison("1.0a1")

    def test_alpha_less_than_beta(self):
        assert PyWhlVersionComparison("1.0a1") < PyWhlVersionComparison("1.0b1")

    def test_beta_less_than_rc(self):
        assert PyWhlVersionComparison("1.0b1") < PyWhlVersionComparison("1.0rc1")

    def test_rc_less_than_final(self):
        assert PyWhlVersionComparison("1.0rc1") < PyWhlVersionComparison("1.0")

    def test_final_less_than_post(self):
        assert PyWhlVersionComparison("1.0") < PyWhlVersionComparison("1.0.post1")

    def test_epoch_ordering(self):
        assert PyWhlVersionComparison("1!1.0") > PyWhlVersionComparison("2014.04")

    def test_release_zero_padding(self):
        assert PyWhlVersionComparison("1.0") == PyWhlVersionComparison("1.0.0")

    def test_local_version_ordering(self):
        cmp = PyWhlVersionComparison("1.0")
        assert cmp.compare_versions("1.0", "1.0+local1") < 0

    def test_pep440_full_ordering(self):
        versions = [
            "1.0.dev456", "1.0a1", "1.0a2.dev456", "1.0a12.dev456",
            "1.0a12", "1.0b1.dev456", "1.0b2", "1.0b2.post345.dev456",
            "1.0b2.post345", "1.0rc1.dev456", "1.0rc1", "1.0",
            "1.0.post456.dev34", "1.0.post456", "1.1.dev1",
        ]
        cmp = PyWhlVersionComparison("1.0")
        for i in range(len(versions) - 1):
            result = cmp.compare_versions(versions[i], versions[i + 1])
            assert result < 0, f"{versions[i]} should be < {versions[i+1]}"


# ============================================================================
# PEP 440: == 操作符测试
# ============================================================================


class TestPEP440VersionMatching:
    def test_exact_match(self):
        cmp = PyWhlVersionComparison("1.1")
        assert cmp.version_match("1.1", "1.1") is True

    def test_exact_match_zero_padding(self):
        cmp = PyWhlVersionComparison("1.1")
        assert cmp.version_match("1.1.0", "1.1") is True
        assert cmp.version_match("1.1", "1.1.0") is True

    def test_exact_match_not_equal(self):
        cmp = PyWhlVersionComparison("1.1")
        assert cmp.version_match("1.1", "1.1.post1") is False
        assert cmp.version_match("1.1", "1.1a1") is False
        assert cmp.version_match("1.1", "1.1.dev1") is False

    def test_wildcard_match(self):
        cmp = PyWhlVersionComparison("1.1")
        assert cmp.version_match("1.1.*", "1.1") is True
        assert cmp.version_match("1.1.*", "1.1.0") is True
        assert cmp.version_match("1.1.*", "1.1.1") is True
        assert cmp.version_match("1.1.*", "1.1a1") is True
        assert cmp.version_match("1.1.*", "1.1.post1") is True

    def test_wildcard_no_match(self):
        cmp = PyWhlVersionComparison("1.1")
        assert cmp.version_match("1.1.*", "1.2") is False
        assert cmp.version_match("1.1.*", "1.0") is False

    def test_local_version_ignored_when_spec_public(self):
        cmp = PyWhlVersionComparison("1.0")
        assert cmp.version_match("1.0", "1.0+local1") is True
        assert cmp.version_match("1.0", "1.0+ubuntu.1") is True

    def test_local_version_strict_when_spec_local(self):
        cmp = PyWhlVersionComparison("1.0")
        assert cmp.version_match("1.0+local1", "1.0+local1") is True
        assert cmp.version_match("1.0+local1", "1.0+local2") is False
        assert cmp.version_match("1.0+local1", "1.0") is False

    def test_post_release_match(self):
        cmp = PyWhlVersionComparison("1.0")
        assert cmp.version_match("1.1", "1.1.post1") is False
        assert cmp.version_match("1.1.post1", "1.1.post1") is True
        assert cmp.version_match("1.1.*", "1.1.post1") is True


# ============================================================================
# PEP 440: != 操作符测试
# ============================================================================


class TestPEP440VersionExclusion:
    def test_not_equal_basic(self):
        cmp = PyWhlVersionComparison("1.1.post1")
        assert _check_version_constraint("1.1.post1", "!=", "1.1", cmp) is True
        assert _check_version_constraint("1.1.post1", "!=", "1.1.post1", cmp) is False

    def test_not_equal_wildcard(self):
        cmp = PyWhlVersionComparison("1.1.post1")
        assert _check_version_constraint("1.1.post1", "!=", "1.1.*", cmp) is False
        cmp2 = PyWhlVersionComparison("1.2")
        assert _check_version_constraint("1.2", "!=", "1.1.*", cmp2) is True


# ============================================================================
# PEP 440: ~= 操作符测试
# ============================================================================


class TestPEP440CompatibleRelease:
    def test_compatible_two_segment(self):
        cmp = PyWhlVersionComparison("1.0")
        matcher = cmp.compatible_version_matcher("2.2")
        assert matcher("2.2") is True
        assert matcher("2.3") is True
        assert matcher("3.0") is False
        assert matcher("2.1") is False

    def test_compatible_three_segment(self):
        cmp = PyWhlVersionComparison("1.0")
        matcher = cmp.compatible_version_matcher("1.4.5")
        assert matcher("1.4.5") is True
        assert matcher("1.4.6") is True
        assert matcher("1.5.0") is False
        assert matcher("1.4.4") is False

    def test_compatible_with_suffix(self):
        cmp = PyWhlVersionComparison("1.0")
        matcher = cmp.compatible_version_matcher("2.2.post3")
        assert matcher("2.2.post3") is True
        assert matcher("2.3") is True
        assert matcher("3.0") is False

    def test_compatible_single_segment_raises(self):
        cmp = PyWhlVersionComparison("1.0")
        with pytest.raises(ValueError):
            cmp.compatible_version_matcher("1")


# ============================================================================
# PEP 440: 有序比较测试
# ============================================================================


class TestPEP440OrderedComparison:
    def test_ordered_comparison_ignores_local(self):
        cmp = PyWhlVersionComparison("1.0")
        assert cmp.compare_versions("1.0+local1", "1.0", ignore_local=True) == 0
        assert cmp.compare_versions("1.0", "1.0+local1", ignore_local=True) == 0

    def test_ge_with_check_constraint(self):
        cmp = PyWhlVersionComparison("1.5+local1")
        assert _check_version_constraint("1.5+local1", ">=", "1.5", cmp) is True

    def test_le_with_check_constraint(self):
        cmp = PyWhlVersionComparison("1.5+local1")
        assert _check_version_constraint("1.5+local1", "<=", "1.5", cmp) is True


# ============================================================================
# PEP 440: 排他性比较测试 (>, <)
# ============================================================================


class TestPEP440ExclusiveComparison:
    def test_gt_basic(self):
        cmp = PyWhlVersionComparison("1.0")
        assert cmp.exclusive_gt("1.7.1", "1.7") is True
        assert cmp.exclusive_gt("2.0", "1.7") is True
        assert cmp.exclusive_gt("1.7", "1.7") is False
        assert cmp.exclusive_gt("1.6", "1.7") is False

    def test_gt_must_not_allow_post_release(self):
        cmp = PyWhlVersionComparison("1.0")
        assert cmp.exclusive_gt("1.7.0.post1", "1.7") is False
        assert cmp.exclusive_gt("1.7.1", "1.7") is True

    def test_gt_post_release_spec(self):
        cmp = PyWhlVersionComparison("1.0")
        assert cmp.exclusive_gt("1.7.0.post3", "1.7.0.post2") is True
        assert cmp.exclusive_gt("1.7.1", "1.7.0.post2") is True
        assert cmp.exclusive_gt("1.7.0", "1.7.0.post2") is False

    def test_gt_must_not_match_local_version(self):
        cmp = PyWhlVersionComparison("1.0")
        assert cmp.exclusive_gt("1.7+local1", "1.7") is False

    def test_lt_basic(self):
        cmp = PyWhlVersionComparison("1.0")
        assert cmp.exclusive_lt("1.6", "1.7") is True
        assert cmp.exclusive_lt("1.7", "1.7") is False
        assert cmp.exclusive_lt("1.8", "1.7") is False

    def test_lt_must_not_allow_pre_release(self):
        cmp = PyWhlVersionComparison("1.0")
        assert cmp.exclusive_lt("1.7a1", "1.7") is False
        assert cmp.exclusive_lt("1.7.dev1", "1.7") is False
        assert cmp.exclusive_lt("1.6.9", "1.7") is True

    def test_lt_pre_release_spec(self):
        cmp = PyWhlVersionComparison("1.0")
        assert cmp.exclusive_lt("1.7a1", "1.7rc1") is True
        assert cmp.exclusive_lt("1.7b1", "1.7rc1") is True


# ============================================================================
# PEP 440: === 操作符测试
# ============================================================================


class TestPEP440ArbitraryEquality:
    def test_arbitrary_equality(self):
        cmp = PyWhlVersionComparison("1.0")
        assert _check_version_constraint("1.0", "===", "1.0", cmp) is True
        assert _check_version_constraint("1.0", "===", "1.0.0", cmp) is False

    def test_arbitrary_equality_case_insensitive(self):
        cmp = PyWhlVersionComparison("FooBar")
        assert _check_version_constraint("FooBar", "===", "foobar", cmp) is True


# ============================================================================
# 多版本约束测试
# ============================================================================


class TestMultipleVersionConstraints:
    def test_parse_multiple_constraints(self):
        name, specs, is_url = _parse_package_spec("requests>=2.0,<3.0")
        assert name == "requests"
        assert len(specs) == 2
        assert (">=", "2.0") in specs
        assert ("<", "3.0") in specs

    def test_parse_single_constraint(self):
        name, specs, is_url = _parse_package_spec("numpy>=1.20")
        assert name == "numpy"
        assert len(specs) == 1

    def test_parse_no_constraint(self):
        name, specs, is_url = _parse_package_spec("numpy")
        assert name == "numpy"
        assert len(specs) == 0

    def test_parse_url_dependency(self):
        name, specs, is_url = _parse_package_spec(
            "pip @ https://github.com/pypa/pip/archive/1.3.1.zip"
        )
        assert name == "pip"
        assert is_url is True

    def test_split_package_spec_backward_compat(self):
        name, op, ver = _split_package_spec("requests>=2.0,<3.0")
        assert name == "requests"
        assert op == ">="
        assert ver == "2.0"


# ============================================================================
# PEP 508: 依赖声明解析测试
# ============================================================================


class TestPEP508RequirementParsing:
    def test_simple_name(self):
        bindings = get_parse_bindings()
        result = parse_requirement("requests", bindings)
        assert result.name == "requests"
        assert result.extras == []
        assert result.specifier == []

    def test_name_with_version(self):
        bindings = get_parse_bindings()
        result = parse_requirement("requests>=2.8.1", bindings)
        assert result.name == "requests"
        assert (">=", "2.8.1") in result.specifier

    def test_name_with_extras(self):
        bindings = get_parse_bindings()
        result = parse_requirement("requests[security]", bindings)
        assert result.name == "requests"
        assert "security" in result.extras

    def test_name_with_multiple_versions(self):
        bindings = get_parse_bindings()
        result = parse_requirement("protobuf<5,>=4.25.3", bindings)
        assert result.name == "protobuf"
        assert len(result.specifier) == 2

    def test_url_dependency(self):
        bindings = get_parse_bindings()
        result = parse_requirement(
            "pip @ https://github.com/pypa/pip/archive/1.3.1.zip", bindings
        )
        assert result.name == "pip"
        assert isinstance(result.specifier, str)

    def test_name_with_marker(self):
        bindings = get_parse_bindings()
        result = parse_requirement(
            "argparse;python_version<'2.7'", bindings
        )
        assert result.name == "argparse"
        assert result.marker is not None


# ============================================================================
# PEP 508: 标识符解析测试
# ============================================================================


class TestPEP508IdentifierParsing:
    def test_valid_identifier(self):
        parser = RequirementParser("requests")
        name = parser.parse_identifier()
        assert name == "requests"

    def test_identifier_with_hyphens(self):
        parser = RequirementParser("my-package")
        name = parser.parse_identifier()
        assert name == "my-package"

    def test_identifier_with_dots(self):
        parser = RequirementParser("my.package")
        name = parser.parse_identifier()
        assert name == "my.package"

    def test_identifier_must_start_with_alnum(self):
        parser = RequirementParser("-invalid")
        with pytest.raises(ValueError):
            parser.parse_identifier()

    def test_identifier_must_end_with_alnum(self):
        parser = RequirementParser("valid->=1.0")
        name = parser.parse_identifier()
        # 应该在 '-' 处停止, 因为后面跟的不是 alnum
        assert name == "valid"


# ============================================================================
# PEP 508: Marker 表达式测试
# ============================================================================


class TestPEP508MarkerEvaluation:
    def test_marker_none(self):
        assert evaluate_marker(None) is True

    def test_marker_simple_comparison(self):
        marker = ("==", "3.10", "3.10")
        assert evaluate_marker(marker) is True

    def test_marker_and(self):
        marker = ("and", ("==", "a", "a"), ("==", "b", "b"))
        assert evaluate_marker(marker) is True
        marker2 = ("and", ("==", "a", "a"), ("==", "b", "c"))
        assert evaluate_marker(marker2) is False

    def test_marker_or(self):
        marker = ("or", ("==", "a", "b"), ("==", "c", "c"))
        assert evaluate_marker(marker) is True
        marker2 = ("or", ("==", "a", "b"), ("==", "c", "d"))
        assert evaluate_marker(marker2) is False

    def test_marker_in(self):
        marker = ("in", "linux", "linux2")
        assert evaluate_marker(marker) is True

    def test_marker_not_in(self):
        marker = ("not in", "win", "linux2")
        assert evaluate_marker(marker) is True


# ============================================================================
# parse_requirement_to_list 测试
# ============================================================================


class TestParseRequirementToList:
    def test_single_constraint(self):
        result = parse_requirement_to_list("torch==2.3.0")
        assert result == ["torch==2.3.0"]

    def test_multiple_constraints(self):
        result = parse_requirement_to_list("protobuf<5,>=4.25.3")
        assert "protobuf<5" in result
        assert "protobuf>=4.25.3" in result

    def test_no_constraint(self):
        result = parse_requirement_to_list("numpy")
        assert result == ["numpy"]

    def test_marker_false_returns_empty(self):
        # 使用一个永远为 False 的 marker
        result = parse_requirement_to_list("pkg;python_version=='0.0'")
        assert result == []


# ============================================================================
# version_utils 测试
# ============================================================================


class TestVersionUtils:
    def test_canonical_version(self):
        assert version_string_is_canonical("1.0") is True
        assert version_string_is_canonical("1.0a1") is True
        assert version_string_is_canonical("1.0.post1") is True
        assert version_string_is_canonical("1.0.dev1") is True
        assert version_string_is_canonical("1.0+local1") is True

    def test_non_canonical_version(self):
        assert version_string_is_canonical("1.0alpha1") is False
        assert version_string_is_canonical("1.0-1") is False
        assert version_string_is_canonical("v1.0") is False

    def test_is_package_has_version(self):
        assert is_package_has_version("torch==2.3.0") is True
        assert is_package_has_version("numpy>=1.20") is True
        assert is_package_has_version("requests") is False

    def test_get_package_name(self):
        assert get_package_name("torch==2.3.0") == "torch"
        assert get_package_name("requests[security]>=2.0") == "requests"
        assert get_package_name("numpy") == "numpy"

    def test_get_package_version(self):
        assert get_package_version("torch==2.3.0") == "2.3.0"
        assert get_package_version("requests>=2.0") == "2.0"

    def test_remove_optional_dependence(self):
        assert remove_optional_dependence_from_package("diffusers[torch]==0.10.2") == "diffusers==0.10.2"
        assert remove_optional_dependence_from_package("requests") == "requests"


# ============================================================================
# Wheel 文件名解析测试
# ============================================================================


class TestWheelParser:
    def test_parse_wheel_filename(self):
        assert parse_wheel_filename("pydantic-1.10.15-py3-none-any.whl") == "pydantic"

    def test_parse_wheel_version(self):
        assert parse_wheel_version("pydantic-1.10.15-py3-none-any.whl") == "1.10.15"

    def test_parse_wheel_to_package_name(self):
        assert parse_wheel_to_package_name("pydantic-1.10.15-py3-none-any.whl") == "pydantic==1.10.15"

    def test_invalid_wheel_raises(self):
        with pytest.raises(ValueError):
            parse_wheel_filename("not_a_wheel.tar.gz")


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
