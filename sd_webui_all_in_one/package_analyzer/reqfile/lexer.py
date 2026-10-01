"""依赖文件词法处理: 将文件字节内容转换为逻辑行

处理流程与 pip 的 ``pip._internal.req.req_file`` 保持一致:
    1. 根据 BOM 或 PEP 263 编码声明解码
    2. 合并以反斜杠结尾的续行
    3. 移除注释 (``#`` 位于行首或前面有空白时才视为注释)
    4. 展开 ``${VAR}`` 形式的环境变量
"""

from __future__ import annotations

import codecs
import os
import re
from dataclasses import dataclass
from typing import (
    Iterator,
    Mapping,
)


BOMS: tuple[tuple[bytes, str], ...] = (
    (codecs.BOM_UTF8, "utf-8"),
    (codecs.BOM_UTF32, "utf-32"),
    (codecs.BOM_UTF32_BE, "utf-32-be"),
    (codecs.BOM_UTF32_LE, "utf-32-le"),
    (codecs.BOM_UTF16, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
)
"""BOM 与编码的对应表. 顺序很重要: UTF-16 LE 的 BOM 是 UTF-32 LE 的 BOM 的前缀"""

COMMENT_REGEX = re.compile(r"(^|\s+)#.*$")
"""注释匹配规则: ``#`` 必须位于行首或前面有空白, 因此 URL 中的 ``#egg=`` 等片段不会被当作注释"""

ENV_VAR_REGEX = re.compile(r"(?P<var>\$\{(?P<name>[A-Z0-9_]+)\})")
"""环境变量引用匹配规则, 仅支持 ``${VAR}`` 形式, 变量名只能包含大写字母, 数字和下划线"""

_PEP263_ENCODING_REGEX = re.compile(rb"coding[:=]\s*([-\w.]+)")

DIRECTIVE_SKIP_VERIFY = "skip_verify"
"""项目自定义指令: 行尾注释中包含 ``skip_verify`` 时, 该依赖不参与安装状态检查"""

KNOWN_DIRECTIVES: tuple[str, ...] = (DIRECTIVE_SKIP_VERIFY,)
"""可在行尾注释中使用的项目自定义指令"""


@dataclass(frozen=True)
class LogicalLine:
    """依赖文件中的一条逻辑行 (已合并续行, 移除注释并展开环境变量)

    Attributes:
        lineno (int):
            逻辑行起始的物理行号 (从 1 开始)
        text (str):
            逻辑行内容
        directives (frozenset[str]):
            行尾注释中声明的项目自定义指令
    """

    lineno: int
    text: str
    directives: frozenset[str] = frozenset()


def decode_requirements(
    data: bytes,
) -> str:
    """解码依赖文件内容

    依次尝试: BOM 指定的编码, 前两行中 PEP 263 风格的编码声明 (``# -*- coding: xxx -*-``), UTF-8.

    Args:
        data (bytes):
            依赖文件的字节内容

    Returns:
        str: 解码后的文本

    Raises:
        UnicodeDecodeError:
            内容无法按检测到的编码解码时
    """
    for bom, encoding in BOMS:
        if data.startswith(bom):
            return data[len(bom) :].decode(encoding)

    for line in data.split(b"\n")[:2]:
        if line[0:1] == b"#":
            match = _PEP263_ENCODING_REGEX.search(line)
            if match is not None:
                try:
                    return data.decode(match.group(1).decode("ascii"))
                except LookupError:
                    # 声明了未知编码时回退到 UTF-8
                    break

    return data.decode("utf-8")


def _join_lines(
    text: str,
) -> Iterator[tuple[int, str]]:
    """合并以反斜杠结尾的续行

    续行中间的注释行不会被拼接进逻辑行.

    Args:
        text (str):
            依赖文件文本

    Yields:
        tuple[int, str]: ``(起始行号, 逻辑行内容)``
    """
    primary_lineno = 0
    pending: list[str] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.endswith("\\") or COMMENT_REGEX.match(line):
            if COMMENT_REGEX.match(line):
                # 在注释行前补一个空格, 保证拼接后仍能按注释规则移除
                line = " " + line
            if pending:
                pending.append(line)
                yield primary_lineno, "".join(pending)
                pending = []
            else:
                yield lineno, line
        else:
            if not pending:
                primary_lineno = lineno
            pending.append(line.strip("\\"))

    if pending:
        yield primary_lineno, "".join(pending)


def expand_env_variables(
    text: str,
    environ: Mapping[str, str] | None = None,
) -> str:
    """展开文本中的 ``${VAR}`` 环境变量引用

    只替换已定义的环境变量, 未定义的引用保持原样.

    Args:
        text (str):
            待处理文本
        environ (Mapping[str, str] | None):
            环境变量映射, 为 ``None`` 时使用 ``os.environ``

    Returns:
        str: 展开环境变量后的文本
    """
    env = os.environ if environ is None else environ
    for var, name in ENV_VAR_REGEX.findall(text):
        value = env.get(name)
        if value is not None:
            text = text.replace(var, value)
    return text


def iter_logical_lines(
    text: str,
    environ: Mapping[str, str] | None = None,
    expand_env: bool = True,
) -> Iterator[LogicalLine]:
    """将依赖文件文本拆分为逻辑行

    Args:
        text (str):
            依赖文件文本
        environ (Mapping[str, str] | None):
            环境变量映射, 为 ``None`` 时使用 ``os.environ``
        expand_env (bool):
            是否展开 ``${VAR}`` 环境变量引用

    Yields:
        LogicalLine: 非空的逻辑行
    """
    for lineno, line in _join_lines(text):
        directives: frozenset[str] = frozenset()
        comment = COMMENT_REGEX.search(line)
        if comment is not None:
            directives = frozenset(directive for directive in KNOWN_DIRECTIVES if directive in comment.group())
            line = line[: comment.start()]
        line = line.strip()
        if not line:
            continue
        if expand_env:
            line = expand_env_variables(line, environ)
        yield LogicalLine(lineno=lineno, text=line, directives=directives)
