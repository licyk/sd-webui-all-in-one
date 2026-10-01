"""依赖文件解析结果的数据模型"""

from __future__ import annotations

from dataclasses import (
    dataclass,
    field,
)
from enum import Enum
from pathlib import Path

from sd_webui_all_in_one.package_analyzer.errors import Diagnostic
from sd_webui_all_in_one.package_analyzer.markers import (
    Marker,
    MarkerEnvironment,
)
from sd_webui_all_in_one.package_analyzer.names import normalize_name
from sd_webui_all_in_one.package_analyzer.reqfile.lexer import DIRECTIVE_SKIP_VERIFY
from sd_webui_all_in_one.package_analyzer.requirement import Requirement
from sd_webui_all_in_one.package_analyzer.version import Version


class EntryKind(str, Enum):
    """依赖条目的类别"""

    NAMED = "named"
    """符合依赖声明规范的条目, 如 ``torch==2.3.0`` 或 ``pkg @ https://...``"""

    URL = "url"
    """未命名的 URL 条目, 如 ``git+https://...`` 或 ``https://.../pkg.whl``"""

    PATH = "path"
    """本地路径条目, 如 ``./pkg``, ``-e .`` 或 ``file:///...``"""


@dataclass(frozen=True)
class SourceLocation:
    """依赖条目在依赖文件中的位置

    Attributes:
        path (str | None):
            依赖文件路径, 直接解析文本时为 ``None``
        lineno (int):
            行号 (从 1 开始)
    """

    path: str | None
    lineno: int

    def __str__(self) -> str:
        return f"{self.path if self.path is not None else '<string>'}:{self.lineno}"


@dataclass(frozen=True)
class RequirementEntry:
    """依赖文件中的一个依赖条目

    Attributes:
        kind (EntryKind):
            条目类别
        raw (str):
            条目的原始文本 (不含选项)
        source (SourceLocation):
            条目所在位置
        requirement (Requirement | None):
            ``NAMED`` 条目对应的依赖声明对象
        name (str | None):
            软件包名. ``URL`` / ``PATH`` 条目的名称来自 ``#egg=`` 片段, Wheel 文件名
            或本地项目的静态元数据, 无法确定时为 ``None``
        extras (tuple[str, ...]):
            请求的 extras
        version (Version | None):
            从 Wheel 文件名推断出的版本号
        url (str | None):
            ``URL`` 条目或 ``name @ url`` 条目的 URL
        path (Path | None):
            ``PATH`` 条目解析后的绝对路径
        vcs (str | None):
            版本控制系统名称 (``git`` / ``hg`` / ``svn`` / ``bzr``)
        revision (str | None):
            VCS URL 中 ``@`` 之后指定的修订版本
        subdirectory (str | None):
            URL 的 ``#subdirectory=`` 片段
        marker (Marker | None):
            环境标记
        editable (bool):
            是否为 ``-e`` / ``--editable`` 条目
        constraint (bool):
            是否来自约束文件 (``-c``)
        hashes (tuple[str, ...]):
            ``--hash`` 选项及 URL 片段中声明的哈希值, 形如 ``sha256:...``
        config_settings (tuple[str, ...]):
            ``--config-settings`` 选项的值
        directives (frozenset[str]):
            行尾注释中声明的项目自定义指令
    """

    kind: EntryKind
    raw: str
    source: SourceLocation
    requirement: Requirement | None = None
    name: str | None = None
    extras: tuple[str, ...] = ()
    version: Version | None = None
    url: str | None = None
    path: Path | None = None
    vcs: str | None = None
    revision: str | None = None
    subdirectory: str | None = None
    marker: Marker | None = None
    editable: bool = False
    constraint: bool = False
    hashes: tuple[str, ...] = ()
    config_settings: tuple[str, ...] = ()
    directives: frozenset[str] = frozenset()

    @property
    def normalized_name(self) -> str | None:
        """规范化后的软件包名, 名称未知时为 ``None``

        Returns:
            str | None: 规范化后的软件包名, 名称未知时为 ``None``
        """
        return normalize_name(self.name) if self.name is not None else None

    @property
    def skip_verify(self) -> bool:
        """条目是否声明了 ``# skip_verify`` 指令

        Returns:
            bool: 条目是否声明了 ``# skip_verify`` 指令
        """
        return DIRECTIVE_SKIP_VERIFY in self.directives

    def applies_to(
        self,
        environment: MarkerEnvironment | None = None,
    ) -> bool:
        """判断此条目在指定环境下是否生效

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
        return f"-e {self.raw}" if self.editable else self.raw


@dataclass
class FileOptions:
    """依赖文件中声明的全局选项

    Attributes:
        index_url (str | None):
            ``-i`` / ``--index-url``, 多次出现时取最后一个
        extra_index_urls (list[str]):
            ``--extra-index-url``
        no_index (bool):
            ``--no-index``
        find_links (list[str]):
            ``-f`` / ``--find-links``
        no_binary (set[str]):
            ``--no-binary`` 指定的软件包名 (或 ``:all:``)
        only_binary (set[str]):
            ``--only-binary`` 指定的软件包名 (或 ``:all:``)
        prefer_binary (bool):
            ``--prefer-binary``
        require_hashes (bool):
            ``--require-hashes`` (会被 ``--no-require-hashes`` 取消)
        pre (bool):
            ``--pre``
        all_releases (set[str]):
            ``--all-releases`` 指定的软件包名 (或 ``:all:``)
        only_final (set[str]):
            ``--only-final`` 指定的软件包名 (或 ``:all:``)
        trusted_hosts (list[str]):
            ``--trusted-host``
        features (list[str]):
            ``--use-feature``
    """

    index_url: str | None = None
    extra_index_urls: list[str] = field(default_factory=list)
    no_index: bool = False
    find_links: list[str] = field(default_factory=list)
    no_binary: set[str] = field(default_factory=set)
    only_binary: set[str] = field(default_factory=set)
    prefer_binary: bool = False
    require_hashes: bool = False
    pre: bool = False
    all_releases: set[str] = field(default_factory=set)
    only_final: set[str] = field(default_factory=set)
    trusted_hosts: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)


@dataclass
class RequirementsFile:
    """依赖文件的解析结果

    Attributes:
        path (str | None):
            根依赖文件路径, 直接解析文本时为 ``None``
        entries (list[RequirementEntry]):
            依赖条目 (含可编辑条目与嵌套文件中的条目), 保持声明顺序
        constraints (list[RequirementEntry]):
            约束条目 (来自 ``-c`` 引用的文件)
        options (FileOptions):
            全局选项
        includes (list[str]):
            通过 ``-r`` / ``-c`` 引用并已读取的嵌套文件
        diagnostics (list[Diagnostic]):
            解析过程中产生的诊断信息
    """

    path: str | None = None
    entries: list[RequirementEntry] = field(default_factory=list)
    constraints: list[RequirementEntry] = field(default_factory=list)
    options: FileOptions = field(default_factory=FileOptions)
    includes: list[str] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def editables(self) -> list[RequirementEntry]:
        """可编辑条目列表

        Returns:
            list[RequirementEntry]: 可编辑条目列表
        """
        return [entry for entry in self.entries if entry.editable]

    @property
    def errors(self) -> list[Diagnostic]:
        """严重程度为 ``error`` 的诊断信息

        Returns:
            list[Diagnostic]: 严重程度为 ``error`` 的诊断信息
        """
        return [diagnostic for diagnostic in self.diagnostics if diagnostic.severity == "error"]

    @property
    def warnings(self) -> list[Diagnostic]:
        """严重程度为 ``warning`` 的诊断信息

        Returns:
            list[Diagnostic]: 严重程度为 ``warning`` 的诊断信息
        """
        return [diagnostic for diagnostic in self.diagnostics if diagnostic.severity == "warning"]
