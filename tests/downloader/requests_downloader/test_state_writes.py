"""requests 下载器状态文件写入与进度刷新测试"""

import json
import sys
import types
from pathlib import Path

import pytest

from sd_webui_all_in_one.downloader import requests_downloader
from sd_webui_all_in_one.downloader.requests_downloader import models as requests_models
from sd_webui_all_in_one.downloader.requests_downloader import scheduler as requests_scheduler
from sd_webui_all_in_one.downloader.requests_downloader import state as requests_state
from sd_webui_all_in_one.downloader.requests_downloader import transfer as requests_transfer
from tests.downloader.helpers import FakeRangeResponse, FakeTqdm, range_response

pytestmark = pytest.mark.usefixtures("small_aria2_size_bounds")


def test_requests_downloader_skips_unchanged_json_state_writes(monkeypatch, tmp_path):
    state_file = tmp_path / "model.bin.tmp.state.json"
    temp_file = tmp_path / "model.bin.tmp"
    temp_file.write_bytes(b"\0" * 8)
    storage = requests_scheduler._PieceStorage(total_size=8, piece_length=4)
    options = requests_models._DownloadOptions(
        split=1,
        max_connection_per_server=1,
        min_split_size=4,
        piece_length=4,
        allow_piece_length_change=False,
        max_tries=1,
        retry_wait=0,
        continue_download=False,
        conditional_get=False,
        remote_time=True,
    )
    write_calls = []
    replace_calls = []
    original_write_text = Path.write_text
    original_replace = Path.replace

    def spy_write_text(self, *args, **kwargs):
        if self.name.endswith("__temp"):
            write_calls.append(self.name)
        return original_write_text(self, *args, **kwargs)

    def spy_replace(self, target):
        replace_calls.append((self.name, Path(target).name))
        return original_replace(self, target)

    monkeypatch.setattr(Path, "write_text", spy_write_text)
    monkeypatch.setattr(Path, "replace", spy_replace)

    requests_state._save_resume_state(
        state_file,
        urls=["https://example.test/model.bin"],
        remote_info=requests_models._RemoteFileInfo(total_size=8, supports_range=True),
        options=options,
        piece_storage=storage,
    )
    requests_state._save_resume_state(
        state_file,
        urls=["https://example.test/model.bin"],
        remote_info=requests_models._RemoteFileInfo(total_size=8, supports_range=True),
        options=options,
        piece_storage=storage,
    )

    assert write_calls == ["model.bin.tmp.state.json__temp"]
    assert replace_calls == [("model.bin.tmp.state.json__temp", "model.bin.tmp.state.json")]
    assert json.loads(state_file.read_text(encoding="utf-8"))["version"] == requests_models.STATE_VERSION

    requests_state._state_temp_path_for(state_file).write_text("stale", encoding="utf-8")
    requests_state._cleanup_resume_files(temp_file, state_file)
    assert not state_file.exists()
    assert not requests_state._state_temp_path_for(state_file).exists()


def test_requests_downloader_flushes_data_before_periodic_and_final_state(monkeypatch, tmp_path):
    payload = b"abcdefgh"
    events = []
    clock = iter([0.0, 11.0, 12.0, 13.0, 14.0, 15.0])
    original_save = requests_state._save_resume_state

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        _, response = range_response(payload, headers)
        return response

    def spy_flush(temp_file):
        events.append("data")

    def spy_save(*args, **kwargs):
        events.append(("state", kwargs["piece_storage"].is_complete()))
        return original_save(*args, **kwargs)

    monkeypatch.setattr(requests_models, "STREAM_CHUNK_SIZE", 4)
    monkeypatch.setattr(requests_transfer.time, "monotonic", lambda: next(clock, 15.0))
    monkeypatch.setattr(requests_state, "_flush_download_data", spy_flush)
    monkeypatch.setattr(requests_state, "_save_resume_state", spy_save)
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=FakeTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=False,
        split=1,
        min_split_size=8,
        piece_length=8,
    )

    assert result.read_bytes() == payload
    assert ("state", False) in events
    assert events[-2:] == ["data", ("state", True)]


def test_requests_downloader_batches_state_writes_and_updates_streaming_progress(monkeypatch, tmp_path):
    payload = b"abcdefghijklmnop"
    save_state_calls = []
    progress_bars = []

    class TrackingTqdm(FakeTqdm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            progress_bars.append(self)

    original_save_state = requests_state._save_resume_state

    def fake_save_state(*args, **kwargs):
        save_state_calls.append(kwargs["piece_storage"].snapshot_completed())
        return original_save_state(*args, **kwargs)

    def fake_head(url, allow_redirects=True, timeout=60, headers=None):
        return FakeRangeResponse(status_code=200, headers={"Content-Length": str(len(payload)), "Accept-Ranges": "bytes"})

    def fake_get(url, stream=True, timeout=60, headers=None):
        _, response = range_response(payload, headers)
        return response

    monkeypatch.setattr(requests_state, "_save_resume_state", fake_save_state)
    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(head=fake_head, get=fake_get))
    monkeypatch.setitem(sys.modules, "tqdm", types.SimpleNamespace(tqdm=TrackingTqdm))

    result = requests_downloader.download_file_from_url(
        "https://example.test/model.bin",
        save_path=tmp_path,
        progress=True,
        split=4,
        max_connection_per_server=1,
        min_split_size=1,
        piece_length=1,
        continue_download=True,
    )

    assert result.read_bytes() == payload
    assert 0 < len(save_state_calls) < len(payload)
    assert progress_bars[-1].n == len(payload)
