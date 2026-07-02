import asyncio
import sys
import types
from types import SimpleNamespace

from sd_webui_all_in_one.launchers import invokeai as invokeai_launcher


class _FakeParser:
    def __init__(self, has_disable_auto_launch: bool = False):
        self._option_string_actions = {}
        self.added: list[tuple[str, tuple, dict]] = []
        if has_disable_auto_launch:
            self._option_string_actions["--disable-auto-launch"] = object()

    def add_argument(self, option: str, *args, **kwargs) -> None:
        if option in self._option_string_actions:
            raise AssertionError(f"{option} already exists")
        self._option_string_actions[option] = object()
        self.added.append((option, args, kwargs))

    def __deepcopy__(self, memo):
        copied = _FakeParser()
        copied._option_string_actions = dict(self._option_string_actions)
        copied.added = list(self.added)
        return copied


def _install_fake_invokeai_modules(monkeypatch, parser, invokeai_args, run_app):
    async def original_serve(self, sockets=None):
        self.events.append(("original_serve", sockets))

    class FakeServer:
        serve = original_serve

        def __init__(self):
            self.config = SimpleNamespace(host="127.0.0.1", port=9090)
            self.events = []

    uvicorn_module = types.ModuleType("uvicorn")
    uvicorn_module.Server = FakeServer

    invokeai_module = types.ModuleType("invokeai")
    frontend_module = types.ModuleType("invokeai.frontend")
    cli_module = types.ModuleType("invokeai.frontend.cli")
    arg_parser_module = types.ModuleType("invokeai.frontend.cli.arg_parser")
    app_module = types.ModuleType("invokeai.app")
    run_app_module = types.ModuleType("invokeai.app.run_app")

    arg_parser_module._parser = parser
    arg_parser_module.InvokeAIArgs = invokeai_args
    run_app_module.run_app = run_app

    invokeai_module.frontend = frontend_module
    invokeai_module.app = app_module
    frontend_module.cli = cli_module
    cli_module.arg_parser = arg_parser_module
    app_module.run_app = run_app_module

    for name, module in {
        "uvicorn": uvicorn_module,
        "invokeai": invokeai_module,
        "invokeai.frontend": frontend_module,
        "invokeai.frontend.cli": cli_module,
        "invokeai.frontend.cli.arg_parser": arg_parser_module,
        "invokeai.app": app_module,
        "invokeai.app.run_app": run_app_module,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    return uvicorn_module, arg_parser_module, original_serve


def test_invokeai_launcher_adds_auto_launch_arg_and_restores(monkeypatch):
    parser = _FakeParser()
    parse_calls = []
    browser_calls = []
    thread_calls = []
    serve_events = []

    class FakeInvokeAIArgs:
        args = object()
        did_parse = True

        @classmethod
        def parse_args(cls):
            parse_calls.append("parse")
            return SimpleNamespace(disable_auto_launch=False)

    class ImmediateThread:
        def __init__(self, target, daemon=False):
            self.target = target
            self.daemon = daemon

        def start(self):
            thread_calls.append(self.daemon)
            self.target()

    def run_app():
        server = uvicorn_module.Server()
        asyncio.run(uvicorn_module.Server.serve(server, ["socket"]))
        serve_events.extend(server.events)

    uvicorn_module, arg_parser_module, original_serve = _install_fake_invokeai_modules(
        monkeypatch,
        parser,
        FakeInvokeAIArgs,
        run_app,
    )
    monkeypatch.setattr(invokeai_launcher.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(invokeai_launcher.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(invokeai_launcher.webbrowser, "open", lambda url: browser_calls.append(url))

    invokeai_launcher.main()

    assert parser.added[0][0] == "--disable-auto-launch"
    assert parse_calls == ["parse"]
    assert thread_calls == [True]
    assert browser_calls == ["http://127.0.0.1:9090"]
    assert serve_events == [("original_serve", ["socket"])]
    assert uvicorn_module.Server.serve is original_serve
    assert arg_parser_module._parser is not parser
    assert FakeInvokeAIArgs.args is None
    assert FakeInvokeAIArgs.did_parse is False


def test_invokeai_launcher_skips_existing_auto_launch_arg(monkeypatch):
    parser = _FakeParser(has_disable_auto_launch=True)
    run_calls = []

    class FakeInvokeAIArgs:
        args = object()
        did_parse = True

        @classmethod
        def parse_args(cls):
            return SimpleNamespace(disable_auto_launch=True)

    def run_app():
        run_calls.append("run")

    _install_fake_invokeai_modules(monkeypatch, parser, FakeInvokeAIArgs, run_app)

    invokeai_launcher.main()

    assert parser.added == []
    assert run_calls == ["run"]


def test_invokeai_launcher_falls_back_after_failed_run(monkeypatch):
    parser = _FakeParser()
    run_calls = []

    class FakeInvokeAIArgs:
        args = object()
        did_parse = True

        @classmethod
        def parse_args(cls):
            return SimpleNamespace(disable_auto_launch=True)

    def run_app():
        run_calls.append("run")
        if len(run_calls) == 1:
            raise RuntimeError("first run failed")
        assert uvicorn_module.Server.serve is original_serve

    uvicorn_module, _arg_parser_module, original_serve = _install_fake_invokeai_modules(
        monkeypatch,
        parser,
        FakeInvokeAIArgs,
        run_app,
    )

    invokeai_launcher.main()

    assert run_calls == ["run", "run"]
    assert uvicorn_module.Server.serve is original_serve
