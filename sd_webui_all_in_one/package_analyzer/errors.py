"""Python 软件包分析工具的异常与诊断信息定义

所有解析异常均继承自 ``ValueError``, 以兼容现有的 ``except ValueError`` 处理逻辑.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


class PackageAnalyzerError(ValueError):
    """软件包分析工具的异常基类"""


class InvalidName(PackageAnalyzerError):
    """软件包名或 extra 名不符合规范"""


class InvalidVersion(PackageAnalyzerError):
    """版本号不符合版本标识符规范"""


class InvalidSpecifier(PackageAnalyzerError):
    """版本约束不符合版本标识符规范"""


class InvalidMarker(PackageAnalyzerError):
    """环境标记表达式不符合依赖声明规范"""


class UndefinedEnvironmentName(PackageAnalyzerError):
    """环境标记引用了当前上下文未定义的字段"""


class InvalidRequirement(PackageAnalyzerError):
    """依赖声明不符合依赖声明规范

    Attributes:
        text (str):
            原始依赖声明文本
        position (int | None):
            出错位置 (从 0 开始的字符下标), 未知时为 ``None``
    """

    def __init__(
        self,
        message: str,
        text: str = "",
        position: int | None = None,
    ) -> None:
        """初始化依赖声明解析异常

        Args:
            message (str):
                错误描述
            text (str):
                原始依赖声明文本
            position (int | None):
                出错位置
        """
        self.message = message
        self.text = text
        self.position = position
        super().__init__(self._render())

    def _render(self) -> str:
        """生成带有出错位置标记的错误信息

        Returns:
            str: 错误信息
        """
        if self.position is None or not self.text:
            return self.message
        return f"{self.message}\n    {self.text}\n    {' ' * self.position}^"


class InvalidWheelFilename(PackageAnalyzerError):
    """Wheel 文件名不符合二进制分发格式规范"""


class InvalidSdistFilename(PackageAnalyzerError):
    """源码包文件名不符合源码分发格式规范"""


class RequirementsFileError(PackageAnalyzerError):
    """依赖文件解析错误

    Attributes:
        path (str | None):
            出错的依赖文件路径
        lineno (int | None):
            出错的行号 (从 1 开始)
    """

    def __init__(
        self,
        message: str,
        path: str | None = None,
        lineno: int | None = None,
    ) -> None:
        """初始化依赖文件解析异常

        Args:
            message (str):
                错误描述
            path (str | None):
                出错的依赖文件路径
            lineno (int | None):
                出错的行号
        """
        self.message = message
        self.path = path
        self.lineno = lineno
        super().__init__(format_location(message, path, lineno))


class UnsupportedOption(RequirementsFileError):
    """依赖文件中出现了不支持的选项"""


class RecursiveInclude(RequirementsFileError):
    """依赖文件之间存在循环引用"""


class NestedFileNotFound(RequirementsFileError):
    """依赖文件引用的嵌套文件无法读取"""


def format_location(
    message: str,
    path: str | None,
    lineno: int | None,
) -> str:
    """为信息添加 ``文件:行号`` 前缀

    Args:
        message (str):
            信息内容
        path (str | None):
            文件路径
        lineno (int | None):
            行号

    Returns:
        str: 带有位置前缀的信息
    """
    if path is None and lineno is None:
        return message
    location = path if path is not None else "<string>"
    if lineno is not None:
        location = f"{location}:{lineno}"
    return f"{location}: {message}"


@dataclass(frozen=True)
class Diagnostic:
    """解析或检查过程中产生的诊断信息

    Attributes:
        severity (Literal["warning", "error"]):
            严重程度. ``warning`` 表示条目有效但无法完全处理, ``error`` 表示条目无效
        message (str):
            诊断信息内容
        path (str | None):
            相关依赖文件路径
        lineno (int | None):
            相关行号 (从 1 开始)
    """

    severity: Literal["warning", "error"]
    message: str
    path: str | None = None
    lineno: int | None = None

    def __str__(self) -> str:
        return format_location(self.message, self.path, self.lineno)
