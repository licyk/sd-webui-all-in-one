"""下载器测试共享夹具"""

import pytest

from sd_webui_all_in_one.downloader.requests_downloader import models as requests_models


@pytest.fixture
def small_aria2_size_bounds(monkeypatch):
    """放宽 Aria2 兼容的分片大小下限, 便于使用小文件测试分片逻辑"""
    monkeypatch.setattr(requests_models, "ARIA2_SIZE_OPTION_MIN", 1)
    monkeypatch.setattr(requests_models, "ARIA2_SIZE_OPTION_MAX", 1024 * 1024 * 1024)
