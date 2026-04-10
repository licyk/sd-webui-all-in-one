"""ComfyUI 环境检查工具"""

import os
import re
import sys
from pathlib import Path
from typing import TypedDict

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
    check_version_constraint,
    get_package_name,
    is_package_has_version,
    is_package_installed,
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


class ComponentEnvironmentDetails(TypedDict):
    """ComfyUI 组件的环境信息结构

    Attributes:
        requirement_path (Path):
            依赖文件路径
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

    requirement_path: Path
    """依赖文件路径"""

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


def normalize_package_name(
    name: str,
) -> str:
    """规范化软件包名 (https://peps.python.org/pep-0503/#normalized-names)

    Args:
        name (str):
            原始包名字符串

    Returns:
        str:
            规范化后的软件包名字符串
    """
    return re.sub(r"[-_.]+", "-", name).lower()


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
    env_data[component_name] = {
        "requirement_path": (requirement_path if requirement_path else env_data.get(component_name).get("requirement_path")),
        "is_disabled": (is_disabled if is_disabled else env_data.get(component_name).get("is_disabled")),
        "requires": (requires if requires else env_data.get(component_name).get("requires")),
        "has_missing_requires": (has_missing_requires if has_missing_requires else env_data.get(component_name).get("has_missing_requires")),
        "missing_requires": (missing_requires if missing_requires else env_data.get(component_name).get("missing_requires")),
        "has_conflict_requires": (has_conflict_requires if has_conflict_requires else env_data.get(component_name).get("has_conflict_requires")),
        "conflict_requires": (conflict_requires if conflict_requires else env_data.get(component_name).get("conflict_requires")),
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

        origin_requires = read_packages_from_requirements_file(requirement_path)
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
) -> list[str]:
    """根据 ComfyUI 环境组件表字典中的 has_missing_requires 和 has_conflict_requires 字段确认需要安装依赖的列表

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典

    Returns:
        list[str]:
            ComfyUI 环境组件的依赖文件路径列表
    """
    requirement_list = []
    for _, details in env_data.items():
        if details.get("has_missing_requires") or details.get("has_conflict_requires"):
            requirement_list.append(details.get("requirement_path").as_posix())

    return requirement_list


def statistical_has_conflict_component(
    env_data: ComfyUIEnvironmentComponent,
    conflict_package_list: list[str],
) -> str:
    """根据 ComfyUI 环境组件表字典中的 conflict_requires 字段统计冲突的组件信息

    Args:
        env_data (ComfyUIEnvironmentComponent):
            ComfyUI 环境组件表字典

    Returns:
        str:
            ComfyUI 环境冲突的组件信息列表
    """
    content = []
    conflict_package_list = remove_duplicate_object_from_list([normalize_package_name(x) for x in conflict_package_list])
    for conflict_package in conflict_package_list:
        content.append(get_package_name(f"{conflict_package}:"))
        for component_name, details in env_data.items():
            for conflict_component_package in details.get("conflict_requires"):
                conflict_component_package_format = normalize_package_name(get_package_name(conflict_component_package))
                conflict_package_format = normalize_package_name(conflict_package)
                if conflict_component_package_format == conflict_package_format:
                    content.append(f" - {component_name}: {conflict_component_package}")
        content.append("")
    return "\n".join([str(x) for x in (content[:-1] if len(content) > 0 and content[-1] == "" else content)])


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


def _is_constraint_pair_conflicting(
    op1: str,
    ver1: str,
    op2: str,
    ver2: str,
) -> bool:
    """检测两个单独的版本约束条件是否不可同时满足

    通过检查两个约束定义的版本区间是否存在交集来判断冲突.
    复用 :func:`check_version_constraint` 进行 PEP 440 合规的版本比较.

    Args:
        op1 (str):
            第 1 个约束的操作符 (如 ``'>=``, ``'=='``, ``'~='`` 等)
        ver1 (str):
            第 1 个约束的版本号
        op2 (str):
            第 2 个约束的操作符
        ver2 (str):
            第 2 个约束的版本号

    Returns:
        bool: 如果两个约束不可同时满足则返回 ``True``
    """
    cmp = PyWhlVersionComparison(ver1)

    # == 或 === 是精确约束, 检查该精确版本是否满足另一个约束
    if op1 in ("==", "==="):
        cmp2 = PyWhlVersionComparison(ver1)
        if not check_version_constraint(ver1, op2, ver2, cmp2):
            logger.debug("冲突约束: %s%s vs %s%s (精确版本 %s 不满足 %s%s)", op1, ver1, op2, ver2, ver1, op2, ver2)
            return True
        return False

    if op2 in ("==", "==="):
        cmp2 = PyWhlVersionComparison(ver2)
        if not check_version_constraint(ver2, op1, ver1, cmp2):
            logger.debug("冲突约束: %s%s vs %s%s (精确版本 %s 不满足 %s%s)", op1, ver1, op2, ver2, ver2, op1, ver1)
            return True
        return False

    # != 约束几乎不会与范围约束产生冲突 (除非范围只包含被排除的版本, 这种情况极为罕见)
    if op1 == "!=" or op2 == "!=":
        return False

    # ~= 展开为 >= ver, == ver_prefix.* 后检测
    # ~= X.Y.Z 等价于 >= X.Y.Z, == X.Y.*
    if op1 == "~=":
        # ~= ver1 等价于 >= ver1 (下界), 检测下界是否与 op2 冲突
        if _is_constraint_pair_conflicting(">=", ver1, op2, ver2):
            return True
        # 还需检测 ~= 的上界 (== prefix.*) 是否与 op2 冲突
        # ~= X.Y.Z 的上界约束等价于 < X.(Y+1).0
        # 但精确计算上界较复杂, 这里用 compatible_version_matcher 来验证
        # 如果 op2 是下界约束 (>, >=), 检查 ver2 是否超出 ~= 的兼容范围
        if op2 in (">", ">="):
            matcher = cmp.compatible_version_matcher(ver1)
            # 如果 ver2 本身不在兼容范围内, 且 ver2 >= ver1, 则存在冲突
            # 因为 op2 要求 > ver2 或 >= ver2, 而 ~= ver1 的上界低于 ver2
            if not matcher(ver2) and PyWhlVersionComparison(ver2) >= PyWhlVersionComparison(ver1):
                logger.debug("冲突约束: ~=%s vs %s%s (兼容范围不包含 %s)", ver1, op2, ver2, ver2)
                return True
        return False

    if op2 == "~=":
        return _is_constraint_pair_conflicting(op2, ver2, op1, ver1) # pylint: disable=arguments-out-of-order

    # 范围约束之间的冲突检测: >, >=, <, <=
    # 下界 vs 上界: 检查下界是否超过上界
    lower_ops = {">", ">="}
    upper_ops = {"<", "<="}

    if op1 in lower_ops and op2 in upper_ops:
        # op1 是下界, op2 是上界
        cmp_result = PyWhlVersionComparison(ver1).compare_versions(ver1, ver2, ignore_local=True)
        if op1 == ">=" and op2 == "<=":
            # >= ver1, <= ver2: 冲突当 ver1 > ver2
            if cmp_result > 0:
                logger.debug("冲突约束: >=%s vs <=%s (%s > %s)", ver1, ver2, ver1, ver2)
                return True
        elif op1 == ">=" and op2 == "<":
            # >= ver1, < ver2: 冲突当 ver1 >= ver2
            if cmp_result >= 0:
                logger.debug("冲突约束: >=%s vs <%s (%s >= %s)", ver1, ver2, ver1, ver2)
                return True
        elif op1 == ">" and op2 == "<=":
            # > ver1, <= ver2: 冲突当 ver1 >= ver2
            if cmp_result >= 0:
                logger.debug("冲突约束: >%s vs <=%s (%s >= %s)", ver1, ver2, ver1, ver2)
                return True
        elif op1 == ">" and op2 == "<":
            # > ver1, < ver2: 冲突当 ver1 >= ver2
            if cmp_result >= 0:
                logger.debug("冲突约束: >%s vs <%s (%s >= %s)", ver1, ver2, ver1, ver2)
                return True
        return False

    if op1 in upper_ops and op2 in lower_ops:
        # 交换后递归检测
        return _is_constraint_pair_conflicting(op2, ver2, op1, ver1) # pylint: disable=arguments-out-of-order

    # 同方向的范围约束 (如 > 和 >=, 或 < 和 <=) 不会互相冲突
    return False


def detect_conflict_package(
    pkg1: str,
    pkg2: str,
) -> bool:
    """检测两个 Python 软件包版本声明是否存在冲突

    使用 PEP 508 解析器解析版本约束, 然后对每对约束条件进行可满足性检测.
    复用 :func:`parse_package_spec` 和 :func:`check_version_constraint` 实现
    完整的 PEP 440 操作符支持.

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

    # 对两组约束中的每对条件进行冲突检测
    for op1, ver1 in specs1:
        for op2, ver2 in specs2:
            try:
                if _is_constraint_pair_conflicting(op1, ver1, op2, ver2):
                    logger.debug("冲突依赖: %s vs %s (约束 %s%s 与 %s%s 冲突)", pkg1, pkg2, op1, ver1, op2, ver2)
                    return True
            except (ValueError, TypeError) as e:
                logger.debug("冲突检测异常: %s%s vs %s%s: %s", op1, ver1, op2, ver2, e)
                continue

    return False


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
    requirement_list: list[str],
    conflict_result: str,
) -> None:
    """显示 ComfyUI 运行环境检查结果

    Args:
        requirement_list (list[str]):
            ComfyUI 组件依赖文件路径列表
        conflict_result (str):
            冲突组件统计信息
    """
    if len(requirement_list) > 0:
        logger.debug("需要安装 ComfyUI 组件列表")
        for requirement in requirement_list:
            component_name = requirement.split("/")[-2]
            logger.debug("%s:", component_name)
            logger.debug(" - %s", requirement)
        print()

    if len(conflict_result) > 0:
        logger.debug("ComfyUI 冲突组件: \n%s", conflict_result)


def process_comfyui_env_analysis(
    comfyui_root_path: Path,
) -> tuple[dict[str, ComponentEnvironmentDetails], list[str], str]:
    """分析 ComfyUI 环境

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录
    Returns:
        (tuple[dict[str, ComponentEnvironmentDetails], list[str], str]):
            ComfyUI 环境组件信息, 缺失依赖的依赖表, 冲突组件信息

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
    conflict_info = statistical_has_conflict_component(env_data, conflict_pkg)
    return env_data, req_list, conflict_info


def comfyui_conflict_analyzer(
    comfyui_root_path: Path,
    install_conflict_component_requirement: bool | None = False,
    interactive_mode: bool | None = False,
    use_uv: bool | None = True,
    custom_env: dict[str, str] | None = None,
) -> None:
    """检查并安装 ComfyUI 的依赖环境

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录
        install_conflict_component_requirement (bool | None):
            检测到冲突依赖时是否按顺序安装组件依赖
        interactive_mode (bool | None):
            是否启用交互模式, 当检测到冲突依赖时将询问是否安装冲突组件依赖
        use_uv (bool | None):
            是否使用 uv 安装依赖
        custom_env (dict[str, str] | None):
            环境变量字典

    Returns:
        AggregateError:
            安装依赖出现错误时
    """
    logger.info("检测 ComfyUI 环境中")
    env_data, req_list, conflict_info = process_comfyui_env_analysis(comfyui_root_path)

    if logger.level <= 10:
        display_comfyui_environment_dict(env_data)
        display_check_result(req_list, conflict_info)

    if len(conflict_info) > 0:
        logger.warning("检测到当前 ComfyUI 环境中安装的插件之间存在依赖冲突情况, 该问题并非致命, 但建议只保留一个插件, 否则部分功能可能无法正常使用")
        logger.warning("您可以选择按顺序安装依赖, 由于这将向环境中安装不符合版本要求的组件, 您将无法完全解决此问题, 但可避免组件由于依赖缺失而无法启动的情况")
        logger.warning("检测到冲突的依赖:")
        print_divider("=")
        print(conflict_info)
        print_divider("=")
        if interactive_mode and input("是否按顺序安装冲突组件依赖 (y/N): ").strip().lower() not in ["yes", "y"]:
            logger.info("忽略警告并继续启动 ComfyUI")
            return
        if not interactive_mode and not install_conflict_component_requirement:
            logger.info("忽略警告并继续启动 ComfyUI")
            return

    task_sum = len(req_list)
    count = 0
    if custom_env is None:
        custom_env = os.environ.copy()

    custom_env = append_python_path(
        new_path=comfyui_root_path,
        origin_env=custom_env,
    )

    err: list[Exception] = []
    for req in req_list:
        count += 1
        req_path = Path(req)
        name = req_path.parent.name
        installer_script = req_path / "install.py"
        logger.info("[%s/%s] 安装 %s 的依赖中", count, task_sum, name)
        try:
            install_requirements(
                path=Path(req),
                use_uv=use_uv,
                cwd=req_path.parent,
                custom_env=custom_env,
            )
        except RuntimeError as e:
            err.append(e)
            logger.error("[%s/%s] 安装 %s 的依赖失败: %s", count, task_sum, name, e)

        if installer_script.is_file():
            logger.info("[%s/%s] 执行 %s 的安装脚本中", count, task_sum, name)
            try:
                run_cmd(
                    [Path(sys.executable).as_posix(), installer_script.as_posix()],
                    cwd=req_path.parent,
                    custom_env=custom_env,
                )
            except RuntimeError as e:
                err.append(e)
                logger.info("[%s/%s] 执行 %s 的安装脚本时发生错误: %s", count, task_sum, name, e)

    if err:
        raise AggregateError("安装 ComfyUI 依赖时出现错误", err)

    logger.info("ComfyUI 环境检查完成")


def check_comfyui_manager_dependence(
    comfyui_root_path: Path,
    use_uv: bool | None = True,
    custom_env: dict[str, str] | None = None,
) -> None:
    """检查 ComfyUI Manager 依赖

    Args:
        comfyui_root_path (Path):
            ComfyUI 根目录
        use_uv (bool | None):
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
