"""压缩包管理测试"""

import builtins
import io
import sys
import tarfile
import types
import zipfile

import pytest

from sd_webui_all_in_one import archive_manager


def test_archive_manager_zip_tar_and_unsupported(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "rarfile", types.SimpleNamespace(RarFile=object))
    monkeypatch.setitem(sys.modules, "py7zr", types.SimpleNamespace(SevenZipFile=object))
    monkeypatch.setitem(sys.modules, "zstandard", types.SimpleNamespace(ZstdDecompressor=object))

    source = tmp_path / "source.txt"
    source.write_text("payload", encoding="utf-8")

    zip_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(source, arcname="source.txt")
    zip_out = tmp_path / "zip-out"
    archive_manager.extract_archive(zip_path, zip_out)
    assert (zip_out / "source.txt").read_text(encoding="utf-8") == "payload"

    tar_path = tmp_path / "sample.tar"
    with tarfile.open(tar_path, "w") as tf:
        tf.add(source, arcname="source.txt")
    tar_out = tmp_path / "tar-out"
    archive_manager.extract_archive(tar_path, tar_out)
    assert (tar_out / "source.txt").read_text(encoding="utf-8") == "payload"

    created_zip = tmp_path / "created.zip"
    archive_manager.create_archive([source], created_zip)
    assert archive_manager.is_supported_archive_format(created_zip) is True
    assert zipfile.is_zipfile(created_zip)

    with pytest.raises(ValueError):
        archive_manager.extract_archive(tmp_path / "bad.exe", tmp_path / "bad-out")


def test_archive_manager_progress_updates_byte_operations(monkeypatch, tmp_path):
    progress_bars = []

    class FakeTqdm:
        def __init__(self, total, desc, unit, disable, unit_scale=False, unit_divisor=1000):
            self.total = total
            self.desc = desc
            self.unit = unit
            self.disable = disable
            self.unit_scale = unit_scale
            self.unit_divisor = unit_divisor
            self.n = 0
            progress_bars.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def update(self, value):
            self.n += value

    monkeypatch.setattr(archive_manager, "_get_tqdm_class", lambda: FakeTqdm)

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "a.txt").write_text("a", encoding="utf-8")
    (source_dir / "b.txt").write_text("b", encoding="utf-8")

    archive_path = tmp_path / "created.zip"
    archive_manager.create_archive([source_dir], archive_path, progress=True)
    archive_manager.extract_archive(archive_path, tmp_path / "out", progress=True)

    tar_path = tmp_path / "created.tar"
    archive_manager.create_archive([source_dir], tar_path, progress=True)
    archive_manager.extract_archive(tar_path, tmp_path / "tar-out", progress=True)

    archive_manager.create_archive([source_dir / "a.txt"], tmp_path / "disabled.zip", progress=False)

    assert [(bar.total, bar.n, bar.unit, bar.disable) for bar in progress_bars] == [
        (2, 2, "B", False),
        (2, 2, "B", False),
        (2, 2, "B", False),
        (2, 2, "B", False),
        (1, 1, "B", True),
    ]


def test_archive_manager_format_detection_matches_supported_handlers(tmp_path):
    assert archive_manager.is_supported_archive_format(tmp_path / "sample.TGZ") is True
    assert archive_manager.is_supported_archive_format(tmp_path / "sample.tbz2") is True
    assert archive_manager.is_supported_archive_format(tmp_path / "sample.txz") is True
    assert archive_manager.is_supported_archive_format(tmp_path / "sample.tlz") is True
    assert archive_manager.is_supported_archive_format(tmp_path / "sample.tar.7z") is True

    assert archive_manager.is_supported_archive_format(tmp_path / "sample.tar.Z") is False
    assert archive_manager.is_supported_archive_format(tmp_path / "sample.tar.lz") is False


def test_archive_create_installs_optional_dependency_before_reimport(monkeypatch, tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("payload", encoding="utf-8")
    archive_path = tmp_path / "created.7z"
    installed = False
    install_calls = []
    import_calls = []
    write_calls = []

    class FakeSevenZipFile:
        def __init__(self, path, mode):
            self.path = path
            self.mode = mode

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def write(self, path, arcname):
            write_calls.append((path, arcname))

    fake_py7zr = types.SimpleNamespace(SevenZipFile=FakeSevenZipFile)
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name != "py7zr":
            return real_import(name, *args, **kwargs)
        import_calls.append(name)
        if name == "py7zr" and not installed:
            raise ImportError("py7zr missing")
        return fake_py7zr

    def fake_install_optional_dependency(package_name):
        nonlocal installed
        installed = True
        install_calls.append(package_name)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(archive_manager, "install_optional_dependency", fake_install_optional_dependency)

    archive_manager.create_archive([source], archive_path)

    assert import_calls == ["py7zr", "py7zr"]
    assert install_calls == ["py7zr"]
    assert write_calls == [(str(source), "source.txt")]


def test_archive_create_tar_variants_and_write_errors(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "py7zr", types.SimpleNamespace(SevenZipFile=object))
    monkeypatch.setitem(sys.modules, "zstandard", types.SimpleNamespace(ZstdCompressor=object))

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "a.txt").write_text("a", encoding="utf-8")
    (source_dir / "b.txt").write_text("b", encoding="utf-8")

    tar_gz = tmp_path / "created.tar.gz"
    archive_manager.create_archive([source_dir], tar_gz)
    with tarfile.open(tar_gz, "r:gz") as tf:
        assert sorted(tf.getnames()) == ["source", "source/a.txt", "source/b.txt"]

    tar_lzma = tmp_path / "created.tar.lzma"
    archive_manager.create_archive([source_dir / "a.txt"], tar_lzma)
    assert tar_lzma.exists()

    with pytest.raises(ValueError, match="rar"):
        archive_manager.create_archive([source_dir], tmp_path / "bad.rar")

    with pytest.raises(ValueError, match="unsupported|不支持"):
        archive_manager.create_archive([source_dir], tmp_path / "bad.bin")


def test_archive_extract_rejects_unsafe_member_paths(tmp_path):
    zip_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../outside.txt", "unsafe")

    with pytest.raises(ValueError, match="不安全"):
        archive_manager.extract_archive(zip_path, tmp_path / "zip-out")
    assert not (tmp_path / "outside.txt").exists()

    tar_path = tmp_path / "unsafe.tar"
    payload = b"unsafe"
    tar_info = tarfile.TarInfo("../outside.txt")
    tar_info.size = len(payload)
    with tarfile.open(tar_path, "w") as tf:
        tf.addfile(tar_info, io.BytesIO(payload))

    with pytest.raises(ValueError, match="不安全"):
        archive_manager.extract_archive(tar_path, tmp_path / "tar-out")
    assert not (tmp_path / "outside.txt").exists()
