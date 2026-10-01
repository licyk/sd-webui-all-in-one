"""依赖声明对象

基于依赖声明规范实现依赖声明字符串 (``name[extra]>=1.0; marker``) 的解析.

参考:
    - https://packaging.python.org/en/latest/specifications/dependency-specifiers/
    - https://peps.python.org/pep-0508/
"""

from __future__ import annotations

import re
from dataclasses import (
    dataclass,
    field,
)

from sd_webui_all_in_one.package_analyzer.errors import (
    InvalidMarker,
    InvalidRequirement,
    InvalidSpecifier,
)
from sd_webui_all_in_one.package_analyzer.markers import (
    Marker,
    MarkerEnvironment,
)
from sd_webui_all_in_one.package_analyzer.names import (
    NAME_PATTERN,
    normalize_extra,
    normalize_name,
)
from sd_webui_all_in_one.package_analyzer.specifiers import (
    Specifier,
    SpecifierSet,
)


_WHITESPACE_REGEX = re.compile(r"\s*")
_NAME_REGEX = re.compile(NAME_PATTERN)
_OPERATOR_REGEX = re.compile(r"===|~=|==|!=|<=|>=|<|>")
_VERSION_REGEX = re.compile(r"[A-Za-z0-9._*+!-]+")
_ARBITRARY_VERSION_REGEX = re.compile(r"[^\s,;)]+")
_URL_REGEX = re.compile(r"\S+")


@dataclass(frozen=True)
class Requirement:
    """依赖声明

    使用示例:
        ```python
        req = Requirement.parse('requests[security]>=2.8.1,<3; python_version < "3.13"')
        req.name  # "requests"
        req.extras  # ("security",)
        str(req.specifier)  # ">=2.8.1,<3"
        req.specifier.contains("2.31.0")  # True
        ```

    Attributes:
        name (str):
            软件包名 (保留原始写法, 比较时使用 ``normalized_name``)
        extras (tuple[str, ...]):
            extras 列表, 保持声明顺序
        specifier (SpecifierSet):
            版本约束集合, URL 依赖时为空
        url (str | None):
            直接引用的 URL (``name @ url`` 形式), 否则为 ``None``
        marker (Marker | None):
            环境标记, 不存在时为 ``None``
    """

    name: str
    extras: tuple[str, ...] = ()
    specifier: SpecifierSet = field(default_factory=SpecifierSet)
    url: str | None = None
    marker: Marker | None = None

    @classmethod
    def parse(
        cls,
        text: str,
    ) -> Requirement:
        """解析依赖声明字符串

        语法::

            specification = wsp* ( url_req | name_req ) wsp*
            name_req      = name wsp* extras? wsp* versionspec? wsp* quoted_marker?
            url_req       = name wsp* extras? wsp* '@' wsp* URI (wsp+ quoted_marker)?

        Args:
            text (str):
                依赖声明字符串

        Returns:
            Requirement: 依赖声明对象

        Raises:
            InvalidRequirement:
                依赖声明不符合规范时
        """
        return _RequirementParser(text).parse()

    @classmethod
    def try_parse(
        cls,
        text: str,
    ) -> Requirement | None:
        """解析依赖声明字符串, 失败时返回 ``None``

        Args:
            text (str):
                依赖声明字符串

        Returns:
            Requirement | None: 依赖声明对象, 依赖声明不符合规范时为 ``None``
        """
        try:
            return cls.parse(text)
        except InvalidRequirement:
            return None

    @property
    def normalized_name(self) -> str:
        """规范化后的软件包名

        Returns:
            str: 规范化后的软件包名
        """
        return normalize_name(self.name)

    @property
    def normalized_extras(self) -> frozenset[str]:
        """规范化后的 extras 集合

        Returns:
            frozenset[str]: 规范化后的 extras 集合
        """
        return frozenset(normalize_extra(extra) for extra in self.extras)

    def applies_to(
        self,
        environment: MarkerEnvironment | None = None,
    ) -> bool:
        """判断此依赖声明在指定环境下是否生效

        未提供 ``extra`` 时按未请求任何 extra 处理.

        Args:
            environment (MarkerEnvironment | None):
                标记求值环境, 为 ``None`` 时使用当前解释器环境

        Returns:
            bool: 无环境标记或环境满足标记时返回 ``True``
        """
        if self.marker is None:
            return True
        env = {"extra": ""}
        if environment is not None:
            env.update(environment)
        return self.marker.evaluate(env)

    def __str__(self) -> str:
        result = self.name
        if self.extras:
            result += f"[{','.join(self.extras)}]"
        if self.url is not None:
            result += f" @ {self.url}"
            if self.marker is not None:
                result += f" ; {self.marker}"
            return result
        result += str(self.specifier)
        if self.marker is not None:
            result += f"; {self.marker}"
        return result


class _RequirementParser:
    """依赖声明的递归下降解析器"""

    def __init__(
        self,
        text: str,
    ) -> None:
        """初始化解析器

        Args:
            text (str):
                依赖声明字符串
        """
        self.text = text
        self.pos = 0

    def error(
        self,
        message: str,
    ) -> InvalidRequirement:
        """构造带有位置信息的解析异常

        Args:
            message (str):
                错误描述

        Returns:
            InvalidRequirement: 解析异常
        """
        return InvalidRequirement(message, self.text, self.pos)

    def skip_whitespace(self) -> None:
        """跳过空白字符"""
        match = _WHITESPACE_REGEX.match(self.text, self.pos)
        if match is not None:
            self.pos = match.end()

    def peek(self) -> str:
        """查看当前位置的字符

        Returns:
            str: 当前字符, 到达末尾时为空字符串
        """
        return self.text[self.pos] if self.pos < len(self.text) else ""

    def parse(self) -> Requirement:
        """解析完整的依赖声明

        Returns:
            Requirement: 依赖声明对象

        Raises:
            InvalidRequirement:
                依赖声明不符合规范时
        """
        self.skip_whitespace()
        name = self.parse_name("软件包名")
        self.skip_whitespace()

        extras: tuple[str, ...] = ()
        if self.peek() == "[":
            extras = self.parse_extras()
            self.skip_whitespace()

        url: str | None = None
        specifier = SpecifierSet()
        marker: Marker | None = None

        if self.peek() == "@":
            self.pos += 1
            self.skip_whitespace()
            match = _URL_REGEX.match(self.text, self.pos)
            if match is None:
                raise self.error("'@' 之后应为 URL")
            url = match.group()
            self.pos = match.end()
            # URL 会吞掉所有非空白字符, 因此环境标记前的 ';' 必须以空白与 URL 分隔
            self.skip_whitespace()
            if self.peek() == ";":
                self.pos += 1
                marker = self.parse_marker()
        else:
            if self.peek() not in ("", ";"):
                specifier = self.parse_versionspec()
                self.skip_whitespace()
            if self.peek() == ";":
                self.pos += 1
                marker = self.parse_marker()

        self.skip_whitespace()
        if self.pos != len(self.text):
            raise self.error("依赖声明末尾存在多余内容")

        return Requirement(name=name, extras=extras, specifier=specifier, url=url, marker=marker)

    def parse_name(
        self,
        kind: str,
    ) -> str:
        """解析软件包名或 extra 名

        Args:
            kind (str):
                名称类别, 用于错误信息

        Returns:
            str: 名称

        Raises:
            InvalidRequirement:
                当前位置不是合法名称时
        """
        match = _NAME_REGEX.match(self.text, self.pos)
        if match is None:
            raise self.error(f"此处应为{kind} (必须以 ASCII 字母或数字开头)")
        self.pos = match.end()
        return match.group()

    def parse_extras(self) -> tuple[str, ...]:
        """解析 extras 列表

        Returns:
            tuple[str, ...]: extras 列表

        Raises:
            InvalidRequirement:
                extras 列表不合法时
        """
        self.pos += 1
        self.skip_whitespace()
        extras: list[str] = []
        if self.peek() != "]":
            while True:
                self.skip_whitespace()
                extras.append(self.parse_name("extra 名"))
                self.skip_whitespace()
                if self.peek() != ",":
                    break
                self.pos += 1
        if self.peek() != "]":
            raise self.error("extras 列表缺少右括号 ']'")
        self.pos += 1
        return tuple(extras)

    def parse_versionspec(self) -> SpecifierSet:
        """解析版本约束, 支持带括号的旧写法

        Returns:
            SpecifierSet: 版本约束集合

        Raises:
            InvalidRequirement:
                版本约束不合法时
        """
        parenthesized = self.peek() == "("
        if parenthesized:
            self.pos += 1

        specifiers: list[Specifier] = []
        while True:
            self.skip_whitespace()
            start = self.pos
            match = _OPERATOR_REGEX.match(self.text, self.pos)
            if match is None:
                raise self.error("此处应为版本比较操作符 (如 ==, >=)")
            operator = match.group()
            self.pos = match.end()
            self.skip_whitespace()
            version_regex = _ARBITRARY_VERSION_REGEX if operator == "===" else _VERSION_REGEX
            match = version_regex.match(self.text, self.pos)
            if match is None:
                raise self.error("版本比较操作符之后应为版本号")
            self.pos = match.end()
            try:
                specifiers.append(Specifier(operator, match.group()))
            except InvalidSpecifier as e:
                self.pos = start
                raise self.error(str(e)) from e
            self.skip_whitespace()
            if self.peek() != ",":
                break
            self.pos += 1

        if parenthesized:
            if self.peek() != ")":
                raise self.error("版本约束缺少右括号 ')'")
            self.pos += 1

        return SpecifierSet(tuple(specifiers))

    def parse_marker(self) -> Marker:
        """解析环境标记 (``;`` 之后直到末尾的部分)

        Returns:
            Marker: 环境标记对象

        Raises:
            InvalidRequirement:
                环境标记不合法时
        """
        marker_text = self.text[self.pos :]
        try:
            marker = Marker.parse(marker_text)
        except InvalidMarker as e:
            raise InvalidRequirement(f"环境标记不合法: {str(e).splitlines()[0]}", self.text, self.pos) from e
        self.pos = len(self.text)
        return marker
