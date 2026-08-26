import base64
import gzip
import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from sd_webui_all_in_one.downloader import requests_downloader


PAYLOAD = (b"0123456789abcdef" * 8192) + b"end"


class _DownloadHandler(BaseHTTPRequestHandler):
    retry_count = 0
    retry_lock = threading.Lock()

    def log_message(self, _format, *_args):
        pass

    def _payload(self):
        return gzip.compress(PAYLOAD) if self.path == "/gzip" else PAYLOAD

    def do_HEAD(self):
        if self.path == "/missing":
            self.send_error(404)
            return
        payload = self._payload()
        self.send_response(200)
        self.send_header("Content-Length", str(len(payload)))
        if self.path in {"/range", "/retry"}:
            self.send_header("Accept-Ranges", "bytes")
        if self.path == "/gzip":
            self.send_header("Content-Encoding", "gzip")
        self.end_headers()

    def do_GET(self):
        if self.path == "/missing":
            self.send_error(404)
            return
        if self.path == "/retry":
            with self.retry_lock:
                type(self).retry_count += 1
                retry_count = type(self).retry_count
            if retry_count == 1:
                self.send_response(503)
                self.send_header("Retry-After", "0")
                self.end_headers()
                return

        payload = self._payload()
        range_header = self.headers.get("Range")
        supports_range = self.path in {"/range", "/range-without-header", "/retry"}
        if range_header and supports_range:
            start_text, end_text = range_header.removeprefix("bytes=").split("-", maxsplit=1)
            start = int(start_text)
            end = len(payload) - 1 if not end_text else int(end_text)
            body = payload[start : end + 1]
            self.send_response(206)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(payload)}")
        else:
            body = payload
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))

        if self.path == "/gzip":
            self.send_header("Content-Encoding", "gzip")
        if self.path == "/digest-get" and range_header is None:
            digest = base64.b64encode(hashlib.sha512(PAYLOAD).digest()).decode("ascii")
            self.send_header("Digest", f"SHA-512={digest}")
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def local_download_server(monkeypatch):
    monkeypatch.setattr(requests_downloader, "ARIA2_SIZE_OPTION_MIN", 1)
    _DownloadHandler.retry_count = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), _DownloadHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize("endpoint", ["range", "range-without-header", "no-range", "gzip", "digest-get"])
def test_requests_downloader_real_http_modes(local_download_server, tmp_path, endpoint):
    result = requests_downloader.download_file_from_url(
        f"{local_download_server}/{endpoint}",
        save_path=tmp_path,
        file_name=f"{endpoint}.bin",
        progress=False,
        split=4,
        max_connection_per_server=2,
        min_split_size=16 * 1024,
        piece_length=16 * 1024,
    )

    assert result.read_bytes() == PAYLOAD


def test_requests_downloader_real_http_retry_and_permanent_error(local_download_server, tmp_path):
    result = requests_downloader.download_file_from_url(
        f"{local_download_server}/retry",
        save_path=tmp_path,
        progress=False,
        split=1,
        min_split_size=16 * 1024,
        piece_length=16 * 1024,
        max_tries=2,
    )
    assert result.read_bytes() == PAYLOAD
    assert _DownloadHandler.retry_count >= 2

    with pytest.raises(requests_downloader.DownloadPermanentHttpError) as exc:
        requests_downloader.download_file_from_url(
            f"{local_download_server}/missing",
            save_path=tmp_path,
            progress=False,
            max_tries=5,
        )
    assert exc.value.status_code == 404
    assert exc.value.attempt == 1
