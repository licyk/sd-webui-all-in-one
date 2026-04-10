"""Python 软件包依赖声明解析器

基于 PEP 508 规范实现依赖声明解析, 并提供 requirements 文件的解析与标准化功能.

参考:
    - https://peps.python.org/pep-0508/
    - https://peps.python.org/pep-0440/
"""

import os
import re
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
    # 延迟导入避免循环依赖
    from sd_webui_all_in_one.package_analyzer.version_utils import (
        get_correct_package_name,
        get_package_name,
        get_package_version,
        is_package_has_version,
        remove_optional_dependence_from_package,
        version_string_is_canonical,
    )
    from sd_webui_all_in_one.package_analyzer.wheel_parser import (
        parse_wheel_to_package_name,
    )

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
