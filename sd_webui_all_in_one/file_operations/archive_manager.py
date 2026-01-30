"""压缩 / 解压工具"""

import os
import zipfile
import tarfile
import lzma
from pathlib import Path
from typing import Iterable

from ani2xcur.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
)
from ani2xcur.logger import get_logger

logger = get_logger(
    name="Archive Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


SUPPORTED_ARCHIVE_FORMAT = [
    ".zip",
    ".7z",
    ".rar",
    ".tar",
    ".tar.Z",
    ".tar.lz",
    ".tar.lzma",
    ".tar.bz2",
    ".tar.7z",
    ".tar.gz",
    ".tar.xz",
    ".tar.zst",
]
"""支持的压缩包格式列表"""


def is_supported_archive_format(
    archive_path: Path,
) -> bool:
    """查看压缩包是否支持解压或是否支持压缩成的格式

    Args:
        archive_path (Path): 压缩包路径
    Returns:
        bool: 支持结果
    """
    name = archive_path.name
    for f in SUPPORTED_ARCHIVE_FORMAT:
        if name.endswith(f):
            return True
    return False


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
    """
    import rarfile
    import py7zr
    import zstandard as zstd

    if not is_supported_archive_format(archive_path):
        raise ValueError(f"不支持的压缩格式: {archive_path}")

    name = archive_path.name.lower()
    extract_to.mkdir(parents=True, exist_ok=True)

    logger.info("将 '%s' 解压到 '%s' 中", archive_path, extract_to)

    if name.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)

    if name.endswith(".tar"):
        with tarfile.open(archive_path, "r") as tar_ref:
            tar_ref.extractall(extract_to)
        return

    if name.endswith(".tar.gz"):
        with tarfile.open(archive_path, "r:gz") as tar_ref:
            tar_ref.extractall(extract_to)
            return

    if name.endswith(".tar.bz2"):
        with tarfile.open(archive_path, "r:bz2") as tar_ref:
            tar_ref.extractall(extract_to)
        return

    if name.endswith(".tar.xz"):
        with tarfile.open(archive_path, "r:xz") as tar_ref:
            tar_ref.extractall(extract_to)
        return

    if name.endswith(".tar.lzma") or name.endswith(".tlz"):
        with lzma.open(archive_path, "rb") as f:
            with tarfile.open(fileobj=f) as tar_ref:
                tar_ref.extractall(extract_to)
        return

    if name.endswith(".tar.zst") or name.endswith(".tar..zst"):
        with open(archive_path, "rb") as fh:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(fh) as reader:
                with tarfile.open(fileobj=reader) as tar_ref:
                    tar_ref.extractall(extract_to)
        return

    if name.endswith(".7z"):
        with py7zr.SevenZipFile(archive_path, mode="r") as archive:
            archive.extractall(path=extract_to)
        return

    if name.endswith(".rar"):
        with rarfile.RarFile(archive_path, mode="r") as archive:
            archive.extractall(path=extract_to)
        return


def create_archive(
    sources: Iterable[Path],
    archive_path: Path,
) -> None:
    """根据扩展名创建压缩包

    Args:
        sources (Iterable[Path]): 要打包的文件或目录的列表
        archive_path (Path): 压缩文件保存路径
    Raises:
        ValueError: 不支持的压缩或不能写入的格式
    """
    import py7zr
    import zstandard as zstd

    def _add_to_tar(
        tar_ref: tarfile.TarFile,
        src: Path,
        arcname: str | None = None,
    ) -> None:
        if arcname is None:
            arcname = src.name
        tar_ref.add(str(src), arcname=arcname)

    if not is_supported_archive_format(archive_path):
        raise ValueError(f"不支持的压缩格式: {archive_path}")

    name = archive_path.name.lower()
    sources = list(sources)
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("将 '%s' 压缩并保存到 '%s' 中", sources, archive_path)

    # zip
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for src in sources:
                if src.is_dir():
                    for root, _, files in os.walk(src):
                        root_p = Path(root)
                        for f in files:
                            fp = root_p / f
                            arcname = str(fp.relative_to(src.parent))
                            zf.write(str(fp), arcname=arcname)
                else:
                    arcname = src.name
                    zf.write(str(src), arcname=arcname)
        return

    # 7z
    if name.endswith(".7z"):
        with py7zr.SevenZipFile(archive_path, mode="w") as archive:
            for src in sources:
                if src.is_dir():
                    archive.writeall(str(src), arcname=src.name)
                else:
                    archive.write(str(src), arcname=src.name)
        return

    # rar 写入不支持
    if name.endswith(".rar"):
        raise ValueError("创建 .rar 压缩包不受支持")

    # 直接由 tarfile 支持的压缩模式
    if name.endswith(".tar"):
        mode = "w"
    elif name.endswith(".tar.gz") or name.endswith(".tgz"):
        mode = "w:gz"
    elif name.endswith(".tar.bz2") or name.endswith(".tbz2"):
        mode = "w:bz2"
    elif name.endswith(".tar.xz") or name.endswith(".txz"):
        mode = "w:xz"
    else:
        mode = None

    if mode is not None:
        with tarfile.open(archive_path, mode) as tar_ref:
            for src in sources:
                _add_to_tar(tar_ref, src)
        return

    # .tar.lzma 直接用 lzma 包装 tar 的文件对象
    if name.endswith(".tar.lzma") or name.endswith(".tlz"):
        with lzma.open(archive_path, "wb") as f:
            with tarfile.open(fileobj=f, mode="w") as tar_ref:
                for src in sources:
                    _add_to_tar(tar_ref, src)
        return

    # .tar.zst 使用 zstandard 的流写入
    if name.endswith(".tar.zst") or name.endswith(".tar..zst"):
        with open(archive_path, "wb") as fh:
            cctx = zstd.ZstdCompressor()
            with cctx.stream_writer(fh) as compressor:
                with tarfile.open(fileobj=compressor, mode="w") as tar_ref:
                    for src in sources:
                        _add_to_tar(tar_ref, src)
        return
