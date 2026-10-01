"""依赖满足状态检查

判断依赖声明或依赖文件中的条目是否已被当前环境满足.

检查结果分为四种:
    - ``SATISFIED``: 已满足
    - ``UNSATISFIED``: 未安装或已安装版本不满足约束
    - ``UNKNOWN``: 条目有效但无法验证 (例如无法确定软件包名的 ``-e .``), 按已满足处理并给出警告
    - ``SKIPPED``: 条目不适用于当前环境 (环境标记不满足, 或声明了 ``# skip_verify``)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
)
from urllib.parse import (
    urlsplit,
)

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.package_analyzer.dependency_categorizer import get_categorized_dependencies
from sd_webui_all_in_one.package_analyzer.errors import (
    InvalidRequirement,
    UndefinedEnvironmentName,
)
from sd_webui_all_in_one.package_analyzer.local_project import file_url_path_to_local_path
from sd_webui_all_in_one.package_analyzer.installed import (
    InstalledDistribution,
    get_installed_distribution,
)
from sd_webui_all_in_one.package_analyzer.markers import MarkerEnvironment
from sd_webui_all_in_one.package_analyzer.names import (
    PACKAGE_NAME_ALIASES,
    normalize_extra,
    normalize_name,
)
from sd_webui_all_in_one.package_analyzer.reqfile.model import (
    EntryKind,
    RequirementEntry,
    RequirementsFile,
)
from sd_webui_all_in_one.package_analyzer.reqfile.parser import parse_requirements_file
from sd_webui_all_in_one.package_analyzer.requirement import Requirement
from sd_webui_all_in_one.package_analyzer.version import Version


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

InstalledLookup = Callable[[str], InstalledDistribution | None]
"""按软件包名查询已安装分发的函数"""


class CheckStatus(str, Enum):
    """依赖检查结果状态"""

    SATISFIED = "satisfied"
    """已满足"""

    UNSATISFIED = "unsatisfied"
    """未安装或版本不满足约束"""

    UNKNOWN = "unknown"
    """无法验证, 按已满足处理"""

    SKIPPED = "skipped"
    """不适用于当前环境"""


@dataclass(frozen=True)
class CheckResult:
    """依赖检查结果

    Attributes:
        status (CheckStatus):
            结果状态
        subject (str):
            被检查的依赖声明文本
        reason (str):
            结果说明
        entry (RequirementEntry | None):
            对应的依赖文件条目, 直接检查依赖声明时为 ``None``
    """

    status: CheckStatus
    subject: str
    reason: str = ""
    entry: RequirementEntry | None = None

    @property
    def ok(self) -> bool:
        """是否无需安装 (除 ``UNSATISFIED`` 以外的状态)

        Returns:
            bool: 是否无需安装 (除 ``UNSATISFIED`` 以外的状态)
        """
        return self.status != CheckStatus.UNSATISFIED

    def __str__(self) -> str:
        location = f"{self.entry.source}: " if self.entry is not None else ""
        return f"{location}{self.subject}: {self.reason}" if self.reason else f"{location}{self.subject}"


def _find_installed(
    name: str,
    lookup: InstalledLookup,
) -> InstalledDistribution | None:
    """查询已安装分发, 未找到时再按替换表中的别名查询

    Args:
        name (str):
            软件包名
        lookup (InstalledLookup):
            查询函数

    Returns:
        InstalledDistribution | None: 已安装分发, 未安装时为 ``None``
    """
    installed = lookup(name)
    if installed is not None:
        return installed
    alias = PACKAGE_NAME_ALIASES.get(name.lower())
    return lookup(alias) if alias is not None else None


def _normalize_url(
    url: str,
) -> str:
    """规范化 URL 以便比较安装来源

    去除 VCS 前缀, 认证信息, ``@revision``, 片段, 末尾的 ``/`` 与 ``.git``.

    Args:
        url (str):
            URL

    Returns:
        str: 规范化后的 URL
    """
    split = urlsplit(url)
    scheme = split.scheme.lower().split("+", 1)[-1]
    netloc = split.netloc.rsplit("@", 1)[-1].lower()
    path = split.path
    if "+" in split.scheme and "@" in path:
        path = path.rsplit("@", 1)[0]
    path = path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return f"{scheme}://{netloc}{path}"


def _same_path(
    left: Path,
    right: Path,
) -> bool:
    """判断两个本地路径是否指向同一位置

    Args:
        left (Path):
            第 1 个路径
        right (Path):
            第 2 个路径

    Returns:
        bool: 指向同一位置时返回 ``True``
    """

    def canonical(path: Path) -> str:
        return os.path.normcase(os.path.realpath(path))

    return canonical(left) == canonical(right)


def _origin_matches(
    direct_url: dict[str, Any],
    url: str | None,
    path: Path | None,
    revision: str | None,
    editable: bool,
) -> bool:
    """判断 ``direct_url.json`` 记录的安装来源是否与依赖条目一致

    Args:
        direct_url (dict[str, Any]):
            ``direct_url.json`` 的内容
        url (str | None):
            依赖条目的 URL
        path (Path | None):
            依赖条目的本地路径
        revision (str | None):
            依赖条目请求的 VCS 修订版本
        editable (bool):
            依赖条目是否为可编辑条目

    Returns:
        bool: 来源一致时返回 ``True``
    """
    recorded = direct_url.get("url")
    if not isinstance(recorded, str):
        return False

    if path is not None:
        split = urlsplit(recorded)
        if split.scheme.lower() != "file":
            return False
        dir_info = direct_url.get("dir_info")
        recorded_editable = isinstance(dir_info, dict) and bool(dir_info.get("editable"))
        return _same_path(Path(file_url_path_to_local_path(split.path)), path) and recorded_editable == editable

    if url is None or _normalize_url(recorded) != _normalize_url(url):
        return False
    if revision is None:
        return True
    vcs_info = direct_url.get("vcs_info")
    if not isinstance(vcs_info, dict):
        return False
    commit_id = vcs_info.get("commit_id")
    return vcs_info.get("requested_revision") == revision or (isinstance(commit_id, str) and commit_id.startswith(revision))


def _check_extras(
    installed: InstalledDistribution,
    extras: tuple[str, ...],
    environment: MarkerEnvironment | None,
    lookup: InstalledLookup,
    seen: set[tuple[str, str]],
) -> str | None:
    """检查已安装分发的 extras 所声明的依赖是否满足

    Args:
        installed (InstalledDistribution):
            已安装分发
        extras (tuple[str, ...]):
            请求的 extras
        environment (MarkerEnvironment | None):
            标记求值环境
        lookup (InstalledLookup):
            查询函数
        seen (set[tuple[str, str]]):
            已检查过的 ``(软件包名, extra)``, 用于避免循环依赖导致的无限递归

    Returns:
        str | None: 首个未满足的依赖的说明, 全部满足时为 ``None``
    """
    for extra in extras:
        key = (normalize_name(installed.name), normalize_extra(extra))
        if key in seen:
            continue
        seen.add(key)

        base_env: dict[str, Any] = dict(environment or {})
        base_env["extra"] = ""
        extra_env: dict[str, Any] = dict(environment or {})
        extra_env["extra"] = extra

        for text in installed.requires:
            try:
                dependency = Requirement.parse(text)
            except InvalidRequirement:
                continue
            if dependency.marker is None:
                continue
            try:
                # 只检查由该 extra 引入的依赖, 无条件依赖不在此处检查
                if dependency.marker.evaluate(base_env) or not dependency.marker.evaluate(extra_env):
                    continue
            except UndefinedEnvironmentName:
                continue
            result = _check_requirement(dependency, extra_env, lookup, seen)
            if result.status == CheckStatus.UNSATISFIED:
                return f"extra '{extra}' 的依赖 '{dependency.name}{dependency.specifier}' 未满足 ({result.reason})"
    return None


def _check_requirement(
    requirement: Requirement,
    environment: MarkerEnvironment | None,
    lookup: InstalledLookup,
    seen: set[tuple[str, str]],
) -> CheckResult:
    """检查依赖声明是否已满足

    Args:
        requirement (Requirement):
            依赖声明
        environment (MarkerEnvironment | None):
            标记求值环境
        lookup (InstalledLookup):
            查询函数
        seen (set[tuple[str, str]]):
            已检查过的 ``(软件包名, extra)``

    Returns:
        CheckResult: 检查结果
    """
    subject = str(requirement)

    try:
        if not requirement.applies_to(environment):
            return CheckResult(CheckStatus.SKIPPED, subject, "环境标记不满足, 不适用于当前环境")
    except UndefinedEnvironmentName as e:
        return CheckResult(CheckStatus.UNKNOWN, subject, f"无法对环境标记求值: {e}")

    installed = _find_installed(requirement.name, lookup)
    if installed is None:
        return CheckResult(CheckStatus.UNSATISFIED, subject, "未安装")

    if requirement.url is not None:
        direct_url = installed.direct_url
        if direct_url is None or not _origin_matches(direct_url, requirement.url, None, None, False):
            return CheckResult(CheckStatus.UNKNOWN, subject, f"已安装版本 {installed.version}, 但无法确认其安装来源与声明的 URL 一致")
    elif not requirement.specifier.contains(installed.version, prereleases=True):
        return CheckResult(CheckStatus.UNSATISFIED, subject, f"已安装版本 {installed.version} 不满足版本约束 '{requirement.specifier}'")

    problem = _check_extras(installed, requirement.extras, environment, lookup, seen)
    if problem is not None:
        return CheckResult(CheckStatus.UNSATISFIED, subject, problem)

    return CheckResult(CheckStatus.SATISFIED, subject, f"已安装版本 {installed.version}")


def check_requirement(
    requirement: Requirement,
    environment: MarkerEnvironment | None = None,
    lookup: InstalledLookup | None = None,
) -> CheckResult:
    """检查依赖声明是否已被当前环境满足

    规则:
        - 环境标记不满足时结果为 ``SKIPPED``
        - 未安装, 或已安装版本不满足版本约束时结果为 ``UNSATISFIED``.
          已安装版本为预发布版本时同样参与匹配
        - 请求了 extras 时, 还会检查已安装分发为这些 extras 声明的依赖
        - ``name @ url`` 形式的依赖在已安装但无法确认安装来源一致时结果为 ``UNKNOWN``

    Args:
        requirement (Requirement):
            依赖声明
        environment (MarkerEnvironment | None):
            标记求值环境, 为 ``None`` 时使用当前解释器环境
        lookup (InstalledLookup | None):
            查询已安装分发的函数, 为 ``None`` 时查询当前环境

    Returns:
        CheckResult: 检查结果
    """
    return _check_requirement(requirement, environment, lookup or get_installed_distribution, set())


def check_entry(
    entry: RequirementEntry,
    environment: MarkerEnvironment | None = None,
    lookup: InstalledLookup | None = None,
) -> CheckResult:
    """检查依赖文件条目是否已被当前环境满足

    规则:
        - 声明了 ``# skip_verify`` 或环境标记不满足的条目结果为 ``SKIPPED``
        - 约束条目只在对应软件包已安装时检查版本
        - URL / 本地路径条目: 无法确定软件包名时结果为 ``UNKNOWN``; 未安装时为 ``UNSATISFIED``;
          能从 Wheel 文件名得知版本时比较版本; 否则对比 ``direct_url.json`` 记录的安装来源,
          无法确认来源一致时为 ``UNKNOWN``

    Args:
        entry (RequirementEntry):
            依赖文件条目
        environment (MarkerEnvironment | None):
            标记求值环境, 为 ``None`` 时使用当前解释器环境
        lookup (InstalledLookup | None):
            查询已安装分发的函数, 为 ``None`` 时查询当前环境

    Returns:
        CheckResult: 检查结果
    """
    lookup = lookup or get_installed_distribution
    subject = str(entry)

    if entry.skip_verify:
        return CheckResult(CheckStatus.SKIPPED, subject, "已通过 skip_verify 指令跳过检查", entry)

    try:
        if not entry.applies_to(environment):
            return CheckResult(CheckStatus.SKIPPED, subject, "环境标记不满足, 不适用于当前环境", entry)
    except UndefinedEnvironmentName as e:
        return CheckResult(CheckStatus.UNKNOWN, subject, f"无法对环境标记求值: {e}", entry)

    seen: set[tuple[str, str]] = set()

    if entry.constraint:
        if entry.name is None or _find_installed(entry.name, lookup) is None:
            return CheckResult(CheckStatus.SKIPPED, subject, "对应软件包未安装, 约束不适用", entry)

    if entry.kind == EntryKind.NAMED and entry.requirement is not None:
        result = _check_requirement(entry.requirement, environment, lookup, seen)
        return CheckResult(result.status, subject, result.reason, entry)

    if entry.name is None:
        return CheckResult(CheckStatus.UNKNOWN, subject, "无法确定软件包名, 无法验证是否已安装", entry)

    installed = _find_installed(entry.name, lookup)
    if installed is None:
        return CheckResult(CheckStatus.UNSATISFIED, subject, f"'{entry.name}' 未安装", entry)

    if entry.version is not None and not entry.editable:
        installed_version = Version.try_parse(installed.version)
        if installed_version is None or installed_version != entry.version:
            return CheckResult(CheckStatus.UNSATISFIED, subject, f"'{entry.name}' 已安装版本 {installed.version} 与文件版本 {entry.version} 不一致", entry)
    else:
        direct_url = installed.direct_url
        if direct_url is None or not _origin_matches(direct_url, entry.url, entry.path, entry.revision, entry.editable):
            return CheckResult(CheckStatus.UNKNOWN, subject, f"'{entry.name}' 已安装版本 {installed.version}, 但无法确认其安装来源与该条目一致", entry)

    problem = _check_extras(installed, entry.extras, environment, lookup, seen)
    if problem is not None:
        return CheckResult(CheckStatus.UNSATISFIED, subject, problem, entry)

    return CheckResult(CheckStatus.SATISFIED, subject, f"'{entry.name}' 已安装版本 {installed.version}", entry)


def check_requirements_file(
    parsed: RequirementsFile,
    environment: MarkerEnvironment | None = None,
    lookup: InstalledLookup | None = None,
) -> list[CheckResult]:
    """检查依赖文件解析结果中的所有条目 (含约束条目)

    Args:
        parsed (RequirementsFile):
            依赖文件解析结果
        environment (MarkerEnvironment | None):
            标记求值环境, 为 ``None`` 时使用当前解释器环境
        lookup (InstalledLookup | None):
            查询已安装分发的函数, 为 ``None`` 时查询当前环境

    Returns:
        list[CheckResult]: 各条目的检查结果, 顺序与条目声明顺序一致
    """
    return [check_entry(entry, environment, lookup) for entry in [*parsed.entries, *parsed.constraints]]


def is_package_installed(
    package: str,
) -> bool:
    """判断依赖声明字符串对应的 Python 软件包是否已安装在当前环境中

    规则见 :func:`check_requirement`. 环境标记不适用于当前环境, 或已安装但无法验证安装来源时返回 ``True``.

    Args:
        package (str):
            Python 软件包声明字符串, 如 ``'requests>=2.0,<3.0'``

    Returns:
        bool: 如果软件包未安装, 未安装正确的版本, 或声明无法解析则返回 ``False``
    """
    try:
        requirement = Requirement.parse(package)
    except InvalidRequirement as e:
        logger.warning("无法解析 Python 软件包声明 '%s', 视为未安装: %s", package, e.message)
        return False

    result = check_requirement(requirement)
    logger.debug("已安装 Python 软件包检测: %s -> %s (%s)", package, result.status.value, result.reason)
    return result.ok


def validate_requirements(
    requirement_path: str | Path,
) -> bool:
    """检测依赖文件中的依赖是否已全部安装

    按 requirements 文件格式解析依赖文件 (含 ``-r`` / ``-c`` 引用的嵌套文件,
    ``-e`` 可编辑条目, URL 与本地路径条目), 并检查所有条目是否已正确安装.

    无法解析的行与无法验证的条目 (例如无法确定软件包名的 ``-e .``) 只产生警告,
    不会中断检查, 也不会被视为缺失依赖.

    Args:
        requirement_path (str | Path):
            依赖文件路径

    Returns:
        bool: 如果有缺失依赖则返回 ``False``

    Raises:
        OSError:
            依赖文件不存在或无法读取时
        UnicodeDecodeError:
            依赖文件无法解码时
    """
    parsed = parse_requirements_file(requirement_path)
    for diagnostic in parsed.diagnostics:
        logger.warning("%s", diagnostic)

    satisfied = True
    for result in check_requirements_file(parsed):
        if result.status == CheckStatus.UNSATISFIED:
            logger.debug("依赖未满足: %s", result)
            satisfied = False
        elif result.status == CheckStatus.UNKNOWN:
            logger.warning("无法验证依赖, 已按已满足处理: %s", result)
        else:
            logger.debug("依赖检查: %s", result)

    return satisfied


def get_missing_package_metadata_dependencies(
    package_name: str,
) -> list[str]:
    """获取已安装软件包的元数据中声明但当前环境缺失的依赖

    Args:
        package_name (str):
            已安装软件包名, 支持 ``package`` 或 ``package[extra1,extra2]`` 格式.

    Returns:
        list[str]: 缺失或版本不满足约束的依赖声明列表

    Raises:
        InvalidRequirement:
            包声明无法解析时 (``ValueError`` 的子类)
        ValueError:
            请求的 extra 不存在时
    """
    request = Requirement.parse(package_name.strip())
    dependencies = get_categorized_dependencies(request.name)

    declarations: list[str] = list(dict.fromkeys(dependencies["mandatory"]))
    optional = {normalize_extra(extra): items for extra, items in dependencies["optional"].items()}
    unknown_extras = [extra for extra in request.extras if normalize_extra(extra) not in optional]
    if unknown_extras:
        raise ValueError(f"未找到 '{request.name}' 的可选依赖分组: {', '.join(unknown_extras)}")
    for extra in request.extras:
        for declaration in optional[normalize_extra(extra)]:
            if declaration not in declarations:
                declarations.append(declaration)

    return [declaration for declaration in declarations if not is_package_installed(declaration)]


def validate_package_metadata_dependencies(
    package_name: str,
) -> bool:
    """检测已安装软件包的元数据中声明的依赖是否完整

    Args:
        package_name (str):
            已安装软件包名, 支持 ``package`` 或 ``package[extra1,extra2]`` 格式.

    Returns:
        bool: 如果所有需要检查的依赖均已安装并满足版本约束则返回 ``True``

    Raises:
        InvalidRequirement:
            包声明无法解析时 (``ValueError`` 的子类)
        ValueError:
            请求的 extra 不存在时
    """
    return not get_missing_package_metadata_dependencies(package_name)
