"""Hotpatcher 运行时日志捕获测试"""

import logging
import os
import subprocess
import sys
import threading
import time

import pytest
from runtime_test_helpers import JsonlHost

from sd_webui_all_in_one_hotpatcher.runtime import RuntimeClient
from sd_webui_all_in_one_hotpatcher.runtime.errors import (
    uninstall_error_capture,
    uninstall_exception_reporter,
)
from sd_webui_all_in_one_hotpatcher.runtime.logs import install_log_capture, uninstall_log_capture


@pytest.fixture(autouse=True)
def clean_exception_reporter():
    uninstall_error_capture()
    uninstall_exception_reporter()
    uninstall_log_capture()
    yield
    uninstall_log_capture()
    uninstall_error_capture()
    uninstall_exception_reporter()


class ForwardingStream:
    def __init__(self, original):
        self.original = original

    def write(self, text):
        return self.original.write(text)

    def flush(self):
        return self.original.flush()

    def __getattr__(self, name):
        return getattr(self.original, name)


class BrokenFlushStream(ForwardingStream):
    def flush(self):
        raise OSError(1, "bad flush")


class BrokenWriteStream(ForwardingStream):
    def write(self, text):
        raise OSError(1, "bad write")


def test_log_capture_sends_logging_records_and_filters_defaults():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(client, streams=(), subprocess_mode="0")
            logging.getLogger("app.test").warning("hello %s", "world")
            logging.getLogger("sd_webui_all_in_one_hotpatcher.noise").warning("hidden")

            assert host.wait_for(lambda message: message.get("type") == "log.record")
            uninstall_log_capture()

        records = [message for message in host.messages if message.get("type") == "log.record"]
        assert len(records) == 1
        payload = records[0]["payload"]
        assert payload["logger"] == "app.test"
        assert payload["level"] == "WARNING"
        assert payload["message"] == "hello world"
        assert payload["process"]


def test_log_capture_tees_stdout_and_stderr(capsys):
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(client, capture_logging=False, streams=("stdout", "stderr"), subprocess_mode="0")
            print("stream hello")
            sys.stderr.write("stream bad\n")

            assert host.wait_for(lambda message: message.get("type") == "log.stream" and message["payload"]["stream"] == "stdout" and "stream hello" in message["payload"]["text"])
            assert host.wait_for(lambda message: message.get("type") == "log.stream" and message["payload"]["stream"] == "stderr" and "stream bad" in message["payload"]["text"])
            uninstall_log_capture()

    captured = capsys.readouterr()
    assert "stream hello" in captured.out
    assert "stream bad" in captured.err


def test_log_capture_wraps_existing_stdout_hook():
    original_stdout = sys.stdout
    preexisting_hook = ForwardingStream(original_stdout)
    sys.stdout = preexisting_hook

    try:
        with JsonlHost() as host:
            with RuntimeClient.connect(host.host, host.port) as client:
                install_log_capture(client, capture_logging=False, streams=("stdout",), subprocess_mode="0")
                print("cooperative stdout")

                assert host.wait_for(lambda message: message.get("type") == "log.stream" and message["payload"]["source"] == "stream" and "cooperative stdout" in message["payload"]["text"])
                uninstall_log_capture()
                assert sys.stdout is preexisting_hook
    finally:
        uninstall_log_capture()
        sys.stdout = original_stdout


def test_log_capture_stream_write_error_is_best_effort():
    original_stdout = sys.stdout
    sys.stdout = BrokenWriteStream(original_stdout)

    try:
        with JsonlHost() as host:
            with RuntimeClient.connect(host.host, host.port) as client:
                install_log_capture(client, capture_logging=False, streams=("stdout",), subprocess_mode="0")
                print("stream write survives")

                assert host.wait_for(lambda message: message.get("type") == "log.stream" and message["payload"]["source"] == "stream" and "stream write survives" in message["payload"]["text"])
                assert host.wait_for(
                    lambda message: (
                        message.get("type") == "log.hook_status"
                        and message["payload"]["component"] == "stream.stdout"
                        and message["payload"]["status"] == "error"
                        and "write failed" in message["payload"]["detail"]
                    )
                )
    finally:
        uninstall_log_capture()
        sys.stdout = original_stdout


def test_log_capture_stream_flush_error_is_best_effort():
    original_stdout = sys.stdout
    sys.stdout = BrokenFlushStream(original_stdout)

    try:
        with JsonlHost() as host:
            with RuntimeClient.connect(host.host, host.port) as client:
                install_log_capture(client, capture_logging=False, streams=("stdout",), subprocess_mode="0")
                sys.stdout.flush()

                assert host.wait_for(
                    lambda message: (
                        message.get("type") == "log.hook_status"
                        and message["payload"]["component"] == "stream.stdout"
                        and message["payload"]["status"] == "error"
                        and "flush failed" in message["payload"]["detail"]
                    )
                )
    finally:
        uninstall_log_capture()
        sys.stdout = original_stdout


def test_log_capture_warns_when_stdout_hook_is_replaced():
    original_stdout = sys.stdout

    try:
        with JsonlHost() as host:
            with RuntimeClient.connect(host.host, host.port) as client:
                install_log_capture(
                    client,
                    capture_logging=False,
                    streams=("stdout",),
                    subprocess_mode="0",
                    hook_policy="warn",
                    hook_check_interval=0,
                )
                sys.stdout = ForwardingStream(original_stdout)

                assert host.wait_for(lambda message: message.get("type") == "log.hook_status" and message["payload"]["component"] == "stream.stdout" and message["payload"]["status"] == "lost")
    finally:
        uninstall_log_capture()
        sys.stdout = original_stdout


def test_log_capture_reapplies_when_stdout_hook_is_replaced():
    original_stdout = sys.stdout

    try:
        with JsonlHost() as host:
            with RuntimeClient.connect(host.host, host.port) as client:
                install_log_capture(
                    client,
                    capture_logging=False,
                    streams=("stdout",),
                    subprocess_mode="0",
                    hook_policy="reapply",
                    hook_check_interval=0,
                )
                sys.stdout = ForwardingStream(original_stdout)

                assert host.wait_for(lambda message: message.get("type") == "log.hook_status" and message["payload"]["component"] == "stream.stdout" and message["payload"]["status"] == "reapplied")
                print("after stdout reapply")
                assert host.wait_for(lambda message: message.get("type") == "log.stream" and message["payload"]["source"] == "stream" and "after stdout reapply" in message["payload"]["text"])
    finally:
        uninstall_log_capture()
        sys.stdout = original_stdout


def test_log_capture_safe_subprocess_captures_explicit_pipe():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(client, capture_logging=False, streams=(), subprocess_mode="safe")
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import sys; print('safe out'); print('safe err', file=sys.stderr)",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            assert result.stdout.strip() == "safe out"
            assert result.stderr.strip() == "safe err"
            assert host.wait_for(
                lambda message: (
                    message.get("type") == "log.stream" and message["payload"]["source"] == "subprocess" and message["payload"]["stream"] == "stdout" and "safe out" in message["payload"]["text"]
                )
            )
            assert host.wait_for(
                lambda message: (
                    message.get("type") == "log.stream" and message["payload"]["source"] == "subprocess" and message["payload"]["stream"] == "stderr" and "safe err" in message["payload"]["text"]
                )
            )
            uninstall_log_capture()


def test_log_capture_safe_subprocess_does_not_force_inherited_output():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(client, capture_logging=False, streams=(), subprocess_mode="safe")
            subprocess.run(
                [sys.executable, "-c", "print('safe inherit')"],
                check=True,
            )
            assert not host.wait_for(
                lambda message: message.get("type") == "log.stream" and message["payload"]["source"] == "subprocess" and "safe inherit" in message["payload"]["text"],
                timeout=0.3,
            )
            uninstall_log_capture()


def test_log_capture_force_subprocess_captures_and_writes_back(capsys):
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(client, capture_logging=False, streams=(), subprocess_mode="force")
            subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import sys; print('force out'); print('force err', file=sys.stderr)",
                ],
                text=True,
                check=True,
            )

            assert host.wait_for(
                lambda message: (
                    message.get("type") == "log.stream" and message["payload"]["source"] == "subprocess" and message["payload"]["stream"] == "stdout" and "force out" in message["payload"]["text"]
                )
            )
            assert host.wait_for(
                lambda message: (
                    message.get("type") == "log.stream" and message["payload"]["source"] == "subprocess" and message["payload"]["stream"] == "stderr" and "force err" in message["payload"]["text"]
                )
            )
            uninstall_log_capture()

    captured = capsys.readouterr()
    assert "force out" in captured.out
    assert "force err" in captured.err


def test_log_capture_subprocess_popen_remains_subclassable():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(client, capture_logging=False, streams=(), subprocess_mode="force")

            class DerivedPopen(subprocess.Popen):
                pass

            assert issubclass(DerivedPopen, subprocess.Popen)
            uninstall_log_capture()


def test_log_capture_wraps_preexisting_subprocess_popen_hook():
    original_popen = subprocess.Popen

    class ThirdPartyPopen(original_popen):
        pass

    subprocess.Popen = ThirdPartyPopen  # ty: ignore[invalid-assignment]
    try:
        with JsonlHost() as host:
            with RuntimeClient.connect(host.host, host.port) as client:
                install_log_capture(client, capture_logging=False, streams=(), subprocess_mode="safe")
                assert issubclass(subprocess.Popen, ThirdPartyPopen)

                result = subprocess.run(
                    [sys.executable, "-c", "print('third party popen')"],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                assert result.stdout.strip() == "third party popen"
                assert host.wait_for(lambda message: message.get("type") == "log.stream" and message["payload"]["source"] == "subprocess" and "third party popen" in message["payload"]["text"])
                uninstall_log_capture()
                assert subprocess.Popen is ThirdPartyPopen
    finally:
        uninstall_log_capture()
        subprocess.Popen = original_popen


def test_log_capture_warns_when_logging_handler_is_removed():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            capture = install_log_capture(
                client,
                streams=(),
                subprocess_mode="0",
                hook_policy="warn",
                hook_check_interval=0,
            )
            assert capture._root_handler is not None
            logging.getLogger().removeHandler(capture._root_handler)

            assert host.wait_for(lambda message: message.get("type") == "log.hook_status" and message["payload"]["component"] == "logging" and message["payload"]["status"] == "lost")
            uninstall_log_capture()


def test_log_capture_reapplies_removed_logging_handler():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            capture = install_log_capture(
                client,
                streams=(),
                subprocess_mode="0",
                hook_policy="reapply",
                hook_check_interval=0,
            )
            handler = capture._root_handler
            assert handler is not None
            logging.getLogger().removeHandler(handler)

            assert host.wait_for(lambda message: message.get("type") == "log.hook_status" and message["payload"]["component"] == "logging" and message["payload"]["status"] == "reapplied")
            assert handler in logging.getLogger().handlers

            logging.getLogger("app.logging.reapply").warning("logging after reapply")
            assert host.wait_for(lambda message: message.get("type") == "log.record" and message["payload"]["message"] == "logging after reapply")
            uninstall_log_capture()


def test_log_capture_fd_force_captures_os_write():
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            capture = install_log_capture(
                client,
                capture_logging=False,
                streams=("stdout",),
                subprocess_mode="0",
                fd_capture="force",
            )
            fd_capture = capture._fd_captures.get("stdout")
            if fd_capture is None or fd_capture.fd is None:
                pytest.skip("fd capture is not supported in this environment")

            os.write(fd_capture.fd, b"fd force hello\n")
            assert host.wait_for(lambda message: message.get("type") == "log.stream" and message["payload"]["source"] == "fd" and "fd force hello" in message["payload"]["text"])
            uninstall_log_capture()


def test_log_capture_bounded_and_raw_policy(capsys):
    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(
                client,
                capture_logging=False,
                streams=("stdout",),
                subprocess_mode="0",
                policy="bounded",
                max_chars=5,
            )
            print("abcdef")

            assert host.wait_for(lambda message: message.get("type") == "log.stream" and message["payload"]["text"] == "abcde" and message["payload"].get("truncated") is True)
            uninstall_log_capture()

    capsys.readouterr()

    with JsonlHost() as host:
        with RuntimeClient.connect(host.host, host.port) as client:
            install_log_capture(
                client,
                capture_logging=False,
                streams=("stdout",),
                subprocess_mode="0",
                policy="raw",
                max_chars=5,
            )
            print("abcdef")

            assert host.wait_for(lambda message: message.get("type") == "log.stream" and message["payload"]["text"] == "abcdef" and "truncated" not in message["payload"])
            uninstall_log_capture()


def test_log_capture_reports_dropped_messages_when_queue_full():
    class BlockingTransport:
        def __init__(self):
            self.events = []
            self.first_send = threading.Event()
            self.release = threading.Event()
            self._blocked = False

        def event(self, message_type, payload):
            self.events.append({"type": message_type, "payload": payload})
            if message_type == "log.stream" and not self._blocked:
                self._blocked = True
                self.first_send.set()
                self.release.wait(timeout=2)

    class BlockingClient:
        def __init__(self):
            self.transport = BlockingTransport()

    client = BlockingClient()
    capture = install_log_capture(
        client,  # ty: ignore[invalid-argument-type]
        capture_logging=False,
        streams=(),
        subprocess_mode="0",
        queue_size=1,
    )
    capture.submit("log.stream", {"text": "first"})
    assert client.transport.first_send.wait(timeout=2)
    capture.submit("log.stream", {"text": "second"})
    capture.submit("log.stream", {"text": "third"})
    client.transport.release.set()

    deadline = time.time() + 2
    while time.time() < deadline:
        if any(event["type"] == "log.dropped" for event in client.transport.events):
            break
        time.sleep(0.01)

    uninstall_log_capture()
    dropped = [event for event in client.transport.events if event["type"] == "log.dropped"]
    assert dropped
    assert dropped[0]["payload"]["count"] >= 1
