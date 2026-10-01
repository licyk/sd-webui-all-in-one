"""版本约束对象

基于版本标识符规范实现版本约束 (``>=1.0``, ``==2.*`` 等) 的校验与匹配.

参考:
    - https://packaging.python.org/en/latest/specifications/version-specifiers/
    - https://peps.python.org/pep-0440/
"""

from __future__ import annotations

import re
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Iterable,
    Iterator,
)

from sd_webui_all_in_one.package_analyzer.errors import (
    InvalidSpecifier,
    InvalidVersion,
)
from sd_webui_all_in_one.package_analyzer.version import Version


OPERATORS: tuple[str, ...] = ("===", "~=", "==", "!=", "<=", ">=", "<", ">")
"""版本比较操作符, 按长度从长到短排列以便前缀匹配"""

_SPECIFIER_REGEX = re.compile(r"^\s*(?P<operator>===|~=|==|!=|<=|>=|<|>)\s*(?P<version>.*?)\s*$", re.DOTALL)


def _coerce_version(
    version: Version | str,
) -> Version | None:
    """将候选版本转换为版本号对象

    Args:
        version (Version | str):
            候选版本

    Returns:
        Version | None: 版本号对象, 字符串不是合法版本号时为 ``None``
    """
    if isinstance(version, Version):
        return version
    return Version.try_parse(version)


@dataclass(frozen=True, eq=False)
class Specifier:
    """单个版本约束, 如 ``>=1.0``

    构造时按规范校验:
        - ``.*`` 通配符只能用于 ``==`` 和 ``!=``, 且只能跟在 release 段之后
        - ``~=`` 至少需要两段 release, 且不能带本地版本标识
        - 本地版本标识不能用于 ``<``, ``<=``, ``>``, ``>=``, ``~=``
        - ``===`` 接受任意不含空白的字符串

    Attributes:
        operator (str):
            版本比较操作符
        version (str):
            约束中书写的版本号文本 (保留原始写法)
    """

    operator: str
    version: str
    _parsed: Version | None = field(init=False, repr=False)
    _wildcard: bool = field(init=False, repr=False)

    def __post_init__(self) -> None:
        operator = self.operator
        text = self.version.strip()
        object.__setattr__(self, "version", text)

        if operator not in OPERATORS:
            raise InvalidSpecifier(f"不合法的版本比较操作符: {operator!r}")
        if not text:
            raise InvalidSpecifier(f"版本约束 {operator!r} 缺少版本号")

        if operator == "===":
            if re.search(r"\s", text):
                raise InvalidSpecifier(f"=== 约束的版本号不能包含空白字符: {text!r}")
            object.__setattr__(self, "_parsed", None)
            object.__setattr__(self, "_wildcard", False)
            return

        wildcard = text.endswith(".*")
        body = text[:-2] if wildcard else text
        try:
            parsed = Version.parse(body)
        except InvalidVersion as e:
            raise InvalidSpecifier(f"版本约束 '{operator}{text}' 中的版本号不合法") from e

        if wildcard:
            if operator not in ("==", "!="):
                raise InvalidSpecifier(f"通配符 '.*' 只能用于 == 和 != 约束: '{operator}{text}'")
            if parsed.pre is not None or parsed.post is not None or parsed.dev is not None or parsed.local_segments is not None:
                raise InvalidSpecifier(f"通配符 '.*' 只能跟在 release 段之后: '{operator}{text}'")
        if parsed.local_segments is not None and operator not in ("==", "!="):
            raise InvalidSpecifier(f"本地版本标识不能用于 {operator} 约束: '{operator}{text}'")
        if operator == "~=" and len(parsed.release) < 2:
            raise InvalidSpecifier(f"~= 约束至少需要两段 release 版本号: '{operator}{text}'")

        object.__setattr__(self, "_parsed", parsed)
        object.__setattr__(self, "_wildcard", wildcard)

    @classmethod
    def parse(
        cls,
        text: str,
    ) -> Specifier:
        """解析单个版本约束字符串

        Args:
            text (str):
                版本约束字符串, 如 ``">=1.0"``

        Returns:
            Specifier: 版本约束对象

        Raises:
            InvalidSpecifier:
                版本约束不符合规范时
        """
        match = _SPECIFIER_REGEX.match(text)
        if match is None:
            raise InvalidSpecifier(f"不合法的版本约束: {text!r}")
        return cls(match.group("operator"), match.group("version"))

    @property
    def parsed_version(self) -> Version | None:
        """约束中的版本号对象 (不含 ``.*`` 通配符)

        Returns:
            Version | None: 版本号对象. ``===`` 约束的版本号不要求合法, 无法解析时为 ``None``
        """
        if self._parsed is not None:
            return self._parsed
        return Version.try_parse(self.version)

    @property
    def is_wildcard(self) -> bool:
        """是否为带 ``.*`` 通配符的前缀匹配约束

        Returns:
            bool: 是否为带 ``.*`` 通配符的前缀匹配约束
        """
        return self._wildcard

    @property
    def prereleases(self) -> bool:
        """此约束是否显式指向预发布版本 (如 ``>=1.0rc1``)

        Returns:
            bool: 此约束是否显式指向预发布版本 (如 ``>=1.0rc1``)
        """
        if self.operator == "!=" or self._wildcard:
            return False
        parsed = self._parsed if self._parsed is not None else Version.try_parse(self.version)
        return parsed is not None and parsed.is_prerelease

    def matches(
        self,
        version: Version | str,
    ) -> bool:
        """判断候选版本是否满足此约束 (不考虑预发布版本的过滤规则)

        Args:
            version (Version | str):
                候选版本. 无法解析为合法版本号的字符串只可能匹配 ``===`` 约束

        Returns:
            bool: 满足约束时返回 ``True``
        """
        if self.operator == "===":
            return str(version).strip().lower() == self.version.lower()

        candidate = _coerce_version(version)
        if candidate is None:
            return False

        spec = self._parsed
        assert spec is not None

        if self.operator == "==":
            return self._match_equal(candidate, spec)
        if self.operator == "!=":
            return not self._match_equal(candidate, spec)
        if self.operator == "~=":
            # ~= X.Y.Z 等价于 >= X.Y.Z, == X.Y.*
            prefix = spec.release[:-1]
            return candidate.without_local() >= spec and candidate.epoch == spec.epoch and _pad_release(candidate.release, len(prefix)) == prefix
        if self.operator == "<=":
            return candidate.without_local() <= spec
        if self.operator == ">=":
            return candidate.without_local() >= spec
        public = candidate.without_local()
        if self.operator == "<":
            if not public < spec:
                return False
            # <V 不能匹配 V 的预发布版本, 除非 V 自身是预发布版本
            if not spec.is_prerelease and public.is_prerelease:
                # 候选版本是 target 的预发布版本: X.Y.postN.devM 对应 X.Y.postN, 其余对应 X.Y
                if public.pre is None and public.post is not None:
                    target = Version(public.epoch, public.release, None, public.post)
                else:
                    target = Version(public.epoch, public.release)
                if target == spec:
                    return False
            return True

        # self.operator == ">". 比较时忽略候选版本的本地版本标识, 因此 >V 不会匹配 V 的本地版本
        if not public > spec:
            return False
        # >V 不能匹配 V 的后发布版本, 除非 V 自身是后发布版本
        if not spec.is_postrelease and public.is_postrelease and Version(public.epoch, public.release, public.pre) == spec:
            return False
        return True

    def _match_equal(
        self,
        candidate: Version,
        spec: Version,
    ) -> bool:
        """``==`` 约束的匹配逻辑

        Args:
            candidate (Version):
                候选版本
            spec (Version):
                约束中的版本

        Returns:
            bool: 匹配时返回 ``True``
        """
        if self._wildcard:
            return candidate.epoch == spec.epoch and _pad_release(candidate.release, len(spec.release)) == spec.release
        if spec.local_segments is None:
            # 约束不含本地版本标识时, 忽略候选版本的本地版本标识
            return candidate.without_local() == spec
        return candidate == spec

    def contains(
        self,
        version: Version | str,
        prereleases: bool | None = None,
    ) -> bool:
        """判断候选版本是否满足此约束, 并应用预发布版本过滤规则

        Args:
            version (Version | str):
                候选版本
            prereleases (bool | None):
                是否允许预发布版本. 仅为 ``False`` 时排除预发布版本:
                单个候选版本没有其他备选, 按规范应当接受预发布版本

        Returns:
            bool: 满足约束时返回 ``True``
        """
        if not self.matches(version):
            return False
        if prereleases is not False:
            return True
        candidate = _coerce_version(version)
        return candidate is None or not candidate.is_prerelease

    def _canonical(self) -> tuple[str, str]:
        """生成用于相等比较的规范化形式

        Returns:
            tuple[str, str]: ``(操作符, 规范化版本号)``
        """
        if self._parsed is None:
            return (self.operator, self.version.lower())
        return (self.operator, str(self._parsed) + (".*" if self._wildcard else ""))

    def __str__(self) -> str:
        return f"{self.operator}{self.version}"

    def __hash__(self) -> int:
        return hash(self._canonical())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Specifier):
            return NotImplemented
        return self._canonical() == other._canonical()


def _pad_release(
    release: tuple[int, ...],
    length: int,
) -> tuple[int, ...]:
    """将 release 段截断或补零到指定长度

    Args:
        release (tuple[int, ...]):
            release 段
        length (int):
            目标长度

    Returns:
        tuple[int, ...]: 调整长度后的 release 段
    """
    return (release + (0,) * length)[:length]


@dataclass(frozen=True, eq=False)
class SpecifierSet:
    """版本约束集合, 多个约束之间为逻辑与关系

    使用示例:
        ```python
        specs = SpecifierSet.parse(">=4.25.3,<5")
        specs.contains("4.26.0")  # True
        specs.contains("5.0")  # False
        ```

    Attributes:
        specifiers (tuple[Specifier, ...]):
            版本约束列表, 保持声明顺序
    """

    specifiers: tuple[Specifier, ...] = ()

    @classmethod
    def parse(
        cls,
        text: str,
    ) -> SpecifierSet:
        """解析以逗号分隔的版本约束字符串

        Args:
            text (str):
                版本约束字符串, 如 ``">=1.0,<2.0"``; 空字符串表示无约束

        Returns:
            SpecifierSet: 版本约束集合

        Raises:
            InvalidSpecifier:
                任一版本约束不符合规范时
        """
        parts = [part.strip() for part in text.split(",")]
        return cls(tuple(Specifier.parse(part) for part in parts if part))

    @property
    def prereleases(self) -> bool:
        """集合中是否有约束显式指向预发布版本

        Returns:
            bool: 集合中是否有约束显式指向预发布版本
        """
        return any(spec.prereleases for spec in self.specifiers)

    def contains(
        self,
        version: Version | str,
        prereleases: bool | None = None,
    ) -> bool:
        """判断候选版本是否满足集合中的所有约束

        Args:
            version (Version | str):
                候选版本
            prereleases (bool | None):
                是否允许预发布版本. 仅为 ``False`` 时排除预发布版本:
                单个候选版本没有其他备选, 按规范应当接受预发布版本

        Returns:
            bool: 满足所有约束时返回 ``True``
        """
        if prereleases is False:
            candidate = _coerce_version(version)
            if candidate is not None and candidate.is_prerelease:
                return False
        return all(spec.matches(version) for spec in self.specifiers)

    def filter(
        self,
        versions: Iterable[Version | str],
        prereleases: bool | None = None,
    ) -> list[Version | str]:
        """从候选版本中筛选出满足约束的版本

        未显式指定 ``prereleases`` 时, 优先返回正式版本; 没有任何正式版本满足约束时才返回预发布版本.

        Args:
            versions (Iterable[Version | str]):
                候选版本
            prereleases (bool | None):
                是否允许预发布版本

        Returns:
            list[Version | str]: 满足约束的候选版本, 保持原有顺序
        """
        matched = [version for version in versions if self.contains(version, prereleases=True)]
        if prereleases or (prereleases is None and self.prereleases):
            return matched

        finals: list[Version | str] = []
        for version in matched:
            candidate = _coerce_version(version)
            if candidate is None or not candidate.is_prerelease:
                finals.append(version)
        if finals or prereleases is False:
            return finals
        return matched

    def __iter__(self) -> Iterator[Specifier]:
        return iter(self.specifiers)

    def __len__(self) -> int:
        return len(self.specifiers)

    def __bool__(self) -> bool:
        return bool(self.specifiers)

    def __str__(self) -> str:
        return ",".join(str(spec) for spec in self.specifiers)

    def __hash__(self) -> int:
        return hash(frozenset(self.specifiers))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SpecifierSet):
            return NotImplemented
        return frozenset(self.specifiers) == frozenset(other.specifiers)
