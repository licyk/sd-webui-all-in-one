"""启动参数目录发现, 加载与修订号测试"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

import pytest

import sd_webui_all_in_one.launch_arguments as launch_arguments_module
from sd_webui_all_in_one.base_manager import sd_webui_base
from sd_webui_all_in_one.launch_arguments import (
    CATALOG_SCHEMA_VERSION,
    build_script_help_command,
    cancel_launch_argument_discovery,
    discover_launch_argument_catalog,
)
from tests.launch_arguments.helpers import HELP_LF


def _get_script_catalog(
    webui_type: str,
    path: Path,
    *,
    timeout_seconds: float = 15.0,
):
    return discover_launch_argument_catalog(
        webui_type,
        path,
        provider_identity="test:script-help",
        help_command_factory=lambda context: build_script_help_command(context, ("launch.py",)),
        use_parser_object=False,
        python_executable=sys.executable,
        timeout_seconds=timeout_seconds,
    )


def test_catalog_models_serialize_stable_snake_case_shape(tmp_path: Path) -> None:
    script = tmp_path / "launch.py"
    script.write_text("print('''" + HELP_LF + "''')", encoding="utf-8")
    catalog = _get_script_catalog("demo", tmp_path)
    payload = catalog.to_dict()
    assert payload["schema_version"] == CATALOG_SCHEMA_VERSION
    assert payload["webui_type"] == "demo"
    assert len(payload["catalog_revision"]) == 64
    assert payload["arguments"][0]["value_kind"] == "boolean"
    assert payload["arguments"][0]["min_values"] == 0
    assert payload["arguments"][0]["max_values"] == 0
    assert "hidden" not in payload["arguments"][0]
    assert "catalogRevision" not in payload
    json.dumps(payload)


def test_discovery_timeout_terminates_child_and_never_returns_empty_success(tmp_path: Path) -> None:
    marker = tmp_path / "completed"
    (tmp_path / "launch.py").write_text(
        "import time, pathlib\ntime.sleep(5)\npathlib.Path(r'%s').write_text('bad')\n" % marker,
        encoding="utf-8",
    )
    started = time.monotonic()
    catalog = _get_script_catalog("demo", tmp_path, timeout_seconds=0.1)
    assert time.monotonic() - started < 3
    assert catalog.arguments == []
    assert catalog.diagnostics[0].code == "discovery_timeout"
    time.sleep(0.1)
    assert not marker.exists()


def test_discovery_shutdown_cancellation_terminates_child(tmp_path: Path) -> None:
    marker = tmp_path / "completed"
    (tmp_path / "launch.py").write_text(
        "import time, pathlib\ntime.sleep(5)\npathlib.Path(r'%s').write_text('bad')\n" % marker,
        encoding="utf-8",
    )
    result = []
    worker = threading.Thread(target=lambda: result.append(_get_script_catalog("demo", tmp_path, timeout_seconds=10)))
    worker.start()
    time.sleep(0.2)
    cancel_launch_argument_discovery()
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert result and result[0].diagnostics[0].code == "discovery_failed"
    assert not marker.exists()


def test_parser_loader_hides_host_arguments_and_restores_argv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sd_webui_path = tmp_path / "sd_webui"
    (sd_webui_path / "modules").mkdir(parents=True)
    (sd_webui_path / "modules" / "__init__.py").write_text("", encoding="utf-8")
    (sd_webui_path / "modules" / "cmd_args.py").write_text(
        """import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--api", action="store_true")
parser.parse_args()
""",
        encoding="utf-8",
    )
    original_argv = ["manager", "--desktop-only"]
    monkeypatch.setattr(sys, "argv", original_argv)

    catalog = sd_webui_base.get_sd_webui_launch_argument_catalog(sd_webui_path)

    assert not catalog.diagnostics
    assert {argument.name for argument in catalog.arguments} >= {"api", "help"}
    assert sys.argv is original_argv


def test_parser_loader_system_exit_falls_back_to_help(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "launch.py").write_text("print('''" + HELP_LF + "''')", encoding="utf-8")
    original_argv = ["manager", "--desktop-only"]
    monkeypatch.setattr(sys, "argv", original_argv)

    def load_parser():
        parser = argparse.ArgumentParser()
        parser.add_argument("--token", required=True)
        parser.parse_args()
        return parser

    catalog = discover_launch_argument_catalog(
        "demo",
        tmp_path,
        provider_identity="test:system-exit",
        help_command_factory=lambda context: build_script_help_command(context, ("launch.py",)),
        parser_loader=load_parser,
        python_executable=sys.executable,
    )

    assert catalog.arguments
    diagnostic = next(item for item in catalog.diagnostics if item.code == "object_discovery_failed")
    assert diagnostic.message == "ArgumentParser loader exited; falling back to --help"
    assert diagnostic.detail == "exit code: 2"
    assert sys.argv is original_argv


def test_parser_loaders_are_serialized(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original_argv = ["manager", "--desktop-only"]
    monkeypatch.setattr(sys, "argv", original_argv)
    barrier = threading.Barrier(3)
    state_lock = threading.Lock()
    active_loaders = 0
    max_active_loaders = 0
    seen_argv: list[list[str]] = []
    catalogs = []

    def load_parser():
        nonlocal active_loaders, max_active_loaders
        with state_lock:
            active_loaders += 1
            max_active_loaders = max(max_active_loaders, active_loaders)
            seen_argv.append(list(sys.argv))
        time.sleep(0.05)
        parser = argparse.ArgumentParser()
        parser.add_argument("--listen", action="store_true")
        with state_lock:
            active_loaders -= 1
        return parser

    def discover() -> None:
        barrier.wait()
        catalogs.append(
            discover_launch_argument_catalog(
                "demo",
                tmp_path,
                provider_identity="test:serialized-loader",
                help_command_factory=lambda _context: None,
                parser_loader=load_parser,
            )
        )

    workers = [threading.Thread(target=discover) for _ in range(2)]
    for worker in workers:
        worker.start()
    barrier.wait()
    for worker in workers:
        worker.join(timeout=2)

    assert all(not worker.is_alive() for worker in workers)
    assert len(catalogs) == 2
    assert all(not catalog.diagnostics for catalog in catalogs)
    assert max_active_loaders == 1
    assert seen_argv == [["manager"], ["manager"]]
    assert sys.argv is original_argv


def test_catalog_revision_changes_with_source_contract(tmp_path: Path) -> None:
    script = tmp_path / "launch.py"
    script.write_text("print('''" + HELP_LF + "''')", encoding="utf-8")
    first = _get_script_catalog("demo", tmp_path)
    script.write_text("print('''" + HELP_LF.replace("--port PORT", "--port-number PORT") + "''')", encoding="utf-8")
    second = _get_script_catalog("demo", tmp_path)
    assert first.catalog_revision != second.catalog_revision


def test_catalog_revision_is_stable_for_contract_and_ignores_transient_noise(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "launch.py").write_text("", encoding="utf-8")
    outputs = iter(
        [
            HELP_LF,
            HELP_LF,
            HELP_LF + "\nWARNING: imported from /tmp/example at 2026-01-01\n",
            HELP_LF.replace("--port PORT", "--port [PORT]"),
        ]
    )
    monkeypatch.setattr(
        launch_arguments_module,
        "_run_help",
        lambda _command, _context: (next(outputs), "", None),
    )
    revisions = [_get_script_catalog("demo", tmp_path).catalog_revision for _ in range(4)]
    assert revisions[0] == revisions[1] == revisions[2]
    assert revisions[3] != revisions[0]
