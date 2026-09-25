"""冲突依赖检测算法测试

测试 comfyui_env_analyze.py 中的冲突检测函数:
- _is_constraint_pair_conflicting: 单对约束冲突检测
- detect_conflict_package: 两个包声明之间的冲突检测
- detect_conflict_package_from_list: 包列表中的冲突检测
"""

from sd_webui_all_in_one.env_check.comfyui_env_analyze import (
    _is_constraint_pair_conflicting,
    detect_conflict_package,
    detect_conflict_package_from_list,
    normalize_package_name,
)


# ============================================================================
# _is_constraint_pair_conflicting: 单对约束冲突检测
# ============================================================================


class TestConstraintPairConflicting:
    """测试两个单独版本约束条件之间的冲突检测"""

    # --- == vs == ---

    def test_eq_eq_same_version(self):
        """==1.0 vs ==1.0: 不冲突"""
        assert _is_constraint_pair_conflicting("==", "1.0", "==", "1.0") is False

    def test_eq_eq_different_version(self):
        """==1.0 vs ==2.0: 冲突"""
        assert _is_constraint_pair_conflicting("==", "1.0", "==", "2.0") is True

    def test_eq_eq_zero_padded(self):
        """==1.0 vs ==1.0.0: 不冲突 (PEP 440 零填充)"""
        assert _is_constraint_pair_conflicting("==", "1.0", "==", "1.0.0") is False

    # --- == vs >= ---

    def test_eq_ge_satisfied(self):
        """==2.0 vs >=1.0: 不冲突"""
        assert _is_constraint_pair_conflicting("==", "2.0", ">=", "1.0") is False

    def test_eq_ge_conflict(self):
        """==1.0 vs >=2.0: 冲突"""
        assert _is_constraint_pair_conflicting("==", "1.0", ">=", "2.0") is True

    def test_eq_ge_boundary(self):
        """==2.0 vs >=2.0: 不冲突"""
        assert _is_constraint_pair_conflicting("==", "2.0", ">=", "2.0") is False

    # --- == vs > ---

    def test_eq_gt_conflict(self):
        """==1.0 vs >1.0: 冲突"""
        assert _is_constraint_pair_conflicting("==", "1.0", ">", "1.0") is True

    def test_eq_gt_satisfied(self):
        """==2.0 vs >1.0: 不冲突"""
        assert _is_constraint_pair_conflicting("==", "2.0", ">", "1.0") is False

    # --- == vs <= ---

    def test_eq_le_satisfied(self):
        """==1.0 vs <=2.0: 不冲突"""
        assert _is_constraint_pair_conflicting("==", "1.0", "<=", "2.0") is False

    def test_eq_le_conflict(self):
        """==3.0 vs <=2.0: 冲突"""
        assert _is_constraint_pair_conflicting("==", "3.0", "<=", "2.0") is True

    def test_eq_le_boundary(self):
        """==2.0 vs <=2.0: 不冲突"""
        assert _is_constraint_pair_conflicting("==", "2.0", "<=", "2.0") is False

    # --- == vs < ---

    def test_eq_lt_conflict(self):
        """==2.0 vs <2.0: 冲突"""
        assert _is_constraint_pair_conflicting("==", "2.0", "<", "2.0") is True

    def test_eq_lt_satisfied(self):
        """==1.0 vs <2.0: 不冲突"""
        assert _is_constraint_pair_conflicting("==", "1.0", "<", "2.0") is False

    # --- == vs != ---

    def test_eq_ne_conflict(self):
        """==1.0 vs !=1.0: 冲突"""
        assert _is_constraint_pair_conflicting("==", "1.0", "!=", "1.0") is True

    def test_eq_ne_satisfied(self):
        """==1.0 vs !=2.0: 不冲突"""
        assert _is_constraint_pair_conflicting("==", "1.0", "!=", "2.0") is False

    # --- >= vs <= ---

    def test_ge_le_no_conflict(self):
        """>= 1.0 vs <= 2.0: 不冲突"""
        assert _is_constraint_pair_conflicting(">=", "1.0", "<=", "2.0") is False

    def test_ge_le_boundary(self):
        """>= 2.0 vs <= 2.0: 不冲突 (交集为 {2.0})"""
        assert _is_constraint_pair_conflicting(">=", "2.0", "<=", "2.0") is False

    def test_ge_le_conflict(self):
        """>= 3.0 vs <= 2.0: 冲突"""
        assert _is_constraint_pair_conflicting(">=", "3.0", "<=", "2.0") is True

    # --- >= vs < ---

    def test_ge_lt_no_conflict(self):
        """>= 1.0 vs < 2.0: 不冲突"""
        assert _is_constraint_pair_conflicting(">=", "1.0", "<", "2.0") is False

    def test_ge_lt_conflict(self):
        """>= 2.0 vs < 2.0: 冲突"""
        assert _is_constraint_pair_conflicting(">=", "2.0", "<", "2.0") is True

    def test_ge_lt_conflict_greater(self):
        """>= 3.0 vs < 2.0: 冲突"""
        assert _is_constraint_pair_conflicting(">=", "3.0", "<", "2.0") is True

    # --- > vs <= ---

    def test_gt_le_no_conflict(self):
        """> 1.0 vs <= 2.0: 不冲突"""
        assert _is_constraint_pair_conflicting(">", "1.0", "<=", "2.0") is False

    def test_gt_le_conflict(self):
        """> 2.0 vs <= 2.0: 冲突"""
        assert _is_constraint_pair_conflicting(">", "2.0", "<=", "2.0") is True

    # --- > vs < ---

    def test_gt_lt_no_conflict(self):
        """> 1.0 vs < 3.0: 不冲突"""
        assert _is_constraint_pair_conflicting(">", "1.0", "<", "3.0") is False

    def test_gt_lt_conflict_equal(self):
        """> 2.0 vs < 2.0: 冲突"""
        assert _is_constraint_pair_conflicting(">", "2.0", "<", "2.0") is True

    def test_gt_lt_conflict_reversed(self):
        """> 3.0 vs < 2.0: 冲突"""
        assert _is_constraint_pair_conflicting(">", "3.0", "<", "2.0") is True

    # --- 同方向约束不冲突 ---

    def test_ge_ge_no_conflict(self):
        """>= 1.0 vs >= 2.0: 不冲突"""
        assert _is_constraint_pair_conflicting(">=", "1.0", ">=", "2.0") is False

    def test_le_le_no_conflict(self):
        """<= 1.0 vs <= 2.0: 不冲突"""
        assert _is_constraint_pair_conflicting("<=", "1.0", "<=", "2.0") is False

    def test_gt_gt_no_conflict(self):
        """> 1.0 vs > 2.0: 不冲突"""
        assert _is_constraint_pair_conflicting(">", "1.0", ">", "2.0") is False

    def test_lt_lt_no_conflict(self):
        """< 1.0 vs < 2.0: 不冲突"""
        assert _is_constraint_pair_conflicting("<", "1.0", "<", "2.0") is False

    # --- != 约束 ---

    def test_ne_ge_no_conflict(self):
        """!= 1.0 vs >= 2.0: 不冲突"""
        assert _is_constraint_pair_conflicting("!=", "1.0", ">=", "2.0") is False

    def test_ne_ne_no_conflict(self):
        """!= 1.0 vs != 2.0: 不冲突"""
        assert _is_constraint_pair_conflicting("!=", "1.0", "!=", "2.0") is False

    # --- ~= 约束 ---

    def test_compatible_ge_no_conflict(self):
        """~= 1.4 vs >= 1.0: 不冲突"""
        assert _is_constraint_pair_conflicting("~=", "1.4", ">=", "1.0") is False

    def test_compatible_ge_conflict(self):
        """~= 1.4 vs >= 2.0: 冲突 (~= 1.4 的上界是 < 2.0, 而 >= 2.0 要求 >= 2.0)"""
        assert _is_constraint_pair_conflicting("~=", "1.4", ">=", "2.0") is True

    def test_compatible_lt_no_conflict(self):
        """~= 1.4 vs < 2.0: 不冲突"""
        assert _is_constraint_pair_conflicting("~=", "1.4", "<", "2.0") is False

    def test_compatible_lt_conflict(self):
        """~= 1.4 vs < 1.0: 冲突 (~= 1.4 要求 >= 1.4, 而 < 1.0 要求 < 1.0)"""
        assert _is_constraint_pair_conflicting("~=", "1.4", "<", "1.0") is True

    def test_compatible_eq_satisfied(self):
        """~= 1.4 vs == 1.5: 不冲突"""
        assert _is_constraint_pair_conflicting("~=", "1.4", "==", "1.5") is False

    def test_compatible_eq_conflict(self):
        """~= 1.4 vs == 1.3: 冲突 (~= 1.4 要求 >= 1.4)"""
        assert _is_constraint_pair_conflicting("~=", "1.4", "==", "1.3") is True

    def test_compatible_eq_conflict_major(self):
        """~= 1.4 vs == 2.0: 冲突 (~= 1.4 要求 == 1.*)"""
        assert _is_constraint_pair_conflicting("~=", "1.4", "==", "2.0") is True

    # --- === 约束 ---

    def test_arbitrary_eq_same(self):
        """=== 1.0 vs === 1.0: 不冲突"""
        assert _is_constraint_pair_conflicting("===", "1.0", "===", "1.0") is False

    def test_arbitrary_eq_different(self):
        """=== 1.0 vs === 2.0: 冲突"""
        assert _is_constraint_pair_conflicting("===", "1.0", "===", "2.0") is True

    # --- 对称性测试 ---

    def test_symmetry_lt_ge(self):
        """< 2.0 vs >= 3.0: 冲突 (反向也应冲突)"""
        assert _is_constraint_pair_conflicting("<", "2.0", ">=", "3.0") is True

    def test_symmetry_le_gt(self):
        """<= 2.0 vs > 2.0: 冲突"""
        assert _is_constraint_pair_conflicting("<=", "2.0", ">", "2.0") is True


# ============================================================================
# detect_conflict_package: 两个包声明之间的冲突检测
# ============================================================================


class TestDetectConflictPackage:
    """测试两个包声明之间的冲突检测"""

    def test_no_conflict_compatible_ranges(self):
        """torch>=1.0 vs torch<=2.0: 不冲突"""
        assert detect_conflict_package("torch>=1.0", "torch<=2.0") is False

    def test_conflict_incompatible_ranges(self):
        """torch>=3.0 vs torch<=2.0: 冲突"""
        assert detect_conflict_package("torch>=3.0", "torch<=2.0") is True

    def test_conflict_exact_versions(self):
        """numpy==1.24.0 vs numpy==1.26.0: 冲突"""
        assert detect_conflict_package("numpy==1.24.0", "numpy==1.26.0") is True

    def test_no_conflict_same_exact_version(self):
        """numpy==1.24.0 vs numpy==1.24.0: 不冲突"""
        assert detect_conflict_package("numpy==1.24.0", "numpy==1.24.0") is False

    def test_conflict_eq_vs_ne(self):
        """requests==2.0 vs requests!=2.0: 冲突"""
        assert detect_conflict_package("requests==2.0", "requests!=2.0") is True

    def test_no_conflict_eq_vs_ne_different(self):
        """requests==2.0 vs requests!=3.0: 不冲突"""
        assert detect_conflict_package("requests==2.0", "requests!=3.0") is False

    def test_no_conflict_no_version(self):
        """torch vs numpy: 不冲突 (无版本约束)"""
        assert detect_conflict_package("torch", "numpy") is False

    def test_no_conflict_one_no_version(self):
        """torch>=1.0 vs torch: 不冲突 (一方无版本约束)"""
        assert detect_conflict_package("torch>=1.0", "torch") is False

    def test_conflict_multi_constraint(self):
        """requests>=2.0,<3.0 vs requests>=3.0: 冲突"""
        assert detect_conflict_package("requests>=2.0,<3.0", "requests>=3.0") is True

    def test_no_conflict_multi_constraint(self):
        """requests>=2.0,<3.0 vs requests>=2.5: 不冲突"""
        assert detect_conflict_package("requests>=2.0,<3.0", "requests>=2.5") is False

    def test_conflict_compatible_release(self):
        """torch~=1.4 vs torch==2.0: 冲突"""
        assert detect_conflict_package("torch~=1.4", "torch==2.0") is True

    def test_no_conflict_compatible_release(self):
        """torch~=1.4 vs torch==1.5: 不冲突"""
        assert detect_conflict_package("torch~=1.4", "torch==1.5") is False

    def test_conflict_gt_vs_lt(self):
        """>3.0 vs <2.0: 冲突"""
        assert detect_conflict_package("pkg>3.0", "pkg<2.0") is True

    def test_no_conflict_gt_vs_lt(self):
        """>1.0 vs <3.0: 不冲突"""
        assert detect_conflict_package("pkg>1.0", "pkg<3.0") is False


# ============================================================================
# detect_conflict_package_from_list: 包列表冲突检测
# ============================================================================


class TestDetectConflictPackageFromList:
    """测试包列表中的冲突检测"""

    def test_no_conflict_empty_list(self):
        """空列表: 无冲突"""
        assert detect_conflict_package_from_list([]) == []

    def test_no_conflict_single_package(self):
        """单个包: 无冲突"""
        assert detect_conflict_package_from_list(["torch>=1.0"]) == []

    def test_no_conflict_different_packages(self):
        """不同包名: 无冲突"""
        result = detect_conflict_package_from_list(
            [
                "torch>=1.0",
                "numpy>=1.24",
                "requests>=2.0",
            ]
        )
        assert result == []

    def test_conflict_same_package(self):
        """同名包版本冲突"""
        result = detect_conflict_package_from_list(
            [
                "numpy==1.24.0",
                "numpy==1.26.0",
            ]
        )
        assert "numpy" in result

    def test_conflict_mixed_packages(self):
        """混合包列表中检测冲突"""
        result = detect_conflict_package_from_list(
            [
                "torch>=2.0",
                "numpy==1.24.0",
                "requests>=2.0",
                "numpy==1.26.0",
                "pillow>=9.0",
            ]
        )
        assert "numpy" in result
        assert "torch" not in result
        assert "requests" not in result
        assert "pillow" not in result

    def test_no_conflict_compatible_same_package(self):
        """同名包兼容约束: 无冲突"""
        result = detect_conflict_package_from_list(
            [
                "torch>=1.0",
                "torch<=2.0",
            ]
        )
        assert result == []

    def test_conflict_range_vs_exact(self):
        """范围约束与精确版本冲突"""
        result = detect_conflict_package_from_list(
            [
                "numpy>=2.0",
                "numpy==1.24.0",
            ]
        )
        assert "numpy" in result

    def test_no_conflict_packages_without_version(self):
        """无版本约束的包: 无冲突"""
        result = detect_conflict_package_from_list(
            [
                "torch",
                "torch",
            ]
        )
        assert result == []

    def test_conflict_with_normalized_names(self):
        """包名规范化后检测冲突 (下划线 vs 连字符)"""
        result = detect_conflict_package_from_list(
            [
                "my-package==1.0",
                "my_package==2.0",
            ]
        )
        assert len(result) > 0


# ============================================================================
# normalize_package_name: 包名规范化
# ============================================================================


class TestNormalizePackageName:
    """测试包名规范化"""

    def test_hyphen(self):
        assert normalize_package_name("my-package") == "my-package"

    def test_underscore(self):
        assert normalize_package_name("my_package") == "my-package"

    def test_dot(self):
        assert normalize_package_name("my.package") == "my-package"

    def test_mixed(self):
        assert normalize_package_name("My_Package.Name") == "my-package-name"

    def test_consecutive_separators(self):
        assert normalize_package_name("my__package") == "my-package"

    def test_uppercase(self):
        assert normalize_package_name("MyPackage") == "mypackage"


# ============================================================================
# detect_conflict_package: PEP 440 语义与对称性
# ============================================================================


class TestDetectConflictPackagePep440Semantics:
    """测试基于版本区间求交集的冲突检测"""

    @staticmethod
    def _assert_symmetric(pkg1: str, pkg2: str, expected: bool) -> None:
        assert detect_conflict_package(pkg1, pkg2) is expected
        assert detect_conflict_package(pkg2, pkg1) is expected

    def test_compatible_release_disjoint(self):
        """~=1.2.0 vs ~=1.3.0: 冲突 (1.2.x 与 1.3.x 无交集)"""
        self._assert_symmetric("x~=1.2.0", "x~=1.3.0", True)

    def test_compatible_release_overlap(self):
        """~=1.2.0 vs ~=1.2.5: 不冲突"""
        self._assert_symmetric("x~=1.2.0", "x~=1.2.5", False)

    def test_wildcard_vs_lower_bound_inside(self):
        """==1.2.* vs >=1.2.5: 不冲突 (1.2.6 同时满足)"""
        self._assert_symmetric("x==1.2.*", "x>=1.2.5", False)

    def test_wildcard_vs_exact_inside(self):
        """==1.2.* vs ==1.2.3: 不冲突"""
        self._assert_symmetric("x==1.2.*", "x==1.2.3", False)

    def test_wildcard_vs_wildcard_disjoint(self):
        """==1.2.* vs ==1.3.*: 冲突"""
        self._assert_symmetric("x==1.2.*", "x==1.3.*", True)

    def test_wildcard_vs_not_equal_wildcard(self):
        """==1.2.* vs !=1.2.*: 冲突"""
        self._assert_symmetric("x==1.2.*", "x!=1.2.*", True)

    def test_exact_vs_local_version(self):
        """torch==2.1.0 vs torch==2.1.0+cu118: 不冲突 (2.1.0+cu118 同时满足)"""
        self._assert_symmetric("torch==2.1.0", "torch==2.1.0+cu118", False)

    def test_different_local_versions(self):
        """torch==2.1.0+cu118 vs torch==2.1.0+cu121: 冲突"""
        self._assert_symmetric("torch==2.1.0+cu118", "torch==2.1.0+cu121", True)

    def test_not_equal_excludes_local_builds(self):
        """!=1.0 vs ==1.0+cu1: 冲突 (!= 忽略候选版本的 local version)"""
        self._assert_symmetric("x!=1.0", "x==1.0+cu1", True)

    def test_less_than_excludes_own_prerelease(self):
        """>=2.0rc1 vs <2.0: 冲突 (<2.0 不允许 2.0 的预发布版本)"""
        self._assert_symmetric("x>=2.0rc1", "x<2.0", True)

    def test_not_equal_collapses_single_point(self):
        """!=1.5 vs >=1.5,<=1.5: 冲突"""
        self._assert_symmetric("x!=1.5", "x>=1.5,<=1.5", True)

    def test_arbitrary_equality_is_string_match(self):
        """===1.0 vs ===1.0.0: 冲突 (=== 为字符串比较)"""
        self._assert_symmetric("x===1.0", "x===1.0.0", True)

    def test_open_interval_not_empty(self):
        """>1.0 vs <1.0.1: 不冲突"""
        self._assert_symmetric("x>1.0", "x<1.0.1", False)

    def test_unparsable_version_is_ignored(self):
        """无法解析的版本号不判定为冲突"""
        self._assert_symmetric("x==not-a-version", "x==1.0", False)

    def test_compatible_release_pair_constraint(self):
        """~=1.2.0 vs ~=1.3.0 (单对约束): 冲突"""
        assert _is_constraint_pair_conflicting("~=", "1.2.0", "~=", "1.3.0") is True
