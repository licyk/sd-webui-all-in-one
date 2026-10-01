"""已安装软件包的依赖分类

从已安装软件包的元数据 (``Requires-Dist``) 中读取依赖声明, 并按环境标记分为必选依赖与各 extra 引入的可选依赖.
"""

from importlib.metadata import requires
from typing import TypedDict

from sd_webui_all_in_one.config import (
    LOGGER_NAME,
    LOGGER_LEVEL,
    LOGGER_COLOR,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.package_analyzer.errors import InvalidRequirement
from sd_webui_all_in_one.package_analyzer.requirement import Requirement


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class PackageDependencies(TypedDict):
    """
    包依赖分类结构的类型定义

    用于描述 Python 包的依赖项分类, 包括必选依赖和可选依赖分组

    Attributes:
        mandatory (list[str]):
            必选依赖列表, 存储格式为 name[extras]version, 例如 "requests>=2.0.0"
        optional (dict[str, list[str]]):
            可选依赖字典, Key 为规范化后的 extra 分组名, Value 为该分组下的依赖列表

    Examples:
        ```python
        deps = {
            "mandatory": ["requests>=2.0.0", "numpy>=1.0.0"],
            "optional": {
                "dev": ["pytest>=6.0.0"],
                "gpu": ["torch>=1.0.0"]
            }
        }
        ```
    """

    mandatory: list[str]
    """必选依赖列表, 存储格式为 name[extras]version"""

    optional: dict[str, list[str]]
    """可选依赖字典, Key 为规范化后的 extra 分组名, Value 为该分组下的依赖列表"""


def get_categorized_dependencies(
    package_name: str,
) -> PackageDependencies:
    """
    获取分类后的依赖字典, 依赖项以“名称[extra]版本”的合并格式展示 (不含环境标记)
    从包的元数据中解析依赖项, 并根据环境标记将其分类为必选依赖和可选依赖.
    环境标记不适用于当前环境的依赖不会出现在结果中

    Args:
        package_name (str):
            要分析的包名称, 必须已安装

    Returns:
        PackageDependencies: 分类后的依赖字典

    Examples:
        ```python
        deps = get_categorized_dependencies("requests")
        print(deps["mandatory"])  # ['urllib3>=1.21.1,<3']
        print(deps["optional"])   # {'socks': ['PySocks>=1.5.6,!=1.5.7']}
        ```"""
    result: PackageDependencies = {"mandatory": [], "optional": {}}

    for text in requires(package_name) or []:
        try:
            requirement = Requirement.parse(text)
        except InvalidRequirement as e:
            logger.error("解析依赖 '%s' 失败: %s", text, e.message)
            continue

        declaration = str(Requirement(requirement.name, requirement.extras, requirement.specifier, requirement.url))

        extra_names = sorted(requirement.marker.extra_names()) if requirement.marker is not None else []
        if not extra_names:
            if requirement.applies_to():
                result["mandatory"].append(declaration)
            continue

        for extra_name in extra_names:
            if requirement.applies_to({"extra": extra_name}):
                result["optional"].setdefault(extra_name, []).append(declaration)

    return result
