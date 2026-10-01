"""依赖文件 (``requirements.txt`` 格式) 解析

模块结构:
    - ``lexer``: 解码, 续行合并, 注释移除, 环境变量展开
    - ``options``: 命令行风格选项解析
    - ``model``: 解析结果的数据模型
    - ``parser``: 条目分类与嵌套文件处理
"""

from sd_webui_all_in_one.package_analyzer.reqfile.lexer import (
    DIRECTIVE_SKIP_VERIFY,
    LogicalLine,
    decode_requirements,
    expand_env_variables,
    iter_logical_lines,
)
from sd_webui_all_in_one.package_analyzer.reqfile.model import (
    EntryKind,
    FileOptions,
    RequirementEntry,
    RequirementsFile,
    SourceLocation,
)
from sd_webui_all_in_one.package_analyzer.reqfile.options import (
    ParsedOption,
    parse_options,
    split_args_and_options,
)
from sd_webui_all_in_one.package_analyzer.reqfile.parser import (
    is_url,
    looks_like_path,
    parse_requirements_file,
    parse_requirements_text,
)

__all__ = [
    "DIRECTIVE_SKIP_VERIFY",
    "LogicalLine",
    "decode_requirements",
    "expand_env_variables",
    "iter_logical_lines",
    "EntryKind",
    "FileOptions",
    "RequirementEntry",
    "RequirementsFile",
    "SourceLocation",
    "ParsedOption",
    "parse_options",
    "split_args_and_options",
    "is_url",
    "looks_like_path",
    "parse_requirements_file",
    "parse_requirements_text",
]
