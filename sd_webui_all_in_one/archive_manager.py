"""压缩 / 解压工具"""

import os
import zipfile
import tarfile
import lzma
import time
from pathlib import Path
from typing import Any, Iterable, Literal

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

ARCHIVE_COPY_CHUNK_SIZE = 1024 * 1024
"""压缩 / 解压进度更新分块大小"""


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


def _get_tqdm_class() -> Any:
    """获取进度条类"""
    try:
        from tqdm import tqdm
    except ImportError:
        from sd_webui_all_in_one.simple_tqdm import SimpleTqdm as tqdm

    return tqdm


def _progress_bar(
    total: int | None,
    desc: str,
    progress: bool,
    unit: str = "B",
    unit_scale: bool = True,
) -> Any:
    """创建进度条"""
    tqdm = _get_tqdm_class()
    return tqdm(
        total=total,
        desc=desc,
        unit=unit,
        unit_scale=unit_scale,
        unit_divisor=1024,
        disable=not progress,
    )


def _member_name(
    member: Any,
) -> str:
    """获取压缩包成员名称"""
    return str(getattr(member, "filename", getattr(member, "name", member)))


def _member_size(
    member: Any,
) -> int:
    """获取压缩包成员的未压缩大小"""
    size = getattr(member, "file_size", getattr(member, "size", getattr(member, "uncompressed", 0)))
    try:
        return int(size or 0)
    except (TypeError, ValueError):
        return 0


def _copy_stream_with_progress(
    src: Any,
    dst: Any,
    progress_bar: Any,
) -> None:
    """分块复制流并更新进度条"""
    while True:
        chunk = src.read(ARCHIVE_COPY_CHUNK_SIZE)
        if not chunk:
            break
        dst.write(chunk)
        progress_bar.update(len(chunk))


class _ProgressReader:
    """读取文件时同步更新进度条"""

    def __init__(
        self,
        file_obj: Any,
        progress_bar: Any,
    ) -> None:
        self.file_obj = file_obj
        self.progress_bar = progress_bar

    def read(
        self,
        size: int = -1,
    ) -> bytes:
        chunk = self.file_obj.read(size)
        if chunk:
            self.progress_bar.update(len(chunk))
        return chunk

    def __getattr__(
        self,
        name: str,
    ) -> Any:
        return getattr(self.file_obj, name)


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
    progress: bool = True,
) -> None:
    """安全解压 zip 压缩包"""
    with zipfile.ZipFile(archive_path, "r") as zip_ref:
        members = zip_ref.infolist()
        for member in members:
            _check_archive_member_path(member.filename, extract_to)

        total_size = sum(member.file_size for member in members if not member.is_dir())
        with _progress_bar(total=total_size, desc=archive_path.name, progress=progress) as pbar:
            for member in members:
                target_path = extract_to / member.filename
                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                    _set_zip_member_attrs(member, target_path)
                    continue

                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zip_ref.open(member, "r") as source, target_path.open("wb") as target:
                    _copy_stream_with_progress(source, target, pbar)
                _set_zip_member_attrs(member, target_path)


def _set_zip_member_attrs(
    member: zipfile.ZipInfo,
    target_path: Path,
) -> None:
    """恢复 zip 成员时间和权限属性"""
    try:
        timestamp = time.mktime(
            (
                member.date_time[0],
                member.date_time[1],
                member.date_time[2],
                member.date_time[3],
                member.date_time[4],
                member.date_time[5],
                0,
                0,
                -1,
            )
        )
        os.utime(target_path, (timestamp, timestamp))
    except (OSError, OverflowError, ValueError):
        pass

    mode = (member.external_attr >> 16) & 0o777
    if mode:
        try:
            os.chmod(target_path, mode)
        except OSError:
            pass


def _extract_tar(
    archive_path: Path,
    extract_to: Path,
    mode: TarExtractMode,
    progress: bool = True,
) -> None:
    """安全解压 tar 压缩包"""
    with tarfile.open(archive_path, mode) as tar_ref:
        members = tar_ref.getmembers()
        for member in members:
            _check_tar_member(member, extract_to)

        _extract_tar_members(tar_ref, members, extract_to, archive_path.name, progress)


def _extract_tar_members(
    tar_ref: tarfile.TarFile,
    members: list[tarfile.TarInfo],
    extract_to: Path,
    desc: str,
    progress: bool = True,
) -> None:
    """按成员解压 tar 并用普通文件字节数更新进度"""
    total_size = sum(member.size for member in members if member.isfile())
    with _progress_bar(total=total_size, desc=desc, progress=progress) as pbar:
        for member in members:
            if not member.isfile():
                tar_ref.extract(member, path=extract_to)
                continue

            target_path = extract_to / member.name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            source = tar_ref.extractfile(member)
            if source is None:
                continue

            with source, target_path.open("wb") as target:
                _copy_stream_with_progress(source, target, pbar)
            _set_tar_member_attrs(tar_ref, member, target_path)


def _set_tar_member_attrs(
    tar_ref: tarfile.TarFile,
    member: tarfile.TarInfo,
    target_path: Path,
) -> None:
    """恢复 tar 成员属性"""
    target = str(target_path)
    try:
        tar_ref.chown(member, target, numeric_owner=False)
        tar_ref.chmod(member, target)
        tar_ref.utime(member, target)
    except OSError:
        if tar_ref.errorlevel > 0:
            raise
    except tarfile.ExtractError:
        if tar_ref.errorlevel > 1:
            raise


def _extract_tar_lzma(
    archive_path: Path,
    extract_to: Path,
    progress: bool = True,
) -> None:
    """安全解压 lzma 压缩的 tar 包"""
    with lzma.open(archive_path, "rb") as f:
        with tarfile.open(fileobj=f) as tar_ref:
            members = tar_ref.getmembers()
            for member in members:
                _check_tar_member(member, extract_to)

            _extract_tar_members(tar_ref, members, extract_to, archive_path.name, progress)


def _extract_tar_zst(
    archive_path: Path,
    extract_to: Path,
    progress: bool = True,
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

                _extract_tar_members(tar_ref, members, extract_to, archive_path.name, progress)


def _get_archive_members_size(
    archive: Any,
) -> int | None:
    """获取第三方压缩包对象中的成员未压缩总大小"""
    try:
        return sum(_member_size(member) for member in archive.list())
    except (AttributeError, TypeError):
        return None


def _create_py7zr_extract_callback(
    py7zr_module: Any,
    progress_bar: Any,
) -> Any:
    """创建 py7zr 解压进度回调"""

    class _ExtractProgressCallback(py7zr_module.callbacks.ExtractCallback):
        def report_start_preparation(self) -> None:
            pass

        def report_start(
            self,
            processing_file_path: str,
            processing_bytes: str,
        ) -> None:
            pass

        def report_update(
            self,
            decompressed_bytes: str,
        ) -> None:
            progress_bar.update(int(decompressed_bytes))

        def report_end(
            self,
            processing_file_path: str,
            wrote_bytes: str,
        ) -> None:
            pass

        def report_warning(
            self,
            message: str,
        ) -> None:
            logger.warning(message)

        def report_postprocess(self) -> None:
            pass

    return _ExtractProgressCallback()


def _add_sources_to_zip(
    zip_ref: zipfile.ZipFile,
    sources: list[Path],
    progress: bool = True,
    desc: str = "archive",
) -> None:
    """将文件或目录列表添加到 zip 压缩包"""
    entries: list[tuple[Path, str]] = []
    for src in sources:
        if not src.is_dir():
            entries.append((src, src.name))
            continue

        for root, _, files in os.walk(src):
            root_p = Path(root)
            for f in files:
                fp = root_p / f
                entries.append((fp, str(fp.relative_to(src.parent))))

    total_size = sum(fp.stat().st_size for fp, _ in entries)
    with _progress_bar(total=total_size, desc=desc, progress=progress) as pbar:
        for fp, arcname in entries:
            zip_info = zipfile.ZipInfo.from_file(fp, arcname=arcname)
            zip_info.compress_type = zip_ref.compression
            with fp.open("rb") as source, zip_ref.open(zip_info, "w") as target:
                _copy_stream_with_progress(source, target, pbar)


def _collect_tar_entries(
    sources: list[Path],
) -> list[tuple[Path, str]]:
    """收集 tar 压缩包条目"""
    entries: list[tuple[Path, str]] = []
    for src in sources:
        entries.append((src, src.name))
        if not src.is_dir():
            continue

        for root, dirs, files in os.walk(src):
            root_p = Path(root)
            for dirname in dirs:
                path = root_p / dirname
                entries.append((path, str(path.relative_to(src.parent))))
            for filename in files:
                path = root_p / filename
                entries.append((path, str(path.relative_to(src.parent))))

    return entries


def _add_sources_to_tar(
    tar_ref: tarfile.TarFile,
    sources: list[Path],
    progress: bool = True,
    desc: str = "archive",
) -> None:
    """将文件或目录列表添加到 tar 压缩包"""
    entries = _collect_tar_entries(sources)
    total_size = sum(src.stat().st_size for src, _ in entries if src.is_file())
    with _progress_bar(total=total_size, desc=desc, progress=progress) as pbar:
        for src, arcname in entries:
            tar_info = tar_ref.gettarinfo(str(src), arcname=arcname)
            if src.is_file():
                with src.open("rb") as source:
                    tar_ref.addfile(tar_info, _ProgressReader(source, pbar))
            else:
                tar_ref.addfile(tar_info)


def _create_tar(
    sources: list[Path],
    archive_path: Path,
    mode: TarCreateMode,
    progress: bool = True,
) -> None:
    """创建 tar 压缩包"""
    with tarfile.open(archive_path, mode) as tar_ref:
        _add_sources_to_tar(tar_ref, sources, progress=progress, desc=archive_path.name)


def _create_tar_lzma(
    sources: list[Path],
    archive_path: Path,
    progress: bool = True,
) -> None:
    """创建 lzma 压缩的 tar 包"""
    with lzma.open(archive_path, "wb") as f:
        with tarfile.open(fileobj=f, mode="w") as tar_ref:
            _add_sources_to_tar(tar_ref, sources, progress=progress, desc=archive_path.name)


def _create_tar_zst(
    sources: list[Path],
    archive_path: Path,
    progress: bool = True,
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
                _add_sources_to_tar(tar_ref, sources, progress=progress, desc=archive_path.name)


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
    progress: bool = True,
) -> None:
    """解压支持的压缩包

    Args:
        archive_path (Path): 压缩包路径
        extract_to (Path): 解压到的路径
        progress (bool): 是否显示解压进度条
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
        _extract_zip(archive_path, extract_to, progress=progress)
        return

    if archive_format in TAR_EXTRACT_MODES:
        _extract_tar(archive_path, extract_to, TAR_EXTRACT_MODES[archive_format], progress=progress)
        return

    if archive_format in [".tar.lzma", ".tlz"]:
        _extract_tar_lzma(archive_path, extract_to, progress=progress)
        return

    if archive_format == ".tar.zst":
        _extract_tar_zst(archive_path, extract_to, progress=progress)
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
            with _progress_bar(total=_get_archive_members_size(archive), desc=archive_path.name, progress=progress) as pbar:
                archive.extractall(
                    path=extract_to,
                    callback=_create_py7zr_extract_callback(py7zr, pbar) if progress else None,
                )
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
            members = archive.infolist()
            for member in members:
                _check_archive_member_path(_member_name(member), extract_to)

            total_size = sum(_member_size(member) for member in members if not getattr(member, "isdir", lambda: False)())
            with _progress_bar(total=total_size, desc=archive_path.name, progress=progress) as pbar:
                for member in members:
                    target_path = extract_to / _member_name(member)
                    if getattr(member, "isdir", lambda: False)():
                        target_path.mkdir(parents=True, exist_ok=True)
                        continue

                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as source, target_path.open("wb") as target:
                        _copy_stream_with_progress(source, target, pbar)
        return

    raise ValueError(f"不支持的压缩格式: {archive_path}")


def create_archive(
    sources: Path | Iterable[Path],
    archive_path: Path,
    progress: bool = True,
) -> None:
    """根据扩展名创建压缩包

    Args:
        sources (Path | Iterable[Path]): 要打包的单个文件、目录或路径列表
        archive_path (Path): 压缩文件保存路径
        progress (bool): 是否显示压缩进度条
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
            _add_sources_to_zip(zf, sources, progress=progress, desc=archive_path.name)
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
            with _progress_bar(total=len(sources), desc=archive_path.name, progress=progress) as pbar:
                for src in sources:
                    if src.is_dir():
                        archive.writeall(str(src), arcname=src.name)
                    else:
                        archive.write(str(src), arcname=src.name)
                    pbar.update(1)
        return

    if archive_format in TAR_CREATE_MODES:
        _create_tar(sources, archive_path, TAR_CREATE_MODES[archive_format], progress=progress)
        return

    if archive_format in [".tar.lzma", ".tlz"]:
        _create_tar_lzma(sources, archive_path, progress=progress)
        return

    if archive_format == ".tar.zst":
        _create_tar_zst(sources, archive_path, progress=progress)
        return

    raise ValueError(f"不支持的压缩格式: {archive_path}")
