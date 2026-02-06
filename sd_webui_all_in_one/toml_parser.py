"""TOML 格式解析工具, 用于将 TOML 字符串转换为 Python 字典对象"""

import re
from typing import Any, BinaryIO, TypeAlias


TomlDict: TypeAlias = dict[str, Any]
"""TOML 内容字典"""


class TomlParser:
    """TOML 格式解析器

    该类提供了解析标准 TOML 字符串的功能, 支持嵌套表、数组表、内联表以及基本数据类型

    Attributes:
        root (TomlDict):
            解析后的根字典对象
        current_table (TomlDict):
            解析过程中当前所在的表 (或嵌套表)的指针
    """

    def __init__(self) -> None:
        """初始化 TomlParser 实例"""
        self.root: TomlDict = {}
        self.current_table: TomlDict = self.root

    def load(self, fp: BinaryIO) -> TomlDict:
        """ "解析 TOML 格式的二进制流并返回字典

        Args:
            fp (BinaryIO):
                待解析的 TOML 二进制流

        Returns:
            TomlDict:
                解析后的字典对象
        """
        b = fp.read()
        try:
            s = b.decode(encoding="utf-8")
        except AttributeError as e:
            raise TypeError("文件必须使用二进制模式打开, 例如: `open('test.toml', 'rb')`") from e
        return self.loads(s)

    def loads(self, content: str) -> TomlDict:
        """解析 TOML 格式的字符串并返回字典

        Args:
            content (str):
                待解析的 TOML 文本内容

        Returns:
            TomlDict:
                解析后的字典对象
        """
        self.root = {}
        self.current_table = self.root

        # 1. 预处理：移除注释
        # 注意：此处为简化处理, 实际复杂的 TOML 解析需要识别字符串内的 #
        lines: list[str] = content.splitlines()
        clean_lines: list[str] = []
        for line in lines:
            # 简单的注释移除：匹配非引号包围的 #
            line = re.sub(r"\s+#.*$", "", line).strip()
            if line:
                clean_lines.append(line)

        # 2. 合并跨行结构 (数组 [ ] 和 内联表 { })
        processed_lines: list[str] = self._merge_multiline(clean_lines)

        # 3. 解析每一行
        for line in processed_lines:
            if line.startswith("[["):
                # 解析数组表 [[table_name]]
                name: str = line.strip("[] ")
                self._navigate(name, is_array_table=True)
            elif line.startswith("["):
                # 解析标准表 [table_name]
                name: str = line.strip("[] ")
                self._navigate(name, is_array_table=False)
            elif "=" in line:
                # 解析键值对 key = value
                key, val = line.split("=", 1)
                self.current_table[key.strip()] = self._parse_value(val.strip())

        return self.root

    def _merge_multiline(self, lines: list[str]) -> list[str]:
        """将跨行的数组或表合并为一行以便解析

        Args:
            lines (list[str]):
                预处理后的行列表

        Returns:
            list[str]:
                合并了跨行结构后的行列表
        """
        merged: list[str] = []
        buffer: str = ""
        depth: int = 0
        for line in lines:
            buffer += " " + line
            depth += line.count("[") - line.count("]")
            depth += line.count("{") - line.count("}")
            if depth == 0:
                merged.append(buffer.strip())
                buffer = ""
        return merged

    def _navigate(self, key_str: str, is_array_table: bool = False) -> None:
        """导航到指定的嵌套表位置并更新 current_table 指针

        Args:
            key_str (str):
                表路径字符串, 如 "a.b.c"
            is_array_table (bool):
                是否为数组表 ([[name]]) 默认为 False
        """
        parts: list[str] = [p.strip() for p in key_str.split(".")]
        curr: Any = self.root

        for i, part in enumerate(parts):
            is_last: bool = i == len(parts) - 1

            if is_last and is_array_table:
                # 处理数组表末尾节点
                if part not in curr:
                    curr[part] = []
                new_dict: TomlDict = {}
                curr[part].append(new_dict)
                self.current_table = new_dict
            else:
                # 处理中间路径或标准表末尾节点
                if part not in curr:
                    curr[part] = {}

                # 检查当前节点是列表还是字典 (处理数组表嵌套)
                if isinstance(curr[part], list):
                    curr = curr[part][-1]
                else:
                    curr = curr[part]

                if is_last:
                    self.current_table = curr

    def _parse_value(self, v: str) -> Any:
        """解析 TOML 值类型

        Args:
            v (str):
                值字符串

        Returns:
            Any:
                转换后的 Python 对象 (str, int, float, bool, list 或 dict)
        """
        v = v.strip()
        # 字符串处理
        if v.startswith('"') and v.endswith('"'):
            return v[1:-1].encode("utf-8").decode("unicode_escape")

        # 布尔值处理
        if v.lower() == "true":
            return True
        if v.lower() == "false":
            return False

        # 数字处理 (整数、浮点数、科学计数法)
        if re.match(r"^-?\d+\.?\d*([eE][+-]?\d+)?$", v):
            return float(v) if ("." in v or "e" in v.lower()) else int(v)

        # 数组处理
        if v.startswith("[") and v.endswith("]"):
            return self._parse_array(v[1:-1])

        # 内联表处理
        if v.startswith("{") and v.endswith("}"):
            return self._parse_inline_table(v[1:-1])

        return v

    def _parse_array(self, content: str) -> list[Any]:
        """解析数组内容

        Args:
            content (str):
                方括号内部的字符串

        Returns:
            list[Any]:
                解析后的 Python 列表
        """
        result: list[Any] = []
        buffer: str = ""
        depth: int = 0
        # 递归解析逻辑, 支持数组嵌套
        for char in content:
            if char in "[{":
                depth += 1
            elif char in "]}":
                depth -= 1

            if char == "," and depth == 0:
                item = buffer.strip()
                if item:
                    result.append(self._parse_value(item))
                buffer = ""
            else:
                buffer += char

        if buffer.strip():
            result.append(self._parse_value(buffer.strip()))
        return result

    def _parse_inline_table(self, content: str) -> TomlDict:
        """解析内联表 (例如 { a = 1, b = 2 })

        Args:
            content (str):
                花括号内部的字符串

        Returns:
            TomlDict:
                解析后的字典对象
        """
        table: TomlDict = {}
        pairs: list[str] = content.split(",")
        for pair in pairs:
            if "=" in pair:
                k, v = pair.split("=", 1)
                table[k.strip()] = self._parse_value(v.strip())
        return table


def loads(data: str) -> TomlDict:
    """解析 TOML 格式的字符串并返回字典

    Args:
        content (str):
            待解析的 TOML 文本内容

    Returns:
        TomlDict:
            解析后的字典对象
    """
    return TomlParser().loads(data)


def load(fp: BinaryIO) -> TomlDict:
    """解析 TOML 格式的二进制流并返回字典

    Args:
        fp (BinaryIO):
            待解析的 TOML 二进制流

    Returns:
        TomlDict:
            解析后的字典对象
    """
    return TomlParser().load(fp)
