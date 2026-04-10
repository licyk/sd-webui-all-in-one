"""Python 软件包版本字符串工具

提供版本号格式检查、包名提取、版本号提取等工具函数.

参考:
    - https://peps.python.org/pep-0440/
    - https://peps.python.org/pep-0508/
"""

import re

from sd_webui_all_in_one.package_analyzer.py_whl_parse import (
    ParsedPyWhlRequirement,
    RequirementParser,
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


REPLACE_PACKAGE_NAME_DICT = {
    "sam2": "SAM-2",
}
"""Python 软件包名替换表"""


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
