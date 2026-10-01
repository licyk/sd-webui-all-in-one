"""环境标记 (environment marker) 的解析与求值

环境标记解析为保留字段名的语法树, 因此同一个标记可以针对任意目标环境求值.

参考:
    - https://packaging.python.org/en/latest/specifications/dependency-specifiers/#environment-markers
    - https://peps.python.org/pep-0508/
"""

from __future__ import annotations

import os
import platform
import re
import sys
from dataclasses import dataclass
from typing import (
    Any,
    Mapping,
)

from sd_webui_all_in_one.package_analyzer.errors import (
    InvalidMarker,
    InvalidSpecifier,
    UndefinedEnvironmentName,
)
from sd_webui_all_in_one.package_analyzer.names import normalize_extra
from sd_webui_all_in_one.package_analyzer.specifiers import Specifier
from sd_webui_all_in_one.package_analyzer.version import Version


STRING_FIELDS: frozenset[str] = frozenset(
    {
        "os_name",
        "sys_platform",
        "platform_machine",
        "platform_python_implementation",
        "platform_system",
        "implementation_name",
    }
)
"""类型为 String 的标记字段"""

VERSION_FIELDS: frozenset[str] = frozenset({"python_version", "python_full_version", "implementation_version"})
"""类型为 Version 的标记字段"""

VERSION_OR_STRING_FIELDS: frozenset[str] = frozenset({"platform_release", "platform_version"})
"""类型为 Version | String 的标记字段"""

SET_FIELDS: frozenset[str] = frozenset({"extras", "dependency_groups"})
"""类型为 Set of strings 的标记字段"""

EXTRA_FIELD = "extra"
"""表示可选依赖分组的特殊标记字段"""

MARKER_FIELDS: frozenset[str] = STRING_FIELDS | VERSION_FIELDS | VERSION_OR_STRING_FIELDS | SET_FIELDS | {EXTRA_FIELD}
"""所有已定义的标记字段"""

LEGACY_FIELD_ALIASES: dict[str, str] = {
    "os.name": "os_name",
    "sys.platform": "sys_platform",
    "platform.version": "platform_version",
    "platform.machine": "platform_machine",
    "platform.python_implementation": "platform_python_implementation",
    "python_implementation": "platform_python_implementation",
}
"""PEP 345 时期的旧字段名到标准字段名的映射 (pip 仍然接受这些写法)"""

MARKER_OPERATORS: tuple[str, ...] = ("===", "~=", "==", "!=", "<=", ">=", "<", ">", "in", "not in")
"""标记表达式支持的比较操作符"""

MarkerEnvironment = Mapping[str, Any]
"""标记求值环境: 字段名到字段值的映射. 集合类型字段的值为字符串集合, 其余为字符串"""


@dataclass(frozen=True)
class MarkerField:
    """标记表达式中的环境字段引用

    Attributes:
        name (str):
            标准字段名
    """

    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class MarkerLiteral:
    """标记表达式中的字符串常量

    Attributes:
        value (str):
            常量内容 (不含引号)
    """

    value: str

    def __str__(self) -> str:
        quote = "'" if '"' in self.value else '"'
        return f"{quote}{self.value}{quote}"


MarkerOperand = MarkerField | MarkerLiteral
"""标记比较表达式的操作数"""


@dataclass(frozen=True)
class MarkerCompare:
    """标记比较表达式, 如 ``python_version >= "3.10"``

    Attributes:
        lhs (MarkerOperand):
            左操作数
        op (str):
            比较操作符
        rhs (MarkerOperand):
            右操作数
    """

    lhs: MarkerOperand
    op: str
    rhs: MarkerOperand

    def __str__(self) -> str:
        return f"{self.lhs} {self.op} {self.rhs}"


@dataclass(frozen=True)
class MarkerAnd:
    """以 ``and`` 连接的标记表达式

    Attributes:
        operands (tuple[MarkerNode, ...]):
            子表达式列表
    """

    operands: tuple[MarkerNode, ...]

    def __str__(self) -> str:
        return " and ".join(f"({node})" if isinstance(node, MarkerOr) else str(node) for node in self.operands)


@dataclass(frozen=True)
class MarkerOr:
    """以 ``or`` 连接的标记表达式

    Attributes:
        operands (tuple[MarkerNode, ...]):
            子表达式列表
    """

    operands: tuple[MarkerNode, ...]

    def __str__(self) -> str:
        return " or ".join(str(node) for node in self.operands)


MarkerNode = MarkerCompare | MarkerAnd | MarkerOr
"""标记语法树节点"""


_WHITESPACE_REGEX = re.compile(r"\s*")
_FIELD_REGEX = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")
_OPERATOR_REGEX = re.compile(r"===|~=|==|!=|<=|>=|<|>|not\s+in\b|in\b")
_KEYWORD_REGEX = {
    "and": re.compile(r"and\b"),
    "or": re.compile(r"or\b"),
}


class _MarkerParser:
    """环境标记的递归下降解析器

    语法::

        marker_or   = marker_and ('or' marker_and)*
        marker_and  = marker_atom ('and' marker_atom)*
        marker_atom = '(' marker_or ')' | marker_var marker_op marker_var
        marker_var  = env_var | python_str
    """

    def __init__(
        self,
        text: str,
        pos: int = 0,
    ) -> None:
        """初始化解析器

        Args:
            text (str):
                待解析文本
            pos (int):
                起始位置
        """
        self.text = text
        self.pos = pos

    def error(
        self,
        message: str,
    ) -> InvalidMarker:
        """构造带有位置信息的解析异常

        Args:
            message (str):
                错误描述

        Returns:
            InvalidMarker: 解析异常
        """
        return InvalidMarker(f"{message} (位置 {self.pos})\n    {self.text}\n    {' ' * self.pos}^")

    def skip_whitespace(self) -> None:
        """跳过空白字符"""
        match = _WHITESPACE_REGEX.match(self.text, self.pos)
        if match is not None:
            self.pos = match.end()

    def parse_or(self) -> MarkerNode:
        """解析 ``or`` 表达式

        Returns:
            MarkerNode: 语法树节点
        """
        operands = [self.parse_and()]
        while self._match_keyword("or"):
            operands.append(self.parse_and())
        return operands[0] if len(operands) == 1 else MarkerOr(tuple(operands))

    def parse_and(self) -> MarkerNode:
        """解析 ``and`` 表达式

        Returns:
            MarkerNode: 语法树节点
        """
        operands = [self.parse_atom()]
        while self._match_keyword("and"):
            operands.append(self.parse_atom())
        return operands[0] if len(operands) == 1 else MarkerAnd(tuple(operands))

    def parse_atom(self) -> MarkerNode:
        """解析括号表达式或比较表达式

        Returns:
            MarkerNode: 语法树节点

        Raises:
            InvalidMarker:
                表达式不合法时
        """
        self.skip_whitespace()
        if self.text.startswith("(", self.pos):
            self.pos += 1
            node = self.parse_or()
            self.skip_whitespace()
            if not self.text.startswith(")", self.pos):
                raise self.error("环境标记缺少右括号 ')'")
            self.pos += 1
            return node

        lhs = self.parse_operand()
        self.skip_whitespace()
        match = _OPERATOR_REGEX.match(self.text, self.pos)
        if match is None:
            raise self.error("环境标记此处应为比较操作符")
        self.pos = match.end()
        op = "not in" if match.group().startswith("not") else match.group()
        rhs = self.parse_operand()
        return MarkerCompare(lhs, op, rhs)

    def parse_operand(self) -> MarkerOperand:
        """解析环境字段或带引号的字符串常量

        Returns:
            MarkerOperand: 操作数

        Raises:
            InvalidMarker:
                操作数不合法或引用了未定义的字段时
        """
        self.skip_whitespace()
        if self.pos < len(self.text) and self.text[self.pos] in "'\"":
            quote = self.text[self.pos]
            end = self.text.find(quote, self.pos + 1)
            if end == -1:
                raise self.error("环境标记中的字符串常量未闭合")
            value = self.text[self.pos + 1 : end]
            self.pos = end + 1
            return MarkerLiteral(value)

        match = _FIELD_REGEX.match(self.text, self.pos)
        if match is None:
            raise self.error("环境标记此处应为环境字段或带引号的字符串常量")
        name = LEGACY_FIELD_ALIASES.get(match.group(), match.group())
        if name not in MARKER_FIELDS:
            raise self.error(f"未定义的环境标记字段: {match.group()!r}")
        self.pos = match.end()
        return MarkerField(name)

    def _match_keyword(
        self,
        keyword: str,
    ) -> bool:
        """匹配 ``and`` / ``or`` 关键字

        Args:
            keyword (str):
                关键字

        Returns:
            bool: 匹配成功时返回 ``True`` 并前移位置
        """
        self.skip_whitespace()
        match = _KEYWORD_REGEX[keyword].match(self.text, self.pos)
        if match is None:
            return False
        self.pos = match.end()
        return True


@dataclass(frozen=True)
class Marker:
    """环境标记

    使用示例:
        ```python
        marker = Marker.parse('python_version >= "3.10" and sys_platform == "win32"')
        marker.evaluate()  # 针对当前解释器求值
        marker.evaluate({"sys_platform": "win32"})  # 覆盖部分字段后求值
        ```

    Attributes:
        tree (MarkerNode):
            标记语法树
    """

    tree: MarkerNode

    @classmethod
    def parse(
        cls,
        text: str,
    ) -> Marker:
        """解析环境标记字符串

        Args:
            text (str):
                环境标记字符串 (不含前导 ``;``)

        Returns:
            Marker: 环境标记对象

        Raises:
            InvalidMarker:
                环境标记不符合规范时
        """
        parser = _MarkerParser(text)
        tree = parser.parse_or()
        parser.skip_whitespace()
        if parser.pos != len(text):
            raise parser.error("环境标记末尾存在多余内容")
        return cls(tree)

    def evaluate(
        self,
        environment: MarkerEnvironment | None = None,
    ) -> bool:
        """对环境标记求值

        Args:
            environment (MarkerEnvironment | None):
                求值环境, 其中的字段会覆盖当前解释器环境的对应字段.
                标记引用 ``extra`` / ``extras`` / ``dependency_groups`` 时必须在此提供

        Returns:
            bool: 环境满足标记时返回 ``True``

        Raises:
            UndefinedEnvironmentName:
                标记引用了求值环境中未定义的字段时
        """
        env: dict[str, Any] = default_environment()
        if environment is not None:
            env.update(environment)
        return _evaluate_node(self.tree, env)

    def fields(self) -> frozenset[str]:
        """获取标记中引用的所有环境字段名

        Returns:
            frozenset[str]: 字段名集合
        """
        return frozenset(_collect_fields(self.tree))

    def extra_names(self) -> frozenset[str]:
        """获取标记中与 ``extra`` 字段做相等比较的 extra 名 (已规范化)

        Returns:
            frozenset[str]: extra 名集合
        """
        return frozenset(_collect_extra_names(self.tree))

    def __str__(self) -> str:
        return str(self.tree)


def _collect_fields(
    node: MarkerNode,
) -> set[str]:
    """递归收集语法树中引用的字段名

    Args:
        node (MarkerNode):
            语法树节点

    Returns:
        set[str]: 字段名集合
    """
    if isinstance(node, MarkerCompare):
        return {operand.name for operand in (node.lhs, node.rhs) if isinstance(operand, MarkerField)}
    result: set[str] = set()
    for child in node.operands:
        result |= _collect_fields(child)
    return result


def _collect_extra_names(
    node: MarkerNode,
) -> set[str]:
    """递归收集语法树中与 ``extra`` 字段做相等比较的 extra 名

    Args:
        node (MarkerNode):
            语法树节点

    Returns:
        set[str]: 规范化后的 extra 名集合
    """
    if isinstance(node, MarkerCompare):
        if node.op not in ("==", "==="):
            return set()
        for field_operand, other in ((node.lhs, node.rhs), (node.rhs, node.lhs)):
            if isinstance(field_operand, MarkerField) and field_operand.name == EXTRA_FIELD and isinstance(other, MarkerLiteral):
                return {normalize_extra(other.value)}
        return set()
    result: set[str] = set()
    for child in node.operands:
        result |= _collect_extra_names(child)
    return result


def format_full_version(
    info: Any,
) -> str:
    """按规范格式化 ``implementation_version`` 字段

    Args:
        info (Any):
            版本信息对象 (如 ``sys.implementation.version``)

    Returns:
        str: 格式化后的版本字符串
    """
    version = f"{info.major}.{info.minor}.{info.micro}"
    kind = info.releaselevel
    if kind != "final":
        version += kind[0] + str(info.serial)
    return version


def default_environment() -> dict[str, Any]:
    """获取当前 Python 解释器的标记求值环境

    不包含 ``extra``, ``extras``, ``dependency_groups``, 这些字段由使用场景提供.

    Returns:
        dict[str, Any]: 字段名到字段值的映射
    """
    return {
        "implementation_name": sys.implementation.name,
        "implementation_version": format_full_version(sys.implementation.version),
        "os_name": os.name,
        "platform_machine": platform.machine(),
        "platform_python_implementation": platform.python_implementation(),
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "python_full_version": platform.python_version(),
        "python_version": ".".join(platform.python_version_tuple()[:2]),
        "sys_platform": sys.platform,
    }


def _evaluate_node(
    node: MarkerNode,
    env: Mapping[str, Any],
) -> bool:
    """对语法树节点求值

    Args:
        node (MarkerNode):
            语法树节点
        env (Mapping[str, Any]):
            求值环境

    Returns:
        bool: 求值结果
    """
    if isinstance(node, MarkerAnd):
        return all(_evaluate_node(child, env) for child in node.operands)
    if isinstance(node, MarkerOr):
        return any(_evaluate_node(child, env) for child in node.operands)

    field_name: str | None = None
    for operand in (node.lhs, node.rhs):
        if isinstance(operand, MarkerField):
            field_name = operand.name
            break

    return compare_marker_values(
        _resolve_operand(node.lhs, env),
        node.op,
        _resolve_operand(node.rhs, env),
        field_name,
    )


def _resolve_operand(
    operand: MarkerOperand,
    env: Mapping[str, Any],
) -> Any:
    """获取操作数在求值环境中的值

    Args:
        operand (MarkerOperand):
            操作数
        env (Mapping[str, Any]):
            求值环境

    Returns:
        Any: 字符串, 或集合类型字段对应的字符串集合

    Raises:
        UndefinedEnvironmentName:
            字段在求值环境中未定义时
    """
    if isinstance(operand, MarkerLiteral):
        return operand.value
    if operand.name not in env:
        raise UndefinedEnvironmentName(f"环境标记字段 {operand.name!r} 在当前求值环境中未定义")
    return env[operand.name]


def compare_marker_values(
    lhs: Any,
    op: str,
    rhs: Any,
    field_name: str | None,
) -> bool:
    """按字段类型比较标记表达式两侧的值

    规则:
        - String 字段: ``==`` / ``!=`` / ``in`` / ``not in`` 按 Python 字符串语义 (区分大小写);
          ``>=`` / ``<=`` / ``~=`` / ``===`` 等同于 ``==``; ``>`` / ``<`` 恒为 ``False``
        - Version 与 Version | String 字段: 按版本约束语义比较, 任一侧无法解析为版本时回退到 String 规则;
          ``in`` / ``not in`` 按 String 规则 (规范允许对 Version 字段恒返回 ``False``,
          此处与 pip 保持一致, 以兼容 ``python_version in "3.10 3.11"`` 这类常见写法)
        - Set of strings 字段: 仅支持 ``in`` / ``not in``, 其余恒为 ``False``
        - ``extra`` 字段: 两侧规范化后按 String 规则比较
        - 两侧均为常量 (``field_name`` 为 ``None``): 能按版本比较时按版本比较, 否则按 String 规则

    Args:
        lhs (Any):
            左值
        op (str):
            比较操作符
        rhs (Any):
            右值
        field_name (str | None):
            表达式中引用的字段名, 两侧均为常量时为 ``None``

    Returns:
        bool: 比较结果
    """
    if field_name in SET_FIELDS:
        if op not in ("in", "not in") or not isinstance(lhs, str) or isinstance(rhs, str):
            return False
        contained = normalize_extra(lhs) in {normalize_extra(str(item)) for item in rhs}
        return contained if op == "in" else not contained

    lhs = str(lhs)
    rhs = str(rhs)

    if field_name == EXTRA_FIELD:
        return _compare_strings(normalize_extra(lhs), op, normalize_extra(rhs))

    if field_name in STRING_FIELDS:
        return _compare_strings(lhs, op, rhs)

    if op in ("in", "not in"):
        return _compare_strings(lhs, op, rhs)

    if op == "===":
        return lhs == rhs

    result = _compare_versions(lhs, op, rhs)
    if result is not None:
        return result
    return _compare_strings(lhs, op, rhs)


def _compare_versions(
    lhs: str,
    op: str,
    rhs: str,
) -> bool | None:
    """按版本约束语义比较, 无法按版本比较时返回 ``None``

    Args:
        lhs (str):
            候选版本
        op (str):
            比较操作符
        rhs (str):
            约束版本

    Returns:
        bool | None: 比较结果, 任一侧无法解析为版本时为 ``None``
    """
    # 本地构建的 CPython 的 python_full_version 形如 "3.13.0+", 需补全为合法版本号
    if lhs.endswith("+"):
        lhs += "local"
    candidate = Version.try_parse(lhs)
    if candidate is None:
        return None
    try:
        spec = Specifier(op, rhs)
    except InvalidSpecifier:
        return None
    return spec.contains(candidate, prereleases=True)


def _compare_strings(
    lhs: str,
    op: str,
    rhs: str,
) -> bool:
    """按 String 字段规则比较

    Args:
        lhs (str):
            左值
        op (str):
            比较操作符
        rhs (str):
            右值

    Returns:
        bool: 比较结果
    """
    if op == "in":
        return lhs in rhs
    if op == "not in":
        return lhs not in rhs
    if op == "!=":
        return lhs != rhs
    if op in ("==", ">=", "<=", "~=", "==="):
        return lhs == rhs
    return False
