"""Read-only discovery of launch arguments supported by installed WebUIs."""

from __future__ import annotations

import atexit
import hashlib
import importlib.metadata
import json
import os
import re
import signal
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol


CATALOG_SCHEMA_VERSION = 2
DEFAULT_DISCOVERY_TIMEOUT_SECONDS = 15.0
MAX_DIAGNOSTIC_OUTPUT = 4096


class LaunchArgumentValueKind(str, Enum):
    BOOLEAN = "boolean"
    VALUE = "value"
    OPTIONAL_VALUE = "optional_value"
    MULTI_VALUE = "multi_value"


@dataclass(frozen=True, slots=True)
class LaunchArgumentDiagnostic:
    severity: str
    code: str
    message: str
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class LaunchArgumentDefinition:
    name: str
    flags: list[str]
    value_kind: LaunchArgumentValueKind
    min_values: int
    max_values: int | None
    help: str
    category: str
    metavar: str | None
    choices: list[str]
    required: bool
    repeatable: bool
    exclusive_group: str | None
    exclusive_group_required: bool
    hidden: bool


@dataclass(frozen=True, slots=True)
class LaunchArgumentCatalog:
    schema_version: int
    webui_type: str
    catalog_revision: str
    arguments: list[LaunchArgumentDefinition] = field(default_factory=list)
    diagnostics: list[LaunchArgumentDiagnostic] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize using the stable snake_case API shape."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LaunchArgumentDiscoveryContext:
    webui_type: str
    webui_path: Path
    python_executable: Path = Path(sys.executable)
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS


class LaunchArgumentProvider(Protocol):
    def provider_identity(self) -> str:
        """Return a stable identity for the normalized provider contract."""

    def get_catalog(self, context: LaunchArgumentDiscoveryContext) -> LaunchArgumentCatalog:
        """Discover and normalize the current installed argument contract."""


@dataclass(frozen=True, slots=True)
class HelpCommand:
    argv: list[str]
    source_identity: str
    env: dict[str, str] | None = None


_ACTIVE_PROCESSES: set[subprocess.Popen[str]] = set()
_ACTIVE_PROCESSES_LOCK = threading.Lock()


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=1)
    except (OSError, subprocess.TimeoutExpired):
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            pass


def cancel_launch_argument_discovery() -> None:
    """Terminate every in-flight discovery child during API/process shutdown."""
    with _ACTIVE_PROCESSES_LOCK:
        processes = list(_ACTIVE_PROCESSES)
    for process in processes:
        _terminate_process(process)


atexit.register(cancel_launch_argument_discovery)


def _run_help(command: HelpCommand, context: LaunchArgumentDiscoveryContext) -> tuple[str, LaunchArgumentDiagnostic | None]:
    try:
        process = subprocess.Popen(
            command.argv,
            cwd=context.webui_path,
            env=command.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=os.name == "posix",
        )
    except OSError as error:
        return "", LaunchArgumentDiagnostic("error", "discovery_unavailable", "Unable to start WebUI help discovery", str(error))
    with _ACTIVE_PROCESSES_LOCK:
        _ACTIVE_PROCESSES.add(process)
    try:
        try:
            stdout, stderr = process.communicate(timeout=context.timeout_seconds)
        except subprocess.TimeoutExpired:
            _terminate_process(process)
            stdout, stderr = process.communicate()
            detail = (stdout + "\n" + stderr).strip()[-MAX_DIAGNOSTIC_OUTPUT:] or None
            return "", LaunchArgumentDiagnostic(
                "error",
                "discovery_timeout",
                f"WebUI help discovery exceeded {context.timeout_seconds:g} seconds",
                detail,
            )
    finally:
        with _ACTIVE_PROCESSES_LOCK:
            _ACTIVE_PROCESSES.discard(process)
    output = "\n".join(part for part in (stdout, stderr) if part).replace("\r\n", "\n").replace("\r", "\n").strip()
    if process.returncode not in (0, None) and not output:
        return "", LaunchArgumentDiagnostic("error", "discovery_failed", f"WebUI help discovery exited with code {process.returncode}")
    return output, None


_HEADING = re.compile(r"^\s*(?P<name>[^:\n]+):\s*$")
_FLAG = re.compile(r"-{1,2}[A-Za-z0-9][A-Za-z0-9_-]*")
_CHOICES = re.compile(r"\{([^{}]+)\}")
_HELP_FLAGS = frozenset({"-h", "--help"})


def _category(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    if normalized in {"options", "optional_arguments", "arguments"}:
        return "general"
    return normalized or "other"


def _canonical_name(flags: list[str]) -> str:
    selected = next((flag for flag in flags if flag.startswith("--")), flags[0])
    return selected.lstrip("-").replace("-", "_")


def _normalized_flags(flags: list[str]) -> list[str]:
    return sorted(
        set(flags),
        key=lambda flag: (0 if flag.startswith("-") and not flag.startswith("--") else 1, flag),
    )


def _value_shape(
    spec: str,
    help_text: str,
) -> tuple[LaunchArgumentValueKind, int, int | None, str | None, list[str], bool]:
    flags = list(_FLAG.finditer(spec))
    tail = spec[flags[-1].end():].strip(" ,") if flags else ""
    choices_match = _CHOICES.search(tail)
    choices = sorted({item.strip() for item in choices_match.group(1).split(",") if item.strip()}) if choices_match else []
    metavar = choices_match.group(0) if choices_match else (tail or None)
    if not tail:
        kind = LaunchArgumentValueKind.BOOLEAN
        min_values, max_values = 0, 0
    elif "..." in tail or tail in {"*", "+"}:
        kind = LaunchArgumentValueKind.MULTI_VALUE
        min_values = 0 if tail == "*" or (tail.startswith("[") and tail.endswith("]")) else 1
        max_values = None
    elif tail.startswith("[") and tail.endswith("]"):
        kind = LaunchArgumentValueKind.OPTIONAL_VALUE
        min_values, max_values = 0, 1
    else:
        kind = LaunchArgumentValueKind.VALUE
        min_values, max_values = 1, 1
    repeatable = bool(re.search(r"repeat|multiple times|more than once", help_text, re.I))
    return kind, min_values, max_values, metavar, choices, repeatable


def _split_option_declaration(line: str) -> tuple[str, str] | None:
    """Split an argparse declaration from same-line help, if present."""
    stripped = line.lstrip()
    if not stripped.startswith("-") or _FLAG.match(stripped) is None:
        return None
    match = re.search(r"\s{2,}", stripped)
    if match is None:
        return stripped.rstrip(), ""
    return stripped[: match.start()].rstrip(), stripped[match.end() :].strip()


def _usage_metadata(usage: str) -> tuple[dict[str, tuple[str, bool]], set[str]]:
    """Scan nested usage delimiters without confusing optional metavars."""
    stack: list[dict[str, object]] = []
    groups: list[tuple[str, list[str]]] = []
    required_flags: set[str] = set()
    index = 0
    while index < len(usage):
        character = usage[index]
        if character in "[(":
            stack.append({"opening": character, "flags": [], "has_pipe": False})
            index += 1
            continue
        if character in ")]":
            expected = "(" if character == ")" else "["
            if stack and stack[-1]["opening"] == expected:
                frame = stack.pop()
                flags = list(dict.fromkeys(frame["flags"]))
                if frame["has_pipe"] and len(flags) >= 2:
                    groups.append((str(frame["opening"]), flags))
            index += 1
            continue
        if character == "|":
            if stack:
                stack[-1]["has_pipe"] = True
            index += 1
            continue
        flag = _FLAG.match(usage, index)
        if flag is not None:
            value = flag.group(0)
            for frame in stack:
                frame["flags"].append(value)
            if not any(frame["opening"] == "[" for frame in stack):
                required_flags.add(value)
            index = flag.end()
            continue
        index += 1

    group_by_flag: dict[str, tuple[str, bool]] = {}
    for opening, flags in groups:
        stable_members = "\0".join(sorted(set(flags)))
        group_name = "exclusive_" + hashlib.sha256(f"{opening}\0{stable_members}".encode()).hexdigest()[:16]
        for flag in flags:
            group_by_flag[flag] = (group_name, opening == "(")
    return group_by_flag, required_flags


def parse_argparse_help(
    help_output: str,
    *,
    hidden_flags: frozenset[str] = frozenset(),
) -> tuple[list[LaunchArgumentDefinition], list[LaunchArgumentDiagnostic]]:
    """Parse the stable subset common to argparse-style help formatters."""
    lines = help_output.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    usage_lines: list[str] = []
    reading_usage = False
    for line in lines:
        if line.lstrip().startswith("usage:"):
            reading_usage = True
        if reading_usage:
            if not line.strip():
                break
            usage_lines.append(line.strip())
    usage = " ".join(usage_lines)
    category = "other"
    parsed: list[tuple[str, str, str]] = []
    diagnostics: list[LaunchArgumentDiagnostic] = []
    current: int | None = None
    unrecognized_declarations = 0
    for line in lines:
        heading = _HEADING.match(line)
        if heading and not line.lstrip().startswith("usage:"):
            category = _category(heading.group("name"))
            current = None
            continue
        declaration = _split_option_declaration(line)
        if declaration is not None:
            spec, help_text = declaration
            flags = _normalized_flags(_FLAG.findall(spec))
            if not flags:
                current = None
                unrecognized_declarations += 1
                continue
            parsed.append((spec, help_text, category))
            current = len(parsed) - 1
        elif line.lstrip().startswith("-"):
            current = None
            unrecognized_declarations += 1
        elif current is not None and line.strip() and len(line) > len(line.lstrip()):
            item = parsed[current]
            parsed[current] = (item[0], " ".join((item[1], line.strip())).strip(), item[2])
        elif not line.strip():
            current = None

    group_by_flag, required_flags = _usage_metadata(usage)

    arguments: list[LaunchArgumentDefinition] = []
    effective_hidden = hidden_flags | _HELP_FLAGS
    for spec, help_text, item_category in parsed:
        flags = _normalized_flags(_FLAG.findall(spec))
        kind, min_values, max_values, metavar, choices, repeatable = _value_shape(spec, help_text)
        group = next((group_by_flag[flag] for flag in flags if flag in group_by_flag), (None, False))
        required = any(flag in required_flags for flag in flags) and group[0] is None
        arguments.append(
            LaunchArgumentDefinition(
                name=_canonical_name(flags),
                flags=flags,
                value_kind=kind,
                min_values=min_values,
                max_values=max_values,
                help=help_text,
                category=item_category or "other",
                metavar=metavar,
                choices=choices,
                required=required,
                repeatable=repeatable,
                exclusive_group=group[0],
                exclusive_group_required=group[1],
                hidden=any(flag in effective_hidden for flag in flags),
            )
        )
    if not arguments:
        diagnostics.append(LaunchArgumentDiagnostic("error", "parse_empty", "WebUI help output contained no recognizable options", help_output[-MAX_DIAGNOSTIC_OUTPUT:] or None))
    elif not usage:
        diagnostics.append(LaunchArgumentDiagnostic("warning", "usage_missing", "Options were parsed, but the help output did not expose a usage line"))
    if unrecognized_declarations:
        diagnostics.append(
            LaunchArgumentDiagnostic(
                "warning",
                "parse_partial",
                f"Skipped {unrecognized_declarations} unrecognized option declaration(s)",
            )
        )
    arguments.sort(key=lambda argument: (argument.name, tuple(argument.flags)))
    return arguments, diagnostics


class ScriptHelpProvider:
    def __init__(self, scripts: tuple[str, ...], *, hidden_flags: frozenset[str] = frozenset()) -> None:
        self.scripts = scripts
        self.hidden_flags = hidden_flags

    def provider_identity(self) -> str:
        return json.dumps(
            {
                "provider": type(self).__name__,
                "scripts": list(self.scripts),
                "hidden_flags": sorted(self.hidden_flags | _HELP_FLAGS),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    def help_command(self, context: LaunchArgumentDiscoveryContext) -> HelpCommand | None:
        script = next((context.webui_path / item for item in self.scripts if (context.webui_path / item).is_file()), None)
        if script is None:
            return None
        digest = hashlib.sha256(script.read_bytes()).hexdigest()[:16]
        source_parts = [script.name, digest]
        head_path = context.webui_path / ".git" / "HEAD"
        try:
            head = head_path.read_text(encoding="utf-8").strip()
            source_parts.append(head)
            if head.startswith("ref: "):
                source_parts.append((context.webui_path / ".git" / head[5:]).read_text(encoding="utf-8").strip())
        except OSError:
            pass
        return HelpCommand([str(context.python_executable), str(script), "--help"], ":".join(source_parts))

    def get_catalog(self, context: LaunchArgumentDiscoveryContext) -> LaunchArgumentCatalog:
        command = self.help_command(context)
        if command is None:
            source_identity = "missing:" + "|".join(self.scripts)
            revision = _contract_revision(
                context.webui_type,
                self.provider_identity(),
                source_identity,
                [],
            )
            return LaunchArgumentCatalog(
                CATALOG_SCHEMA_VERSION,
                context.webui_type,
                revision,
                diagnostics=[LaunchArgumentDiagnostic("error", "discovery_unavailable", "No supported WebUI launch script exists in the installed core")],
            )
        output, failure = _run_help(command, context)
        if failure is not None:
            return LaunchArgumentCatalog(
                CATALOG_SCHEMA_VERSION,
                context.webui_type,
                _contract_revision(
                    context.webui_type,
                    self.provider_identity(),
                    command.source_identity,
                    [],
                ),
                diagnostics=[failure],
            )
        arguments, diagnostics = parse_argparse_help(output, hidden_flags=self.hidden_flags)
        return LaunchArgumentCatalog(
            CATALOG_SCHEMA_VERSION,
            context.webui_type,
            _contract_revision(
                context.webui_type,
                self.provider_identity(),
                command.source_identity,
                arguments,
            ),
            arguments,
            diagnostics,
        )


class InvokeAiHelpProvider(ScriptHelpProvider):
    def __init__(self) -> None:
        super().__init__((), hidden_flags=frozenset({"--disable-auto-launch"}))

    def help_command(self, context: LaunchArgumentDiscoveryContext) -> HelpCommand:
        try:
            version = importlib.metadata.version("invokeai")
        except importlib.metadata.PackageNotFoundError:
            version = "unavailable"
        source = f"invokeai.frontend.cli.arg_parser:_parser:{version}"
        code = "from invokeai.frontend.cli.arg_parser import _parser; _parser.print_help()"
        env = os.environ.copy()
        env["INVOKEAI_ROOT"] = str(context.webui_path)
        return HelpCommand([str(context.python_executable), "-c", code], source, env)


PROVIDERS: dict[str, LaunchArgumentProvider] = {
    "sd_webui": ScriptHelpProvider(("launch.py",), hidden_flags=frozenset({"--api-auth", "--api-server-stop"})),
    "comfyui": ScriptHelpProvider(("main.py",)),
    "fooocus": ScriptHelpProvider(("launch.py",)),
    "invokeai": InvokeAiHelpProvider(),
    "sd_trainer": ScriptHelpProvider(("gui.py", "kohya_gui.py")),
    "qwen_tts_webui": ScriptHelpProvider(("launch.py",)),
}


def _contract_revision(
    webui_type: str,
    provider_identity: str,
    source_identity: str,
    arguments: list[LaunchArgumentDefinition],
) -> str:
    canonical_arguments = [
        {
            "name": argument.name,
            "flags": sorted(argument.flags),
            "value_kind": argument.value_kind.value,
            "min_values": argument.min_values,
            "max_values": argument.max_values,
            "metavar": argument.metavar,
            "choices": sorted(argument.choices),
            "category": argument.category,
            "required": argument.required,
            "repeatable": argument.repeatable,
            "exclusive_group": argument.exclusive_group,
            "exclusive_group_required": argument.exclusive_group_required,
            "hidden": argument.hidden,
        }
        for argument in sorted(arguments, key=lambda item: (item.name, tuple(sorted(item.flags))))
    ]
    payload = json.dumps(
        {
            "schema_version": CATALOG_SCHEMA_VERSION,
            "webui_type": webui_type.strip().lower(),
            "provider_identity": provider_identity,
            "source_identity": source_identity,
            "arguments": canonical_arguments,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def get_launch_argument_catalog(
    webui_type: str,
    webui_path: str | Path,
    *,
    python_executable: str | Path | None = None,
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
) -> LaunchArgumentCatalog:
    """Discover the current installed catalog without persisting user data."""
    provider = PROVIDERS.get(webui_type)
    if provider is None:
        raise ValueError(f"Unsupported webui_type: {webui_type}")
    path = Path(webui_path)
    context = LaunchArgumentDiscoveryContext(
        webui_type=webui_type,
        webui_path=path,
        python_executable=Path(python_executable or sys.executable),
        timeout_seconds=max(0.1, min(float(timeout_seconds), 30.0)),
    )
    return provider.get_catalog(context)


__all__ = [
    "CATALOG_SCHEMA_VERSION",
    "LaunchArgumentCatalog",
    "LaunchArgumentDefinition",
    "LaunchArgumentDiagnostic",
    "LaunchArgumentDiscoveryContext",
    "LaunchArgumentProvider",
    "LaunchArgumentValueKind",
    "PROVIDERS",
    "cancel_launch_argument_discovery",
    "get_launch_argument_catalog",
    "parse_argparse_help",
]
