"""压缩包下载与解压测试"""

import pytest

from sd_webui_all_in_one.downloader import archive_downloader


def test_download_archive_and_unpack_uses_url_name_and_wraps_errors(monkeypatch, tmp_path):
    calls = []

    def fake_download_file(url, path, save_name):
        calls.append(("download", url, path, save_name))
        archive = path / save_name
        archive.write_text("data", encoding="utf-8")
        return archive

    def fake_extract_archive(archive_path, extract_to):
        calls.append(("extract", archive_path.name, extract_to))

    monkeypatch.setattr(archive_downloader, "download_file", fake_download_file)
    monkeypatch.setattr(archive_downloader, "extract_archive", fake_extract_archive)

    archive_downloader.download_archive_and_unpack("https://example.test/releases/pkg.zip?download=1", tmp_path / "out")

    assert calls[0][0] == "download"
    assert calls[0][3] == "pkg.zip"
    assert calls[1] == ("extract", "pkg.zip", tmp_path / "out")

    monkeypatch.setattr(archive_downloader, "extract_archive", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad archive")))

    with pytest.raises(RuntimeError) as exc:
        archive_downloader.download_archive_and_unpack("https://example.test/pkg.zip", tmp_path / "out")

    assert "bad archive" in str(exc.value)
