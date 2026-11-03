"""已安装分发的信息读取

读取当前环境中已安装软件包的版本, 依赖声明以及安装来源 (``direct_url.json``),
并检测元数据已损坏 (缺少 ``METADATA`` 或其中没有 ``Version``) 的分发.

参考:
    - https://packaging.python.org/en/latest/specifications/recording-installed-packages/
    - https://packaging.python.org/en/latest/specifications/direct-url/
"""

from __future__ import annotations

import importlib.metadata
import json
import sysconfig
from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path
from typing import (
    Any,
    Callable,
)

from sd_webui_all_in_one.package_analyzer.names import (
    is_valid_name,
    normalize_name,
)
from sd_webui_all_in_one.package_analyzer.version import Version


DIST_INFO_SUFFIX = ".dist-info"
"""已安装分发元数据目录的后缀"""


def read_metadata_name_version(
    metadata_path: Path,
) -> tuple[str | None, str | None]:
    """只扫描元数据文件头部读取 ``Name`` 与 ``Version``

    比完整解析 ``METADATA`` 快得多, 适合需要遍历大量分发的场景.

    Args:
        metadata_path (Path):
            ``METADATA`` 或 ``PKG-INFO`` 文件路径

    Returns:
        tuple[str | None, str | None]: 软件包名与版本号, 未找到的字段为 ``None``

    Raises:
        OSError:
            文件不存在或无法读取时
    """
    name: str | None = None
    version: str | None = None
    with metadata_path.open(encoding="utf-8", errors="replace") as file:
        for line in file:
            if not line.strip():
                # 空行之后是正文, Name 和 Version 只会出现在头部
                break
            if line[0] in " \t":
                continue
            key, sep, value = line.partition(":")
            if sep == "":
                continue
            normalized_key = key.strip().lower()
            if normalized_key == "name":
                name = name or value.strip()
            elif normalized_key == "version":
                version = version or value.strip()
            if name and version:
                break
    return name or None, version or None


def _distribution_version(
    distribution: importlib.metadata.Distribution,
) -> str | None:
    """读取分发的版本号

    ``METADATA`` 缺失, 为空或没有 ``Version`` 字段时, ``Distribution.version`` 在
    Python 3.11 中返回 ``None``, 在更新的版本中可能抛出 ``KeyError``, 这里统一返回 ``None``.

    Args:
        distribution (importlib.metadata.Distribution):
            已安装的分发

    Returns:
        str | None: 版本号, 元数据损坏时为 ``None``
    """
    try:
        version = distribution.version
    except (KeyError, OSError, ValueError):
        return None
    return version if isinstance(version, str) and version.strip() else None


def find_distribution(
    name: str,
) -> importlib.metadata.Distribution | None:
    """按软件包名查找已安装的分发

    元数据已损坏 (读取不到版本号) 的分发会被跳过并继续查找, 避免残留的损坏
    ``.dist-info`` 目录遮蔽同名的正常分发.

    Args:
        name (str):
            软件包名 (任意写法)

    Returns:
        importlib.metadata.Distribution | None: 已安装的分发, 未安装或元数据均已损坏时为 ``None``
    """
    if not name.strip():
        # importlib.metadata 对空包名抛出 ValueError 而不是 PackageNotFoundError
        return None
    for candidate in dict.fromkeys((name, normalize_name(name))):
        for distribution in importlib.metadata.distributions(name=candidate):
            if _distribution_version(distribution) is not None:
                return distribution
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
    version = _distribution_version(distribution)
    if version is None:
        return None
    return InstalledDistribution(name=name, version=version, loader=lambda: distribution)


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
    return _distribution_version(distribution) if distribution is not None else None


@dataclass(frozen=True)
class BrokenDistribution:
    """元数据已损坏的已安装分发

    ``.dist-info`` 目录存在, 但 ``METADATA`` 缺失, 为空或没有 ``Version`` 字段.
    ``importlib.metadata`` 读到的版本号为 ``None``, 而 uv 根据目录名仍认为软件包已安装,
    因此无法通过普通的安装命令修复.

    Attributes:
        path (Path):
            ``.dist-info`` 目录路径
        name (str | None):
            从目录名解析出的软件包名, 无法解析时为 ``None``
        version (str | None):
            从目录名解析出的版本号, 无法解析时为 ``None``
        reason (str):
            判定为损坏的原因
    """

    path: Path
    name: str | None
    version: str | None
    reason: str

    @property
    def requirement(self) -> str | None:
        """用于重新安装该分发的依赖声明, 如 ``numpy==2.2.6``

        Returns:
            str | None: 依赖声明, 无法确定软件包名时为 ``None``
        """
        if self.name is None:
            return None
        return f"{self.name}=={self.version}" if self.version is not None else self.name


def _parse_dist_info_dirname(
    dirname: str,
) -> tuple[str | None, str | None]:
    """从 ``{name}-{version}.dist-info`` 形式的目录名解析软件包名与版本号

    Args:
        dirname (str):
            ``.dist-info`` 目录名

    Returns:
        tuple[str | None, str | None]: 软件包名与版本号, 无法解析的部分为 ``None``
    """
    stem = dirname[: -len(DIST_INFO_SUFFIX)] if dirname.endswith(DIST_INFO_SUFFIX) else dirname
    name, _, version = stem.partition("-")
    return (
        name if name and is_valid_name(name) else None,
        version if version and Version.try_parse(version) is not None else None,
    )


def _site_packages_paths() -> list[str]:
    """获取当前解释器安装软件包的目录 (``purelib`` 与 ``platlib``)

    Returns:
        list[str]: 去重后的目录列表
    """
    paths = sysconfig.get_paths()
    return list(dict.fromkeys(path for path in (paths.get("purelib"), paths.get("platlib")) if path))


def _metadata_problem(
    distribution: importlib.metadata.Distribution,
    dist_path: Path,
) -> str | None:
    """判断 ``.dist-info`` 分发的元数据是否损坏

    Args:
        distribution (importlib.metadata.Distribution):
            已安装的分发
        dist_path (Path):
            ``.dist-info`` 目录路径

    Returns:
        str | None: 损坏原因, 元数据正常时为 ``None``
    """
    metadata_path = dist_path / "METADATA"
    try:
        _, version = read_metadata_name_version(metadata_path)
    except OSError:
        version = None
    # 头部扫描读不到时再用标准解析确认, 与 find_distribution 的判定保持一致
    if version is not None or _distribution_version(distribution) is not None:
        return None
    if not metadata_path.is_file():
        return "缺少 METADATA 文件"
    return "METADATA 文件为空或缺少 Version 字段"


def find_broken_distributions(
    paths: list[str] | list[Path] | None = None,
) -> list[BrokenDistribution]:
    """查找元数据已损坏的 ``.dist-info`` 分发

    Args:
        paths (list[str] | list[Path] | None):
            要扫描的目录, 为 ``None`` 时扫描当前解释器的 site-packages 目录

    Returns:
        list[BrokenDistribution]: 元数据已损坏的分发, 按路径排序 (目录遍历顺序取决于文件系统)
    """
    search_paths = [str(path) for path in paths] if paths is not None else _site_packages_paths()
    broken: list[BrokenDistribution] = []
    for distribution in importlib.metadata.distributions(path=search_paths):
        dist_path = getattr(distribution, "_path", None)
        if not isinstance(dist_path, Path) or not dist_path.name.endswith(DIST_INFO_SUFFIX) or not dist_path.is_dir():
            continue
        reason = _metadata_problem(distribution, dist_path)
        if reason is None:
            continue
        name, version = _parse_dist_info_dirname(dist_path.name)
        broken.append(BrokenDistribution(path=dist_path, name=name, version=version, reason=reason))
    broken.sort(key=lambda item: str(item.path))
    return broken
