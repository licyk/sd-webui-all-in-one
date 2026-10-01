"""版本约束范围计算"""

from typing import NamedTuple

from sd_webui_all_in_one.package_analyzer import (
    Specifier,
    Version,
)
from sd_webui_all_in_one.env_check.shared import logger


class _VersionBound(NamedTuple):
    """版本区间的端点"""

    version: Version
    """端点版本 (不含 local version)"""

    inclusive: bool
    """端点本身是否属于区间"""


class _VersionRange(NamedTuple):
    """版本区间, 端点为 ``None`` 时表示该方向无界"""

    lower: _VersionBound | None
    """下界"""

    upper: _VersionBound | None
    """上界"""


class _ConstraintEffect(NamedTuple):
    """单个版本约束对可选版本集合的影响"""

    allowed: _VersionRange | None
    """约束允许的版本区间"""

    excluded: _VersionRange | None
    """约束排除的版本区间 (``!=``)"""

    local: str | None
    """精确匹配要求的 local version"""


_UNBOUNDED_RANGE = _VersionRange(None, None)
"""无界版本区间"""


def _compare_version_components(
    v1: Version,
    v2: Version,
) -> int:
    """按 PEP 440 规则比较两个版本 (忽略 local version)"""
    left = v1.without_local()
    right = v2.without_local()
    return (left > right) - (left < right)


def _release_floor(
    epoch: int,
    release: tuple[int, ...],
) -> Version:
    """返回以指定 release 段开头的最小版本 ``X.Y.dev0``"""
    return Version(epoch=epoch, release=release, dev=0)


def _prefix_range(
    epoch: int,
    prefix: tuple[int, ...],
) -> _VersionRange:
    """前缀匹配 ``== X.Y.*`` 对应的版本区间 ``[X.Y.dev0, X.(Y+1).dev0)``"""
    upper_release = prefix[:-1] + (prefix[-1] + 1,)
    return _VersionRange(
        _VersionBound(_release_floor(epoch, prefix), True),
        _VersionBound(_release_floor(epoch, upper_release), False),
    )


def _lower_bound_not_looser(
    a: _VersionBound | None,
    b: _VersionBound | None,
) -> bool:
    """下界 ``a`` 是否不比下界 ``b`` 宽松"""
    if b is None:
        return True
    if a is None:
        return False
    result = _compare_version_components(a.version, b.version)
    return result > 0 or (result == 0 and (b.inclusive or not a.inclusive))


def _upper_bound_not_looser(
    a: _VersionBound | None,
    b: _VersionBound | None,
) -> bool:
    """上界 ``a`` 是否不比上界 ``b`` 宽松"""
    if b is None:
        return True
    if a is None:
        return False
    result = _compare_version_components(a.version, b.version)
    return result < 0 or (result == 0 and (b.inclusive or not a.inclusive))


def _intersect_version_ranges(
    a: _VersionRange,
    b: _VersionRange,
) -> _VersionRange:
    """计算两个版本区间的交集"""
    lower = a.lower if _lower_bound_not_looser(a.lower, b.lower) else b.lower
    upper = a.upper if _upper_bound_not_looser(a.upper, b.upper) else b.upper
    return _VersionRange(lower, upper)


def _is_version_range_empty(
    version_range: _VersionRange,
) -> bool:
    """判断版本区间是否为空"""
    if version_range.lower is None or version_range.upper is None:
        return False
    result = _compare_version_components(version_range.lower.version, version_range.upper.version)
    return result > 0 or (result == 0 and not (version_range.lower.inclusive and version_range.upper.inclusive))


def _is_version_range_within(
    inner: _VersionRange,
    outer: _VersionRange,
) -> bool:
    """判断版本区间 ``inner`` 是否完全落在 ``outer`` 内"""
    return _lower_bound_not_looser(inner.lower, outer.lower) and _upper_bound_not_looser(inner.upper, outer.upper)


def _version_constraint_effect(
    op: str,
    version: str,
) -> _ConstraintEffect | None:
    """将单个版本约束转换为版本区间

    Args:
        op (str):
            版本约束操作符
        version (str):
            版本约束中的版本号

    Returns:
        (_ConstraintEffect | None):
            约束对可选版本集合的影响, 不影响区间判断的约束返回 ``None``

    Raises:
        ValueError:
            版本号或操作符无法解析时
    """
    spec = Specifier(op, version)
    parsed = spec.parsed_version
    if parsed is None:
        raise ValueError(f"无法解析版本号: {version}")
    public = parsed.without_local()

    if op in ("==", "===", "!="):
        if spec.is_wildcard:
            matched = _prefix_range(parsed.epoch, parsed.release)
        else:
            point = _VersionBound(public, True)
            matched = _VersionRange(point, point)
        if op == "!=":
            # 带 local version 的排除只排除某个特定构建, 不影响版本区间
            if parsed.local is not None:
                return None
            return _ConstraintEffect(None, matched, None)
        return _ConstraintEffect(matched, None, parsed.local)

    if op == "~=":
        # ~= X.Y.Z 等价于 >= X.Y.Z, == X.Y.*
        upper = _prefix_range(parsed.epoch, parsed.release[:-1]).upper
        return _ConstraintEffect(_VersionRange(_VersionBound(public, True), upper), None, None)

    if op == ">=":
        return _ConstraintEffect(_VersionRange(_VersionBound(public, True), None), None, None)

    if op == ">":
        return _ConstraintEffect(_VersionRange(_VersionBound(public, False), None), None, None)

    if op == "<=":
        return _ConstraintEffect(_VersionRange(None, _VersionBound(public, True)), None, None)

    # op == "<". < V 不允许 V 的预发布版本 (除非 V 本身是预发布版本), 因此上界取 V.dev0
    if not parsed.is_prerelease and not parsed.is_postrelease:
        return _ConstraintEffect(_VersionRange(None, _VersionBound(_release_floor(parsed.epoch, parsed.release), False)), None, None)
    return _ConstraintEffect(_VersionRange(None, _VersionBound(public, False)), None, None)


def _are_version_constraints_satisfiable(
    specs: list[tuple[str, str]],
) -> bool:
    """检测一组版本约束是否能被同一个版本同时满足

    将每个约束转换为版本区间后求交集, 再检查交集是否为空、是否被 ``!=`` 约束完全排除,
    以及是否要求了互不相同的 local version / ``===`` 版本.
    无法解析的约束会被忽略, 即宁可漏报也不误报冲突.

    Args:
        specs (list[tuple[str, str]]):
            ``(操作符, 版本号)`` 形式的版本约束列表

    Returns:
        bool: 如果存在满足所有约束的版本则返回 ``True``
    """
    allowed = _UNBOUNDED_RANGE
    excluded: list[_VersionRange] = []
    required_locals: set[str] = set()
    arbitrary_versions: set[str] = set()

    for op, version in specs:
        if op == "===":
            arbitrary_versions.add(version.strip().lower())
        try:
            effect = _version_constraint_effect(op, version)
        except (ValueError, TypeError) as e:
            logger.debug("忽略无法解析的版本约束 %s%s: %s", op, version, e)
            continue
        if effect is None:
            continue
        if effect.allowed is not None:
            allowed = _intersect_version_ranges(allowed, effect.allowed)
        if effect.excluded is not None:
            excluded.append(effect.excluded)
        if effect.local is not None:
            required_locals.add(effect.local)

    if _is_version_range_empty(allowed):
        return False
    if len(required_locals) > 1 or len(arbitrary_versions) > 1:
        return False
    return not any(_is_version_range_within(allowed, exclusion) for exclusion in excluded)


def _is_constraint_pair_conflicting(
    op1: str,
    ver1: str,
    op2: str,
    ver2: str,
) -> bool:
    """检测两个单独的版本约束条件是否不可同时满足

    Args:
        op1 (str):
            第 1 个约束的操作符 (如 ``'>='``, ``'=='``, ``'~='`` 等)
        ver1 (str):
            第 1 个约束的版本号
        op2 (str):
            第 2 个约束的操作符
        ver2 (str):
            第 2 个约束的版本号

    Returns:
        bool: 如果两个约束不可同时满足则返回 ``True``
    """
    conflicting = not _are_version_constraints_satisfiable([(op1, ver1), (op2, ver2)])
    if conflicting:
        logger.debug("冲突约束: %s%s vs %s%s", op1, ver1, op2, ver2)
    return conflicting
