"""TOML 格式解析工具, 用于将 TOML 字符串转换为 Python 字典对象"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import (
    date,
    datetime,
    time,
    timedelta,
    timezone,
)
from typing import (
    Any,
    BinaryIO,
    NoReturn,
    TypeAlias,
)


TomlDict: TypeAlias = dict[str, Any]
"""TOML 内容字典"""


_BARE_KEY_RE = re.compile(r"[A-Za-z0-9_-]")
_DEC_INT_RE = re.compile(r"[+-]?(?:0|[1-9](?:_?[0-9])*)\Z")
_HEX_INT_RE = re.compile(r"0[xX][0-9A-Fa-f](?:_?[0-9A-Fa-f])*\Z")
_OCT_INT_RE = re.compile(r"0[oO][0-7](?:_?[0-7])*\Z")
_BIN_INT_RE = re.compile(r"0[bB][01](?:_?[01])*\Z")
_FLOAT_RE = re.compile(
    r"[+-]?(?:0|[1-9](?:_?[0-9])*)(?:\.[0-9](?:_?[0-9])*)?(?:[eE][+-]?[0-9](?:_?[0-9])*)\Z"
    r"|[+-]?(?:0|[1-9](?:_?[0-9])*)\.[0-9](?:_?[0-9])*\Z"
)
_DATE_RE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})\Z")
_TIME_RE = re.compile(r"([0-9]{2}):([0-9]{2})(?::([0-9]{2})(\.[0-9]+)?)?\Z")
_DATETIME_RE = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt ]"
    r"([0-9]{2}):([0-9]{2})(?::([0-9]{2})(\.[0-9]+)?)?"
    r"(Z|[+-][0-9]{2}:[0-9]{2})?\Z"
)


@dataclass
class _TableMeta:
    """表定义状态"""

    explicit: bool = False
    defined_by_dotted: bool = False
    frozen: bool = False


class TomlDecodeError(ValueError):
    """TOML 解析错误"""

    def __init__(
        self,
        message: str,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        self.message = message
        self.line = line
        self.column = column
        if line is not None and column is not None:
            super().__init__(f"{message} (line {line}, column {column})")
        else:
            super().__init__(message)


class TomlParser:
    """TOML 格式解析器"""

    def __init__(
        self,
    ) -> None:
        """初始化 TomlParser 实例"""
        self.root: TomlDict = {}
        self.current_table: TomlDict = self.root
        self._data: str = ""
        self._pos: int = 0
        self._line: int = 1
        self._column: int = 1
        self._meta: dict[int, _TableMeta] = {}
        self._array_table_lists: set[int] = set()

    def load(self, fp: BinaryIO) -> TomlDict:
        """解析 TOML 格式的二进制流并返回字典

        Args:
            fp (BinaryIO):
                待解析的 TOML 二进制流

        Returns:
            TomlDict:
                解析后的字典对象

        Raises:
            TypeError:
                传入的文件对象未返回二进制数据时抛出。
            TomlDecodeError:
                输入不是有效 UTF-8 TOML 文档时抛出。
        """
        b = fp.read()
        try:
            s = b.decode(encoding="utf-8")
        except AttributeError as e:
            raise TypeError("文件必须使用二进制模式打开, 例如: `open('test.toml', 'rb')`") from e
        except UnicodeDecodeError as e:
            raise TomlDecodeError("TOML 文件必须使用有效的 UTF-8 编码") from e
        return self.loads(s)

    def loads(self, content: str) -> TomlDict:
        """解析 TOML 格式的字符串并返回字典

        Args:
            content (str):
                待解析的 TOML 文本内容

        Returns:
            TomlDict:
                解析后的字典对象

        Raises:
            TypeError:
                传入的 TOML 内容不是字符串时抛出。
            TomlDecodeError:
                输入不是有效 TOML 文档时抛出。
        """
        if not isinstance(content, str):
            raise TypeError("TOML 内容必须是字符串")

        self.root = {}
        self.current_table = self.root
        self._meta = {id(self.root): _TableMeta()}
        self._array_table_lists = set()
        self._data = self._normalize_document(content)
        self._pos = 0
        self._line = 1
        self._column = 1

        while True:
            self._skip_ws_comments(allow_newline=True)
            if self._eof():
                return self.root
            if self._peek() == "[":
                self._parse_table_header()
            else:
                self._parse_key_value(self.current_table, mark_dotted=True, allow_newline=False)
                self._consume_statement_end()

    def _normalize_document(self, content: str) -> str:
        """规范化换行并校验 Unicode 文档结构"""
        normalized = content.replace("\r\n", "\n")
        if "\r" in normalized:
            raise TomlDecodeError("TOML 只支持 LF 或 CRLF 换行")
        if normalized.startswith("\ufeff"):
            normalized = normalized[1:]
        for ch in normalized:
            code = ord(ch)
            if 0xD800 <= code <= 0xDFFF:
                raise TomlDecodeError("TOML 文档包含非法 Unicode 代理码位")
        return normalized

    def _parse_table_header(self) -> None:
        """解析 [table] 或 [[array-table]]"""
        self._expect("[")
        is_array_table = self._peek() == "["
        if is_array_table:
            self._advance()

        self._skip_ws(allow_newline=False)
        parts = self._parse_key(allow_newline=False)
        self._skip_ws(allow_newline=False)

        if is_array_table:
            self._expect("]")
            self._expect("]")
        else:
            self._expect("]")

        self._consume_statement_end()
        self._navigate_table(parts, is_array_table=is_array_table)

    def _navigate_table(self, parts: list[str], is_array_table: bool) -> None:
        if not parts:
            self._error("表名不能为空")

        parent = self.root
        for part in parts[:-1]:
            parent = self._get_or_create_child_table(parent, part)

        name = parts[-1]
        parent_meta = self._table_meta(parent)
        if parent_meta.frozen:
            self._error("不能向内联表添加键或子表")

        existing = parent.get(name)
        if is_array_table:
            if existing is None:
                array: list[Any] = []
                parent[name] = array
                self._array_table_lists.add(id(array))
            elif isinstance(existing, list):
                if id(existing) not in self._array_table_lists:
                    self._error("不能向静态数组追加数组表")
                array = existing
            else:
                self._error("数组表与已定义的键或表冲突")

            new_table: TomlDict = {}
            array.append(new_table)
            self._meta[id(new_table)] = _TableMeta(explicit=True)
            self.current_table = new_table
            return

        if existing is None:
            table: TomlDict = {}
            parent[name] = table
            self._meta[id(table)] = _TableMeta()
        elif isinstance(existing, list):
            self._error("普通表与数组表或数组值冲突")
        elif isinstance(existing, dict):
            table = existing
        else:
            self._error("普通表与已定义的值冲突")

        meta = self._table_meta(table)
        if meta.frozen:
            self._error("不能重新打开内联表")
        if meta.explicit or meta.defined_by_dotted:
            self._error("不能重复定义表")
        meta.explicit = True
        self.current_table = table

    def _parse_key_value(self, table: TomlDict, mark_dotted: bool, allow_newline: bool) -> None:
        parts = self._parse_key(allow_newline=allow_newline)
        self._skip_ws(allow_newline=allow_newline)
        self._expect("=")
        self._skip_ws(allow_newline=allow_newline)
        value = self._parse_value(terminators=",}" if allow_newline else "")
        self._set_key(table, parts, value, mark_dotted=mark_dotted)

    def _parse_key(self, allow_newline: bool) -> list[str]:
        parts = [self._parse_key_part()]
        while True:
            self._skip_ws(allow_newline=allow_newline)
            if self._peek() != ".":
                return parts
            self._advance()
            self._skip_ws(allow_newline=allow_newline)
            parts.append(self._parse_key_part())

    def _parse_key_part(self) -> str:
        ch = self._peek()
        if ch == '"':
            if self._starts_with('"""'):
                self._error("键名不能使用多行字符串")
            return self._parse_basic_string(multiline=False)
        if ch == "'":
            if self._starts_with("'''"):
                self._error("键名不能使用多行字符串")
            return self._parse_literal_string(multiline=False)

        chars: list[str] = []
        while not self._eof() and _BARE_KEY_RE.fullmatch(self._peek()):
            chars.append(self._peek())
            self._advance()
        if not chars:
            self._error("裸键不能为空或包含非法字符")
        return "".join(chars)

    def _set_key(
        self,
        table: TomlDict,
        parts: list[str],
        value: Any,
        mark_dotted: bool,
    ) -> None:
        current = table
        for part in parts[:-1]:
            current_meta = self._table_meta(current)
            if current_meta.frozen:
                self._error("不能向内联表添加键或子表")

            existing = current.get(part)
            if existing is None:
                child: TomlDict = {}
                current[part] = child
                self._meta[id(child)] = _TableMeta(defined_by_dotted=mark_dotted)
                current = child
                continue

            if isinstance(existing, list):
                if id(existing) not in self._array_table_lists or not existing:
                    self._error("不能把数组当作表使用")
                current = existing[-1]
            elif isinstance(existing, dict):
                current = existing
            else:
                self._error("不能把已定义的值当作表使用")

            child_meta = self._table_meta(current)
            if child_meta.frozen:
                self._error("不能向内联表添加键或子表")
            if mark_dotted:
                child_meta.defined_by_dotted = True

        target_meta = self._table_meta(current)
        if target_meta.frozen:
            self._error("不能向内联表添加键")

        name = parts[-1]
        if name in current:
            self._error("不能重复定义键")
        current[name] = value

    def _get_or_create_child_table(self, table: TomlDict, key: str) -> TomlDict:
        meta = self._table_meta(table)
        if meta.frozen:
            self._error("不能向内联表添加子表")

        existing = table.get(key)
        if existing is None:
            child: TomlDict = {}
            table[key] = child
            self._meta[id(child)] = _TableMeta()
            return child
        if isinstance(existing, list):
            if id(existing) not in self._array_table_lists or not existing:
                self._error("不能把数组当作表使用")
            return existing[-1]
        if isinstance(existing, dict):
            child_meta = self._table_meta(existing)
            if child_meta.frozen:
                self._error("不能向内联表添加子表")
            return existing
        self._error("不能把已定义的值当作表使用")

    def _parse_value(self, terminators: str) -> Any:
        if self._eof():
            self._error("缺少 TOML 值")

        ch = self._peek()
        if ch == '"':
            return self._parse_basic_string(multiline=self._starts_with('"""'))
        if ch == "'":
            return self._parse_literal_string(multiline=self._starts_with("'''"))
        if ch == "[":
            return self._parse_array()
        if ch == "{":
            return self._parse_inline_table()
        return self._parse_bare_value(terminators=terminators)

    def _parse_bare_value(self, terminators: str) -> Any:
        start_line = self._line
        start_column = self._column
        chars: list[str] = []
        while not self._eof():
            ch = self._peek()
            if ch == "\n" or ch == "#" or ch in terminators:
                break
            chars.append(ch)
            self._advance()

        token = "".join(chars).strip()
        if not token:
            raise TomlDecodeError("缺少 TOML 值", start_line, start_column)
        return self._parse_token(token, start_line, start_column)

    def _parse_token(self, token: str, line: int, column: int) -> Any:
        if token == "true":
            return True
        if token == "false":
            return False
        if token in {"inf", "+inf", "-inf", "nan", "+nan", "-nan"}:
            return float(token)

        try:
            datetime_value = self._parse_datetime_token(token)
        except ValueError as e:
            raise TomlDecodeError(f"无效的日期或时间值: {token}", line, column) from e
        if datetime_value is not None:
            return datetime_value

        if _HEX_INT_RE.fullmatch(token):
            return int(token[2:].replace("_", ""), 16)
        if _OCT_INT_RE.fullmatch(token):
            return int(token[2:].replace("_", ""), 8)
        if _BIN_INT_RE.fullmatch(token):
            return int(token[2:].replace("_", ""), 2)
        if _DEC_INT_RE.fullmatch(token):
            return int(token.replace("_", ""), 10)
        if _FLOAT_RE.fullmatch(token):
            return float(token.replace("_", ""))

        raise TomlDecodeError(f"无效的 TOML 值: {token}", line, column)

    def _parse_datetime_token(self, token: str) -> datetime | date | time | None:
        dt_match = _DATETIME_RE.fullmatch(token)
        if dt_match:
            year, month, day, hour, minute, second, fraction, offset = dt_match.groups()
            tz = self._parse_timezone(offset)
            return datetime(
                int(year),
                int(month),
                int(day),
                int(hour),
                int(minute),
                int(second or "0"),
                self._parse_microsecond(fraction),
                tzinfo=tz,
            )

        date_match = _DATE_RE.fullmatch(token)
        if date_match:
            year, month, day = date_match.groups()
            return date(int(year), int(month), int(day))

        time_match = _TIME_RE.fullmatch(token)
        if time_match:
            hour, minute, second, fraction = time_match.groups()
            return time(
                int(hour),
                int(minute),
                int(second or "0"),
                self._parse_microsecond(fraction),
            )

        return None

    def _parse_timezone(self, offset: str | None) -> timezone | None:
        if offset is None:
            return None
        if offset == "Z":
            return timezone.utc
        sign = 1 if offset[0] == "+" else -1
        hours = int(offset[1:3])
        minutes = int(offset[4:6])
        return timezone(sign * timedelta(hours=hours, minutes=minutes))

    def _parse_microsecond(self, fraction: str | None) -> int:
        if fraction is None:
            return 0
        return int((fraction[1:] + "000000")[:6])

    def _parse_array(self) -> list[Any]:
        values: list[Any] = []
        self._expect("[")
        self._skip_ws_comments(allow_newline=True)
        if self._peek() == "]":
            self._advance()
            return values

        while True:
            values.append(self._parse_value(terminators=",]"))
            self._skip_ws_comments(allow_newline=True)
            if self._peek() == ",":
                self._advance()
                self._skip_ws_comments(allow_newline=True)
                if self._peek() == "]":
                    self._advance()
                    return values
                continue
            if self._peek() == "]":
                self._advance()
                return values
            self._error("数组元素之间必须使用逗号分隔")

    def _parse_inline_table(self) -> TomlDict:
        table: TomlDict = {}
        self._meta[id(table)] = _TableMeta()
        self._expect("{")
        self._skip_ws_comments(allow_newline=True)
        if self._peek() == "}":
            self._advance()
            self._freeze_inline_table(table)
            return table

        while True:
            self._parse_key_value(table, mark_dotted=False, allow_newline=True)
            self._skip_ws_comments(allow_newline=True)
            if self._peek() == ",":
                self._advance()
                self._skip_ws_comments(allow_newline=True)
                if self._peek() == "}":
                    self._advance()
                    self._freeze_inline_table(table)
                    return table
                continue
            if self._peek() == "}":
                self._advance()
                self._freeze_inline_table(table)
                return table
            self._error("内联表键值对之间必须使用逗号分隔")

    def _freeze_inline_table(self, table: TomlDict) -> None:
        self._table_meta(table).frozen = True
        for value in table.values():
            if isinstance(value, dict):
                self._freeze_inline_table(value)
            elif isinstance(value, list):
                self._freeze_inline_values(value)

    def _freeze_inline_values(self, values: list[Any]) -> None:
        for value in values:
            if isinstance(value, dict):
                self._freeze_inline_table(value)
            elif isinstance(value, list):
                self._freeze_inline_values(value)

    def _parse_basic_string(self, multiline: bool) -> str:
        if multiline:
            self._expect('"""')
            if self._peek() == "\n":
                self._advance()
        else:
            self._expect('"')

        result: list[str] = []
        while not self._eof():
            ch = self._peek()
            if ch == '"':
                if multiline:
                    quote_count = self._count_repeated('"')
                    if quote_count >= 3:
                        if quote_count > 5:
                            self._error("多行基础字符串中未转义的引号过多")
                        result.append('"' * (quote_count - 3))
                        self._advance(quote_count)
                        return "".join(result)
                    result.append('"' * quote_count)
                    self._advance(quote_count)
                    continue

                self._advance()
                return "".join(result)

            if ch == "\\":
                if multiline and self._consume_line_ending_backslash():
                    continue
                result.append(self._parse_escape_sequence())
                continue

            self._validate_string_char(ch, multiline=multiline)
            result.append(ch)
            self._advance()

        self._error("字符串未闭合")

    def _parse_literal_string(self, multiline: bool) -> str:
        if multiline:
            self._expect("'''")
            if self._peek() == "\n":
                self._advance()
        else:
            self._expect("'")

        result: list[str] = []
        while not self._eof():
            ch = self._peek()
            if ch == "'":
                if multiline:
                    quote_count = self._count_repeated("'")
                    if quote_count >= 3:
                        if quote_count > 5:
                            self._error("多行字面量字符串中未转义的引号过多")
                        result.append("'" * (quote_count - 3))
                        self._advance(quote_count)
                        return "".join(result)
                    result.append("'" * quote_count)
                    self._advance(quote_count)
                    continue

                self._advance()
                return "".join(result)

            self._validate_string_char(ch, multiline=multiline)
            result.append(ch)
            self._advance()

        self._error("字符串未闭合")

    def _parse_escape_sequence(self) -> str:
        self._expect("\\")
        ch = self._peek()
        escapes = {
            "b": "\b",
            "t": "\t",
            "n": "\n",
            "f": "\f",
            "r": "\r",
            "e": "\x1b",
            '"': '"',
            "\\": "\\",
        }
        if ch in escapes:
            self._advance()
            return escapes[ch]
        if ch == "x":
            return self._parse_unicode_escape(length=2)
        if ch == "u":
            return self._parse_unicode_escape(length=4)
        if ch == "U":
            return self._parse_unicode_escape(length=8)
        self._error("无效的字符串转义序列")

    def _parse_unicode_escape(self, length: int) -> str:
        self._advance()
        digits = self._data[self._pos : self._pos + length]
        if len(digits) != length or not all(ch in "0123456789abcdefABCDEF" for ch in digits):
            self._error("无效的 Unicode 转义序列")
        value = int(digits, 16)
        if value > 0x10FFFF or 0xD800 <= value <= 0xDFFF:
            self._error("Unicode 转义必须是有效的标量值")
        self._advance(length)
        return chr(value)

    def _consume_line_ending_backslash(self) -> bool:
        idx = self._pos + 1
        while idx < len(self._data) and self._data[idx] in " \t":
            idx += 1
        if idx >= len(self._data) or self._data[idx] != "\n":
            return False

        self._advance()
        while self._peek() and self._peek() in " \t":
            self._advance()
        self._expect("\n")
        while self._peek() and self._peek() in " \t\n":
            self._advance()
        return True

    def _validate_string_char(self, ch: str, multiline: bool) -> None:
        code = ord(ch)
        if ch == "\n" and not multiline:
            self._error("单行字符串不能包含换行")
        if ch == "\t":
            return
        if ch == "\n" and multiline:
            return
        if code <= 0x1F or code == 0x7F:
            self._error("字符串包含未转义的控制字符")

    def _consume_statement_end(self) -> None:
        self._skip_ws(allow_newline=False)
        if self._peek() == "#":
            self._consume_comment()
        if self._eof():
            return
        if self._peek() == "\n":
            self._advance()
            return
        self._error("键值对后必须是换行或文件结束")

    def _skip_ws_comments(self, allow_newline: bool) -> None:
        while True:
            self._skip_ws(allow_newline=allow_newline)
            if self._peek() == "#":
                self._consume_comment()
                continue
            break

    def _skip_ws(self, allow_newline: bool) -> None:
        while True:
            ch = self._peek()
            if ch and ch in " \t":
                self._advance()
            elif allow_newline and ch == "\n":
                self._advance()
            else:
                return

    def _consume_comment(self) -> None:
        self._expect("#")
        while not self._eof() and self._peek() != "\n":
            ch = self._peek()
            code = ord(ch)
            if ch != "\t" and (code <= 0x1F or code == 0x7F):
                self._error("注释包含非法控制字符")
            self._advance()

    def _table_meta(self, table: TomlDict) -> _TableMeta:
        table_id = id(table)
        if table_id not in self._meta:
            self._meta[table_id] = _TableMeta()
        return self._meta[table_id]

    def _count_repeated(self, char: str) -> int:
        count = 0
        while self._peek(count) == char:
            count += 1
        return count

    def _starts_with(self, text: str) -> bool:
        return self._data.startswith(text, self._pos)

    def _expect(self, text: str) -> None:
        if not self._starts_with(text):
            self._error(f"期望 {text!r}")
        self._advance(len(text))

    def _peek(self, offset: int = 0) -> str:
        idx = self._pos + offset
        if idx >= len(self._data):
            return ""
        return self._data[idx]

    def _advance(self, count: int = 1) -> None:
        for _ in range(count):
            if self._eof():
                return
            ch = self._data[self._pos]
            self._pos += 1
            if ch == "\n":
                self._line += 1
                self._column = 1
            else:
                self._column += 1

    def _eof(self) -> bool:
        return self._pos >= len(self._data)

    def _error(self, message: str) -> NoReturn:
        raise TomlDecodeError(message, self._line, self._column)


def loads(
    data: str,
) -> TomlDict:
    """解析 TOML 格式的字符串并返回字典

    Args:
        data (str):
            待解析的 TOML 文本内容

    Returns:
        TomlDict:
            解析后的字典对象
    """
    return TomlParser().loads(data)


def load(
    fp: BinaryIO,
) -> TomlDict:
    """解析 TOML 格式的二进制流并返回字典

    Args:
        fp (BinaryIO):
            待解析的 TOML 二进制流

    Returns:
        TomlDict:
            解析后的字典对象
    """
    return TomlParser().load(fp)
