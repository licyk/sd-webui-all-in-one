import json
import importlib
import sys
import types
from pathlib import Path

import pytest

fix_dependencies = importlib.import_module("sd_webui_all_in_one.env_check.fix_dependencies")
check_fooocus_args = importlib.import_module("sd_webui_all_in_one.env_check.check_fooocus_args")
fix_forge_neo_alert = importlib.import_module("sd_webui_all_in_one.env_check.fix_forge_neo_alert")
fix_torch = importlib.import_module("sd_webui_all_in_one.env_check.fix_torch")
ext_installer = importlib.import_module("sd_webui_all_in_one.env_check.sd_webui_extension_dependency_installer")


def test_run_extension_installer_sets_pythonpath_and_live_output(monkeypatch, tmp_path):
    webui = tmp_path / "webui"
    extension = webui / "extensions" / "demo"
    extension.mkdir(parents=True)
    (extension / "install.py").write_text("print('install')\n", encoding="utf-8")
    origin_env = {"PYTHONPATH": "old", "KEEP": "1"}
    calls = []

    def fake_run_cmd(command, custom_env, cwd):
        calls.append((command, custom_env, cwd))

    monkeypatch.setattr(ext_installer, "run_cmd", fake_run_cmd)

    assert ext_installer.run_extension_installer(webui, extension, custom_env=origin_env) is True
    assert origin_env == {"PYTHONPATH": "old", "KEEP": "1"}
    assert calls[0][0] == [Path(sys.executable).as_posix(), (extension / "install.py").as_posix()]
    assert calls[0][1]["WEBUI_LAUNCH_LIVE_OUTPUT"] == "1"
    assert calls[0][1]["PYTHONPATH"].startswith(webui.as_posix())
    assert calls[0][2] == webui

    monkeypatch.setattr(ext_installer, "run_cmd", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad install")))
    assert ext_installer.run_extension_installer(webui, extension) is False
    assert ext_installer.run_extension_installer(webui, webui / "missing") is False


def test_install_extension_requirements_filters_disabled_and_builtin(monkeypatch, tmp_path):
    webui = tmp_path / "webui"
    extra = webui / "extensions"
    builtin = webui / "extensions-builtin"
    for folder in [
        extra / "enabled",
        extra / "disabled",
        builtin / "builtin-enabled",
        builtin / "builtin-disabled",
    ]:
        folder.mkdir(parents=True)
        (folder / "install.py").write_text("", encoding="utf-8")
    (webui / "config.json").write_text(json.dumps({"disabled_extensions": ["disabled", "builtin-disabled"]}), encoding="utf-8")
    calls = []
    monkeypatch.setattr(ext_installer, "run_extension_installer", lambda sd_webui_base_path, extension_dir, custom_env=None: calls.append(extension_dir.name) or True)

    ext_installer.install_extension_requirements(webui, custom_env={"A": "B"})
    assert calls == ["enabled", "builtin-enabled"]

    calls.clear()
    (webui / "config.json").write_text(json.dumps({"disable_all_extensions": "extra"}), encoding="utf-8")
    ext_installer.install_extension_requirements(webui)
    assert sorted(calls) == ["builtin-disabled", "builtin-enabled"]

    calls.clear()
    (webui / "config.json").write_text(json.dumps({"disable_all_extensions": "all"}), encoding="utf-8")
    ext_installer.install_extension_requirements(webui)
    assert calls == []


def test_fix_forge_neo_alert_worker_updates_moves_or_ignores(monkeypatch, tmp_path):
    webui = tmp_path / "webui"
    modules = webui / "modules"
    modules.mkdir(parents=True)
    (modules / "__init__.py").write_text("", encoding="utf-8")
    (modules / "launch_utils.py").write_text("VERSION_UID = 'new-version'\n", encoding="utf-8")
    config = webui / "config.json"
    config.write_text(json.dumps({"VERSION_UID": "old"}), encoding="utf-8")

    try:
        fix_forge_neo_alert.fix_alert_worker(webui)
    finally:
        sys.path = [p for p in sys.path if p != webui.as_posix()]
        sys.modules.pop("modules.launch_utils", None)
        sys.modules.pop("modules", None)

    assert json.loads(config.read_text(encoding="utf-8"))["VERSION_UID"] == "new-version"

    moved = []
    config.write_text("{", encoding="utf-8")
    monkeypatch.setattr(fix_forge_neo_alert, "move_files", lambda src, dst: moved.append((src, dst)))
    try:
        fix_forge_neo_alert.fix_alert_worker(webui)
    finally:
        sys.path = [p for p in sys.path if p != webui.as_posix()]
        sys.modules.pop("modules.launch_utils", None)
        sys.modules.pop("modules", None)
    assert moved == [(config, webui / "tmp" / "config.json")]

    missing = tmp_path / "missing-webui"
    missing.mkdir()
    fix_forge_neo_alert.fix_alert_worker(missing)


def test_fix_forge_neo_alert_process_cleanup(monkeypatch, tmp_path):
    events = []

    class FakeProcess:
        def __init__(self, target, args, name):
            events.append(("process", target.__name__, args, name))
            self.alive = True

        def start(self):
            events.append("start")

        def join(self):
            events.append("join")

        def is_alive(self):
            return self.alive

        def terminate(self):
            events.append("terminate")
            self.alive = False

        def close(self):
            events.append("close")

    class FakeContext:
        Process = FakeProcess

    monkeypatch.setattr(fix_forge_neo_alert.multiprocessing, "get_context", lambda mode: events.append(("ctx", mode)) or FakeContext())

    fix_forge_neo_alert.fix_forge_neo_alert(tmp_path)

    assert events == [
        ("ctx", "spawn"),
        ("process", "fix_alert_worker", (tmp_path,), "ForgeNeoAlertFix"),
        "start",
        "join",
        "terminate",
        "join",
        "close",
    ]


def test_check_fooocus_hf_mirror_arg_detects_supported_parser(tmp_path):
    modules = tmp_path / "ldm_patched" / "modules"
    modules.mkdir(parents=True)
    (tmp_path / "ldm_patched" / "__init__.py").write_text("", encoding="utf-8")
    (modules / "__init__.py").write_text("", encoding="utf-8")
    (modules / "args_parser.py").write_text(
        "import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--hf-mirror')\n",
        encoding="utf-8",
    )

    assert check_fooocus_args.check_fooocus_hf_mirror_arg(tmp_path, timeout=5) is True


def test_check_fooocus_hf_mirror_arg_rejects_missing_or_unsupported_parser(tmp_path):
    missing = tmp_path / "missing"
    missing.mkdir()
    assert check_fooocus_args.check_fooocus_hf_mirror_arg(missing, timeout=5) is False

    modules = tmp_path / "unsupported" / "ldm_patched" / "modules"
    modules.mkdir(parents=True)
    (tmp_path / "unsupported" / "ldm_patched" / "__init__.py").write_text("", encoding="utf-8")
    (modules / "__init__.py").write_text("", encoding="utf-8")
    (modules / "args_parser.py").write_text(
        "import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--listen')\n",
        encoding="utf-8",
    )

    assert check_fooocus_args.check_fooocus_hf_mirror_arg(tmp_path / "unsupported", timeout=5) is False


def test_py_dependency_checker_installs_missing_and_wraps(monkeypatch, tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("demo\n", encoding="utf-8")
    calls = []

    monkeypatch.setattr(fix_dependencies, "validate_requirements", lambda path: calls.append(("validate", path)) or False)
    monkeypatch.setattr(fix_dependencies, "install_requirements", lambda **kwargs: calls.append(("install", kwargs)))

    fix_dependencies.py_dependency_checker(req, use_uv=False, custom_env={"A": "B"})

    assert calls == [
        ("validate", req),
        ("install", {"path": req, "use_uv": False, "cwd": tmp_path, "custom_env": {"A": "B"}}),
    ]

    monkeypatch.setattr(fix_dependencies, "install_requirements", lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("pip bad")))
    with pytest.raises(RuntimeError, match="pip bad"):
        fix_dependencies.py_dependency_checker(req)

    with pytest.raises(FileNotFoundError):
        fix_dependencies.py_dependency_checker(tmp_path / "missing.txt")


def test_py_package_metadata_dependency_checker_installs_only_missing(monkeypatch):
    calls = []
    monkeypatch.setattr(fix_dependencies, "get_missing_package_metadata_dependencies", lambda package_name: calls.append(("missing", package_name)) or [])
    monkeypatch.setattr(fix_dependencies, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))

    fix_dependencies.py_package_metadata_dependency_checker("demo[gpu]", name="Demo")

    assert calls == [("missing", "demo[gpu]")]

    calls.clear()
    monkeypatch.setattr(
        fix_dependencies,
        "get_missing_package_metadata_dependencies",
        lambda package_name: calls.append(("missing", package_name)) or ["dep>=1.0", "pkg[extra]>=2.0"],
    )

    fix_dependencies.py_package_metadata_dependency_checker("demo[gpu]", name="Demo", use_uv=False, custom_env={"A": "B"})

    assert calls == [
        ("missing", "demo[gpu]"),
        ("pip", ("dep>=1.0", "pkg[extra]>=2.0"), {"use_uv": False, "custom_env": {"A": "B"}}),
    ]


def test_py_package_metadata_dependency_checker_wraps_install_error(monkeypatch):
    monkeypatch.setattr(fix_dependencies, "get_missing_package_metadata_dependencies", lambda _package_name: ["dep>=1.0"])
    monkeypatch.setattr(fix_dependencies, "pip_install", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("pip bad")))

    with pytest.raises(RuntimeError, match="pip bad"):
        fix_dependencies.py_package_metadata_dependency_checker("demo")


def test_fix_torch_libomp_copies_missing_runtime(monkeypatch, tmp_path):
    torch_root = tmp_path / "torch"
    lib = torch_root / "lib"
    lib.mkdir(parents=True)
    fbgemm = lib / "fbgemm.dll"
    fbgemm.write_bytes(b"needs libomp140.x86_64.dll")
    (lib / "libiomp5md.dll").write_bytes(b"runtime")

    spec = types.SimpleNamespace(submodule_search_locations=[torch_root.as_posix()])
    monkeypatch.setattr(fix_torch.importlib.util, "find_spec", lambda name: spec if name == "torch" else None)
    monkeypatch.setattr(fix_torch.ctypes.cdll, "LoadLibrary", lambda _path: (_ for _ in ()).throw(FileNotFoundError("missing dll")))

    fix_torch.fix_torch_libomp()

    assert (lib / "libomp140.x86_64.dll").read_bytes() == b"runtime"

    (lib / "libomp140.x86_64.dll").write_bytes(b"existing")
    fix_torch.fix_torch_libomp()
    assert (lib / "libomp140.x86_64.dll").read_bytes() == b"existing"
