"""Python 软件包分析工具包

提供 Python 软件包的版本比较、依赖解析、安装验证等功能.

模块分层结构:
    底层:
        - ``py_whl_parse``: PEP 508 解析器基础设施
        - ``py_ver_cmp``: PEP 440 版本比较器
        - ``ver_cmp``: 通用版本比较器
    中层:
        - ``version_utils``: 版本字符串工具 (canonical 检查、包名/版本提取)
        - ``wheel_parser``: Wheel 文件名解析
        - ``requirement_parser``: PEP 508 依赖声明解析与 marker 评估
    高层:
        - ``requirement_normalizer``: 依赖声明标准化 (组合中层模块完成 requirements 列表标准化)
    最高层:
        - ``installation_checker``: 安装状态检查与依赖验证
"""

# 版本字符串工具
from sd_webui_all_in_one.package_analyzer.version_utils import (
    version_string_is_canonical,
    is_package_has_version,
    get_package_name,
    get_package_version,
    get_package_version_specs,
    remove_optional_dependence_from_package,
    get_correct_package_name,
)

# Wheel 文件名解析
from sd_webui_all_in_one.package_analyzer.wheel_parser import (
    parse_wheel_filename,
    parse_wheel_version,
    parse_wheel_to_package_name,
)

# Requirements 解析
from sd_webui_all_in_one.package_analyzer.py_whl_parse import (
    ParsedPyWhlRequirement,
    RequirementParser,
    get_parse_bindings,
)
from sd_webui_all_in_one.package_analyzer.requirement_parser import (
    parse_requirement,
    evaluate_marker,
    parse_requirement_to_list,
    read_packages_from_requirements_file,
)
from sd_webui_all_in_one.package_analyzer.requirement_normalizer import (
    parse_requirement_list,
)

# 依赖分类
from sd_webui_all_in_one.package_analyzer.dependency_categorizer import (
    PackageDependencies,
    format_requirement,
    get_categorized_dependencies,
)

# 安装状态检查
from sd_webui_all_in_one.package_analyzer.installation_checker import (
    get_package_version_from_library,
    is_package_installed,
    validate_requirements,
    parse_package_spec,
    check_version_constraint,
)

# PEP 440 版本比较
from sd_webui_all_in_one.package_analyzer.py_ver_cmp import (
    PyWhlVersionComparison,
    PyWhlVersionMatcher,
)

# 通用版本比较
from sd_webui_all_in_one.package_analyzer.ver_cmp import (
    CommonVersionComparison,
    version_increment,
    version_decrement,
)

__all__ = [
    # version_utils
    "version_string_is_canonical",
    "is_package_has_version",
    "get_package_name",
    "get_package_version",
    "get_package_version_specs",
    "remove_optional_dependence_from_package",
    "get_correct_package_name",
    # wheel_parser
    "parse_wheel_filename",
    "parse_wheel_version",
    "parse_wheel_to_package_name",
    # requirement_parser / py_whl_parse
    "ParsedPyWhlRequirement",
    "RequirementParser",
    "get_parse_bindings",
    "parse_requirement",
    "evaluate_marker",
    "parse_requirement_to_list",
    "parse_requirement_list",
    # dependency_categorizer
    "PackageDependencies",
    "format_requirement",
    "get_categorized_dependencies",
    "read_packages_from_requirements_file",
    # installation_checker
    "get_package_version_from_library",
    "is_package_installed",
    "validate_requirements",
    "parse_package_spec",
    "check_version_constraint",
    # py_ver_cmp
    "PyWhlVersionComparison",
    "PyWhlVersionMatcher",
    # ver_cmp
    "CommonVersionComparison",
    "version_increment",
    "version_decrement",
]
