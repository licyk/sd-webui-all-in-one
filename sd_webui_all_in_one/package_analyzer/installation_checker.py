"""Python 软件包安装状态检查器

提供已安装软件包的版本查询和依赖验证功能.

参考:
    - https://peps.python.org/pep-0440/
    - https://peps.python.org/pep-0508/
"""

import importlib.metadata
from typing import Callable
from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.package_analyzer.py_ver_cmp import PyWhlVersionComparison
from sd_webui_all_in_one.package_analyzer.version_utils import _try_parse_requirement
from sd_webui_all_in_one.package_analyzer.requirement_parser import (
    parse_requirement_list,
    read_packages_from_requirements_file,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


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


def _split_package_spec(
    package: str,
) -> tuple[str, str, str | None]:
    """将包声明分割为 ``(包名, 操作符, 版本号)``

    优先使用 PEP 508 解析器, 失败时回退到按操作符优先级从长到短匹配.

    Args:
        package (str):
            包声明字符串, 如 ``'requests>=2.0'``

    Returns:
        tuple[str, str, str | None]:
            ``(包名, 操作符, 版本号)`` 元组, 如果没有版本约束则操作符为空字符串, 版本号为 ``None``
    """
    # 优先使用 PEP 508 解析器
    parsed = _try_parse_requirement(package)
    if parsed is not None:
        if isinstance(parsed.specifier, list) and len(parsed.specifier) > 0:
            op, ver = parsed.specifier[0]
            return (parsed.name, op, ver)
        elif isinstance(parsed.specifier, str):
            # URL 依赖
            return (parsed.name, "@", parsed.specifier)
        else:
            return (parsed.name, "", None)

    # 回退: 按长度从长到短匹配操作符
    operators = ["===", "~=", "==", "!=", "<=", ">=", "<", ">"]
    for op in operators:
        if op in package:
            parts = package.split(op, 1)
            return (parts[0].strip(), op, parts[1].strip())

    return (package.strip(), "", None)


# 版本比较操作符分发表
_VERSION_OPS: dict[str, Callable[[str, str, PyWhlVersionComparison], bool]] = {
    "===": lambda env_ver, pkg_ver, _cmp: env_ver.lower() == pkg_ver.lower(),
    "==": lambda _env_ver, pkg_ver, cmp: cmp == PyWhlVersionComparison(pkg_ver),
    "~=": lambda env_ver, pkg_ver, cmp: cmp.compatible_version_matcher(pkg_ver)(env_ver),
    "!=": lambda _env_ver, pkg_ver, cmp: cmp != PyWhlVersionComparison(pkg_ver),
    "<=": lambda _env_ver, pkg_ver, cmp: cmp <= PyWhlVersionComparison(pkg_ver),
    ">=": lambda _env_ver, pkg_ver, cmp: cmp >= PyWhlVersionComparison(pkg_ver),
    "<": lambda _env_ver, pkg_ver, cmp: cmp < PyWhlVersionComparison(pkg_ver),
    ">": lambda _env_ver, pkg_ver, cmp: cmp > PyWhlVersionComparison(pkg_ver),
}
"""版本比较操作符到比较函数的映射表"""


def is_package_installed(
    package: str,
) -> bool:
    """判断 Python 软件包是否已安装在环境中

    使用 PEP 508 解析器解析包声明, 然后检查已安装版本是否满足约束.

    Args:
        package (str):
            Python 软件包声明字符串, 如 ``'requests>=2.0'``

    Returns:
        bool: 如果软件包未安装或未安装正确的版本则返回 ``False``
    """
    pkg_name, op, pkg_version = _split_package_spec(package)

    env_pkg_version = get_package_version_from_library(pkg_name)
    logger.debug(
        "已安装 Python 软件包检测: pkg_name: %s, env_pkg_version: %s, pkg_version: %s",
        pkg_name,
        env_pkg_version,
        pkg_version,
    )

    if env_pkg_version is None:
        return False

    if pkg_version is not None and op:
        cmp = PyWhlVersionComparison(env_pkg_version)
        check_fn = _VERSION_OPS.get(op)

        if check_fn:
            logger.debug("包含条件: %s", op)
            logger.debug("%s %s %s ?", env_pkg_version, op, pkg_version)
            result = check_fn(env_pkg_version, pkg_version, cmp)
            if result:
                logger.debug("%s %s %s 条件成立", env_pkg_version, op, pkg_version)
                return True

        logger.debug("%s 需要安装", package)
        return False

    return True


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
