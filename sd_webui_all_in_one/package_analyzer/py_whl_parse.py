"""Python 软件包名称解析器"""

import os
import sys
import platform
from typing import Any, NamedTuple


class ParsedPyWhlRequirement(NamedTuple):
    """解析后的依赖声明信息

    参考: https://peps.python.org/pep-0508
    """

    name: str
    """软件包名称"""

    extras: list[str]
    """extras 列表，例如 ['fred', 'bar']"""

    specifier: list[tuple[str, str]] | str
    """版本约束列表或 URL 地址

    如果是版本依赖，则为版本约束列表，例如 [('>=', '1.0'), ('<', '2.0')]
    如果是 URL 依赖，则为 URL 字符串，例如 'http://example.com/package.tar.gz'
    """

    marker: Any
    """环境标记表达式，用于条件依赖"""


class Parser:
    """语法解析器

    Attributes:
        text (str): 待解析的字符串
        pos (int): 字符起始位置
        len (int): 字符串长度
    """

    def __init__(self, text: str) -> None:
        """初始化解析器

        Args:
            text (str): 要解析的文本
        """
        self.text = text
        self.pos = 0
        self.len = len(text)

    def peek(self) -> str:
        """查看当前位置的字符但不移动指针

        Returns:
            str: 当前位置的字符，如果到达末尾则返回空字符串
        """
        if self.pos < self.len:
            return self.text[self.pos]
        return ""

    def consume(self, expected: str | None = None) -> str:
        """消耗当前字符并移动指针

        Args:
            expected (str | None): 期望的字符，如果提供但不匹配会抛出异常

        Returns:
            str: 实际消耗的字符

        Raises:
            ValueError: 当字符不匹配或到达文本末尾时
        """
        if self.pos >= self.len:
            raise ValueError(f"不期望的输入内容结尾, 期望: {expected}")

        char = self.text[self.pos]
        if expected and char != expected:
            raise ValueError(f"期望 '{expected}', 得到 '{char}' 在位置 {self.pos}")

        self.pos += 1
        return char

    def skip_whitespace(self):
        """跳过空白字符（空格和制表符）"""
        while self.pos < self.len and self.text[self.pos] in " \t":
            self.pos += 1

    def match(self, pattern: str) -> str | None:
        """尝试匹配指定模式, 成功则移动指针

        Args:
            pattern (str): 要匹配的模式字符串

        Returns:
            (str | None): 匹配成功的字符串, 否则为 None
        """
        # 跳过空格再匹配
        original_pos = self.pos
        self.skip_whitespace()

        if self.text.startswith(pattern, self.pos):
            result = self.text[self.pos : self.pos + len(pattern)]
            self.pos += len(pattern)
            return result

        # 如果没有匹配，恢复位置
        self.pos = original_pos
        return None

    def read_while(self, condition) -> str:
        """读取满足条件的字符序列

        Args:
            condition: 判断字符是否满足条件的函数

        Returns:
            str: 满足条件的字符序列
        """
        start = self.pos
        while self.pos < self.len and condition(self.text[self.pos]):
            self.pos += 1
        return self.text[start : self.pos]

    def eof(self) -> bool:
        """检查是否到达文本末尾

        Returns:
            bool: 如果到达末尾返回 True, 否则返回 False
        """
        return self.pos >= self.len


class RequirementParser(Parser):
    """Python 软件包解析工具

    Attributes:
        bindings (dict[str, str] | None): 解析语法
    """

    def __init__(self, text: str, bindings: dict[str, str] | None = None):
        """初始化依赖声明解析器

        Args:
            text (str): 覫解析的依赖声明文本
            bindings (dict[str, str] | None): 环境变量绑定字典
        """
        super().__init__(text)
        self.bindings = bindings or {}

    def parse(self) -> ParsedPyWhlRequirement:
        """解析依赖声明，返回 (name, extras, version_specs / url, marker)

        Returns:
            ParsedPyWhlRequirement: 解析结果元组
        """
        self.skip_whitespace()

        # 首先解析名称
        name = self.parse_identifier()
        self.skip_whitespace()

        # 解析 extras
        extras = []
        if self.peek() == "[":
            extras = self.parse_extras()
            self.skip_whitespace()

        # 检查是 URL 依赖还是版本依赖
        if self.peek() == "@":
            # URL依赖
            self.consume("@")
            self.skip_whitespace()
            url = self.parse_url()
            self.skip_whitespace()

            # 解析可选的 marker
            marker = None
            if self.match(";"):
                marker = self.parse_marker()

            return ParsedPyWhlRequirement(name, extras, url, marker)
        else:
            # 版本依赖
            versions = []
            # 检查是否有版本约束 (不是以分号开头)
            if not self.eof() and self.peek() not in (";", ","):
                versions = self.parse_versionspec()
                self.skip_whitespace()

            # 解析可选的 marker
            marker = None
            if self.match(";"):
                marker = self.parse_marker()

            return ParsedPyWhlRequirement(name, extras, versions, marker)

    def parse_identifier(self) -> str:
        """解析标识符

        Returns:
            str: 解析得到的标识符
        """

        def is_identifier_char(c):
            return c.isalnum() or c in "-_."

        result = self.read_while(is_identifier_char)
        if not result:
            raise ValueError("应为预期标识符")
        return result

    def parse_extras(self) -> list[str]:
        """解析 extras 列表

        Returns:
            list[str]: extras 列表
        """
        self.consume("[")
        self.skip_whitespace()

        extras = []
        if self.peek() != "]":
            extras.append(self.parse_identifier())
            self.skip_whitespace()

            while self.match(","):
                self.skip_whitespace()
                extras.append(self.parse_identifier())
                self.skip_whitespace()

        self.consume("]")
        return extras

    def parse_versionspec(self) -> list[tuple[str, str]]:
        """解析版本约束

        Returns:
            list[tuple[str, str]]: 版本约束列表
        """
        if self.match("("):
            versions = self.parse_version_many()
            self.consume(")")
            return versions
        else:
            return self.parse_version_many()

    def parse_version_many(self) -> list[tuple[str, str]]:
        """解析多个版本约束

        Returns:
            list[tuple[str, str]]: 多个版本约束组成的列表
        """
        versions = [self.parse_version_one()]
        self.skip_whitespace()

        while self.match(","):
            self.skip_whitespace()
            versions.append(self.parse_version_one())
            self.skip_whitespace()

        return versions

    def parse_version_one(self) -> tuple[str, str]:
        """解析单个版本约束

        Returns:
            tuple[str, str]: (操作符, 版本号) 元组
        """
        op = self.parse_version_cmp()
        self.skip_whitespace()
        version = self.parse_version()
        return (op, version)

    def parse_version_cmp(self) -> str:
        """解析版本比较操作符

        Returns:
            str: 版本比较操作符

        Raises:
            ValueError: 当找不到有效的版本比较操作符时
        """
        operators = ["<=", ">=", "==", "!=", "~=", "===", "<", ">"]

        for op in operators:
            if self.match(op):
                return op

        raise ValueError(f"预期在位置 {self.pos} 处出现版本比较符")

    def parse_version(self) -> str:
        """解析版本号

        Returns:
            str: 版本号字符串

        Raises:
            ValueError: 当找不到有效版本号时
        """

        def is_version_char(c):
            return c.isalnum() or c in "-_.*+!"

        version = self.read_while(is_version_char)
        if not version:
            raise ValueError("期望为版本字符串")
        return version

    def parse_url(self) -> str:
        """解析 URL (简化版本)

        Returns:
            str: URL 字符串

        Raises:
            ValueError: 当找不到有效 URL 时
        """
        # 读取直到遇到空白或分号
        start = self.pos
        while self.pos < self.len and self.text[self.pos] not in " \t;":
            self.pos += 1
        url = self.text[start : self.pos]

        if not url:
            raise ValueError("@ 后的预期 URL")

        return url

    def parse_marker(self) -> Any:
        """解析 marker 表达式

        Returns:
            Any: 解析后的 marker 表达式
        """
        self.skip_whitespace()
        return self.parse_marker_or()

    def parse_marker_or(self) -> Any:
        """解析 OR 表达式

        Returns:
            Any: 解析后的 OR 表达式
        """
        left = self.parse_marker_and()
        self.skip_whitespace()

        if self.match("or"):
            self.skip_whitespace()
            right = self.parse_marker_or()
            return ("or", left, right)

        return left

    def parse_marker_and(self) -> Any:
        """解析 AND 表达式

        Returns:
            Any: 解析后的 AND 表达式
        """
        left = self.parse_marker_expr()
        self.skip_whitespace()

        if self.match("and"):
            self.skip_whitespace()
            right = self.parse_marker_and()
            return ("and", left, right)

        return left

    def parse_marker_expr(self) -> Any:
        """解析基础 marker 表达式

        Returns:
            Any: 解析后的基础表达式
        """
        self.skip_whitespace()

        if self.peek() == "(":
            self.consume("(")
            expr = self.parse_marker()
            self.consume(")")
            return expr

        left = self.parse_marker_var()
        self.skip_whitespace()

        op = self.parse_marker_op()
        self.skip_whitespace()

        right = self.parse_marker_var()

        return (op, left, right)

    def parse_marker_var(self) -> str:
        """解析 marker 变量

        Returns:
            str: 解析得到的变量值
        """
        self.skip_whitespace()

        # 检查是否是环境变量
        env_vars = [
            "python_version",
            "python_full_version",
            "os_name",
            "sys_platform",
            "platform_release",
            "platform_system",
            "platform_version",
            "platform_machine",
            "platform_python_implementation",
            "implementation_name",
            "implementation_version",
            "extra",
        ]

        for var in env_vars:
            if self.match(var):
                # 返回绑定的值，如果不存在则返回变量名
                return self.bindings.get(var, var)

        # 否则解析为字符串
        return self.parse_python_str()

    def parse_marker_op(self) -> str:
        """解析 marker 操作符

        Returns:
            str: marker 操作符

        Raises:
            ValueError: 当找不到有效操作符时
        """
        # 版本比较操作符
        version_ops = ["<=", ">=", "==", "!=", "~=", "===", "<", ">"]
        for op in version_ops:
            if self.match(op):
                return op

        # in 操作符
        if self.match("in"):
            return "in"

        # not in 操作符
        if self.match("not"):
            self.skip_whitespace()
            if self.match("in"):
                return "not in"
            raise ValueError("预期在 'not' 之后出现 'in'")

        raise ValueError(f"在位置 {self.pos} 处应出现标记运算符")

    def parse_python_str(self) -> str:
        """解析 Python 字符串

        Returns:
            str: 解析得到的字符串
        """
        self.skip_whitespace()

        if self.peek() == '"':
            return self.parse_quoted_string('"')
        elif self.peek() == "'":
            return self.parse_quoted_string("'")
        else:
            # 如果没有引号，读取标识符
            return self.parse_identifier()

    def parse_quoted_string(self, quote: str) -> str:
        """解析引号字符串

        Args:
            quote (str): 引号字符

        Returns:
            str: 解析得到的字符串

        Raises:
            ValueError: 当字符串未正确闭合时
        """
        self.consume(quote)
        result = []

        while self.pos < self.len and self.text[self.pos] != quote:
            if self.text[self.pos] == "\\":  # 处理转义
                self.pos += 1
                if self.pos < self.len:
                    result.append(self.text[self.pos])
                    self.pos += 1
            else:
                result.append(self.text[self.pos])
                self.pos += 1

        if self.pos >= self.len:
            raise ValueError(f"未闭合的字符串字面量，预期为 '{quote}'")

        self.consume(quote)
        return "".join(result)


def format_full_version(info: str) -> str:
    """格式化完整的版本信息

    Args:
        info (str): 版本信息

    Returns:
        str: 格式化后的版本字符串
    """
    version = f"{info.major}.{info.minor}.{info.micro}"
    kind = info.releaselevel
    if kind != "final":
        version += kind[0] + str(info.serial)
    return version


def get_parse_bindings() -> dict[str, str]:
    """获取用于解析 Python 软件包名的语法

    Returns:
        (dict[str, str]): 解析 Python 软件包名的语法字典
    """
    # 创建环境变量绑定
    if hasattr(sys, "implementation"):
        implementation_version = format_full_version(sys.implementation.version)
        implementation_name = sys.implementation.name
    else:
        implementation_version = "0"
        implementation_name = ""

    bindings = {
        "implementation_name": implementation_name,
        "implementation_version": implementation_version,
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
    return bindings
