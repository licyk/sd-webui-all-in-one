"""Hotpatcher 运行时测试辅助工具"""

import json
import socket
import threading
import time

from sd_webui_all_in_one_hotpatcher.runtime.protocol import encode_message


class JsonlHost:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.messages = []
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._sock = socket.socket()
        self._sock.bind(("127.0.0.1", 0))
        self.host, self.port = self._sock.getsockname()
        self._sock.listen()

    def __enter__(self):
        self._thread.start()
        self._ready.wait(timeout=2)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop.set()
        try:
            with socket.create_connection((self.host, self.port), timeout=0.2):
                pass
        except Exception:
            pass
        self._thread.join(timeout=2)
        self._sock.close()

    def _run(self):
        self._ready.set()
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        with conn:
            file = conn.makefile("rb")
            for line in file:
                message = json.loads(line.decode("utf-8"))
                self.messages.append(message)
                if message.get("type") == "channel.open":
                    return
                message_id = message.get("id")
                if message_id is None:
                    continue
                response = self.responses.get(message.get("type"), {"ok": True, "payload": {}})
                response = dict(response)
                response["id"] = message_id
                conn.sendall(encode_message(response))

    def wait_for(self, predicate, timeout=2):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if any(predicate(message) for message in self.messages):
                return True
            time.sleep(0.01)
        return False


def locals_for_function(payload, function_name):
    frame = next(frame for frame in payload["frames"] if frame["function"] == function_name)
    return frame["locals"]
