"""已安装分发的信息读取

读取当前环境中已安装软件包的版本, 依赖声明以及安装来源 (``direct_url.json``).

参考:
    - https://packaging.python.org/en/latest/specifications/recording-installed-packages/
    - https://packaging.python.org/en/latest/specifications/direct-url/
"""

from __future__ import annotations

import importlib.metadata
import json
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Any,
    Callable,
)

from sd_webui_all_in_one.package_analyzer.names import normalize_name


def find_distribution(
    name: str,
) -> importlib.metadata.Distribution | None:
    """按软件包名查找已安装的分发

    Args:
        name (str):
            软件包名 (任意写法)

    Returns:
        importlib.metadata.Distribution | None: 已安装的分发, 未安装时为 ``None``
    """
    if not name.strip():
        # importlib.metadata 对空包名抛出 ValueError 而不是 PackageNotFoundError
        return None
    for candidate in dict.fromkeys((name, normalize_name(name))):
        try:
            return importlib.metadata.distribution(candidate)
        except importlib.metadata.PackageNotFoundError:
            continue
    return None


@dataclass
class InstalledDistribution:
    """已安装的分发

    ``direct_url`` 与 ``requires`` 在首次访问时才从分发元数据中读取.

    Attributes:
        name (str):
            软件包名
        version (str):
            已安装的版本号
        loader (Callable[[], importlib.metadata.Distribution | None] | None):
            用于延迟获取分发元数据的函数
    """

    name: str
    version: str
    loader: Callable[[], importlib.metadata.Distribution | None] | None = None
    _distribution: importlib.metadata.Distribution | None = field(default=None, init=False, repr=False)
    _loaded: bool = field(default=False, init=False, repr=False)

    def _load(self) -> importlib.metadata.Distribution | None:
        """获取分发元数据对象

        Returns:
            importlib.metadata.Distribution | None: 分发元数据对象, 无法获取时为 ``None``
        """
        if not self._loaded:
            self._loaded = True
            if self.loader is not None:
                self._distribution = self.loader()
        return self._distribution

    @property
    def direct_url(self) -> dict[str, Any] | None:
        """``direct_url.json`` 的内容. 软件包不是通过直接引用 (URL / 本地路径) 安装时为 ``None``

        Returns:
            dict[str, Any] | None: ``direct_url.json`` 的内容. 软件包不是通过直接引用 (URL / 本地路径) 安装时为 ``None``
        """
        distribution = self._load()
        if distribution is None:
            return None
        try:
            text = distribution.read_text("direct_url.json")
        except (OSError, UnicodeDecodeError):
            return None
        if not text:
            return None
        try:
            data = json.loads(text)
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    @property
    def requires(self) -> list[str]:
        """分发元数据中声明的依赖 (``Requires-Dist``)

        Returns:
            list[str]: 分发元数据中声明的依赖 (``Requires-Dist``)
        """
        distribution = self._load()
        if distribution is None:
            return []
        return list(distribution.requires or [])

    @property
    def editable(self) -> bool:
        """是否以可编辑模式安装

        Returns:
            bool: 是否以可编辑模式安装
        """
        direct_url = self.direct_url
        if direct_url is None:
            return False
        dir_info = direct_url.get("dir_info")
        return isinstance(dir_info, dict) and bool(dir_info.get("editable"))


def get_installed_distribution(
    name: str,
) -> InstalledDistribution | None:
    """获取已安装的分发信息

    Args:
        name (str):
            软件包名 (任意写法)

    Returns:
        InstalledDistribution | None: 已安装的分发信息, 未安装时为 ``None``
    """
    distribution = find_distribution(name)
    if distribution is None:
        return None
    return InstalledDistribution(name=name, version=distribution.version, loader=lambda: distribution)


def get_package_version_from_library(
    package_name: str,
) -> str | None:
    """获取已安装的 Python 软件包版本号

    软件包名按规范化后的名称匹配, ``Foo_Bar`` 与 ``foo-bar`` 视为同一个软件包.

    Args:
        package_name (str):
            Python 软件包名

    Returns:
        str | None: 如果获取到版本号则返回版本号字符串, 否则返回 ``None``
    """
    distribution = find_distribution(package_name)
    return distribution.version if distribution is not None else None
