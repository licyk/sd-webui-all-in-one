"""Hotpatcher 旧版传输测试辅助工具"""

import socket


class ScriptedReader:
    def __init__(self, items=(), *, close_error=None):
        self.items = list(items)
        self.close_error = close_error
        self.close_calls = 0
        self.closed = False

    def readline(self):
        if not self.items:
            return b""
        item = self.items.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def close(self):
        self.close_calls += 1
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


class FakeSocket:
    def __init__(
        self,
        reader,
        *,
        timeout=5.0,
        fail_send_calls=(),
        send_errors=None,
        shutdown_error=None,
        close_error=None,
    ):
        self.reader = reader
        self.timeout = timeout
        self.timeout_history = []
        self.fail_send_calls = set(fail_send_calls)
        self.send_errors = dict(send_errors or {})
        self.shutdown_error = shutdown_error
        self.close_error = close_error
        self.send_attempts = []
        self.makefile_timeouts = []
        self.shutdown_calls = 0
        self.close_calls = 0
        self.closed = False
        self.send_timeouts = []

    def settimeout(self, value):
        self.timeout = value
        self.timeout_history.append(value)

    def gettimeout(self):
        return self.timeout

    def makefile(self, mode):
        assert mode == "rb"
        self.makefile_timeouts.append(self.timeout)
        return self.reader

    def sendall(self, data):
        self.send_attempts.append(data)
        self.send_timeouts.append(self.timeout)
        error = self.send_errors.get(len(self.send_attempts))
        if error is not None:
            raise error
        if len(self.send_attempts) in self.fail_send_calls:
            raise BrokenPipeError("scripted send failure")

    def shutdown(self, how):
        assert how == socket.SHUT_RDWR
        self.shutdown_calls += 1
        if self.shutdown_error is not None:
            raise self.shutdown_error

    def close(self):
        self.close_calls += 1
        self.closed = True
        if self.close_error is not None:
            raise self.close_error
