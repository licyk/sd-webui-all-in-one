"""重试装饰器测试"""

import pytest

from sd_webui_all_in_one import retry_decorator


def test_retryable_retries_none_and_unretryable(monkeypatch):
    monkeypatch.setattr(retry_decorator.time, "sleep", lambda _delay: None)
    attempts = {"value": 0}

    @retry_decorator.retryable(times=3, delay=0, catch_exceptions=ValueError, raise_exception=RuntimeError)
    def eventually_ok():
        attempts["value"] += 1
        if attempts["value"] == 1:
            raise ValueError("temporary")
        return "done"

    assert eventually_ok() == "done"
    assert attempts["value"] == 2

    none_attempts = {"value": 0}

    @retry_decorator.retryable(times=2, delay=0, retry_on_none=True)
    def always_none():
        none_attempts["value"] += 1
        return None

    with pytest.raises(RuntimeError):
        always_none()
    assert none_attempts["value"] == 2

    @retry_decorator.retryable(times=3, delay=0, catch_exceptions=ValueError)
    def fatal():
        raise TypeError("no retry")

    with pytest.raises(TypeError):
        fatal()
