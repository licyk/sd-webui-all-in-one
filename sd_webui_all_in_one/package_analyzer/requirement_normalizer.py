"""Python 软件包依赖声明标准化器

将原始的 requirements 列表标准化为规范的软件包声明列表.
此模块是高层编排模块, 组合使用底层解析器和工具函数完成标准化流程.

分层设计:
    底层: ``py_whl_parse`` (PEP 508 解析器), ``py_ver_cmp`` (PEP 440 版本比较)
    中层: ``version_utils`` (版本字符串工具), ``wheel_parser`` (Wheel 文件名解析),
          ``requirement_parser`` (依赖声明解析)
    高层: ``requirement_normalizer`` (本模块, 依赖标准化编排)
    最高层: ``installation_checker`` (安装状态检查)

参考:
    - https://peps.python.org/pep-0508/
    - https://peps.python.org/pep-0440/
"""

import os
import re

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.package_analyzer.version_utils import (
    get_correct_package_name,
    get_package_version,
    is_package_has_version,
    remove_optional_dependence_from_package,
    version_string_is_canonical,
)
from sd_webui_all_in_one.package_analyzer.wheel_parser import parse_wheel_to_package_name
from sd_webui_all_in_one.package_analyzer.requirement_parser import parse_requirement_to_list


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


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

        if requirement.startswith("https://") or requirement.startswith("http://"):
            package_name = parse_wheel_to_package_name(os.path.basename(requirement))
            package_list.append(package_name)
            continue

        possble_requirement = parse_requirement_to_list(requirement)
        if len(possble_requirement) == 0:
            continue
        elif len(possble_requirement) == 1:
            # 单个约束, 直接添加 (已由 parse_requirement_to_list 标准化)
            format_package_name = remove_optional_dependence_from_package(possble_requirement[0].strip())
            package_list.append(format_package_name)
        else:
            # 多个约束 (如 protobuf<5,>=4.25.3 -> ["protobuf<5", "protobuf>=4.25.3"])
            # 递归处理每个独立约束
            requirements_list = parse_requirement_list(possble_requirement)
            package_list += requirements_list
            continue

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
