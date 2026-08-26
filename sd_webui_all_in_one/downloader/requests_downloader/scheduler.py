"""Requests 下载器的连接、镜像和分片调度。"""

import math
import threading
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any

from sd_webui_all_in_one.downloader.requests_downloader.http import _url_host_key
from sd_webui_all_in_one.downloader.requests_downloader.models import _Segment
from sd_webui_all_in_one.downloader.requests_downloader.state import _in_flight_bitfield_to_hex


class _ThreadLocalSessionPool:
    """为每个下载线程复用一个 requests Session"""

    def __init__(
        self,
        pool_size: int,
    ) -> None:
        self.pool_size = max(1, pool_size)
        self.local = threading.local()
        self.lock = threading.Lock()
        self.sessions: list[Any] = []

    def get(self) -> Any:
        session = getattr(self.local, "session", None)
        if session is not None:
            return session

        import requests

        session_factory = getattr(requests, "Session", None)
        if callable(session_factory):
            session = session_factory()
            self._configure_session(session)
            with self.lock:
                self.sessions.append(session)
        else:
            session = requests
        self.local.session = session
        return session

    def close_all(self) -> None:
        with self.lock:
            sessions = list(self.sessions)
            self.sessions.clear()
        for session in sessions:
            session.close()

    def _configure_session(
        self,
        session: Any,
    ) -> None:
        import requests

        if not hasattr(requests, "adapters") or not hasattr(session, "mount"):
            return
        for prefix in ("http://", "https://"):
            session.mount(prefix, requests.adapters.HTTPAdapter(pool_connections=self.pool_size, pool_maxsize=self.pool_size))


@dataclass
class _UriHealth:
    successes: int = 0
    failures: int = 0
    total_bytes: int = 0
    total_seconds: float = 0.0
    last_error: str | None = None
    last_success: float | None = None
    cooldown_until: float = 0.0

    @property
    def average_speed(self) -> float:
        return self.total_bytes / self.total_seconds if self.total_seconds > 0 else 0.0

    @property
    def success_rate(self) -> float:
        return self.successes / max(1, self.successes + self.failures)


class _UriPool:
    """aria2 FileEntry URI 池的简化实现"""

    def __init__(
        self,
        urls: list[str],
        max_connection_per_server: int,
        host_keys: dict[str, tuple[str, str, int | None]] | None = None,
    ) -> None:
        self.urls = list(urls)
        self.max_connection_per_server = max(1, max_connection_per_server)
        self.keys = [(host_keys or {}).get(url, _url_host_key(url)) for url in self.urls]
        self.key_by_url = dict(zip(self.urls, self.keys))
        self.in_flight: Counter[tuple[str, str, int | None]] = Counter()
        self.health = {url: _UriHealth() for url in self.urls}
        self.disabled_errors: dict[str, Exception] = {}
        self.next_index = 0
        self.condition = threading.Condition()

    @property
    def capacity(self) -> int:
        return max(1, len(set(self.keys)) * self.max_connection_per_server)

    def acquire(
        self,
        stop_event: threading.Event | None = None,
        excluded_urls: set[str] | None = None,
    ) -> str | None:
        excluded_urls = excluded_urls or set()
        with self.condition:
            while True:
                now = time.monotonic()
                candidates: list[int] = []
                for offset in range(len(self.urls)):
                    index = (self.next_index + offset) % len(self.urls)
                    url = self.urls[index]
                    if url in excluded_urls or url in self.disabled_errors:
                        continue
                    key = self.keys[index]
                    if self.in_flight[key] >= self.max_connection_per_server:
                        continue
                    if self.health[url].cooldown_until <= now:
                        candidates.append(index)

                if candidates:
                    unknown = [index for index in candidates if self.health[self.urls[index]].successes == 0 and self.health[self.urls[index]].failures == 0]
                    if unknown:
                        selected_index = unknown[0]
                    else:
                        selected_index = max(
                            candidates,
                            key=lambda index: (
                                self.health[self.urls[index]].success_rate,
                                self.health[self.urls[index]].average_speed,
                                self.health[self.urls[index]].last_success or 0.0,
                            ),
                        )
                    key = self.keys[selected_index]
                    self.in_flight[key] += 1
                    self.next_index = (selected_index + 1) % len(self.urls)
                    return self.urls[selected_index]

                if all(url in excluded_urls or url in self.disabled_errors for url in self.urls):
                    return None

                if stop_event is not None and stop_event.is_set():
                    return None
                cooldowns = [self.health[url].cooldown_until - now for url in self.urls if url not in excluded_urls and url not in self.disabled_errors and self.health[url].cooldown_until > now]
                self.condition.wait(timeout=min(cooldowns, default=0.1))

    def release(
        self,
        url: str | None,
    ) -> None:
        if url is None:
            return
        key = self.key_by_url[url]
        with self.condition:
            if self.in_flight[key] > 0:
                self.in_flight[key] -= 1
                if self.in_flight[key] <= 0:
                    del self.in_flight[key]
            self.condition.notify_all()

    def report_success(self, url: str, *, byte_count: int, elapsed: float) -> None:
        with self.condition:
            health = self.health[url]
            health.successes += 1
            health.total_bytes += max(0, byte_count)
            health.total_seconds += max(elapsed, 1e-9)
            health.last_success = time.monotonic()
            health.last_error = None
            health.cooldown_until = 0.0
            self.condition.notify_all()

    def report_failure(self, url: str, error: Exception, *, cooldown: float = 0.0, permanent: bool = False) -> None:
        with self.condition:
            health = self.health[url]
            health.failures += 1
            health.last_error = str(error)
            health.cooldown_until = max(health.cooldown_until, time.monotonic() + max(0.0, cooldown))
            if permanent:
                self.disabled_errors[url] = error
            self.condition.notify_all()


class _PieceStorage:
    """aria2 PieceStorage 的轻量 Python 实现"""

    def __init__(
        self,
        *,
        total_size: int,
        piece_length: int,
        completed: list[bool] | None = None,
        in_flight_lengths: list[int] | None = None,
    ) -> None:
        self.total_size = total_size
        self.piece_length = max(1, piece_length)
        self.piece_count = max(1, math.ceil(total_size / self.piece_length))
        self.lock = threading.Lock()
        raw_completed = completed if completed and len(completed) == self.piece_count else [False] * self.piece_count
        raw_in_flight_lengths = in_flight_lengths if in_flight_lengths and len(in_flight_lengths) == self.piece_count else [0] * self.piece_count
        self.completed: list[bool] = []
        self.in_flight_lengths: list[int] = []
        for index in range(self.piece_count):
            piece_size = self._piece_size_unlocked(index)
            is_complete = bool(raw_completed[index])
            in_flight_length = 0 if is_complete else max(0, min(int(raw_in_flight_lengths[index]), piece_size))
            if in_flight_length >= piece_size:
                is_complete = True
                in_flight_length = 0
            self.completed.append(is_complete)
            self.in_flight_lengths.append(0 if is_complete else in_flight_length)
        self.in_use = [False] * self.piece_count
        self.in_use_owner: list[int | None] = [None] * self.piece_count
        self.owner_idle: dict[int, bool] = {}

    def snapshot_completed(self) -> list[bool]:
        with self.lock:
            return list(self.completed)

    def snapshot_in_flight_pieces(self) -> list[dict[str, object]]:
        with self.lock:
            pieces: list[dict[str, object]] = []
            for index, completed_length in enumerate(self.in_flight_lengths):
                if completed_length <= 0 or self.completed[index]:
                    continue
                piece_size = self._piece_size_unlocked(index)
                pieces.append(
                    {
                        "index": index,
                        "length": piece_size,
                        "completed_length": completed_length,
                        "bitfield": _in_flight_bitfield_to_hex(
                            piece_size=piece_size,
                            completed_length=completed_length,
                        ),
                    }
                )
            return pieces

    def completed_piece_count(self) -> int:
        with self.lock:
            return sum(1 for done in self.completed if done)

    def completed_size(self) -> int:
        with self.lock:
            return sum(self._piece_size_unlocked(index) if done else self.in_flight_lengths[index] for index, done in enumerate(self.completed))

    def is_complete(self) -> bool:
        with self.lock:
            return all(self.completed)

    def check_out_segment(
        self,
        min_split_size: int,
        owner_id: int = 0,
    ) -> _Segment | None:
        with self.lock:
            index = self._select_sparse_missing_unused_piece_unlocked(min_split_size)
            if index is None:
                return None

            return self._check_out_piece_unlocked(index, owner_id)

    def check_out_piece(
        self,
        index: int,
        owner_id: int = 0,
    ) -> _Segment | None:
        with self.lock:
            if index < 0 or index >= self.piece_count or self.completed[index] or self.in_use[index]:
                return None
            return self._check_out_piece_unlocked(index, owner_id)

    def check_out_clean_piece(
        self,
        index: int,
        owner_id: int = 0,
    ) -> _Segment | None:
        with self.lock:
            if index < 0 or index >= self.piece_count or self.completed[index] or self.in_use[index] or self.in_flight_lengths[index] > 0:
                return None
            return self._check_out_piece_unlocked(index, owner_id)

    def check_out_clean_idle_piece(
        self,
        index: int,
        owner_id: int = 0,
    ) -> _Segment | None:
        with self.lock:
            if index < 0 or index >= self.piece_count or self.completed[index] or self.in_flight_lengths[index] > 0:
                return None
            current_owner = self.in_use_owner[index]
            if current_owner is None:
                return self._check_out_piece_unlocked(index, owner_id)
            if current_owner == owner_id:
                return self._segment_for_piece_unlocked(index, owner_id)
            if not self.owner_idle.get(current_owner, False):
                return None
            self.in_use_owner[index] = owner_id
            self.owner_idle[owner_id] = True
            return self._segment_for_piece_unlocked(index, owner_id)

    def mark_complete(
        self,
        segment: _Segment,
    ) -> int:
        with self.lock:
            newly_completed = 0
            for index in range(segment.start_piece, segment.end_piece + 1):
                if not self.completed[index]:
                    self.completed[index] = True
                    self.in_flight_lengths[index] = 0
                    newly_completed += 1
                if self.in_use_owner[index] == segment.owner_id:
                    self.in_use[index] = False
                    self.in_use_owner[index] = None
            return newly_completed

    def record_progress(
        self,
        segment: _Segment,
        next_offset: int,
    ) -> None:
        with self.lock:
            index = segment.start_piece
            if index < 0 or index >= self.piece_count or self.completed[index] or self.in_use_owner[index] != segment.owner_id:
                return
            self.owner_idle[segment.owner_id] = False
            piece_start = self._piece_start_unlocked(index)
            piece_size = self._piece_size_unlocked(index)
            in_flight_length = max(0, min(next_offset - piece_start, piece_size))
            if in_flight_length > self.in_flight_lengths[index]:
                self.in_flight_lengths[index] = in_flight_length

    def refresh_segment(
        self,
        segment: _Segment,
    ) -> _Segment | None:
        with self.lock:
            index = segment.start_piece
            if index < 0 or index >= self.piece_count or self.completed[index]:
                return None
            self.in_use[index] = True
            self.in_use_owner[index] = segment.owner_id
            self.owner_idle[segment.owner_id] = True
            return self._segment_for_piece_unlocked(index, segment.owner_id)

    def release(
        self,
        segment: _Segment,
    ) -> None:
        with self.lock:
            for index in range(segment.start_piece, segment.end_piece + 1):
                if self.in_use_owner[index] == segment.owner_id:
                    self.in_use[index] = False
                    self.in_use_owner[index] = None

    def owns_segment(
        self,
        segment: _Segment,
    ) -> bool:
        with self.lock:
            return all(0 <= index < self.piece_count and self.in_use_owner[index] == segment.owner_id for index in range(segment.start_piece, segment.end_piece + 1))

    def _piece_start_unlocked(
        self,
        index: int,
    ) -> int:
        return index * self.piece_length

    def _piece_end_unlocked(
        self,
        index: int,
    ) -> int:
        return min((index + 1) * self.piece_length, self.total_size) - 1

    def _piece_size_unlocked(
        self,
        index: int,
    ) -> int:
        return self._piece_end_unlocked(index) - self._piece_start_unlocked(index) + 1

    def _check_out_piece_unlocked(
        self,
        index: int,
        owner_id: int,
    ) -> _Segment:
        self.in_use[index] = True
        self.in_use_owner[index] = owner_id
        self.owner_idle[owner_id] = True
        return self._segment_for_piece_unlocked(index, owner_id)

    def _segment_for_piece_unlocked(
        self,
        index: int,
        owner_id: int,
    ) -> _Segment:
        piece_start = self._piece_start_unlocked(index)
        start = min(piece_start + self.in_flight_lengths[index], self._piece_end_unlocked(index))
        return _Segment(
            start_piece=index,
            end_piece=index,
            start=start,
            end=self._piece_end_unlocked(index),
            piece_start=piece_start,
            owner_id=owner_id,
        )

    def _select_sparse_missing_unused_piece_unlocked(
        self,
        min_split_size: int,
    ) -> int | None:
        ranges: list[tuple[int, int]] = []
        index = 0
        while index < self.piece_count:
            while index < self.piece_count and (self.completed[index] or self.in_use[index]):
                index += 1
            if index >= self.piece_count:
                break
            start = index
            while index < self.piece_count and not self.completed[index] and not self.in_use[index]:
                index += 1
            end = index
            if start > 0 and self.in_use[start - 1]:
                start = (start + end) // 2
            if start < end:
                ranges.append((start, end))

        if not ranges:
            return None

        max_range = ranges[0]
        for current in ranges[1:]:
            if self._range_is_better_unlocked(current, max_range):
                max_range = current

        start, end = max_range
        if start == 0:
            return 0

        previous_completed = self.completed[start - 1] and not self.in_use[start - 1]
        range_size = (end - start) * self.piece_length
        if previous_completed or range_size >= min_split_size:
            return start
        return None

    def _range_is_better_unlocked(
        self,
        current: tuple[int, int],
        best: tuple[int, int],
    ) -> bool:
        current_size = current[1] - current[0]
        best_size = best[1] - best[0]
        if current_size != best_size:
            return current_size > best_size
        if best[0] <= 0 or current[0] <= 0:
            return False

        best_previous_completed = self.completed[best[0] - 1] and not self.in_use[best[0] - 1]
        current_previous_completed = self.completed[current[0] - 1] and not self.in_use[current[0] - 1]
        return current_previous_completed and not best_previous_completed


class _SegmentManager:
    """aria2 SegmentMan 的轻量 Python 实现"""

    def __init__(
        self,
        piece_storage: _PieceStorage,
        min_split_size: int,
    ) -> None:
        self.piece_storage = piece_storage
        self.min_split_size = min_split_size

    def get_segment(
        self,
        owner_id: int = 0,
    ) -> _Segment | None:
        return self.piece_storage.check_out_segment(self.min_split_size, owner_id)

    def get_next_segment(
        self,
        segment: _Segment,
    ) -> _Segment | None:
        next_index = segment.end_piece + 1
        next_segment = self.piece_storage.check_out_clean_piece(next_index, segment.owner_id)
        if next_segment is not None:
            return next_segment
        return self.piece_storage.check_out_clean_idle_piece(next_index, segment.owner_id)

    def mark_complete(
        self,
        segment: _Segment,
    ) -> int:
        return self.piece_storage.mark_complete(segment)

    def record_progress(
        self,
        segment: _Segment,
        next_offset: int,
    ) -> None:
        self.piece_storage.record_progress(segment, next_offset)

    def refresh_segment(
        self,
        segment: _Segment,
    ) -> _Segment | None:
        return self.piece_storage.refresh_segment(segment)

    def release(
        self,
        segment: _Segment,
    ) -> None:
        self.piece_storage.release(segment)

    def owns_segment(
        self,
        segment: _Segment,
    ) -> bool:
        return self.piece_storage.owns_segment(segment)
