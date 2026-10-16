"""package_analyzer 分发文件名规范测试

参考:
    - https://packaging.python.org/en/latest/specifications/binary-distribution-format/
"""

import pytest

from sd_webui_all_in_one.package_analyzer.errors import (
    InvalidSdistFilename,
    InvalidWheelFilename,
)
from sd_webui_all_in_one.package_analyzer.filenames import (
    SdistFilename,
    WheelFilename,
    WheelTag,
    is_archive_filename,
)
from sd_webui_all_in_one.package_analyzer.version import Version


# ============================================================================
# 分发文件名
# ============================================================================
class TestFilenames:
    def test_wheel_filename(self):
        wheel = WheelFilename.parse("typing_extensions-4.12.2-py3-none-any.whl")
        assert wheel.distribution == "typing_extensions"
        assert wheel.name == "typing-extensions"
        assert wheel.version == Version.parse("4.12.2")
        assert wheel.build is None
        assert wheel.tags == {WheelTag("py3", "none", "any")}

    def test_wheel_filename_with_build_tag_and_compressed_tags(self):
        wheel = WheelFilename.parse("torch-2.3.0+cu118-1local-cp311.cp312-cp311-manylinux_2_28_x86_64.manylinux2014_x86_64.whl")
        assert wheel.version == Version.parse("2.3.0+cu118")
        assert wheel.build == (1, "local")
        assert len(wheel.tags) == 4
        assert WheelTag("cp312", "cp311", "manylinux2014_x86_64") in wheel.tags

    @pytest.mark.parametrize(
        "filename",
        [
            "not_a_wheel.tar.gz",
            "pkg-1.0.whl",
            "pkg-1.0-py3-none.whl",
            "pkg-1.0-1-2-py3-none-any.whl",
            "pkg-notaversion-py3-none-any.whl",
            "pkg-1.0-build-py3-none-any.whl",
            "bad__name-1.0-py3-none-any.whl",
        ],
    )
    def test_invalid_wheel_filenames(self, filename):
        with pytest.raises(InvalidWheelFilename):
            WheelFilename.parse(filename)

    def test_sdist_filename(self):
        sdist = SdistFilename.parse("my_package-1.0.tar.gz")
        assert sdist.name == "my-package"
        assert sdist.version == Version.parse("1.0")
        assert SdistFilename.parse("old-0.1.zip").distribution == "old"

    @pytest.mark.parametrize("filename", ["pkg-1.0.whl", "pkg.tar.gz", "pkg-main.tar.gz", "-1.0.tar.gz"])
    def test_invalid_sdist_filenames(self, filename):
        with pytest.raises(InvalidSdistFilename):
            SdistFilename.parse(filename)

    def test_archive_detection(self):
        assert is_archive_filename("a-1.0-py3-none-any.whl") is True
        assert is_archive_filename("A-1.0.TAR.GZ") is True
        assert is_archive_filename("requirements.txt") is False
