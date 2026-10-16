"""requests 下载器目标文件锁测试"""

import os
import subprocess
import sys
import threading
import time
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from sd_webui_all_in_one.downloader import requests_downloader
from sd_webui_all_in_one.downloader.requests_downloader import models as requests_models
from tests.downloader.helpers import FakeRangeResponse, FakeTqdm, range_response

pytestmark = pytest.mark.usefixtures("small_aria2_size_bounds")


def test_requests_downloader_serializes_same_target_and_reuses_result(monkeypatch, tmp_path):
    payload = b"abcdefghijkl"
    probe_barrier = threading.Barrier(2)
    get_calls = []

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        probe_barrier.wait(timeout=2)
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        get_calls.append(headers["Range"])
        _, response = range_response(payload, headers)
        return response

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    def download():
        return requests_downloader.download_file_from_url(
            "https://example.test/model.bin",
            save_path=tmp_path,
            progress=False,
            split=1,
            min_split_size=4,
            piece_length=4,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: download(), range(2)))

    assert results == [tmp_path / "model.bin", tmp_path / "model.bin"]
    assert get_calls == ["bytes=0-"]
    assert results[0].read_bytes() == payload
    assert not requests_models._lock_path_for(results[0]).exists()
    assert not requests_models._TARGET_PATH_LOCKS


def test_requests_downloader_target_lock_is_scoped_by_directory(tmp_path):
    first_entered = threading.Event()
    release_first = threading.Event()
    first_target = tmp_path / "first" / "model.bin"
    second_target = tmp_path / "second" / "model.bin"

    def hold_first_lock():
        with requests_models._target_download_lock(first_target):
            first_entered.set()
            release_first.wait(timeout=2)

    thread = threading.Thread(target=hold_first_lock)
    thread.start()
    assert first_entered.wait(timeout=2)
    with requests_models._target_download_lock(second_target):
        assert requests_models._lock_path_for(second_target).exists() is (os.name != "nt")
    assert not requests_models._lock_path_for(second_target).exists()
    release_first.set()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert not requests_models._lock_path_for(first_target).exists()


def test_requests_downloader_target_lock_is_removed_after_error(tmp_path):
    target = tmp_path / "model.bin"

    with pytest.raises(RuntimeError, match="download failed"):
        with requests_models._target_download_lock(target):
            assert requests_models._lock_path_for(target).exists() is (os.name != "nt")
            raise RuntimeError("download failed")

    assert not requests_models._lock_path_for(target).exists()
    assert not requests_models._TARGET_PATH_LOCKS


def test_requests_downloader_target_lock_waits_across_processes(tmp_path):
    target = tmp_path / "model.bin"
    ready = tmp_path / "child-ready"
    process_timeout = 30
    command = (
        "from pathlib import Path; import sys; "
        "from sd_webui_all_in_one.downloader.requests_downloader.models import _target_download_lock; "
        "Path(sys.argv[2]).touch(); "
        "\nwith _target_download_lock(Path(sys.argv[1])):\n print('acquired', flush=True)"
    )

    process = None
    try:
        with requests_models._target_download_lock(target):
            process = subprocess.Popen(
                [sys.executable, "-c", command, str(target), str(ready)],
                cwd=Path(__file__).parents[3],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # Wait for imports to finish before checking lock contention. Cold
            # starts on shared Windows runners can take several seconds.
            deadline = time.monotonic() + process_timeout
            while not ready.exists():
                if process.poll() is not None:
                    stdout, stderr = process.communicate(timeout=process_timeout)
                    pytest.fail(f"Lock subprocess exited before becoming ready ({process.returncode}): {stdout}\n{stderr}")
                assert time.monotonic() < deadline, "Lock subprocess did not become ready within 30 seconds"
                time.sleep(0.05)

            # The child must remain blocked while the parent holds the lock.
            with pytest.raises(subprocess.TimeoutExpired):
                process.wait(timeout=0.5)

        stdout, stderr = process.communicate(timeout=process_timeout)
        assert process.returncode == 0, stderr
        assert stdout.strip() == "acquired"
        assert not requests_models._lock_path_for(target).exists()
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=process_timeout)
