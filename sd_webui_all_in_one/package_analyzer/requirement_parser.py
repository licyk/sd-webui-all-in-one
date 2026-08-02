"""Python 软件包依赖声明解析器

基于 PEP 508 规范实现依赖声明解析, 并提供 requirements 文件的解析与标准化功能.

参考:
    - https://peps.python.org/pep-0508/
    - https://peps.python.org/pep-0440/
"""

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


def _compare_marker_versions(
    op: str,
    left: str,
    right: str,
) -> bool:
    """比较 marker 表达式中的版本号

    优先使用 PEP 440 语义比较, 失败时回退到字符串比较.

    Args:
        op (str):
            比较操作符
        left (str):
            左操作数 (已转为小写)
        right (str):
            右操作数 (已转为小写)

    Returns:
        bool: 比较结果
    """
    try:
        left_ver = PyWhlVersionComparison(left)
        right_ver = PyWhlVersionComparison(right)

        if op == "~=":
            matcher = right_ver.compatible_version_matcher(right)
            return matcher(left)
        if op == "===":
            return left == right

        comparators = {
            "<": lambda: left_ver < right_ver,
            "<=": lambda: left_ver <= right_ver,
            ">": lambda: left_ver > right_ver,
            ">=": lambda: left_ver >= right_ver,
            "==": lambda: left_ver == right_ver,
            "!=": lambda: left_ver != right_ver,
        }
        fn = comparators.get(op)
        return fn() if fn else False
    except Exception:
        # 回退到字符串比较
        if op == "~=":
            # ~= X.Y 等价于 >= X.Y, == X.*
            # 字符串回退: 检查前缀匹配 + 字符串 >=
            parts = right.split(".")
            if len(parts) >= 2:
                prefix = ".".join(parts[:-1]) + "."
                return left >= right and left.startswith(prefix)
            return left >= right
        if op == "===":
            return left == right

        string_comparators = {
            "<": lambda: left < right,
            "<=": lambda: left <= right,
            ">": lambda: left > right,
            ">=": lambda: left >= right,
            "==": lambda: left == right,
            "!=": lambda: left != right,
        }
        fn = string_comparators.get(op)
        return fn() if fn else False


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

    if not isinstance(marker, tuple):
        return False

    op = marker[0]

    # 逻辑运算
    if op in ("and", "or"):
        left = evaluate_marker(marker[1])
        right = evaluate_marker(marker[2])
        return (left and right) if op == "and" else (left or right)

    left = str(marker[1]).lower()
    right = str(marker[2]).lower()

    # 字符串包含操作
    if op == "in":
        return left in right
    if op == "not in":
        return left not in right

    # 版本比较操作
    if op in ("<", "<=", ">", ">=", "==", "!=", "~=", "==="):
        return _compare_marker_versions(op, left, right)

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
