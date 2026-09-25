"""ComfyUI 环境检查工具"""

import os
import sys
from pathlib import Path
from collections import deque
from collections.abc import Callable
from typing import NamedTuple, TypedDict, Literal, TypeAlias

from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.utils import (
    remove_duplicate_object_from_list,
    print_divider,
    append_python_path,
)
from sd_webui_all_in_one.package_analyzer import (
    PyWhlVersionComparison,
    PyWhlVersionComponent,
    get_package_name,
    is_package_has_version,
    is_package_installed,
    normalize_package_name,
    parse_package_spec,
    parse_requirement_list,
    read_packages_from_requirements_file,
    validate_requirements,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

ComponentType: TypeAlias = Literal["core", "extension"]
"""组件类型
- core: 内核
- extension: 扩展
"""

class ComponentEnvironmentDetails(TypedDict):
    """ComfyUI 组件的环境信息结构

    Attributes:
        requirement_path (Path | None):
            依赖文件路径
        component_type (ComponentType | None):
            组件类型
        is_disabled (bool):
            组件是否禁用
        requires (list[str]):
            需要的依赖列表
        has_missing_requires (bool):
            是否存在缺失依赖
        missing_requires (list[str]):
            具体缺失的依赖项
        has_conflict_requires (bool):
            是否存在冲突依赖
        conflict_requires (list[str]):
            具体冲突的依赖项
    """

    requirement_path: Path | None
    """依赖文件路径"""

    component_type: ComponentType | None
    """组件类型"""

    is_disabled: bool
    """组件是否禁用"""

    requires: list[str]
    """需要的依赖列表"""

    has_missing_requires: bool
    """是否存在缺失依赖"""

    missing_requires: list[str]
    """具体缺失的依赖项"""

    has_conflict_requires: bool
    """是否存在冲突依赖"""

    conflict_requires: list[str]
    """具体冲突的依赖项"""


ComfyUIEnvironmentComponent = dict[str, ComponentEnvironmentDetails]
"""ComfyUI 环境组件表字典"""


class ComfyUIConflictItem(TypedDict):
    """单个冲突组件与其版本要求。"""

    component: str
    component_type: ComponentType | None
    requirement: str


class ComfyUIConflictGroup(TypedDict):
    """单个软件包的冲突组。"""

    package: str
    components: list[ComfyUIConflictItem]


ComfyUIDisableReason: TypeAlias = Literal["self_conflict", "conflicts_with_protected", "optimal_selection"]
"""组件被建议禁用的原因
- self_conflict: 组件自身的依赖声明互相冲突
- conflicts_with_protected: 与受保护组件 (如 ComfyUI 内核) 冲突
- optimal_selection: 为保留最多组件而在冲突组件中选择禁用
"""


class ComfyUIConflictEdge(TypedDict):
    """两个组件之间 (或组件自身) 的一条依赖冲突关系。"""

    package: str
    """冲突的软件包名称"""

    component: str
    """组件名称"""

    requirement: str
    """组件的版本声明"""

    other_component: str
    """与之冲突的组件名称"""

    other_requirement: str
    """与之冲突的组件的版本声明"""


class ComfyUIDisableCandidate(TypedDict):
    """建议禁用的组件及原因。"""

    component: str
    """组件名称"""

    reason: ComfyUIDisableReason
    """建议禁用的原因"""

    conflicts_with: list[str]
    """与之冲突的保留组件"""

    packages: list[str]
    """产生冲突的软件包"""


class ComfyUIConflictResolution(TypedDict):
    """冲突组件禁用方案。

    Attributes:
        keep_components (list[str]):
            保留的冲突相关组件。
        disable_components (list[str]):
            可禁用的组件列表, 禁用后剩余组件之间不再存在可解决的冲突。
        disable_details (list[ComfyUIDisableCandidate]):
            每个可禁用组件的禁用原因。
        unresolvable_conflicts (list[ComfyUIConflictEdge]):
            无法通过禁用扩展解决的冲突 (如 ComfyUI 内核依赖自身冲突)。
        is_optimal (bool):
            方案是否已被证明为保留组件最多的方案。
        is_conflict_free (bool):
            执行方案后是否不再存在冲突。
    """

    keep_components: list[str]
    """保留的冲突相关组件。"""

    disable_components: list[str]
    """可禁用的组件列表。"""

    disable_details: list[ComfyUIDisableCandidate]
    """每个可禁用组件的禁用原因。"""

    unresolvable_conflicts: list[ComfyUIConflictEdge]
    """无法通过禁用扩展解决的冲突。"""

    is_optimal: bool
    """方案是否已被证明为保留组件最多的方案。"""

    is_conflict_free: bool
    """执行方案后是否不再存在冲突。"""


ComfyUIConflictAction: TypeAlias = Literal["install", "disable", "skip"]
"""检测到冲突依赖时的处理方式
- install: 按顺序安装冲突组件依赖
- disable: 禁用冲突组件并继续安装依赖
- skip: 忽略冲突
"""


class ComfyUIConflictAnalysisResult(TypedDict):
    """ComfyUI 组件依赖检查结果。

    Attributes:
        components (ComfyUIEnvironmentComponent):
            ComfyUI 组件环境信息。
        requirement_paths (list[Path]):
            需要安装或修复的依赖文件路径。
        conflicts (list[ComfyUIConflictGroup]):
            结构化的冲突依赖信息。
        conflict_info (str):
            冲突依赖文本说明。
        has_missing_requires (bool):
            是否存在缺失依赖。
        has_conflict_requires (bool):
            是否存在冲突依赖。
        conflict_resolution (ComfyUIConflictResolution):
            冲突组件禁用方案, 记录可禁用的组件列表。
    """

    components: ComfyUIEnvironmentComponent
    """ComfyUI 组件环境信息。"""

    requirement_paths: list[Path]
    """需要安装或修复的依赖文件路径。"""

    conflicts: list[ComfyUIConflictGroup]
    """结构化的冲突依赖信息。"""

    conflict_info: str
    """冲突依赖文本说明。"""

    has_missing_requires: bool
    """是否存在缺失依赖。"""

    has_conflict_requires: bool
    """是否存在冲突依赖。"""

    conflict_resolution: ComfyUIConflictResolution
    """冲突组件禁用方案。"""


def create_comfyui_environment_dict(
    comfyui_path: Path,
) -> ComfyUIEnvironmentComponent:
    """创建 ComfyUI 环境组件表字典

    Args:
        comfyui_path (Path):
            ComfyUI 根路径

    Returns:
        ComfyUIEnvironmentComponent:
            ComfyUI 环境组件表字典
    """
    comfyui_env_data: ComfyUIEnvironmentComponent = {
        "ComfyUI": {
            "requirement_path": comfyui_path / "requirements.txt",
            "component_type": "core",
            "is_disabled": False,
            "requires": [],
            "has_missing_requires": False,
            "missing_requires": [],
            "has_conflict_requires": False,
            "conflict_requires": [],
        },
    }

    custom_nodes_path = comfyui_path / "custom_nodes"
    for custom_node in custom_nodes_path.iterdir():
        if custom_node.is_file():
            continue

        custom_node_requirement_path = custom_node / "requirements.txt"
        custom_node_is_disabled = custom_node.name.endswith(".disabled")

        comfyui_env_data[custom_node.name] = {
            "requirement_path": custom_node_requirement_path if custom_node_requirement_path.is_file() else None,
            "component_type": "extension",
            "is_disabled": custom_node_is_disabled,
            "requires": [],
            "has_missing_requires": False,
            "missing_requires": [],
            "has_conflict_requires": False,
            "conflict_requires": [],
        }

    return comfyui_env_data


def update_comfyui_environment_dict(
    env_data: ComfyUIEnvironmentComponent,
    component_name: str,
    requirement_path: Path | None = None,
    component_type: ComponentType | None = None,
    is_disabled: bool | None = None,
    requires: list[str] | None = None,
    has_missing_requires: bool | None = None,
    missing_requires: list[str] | None = None,
    has_conflict_requires: bool | None = None,
    conflict_requires: list[str] | None = None,
) -> None:
    """更新 ComfyUI 环境组件表字典

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典
        component_name (str):
            ComfyUI 组件名称
        requirement_path (Path | None):
            ComfyUI 组件依赖文件路径
        component_type (ComponentType | None):
            组件类型
        is_disabled (bool | None):
            ComfyUI 组件是否被禁用
        requires (list[str] | None):
            ComfyUI 组件需要的依赖列表
        has_missing_requires (bool | None):
            ComfyUI 组件是否存在缺失依赖
        missing_requires (list[str] | None):
            ComfyUI 组件缺失依赖列表
        has_conflict_requires (bool | None):
            ComfyUI 组件是否存在冲突依赖
        conflict_requires (list[str] | None):
            ComfyUI 组件冲突依赖列表
    """
    current = env_data.get(
        component_name,
        {
            "requirement_path": None,
            "is_disabled": False,
            "component_type": None,
            "requires": [],
            "has_missing_requires": False,
            "missing_requires": [],
            "has_conflict_requires": False,
            "conflict_requires": [],
        },
    )
    env_data[component_name] = {
        "requirement_path": requirement_path if requirement_path is not None else current.get("requirement_path"),
        "component_type": component_type if component_type is not None else current.get("component_type", "core"),
        "is_disabled": is_disabled if is_disabled is not None else current.get("is_disabled", False),
        "requires": requires if requires is not None else current.get("requires", []),
        "has_missing_requires": has_missing_requires if has_missing_requires is not None else current.get("has_missing_requires", False),
        "missing_requires": missing_requires if missing_requires is not None else current.get("missing_requires", []),
        "has_conflict_requires": has_conflict_requires if has_conflict_requires is not None else current.get("has_conflict_requires", False),
        "conflict_requires": conflict_requires if conflict_requires is not None else current.get("conflict_requires", []),
    }


def update_comfyui_component_requires_list(
    env_data: ComfyUIEnvironmentComponent,
) -> None:
    """更新 ComfyUI 环境组件表字典, 根据字典中的 requirement_path 确定 Python 软件包版本声明文件, 并解析后写入 requires 字段

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典
    """
    for component_name, details in env_data.items():
        if details.get("is_disabled"):
            continue

        requirement_path = details.get("requirement_path")
        if requirement_path is None:
            continue

        try:
            origin_requires = read_packages_from_requirements_file(requirement_path)
        except (OSError, UnicodeDecodeError) as e:
            # 单个组件的依赖表损坏不应中断整个环境分析, 但需要让用户知道该组件未被检查
            logger.error("读取 '%s' 的依赖表 '%s' 失败, 跳过该组件的依赖检查: %s", component_name, requirement_path, e)
            continue

        requires = parse_requirement_list(origin_requires)
        update_comfyui_environment_dict(
            env_data=env_data,
            component_name=component_name,
            requires=requires,
        )


def update_comfyui_component_missing_requires_list(
    env_data: ComfyUIEnvironmentComponent,
) -> None:
    """更新 ComfyUI 环境组件表字典, 根据字典中的 requires 检查缺失的 Python 软件包, 并保存到 missing_requires 字段和设置 has_missing_requires 状态

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典
    """
    for component_name, details in env_data.items():
        if details.get("is_disabled"):
            continue

        requires = details.get("requires")
        has_missing_requires = False
        missing_requires = []

        for package in requires:
            if not is_package_installed(package):
                has_missing_requires = True
                missing_requires.append(package)

        update_comfyui_environment_dict(
            env_data=env_data,
            component_name=component_name,
            has_missing_requires=has_missing_requires,
            missing_requires=missing_requires,
        )


def update_comfyui_component_conflict_requires_list(
    env_data: ComfyUIEnvironmentComponent,
    conflict_package_list: list[str],
) -> None:
    """更新 ComfyUI 环境组件表字典, 根据 conflicconflict_package_listt_package 检查 ComfyUI 组件冲突的 Python 软件包, 并保存到 conflict_requires 字段和设置 has_conflict_requires 状态

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典
        conflict_package_list (list[str]):
            冲突的 Python 软件包列表
    """
    for component_name, details in env_data.items():
        if details.get("is_disabled"):
            continue

        requires = details.get("requires")
        has_conflict_requires = False
        conflict_requires: list[str] = []

        for conflict_package in conflict_package_list:
            for package in requires:
                if is_package_has_version(package) and get_package_name(conflict_package) == get_package_name(package):
                    has_conflict_requires = True
                    conflict_requires.append(package)

        update_comfyui_environment_dict(
            env_data=env_data,
            component_name=component_name,
            has_conflict_requires=has_conflict_requires,
            conflict_requires=conflict_requires,
        )


def get_comfyui_component_requires_list(
    env_data: ComfyUIEnvironmentComponent,
) -> list[str]:
    """从 ComfyUI 环境组件表字典读取所有组件的 requires

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典

    Returns:
        list[str]:
            ComfyUI 环境组件的 Python 软件包列表
    """
    package_list = []
    for _, details in env_data.items():
        if details.get("is_disabled"):
            continue

        package_list += details.get("requires")

    return remove_duplicate_object_from_list(package_list)


def statistical_need_install_require_component(
    env_data: ComfyUIEnvironmentComponent,
) -> list[Path]:
    """根据 ComfyUI 环境组件表字典中的 has_missing_requires 和 has_conflict_requires 字段确认需要安装依赖的列表

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典

    Returns:
        list[Path]:
            ComfyUI 环境组件的依赖文件路径列表
    """
    requirement_list = []
    for _, details in env_data.items():
        requirement_path = details.get("requirement_path")
        if requirement_path is not None and (details.get("has_missing_requires") or details.get("has_conflict_requires")):
            requirement_list.append(requirement_path)

    return requirement_list


def collect_conflict_components(
    env_data: ComfyUIEnvironmentComponent,
    conflict_package_list: list[str],
) -> list[ComfyUIConflictGroup]:
    """收集 ComfyUI 组件冲突信息并返回结构化数据。

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典
        conflict_package_list (list[str]):
            冲突的软件包名称列表

    Returns:
        list[ComfyUIConflictGroup]:
            结构化的冲突组列表
    """
    conflict_package_list = remove_duplicate_object_from_list(
        [normalize_package_name(x) for x in conflict_package_list]
    )
    conflicts: list[ComfyUIConflictGroup] = []

    for conflict_package in conflict_package_list:
        group_components: list[ComfyUIConflictItem] = []
        for component_name, details in env_data.items():
            for conflict_component_package in details.get("conflict_requires"):
                if normalize_package_name(get_package_name(conflict_component_package)) == normalize_package_name(conflict_package):
                    group_components.append(
                        {
                            "component": component_name,
                            "component_type": details.get("component_type"),
                            "requirement": conflict_component_package,
                        }
                    )

        if group_components:
            conflicts.append(
                {
                    "package": get_package_name(conflict_package),
                    "components": group_components,
                }
            )

    return conflicts


def format_conflict_info(
    conflicts: list[ComfyUIConflictGroup],
) -> str:
    """将结构化冲突组渲染为文本说明。
    
    Args:
        conflicts (list[ComfyUIConflictGroup]):
            冲突组信息列表

    Returns:
        冲突信息文本
    """
    content: list[str] = []
    for conflict in conflicts:
        content.append(f"{conflict['package']}:")
        for item in conflict["components"]:
            component_type = item.get("component_type")
            type_suffix = f" ({component_type})" if component_type else ""
            content.append(f" - {item['component']}{type_suffix}: {item['requirement']}")
        content.append("")

    if len(content) > 0 and content[-1] == "":
        content.pop()

    return "\n".join(content)


def fitter_has_version_package(
    package_list: list[str],
) -> list[str]:
    """过滤不包含版本的 Python 软件包, 仅保留包含版本号声明的 Python 软件包

    Args:
        package_list (list[str]): Python 软件包列表

    Returns:
        list[str]: 仅包含版本号的 Python 软件包列表
    """
    return [p for p in package_list if is_package_has_version(p)]


class _VersionBound(NamedTuple):
    """版本区间的端点"""

    version: PyWhlVersionComponent
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


_VERSION_COMPARATOR = PyWhlVersionComparison("0")
"""用于解析与比较版本号的比较器"""

_UNBOUNDED_RANGE = _VersionRange(None, None)
"""无界版本区间"""


def _compare_version_components(
    v1: PyWhlVersionComponent,
    v2: PyWhlVersionComponent,
) -> int:
    """按 PEP 440 规则比较两个版本 (忽略 local version)"""
    return _VERSION_COMPARATOR.compare_version_objects(v1, v2, ignore_local=True)


def _release_floor(
    epoch: int,
    release: tuple[int, ...],
) -> PyWhlVersionComponent:
    """返回以指定 release 段开头的最小版本 ``X.Y.dev0``"""
    return PyWhlVersionComponent(epoch=epoch, release=release, pre_l=None, pre_n=None, post_n=None, dev_n=0, local=None, is_wildcard=False)


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
    parsed = _VERSION_COMPARATOR.parse_version(version)
    public = parsed._replace(local=None, is_wildcard=False)

    if op in ("==", "===", "!="):
        if parsed.is_wildcard:
            matched = _prefix_range(parsed.epoch, parsed.release)
        else:
            point = _VersionBound(public, True)
            matched = _VersionRange(point, point)
        if op == "!=":
            # 带 local version 的排除只排除某个特定构建, 不影响版本区间
            if parsed.local is not None and not parsed.is_wildcard:
                return None
            return _ConstraintEffect(None, matched, None)
        local = parsed.local.lower() if parsed.local is not None and not parsed.is_wildcard else None
        return _ConstraintEffect(matched, None, local)

    if op == "~=":
        # ~= X.Y.Z 等价于 >= X.Y.Z, == X.Y.*
        if len(parsed.release) < 2:
            raise ValueError(f"~= 操作符不能用于单段版本号: {version}")
        upper = _prefix_range(parsed.epoch, parsed.release[:-1]).upper
        return _ConstraintEffect(_VersionRange(_VersionBound(public, True), upper), None, None)

    if op == ">=":
        return _ConstraintEffect(_VersionRange(_VersionBound(public, True), None), None, None)

    if op == ">":
        return _ConstraintEffect(_VersionRange(_VersionBound(public, False), None), None, None)

    if op == "<=":
        return _ConstraintEffect(_VersionRange(None, _VersionBound(public, True)), None, None)

    if op == "<":
        # PEP 440: < V 不允许 V 的预发布版本 (除非 V 本身是预发布版本), 因此上界取 V.dev0
        if parsed.pre_l is None and parsed.dev_n is None and parsed.post_n is None:
            return _ConstraintEffect(_VersionRange(None, _VersionBound(_release_floor(parsed.epoch, parsed.release), False)), None, None)
        return _ConstraintEffect(_VersionRange(None, _VersionBound(public, False)), None, None)

    raise ValueError(f"未知的版本约束操作符: {op}")


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


def detect_conflict_package(
    pkg1: str,
    pkg2: str,
) -> bool:
    """检测两个 Python 软件包版本声明是否存在冲突

    使用 PEP 508 解析器解析版本约束, 将两个声明的全部约束转换为版本区间求交集,
    交集为空时即判定为冲突. 支持 ``==`` / ``!=`` 通配符, ``~=`` 上界, local version
    以及 ``<V`` 不包含 V 的预发布版本等 PEP 440 语义.

    Args:
        pkg1 (str):
            第 1 个 Python 软件包版本声明
        pkg2 (str):
            第 2 个 Python 软件包版本声明

    Returns:
        bool: 如果 Python 软件包版本声明出现冲突则返回 ``True``
    """
    _, specs1, is_url1 = parse_package_spec(pkg1)
    _, specs2, is_url2 = parse_package_spec(pkg2)

    # URL 依赖或无版本约束不参与冲突检测
    if is_url1 or is_url2 or not specs1 or not specs2:
        return False

    logger.debug("冲突依赖检测: pkg1: %s, specs1: %s, pkg2: %s, specs2: %s", pkg1, specs1, pkg2, specs2)
    conflicting = not _are_version_constraints_satisfiable(specs1 + specs2)
    if conflicting:
        logger.debug("冲突依赖: %s vs %s", pkg1, pkg2)
    return conflicting


def detect_conflict_package_from_list(
    package_list: list[str],
) -> list[str]:
    """检测 Python 软件包版本声明列表中存在冲突的软件包

    先按规范化包名分组, 再仅对同名包组内的约束进行冲突检测.
    相比全量 O(n²) 比较, 大幅减少无效比较次数.

    Args:
        package_list (list[str]):
            Python 软件包版本声明列表

    Returns:
        list[str]:
            冲突的 Python 软件包名列表
    """
    # 1. 一次性解析所有包, 按规范化包名分组
    groups: dict[str, list[str]] = {}
    for pkg in package_list:
        name = normalize_package_name(get_package_name(pkg))
        groups.setdefault(name, []).append(pkg)

    # 2. 只对同名包组内的约束进行冲突检测
    conflict_packages: list[str] = []
    for _norm_name, entries in groups.items():
        if len(entries) < 2:
            continue

        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                if detect_conflict_package(entries[i], entries[j]):
                    conflict_packages.append(get_package_name(entries[i]))

    return remove_duplicate_object_from_list(conflict_packages)


def build_component_conflict_graph(
    conflicts: list[ComfyUIConflictGroup],
) -> tuple[dict[str, ComponentType | None], dict[str, set[str]], list[ComfyUIConflictEdge], dict[str, list[ComfyUIConflictEdge]]]:
    """根据冲突组构建组件级冲突图

    冲突组只记录了声明同一冲突软件包的组件, 组内组件之间不一定互相冲突,
    因此需要对组内每对版本声明重新检测, 仅在真正无法同时满足的组件之间连边.

    Args:
        conflicts (list[ComfyUIConflictGroup]):
            结构化的冲突组列表

    Returns:
        (tuple[dict[str, ComponentType | None], dict[str, set[str]], list[ComfyUIConflictEdge], dict[str, list[ComfyUIConflictEdge]]]):
            组件类型表, 邻接表, 组件之间的冲突关系列表, 组件自身的冲突关系表
    """
    component_types: dict[str, ComponentType | None] = {}
    adjacency: dict[str, set[str]] = {}
    edges: list[ComfyUIConflictEdge] = []
    self_conflicts: dict[str, list[ComfyUIConflictEdge]] = {}

    for group in conflicts:
        items = group["components"]
        for item in items:
            component_types.setdefault(item["component"], item.get("component_type"))
            adjacency.setdefault(item["component"], set())

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                if not detect_conflict_package(a["requirement"], b["requirement"]):
                    continue
                edge: ComfyUIConflictEdge = {
                    "package": group["package"],
                    "component": a["component"],
                    "requirement": a["requirement"],
                    "other_component": b["component"],
                    "other_requirement": b["requirement"],
                }
                if a["component"] == b["component"]:
                    self_conflicts.setdefault(a["component"], []).append(edge)
                    continue
                edges.append(edge)
                adjacency[a["component"]].add(b["component"])
                adjacency[b["component"]].add(a["component"])

    return component_types, adjacency, edges, self_conflicts


def _split_connected_components(
    nodes: list[str],
    adjacency: dict[str, set[str]],
) -> list[list[str]]:
    """将冲突图拆分为连通分量, 各分量内节点按名称排序"""
    visited: set[str] = set()
    result: list[list[str]] = []
    for start in nodes:
        if start in visited:
            continue
        visited.add(start)
        queue = deque([start])
        component: list[str] = []
        while queue:
            node = queue.popleft()
            component.append(node)
            for neighbor in sorted(adjacency[node]):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        result.append(sorted(component))
    return result


def _iter_mask_bits(
    mask: int,
) -> list[int]:
    """返回位掩码中所有置位的下标"""
    bits: list[int] = []
    while mask:
        low = mask & -mask
        bits.append(low.bit_length() - 1)
        mask ^= low
    return bits


def _max_weight_independent_set(
    neighbors: list[int],
    weights: list[int],
    search_budget: int,
) -> tuple[int, bool]:
    """使用位集分支定界求解最大权独立集

    先以贪心解作为初始下界, 搜索中使用度为 0 / 1 的节点约简, 并以贪心团划分作为上界剪枝.
    搜索步数超过预算时返回当前最优解 (仍然是合法的独立集).

    Args:
        neighbors (list[int]):
            每个节点的邻居位掩码
        weights (list[int]):
            每个节点的权重
        search_budget (int):
            最大搜索步数

    Returns:
        (tuple[int, bool]):
            选中节点的位掩码, 以及该结果是否已被证明为最优解
    """
    node_count = len(neighbors)
    degrees = [mask.bit_count() for mask in neighbors]

    greedy_set, blocked = 0, 0
    for v in sorted(range(node_count), key=lambda x: (-weights[x] / (degrees[x] + 1), x)):
        if not (blocked >> v) & 1:
            greedy_set |= 1 << v
            blocked |= neighbors[v] | (1 << v)
    best_weight = sum(weights[v] for v in _iter_mask_bits(greedy_set))
    best_set = greedy_set
    steps = 0

    def clique_cover_bound(candidates: int) -> int:
        # 将候选节点贪心划分为若干团, 每个团至多选一个节点, 上界为各团最大权重之和
        bound, rest = 0, candidates
        while rest:
            v = (rest & -rest).bit_length() - 1
            rest &= ~(1 << v)
            members, top = 1 << v, weights[v]
            for u in _iter_mask_bits(rest & neighbors[v]):
                if (neighbors[u] & members) == members:
                    members |= 1 << u
                    top = max(top, weights[u])
                    rest &= ~(1 << u)
            bound += top
        return bound

    def search(candidates: int, current_weight: int, current_set: int) -> bool:
        nonlocal best_weight, best_set, steps
        steps += 1
        if steps > search_budget:
            return False

        # 约简: 候选中无邻居的节点必选; 仅有一个邻居且权重不小于该邻居的节点必选
        changed = True
        while changed and candidates:
            changed = False
            for v in _iter_mask_bits(candidates):
                if not (candidates >> v) & 1:
                    continue
                local_neighbors = neighbors[v] & candidates
                if local_neighbors == 0 or (local_neighbors & (local_neighbors - 1) == 0 and weights[v] >= weights[local_neighbors.bit_length() - 1]):
                    current_weight += weights[v]
                    current_set |= 1 << v
                    candidates &= ~(local_neighbors | (1 << v))
                    changed = True

        if candidates == 0:
            if current_weight > best_weight:
                best_weight, best_set = current_weight, current_set
            return True

        if current_weight + clique_cover_bound(candidates) <= best_weight:
            return True

        # 在候选中度最大的节点上分支 (同度时取下标最小者, 保证结果确定)
        pivot = max(_iter_mask_bits(candidates), key=lambda x: ((neighbors[x] & candidates).bit_count(), -x))
        if not search(candidates & ~(neighbors[pivot] | (1 << pivot)), current_weight + weights[pivot], current_set | (1 << pivot)):
            return False
        return search(candidates & ~(1 << pivot), current_weight, current_set)

    is_optimal = search((1 << node_count) - 1, 0, 0)
    return best_set, is_optimal


def resolve_conflict_components(
    conflicts: list[ComfyUIConflictGroup],
    protected_components: list[str] | None = None,
    preferred_components: list[str] | None = None,
    search_budget: int = 200_000,
) -> ComfyUIConflictResolution:
    """计算保留组件最多的无冲突组合, 并给出需要禁用的组件列表

    算法流程:
    1. 对冲突组内的版本声明逐对检测, 构建组件级冲突图.
    2. ComfyUI 内核与 ``protected_components`` 中的组件始终保留; 与其冲突的扩展, 以及自身依赖冲突的扩展必须禁用.
    3. 对剩余冲突图的每个连通分量求最大权独立集: 首先保证保留的组件数量最多,
       其次优先保留 ``preferred_components`` 中的组件, 最后按组件名称确定性地选择.

    Args:
        conflicts (list[ComfyUIConflictGroup]):
            结构化的冲突组列表
        protected_components (list[str] | None):
            始终保留的组件
        preferred_components (list[str] | None):
            保留数量相同时优先保留的组件
        search_budget (int):
            每个连通分量的最大搜索步数, 超出后使用当前最优解

    Returns:
        ComfyUIConflictResolution: 冲突组件禁用方案
    """
    component_types, adjacency, edges, self_conflicts = build_component_conflict_graph(conflicts)
    protected = {name for name, component_type in component_types.items() if component_type == "core"}
    protected |= set(protected_components or []) & set(component_types)
    preferred = set(preferred_components or [])

    disable: dict[str, ComfyUIDisableCandidate] = {}
    unresolvable: list[ComfyUIConflictEdge] = []

    def add_disable(name: str, reason: ComfyUIDisableReason) -> None:
        if name not in disable:
            disable[name] = {"component": name, "reason": reason, "conflicts_with": [], "packages": []}

    for name, self_edges in self_conflicts.items():
        if name in protected:
            unresolvable.extend(self_edges)
        else:
            add_disable(name, "self_conflict")

    for edge in edges:
        if edge["component"] in protected and edge["other_component"] in protected:
            unresolvable.append(edge)

    for name in sorted(component_types):
        if name not in protected and adjacency[name] & protected:
            add_disable(name, "conflicts_with_protected")

    free_nodes = sorted(name for name in component_types if name not in protected and name not in disable and adjacency[name])
    free_set = set(free_nodes)
    is_optimal = True
    for component in _split_connected_components(free_nodes, {name: adjacency[name] & free_set for name in free_nodes}):
        index = {name: i for i, name in enumerate(component)}
        neighbors = [sum(1 << index[other] for other in adjacency[name] if other in index) for name in component]
        # 基础权重大于所有偏好加成之和, 保证 "保留数量" 严格优先于 "偏好"
        scale = len(component) + 1
        weights = [scale + (1 if name in preferred else 0) for name in component]
        chosen, optimal = _max_weight_independent_set(neighbors, weights, search_budget)
        is_optimal = is_optimal and optimal
        for i, name in enumerate(component):
            if not (chosen >> i) & 1:
                add_disable(name, "optimal_selection")

    for edge in edges:
        for name, other in ((edge["component"], edge["other_component"]), (edge["other_component"], edge["component"])):
            if name in disable and other not in disable:
                if other not in disable[name]["conflicts_with"]:
                    disable[name]["conflicts_with"].append(other)
                if edge["package"] not in disable[name]["packages"]:
                    disable[name]["packages"].append(edge["package"])
    for name, self_edges in self_conflicts.items():
        if name in disable:
            for edge in self_edges:
                if edge["package"] not in disable[name]["packages"]:
                    disable[name]["packages"].append(edge["package"])

    details = [disable[name] for name in sorted(disable)]
    for detail in details:
        detail["conflicts_with"].sort()
        detail["packages"].sort()

    keep = sorted(name for name in component_types if name not in disable)
    keep_set = set(keep)
    is_conflict_free = not any(name in keep_set for name in self_conflicts) and not any(edge["component"] in keep_set and edge["other_component"] in keep_set for edge in edges)
    return {
        "keep_components": keep,
        "disable_components": sorted(disable),
        "disable_details": details,
        "unresolvable_conflicts": unresolvable,
        "is_optimal": is_optimal,
        "is_conflict_free": is_conflict_free,
    }


def format_conflict_resolution_info(
    resolution: ComfyUIConflictResolution,
) -> str:
    """将冲突组件禁用方案渲染为文本说明。

    Args:
        resolution (ComfyUIConflictResolution):
            冲突组件禁用方案

    Returns:
        str: 禁用方案文本
    """
    content: list[str] = []
    if resolution["disable_details"]:
        content.append(f"可禁用以下 {len(resolution['disable_components'])} 个组件以解决冲突 (保留 {len(resolution['keep_components'])} 个冲突相关组件):")
        for detail in resolution["disable_details"]:
            packages = ", ".join(detail["packages"])
            conflicts_with = ", ".join(detail["conflicts_with"])
            if detail["reason"] == "self_conflict":
                content.append(f" - {detail['component']}: 组件自身的依赖声明存在冲突 ({packages})")
            elif detail["reason"] == "conflicts_with_protected":
                content.append(f" - {detail['component']}: 与必须保留的组件 {conflicts_with} 存在冲突 ({packages})")
            else:
                content.append(f" - {detail['component']}: 与 {conflicts_with} 存在冲突 ({packages})")
        if not resolution["is_optimal"]:
            content.append("冲突关系较复杂, 以上为近似方案, 可能不是保留组件最多的方案")

    if resolution["unresolvable_conflicts"]:
        content.append("以下冲突无法通过禁用扩展解决:")
        for edge in resolution["unresolvable_conflicts"]:
            content.append(f" - {edge['package']}: {edge['component']} ({edge['requirement']}) <-> {edge['other_component']} ({edge['other_requirement']})")

    return "\n".join(content)


def display_comfyui_environment_dict(
    env_data: ComfyUIEnvironmentComponent,
) -> None:
    """列出 ComfyUI 环境组件字典内容

    Args:
        env_data (ComfyUIEnvironmentComponent): ComfyUI 环境组件表字典
    """
    logger.debug("ComfyUI 环境组件表")
    for component_name, details in env_data.items():
        logger.debug("Component: %s", component_name)
        logger.debug(" - requirement_path: %s", details["requirement_path"])
        logger.debug(" - is_disabled: %s", details["is_disabled"])
        logger.debug(" - requires: %s", details["requires"])
        logger.debug(" - has_missing_requires: %s", details["has_missing_requires"])
        logger.debug(" - missing_requires: %s", details["missing_requires"])
        logger.debug(" - has_conflict_requires: %s", details["has_conflict_requires"])
        logger.debug(" - conflict_requires: %s", details["conflict_requires"])
        print()


def display_check_result(
    requirement_list: list[Path],
    conflict_result: str,
) -> None:
    """显示 ComfyUI 运行环境检查结果

    Args:
        requirement_list (list[Path]):
            ComfyUI 组件依赖文件路径列表
        conflict_result (str):
            冲突组件统计信息
    """
    if len(requirement_list) > 0:
        logger.debug("需要安装 ComfyUI 组件列表")
        for requirement in requirement_list:
            component_name = requirement.parent.name
            logger.debug("%s:", component_name)
            logger.debug(" - %s", requirement)
        print()

    if len(conflict_result) > 0:
        logger.debug("ComfyUI 冲突组件: \n%s", conflict_result)


def process_comfyui_env_analysis(
    comfyui_root_path: Path,
) -> tuple[dict[str, ComponentEnvironmentDetails], list[Path], list[ComfyUIConflictGroup]]:
    """分析 ComfyUI 环境

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录
    Returns:
        (tuple[dict[str, ComponentEnvironmentDetails], list[Path], list[ComfyUIConflictGroup]]):
            ComfyUI 环境组件信息, 缺失依赖的依赖表, 结构化冲突信息

    Raises:
        FileNotFoundError:
            ComfyUI 依赖文件缺失 / 自定义节点文件夹未找到时
    """
    if not (comfyui_root_path / "requirements.txt").exists():
        logger.error("ComfyUI 依赖文件缺失, 请检查 ComfyUI 是否安装完整")
        raise FileNotFoundError("ComfyUI 依赖文件缺失, 请检查 ComfyUI 是否安装完整")

    if not (comfyui_root_path / "custom_nodes").exists():
        logger.error("ComfyUI 自定义节点文件夹未找到, 请检查 ComfyUI 是否安装完整")
        raise FileNotFoundError("ComfyUI 自定义节点文件夹未找到, 请检查 ComfyUI 是否安装完整")

    env_data = create_comfyui_environment_dict(comfyui_root_path)
    update_comfyui_component_requires_list(env_data)
    update_comfyui_component_missing_requires_list(env_data)
    pkg_list = get_comfyui_component_requires_list(env_data)
    has_version_pkg = fitter_has_version_package(pkg_list)
    conflict_pkg = detect_conflict_package_from_list(has_version_pkg)
    update_comfyui_component_conflict_requires_list(env_data, conflict_pkg)
    req_list = statistical_need_install_require_component(env_data)
    conflicts = collect_conflict_components(env_data, conflict_pkg)
    return env_data, req_list, conflicts


def check_comfyui_component_dependencies(
    comfyui_root_path: Path,
) -> ComfyUIConflictAnalysisResult:
    """检查 ComfyUI 组件依赖状态，不执行依赖修复。

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录。

    Returns:
        ComfyUIConflictAnalysisResult: ComfyUI 组件依赖检查结果。

    Raises:
        FileNotFoundError: ComfyUI 依赖文件缺失 / 自定义节点文件夹未找到时抛出。
    """
    env_data, req_list, conflicts = process_comfyui_env_analysis(comfyui_root_path)
    conflict_info = format_conflict_info(conflicts)
    has_missing_requires = any(details.get("has_missing_requires", False) for details in env_data.values())
    has_conflict_requires = any(details.get("has_conflict_requires", False) for details in env_data.values())
    # 保留数量相同时, 优先保留冲突依赖已被当前环境满足的组件, 以减少对现有环境的改动
    preferred_components = [
        component_name for component_name, details in env_data.items() if details.get("conflict_requires") and all(is_package_installed(package) for package in details["conflict_requires"])
    ]
    conflict_resolution = resolve_conflict_components(conflicts, preferred_components=preferred_components)
    return {
        "components": env_data,
        "requirement_paths": req_list,
        "conflicts": conflicts,
        "conflict_info": conflict_info,
        "has_missing_requires": has_missing_requires,
        "has_conflict_requires": has_conflict_requires,
        "conflict_resolution": conflict_resolution,
    }


def _prompt_conflict_action(
    resolution: ComfyUIConflictResolution,
) -> ComfyUIConflictAction:
    """在交互模式下询问检测到冲突依赖时的处理方式

    Args:
        resolution (ComfyUIConflictResolution):
            冲突组件禁用方案

    Returns:
        ComfyUIConflictAction: 用户选择的处理方式
    """
    can_disable = len(resolution["disable_components"]) > 0
    print("请选择冲突依赖的处理方式:")
    print("1. 按顺序安装冲突组件依赖")
    if can_disable:
        print(f"2. 禁用冲突组件并继续安装依赖 (将禁用: {', '.join(resolution['disable_components'])})")
    print("N. 忽略冲突并继续")
    answer = input("请输入选项 (1/2/N): " if can_disable else "请输入选项 (1/N): ").strip().lower()
    if answer in ["1", "yes", "y"]:
        return "install"
    if can_disable and answer in ["2", "d", "disable"]:
        return "disable"
    return "skip"


def _select_conflict_action(
    resolution: ComfyUIConflictResolution,
    install_conflict_component_requirement: bool,
    disable_conflict_component: bool,
    interactive_mode: bool,
) -> ComfyUIConflictAction:
    """确定检测到冲突依赖时的处理方式

    交互模式下由用户选择; 非交互模式下优先禁用冲突组件, 其次按顺序安装冲突组件依赖.

    Args:
        resolution (ComfyUIConflictResolution):
            冲突组件禁用方案
        install_conflict_component_requirement (bool):
            是否按顺序安装冲突组件依赖
        disable_conflict_component (bool):
            是否禁用冲突组件并继续安装依赖
        interactive_mode (bool):
            是否启用交互模式

    Returns:
        ComfyUIConflictAction: 处理方式
    """
    if interactive_mode:
        return _prompt_conflict_action(resolution)
    if disable_conflict_component and resolution["disable_components"]:
        return "disable"
    if install_conflict_component_requirement:
        return "install"
    return "skip"


def _create_disable_component_callback(
    comfyui_root_path: Path,
) -> Callable[[str], None]:
    """创建默认的 ComfyUI 组件禁用函数

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录

    Returns:
        Callable[[str], None]: 接收组件名称并禁用该组件的函数
    """
    # 延迟导入, 避免 env_check 与 base_manager 之间的循环导入
    from sd_webui_all_in_one.base_manager.comfyui_base.extensions.local import set_comfyui_custom_node_status  # pylint: disable=import-outside-toplevel

    def disable_component(component_name: str) -> None:
        set_comfyui_custom_node_status(comfyui_root_path, component_name, False)

    return disable_component


def _disable_conflict_components(
    components: list[str],
    disable_component_callback: Callable[[str], None],
) -> list[Exception]:
    """禁用冲突组件

    Args:
        components (list[str]):
            需要禁用的组件列表
        disable_component_callback (Callable[[str], None]):
            禁用单个组件的函数

    Returns:
        list[Exception]: 禁用组件时出现的错误
    """
    err: list[Exception] = []
    disabled: list[str] = []
    task_sum = len(components)
    for count, component_name in enumerate(components, start=1):
        logger.info("[%s/%s] 禁用 %s 中", count, task_sum, component_name)
        try:
            disable_component_callback(component_name)
            disabled.append(component_name)
        except (OSError, ValueError, RuntimeError) as e:
            err.append(e)
            logger.error("[%s/%s] 禁用 %s 失败: %s", count, task_sum, component_name, e)

    if disabled:
        logger.info("已禁用以下冲突组件: %s", ", ".join(disabled))
        logger.info("如需重新启用, 可在 ComfyUI 扩展管理中重新启用这些组件")
    return err


def _install_component_requirements(
    comfyui_root_path: Path,
    req_list: list[Path],
    install_sequentially: bool,
    use_uv: bool,
    custom_env: dict[str, str] | None,
) -> list[Exception]:
    """安装 ComfyUI 组件依赖并执行组件的安装脚本

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录
        req_list (list[Path]):
            需要安装的依赖文件路径列表
        install_sequentially (bool):
            是否按顺序逐个安装依赖, 为 ``False`` 时先尝试批量安装, 失败后回退到按顺序安装
        use_uv (bool):
            是否使用 uv 安装依赖
        custom_env (dict[str, str] | None):
            环境变量字典

    Returns:
        list[Exception]: 安装依赖时出现的错误
    """
    comfyui_root_path = comfyui_root_path.resolve()
    req_paths = [req.resolve() for req in req_list]
    task_sum = len(req_paths)
    install_script_paths = [req_path for req_path in req_paths if (req_path.parent / "install.py").is_file()]
    install_script_sum = len(install_script_paths)
    install_script_index = {req_path: count for count, req_path in enumerate(install_script_paths, start=1)}
    if custom_env is None:
        custom_env = os.environ.copy()

    custom_env = append_python_path(
        new_path=comfyui_root_path,
        origin_env=custom_env,
    )

    err: list[Exception] = []

    def install_one_requirement(
        req_path: Path,
        count: int,
    ) -> None:
        name = req_path.parent.name
        logger.info("[%s/%s] 安装 %s 的依赖中", count, task_sum, name)
        try:
            install_requirements(
                path=req_path,
                use_uv=use_uv,
                cwd=req_path.parent,
                custom_env=custom_env,
            )
        except RuntimeError as e:
            err.append(e)
            logger.error("[%s/%s] 安装 %s 的依赖失败: %s", count, task_sum, name, e)

    def run_one_install_script(
        req_path: Path,
        count: int,
    ) -> None:
        name = req_path.parent.name
        installer_script = req_path.parent / "install.py"
        logger.info("[%s/%s] 执行 %s 的安装脚本中", count, install_script_sum, name)
        try:
            run_cmd(
                [Path(sys.executable).as_posix(), installer_script.as_posix()],
                cwd=req_path.parent,
                custom_env=custom_env,
            )
        except RuntimeError as e:
            err.append(e)
            logger.info("[%s/%s] 执行 %s 的安装脚本时发生错误: %s", count, install_script_sum, name, e)

    def run_install_script_for_requirement(req_path: Path) -> None:
        install_script_count = install_script_index.get(req_path)
        if install_script_count is not None:
            run_one_install_script(req_path, install_script_count)

    def install_requirements_sequentially() -> None:
        for count, req_path in enumerate(req_paths, start=1):
            install_one_requirement(req_path, count)
            run_install_script_for_requirement(req_path)

    def run_install_scripts_sequentially() -> None:
        install_script_names = ", ".join(req_path.parent.name for req_path in install_script_paths)
        if len(install_script_paths) > 0:
            logger.info("执行以下 ComfyUI 组件的安装脚本中: %s", install_script_names)
        for count, req_path in enumerate(install_script_paths, start=1):
            run_one_install_script(req_path, count)

    batch_requirement_names = ", ".join(req_path.parent.name for req_path in req_paths)
    if install_sequentially:
        install_requirements_sequentially()
    elif req_paths:
        try:
            logger.info("批量安装以下 ComfyUI 组件的依赖中: %s", batch_requirement_names)
            install_requirements(
                path=req_paths,
                use_uv=use_uv,
                cwd=comfyui_root_path,
                custom_env=custom_env,
            )
            logger.info("批量安装以下 ComfyUI 组件的依赖完成: %s", batch_requirement_names)
            run_install_scripts_sequentially()
        except RuntimeError as e:
            logger.warning("批量安装以下 ComfyUI 组件的依赖失败, 回退到按顺序安装: %s, 错误: %s", batch_requirement_names, e)
            install_requirements_sequentially()

    return err


def comfyui_conflict_analyzer(
    comfyui_root_path: Path,
    install_conflict_component_requirement: bool = False,
    disable_conflict_component: bool = False,
    interactive_mode: bool = False,
    use_uv: bool = True,
    custom_env: dict[str, str] | None = None,
    disable_component_callback: Callable[[str], None] | None = None,
) -> None:
    """检查并安装 ComfyUI 的依赖环境

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录
        install_conflict_component_requirement (bool):
            检测到冲突依赖时是否按顺序安装组件依赖
        disable_conflict_component (bool):
            检测到冲突依赖时是否禁用冲突组件 (保留尽可能多的组件) 并继续安装依赖, 优先于 ``install_conflict_component_requirement``
        interactive_mode (bool):
            是否启用交互模式, 当检测到冲突依赖时将询问处理方式
        use_uv (bool):
            是否使用 uv 安装依赖
        custom_env (dict[str, str] | None):
            环境变量字典
        disable_component_callback (Callable[[str], None] | None):
            禁用单个组件的函数, 未指定时使用 ComfyUI 扩展管理的禁用方式

    Raises:
        AggregateError:
            禁用冲突组件或安装依赖出现错误时
    """
    logger.info("检测 ComfyUI 环境中")
    analysis = check_comfyui_component_dependencies(comfyui_root_path)
    env_data = analysis["components"]
    req_list = analysis["requirement_paths"]
    conflict_info = analysis["conflict_info"]

    if logger.level <= 10:
        display_comfyui_environment_dict(env_data)
        display_check_result(req_list, conflict_info)

    err: list[Exception] = []
    has_conflict = len(conflict_info) > 0
    if has_conflict:
        resolution = analysis["conflict_resolution"]
        resolution_info = format_conflict_resolution_info(resolution)
        logger.warning("检测到当前 ComfyUI 环境中安装的插件之间存在依赖冲突情况, 该问题并非致命, 但建议只保留一个插件, 否则部分功能可能无法正常使用")
        logger.warning("您可以选择按顺序安装依赖, 由于这将向环境中安装不符合版本要求的组件, 您将无法完全解决此问题, 但可避免组件由于依赖缺失而无法启动的情况")
        if resolution["disable_components"]:
            logger.warning("您也可以选择禁用部分冲突组件, 在保留尽可能多组件的前提下消除冲突, 再继续安装依赖")
        logger.warning("检测到冲突的依赖:")
        print_divider("=")
        print(conflict_info)
        if resolution_info:
            print_divider("-")
            print(resolution_info)
        print_divider("=")

        action = _select_conflict_action(
            resolution=resolution,
            install_conflict_component_requirement=install_conflict_component_requirement,
            disable_conflict_component=disable_conflict_component,
            interactive_mode=interactive_mode,
        )
        if action == "disable":
            if disable_component_callback is None:
                disable_component_callback = _create_disable_component_callback(comfyui_root_path)
            err.extend(_disable_conflict_components(resolution["disable_components"], disable_component_callback))

            logger.info("重新检测 ComfyUI 环境中")
            analysis = check_comfyui_component_dependencies(comfyui_root_path)
            req_list = analysis["requirement_paths"]
            conflict_info = analysis["conflict_info"]
            has_conflict = len(conflict_info) > 0
            if has_conflict:
                logger.warning("禁用冲突组件后仍存在依赖冲突:")
                print_divider("=")
                print(conflict_info)
                print_divider("=")
                if interactive_mode:
                    install_conflict = input("是否按顺序安装冲突组件依赖 (y/N): ").strip().lower() in ["yes", "y"]
                else:
                    install_conflict = install_conflict_component_requirement
                action = "install" if install_conflict else "skip"
            else:
                logger.info("禁用冲突组件后已不存在依赖冲突, 继续安装依赖")

        if action == "skip":
            logger.info("忽略警告并继续启动 ComfyUI")
            if err:
                raise AggregateError("禁用 ComfyUI 冲突组件时出现错误", err)
            return

    err.extend(
        _install_component_requirements(
            comfyui_root_path=comfyui_root_path,
            req_list=req_list,
            install_sequentially=has_conflict,
            use_uv=use_uv,
            custom_env=custom_env,
        )
    )

    if err:
        raise AggregateError("安装 ComfyUI 依赖时出现错误", err)

    logger.info("ComfyUI 环境检查完成")


def check_comfyui_manager_dependence(
    comfyui_root_path: Path,
    use_uv: bool = True,
    custom_env: dict[str, str] | None = None,
) -> None:
    """检查 ComfyUI Manager 依赖

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录
        use_uv (bool):
            是否使用 uv 安装依赖
        custom_env (dict[str, str] | None):
            环境变量字典

    Raises:
        RuntimeError:
            安装 ComfyUI Manager 依赖发生错误时
    """
    comfyui_manager_requirement = comfyui_root_path / "manager_requirements.txt"
    if not comfyui_manager_requirement.is_file():
        logger.debug("ComfyUI Manager 依赖表不存在, 跳过 ComfyUI Manager 依赖检查")
        return

    logger.info("检查 ComfyUI Manager 依赖中")
    if not validate_requirements(comfyui_manager_requirement):
        logger.info("安装 ComfyUI Manager 依赖中")
        try:
            install_requirements(
                path=comfyui_manager_requirement,
                use_uv=use_uv,
                custom_env=custom_env,
                cwd=comfyui_root_path,
            )
            logger.info("安装 ComfyUI Manager 依赖完成")
        except RuntimeError as e:
            logger.error("安装 ComfyUI Manager 依赖出现错误: %s", e)
            raise RuntimeError(f"安装 ComfyUI Manager 依赖出现错误: {e}") from e
    else:
        logger.info("ComfyUI Manager 依赖检查完成")
