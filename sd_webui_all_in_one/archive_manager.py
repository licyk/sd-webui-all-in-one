"""压缩 / 解压工具"""

import os
import zipfile
import tarfile
import lzma
from pathlib import Path
from typing import Iterable, Literal

from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.optional_dependency import install_optional_dependency

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


SUPPORTED_ARCHIVE_FORMAT = [
    ".zip",
    ".7z",
    ".rar",
    ".tar",
    ".tar.lzma",
    ".tar.bz2",
    ".tar.gz",
    ".tar.xz",
    ".tar.zst",
    ".tgz",
    ".tbz2",
    ".txz",
    ".tlz",
]
"""支持的压缩包格式列表"""

SUPPORTED_EXTRACT_ARCHIVE_FORMAT = SUPPORTED_ARCHIVE_FORMAT
"""支持解压的压缩包格式列表"""

SUPPORTED_CREATE_ARCHIVE_FORMAT = [
    ".zip",
    ".7z",
    ".tar",
    ".tar.lzma",
    ".tar.bz2",
    ".tar.gz",
    ".tar.xz",
    ".tar.zst",
    ".tgz",
    ".tbz2",
    ".txz",
    ".tlz",
]
"""支持创建的压缩包格式列表"""

TarExtractMode = Literal["r", "r:gz", "r:bz2", "r:xz"]
TarCreateMode = Literal["w", "w:gz", "w:bz2", "w:xz"]

TAR_EXTRACT_MODES: dict[str, TarExtractMode] = {
    ".tar": "r",
    ".tar.gz": "r:gz",
    ".tgz": "r:gz",
    ".tar.bz2": "r:bz2",
    ".tbz2": "r:bz2",
    ".tar.xz": "r:xz",
    ".txz": "r:xz",
}
"""tarfile 支持的解压模式"""

TAR_CREATE_MODES: dict[str, TarCreateMode] = {
    ".tar": "w",
    ".tar.gz": "w:gz",
    ".tgz": "w:gz",
    ".tar.bz2": "w:bz2",
    ".tbz2": "w:bz2",
    ".tar.xz": "w:xz",
    ".txz": "w:xz",
}
"""tarfile 支持的压缩模式"""


def _get_archive_format(
    archive_path: Path,
    supported_formats: Iterable[str],
) -> str | None:
    """根据文件名获取压缩格式"""
    name = archive_path.name.lower()
    for suffix in sorted(supported_formats, key=lambda value: len(value), reverse=True):
        suffix = suffix.lower()
        if name.endswith(suffix):
            return suffix
    return None


def _is_path_in_directory(
    path: Path,
    directory: Path,
) -> bool:
    """检查路径是否位于指定目录中"""
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def _check_archive_member_path(
    member_name: str,
    extract_to: Path,
) -> None:
    """检查压缩包成员路径是否会逃逸解压目录"""
    member_path = Path(member_name)
    target_path = extract_to / member_path
    if member_path.is_absolute() or not _is_path_in_directory(target_path, extract_to):
        raise ValueError(f"压缩包包含不安全的路径: {member_name}")


def _check_tar_member(
    member: tarfile.TarInfo,
    extract_to: Path,
) -> None:
    """检查 tar 成员是否可安全解压"""
    _check_archive_member_path(member.name, extract_to)
    if member.isdev():
        raise ValueError(f"压缩包包含不安全的设备文件: {member.name}")
    if member.issym() or member.islnk():
        link_path = Path(member.linkname)
        base_path = extract_to if link_path.is_absolute() else extract_to / Path(member.name).parent
        target_path = link_path if link_path.is_absolute() else base_path / link_path
        if not _is_path_in_directory(target_path, extract_to):
            raise ValueError(f"压缩包包含不安全的链接: {member.name}")


def _extract_zip(
    archive_path: Path,
    extract_to: Path,
) -> None:
    """安全解压 zip 压缩包"""
    with zipfile.ZipFile(archive_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            _check_archive_member_path(member.filename, extract_to)
        zip_ref.extractall(extract_to)


def _extract_tar(
    archive_path: Path,
    extract_to: Path,
    mode: TarExtractMode,
) -> None:
    """安全解压 tar 压缩包"""
    with tarfile.open(archive_path, mode) as tar_ref:
        members = tar_ref.getmembers()
        for member in members:
            _check_tar_member(member, extract_to)
        tar_ref.extractall(extract_to, members=members)


def _extract_tar_lzma(
    archive_path: Path,
    extract_to: Path,
) -> None:
    """安全解压 lzma 压缩的 tar 包"""
    with lzma.open(archive_path, "rb") as f:
        with tarfile.open(fileobj=f) as tar_ref:
            members = tar_ref.getmembers()
            for member in members:
                _check_tar_member(member, extract_to)
            tar_ref.extractall(extract_to, members=members)


def _extract_tar_zst(
    archive_path: Path,
    extract_to: Path,
) -> None:
    """安全解压 zstd 压缩的 tar 包"""
    try:
        import zstandard as zstd
    except ImportError:
        try:
            install_optional_dependency("zstandard")
            import zstandard as zstd
        except (RuntimeError, ImportError) as e:
            logger.error("安装 zstandard 模块失败: %s", e)
            raise RuntimeError(f"安装 zstandard 模块失败: {e}") from e

    with open(archive_path, "rb") as fh:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(fh) as reader:
            with tarfile.open(fileobj=reader) as tar_ref:
                members = tar_ref.getmembers()
                for member in members:
                    _check_tar_member(member, extract_to)
                tar_ref.extractall(extract_to, members=members)


def _add_to_tar(
    tar_ref: tarfile.TarFile,
    src: Path,
    arcname: str | None = None,
) -> None:
    """将文件或目录添加到 tar 压缩包"""
    if arcname is None:
        arcname = src.name
    tar_ref.add(str(src), arcname=arcname)


def _add_sources_to_zip(
    zip_ref: zipfile.ZipFile,
    sources: list[Path],
) -> None:
    """将文件或目录列表添加到 zip 压缩包"""
    for src in sources:
        if src.is_dir():
            for root, _, files in os.walk(src):
                root_p = Path(root)
                for f in files:
                    fp = root_p / f
                    arcname = str(fp.relative_to(src.parent))
                    zip_ref.write(str(fp), arcname=arcname)
        else:
            zip_ref.write(str(src), arcname=src.name)


def _add_sources_to_tar(
    tar_ref: tarfile.TarFile,
    sources: list[Path],
) -> None:
    """将文件或目录列表添加到 tar 压缩包"""
    for src in sources:
        _add_to_tar(tar_ref, src)


def _create_tar(
    sources: list[Path],
    archive_path: Path,
    mode: TarCreateMode,
) -> None:
    """创建 tar 压缩包"""
    with tarfile.open(archive_path, mode) as tar_ref:
        _add_sources_to_tar(tar_ref, sources)


def _create_tar_lzma(
    sources: list[Path],
    archive_path: Path,
) -> None:
    """创建 lzma 压缩的 tar 包"""
    with lzma.open(archive_path, "wb") as f:
        with tarfile.open(fileobj=f, mode="w") as tar_ref:
            _add_sources_to_tar(tar_ref, sources)


def _create_tar_zst(
    sources: list[Path],
    archive_path: Path,
) -> None:
    """创建 zstd 压缩的 tar 包"""
    try:
        import zstandard as zstd
    except ImportError:
        try:
            install_optional_dependency("zstandard")
            import zstandard as zstd
        except (RuntimeError, ImportError) as e:
            logger.error("安装 zstandard 模块失败: %s", e)
            raise RuntimeError(f"安装 zstandard 模块失败: {e}") from e

    with open(archive_path, "wb") as fh:
        cctx = zstd.ZstdCompressor()
        with cctx.stream_writer(fh) as compressor:
            with tarfile.open(fileobj=compressor, mode="w") as tar_ref:
                _add_sources_to_tar(tar_ref, sources)


def is_supported_archive_format(
    archive_path: Path,
) -> bool:
    """查看压缩包是否支持解压或是否支持压缩成的格式

    Args:
        archive_path (Path): 压缩包路径
    Returns:
        bool: 支持结果
    """
    return _get_archive_format(archive_path, SUPPORTED_ARCHIVE_FORMAT) is not None


def extract_archive(
    archive_path: Path,
    extract_to: Path,
) -> None:
    """解压支持的压缩包

    Args:
        archive_path (Path): 压缩包路径
        extract_to (Path): 解压到的路径
    Raises:
        ValueError: 不支持解压时
        RuntimeError: 安装解压所需的可选依赖失败时
    """
    archive_format = _get_archive_format(archive_path, SUPPORTED_EXTRACT_ARCHIVE_FORMAT)
    if archive_format is None:
        raise ValueError(f"不支持的压缩格式: {archive_path}")

    extract_to.mkdir(parents=True, exist_ok=True)

    logger.info("将 '%s' 解压到 '%s' 中", archive_path, extract_to)

    if archive_format == ".zip":
        _extract_zip(archive_path, extract_to)
        return

    if archive_format in TAR_EXTRACT_MODES:
        _extract_tar(archive_path, extract_to, TAR_EXTRACT_MODES[archive_format])
        return

    if archive_format in [".tar.lzma", ".tlz"]:
        _extract_tar_lzma(archive_path, extract_to)
        return

    if archive_format == ".tar.zst":
        _extract_tar_zst(archive_path, extract_to)
        return

    if archive_format == ".7z":
        try:
            import py7zr
        except ImportError:
            try:
                install_optional_dependency("py7zr")
                import py7zr
            except (RuntimeError, ImportError) as e:
                logger.error("安装 py7zr 模块失败: %s", e)
                raise RuntimeError(f"安装 py7zr 模块失败: {e}") from e

        with py7zr.SevenZipFile(archive_path, mode="r") as archive:
            archive.extractall(path=extract_to)
        return

    if archive_format == ".rar":
        try:
            import rarfile
        except ImportError:
            try:
                install_optional_dependency("rarfile")
                import rarfile
            except (RuntimeError, ImportError) as e:
                logger.error("安装 rarfile 模块失败: %s", e)
                raise RuntimeError(f"安装 rarfile 模块失败: {e}") from e

        with rarfile.RarFile(archive_path, mode="r") as archive:
            archive.extractall(path=extract_to)
        return

    raise ValueError(f"不支持的压缩格式: {archive_path}")


def create_archive(
    sources: Path | Iterable[Path],
    archive_path: Path,
) -> None:
    """根据扩展名创建压缩包

    Args:
        sources (Path | Iterable[Path]): 要打包的单个文件、目录或路径列表
        archive_path (Path): 压缩文件保存路径
    Raises:
        ValueError: 不支持的压缩或不能写入的格式
        RuntimeError: 安装压缩所需的可选依赖失败时
    """
    archive_format = _get_archive_format(archive_path, SUPPORTED_CREATE_ARCHIVE_FORMAT)
    if archive_format is None:
        if _get_archive_format(archive_path, SUPPORTED_EXTRACT_ARCHIVE_FORMAT) == ".rar":
            raise ValueError("创建 .rar 压缩包不受支持")
        raise ValueError(f"不支持的压缩格式: {archive_path}")

    sources = [sources] if isinstance(sources, Path) else list(sources)
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("将 '%s' 压缩并保存到 '%s' 中", sources, archive_path)
    logger.debug("创建压缩包: sources=%s, count=%s, archive='%s', format='%s'", sources, len(sources), archive_path, archive_format)

    if archive_format == ".zip":
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            _add_sources_to_zip(zf, sources)
        return

    if archive_format == ".7z":
        try:
            import py7zr
        except ImportError:
            try:
                install_optional_dependency("py7zr")
                import py7zr
            except (RuntimeError, ImportError) as e:
                logger.error("安装 py7zr 模块失败: %s", e)
                raise RuntimeError(f"安装 py7zr 模块失败: {e}") from e

        with py7zr.SevenZipFile(archive_path, mode="w") as archive:
            for src in sources:
                if src.is_dir():
                    archive.writeall(str(src), arcname=src.name)
                else:
                    archive.write(str(src), arcname=src.name)
        return

    if archive_format in TAR_CREATE_MODES:
        _create_tar(sources, archive_path, TAR_CREATE_MODES[archive_format])
        return

    if archive_format in [".tar.lzma", ".tlz"]:
        _create_tar_lzma(sources, archive_path)
        return

    if archive_format == ".tar.zst":
        _create_tar_zst(sources, archive_path)
        return

    raise ValueError(f"不支持的压缩格式: {archive_path}")
