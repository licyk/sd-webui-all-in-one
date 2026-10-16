"""多线程下载器测试"""

import pytest

from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.downloader.multi_thread import MultiThreadDownloader


def test_multi_thread_downloader_runs_args_kwargs_and_aggregates_errors():
    calls = []

    def download(name, suffix=""):
        calls.append((name, suffix))

    downloader = MultiThreadDownloader(
        download_func=download,
        download_args_list=[["a"], ["b"]],
        download_kwargs_list=[{"suffix": "1"}, {"suffix": "2"}],
    )

    downloader.start(num_threads=2, retry_count=1)

    assert sorted(calls) == [("a", "1"), ("b", "2")]

    def always_fails(name):
        raise ValueError(name)

    failing = MultiThreadDownloader(download_func=always_fails, download_args_list=[["bad"]])

    with pytest.raises(AggregateError) as exc:
        failing.start(num_threads=1, retry_count=2)

    assert len(exc.value.exceptions) == 2
