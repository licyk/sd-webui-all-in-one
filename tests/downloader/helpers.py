"""下载器测试辅助工具"""

from sd_webui_all_in_one.downloader.requests_downloader import models as requests_models
from sd_webui_all_in_one.downloader.requests_downloader import state as requests_state


class FakeTqdm:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.n = kwargs.get("initial", 0)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def update(self, value):
        self.n += value

    def close(self):
        pass


class FakeRequestsResponse:
    def __init__(self, chunks, status_code=200):
        self._chunks = chunks
        self.status_code = status_code
        self.headers = {"content-length": str(sum(len(chunk) for chunk in chunks))}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("bad status")

    def iter_content(self, chunk_size=1024):
        yield from self._chunks


class FakeRangeResponse:
    def __init__(self, payload=b"", status_code=200, headers=None):
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"bad status: {self.status_code}")

    def iter_content(self, chunk_size=64 * 1024):
        for index in range(0, len(self.payload), chunk_size):
            yield self.payload[index : index + chunk_size]

    def close(self):
        pass


def response_range(headers, total_size):
    range_header = headers.get("Range") if headers else None
    if range_header is None:
        return range_header, 0, total_size - 1, 200
    start, end = range_header.removeprefix("bytes=").split("-", maxsplit=1)
    return range_header, int(start), total_size - 1 if end == "" else int(end), 206


def range_response(payload, headers):
    range_header, start, end, status_code = response_range(headers, len(payload))
    response_headers = {"Content-Length": str(end - start + 1)}
    if range_header is not None:
        response_headers["Content-Range"] = f"bytes {start}-{end}/{len(payload)}"
    return range_header, FakeRangeResponse(payload[start : end + 1], status_code=status_code, headers=response_headers)


def request_state(
    *,
    url,
    total_size,
    completed,
    in_flight_lengths=None,
    etag=None,
    last_modified=None,
    digest_sha256=None,
    piece_length=4,
):
    if in_flight_lengths is None:
        in_flight_lengths = [0] * len(completed)
    in_flight_pieces = []
    for index, completed_length in enumerate(in_flight_lengths):
        if completed_length <= 0:
            continue
        piece_size = min((index + 1) * piece_length, total_size) - index * piece_length
        in_flight_pieces.append(
            {
                "index": index,
                "length": piece_size,
                "completed_length": completed_length,
                "bitfield": requests_state._in_flight_bitfield_to_hex(
                    piece_size=piece_size,
                    completed_length=completed_length,
                ),
            }
        )
    state = {
        "version": requests_models.STATE_VERSION,
        "url": url,
        "total_size": total_size,
        "etag": etag,
        "last_modified": last_modified,
        "digest_sha256": digest_sha256,
        "piece_length": piece_length,
        "piece_count": len(completed),
        "completed_bitfield": requests_state._bitfield_to_hex(completed),
        "in_flight_pieces": in_flight_pieces,
    }
    return state
