"""Python 软件包检查工具"""

import os
import re
import importlib.metadata
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


def version_string_is_canonical(
    version: str,
) -> bool:
    """判断版本号标识符是否符合标准

    Args:
        version (str): 版本号字符串
    Returns:
        bool: 如果版本号标识符符合 PEP 440 标准, 则返回`True`
    """
    return (
        re.match(
            r"^([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?$",
            version,
        )
        is not None
    )


def is_package_has_version(
    package: str,
) -> bool:
    """检查 Python 软件包是否指定版本号

    Args:
        package (str): Python 软件包名

    Returns:
        bool: 如果 Python 软件包存在版本声明, 如`torch==2.3.0`, 则返回`True`
    """
    return package != (package.replace("===", "").replace("~=", "").replace("!=", "").replace("<=", "").replace(">=", "").replace("<", "").replace(">", "").replace("==", ""))


def get_package_name(
    package: str,
) -> str:
    """获取 Python 软件包的包名, 去除末尾的版本声明

    Args:
        package (str): Python 软件包名

    Returns:
        str: 返回去除版本声明后的 Python 软件包名
    """
    return package.split("===")[0].split("~=")[0].split("!=")[0].split("<=")[0].split(">=")[0].split("<")[0].split(">")[0].split("==")[0].strip()


def get_package_version(
    package: str,
) -> str:
    """获取 Python 软件包的包版本号

    Args:
        package (str): Python 软件包名

    返回值:
        str: 返回 Python 软件包的包版本号
    """
    return package.split("===").pop().split("~=").pop().split("!=").pop().split("<=").pop().split(">=").pop().split("<").pop().split(">").pop().split("==").pop().strip()


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
"""解析 Python Wheel 名的的正则表达式"""

REPLACE_PACKAGE_NAME_DICT = {
    "sam2": "SAM-2",
}
"""Python 软件包名替换表"""


def parse_wheel_filename(
    filename: str,
) -> str:
    """解析 Python wheel 文件名并返回 distribution 名称

    Args:
        filename (str): wheel 文件名, 例如 pydantic-1.10.15-py3-none-any.whl
    Returns:
        str: distribution 名称, 例如 pydantic
    Raises:
        ValueError: 如果文件名不符合 PEP491 规范
    """
    match = re.fullmatch(WHEEL_PATTERN, filename, re.VERBOSE)
    if not match:
        logger.debug("未知的 Wheel 文件名: %s", filename)
        raise ValueError(f"未知的 Wheel 文件名: {filename}")
    return match.group("distribution")


def parse_wheel_version(
    filename: str,
) -> str:
    """解析 Python wheel 文件名并返回 version 名称

    Args:
        filename (str): wheel 文件名, 例如 pydantic-1.10.15-py3-none-any.whl
    Returns:
        str: version 名称, 例如 1.10.15
    Raises:
        ValueError: 如果文件名不符合 PEP491 规范
    """
    match = re.fullmatch(WHEEL_PATTERN, filename, re.VERBOSE)
    if not match:
        logger.debug("未知的 Wheel 文件名: %s", filename)
        raise ValueError(f"未知的 Wheel 文件名: {filename}")
    return match.group("version")


def parse_wheel_to_package_name(
    filename: str,
) -> str:
    """解析 Python wheel 文件名并返回 <distribution>==<version>

    Args:
        filename (str): wheel 文件名, 例如 pydantic-1.10.15-py3-none-any.whl

    Returns:
        str: <distribution>==<version> 名称, 例如 pydantic==1.10.15
    """
    distribution = parse_wheel_filename(filename)
    version = parse_wheel_version(filename)
    return f"{distribution}=={version}"


def remove_optional_dependence_from_package(
    filename: str,
) -> str:
    """移除 Python 软件包声明中可选依赖

    Args:
        filename (str): Python 软件包名

    Returns:
        str: 移除可选依赖后的软件包名, e.g. diffusers[torch]==0.10.2 -> diffusers==0.10.2
    """
    return re.sub(r"\[.*?\]", "", filename)


def get_correct_package_name(
    name: str,
) -> str:
    """将原 Python 软件包名替换成正确的 Python 软件包名

    Args:
        name (str): 原 Python 软件包名
    Returns:
        str: 替换成正确的软件包名, 如果原有包名正确则返回原包名
    """
    return REPLACE_PACKAGE_NAME_DICT.get(name, name)


def parse_requirement(
    text: str,
    bindings: dict[str, str],
) -> ParsedPyWhlRequirement:
    """解析依赖声明的主函数

    Args:
        text (str): 依赖声明文本
        bindings (dict[str, str]): 解析 Python 软件包名的语法字典

    Returns:
        ParsedPyWhlRequirement: 解析结果元组
    """
    parser = RequirementParser(text, bindings)
    return parser.parse()


def evaluate_marker(
    marker: Any,
) -> bool:
    """评估 marker 表达式, 判断当前环境是否符合要求

    Args:
        marker (Any): marker 表达式
    Returns:
        bool: 评估结果
    """
    if marker is None:
        return True

    if isinstance(marker, tuple):
        op = marker[0]

        if op in ("and", "or"):
            left = evaluate_marker(marker[1])
            right = evaluate_marker(marker[2])

            if op == "and":
                return left and right
            else:  # 'or'
                return left or right
        else:
            # 处理比较操作
            left = marker[1]
            right = marker[2]

            if op in ["<", "<=", ">", ">=", "==", "!=", "~=", "==="]:
                try:
                    left_ver = PyWhlVersionComparison(str(left).lower())
                    right_ver = PyWhlVersionComparison(str(right).lower())

                    if op == "<":
                        return left_ver < right_ver
                    elif op == "<=":
                        return left_ver <= right_ver
                    elif op == ">":
                        return left_ver > right_ver
                    elif op == ">=":
                        return left_ver >= right_ver
                    elif op == "==":
                        return left_ver == right_ver
                    elif op == "!=":
                        return left_ver != right_ver
                    elif op == "~=":
                        return left_ver >= ~right_ver
                    elif op == "===":
                        # 任意相等, 直接比较字符串
                        return str(left).lower() == str(right).lower()
                except Exception:
                    # 如果版本比较失败, 回退到字符串比较
                    left_str = str(left).lower()
                    right_str = str(right).lower()
                    if op == "<":
                        return left_str < right_str
                    elif op == "<=":
                        return left_str <= right_str
                    elif op == ">":
                        return left_str > right_str
                    elif op == ">=":
                        return left_str >= right_str
                    elif op == "==":
                        return left_str == right_str
                    elif op == "!=":
                        return left_str != right_str
                    elif op == "~=":
                        # 简化处理
                        return left_str >= right_str
                    elif op == "===":
                        return left_str == right_str

            # 处理 in 和 not in 操作
            elif op == "in":
                # 将右边按逗号分割, 检查左边是否在其中
                values = [v.strip() for v in str(right).lower().split(",")]
                return str(left).lower() in values

            elif op == "not in":
                # 将右边按逗号分割, 检查左边是否不在其中
                values = [v.strip() for v in str(right).lower().split(",")]
                return str(left).lower() not in values

    return False


def parse_requirement_to_list(
    text: str,
) -> list[str]:
    """解析依赖声明并返回依赖列表

    Args:
        text (str): 依赖声明
    Returns:
        list[str]: 解析后的依赖声明表
    """
    try:
        bindings = get_parse_bindings()
        name, _, version_specs, marker = parse_requirement(text, bindings)
    except Exception as e:
        logger.debug("解析失败: %s", e)
        return []

    # 检查marker条件
    if not evaluate_marker(marker):
        return []

    # 构建依赖列表
    dependencies = []

    # 如果是 URL 依赖
    if isinstance(version_specs, str):
        # URL 依赖只返回包名
        dependencies.append(name)
    else:
        # 版本依赖
        if version_specs:
            # 有版本约束, 为每个约束创建一个依赖项
            for op, version in version_specs:
                dependencies.append(f"{name}{op}{version}")
        else:
            # 没有版本约束, 只返回包名
            dependencies.append(name)

    return dependencies


def parse_requirement_list(
    requirements: list[str],
) -> list[str]:
    """将 Python 软件包声明列表解析成标准 Python 软件包名列表

    例如有以下的 Python 软件包声明列表:
    ```python
    requirements = [
        'torch==2.3.0',
        'diffusers[torch]==0.10.2',
        'NUMPY',
        '-e .',
        '--index-url https://pypi.python.org/simple',
        '--extra-index-url https://download.pytorch.org/whl/cu124',
        '--find-links https://download.pytorch.org/whl/torch_stable.html',
        '-e git+https://github.com/Nerogar/mgds.git@2c67a5a#egg=mgds',
        'git+https://github.com/WASasquatch/img2texture.git',
        'https://github.com/Panchovix/pydantic-fixreforge/releases/download/main_v1/pydantic-1.10.15-py3-none-any.whl',
        'prodigy-plus-schedule-free==1.9.1 # prodigy+schedulefree optimizer',
        'protobuf<5,>=4.25.3',
    ]
    ```

    上述例子中的软件包名声明列表将解析成:
    ```python
        requirements = [
            'torch==2.3.0',
            'diffusers==0.10.2',
            'numpy',
            'mgds',
            'img2texture',
            'pydantic==1.10.15',
            'prodigy-plus-schedule-free==1.9.1',
            'protobuf<5',
            'protobuf>=4.25.3',
        ]
    ```

    Args:
        requirements (list[str]): Python 软件包名声明列表

    Returns:
        list[str]: 将 Python 软件包名声明列表解析成标准声明列表
    """

    def _extract_repo_name(url_string: str) -> str | None:
        """从包含 Git 仓库 URL 的字符串中提取仓库名称

        Args:
            url_string (str): 包含 Git 仓库 URL 的字符串

        Returns:
            (str | None): 提取到的仓库名称, 如果未找到则返回 None
        """
        # 模式1: 匹配 git+https:// 或 git+ssh:// 开头的 URL
        # 模式2: 匹配直接以 git+ 开头的 URL
        patterns = [
            # 匹配 git+protocol://host/path/to/repo.git 格式
            r"git\+[a-z]+://[^/]+/(?:[^/]+/)*([^/@]+?)(?:\.git)?(?:@|$)",
            # 匹配 git+https://host/owner/repo.git 格式
            r"git\+https://[^/]+/[^/]+/([^/@]+?)(?:\.git)?(?:@|$)",
            # 匹配 git+ssh://git@host:owner/repo.git 格式
            r"git\+ssh://git@[^:]+:[^/]+/([^/@]+?)(?:\.git)?(?:@|$)",
            # 通用模式: 匹配最后一个斜杠后的内容, 直到遇到 @ 或 .git 或字符串结束
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
        # 清理注释内容
        # prodigy-plus-schedule-free==1.9.1 # prodigy+schedulefree optimizer -> prodigy-plus-schedule-free==1.9.1
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

        # -e git+https://github.com/Nerogar/mgds.git@2c67a5a#egg=mgds -> mgds
        # git+https://github.com/WASasquatch/img2texture.git -> img2texture
        # git+https://github.com/deepghs/waifuc -> waifuc
        # -e git+https://github.com/Nerogar/mgds.git@2c67a5a -> mgds
        # git+ssh://git@github.com:licyk/sd-webui-all-in-one@dev -> sd-webui-all-in-one
        # git+https://gitlab.com/user/my-project.git@main -> my-project
        # git+ssh://git@bitbucket.org:team/repo-name.git@develop -> repo-name
        # https://github.com/another/repo.git -> repo
        # git@github.com:user/repository.git -> repository
        if requirement.startswith("-e git+http") or requirement.startswith("git+http") or requirement.startswith("-e git+ssh://") or requirement.startswith("git+ssh://"):
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

        # https://github.com/Panchovix/pydantic-fixreforge/releases/download/main_v1/pydantic-1.10.15-py3-none-any.whl -> pydantic==1.10.15
        if requirement.startswith("https://") or requirement.startswith("http://"):
            package_name = parse_wheel_to_package_name(os.path.basename(requirement))
            package_list.append(package_name)
            continue

        # 常规 Python 软件包声明
        # 解析版本列表
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

    # 处理包名大小写并统一成小写
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
        file_path (str | Path): requirements.txt 文件路径

    Returns:
        list[str]: 从 requirements.txt 文件中读取的 Python 软件包声明列表
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.readlines()
    except Exception as e:
        logger.debug("打开 %s 时出现错误: %s\n请检查文件是否出现损坏", file_path, e)
        return []


def get_package_version_from_library(
    package_name: str,
) -> str | None:
    """获取已安装的 Python 软件包版本号

    Args:
        package_name (str): Python 软件包名

    Returns:
        (str | None): 如果获取到 Python 软件包版本号则返回版本号字符串, 否则返回`None`
    """
    try:
        ver = importlib.metadata.version(package_name)
    except Exception as _:
        ver = None

    if ver is None:
        try:
            ver = importlib.metadata.version(package_name.lower())
        except Exception as _:
            ver = None

    if ver is None:
        try:
            ver = importlib.metadata.version(package_name.replace("_", "-"))
        except Exception as _:
            ver = None

    return ver


def is_package_installed(
    package: str,
) -> bool:
    """判断 Python 软件包是否已安装在环境中

    Args:
        package (str): Python 软件包名

    Returns:
        bool: 如果 Python 软件包未安装或者未安装正确的版本, 则返回`False`
    """
    # 分割 Python 软件包名和版本号
    if "===" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split("===")]
    elif "~=" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split("~=")]
    elif "!=" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split("!=")]
    elif "<=" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split("<=")]
    elif ">=" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split(">=")]
    elif "<" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split("<")]
    elif ">" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split(">")]
    elif "==" in package:
        pkg_name, pkg_version = [x.strip() for x in package.split("==")]
    else:
        pkg_name, pkg_version = package.strip(), None

    env_pkg_version = get_package_version_from_library(pkg_name)
    logger.debug(
        "已安装 Python 软件包检测: pkg_name: %s, env_pkg_version: %s, pkg_version: %s",
        pkg_name,
        env_pkg_version,
        pkg_version,
    )

    if env_pkg_version is None:
        return False

    if pkg_version is not None:
        # ok = env_pkg_version === / == pkg_version
        if "===" in package or "==" in package:
            logger.debug("包含条件: === / ==")
            logger.debug("%s == %s ?", env_pkg_version, pkg_version)
            if PyWhlVersionComparison(env_pkg_version) == PyWhlVersionComparison(pkg_version):
                logger.debug("%s == %s 条件成立", env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version ~= pkg_version
        if "~=" in package:
            logger.debug("包含条件: ~=")
            logger.debug("%s ~= %s ?", env_pkg_version, pkg_version)
            if PyWhlVersionComparison(env_pkg_version) == ~PyWhlVersionComparison(pkg_version):
                logger.debug("%s == %s 条件成立", env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version != pkg_version
        if "!=" in package:
            logger.debug("包含条件: !=")
            logger.debug("%s != %s ?", env_pkg_version, pkg_version)
            if PyWhlVersionComparison(env_pkg_version) != PyWhlVersionComparison(pkg_version):
                logger.debug("%s != %s 条件成立", env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version <= pkg_version
        if "<=" in package:
            logger.debug("包含条件: <=")
            logger.debug("%s <= %s ?", env_pkg_version, pkg_version)
            if PyWhlVersionComparison(env_pkg_version) <= PyWhlVersionComparison(pkg_version):
                logger.debug("%s <= %s 条件成立", env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version >= pkg_version
        if ">=" in package:
            logger.debug("包含条件: >=")
            logger.debug("%s >= %s ?", env_pkg_version, pkg_version)
            if PyWhlVersionComparison(env_pkg_version) >= PyWhlVersionComparison(pkg_version):
                logger.debug("%s >= %s 条件成立", env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version < pkg_version
        if "<" in package:
            logger.debug("包含条件: <")
            logger.debug("%s < %s ?", env_pkg_version, pkg_version)
            if PyWhlVersionComparison(env_pkg_version) < PyWhlVersionComparison(pkg_version):
                logger.debug("%s < %s 条件成立", env_pkg_version, pkg_version)
                return True

        # ok = env_pkg_version > pkg_version
        if ">" in package:
            logger.debug("包含条件: >")
            logger.debug("%s > %s ?", env_pkg_version, pkg_version)
            if PyWhlVersionComparison(env_pkg_version) > PyWhlVersionComparison(pkg_version):
                logger.debug("%s > %s 条件成立", env_pkg_version, pkg_version)
                return True

        logger.debug("%s 需要安装", package)
        return False

    return True


def validate_requirements(
    requirement_path: str | Path,
) -> bool:
    """检测环境依赖是否完整

    Args:
        requirement_path (str | Path): 依赖文件路径

    Returns:
        bool: 如果有缺失依赖则返回`False`
    """
    origin_requires = read_packages_from_requirements_file(requirement_path)
    requires = parse_requirement_list(origin_requires)
    for package in requires:
        if not is_package_installed(package):
            return False

    return True
