"""各 WebUI 管理器的启动参数目录测试"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import sd_webui_all_in_one.base_manager.invokeai_base.catalog as invokeai_catalog
from sd_webui_all_in_one.api_server import registry
from sd_webui_all_in_one.base_manager import comfyui_base, fooocus_base, invokeai_base, mizuoto_tts_webui_base, qwen_tts_webui_base, rvc_next_webui_base, sd_trainer_base, sd_webui_base
from sd_webui_all_in_one.base_manager.launch_arguments import (
    LaunchArgumentValueKind,
)
from tests.base_manager.launch_arguments.helpers import HELP_LF


def _write_comfyui_argument_parser(path: Path) -> None:
    package = path / "comfy"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "cli_args.py").write_text(
        """import argparse
parser = argparse.ArgumentParser()
network = parser.add_argument_group("Network options")
network.add_argument("--listen", nargs="?", metavar="IP")
network.add_argument("--port", type=int, default=8188)
cache = parser.add_mutually_exclusive_group()
cache.add_argument("--cache-classic", action="store_true")
cache.add_argument("--cache-lru", type=int)
""",
        encoding="utf-8",
    )


def test_missing_comfyui_parser_returns_explicit_unavailable_catalog(tmp_path: Path) -> None:
    catalog = comfyui_base.get_comfyui_launch_argument_catalog(tmp_path)
    assert catalog.arguments == []
    assert any(diagnostic.code == "discovery_unavailable" for diagnostic in catalog.diagnostics)


def test_api_registry_exposes_structured_catalog(tmp_path: Path) -> None:
    _write_comfyui_argument_parser(tmp_path)
    methods = registry.get_default_methods()
    target = methods["comfyui.launch.arguments_catalog"]
    assert callable(target)
    result = target(tmp_path)
    assert result.webui_type == "comfyui"
    assert result.arguments
    assert result.arguments[0].min_values == 0
    assert result.arguments[0].max_values == 0


def test_comfyui_base_parses_actual_argument_parser_object(tmp_path: Path) -> None:
    _write_comfyui_argument_parser(tmp_path)

    catalog = comfyui_base.get_comfyui_launch_argument_catalog(tmp_path)

    assert catalog.webui_type == "comfyui"
    assert len(catalog.catalog_revision) == 64
    assert catalog.diagnostics == []
    by_name = {argument.name: argument for argument in catalog.arguments}
    assert by_name["listen"].category == "network_options"
    assert by_name["listen"].value_kind is LaunchArgumentValueKind.OPTIONAL_VALUE
    assert by_name["cache_classic"].exclusive_group == by_name["cache_lru"].exclusive_group


def test_migrated_base_managers_parse_their_actual_parser_objects(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sd_webui_path = tmp_path / "sd_webui"
    (sd_webui_path / "modules").mkdir(parents=True)
    (sd_webui_path / "modules" / "__init__.py").write_text("", encoding="utf-8")
    (sd_webui_path / "modules" / "cmd_args.py").write_text(
        "import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--api', action='store_true')\n",
        encoding="utf-8",
    )

    fooocus_path = tmp_path / "fooocus"
    fooocus_path.mkdir()
    (fooocus_path / "args_manager.py").write_text(
        """import argparse
class ArgsParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("--preset")
args_parser = ArgsParser()
""",
        encoding="utf-8",
    )

    trainer_path = tmp_path / "trainer"
    trainer_path.mkdir()
    (trainer_path / "gui.py").write_text(
        "import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--listen', action='store_true')\n",
        encoding="utf-8",
    )

    kohya_path = tmp_path / "kohya"
    kohya_path.mkdir()
    (kohya_path / "kohya_gui.py").write_text(
        """import argparse
def initialize_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    return parser
""",
        encoding="utf-8",
    )

    qwen_path = tmp_path / "qwen"
    (qwen_path / "qwen_tts_webui").mkdir(parents=True)
    (qwen_path / "qwen_tts_webui" / "__init__.py").write_text("", encoding="utf-8")
    (qwen_path / "qwen_tts_webui" / "cmd_args.py").write_text(
        """import argparse
def get_args_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-port", type=int)
    return parser
""",
        encoding="utf-8",
    )

    rvc_path = tmp_path / "rvc"
    (rvc_path / "rvc_next_webui").mkdir(parents=True)
    (rvc_path / "rvc_next_webui" / "__init__.py").write_text("", encoding="utf-8")
    (rvc_path / "rvc_next_webui" / "cmd_args.py").write_text(
        """import argparse
def get_args_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true")
    return parser
""",
        encoding="utf-8",
    )

    mizuoto_path = tmp_path / "mizuoto"
    (mizuoto_path / "mizuoto_tts_webui").mkdir(parents=True)
    (mizuoto_path / "mizuoto_tts_webui" / "__init__.py").write_text("", encoding="utf-8")
    (mizuoto_path / "mizuoto_tts_webui" / "cmd_args.py").write_text(
        """import argparse
def get_args_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true")
    return parser
""",
        encoding="utf-8",
    )

    invoke_parser = argparse.ArgumentParser()
    invoke_parser.add_argument("--invoke-model")
    original_import_module = invokeai_catalog.importlib.import_module
    monkeypatch.setattr(
        invokeai_catalog.importlib,
        "import_module",
        lambda name: SimpleNamespace(_parser=invoke_parser) if name == "invokeai.frontend.cli.arg_parser" else original_import_module(name),
    )

    catalogs = {
        "sd_webui": sd_webui_base.get_sd_webui_launch_argument_catalog(sd_webui_path),
        "fooocus": fooocus_base.get_fooocus_launch_argument_catalog(fooocus_path),
        "trainer": sd_trainer_base.get_sd_trainer_launch_argument_catalog(trainer_path),
        "kohya": sd_trainer_base.get_sd_trainer_launch_argument_catalog(kohya_path),
        "qwen": qwen_tts_webui_base.get_qwen_tts_webui_launch_argument_catalog(qwen_path),
        "rvc": rvc_next_webui_base.get_rvc_next_webui_launch_argument_catalog(rvc_path),
        "mizuoto": mizuoto_tts_webui_base.get_mizuoto_tts_webui_launch_argument_catalog(mizuoto_path),
        "invokeai": invokeai_base.get_invokeai_launch_argument_catalog(tmp_path / "invokeai"),
    }

    assert all(not catalog.diagnostics for catalog in catalogs.values())
    assert {argument.name for argument in catalogs["sd_webui"].arguments} >= {"api", "help"}
    assert {argument.name for argument in catalogs["fooocus"].arguments} >= {"preset", "help"}
    assert {argument.name for argument in catalogs["trainer"].arguments} >= {"listen", "help"}
    assert {argument.name for argument in catalogs["kohya"].arguments} >= {"headless", "help"}
    assert {argument.name for argument in catalogs["qwen"].arguments} >= {"server_port", "help"}
    assert {argument.name for argument in catalogs["rvc"].arguments} >= {"no_browser", "help"}
    assert {argument.name for argument in catalogs["invokeai"].arguments} >= {"invoke_model", "help"}
    methods = registry.get_default_methods()
    assert {
        "sd_webui.launch.arguments_catalog",
        "comfyui.launch.arguments_catalog",
        "fooocus.launch.arguments_catalog",
        "invokeai.launch.arguments_catalog",
        "sd_trainer.launch.arguments_catalog",
        "qwen_tts_webui.launch.arguments_catalog",
        "rvc_next_webui.launch.arguments_catalog",
        "mizuoto_tts_webui.launch.arguments_catalog",
    }.issubset(methods)


def test_base_manager_object_failure_falls_back_to_help_and_switch_can_disable_object(tmp_path: Path) -> None:
    (tmp_path / "launch.py").write_text("print('''" + HELP_LF + "''')", encoding="utf-8")

    fallback = sd_webui_base.get_sd_webui_launch_argument_catalog(
        tmp_path,
        python_executable=sys.executable,
    )
    help_only = sd_webui_base.get_sd_webui_launch_argument_catalog(
        tmp_path,
        use_parser_object=False,
        python_executable=sys.executable,
    )

    assert fallback.arguments == help_only.arguments
    assert any(diagnostic.code == "object_discovery_failed" for diagnostic in fallback.diagnostics)
    assert not any(diagnostic.code.startswith("object_discovery") for diagnostic in help_only.diagnostics)

    unavailable = sd_webui_base.get_sd_webui_launch_argument_catalog(tmp_path / "missing")
    assert unavailable.arguments == []
    assert any(diagnostic.severity == "error" for diagnostic in unavailable.diagnostics)
