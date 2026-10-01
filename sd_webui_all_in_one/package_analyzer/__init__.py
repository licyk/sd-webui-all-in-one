"""Python 软件包分析工具包

提供 Python 软件包的版本比较、依赖解析、安装验证等功能.

模块分层结构 (上层只依赖下层):
    规范实现:
        - ``errors``: 异常与诊断信息
        - ``names``: 软件包名 / extra 名的校验与规范化
        - ``version``: 版本号对象
        - ``specifiers``: 版本约束对象
        - ``markers``: 环境标记的解析与求值
        - ``requirement``: 依赖声明对象
        - ``filenames``: Wheel / 源码包文件名解析
    依赖文件:
        - ``reqfile``: requirements 文件解析 (选项, 续行, 嵌套文件, URL / 本地路径 / 可编辑条目)
        - ``local_project``: 本地项目目录的静态元数据读取
    环境检查:
        - ``installed``: 已安装分发的信息读取
        - ``dependency_categorizer``: 已安装软件包的依赖分类
        - ``checker``: 依赖满足状态检查
    其他:
        - ``ver_cmp``: 通用版本比较器 (用于不遵循 Python 版本标识符规范的版本号)
"""

# 规范实现
from sd_webui_all_in_one.package_analyzer.errors import (
    Diagnostic,
    InvalidMarker,
    InvalidName,
    InvalidRequirement,
    InvalidSdistFilename,
    InvalidSpecifier,
    InvalidVersion,
    InvalidWheelFilename,
    NestedFileNotFound,
    PackageAnalyzerError,
    RecursiveInclude,
    RequirementsFileError,
    UndefinedEnvironmentName,
    UnsupportedOption,
)
from sd_webui_all_in_one.package_analyzer.names import (
    is_valid_name,
    normalize_extra,
    normalize_name,
)
from sd_webui_all_in_one.package_analyzer.version import Version
from sd_webui_all_in_one.package_analyzer.specifiers import (
    Specifier,
    SpecifierSet,
)
from sd_webui_all_in_one.package_analyzer.markers import (
    Marker,
    MarkerEnvironment,
    default_environment,
)
from sd_webui_all_in_one.package_analyzer.requirement import Requirement
from sd_webui_all_in_one.package_analyzer.filenames import (
    SdistFilename,
    WheelFilename,
    WheelTag,
)

# 依赖文件解析
from sd_webui_all_in_one.package_analyzer.reqfile import (
    EntryKind,
    FileOptions,
    RequirementEntry,
    RequirementsFile,
    SourceLocation,
    parse_requirements_file,
    parse_requirements_text,
)

# 环境检查
from sd_webui_all_in_one.package_analyzer.installed import (
    InstalledDistribution,
    get_installed_distribution,
    get_package_version_from_library,
)
from sd_webui_all_in_one.package_analyzer.dependency_categorizer import (
    PackageDependencies,
    get_categorized_dependencies,
)
from sd_webui_all_in_one.package_analyzer.checker import (
    CheckResult,
    CheckStatus,
    check_entry,
    check_requirement,
    check_requirements_file,
    get_missing_package_metadata_dependencies,
    is_package_installed,
    validate_package_metadata_dependencies,
    validate_requirements,
)

# 通用版本比较
from sd_webui_all_in_one.package_analyzer.ver_cmp import (
    CommonVersionComparison,
    version_increment,
    version_decrement,
)

__all__ = [
    # errors
    "Diagnostic",
    "InvalidMarker",
    "InvalidName",
    "InvalidRequirement",
    "InvalidSdistFilename",
    "InvalidSpecifier",
    "InvalidVersion",
    "InvalidWheelFilename",
    "NestedFileNotFound",
    "PackageAnalyzerError",
    "RecursiveInclude",
    "RequirementsFileError",
    "UndefinedEnvironmentName",
    "UnsupportedOption",
    # names / version / specifiers / markers / requirement / filenames
    "is_valid_name",
    "normalize_extra",
    "normalize_name",
    "Version",
    "Specifier",
    "SpecifierSet",
    "Marker",
    "MarkerEnvironment",
    "default_environment",
    "Requirement",
    "SdistFilename",
    "WheelFilename",
    "WheelTag",
    # reqfile
    "EntryKind",
    "FileOptions",
    "RequirementEntry",
    "RequirementsFile",
    "SourceLocation",
    "parse_requirements_file",
    "parse_requirements_text",
    # installed / dependency_categorizer / checker
    "InstalledDistribution",
    "get_installed_distribution",
    "get_package_version_from_library",
    "PackageDependencies",
    "get_categorized_dependencies",
    "CheckResult",
    "CheckStatus",
    "check_entry",
    "check_requirement",
    "check_requirements_file",
    "get_missing_package_metadata_dependencies",
    "is_package_installed",
    "validate_package_metadata_dependencies",
    "validate_requirements",
    # ver_cmp
    "CommonVersionComparison",
    "version_increment",
    "version_decrement",
]
