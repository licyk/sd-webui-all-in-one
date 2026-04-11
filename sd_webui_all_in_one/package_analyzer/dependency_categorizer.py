"""依赖导出工具"""

from importlib.metadata import requires
from typing import TypedDict

from sd_webui_all_in_one.package_analyzer import (
    evaluate_marker,
    parse_requirement,
)
from sd_webui_all_in_one.package_analyzer.py_whl_parse import get_parse_bindings


class PackageDependencies(TypedDict):
    """
    包依赖分类结构的类型定义

    用于描述 Python 包的依赖项分类, 包括必选依赖和可选依赖分组

    Attributes:
        mandatory (list[str]):
            必选依赖列表, 存储格式为 name[extras]version, 例如 "requests>=2.0.0"
        optional (dict[str, list[str]]):
            可选依赖字典, Key 为 extra 分组名, Value 为该分组下的依赖列表

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
    """可选依赖字典, Key 为 extra 分组名, Value 为该分组下的依赖列表"""


def format_requirement(
    name: str,
    extras: list[str],
    version_specs: list[tuple[str, str]] | str,
) -> str:
    """
    将解析出的组件重新拼装为标准的依赖字符串

    Args:
        name (str):
            包名称
        extras (list[str]):
            可选依赖列表, 例如 ["dev", "test"]
        version_specs (list[tuple[str, str]] | str):
            版本规范列表, 格式为 [('>=', '1.0.0'), ('<', '2.0.0')] 或字符串

    Returns:
        str: 格式化后的依赖字符串, 例如 "requests[dev]>=1.0.0,<2.0.0"

    Examples:
        ```python
        # 基本用法
        result = format_requirement("requests", [], [('>=', '2.0.0')])
        # 输出: "requests>=2.0.0"

        # 带 extras
        result = format_requirement("torch", ["cuda"], [('>=', '1.0.0')])
        # 输出: "torch[cuda]>=1.0.0"
        ```
    """
    res = name

    # 合并 extras: name[extra1,extra2]
    if extras:
        res += f"[{','.join(extras)}]"

    # 合并版本号: name>=1.0.0,<=2.0.0
    if version_specs:
        # version_specs 格式通常为 [('>=', '1.0.0'), ('<', '2.0.0')]
        specs_str = ",".join([f"{op}{ver}" for op, ver in version_specs])
        res += specs_str

    return res


def get_categorized_dependencies(
    package_name: str,
) -> PackageDependencies:
    """
    获取分类后的依赖字典, 依赖项以“名称[extra]版本”的合并格式展示
    从包的元数据中解析依赖项, 并根据 marker 将其分类为必选依赖和可选依赖

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
    raw_reqs = requires(package_name)
    bindings = get_parse_bindings()
    result: PackageDependencies = {"mandatory": [], "optional": {}}

    if not raw_reqs:
        return result

    for req_str in raw_reqs:
        try:
            name, extras, version_specs, marker = parse_requirement(req_str, bindings)

            # 拼装成合并后的字符串
            full_req_name = format_requirement(name, extras, version_specs)

            is_optional = False
            if marker and isinstance(marker, (list, tuple)):
                if "extra" in marker:
                    # 获取 marker 中的 extra 分组名称
                    extra_group = marker[-1]
                    if extra_group not in result["optional"]:
                        result["optional"][extra_group] = []

                    result["optional"][extra_group].append(full_req_name)
                    is_optional = True

            if not is_optional:
                # 检查非 extra 的 marker (如 Python 版本环境标记)
                if evaluate_marker(marker):
                    result["mandatory"].append(full_req_name)

        except Exception as e:
            print(f"解析依赖 '{req_str}' 失败: {e}")

    return result
