"""哈希工具测试"""

import hashlib

from sd_webui_all_in_one.downloader.hash_utils import compare_sha256


def test_compare_sha256_strips_and_lowercases_prefix(tmp_path):
    file_path = tmp_path / "data.bin"
    file_path.write_bytes(b"abc")
    digest = hashlib.sha256(b"abc").hexdigest()

    assert compare_sha256(file_path, f"  {digest[:10].upper()}  ") is True
    assert compare_sha256(file_path, "0" * 10) is False
