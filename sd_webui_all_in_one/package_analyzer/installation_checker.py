"""Python 软件包安装状态检查器

提供已安装软件包的版本查询和依赖验证功能.

参考:
    - https://peps.python.org/pep-0440/
    - https://peps.python.org/pep-0508/
"""

import importlib.metadata
import re
from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.package_analyzer.py_ver_cmp import PyWhlVersionComparison
from sd_webui_all_in_one.package_analyzer.dependency_categorizer import get_categorized_dependencies
from sd_webui_all_in_one.package_analyzer.version_utils import _try_parse_requirement
from sd_webui_all_in_one.package_analyzer.requirement_normalizer import parse_requirement_list
from sd_webui_all_in_one.package_analyzer.requirement_parser import read_packages_from_requirements_file


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def _normalize_extra_name(extra_name: str) -> str:
    """标准化 optional extra 分组名"""
    return re.sub(r"[-_.]+", "-", extra_name).lower()


def _parse_package_metadata_dependency_request(
    package_name: str,
) -> tuple[str, list[str]]:
    """解析 metadata 依赖检查请求中的包名和 optional extras"""
    package_name = package_name.strip()
    if not package_name:
        raise ValueError("Python 软件包名不能为空")

    parsed = _try_parse_requirement(package_name)
    if parsed is None:
        raise ValueError(f"无法解析 Python 软件包声明: {package_name}")

    extras: list[str] = []
    for extra in parsed.extras:
        if extra not in extras:
            extras.append(extra)

    return parsed.name, extras


def _get_package_metadata_dependencies(
    package_name: str,
) -> list[str]:
    """获取指定包 metadata 中需要检查的依赖列表"""
    base_name, requested_extras = _parse_package_metadata_dependency_request(package_name)
    deps = get_categorized_dependencies(base_name)
    requires: list[str] = []

    def append_unique(requirement: str) -> None:
        if requirement not in requires:
            requires.append(requirement)

    for requirement in deps["mandatory"]:
        append_unique(requirement)

    optional_lookup = {_normalize_extra_name(extra): extra for extra in deps["optional"]}
    unknown_extras: list[str] = []
    for extra in requested_extras:
        optional_key = optional_lookup.get(_normalize_extra_name(extra))
        if optional_key is None:
            unknown_extras.append(extra)
            continue

        for requirement in deps["optional"][optional_key]:
            append_unique(requirement)

    if unknown_extras:
        raise ValueError(f"未找到 '{base_name}' 的可选依赖分组: {', '.join(unknown_extras)}")

    return requires


def get_package_version_from_library(
    package_name: str,
) -> str | None:
    """获取已安装的 Python 软件包版本号

    依次尝试原始包名、小写包名、下划线转连字符包名进行查找.

    Args:
        package_name (str):
            Python 软件包名

    Returns:
        str | None: 如果获取到版本号则返回版本号字符串, 否则返回 ``None``
    """
    try:
        ver = importlib.metadata.version(package_name)
    except Exception:
        ver = None

    if ver is None:
        try:
            ver = importlib.metadata.version(package_name.lower())
        except Exception:
            ver = None

    if ver is None:
        try:
            ver = importlib.metadata.version(package_name.replace("_", "-"))
        except Exception:
            ver = None

    return ver


def parse_package_spec(
    package: str,
) -> tuple[str, list[tuple[str, str]], bool]:
    """将包声明解析为 ``(包名, 版本约束列表, 是否为URL依赖)``

    优先使用 PEP 508 解析器, 失败时回退到按操作符优先级从长到短匹配.
    支持多版本约束 (PEP 440: 逗号等价于逻辑 AND).

    Args:
        package (str):
            包声明字符串, 如 ``'requests>=2.0,<3.0'``

    Returns:
        tuple[str, list[tuple[str, str]], bool]:
            ``(包名, [(操作符, 版本号), ...], 是否为URL依赖)`` 元组.
            如果没有版本约束则列表为空.
    """
    # 优先使用 PEP 508 解析器
    parsed = _try_parse_requirement(package)
    if parsed is not None:
        if isinstance(parsed.specifier, list) and len(parsed.specifier) > 0:
            return (parsed.name, parsed.specifier, False)
        elif isinstance(parsed.specifier, str):
            # URL 依赖
            return (parsed.name, [("@", parsed.specifier)], True)
        else:
            return (parsed.name, [], False)

    # 回退: 按长度从长到短匹配操作符
    operators = ["===", "~=", "==", "!=", "<=", ">=", "<", ">"]
    for op in operators:
        if op in package:
            parts = package.split(op, 1)
            return (parts[0].strip(), [(op, parts[1].strip())], False)

    return (package.strip(), [], False)


def _split_package_spec(
    package: str,
) -> tuple[str, str, str | None]:
    """将包声明分割为 ``(包名, 操作符, 版本号)``

    .. deprecated::
        此函数仅返回第一个版本约束, 对于多约束声明不完整.
        请使用 :func:`parse_package_spec` 代替.

    优先使用 PEP 508 解析器, 失败时回退到按操作符优先级从长到短匹配.

    Args:
        package (str):
            包声明字符串, 如 ``'requests>=2.0'``

    Returns:
        tuple[str, str, str | None]:
            ``(包名, 操作符, 版本号)`` 元组, 如果没有版本约束则操作符为空字符串, 版本号为 ``None``
    """
    name, specs, _is_url = parse_package_spec(package)
    if specs:
        op, ver = specs[0]
        return (name, op, ver)
    return (name, "", None)


def check_version_constraint(
    env_ver: str,
    op: str,
    pkg_ver: str,
    cmp: PyWhlVersionComparison,
) -> bool:
    """检查单个版本约束是否满足

    根据 PEP 440 规范实现各操作符的语义:
    - ``===``: 任意相等 (简单字符串比较, 不区分大小写)
    - ``==``: 版本匹配 (支持通配符 ``.*``, 忽略 candidate 的 local version)
    - ``!=``: 版本排除 (``==`` 的取反, 支持通配符)
    - ``~=``: 兼容性版本匹配
    - ``>=``, ``<=``: 包含性有序比较 (忽略 local version)
    - ``>``, ``<``: 排他性有序比较 (忽略 local version, 有 post/pre-release 特殊规则)

    Args:
        env_ver (str):
            已安装的版本号
        op (str):
            版本比较操作符
        pkg_ver (str):
            约束中指定的版本号
        cmp (PyWhlVersionComparison):
            用已安装版本初始化的比较器

    Returns:
        bool: 如果约束满足则返回 ``True``
    """
    if op == "===":
        # PEP 440: 任意相等, 简单字符串比较
        return env_ver.lower() == pkg_ver.lower()

    if op == "==":
        # PEP 440: 版本匹配 (支持通配符, 忽略 local version)
        return cmp.version_match(pkg_ver, env_ver)

    if op == "!=":
        # PEP 440: 版本排除 (== 的取反)
        return not cmp.version_match(pkg_ver, env_ver)

    if op == "~=":
        # PEP 440: 兼容性版本匹配
        return cmp.compatible_version_matcher(pkg_ver)(env_ver)

    if op == ">=":
        # PEP 440: 包含性有序比较, 忽略 local version
        return cmp.compare_versions(env_ver, pkg_ver, ignore_local=True) >= 0

    if op == "<=":
        # PEP 440: 包含性有序比较, 忽略 local version
        return cmp.compare_versions(env_ver, pkg_ver, ignore_local=True) <= 0

    if op == ">":
        # PEP 440: 排他性大于比较
        return cmp.exclusive_gt(env_ver, pkg_ver)

    if op == "<":
        # PEP 440: 排他性小于比较
        return cmp.exclusive_lt(env_ver, pkg_ver)

    return False


def is_package_installed(
    package: str,
) -> bool:
    """判断 Python 软件包是否已安装在环境中

    使用 PEP 508 解析器解析包声明, 然后检查已安装版本是否满足所有约束.
    PEP 440 规定逗号等价于逻辑 AND, 候选版本必须满足所有版本约束.

    Args:
        package (str):
            Python 软件包声明字符串, 如 ``'requests>=2.0,<3.0'``

    Returns:
        bool: 如果软件包未安装或未安装正确的版本则返回 ``False``
    """
    pkg_name, specs, _is_url = parse_package_spec(package)

    env_pkg_version = get_package_version_from_library(pkg_name)
    logger.debug(
        "已安装 Python 软件包检测: pkg_name: %s, env_pkg_version: %s, specs: %s",
        pkg_name,
        env_pkg_version,
        specs,
    )

    if env_pkg_version is None:
        return False

    if not specs:
        # 无版本约束, 只要安装了就行
        return True

    cmp = PyWhlVersionComparison(env_pkg_version)

    # PEP 440: 逗号等价于逻辑 AND, 必须满足所有约束
    for op, pkg_version in specs:
        logger.debug("%s %s %s ?", env_pkg_version, op, pkg_version)
        if not check_version_constraint(env_pkg_version, op, pkg_version, cmp):
            logger.debug("%s %s %s 条件不成立", env_pkg_version, op, pkg_version)
            logger.debug("%s 需要安装", package)
            return False
        logger.debug("%s %s %s 条件成立", env_pkg_version, op, pkg_version)

    return True


def get_missing_package_metadata_dependencies(
    package_name: str,
) -> list[str]:
    """获取 wheel metadata 中声明但当前环境缺失的依赖

    Args:
        package_name (str):
            已安装软件包名, 支持 ``package`` 或 ``package[extra1,extra2]`` 格式.

    Returns:
        list[str]: 缺失或版本不满足约束的依赖声明列表

    Raises:
        ValueError:
            包声明无法解析或请求的 optional extra 不存在时
    """
    requires = _get_package_metadata_dependencies(package_name)
    missing: list[str] = []
    for package in requires:
        if not is_package_installed(package):
            missing.append(package)

    return missing


def validate_package_metadata_dependencies(
    package_name: str,
) -> bool:
    """检测 wheel metadata 中声明的依赖是否完整

    Args:
        package_name (str):
            已安装软件包名, 支持 ``package`` 或 ``package[extra1,extra2]`` 格式.

    Returns:
        bool: 如果所有需要检查的依赖均已安装并满足版本约束则返回 ``True``

    Raises:
        ValueError:
            包声明无法解析或请求的 optional extra 不存在时
    """
    return not get_missing_package_metadata_dependencies(package_name)


def validate_requirements(
    requirement_path: str | Path,
) -> bool:
    """检测环境依赖是否完整

    读取 requirements 文件并检查所有依赖是否已正确安装.

    Args:
        requirement_path (str | Path):
            依赖文件路径

    Returns:
        bool: 如果有缺失依赖则返回 ``False``
    """
    origin_requires = read_packages_from_requirements_file(requirement_path)
    requires = parse_requirement_list(origin_requires)
    for package in requires:
        if not is_package_installed(package):
            return False

    return True
