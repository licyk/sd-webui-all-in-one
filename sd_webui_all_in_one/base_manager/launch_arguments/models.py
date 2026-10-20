"""启动参数目录的数据模型与常量"""

from __future__ import annotations

import sys
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


CATALOG_SCHEMA_VERSION = 2
DEFAULT_DISCOVERY_TIMEOUT_SECONDS = 15.0
MAX_DIAGNOSTIC_OUTPUT = 4096


class LaunchArgumentValueKind(str, Enum):
    """启动参数值类型。"""

    BOOLEAN = "boolean"
    VALUE = "value"
    OPTIONAL_VALUE = "optional_value"
    MULTI_VALUE = "multi_value"


@dataclass(frozen=True, slots=True)
class LaunchArgumentDiagnostic:
    """启动参数发现诊断。"""

    severity: str
    code: str
    message: str
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class LaunchArgumentDefinition:
    """一个规范化的启动参数定义。"""

    name: str
    flags: list[str]
    value_kind: LaunchArgumentValueKind
    min_values: int
    max_values: int | None
    help: str
    category: str
    metavar: str | None
    choices: list[str]
    required: bool
    repeatable: bool
    exclusive_group: str | None
    exclusive_group_required: bool


@dataclass(frozen=True, slots=True)
class LaunchArgumentCatalog:
    """指定 WebUI 的启动参数目录。"""

    schema_version: int
    webui_type: str
    catalog_revision: str
    arguments: list[LaunchArgumentDefinition] = field(default_factory=list)
    diagnostics: list[LaunchArgumentDiagnostic] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """按稳定的蛇形命名 API 结构序列化。

        Returns:
            dict[str, object]: 可序列化的参数目录。
        """
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LaunchArgumentDiscoveryContext:
    """启动参数发现上下文。"""

    webui_type: str
    webui_path: Path
    python_executable: Path = Path(sys.executable)
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS


@dataclass(frozen=True, slots=True)
class HelpCommand:
    """用于提取帮助文档的子进程命令。"""

    argv: list[str]
    source_identity: str
    env: dict[str, str] | None = None
