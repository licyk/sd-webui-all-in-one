import re
import os
from pathlib import Path
from urllib.parse import urlparse
from typing import Iterable
from tempfile import TemporaryDirectory

import zipfile
import tarfile
import lzma
import requests
import rarfile
import py7zr
import zstandard as zstd
from tqdm import tqdm

PATTERN = r"^(?P<Name>[^-]+)-(?P<Version>[^-]+)\+(?P<BuildDate>\d{8})-(?P<Type>.+?)\.(?P<Ext>tar\..+)$"


def get_latest_python_standalone_list() -> list[tuple[str, str]]:
    res = requests.get(
        "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
    )
    release = res.json()
    assets = release["assets"]
    url_list = []
    for info in assets:
        name: str = info["name"]
        url = info["browser_download_url"]
        if not name.startswith("cpython"):
            continue
        url_list.append((name, url))

    return url_list


def find_python(
    origin_data: list[tuple[str, str]], ver_prefix: str, dtype: str
) -> tuple[str | None, str | None]:
    for full_name, url in origin_data:
        match = re.match(PATTERN, full_name)
        if not match:
            continue

        ver = match.group("Version")
        pkg_type = match.group("Type")
        if ver.startswith(ver_prefix) and pkg_type == dtype:
            return (full_name, url)

    return (None, None)


def download_file_from_url(
    url: str,
    save_path: Path | None = None,
    file_name: str | None = None,
    progress: bool | None = True,
    re_download: bool | None = False,
) -> Path:
    if save_path is None:
        save_path = Path.cwd()

    if not file_name:
        parts = urlparse(url)
        file_name = Path(parts.path).name

    cached_file = save_path.resolve() / file_name

    if re_download or not cached_file.exists():
        save_path.mkdir(parents=True, exist_ok=True)
        temp_file = save_path / f"{file_name}.tmp"
        print(f"下载 {file_name} 到 {cached_file} 中")
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))
        with tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            desc=file_name,
            disable=not progress,
        ) as progress_bar:
            with open(temp_file, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
                        progress_bar.update(len(chunk))

        temp_file.rename(cached_file)
        print(
            f"{file_name} 下载完成",
        )
    else:
        print(f"{file_name} 已存在于 {cached_file} 中")
    return cached_file


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


def is_supported_archive_format(
    archive_path: Path,
) -> bool:
    name = archive_path.name
    for f in SUPPORTED_ARCHIVE_FORMAT:
        if name.endswith(f):
            return True
    return False


def extract_archive(
    archive_path: Path,
    extract_to: Path,
) -> None:
    if not is_supported_archive_format(archive_path):
        raise ValueError(f"不支持的压缩格式: {archive_path}")

    name = archive_path.name.lower()
    extract_to.mkdir(parents=True, exist_ok=True)

    print(f"将 {archive_path} 解压到 {extract_to} 中")

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
    def _add_to_tar(
        tar_ref: tarfile.TarFile,
        src: Path,
    ) -> None:
        if src.is_dir():
            for item in src.iterdir():
                tar_ref.add(str(item), arcname=str(item.relative_to(src)))
        else:
            tar_ref.add(str(src), arcname=src.name)

    if not is_supported_archive_format(archive_path):
        raise ValueError(f"不支持的压缩格式: {archive_path}")

    name = archive_path.name.lower()
    sources = list(sources)
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"将 {sources} 压缩并保存到 {archive_path} 中")

    # zip
    if name.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for src in sources:
                if src.is_dir():
                    for root, _, files in os.walk(src):
                        root_p = Path(root)
                        for f in files:
                            fp = root_p / f
                            arcname = str(fp.relative_to(src))
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
                    archive.writeall(str(src), arcname="")
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


def convert_to_zip(
    data: list[tuple[str, str]], base_path: Path, system: str, arch: str
):
    for name, url in data:
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            file = download_file_from_url(url=url, save_path=tmp_dir, file_name=name)
            extract_path = file.parent / file.name.split(".tar")[0]
            save_path = (
                base_path
                / system
                / arch
                / f"{file.name.split('.tar')[0]}.zip"
            )
            extract_archive(file, extract_path)
            create_archive([extract_path], save_path)


def main() -> None:
    release_data = get_latest_python_standalone_list()
    root_path = Path(__file__).parent
    windows_aarch64_list = []
    windows_amd64_list = []
    linux_aarch64_list = []
    linux_amd64_list = []
    macos_aarch64_list = []
    macos_amd64_list = []
    for ver_prefix in ["3.10", "3.11", "3.12", "3.13", "3.14"]:
        info = find_python(
            release_data, ver_prefix, "aarch64-pc-windows-msvc-install_only"
        )
        if info[0]:
            windows_aarch64_list.append(info)

        info = find_python(
            release_data, ver_prefix, "x86_64-pc-windows-msvc-install_only"
        )
        if info[0]:
            windows_amd64_list.append(info)

        info = find_python(
            release_data, ver_prefix, "aarch64-unknown-linux-gnu-install_only"
        )
        if info[0]:
            linux_aarch64_list.append(info)

        info = find_python(
            release_data, ver_prefix, "x86_64-unknown-linux-gnu-install_only"
        )
        if info[0]:
            linux_amd64_list.append(info)

        info = find_python(
            release_data, ver_prefix, "aarch64-apple-darwin-install_only"
        )
        if info[0]:
            macos_aarch64_list.append(info)

        info = find_python(release_data, ver_prefix, "x86_64-apple-darwin-install_only")
        if info[0]:
            macos_amd64_list.append(info)

    convert_to_zip(windows_aarch64_list, root_path, "windows", "aarch64")
    convert_to_zip(windows_amd64_list, root_path, "windows", "amd64")
    convert_to_zip(linux_aarch64_list, root_path, "linux", "aarch64")
    convert_to_zip(linux_amd64_list, root_path, "linux", "amd64")
    convert_to_zip(macos_aarch64_list, root_path, "macos", "aarch64")
    convert_to_zip(macos_amd64_list, root_path, "macos", "amd64")


if __name__ == "__main__":
    main()
