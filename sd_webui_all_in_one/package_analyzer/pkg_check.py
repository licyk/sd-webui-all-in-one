"""Python 软件包检查工具

提供 Python 软件包的版本检查、依赖解析和安装验证功能.

参考:
    - https://peps.python.org/pep-0440/
    - https://peps.python.org/pep-0508/
"""

import os
import re
import importlib.metadata
from typing import Any
from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.package_analyzer.py_ver_cmp import PyWhlVersionComparison
from sd_webui_all_in_one.package_analyzer.py_whl_parse import (
    ParsedPyWhlRequirement,
    RequirementParser,
    get_parse_bindings,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


# PEP 440 Appendix B: canonical version regex (含 local version)
_CANONICAL_VERSION_REGEX = re.compile(
    r"^([1-9][0-9]*!)?"  # epoch
    r"(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*"  # release
    r"((a|b|rc)(0|[1-9][0-9]*))?"  # pre-release
    r"(\.post(0|[1-9][0-9]*))?"  # post-release
    r"(\.dev(0|[1-9][0-9]*))?"  # dev-release
    r"(\+[a-z0-9]+(\.[a-z0-9]+)*)?$"  # local version
)


def version_string_is_canonical(
    version: str,
) -> bool:
    """判断版本号标识符是否符合 PEP 440 canonical 格式

    Args:
        version (str):
            版本号字符串

    Returns:
        bool: 如果版本号标识符符合 PEP 440 canonical 格式则返回 ``True``
    """
    return _CANONICAL_VERSION_REGEX.match(version) is not None


def _try_parse_requirement(
    package: str,
) -> ParsedPyWhlRequirement | None:
    """尝试使用 PEP 508 解析器解析软件包声明

    Args:
        package (str):
            Python 软件包声明字符串

    Returns:
        ParsedPyWhlRequirement | None: 解析成功返回结果, 失败返回 ``None``
    """
    try:
        parser = RequirementParser(package.strip())
        return parser.parse()
    except Exception:
        return None


def is_package_has_version(
    package: str,
) -> bool:
    """检查 Python 软件包声明是否包含版本约束

    使用 PEP 508 解析器解析软件包声明, 检查是否存在版本说明符.

    使用示例:
        ```python
        is_package_has_version("torch==2.3.0")  # True
        is_package_has_version("numpy")  # False
        is_package_has_version("requests>=2.0,<3.0")  # True
        ```

    Args:
        package (str):
            Python 软件包声明字符串

    Returns:
        bool: 如果软件包声明包含版本约束则返回 ``True``
    """
    parsed = _try_parse_requirement(package)
    if parsed is not None:
        # 如果是 URL 依赖 (str), 视为有版本约束
        if isinstance(parsed.specifier, str):
            return True
        # 如果有版本说明符列表且非空
        return len(parsed.specifier) > 0

    # 解析失败时回退到字符串检测
    return package != (
        package.replace("===", "")
        .replace("~=", "")
        .replace("!=", "")
        .replace("<=", "")
        .replace(">=", "")
        .replace("<", "")
        .replace(">", "")
        .replace("==", "")
    )


def get_package_name(
    package: str,
) -> str:
    """获取 Python 软件包的包名, 去除版本声明和 extras

    使用 PEP 508 解析器提取包名.

    使用示例:
        ```python
        get_package_name("torch==2.3.0")  # "torch"
        get_package_name("requests[security]>=2.0")  # "requests"
        get_package_name("numpy")  # "numpy"
        ```

    Args:
        package (str):
            Python 软件包声明字符串

    Returns:
        str: 去除版本声明后的 Python 软件包名
    """
    parsed = _try_parse_requirement(package)
    if parsed is not None:
        return parsed.name

    # 解析失败时回退到字符串分割
    return (
        package.split("===")[0]
        .split("~=")[0]
        .split("!=")[0]
        .split("<=")[0]
        .split(">=")[0]
        .split("<")[0]
        .split(">")[0]
        .split("==")[0]
        .split("[")[0]
        .strip()
    )


def get_package_version(
    package: str,
) -> str:
    """获取 Python 软件包声明中的版本号

    使用 PEP 508 解析器提取第一个版本约束的版本号.

    使用示例:
        ```python
        get_package_version("torch==2.3.0")  # "2.3.0"
        get_package_version("requests>=2.0")  # "2.0"
        ```

    Args:
        package (str):
            Python 软件包声明字符串

    Returns:
        str: Python 软件包的版本号字符串
    """
    parsed = _try_parse_requirement(package)
    if parsed is not None and isinstance(parsed.specifier, list) and len(parsed.specifier) > 0:
        # 返回第一个版本约束的版本号
        return parsed.specifier[0][1]

    # 解析失败时回退到字符串分割
    return (
        package.split("===")
        .pop()
        .split("~=")
        .pop()
        .split("!=")
        .pop()
        .split("<=")
        .pop()
        .split(">=")
        .pop()
        .split("<")
        .pop()
        .split(">")
        .pop()
        .split("==")
        .pop()
        .strip()
    )


WHEEL_PATTERN = r"""
    ^                           # 字符串开始
    (?P<distribution>[^-]+)     # 包名 (匹配第一个非连字符段)
    -                           # 分隔符
    (?:                         # 版本号和可选构建号组合
        (?P<version>[^-]+)      # 版本号 (至少一个非连字符段)
        (?:-(?P<build>\d\w*))?  # 可选构建号 (以数字开头)
    )
    -                           # 分隔符
    (?P<python>[^-]+)           # Python 版本标签
    -                           # 分隔符
    (?P<abi>[^-]+)              # ABI 标签
    -                           # 分隔符
    (?P<platform>[^-]+)         # 平台标签
    \.whl$                      # 固定后缀
"""
"""解析 Python Wheel 文件名的正则表达式"""

REPLACE_PACKAGE_NAME_DICT = {
    "sam2": "SAM-2",
}
"""Python 软件包名替换表"""


def parse_wheel_filename(
    filename: str,
) -> str:
    """解析 Python wheel 文件名并返回 distribution 名称

    Args:
        filename (str):
            wheel 文件名, 例如 ``pydantic-1.10.15-py3-none-any.whl``

    Returns:
        str: distribution 名称, 例如 ``pydantic``

    Raises:
        ValueError: 如果文件名不符合 PEP 491 规范
    """
    match = re.fullmatch(WHEEL_PATTERN, filename, re.VERBOSE)
    if not match:
        logger.debug("未知的 Wheel 文件名: %s", filename)
        raise ValueError(f"未知的 Wheel 文件名: {filename}")
    return match.group("distribution")


def parse_wheel_version(
    filename: str,
) -> str:
    """解析 Python wheel 文件名并返回版本号

    Args:
        filename (str):
            wheel 文件名, 例如 ``pydantic-1.10.15-py3-none-any.whl``

    Returns:
        str: 版本号, 例如 ``1.10.15``

    Raises:
        ValueError: 如果文件名不符合 PEP 491 规范
    """
    match = re.fullmatch(WHEEL_PATTERN, filename, re.VERBOSE)
    if not match:
        logger.debug("未知的 Wheel 文件名: %s", filename)
        raise ValueError(f"未知的 Wheel 文件名: {filename}")
    return match.group("version")


def parse_wheel_to_package_name(
    filename: str,
) -> str:
    """解析 Python wheel 文件名并返回 ``<distribution>==<version>``

    Args:
        filename (str):
            wheel 文件名, 例如 ``pydantic-1.10.15-py3-none-any.whl``

    Returns:
        str: ``<distribution>==<version>`` 格式, 例如 ``pydantic==1.10.15``
    """
    distribution = parse_wheel_filename(filename)
    version = parse_wheel_version(filename)
    return f"{distribution}=={version}"


def remove_optional_dependence_from_package(
    filename: str,
) -> str:
    """移除 Python 软件包声明中的可选依赖 (extras)

    使用示例:
        ```python
        remove_optional_dependence_from_package("diffusers[torch]==0.10.2")
        # "diffusers==0.10.2"
        ```

    Args:
        filename (str):
            Python 软件包声明字符串

    Returns:
        str: 移除可选依赖后的软件包名
    """
    return re.sub(r"\[.*?\]", "", filename)


def get_correct_package_name(
    name: str,
) -> str:
    """将原 Python 软件包名替换成正确的 Python 软件包名

    Args:
        name (str):
            原 Python 软件包名

    Returns:
        str: 替换成正确的软件包名, 如果原有包名正确则返回原包名
    """
    return REPLACE_PACKAGE_NAME_DICT.get(name, name)


def parse_requirement(
    text: str,
    bindings: dict[str, str],
) -> ParsedPyWhlRequirement:
    """解析 PEP 508 依赖声明

    Args:
        text (str):
            依赖声明文本
        bindings (dict[str, str]):
            PEP 508 环境变量绑定字典

    Returns:
        ParsedPyWhlRequirement: 解析结果元组
    """
    parser = RequirementParser(text, bindings)
    return parser.parse()


def evaluate_marker(
    marker: Any,
) -> bool:
    """评估 PEP 508 marker 表达式, 判断当前环境是否符合要求

    PEP 508 规则:
    - 版本比较操作符 (``<``, ``<=``, ``>``, ``>=``, ``==``, ``!=``, ``~=``) 使用 PEP 440 语义
    - ``in`` / ``not in`` 使用字符串包含语义
    - ``and`` / ``or`` 使用逻辑运算

    Args:
        marker (Any):
            marker 表达式 (嵌套元组结构)

    Returns:
        bool: 评估结果
    """
    if marker is None:
        return True

    if isinstance(marker, tuple):
        op = marker[0]

        if op in ("and", "or"):
            left = evaluate_marker(marker[1])
            right = evaluate_marker(marker[2])

            if op == "and":
                return left and right
            else:
                return left or right
        else:
            left = marker[1]
            right = marker[2]

            if op in ["<", "<=", ">", ">=", "==", "!=", "~=", "==="]:
                try:
                    left_ver = PyWhlVersionComparison(str(left).lower())
                    right_ver = PyWhlVersionComparison(str(right).lower())

                    if op == "<":
                        return left_ver < right_ver
                    elif op == "<=":
                        return left_ver <= right_ver
                    elif op == ">":
                        return left_ver > right_ver
                    elif op == ">=":
                        return left_ver >= right_ver
                    elif op == "==":
                        return left_ver == right_ver
                    elif op == "!=":
                        return left_ver != right_ver
                    elif op == "~=":
                        matcher = right_ver.compatible_version_matcher(str(right).lower())
                        return matcher(str(left).lower())
                    elif op == "===":
                        return str(left).lower() == str(right).lower()
                except Exception:
                    left_str = str(left).lower()
                    right_str = str(right).lower()
                    if op == "<":
                        return left_str < right_str
                    elif op == "<=":
                        return left_str <= right_str
                    elif op == ">":
                        return left_str > right_str
                    elif op == ">=":
                        return left_str >= right_str
                    elif op == "==":
                        return left_str == right_str
                    elif op == "!=":
                        return left_str != right_str
                    elif op == "~=":
                        return left_str >= right_str
                    elif op == "===":
                        return left_str == right_str

            elif op == "in":
                return str(left).lower() in str(right).lower()

            elif op == "not in":
                return str(left).lower() not in str(right).lower()

    return False


def parse_requirement_to_list(
    text: str,
) -> list[str]:
    """解析依赖声明并返回依赖列表

    将单个 PEP 508 依赖声明解析为标准化的依赖列表.
    如果声明包含多个版本约束, 每个约束会生成一个独立的依赖项.

    使用示例:
        ```python
        parse_requirement_to_list("protobuf<5,>=4.25.3")
        # ["protobuf<5", "protobuf>=4.25.3"]
        ```

    Args:
        text (str):
            依赖声明字符串

    Returns:
        list[str]: 解析后的依赖声明列表
    """
    try:
        bindings = get_parse_bindings()
        name, _, version_specs, marker = parse_requirement(text, bindings)
    except Exception as e:
        logger.debug("解析失败: %s", e)
        return []

    if not evaluate_marker(marker):
        return []

    dependencies: list[str] = []

    if isinstance(version_specs, str):
        dependencies.append(name)
    else:
        if version_specs:
            for op, version in version_specs:
                dependencies.append(f"{name}{op}{version}")
        else:
            dependencies.append(name)

    return dependencies


def parse_requirement_list(
    requirements: list[str],
) -> list[str]:
    """将 Python 软件包声明列表解析成标准 Python 软件包名列表

    处理各种格式的软件包声明, 包括:
    - 标准 PEP 508 声明: ``torch==2.3.0``
    - 带 extras 的声明: ``diffusers[torch]==0.10.2``
    - Git 仓库引用: ``git+https://github.com/user/repo.git``
    - Wheel URL: ``https://example.com/package-1.0-py3-none-any.whl``
    - 带注释的声明: ``package==1.0 # comment``

    使用示例:
        ```python
        parse_requirement_list([
            'torch==2.3.0',
            'diffusers[torch]==0.10.2',
            'NUMPY',
            'protobuf<5,>=4.25.3',
        ])
        # ['torch==2.3.0', 'diffusers==0.10.2', 'numpy', 'protobuf<5', 'protobuf>=4.25.3']
        ```

    Args:
        requirements (list[str]):
            Python 软件包声明列表

    Returns:
        list[str]: 标准化后的 Python 软件包声明列表
    """

    def _extract_repo_name(url_string: str) -> str | None:
        """从包含 Git 仓库 URL 的字符串中提取仓库名称

        Args:
            url_string (str):
                包含 Git 仓库 URL 的字符串

        Returns:
            str | None: 提取到的仓库名称, 如果未找到则返回 ``None``
        """
        patterns = [
            r"git\+[a-z]+://[^/]+/(?:[^/]+/)*([^/@]+?)(?:\.git)?(?:@|$)",
            r"git\+https://[^/]+/[^/]+/([^/@]+?)(?:\.git)?(?:@|$)",
            r"git\+ssh://git@[^:]+:[^/]+/([^/@]+?)(?:\.git)?(?:@|$)",
            r"/([^/@]+?)(?:\.git)?(?:@|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url_string)
            if match:
                return match.group(1)

        return None

    package_list: list[str] = []
    canonical_package_list: list[str] = []
    for requirement in requirements:
        requirement = re.sub(r"\s*#.*$", "", requirement).strip()
        logger.debug("原始 Python 软件包名: %s", requirement)

        if (
            requirement is None
            or requirement == ""
            or requirement.startswith("#")
            or "# skip_verify" in requirement
            or requirement.startswith("--index-url")
            or requirement.startswith("--extra-index-url")
            or requirement.startswith("--find-links")
            or requirement.startswith("-e .")
            or requirement.startswith("-r ")
        ):
            continue

        if (
            requirement.startswith("-e git+http")
            or requirement.startswith("git+http")
            or requirement.startswith("-e git+ssh://")
            or requirement.startswith("git+ssh://")
        ):
            egg_match = re.search(r"egg=([^#&]+)", requirement)
            if egg_match:
                package_list.append(egg_match.group(1).split("-")[0])
                continue

            repo_name_match = _extract_repo_name(requirement)
            if repo_name_match is not None:
                package_list.append(repo_name_match)
                continue

            package_name = os.path.basename(requirement)
            package_name = package_name.split(".git")[0] if package_name.endswith(".git") else package_name
            package_list.append(package_name)
            continue

        if requirement.startswith("https://") or requirement.startswith("http://"):
            package_name = parse_wheel_to_package_name(os.path.basename(requirement))
            package_list.append(package_name)
            continue

        possble_requirement = parse_requirement_to_list(requirement)
        if len(possble_requirement) == 0:
            continue
        elif len(possble_requirement) == 1:
            requirement = possble_requirement[0]
        else:
            requirements_list = parse_requirement_list(possble_requirement)
            package_list += requirements_list
            continue

        multi_requirements = requirement.split(",")
        if len(multi_requirements) > 1:
            package_name = get_package_name(multi_requirements[0].strip())
            for package_name_with_version_marked in multi_requirements:
                version_symbol = str.replace(package_name_with_version_marked, package_name, "", 1)
                format_package_name = remove_optional_dependence_from_package(f"{package_name}{version_symbol}".strip())
                package_list.append(format_package_name)
        else:
            format_package_name = remove_optional_dependence_from_package(multi_requirements[0].strip())
            package_list.append(format_package_name)

    for p in package_list:
        p = p.lower().strip()
        logger.debug("预处理后的 Python 软件包名: %s", p)
        if not is_package_has_version(p):
            logger.debug("%s 无版本声明", p)
            new_p = get_correct_package_name(p)
            logger.debug("包名处理: %s -> %s", p, new_p)
            canonical_package_list.append(new_p)
            continue

        if version_string_is_canonical(get_package_version(p)):
            canonical_package_list.append(p)
        else:
            logger.debug("%s 软件包名的版本不符合标准", p)

    return canonical_package_list


def read_packages_from_requirements_file(
    file_path: str | Path,
) -> list[str]:
    """从 requirements.txt 文件中读取 Python 软件包版本声明列表

    Args:
        file_path (str | Path):
            requirements.txt 文件路径

    Returns:
        list[str]: 从文件中读取的 Python 软件包声明列表
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.readlines()
    except Exception as e:
        logger.debug("打开 %s 时出现错误: %s\n请检查文件是否出现损坏", file_path, e)
        return []


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

        if op in ("===", "=="):
            logger.debug("包含条件: %s", op)
            logger.debug("%s == %s ?", env_pkg_version, pkg_version)
            if op == "===" and env_pkg_version.lower() == pkg_version.lower():
                logger.debug("%s === %s 条件成立", env_pkg_version, pkg_version)
                return True
            elif op == "==" and cmp == PyWhlVersionComparison(pkg_version):
                logger.debug("%s == %s 条件成立", env_pkg_version, pkg_version)
                return True

        elif op == "~=":
            logger.debug("包含条件: ~=")
            logger.debug("%s ~= %s ?", env_pkg_version, pkg_version)
            matcher = cmp.compatible_version_matcher(pkg_version)
            if matcher(env_pkg_version):
                logger.debug("%s ~= %s 条件成立", env_pkg_version, pkg_version)
                return True

        elif op == "!=":
            logger.debug("包含条件: !=")
            logger.debug("%s != %s ?", env_pkg_version, pkg_version)
            if cmp != PyWhlVersionComparison(pkg_version):
                logger.debug("%s != %s 条件成立", env_pkg_version, pkg_version)
                return True

        elif op == "<=":
            logger.debug("包含条件: <=")
            logger.debug("%s <= %s ?", env_pkg_version, pkg_version)
            if cmp <= PyWhlVersionComparison(pkg_version):
                logger.debug("%s <= %s 条件成立", env_pkg_version, pkg_version)
                return True

        elif op == ">=":
            logger.debug("包含条件: >=")
            logger.debug("%s >= %s ?", env_pkg_version, pkg_version)
            if cmp >= PyWhlVersionComparison(pkg_version):
                logger.debug("%s >= %s 条件成立", env_pkg_version, pkg_version)
                return True

        elif op == "<":
            logger.debug("包含条件: <")
            logger.debug("%s < %s ?", env_pkg_version, pkg_version)
            if cmp < PyWhlVersionComparison(pkg_version):
                logger.debug("%s < %s 条件成立", env_pkg_version, pkg_version)
                return True

        elif op == ">":
            logger.debug("包含条件: >")
            logger.debug("%s > %s ?", env_pkg_version, pkg_version)
            if cmp > PyWhlVersionComparison(pkg_version):
                logger.debug("%s > %s 条件成立", env_pkg_version, pkg_version)
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
