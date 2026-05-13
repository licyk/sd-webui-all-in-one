import sys
import types
from pathlib import Path

PATCHER_ROOT = Path(__file__).resolve().parents[1] / "sd_webui_all_in_one" / "patcher"
if str(PATCHER_ROOT) not in sys.path:
    sys.path.insert(0, str(PATCHER_ROOT))

from sd_webui_all_in_one_hotpatcher.runtime import audit
from sd_webui_all_in_one_hotpatcher.runtime import browser
from sd_webui_all_in_one_hotpatcher_ext import zluda


class FakeClient:
    def __init__(self):
        self.events = []

    def event(self, name, payload):
        self.events.append((name, payload))


def test_audit_json_safe_extracts_nested_code_strings_and_bytes():
    def outer():
        value = "outer-value"

        def inner():
            return "inner-value"

        return value, inner

    value = audit._json_safe({"code": outer.__code__, "payload": b"abc", "items": [None, True, object()]})

    assert value["payload"] == {"type": "bytes", "base64": "YWJj"}
    assert value["code"]["type"] == "code"
    assert value["code"]["name"] == "outer"
    assert {"inner-value", "outer-value"}.issubset(value["code"]["strings"])
    assert value["items"][:2] == [None, True]
    assert value["items"][2]["type"] == "object"


def test_install_audit_hook_filters_events_and_serializes_args(monkeypatch):
    hooks = []
    client = FakeClient()
    monkeypatch.setattr(audit.sys, "addaudithook", lambda hook: hooks.append(hook))

    audit.install_audit_hook(client, ["open"])
    hooks[0]("ignored", ("x",))
    hooks[0]("open", ("file.txt", b"data"))

    assert client.events == [
        (
            "audit.event",
            {
                "event": "open",
                "args": ["file.txt", {"type": "bytes", "base64": "ZGF0YQ=="}],
            },
        )
    ]


def test_patch_webbrowser_routes_open_to_runtime_client(monkeypatch):
    class FakeMonkeyZoo:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def patch_function(self, name, hook):
            self.name = name
            self.hook = hook

    fake_monkey = FakeMonkeyZoo()
    fake_webbrowser = types.SimpleNamespace(open=lambda url, *args, **kwargs: False)
    client = FakeClient()
    monkeypatch.setattr(browser, "install_import_hook", lambda: None)
    monkeypatch.setattr(browser, "monkey_zoo", lambda name: fake_monkey)
    monkeypatch.setitem(sys.modules, "webbrowser", fake_webbrowser)

    browser.patch_webbrowser(client)

    assert fake_monkey.name == "open"
    assert fake_webbrowser.open("https://example.test") is True
    assert client.events == [("browser.open", {"url": "https://example.test"})]


def test_zluda_apply_from_config_dispatches_enabled_options(monkeypatch):
    calls = []
    monkeypatch.setattr(zluda, "apply_zluda_compat", lambda: calls.append("compat"))
    monkeypatch.setattr(zluda, "apply_zluda_library", lambda path: calls.append(("library", path)))
    monkeypatch.setattr(zluda, "apply_torch_zluda_timer_hotfix", lambda: calls.append("timer"))

    zluda.apply_from_config(None)
    zluda.apply_from_config({})
    assert calls == []

    zluda.apply_from_config({"compat": True, "path": "C:/zluda", "torch_zluda_timer": True})

    assert calls == ["compat", ("library", "C:/zluda"), "timer"]
