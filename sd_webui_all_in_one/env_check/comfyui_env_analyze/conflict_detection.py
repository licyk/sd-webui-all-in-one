"""软件包依赖冲突检测"""

from sd_webui_all_in_one.utils import (
    remove_duplicate_object_from_list,
)
from sd_webui_all_in_one.package_analyzer import (
    get_package_name,
    normalize_package_name,
    parse_package_spec,
)
from sd_webui_all_in_one.env_check.shared import logger
from sd_webui_all_in_one.env_check.comfyui_env_analyze.version_constraints import (
    _are_version_constraints_satisfiable,
)


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
