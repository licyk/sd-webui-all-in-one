"""分发文件名解析

解析 Wheel 与源码包 (sdist) 的文件名, 提取软件包名, 版本号与兼容性标签.

参考:
    - https://packaging.python.org/en/latest/specifications/binary-distribution-format/#file-name-convention
    - https://packaging.python.org/en/latest/specifications/source-distribution-format/#source-distribution-file-name
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sd_webui_all_in_one.package_analyzer.errors import (
    InvalidSdistFilename,
    InvalidVersion,
    InvalidWheelFilename,
)
from sd_webui_all_in_one.package_analyzer.names import normalize_name
from sd_webui_all_in_one.package_analyzer.version import Version


_WHEEL_NAME_REGEX = re.compile(r"^[\w\d._]*$", re.UNICODE)
_BUILD_TAG_REGEX = re.compile(r"(\d+)(.*)")

SDIST_EXTENSIONS: tuple[str, ...] = (".tar.gz", ".zip")
"""规范定义的源码包扩展名 (``.zip`` 为历史遗留格式)"""

ARCHIVE_EXTENSIONS: tuple[str, ...] = (
    ".whl",
    ".tar.gz",
    ".tgz",
    ".tar",
    ".tar.bz2",
    ".tbz",
    ".tar.xz",
    ".txz",
    ".tlz",
    ".tar.lz",
    ".tar.lzma",
    ".zip",
)
"""pip 视为可安装归档文件的扩展名"""


def is_archive_filename(
    filename: str,
) -> bool:
    """判断文件名是否为可安装的归档文件 (Wheel 或源码包)

    Args:
        filename (str):
            文件名或路径

    Returns:
        bool: 文件名以归档扩展名结尾时返回 ``True``
    """
    return filename.lower().endswith(ARCHIVE_EXTENSIONS)


@dataclass(frozen=True)
class WheelTag:
    """Wheel 兼容性标签

    Attributes:
        interpreter (str):
            Python 标签, 如 ``cp311``
        abi (str):
            ABI 标签, 如 ``cp311``, ``abi3``, ``none``
        platform (str):
            平台标签, 如 ``manylinux_2_28_x86_64``, ``any``
    """

    interpreter: str
    abi: str
    platform: str

    def __str__(self) -> str:
        return f"{self.interpreter}-{self.abi}-{self.platform}"


@dataclass(frozen=True)
class WheelFilename:
    """解析后的 Wheel 文件名

    文件名格式::

        {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl

    Attributes:
        distribution (str):
            文件名中的软件包名 (原始写法)
        version (Version):
            版本号
        build (tuple[int, str] | None):
            构建标签 ``(数字, 后缀)``, 不存在时为 ``None``
        tags (frozenset[WheelTag]):
            展开压缩标签集后的兼容性标签集合
    """

    distribution: str
    version: Version
    build: tuple[int, str] | None
    tags: frozenset[WheelTag]

    @property
    def name(self) -> str:
        """规范化后的软件包名

        Returns:
            str: 规范化后的软件包名
        """
        return normalize_name(self.distribution)

    @classmethod
    def parse(
        cls,
        filename: str,
    ) -> WheelFilename:
        """解析 Wheel 文件名

        Args:
            filename (str):
                Wheel 文件名, 如 ``pydantic-1.10.15-py3-none-any.whl``

        Returns:
            WheelFilename: 解析结果

        Raises:
            InvalidWheelFilename:
                文件名不符合二进制分发格式规范时
        """
        if not filename.endswith(".whl"):
            raise InvalidWheelFilename(f"Wheel 文件名必须以 '.whl' 结尾: {filename!r}")

        stem = filename[:-4]
        dashes = stem.count("-")
        if dashes not in (4, 5):
            raise InvalidWheelFilename(f"Wheel 文件名的组成部分数量不正确: {filename!r}")

        parts = stem.split("-", dashes - 2)
        distribution = parts[0]
        if "__" in distribution or _WHEEL_NAME_REGEX.match(distribution) is None or not distribution:
            raise InvalidWheelFilename(f"Wheel 文件名中的软件包名不合法: {filename!r}")

        try:
            version = Version.parse(parts[1])
        except InvalidVersion as e:
            raise InvalidWheelFilename(f"Wheel 文件名中的版本号不合法: {filename!r}") from e

        build: tuple[int, str] | None = None
        if dashes == 5:
            build_match = _BUILD_TAG_REGEX.fullmatch(parts[2])
            if build_match is None:
                raise InvalidWheelFilename(f"Wheel 文件名中的构建标签必须以数字开头: {filename!r}")
            build = (int(build_match.group(1)), build_match.group(2))

        interpreters, abis, platforms = parts[-1].split("-")
        tags = frozenset(WheelTag(interpreter, abi, platform) for interpreter in interpreters.split(".") for abi in abis.split(".") for platform in platforms.split("."))

        return cls(distribution=distribution, version=version, build=build, tags=tags)


@dataclass(frozen=True)
class SdistFilename:
    """解析后的源码包文件名

    文件名格式::

        {name}-{version}.tar.gz

    Attributes:
        distribution (str):
            文件名中的软件包名 (原始写法)
        version (Version):
            版本号
    """

    distribution: str
    version: Version

    @property
    def name(self) -> str:
        """规范化后的软件包名

        Returns:
            str: 规范化后的软件包名
        """
        return normalize_name(self.distribution)

    @classmethod
    def parse(
        cls,
        filename: str,
    ) -> SdistFilename:
        """解析源码包文件名

        Args:
            filename (str):
                源码包文件名, 如 ``requests-2.31.0.tar.gz``

        Returns:
            SdistFilename: 解析结果

        Raises:
            InvalidSdistFilename:
                文件名不符合源码分发格式规范时
        """
        stem: str | None = None
        for extension in SDIST_EXTENSIONS:
            if filename.endswith(extension):
                stem = filename[: -len(extension)]
                break
        if stem is None:
            raise InvalidSdistFilename(f"源码包文件名必须以 '.tar.gz' 或 '.zip' 结尾: {filename!r}")

        distribution, separator, version_text = stem.rpartition("-")
        if not separator or not distribution:
            raise InvalidSdistFilename(f"源码包文件名必须为 '<name>-<version>' 形式: {filename!r}")

        try:
            version = Version.parse(version_text)
        except InvalidVersion as e:
            raise InvalidSdistFilename(f"源码包文件名中的版本号不合法: {filename!r}") from e

        return cls(distribution=distribution, version=version)
