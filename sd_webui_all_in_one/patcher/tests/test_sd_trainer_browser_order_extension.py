import asyncio
import importlib
import socket
import sys
import textwrap
import time
import webbrowser

import pytest

from sd_webui_all_in_one_hotpatcher import monkey_zoo, uninstall_import_hook
from sd_webui_all_in_one_hotpatcher_ext import sd_trainer_browser_order

MAIN_URL = "http://127.0.0.1:28000/lora/sd3.html"
MONITOR_URL = "http://127.0.0.1:6008/"

NEXT_APPLICATION = """
import os
import webbrowser

flags = []


def _resolve_browser():
    name = os.environ.get("MIKAZUKI_BROWSER", "")
    if name:
        return webbrowser.get(name)
    return webbrowser


def train_monitor_browser_url():
    return "http://127.0.0.1:6008/"


async def app_startup():
    browser = _resolve_browser()
    flags.append(browser is not webbrowser)
    for url in {urls!r}:
        browser.open(url)
"""

LEGACY_APPLICATION = """
import webbrowser


async def app_startup():
    webbrowser.open("http://127.0.0.1:28000")
"""


@pytest.fixture(autouse=True)
def clean_import_state(monkeypatch):
    uninstall_import_hook()
    monkey_zoo.clear()
    _clear_mikazuki_modules()
    before_path = list(sys.path)
    monkeypatch.setenv("MIKAZUKI_PORT", "28000")
    monkeypatch.delenv("MIKAZUKI_BROWSER", raising=False)
    yield
    uninstall_import_hook()
    monkey_zoo.clear()
    sys.path[:] = before_path
    _clear_mikazuki_modules()


@pytest.fixture
def opened(monkeypatch):
    urls = []
    monkeypatch.setattr(webbrowser, "open", lambda url, *args, **kwargs: urls.append(url) or True)
    return urls


@pytest.fixture
def sync_replay(monkeypatch):
    """让回放在当前线程同步执行, 并记录等待和延迟调用。"""

    events = []
    monkeypatch.setattr(
        sd_trainer_browser_order,
        "_wait_for_tcp_port",
        lambda host, port, timeout, interval=0.2: events.append(("wait", host, port)) or True,
    )
    monkeypatch.setattr(sd_trainer_browser_order.time, "sleep", lambda seconds: events.append(("sleep", seconds)))
    monkeypatch.setattr(
        sd_trainer_browser_order,
        "_start_replay",
        lambda requests: sd_trainer_browser_order.replay_browser_requests(
            requests,
            monitor_delay=sd_trainer_browser_order._monitor_delay,
        ),
    )
    return events


def test_patch_opens_main_webui_before_monitor(monkeypatch, tmp_path, opened, sync_replay):
    _create_fake_application(monkeypatch, tmp_path, NEXT_APPLICATION.format(urls=[MONITOR_URL, MAIN_URL]))

    sd_trainer_browser_order.patch_sd_trainer_browser_order(monitor_delay=2)
    module = importlib.import_module(sd_trainer_browser_order.TARGET_MODULE)
    asyncio.run(module.app_startup())

    assert opened == [MAIN_URL, MONITOR_URL]
    assert sync_replay == [("wait", "127.0.0.1", 28000), ("sleep", 2.0)]
    assert module.flags == [False]
    assert module.webbrowser is webbrowser


def test_patch_defers_opening_until_app_startup_returns(monkeypatch, tmp_path, opened):
    captured = []
    monkeypatch.setattr(sd_trainer_browser_order, "_start_replay", captured.append)
    _create_fake_application(monkeypatch, tmp_path, NEXT_APPLICATION.format(urls=[MAIN_URL, MONITOR_URL]))

    sd_trainer_browser_order.patch_sd_trainer_browser_order()
    module = importlib.import_module(sd_trainer_browser_order.TARGET_MODULE)
    asyncio.run(module.app_startup())

    assert opened == []
    assert [request.url for request in captured[0]] == [MAIN_URL, MONITOR_URL]


def test_patch_waits_for_main_port_before_opening(monkeypatch, tmp_path, opened):
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    port = server.getsockname()[1]
    main_url = f"http://127.0.0.1:{port}/"
    monkeypatch.setenv("MIKAZUKI_PORT", str(port))
    threads = []
    start_replay = sd_trainer_browser_order._start_replay
    monkeypatch.setattr(sd_trainer_browser_order, "_start_replay", lambda requests: threads.append(start_replay(requests)))
    _create_fake_application(monkeypatch, tmp_path, NEXT_APPLICATION.format(urls=[main_url, MONITOR_URL]))

    try:
        sd_trainer_browser_order.patch_sd_trainer_browser_order(monitor_delay=0)
        module = importlib.import_module(sd_trainer_browser_order.TARGET_MODULE)
        asyncio.run(module.app_startup())
        time.sleep(0.5)
        assert opened == []

        server.listen()
        threads[0].join(timeout=10)
    finally:
        server.close()

    assert not threads[0].is_alive()
    assert opened == [main_url, MONITOR_URL]


def test_patch_orders_requests_from_browser_controller(monkeypatch, tmp_path, opened, sync_replay):
    controller_opened = []

    class FakeController:
        def open(self, url, *args, **kwargs):
            controller_opened.append(url)
            return True

    monkeypatch.setattr(webbrowser, "get", lambda using=None: FakeController())
    monkeypatch.setenv("MIKAZUKI_BROWSER", "chrome")
    _create_fake_application(monkeypatch, tmp_path, NEXT_APPLICATION.format(urls=[MONITOR_URL, MAIN_URL]))

    sd_trainer_browser_order.patch_sd_trainer_browser_order()
    module = importlib.import_module(sd_trainer_browser_order.TARGET_MODULE)
    asyncio.run(module.app_startup())

    assert controller_opened == [MAIN_URL, MONITOR_URL]
    assert opened == []
    assert module.flags == [True]


def test_patch_leaves_legacy_single_webui_untouched(monkeypatch, tmp_path, opened):
    monkeypatch.setattr(
        sd_trainer_browser_order,
        "_start_replay",
        lambda _requests: (_ for _ in ()).throw(AssertionError("legacy branch must not be deferred")),
    )
    _create_fake_application(monkeypatch, tmp_path, LEGACY_APPLICATION)

    sd_trainer_browser_order.patch_sd_trainer_browser_order()
    module = importlib.import_module(sd_trainer_browser_order.TARGET_MODULE)

    assert not hasattr(module.app_startup, sd_trainer_browser_order._WRAPPER_MARKER_ATTR)
    asyncio.run(module.app_startup())
    assert opened == ["http://127.0.0.1:28000"]


def test_patch_wraps_already_imported_application_once(monkeypatch, tmp_path, opened, sync_replay):
    _create_fake_application(monkeypatch, tmp_path, NEXT_APPLICATION.format(urls=[MONITOR_URL, MAIN_URL]))
    module = importlib.import_module(sd_trainer_browser_order.TARGET_MODULE)

    sd_trainer_browser_order.patch_sd_trainer_browser_order()
    wrapped = module.app_startup
    sd_trainer_browser_order.patch_sd_trainer_browser_order()

    assert module.app_startup is wrapped
    asyncio.run(module.app_startup())
    assert opened == [MAIN_URL, MONITOR_URL]


def test_replay_still_opens_remaining_urls_when_one_fails(monkeypatch, sync_replay):
    opened = []

    def failing_open(url):
        raise OSError("no browser")

    requests = [
        sd_trainer_browser_order.BrowserRequest(MONITOR_URL, lambda: opened.append),
        sd_trainer_browser_order.BrowserRequest(MAIN_URL, lambda: failing_open),
    ]

    sd_trainer_browser_order.replay_browser_requests(requests, monitor_delay=0)

    assert opened == [MONITOR_URL]


def test_order_keeps_recorded_order_without_main_port(monkeypatch):
    monkeypatch.delenv("MIKAZUKI_PORT")
    requests = [
        sd_trainer_browser_order.BrowserRequest(MONITOR_URL, lambda: print),
        sd_trainer_browser_order.BrowserRequest(MAIN_URL, lambda: print),
    ]

    assert sd_trainer_browser_order.order_browser_requests(requests) == requests


def test_patch_registration_is_deduplicated():
    sd_trainer_browser_order.patch_sd_trainer_browser_order()
    sd_trainer_browser_order.patch_sd_trainer_browser_order()

    monkey = monkey_zoo[sd_trainer_browser_order.TARGET_MODULE]
    assert monkey is not None
    assert len(monkey.function_patches) == 1
    assert sd_trainer_browser_order.is_sd_trainer_browser_order_patch_registered() is True


def test_apply_from_config_ignores_disabled_config():
    sd_trainer_browser_order.apply_from_config({"enabled": False})

    assert sd_trainer_browser_order.TARGET_MODULE not in monkey_zoo
    assert sd_trainer_browser_order.is_sd_trainer_browser_order_patch_registered() is False


def test_apply_from_config_reads_monitor_delay():
    sd_trainer_browser_order.apply_from_config({"enabled": True, "monitor_delay": "3"})
    assert sd_trainer_browser_order._monitor_delay == 3.0

    sd_trainer_browser_order.apply_from_config({"enabled": True, "monitor_delay": "bad"})
    assert sd_trainer_browser_order._monitor_delay == sd_trainer_browser_order.DEFAULT_MONITOR_DELAY


def _create_fake_application(monkeypatch, tmp_path, source):
    package = tmp_path / "mikazuki" / "app"
    package.mkdir(parents=True)
    (tmp_path / "mikazuki" / "__init__.py").write_text("", encoding="utf-8")
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "application.py").write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()


def _clear_mikazuki_modules():
    for module_name in list(sys.modules):
        if module_name == "mikazuki" or module_name.startswith("mikazuki."):
            sys.modules.pop(module_name, None)
