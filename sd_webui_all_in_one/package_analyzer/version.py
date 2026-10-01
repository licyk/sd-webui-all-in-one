"""版本号对象

基于版本标识符规范实现版本号的解析, 规范化与排序.

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
from functools import total_ordering
from typing import Any

from sd_webui_all_in_one.package_analyzer.errors import InvalidVersion


VERSION_PATTERN = r"""
    v?
    (?:
        (?:(?P<epoch>[0-9]+)!)?                           # epoch
        (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
        (?P<pre>                                          # pre-release
            [-_\.]?
            (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
            [-_\.]?
            (?P<pre_n>[0-9]+)?
        )?
        (?P<post>                                         # post release
            (?:-(?P<post_n1>[0-9]+))
            |
            (?:
                [-_\.]?
                (?P<post_l>post|rev|r)
                [-_\.]?
                (?P<post_n2>[0-9]+)?
            )
        )?
        (?P<dev>                                          # dev release
            [-_\.]?
            (?P<dev_l>dev)
            [-_\.]?
            (?P<dev_n>[0-9]+)?
        )?
    )
    (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
"""
"""解析版本号的正则表达式 (需配合 ``re.VERBOSE | re.IGNORECASE`` 使用)"""

_VERSION_REGEX = re.compile(r"^\s*" + VERSION_PATTERN + r"\s*$", re.VERBOSE | re.IGNORECASE)

_PRE_RELEASE_NORMALIZATION: dict[str, str] = {
    "alpha": "a",
    "beta": "b",
    "c": "rc",
    "pre": "rc",
    "preview": "rc",
}

_LOCAL_SEPARATOR_REGEX = re.compile(r"[-_.]")


def _build_key(
    epoch: int,
    release: tuple[int, ...],
    pre: tuple[str, int] | None,
    post: int | None,
    dev: int | None,
    local: tuple[int | str, ...] | None,
) -> tuple[Any, ...]:
    """生成版本号的排序键

    排序规则 (同一 release 段内)::

        .devN < aN < bN < rcN < <无后缀> < .postN

    Args:
        epoch (int):
            版本纪元
        release (tuple[int, ...]):
            release 段
        pre (tuple[str, int] | None):
            预发布段
        post (int | None):
            后发布编号
        dev (int | None):
            开发版编号
        local (tuple[int | str, ...] | None):
            本地版本段

    Returns:
        tuple[Any, ...]: 可直接比较的排序键
    """
    # release 段尾部的 0 不影响排序 (1.0 == 1.0.0)
    trimmed = len(release)
    while trimmed > 1 and release[trimmed - 1] == 0:
        trimmed -= 1
    release_key = release[:trimmed]

    pre_key: tuple[Any, ...]
    if pre is None and post is None and dev is not None:
        # 1.0.dev1 排在 1.0a0 之前
        pre_key = (-1,)
    elif pre is None:
        pre_key = (1,)
    else:
        pre_key = (0, pre[0], pre[1])

    post_key = (-1, 0) if post is None else (0, post)
    dev_key = (1, 0) if dev is None else (0, dev)

    local_key: tuple[Any, ...]
    if local is None:
        local_key = (-1,)
    else:
        # 数字段大于字母段; 前缀相同时段数多的更大
        local_key = (0, tuple((1, part, "") if isinstance(part, int) else (0, 0, part) for part in local))

    return (epoch, release_key, pre_key, post_key, dev_key, local_key)


@total_ordering
@dataclass(frozen=True, eq=False)
class Version:
    """符合版本标识符规范的版本号

    使用示例:
        ```python
        Version.parse("1.0.0") == Version.parse("1.0")  # True
        Version.parse("2.3.0+cu118") > Version.parse("2.3.0")  # True
        str(Version.parse("1.0-ALPHA.1"))  # "1.0a1"
        ```

    Attributes:
        epoch (int):
            版本纪元, 默认为 0
        release (tuple[int, ...]):
            release 段, 如 ``(1, 2, 3)``
        pre (tuple[str, int] | None):
            规范化后的预发布段, 如 ``("rc", 1)``
        post (int | None):
            后发布编号
        dev (int | None):
            开发版编号
        local_segments (tuple[int | str, ...] | None):
            本地版本段, 如 ``("cu118",)``
    """

    epoch: int
    release: tuple[int, ...]
    pre: tuple[str, int] | None = None
    post: int | None = None
    dev: int | None = None
    local_segments: tuple[int | str, ...] | None = None
    _key: tuple[Any, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_key",
            _build_key(self.epoch, self.release, self.pre, self.post, self.dev, self.local_segments),
        )

    @classmethod
    def parse(
        cls,
        text: str,
    ) -> Version:
        """解析版本号字符串

        解析时自动完成规范化: 大小写, 前导 ``v``, 分隔符, 预发布标签别名
        (``alpha`` -> ``a`` 等), 隐式编号 (``1.0a`` -> ``1.0a0``), 隐式 post (``1.0-1`` -> ``1.0.post1``).

        Args:
            text (str):
                版本号字符串

        Returns:
            Version: 版本号对象

        Raises:
            InvalidVersion:
                版本号不符合规范时
        """
        match = _VERSION_REGEX.match(text)
        if match is None:
            raise InvalidVersion(f"不合法的版本号: {text!r}")

        groups = match.groupdict()

        pre: tuple[str, int] | None = None
        if groups["pre_l"]:
            label = groups["pre_l"].lower()
            pre = (_PRE_RELEASE_NORMALIZATION.get(label, label), int(groups["pre_n"] or 0))

        post: int | None = None
        if groups["post_n1"]:
            post = int(groups["post_n1"])
        elif groups["post_l"]:
            post = int(groups["post_n2"] or 0)

        dev: int | None = None
        if groups["dev_l"]:
            dev = int(groups["dev_n"] or 0)

        local: tuple[int | str, ...] | None = None
        if groups["local"]:
            local = tuple(int(part) if part.isdigit() else part.lower() for part in _LOCAL_SEPARATOR_REGEX.split(groups["local"]))

        return cls(
            epoch=int(groups["epoch"] or 0),
            release=tuple(int(part) for part in groups["release"].split(".")),
            pre=pre,
            post=post,
            dev=dev,
            local_segments=local,
        )

    @classmethod
    def try_parse(
        cls,
        text: str,
    ) -> Version | None:
        """解析版本号字符串, 失败时返回 ``None``

        Args:
            text (str):
                版本号字符串

        Returns:
            Version | None: 版本号对象, 无法解析时为 ``None``
        """
        try:
            return cls.parse(text)
        except InvalidVersion:
            return None

    @property
    def local(self) -> str | None:
        """本地版本标识 (``+`` 之后的部分), 不存在时为 ``None``

        Returns:
            str | None: 本地版本标识 (``+`` 之后的部分), 不存在时为 ``None``
        """
        if self.local_segments is None:
            return None
        return ".".join(str(part) for part in self.local_segments)

    @property
    def base_version(self) -> str:
        """仅含 epoch 与 release 段的版本号字符串

        Returns:
            str: 仅含 epoch 与 release 段的版本号字符串
        """
        release = ".".join(str(part) for part in self.release)
        return f"{self.epoch}!{release}" if self.epoch else release

    @property
    def public(self) -> str:
        """去除本地版本标识后的版本号字符串

        Returns:
            str: 去除本地版本标识后的版本号字符串
        """
        return str(self).split("+", 1)[0]

    @property
    def is_prerelease(self) -> bool:
        """是否为预发布版本 (含 pre-release 段或 dev 段)

        Returns:
            bool: 是否为预发布版本 (含 pre-release 段或 dev 段)
        """
        return self.pre is not None or self.dev is not None

    @property
    def is_postrelease(self) -> bool:
        """是否为后发布版本

        Returns:
            bool: 是否为后发布版本
        """
        return self.post is not None

    @property
    def is_devrelease(self) -> bool:
        """是否为开发版本

        Returns:
            bool: 是否为开发版本
        """
        return self.dev is not None

    def without_local(self) -> Version:
        """返回去除本地版本标识的版本号

        Returns:
            Version: 不含本地版本标识的版本号对象
        """
        if self.local_segments is None:
            return self
        return Version(self.epoch, self.release, self.pre, self.post, self.dev, None)

    def __str__(self) -> str:
        parts: list[str] = [self.base_version]
        if self.pre is not None:
            parts.append(f"{self.pre[0]}{self.pre[1]}")
        if self.post is not None:
            parts.append(f".post{self.post}")
        if self.dev is not None:
            parts.append(f".dev{self.dev}")
        if self.local_segments is not None:
            parts.append(f"+{self.local}")
        return "".join(parts)

    def __hash__(self) -> int:
        return hash(self._key)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key == other._key

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key < other._key
