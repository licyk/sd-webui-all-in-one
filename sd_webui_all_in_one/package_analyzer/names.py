"""Python 软件包名与 extra 名的校验和规范化

参考:
    - https://packaging.python.org/en/latest/specifications/name-normalization/
    - https://peps.python.org/pep-0685/
"""

import re

from sd_webui_all_in_one.package_analyzer.errors import InvalidName


NAME_PATTERN = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
"""匹配合法软件包名 / extra 名的正则表达式片段 (仅 ASCII)"""

PACKAGE_NAME_ALIASES: dict[str, str] = {
    "sam2": "SAM-2",
}
"""依赖声明中的软件包名到实际分发名的替换表"""

_NAME_REGEX = re.compile(NAME_PATTERN + r"\Z")
_SEPARATOR_REGEX = re.compile(r"[-_.]+")


def is_valid_name(
    name: str,
) -> bool:
    """判断软件包名 (或 extra 名) 是否合法

    合法名称仅包含 ASCII 字母, 数字, ``.``, ``-``, ``_``, 且必须以字母或数字开头和结尾.

    Args:
        name (str):
            待检查的名称

    Returns:
        bool: 名称合法时返回 ``True``
    """
    return _NAME_REGEX.match(name) is not None


def normalize_name(
    name: str,
    validate: bool = False,
) -> str:
    """规范化软件包名

    将连续的 ``-``, ``_``, ``.`` 替换为单个 ``-`` 并转为小写.

    Args:
        name (str):
            待规范化的名称
        validate (bool):
            是否在规范化前校验名称合法性

    Returns:
        str: 规范化后的名称

    Raises:
        InvalidName:
            ``validate`` 为 ``True`` 且名称不合法时
    """
    if validate and not is_valid_name(name):
        raise InvalidName(f"不合法的软件包名: {name!r}")
    return _SEPARATOR_REGEX.sub("-", name).lower()


def normalize_extra(
    name: str,
) -> str:
    """规范化 extra 名, 规则与软件包名一致 (PEP 685)

    Args:
        name (str):
            待规范化的 extra 名

    Returns:
        str: 规范化后的 extra 名
    """
    return _SEPARATOR_REGEX.sub("-", name).lower()
