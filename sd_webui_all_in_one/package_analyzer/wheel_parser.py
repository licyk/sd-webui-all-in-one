"""Python Wheel 文件名解析器

提供 Wheel 文件名的解析功能, 包括提取 distribution 名称和版本号.

参考:
    - https://peps.python.org/pep-0491/
"""

import re

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
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
