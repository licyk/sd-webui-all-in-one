import importlib
import importlib.machinery
import importlib.util
import json
import py_compile
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

import pytest
from control_hook_test_helpers import clean_hook_state, write_module

from sd_webui_all_in_one_hotpatcher import PostExecLoader, install_import_hook, monkey_zoo
from sd_webui_all_in_one_hotpatcher.control import PatchOutcomeKind, PatchSet, PatchStatus
from sd_webui_all_in_one_hotpatcher.hook import _is_post_exec_spec

PATCHER_ROOT = Path(__file__).resolve().parents[2]

TARGET_SOURCE = """
def greet(name):
    return f"hello {name}"

LOADED = True
"""


@pytest.fixture(autouse=True)
def clean_state():
    with clean_hook_state():
        yield


def upper_wrapper(func, module):
    def wrapper(name):
        return func(name).upper()

    return wrapper


def write_sourceless_module(directory, name):
    source_path = write_module(directory, name, TARGET_SOURCE)
    compiled = directory / f"{name}.pyc"
    py_compile.compile(str(source_path), cfile=str(compiled), doraise=True)
    source_path.unlink()
    importlib.invalidate_caches()
    return compiled


def outcome_of(handle):
    outcome = handle.last_outcome
    assert outcome is not None
    return outcome


def loader_of(module):
    spec = module.__spec__
    assert spec is not None
    return spec.loader


def test_post_exec_loader_patches_sourceless_pyc(tmp_path):
    write_sourceless_module(tmp_path, "hpc_sourceless")
    sys.path.insert(0, str(tmp_path))
    install_import_hook()
    order = []

    with monkey_zoo("hpc_sourceless") as monkey:
        premodule = monkey.patch_premodule(lambda module: order.append(("pre", hasattr(module, "LOADED"))))
        function = monkey.patch_function("greet", upper_wrapper)
        module_patch = monkey.patch_module(lambda module: order.append(("post", module.LOADED)))
        injection = monkey.inject_import("math", "sqrt")
        source = monkey.patch_sources(lambda text, filename: text)
        bytecode = monkey.patch_bytecode(lambda code: None)

    module = importlib.import_module("hpc_sourceless")

    assert isinstance(loader_of(module), PostExecLoader)
    assert isinstance(loader_of(module).loader, importlib.machinery.SourcelessFileLoader)
    assert module.greet("ada") == "HELLO ADA"
    assert module.sqrt(9) == 3
    assert order == [("pre", False), ("post", True)]
    for handle in (premodule, function, module_patch, injection):
        assert outcome_of(handle).kind is PatchOutcomeKind.APPLIED
    for handle in (source, bytecode):
        assert outcome_of(handle).kind is PatchOutcomeKind.SKIPPED
        assert outcome_of(handle).reason == "unsupported_loader"

    loader = loader_of(module)
    assert loader.get_code("hpc_sourceless") is not None
    assert loader.get_source("hpc_sourceless") is None
    assert loader.is_package("hpc_sourceless") is False
    assert hasattr(loader, "get_resource_reader")
    assert not hasattr(loader, "definitely_missing_attribute")


def test_post_exec_loader_writes_are_revertible(tmp_path):
    write_sourceless_module(tmp_path, "hpc_sourceless_owned")
    sys.path.insert(0, str(tmp_path))
    install_import_hook()
    patch_set = PatchSet("sourceless")
    with patch_set.context.module("hpc_sourceless_owned") as monkey:
        monkey.patch_function("greet", upper_wrapper)

    module = importlib.import_module("hpc_sourceless_owned")
    assert module.greet("ada") == "HELLO ADA"

    report = patch_set.close()

    assert report.handles[0]["status"] == "reverted"
    assert module.greet("ada") == "hello ada"


def test_post_exec_loader_handles_zipimport(tmp_path):
    archive_path = tmp_path / "hpc_archive.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("hpc_zipped.py", textwrap.dedent(TARGET_SOURCE))
    sys.path.insert(0, str(archive_path))
    importlib.invalidate_caches()
    install_import_hook()

    with monkey_zoo("hpc_zipped") as monkey:
        monkey.patch_function("greet", upper_wrapper)
        source = monkey.patch_sources(lambda text, filename: text)

    module = importlib.import_module("hpc_zipped")

    assert isinstance(loader_of(module), PostExecLoader)
    assert module.greet("ada") == "HELLO ADA"
    assert "def greet" in loader_of(module).get_source("hpc_zipped")
    assert outcome_of(source).reason == "unsupported_loader"


def test_spec_from_file_location_wraps_sourceless_file(tmp_path):
    compiled = write_sourceless_module(tmp_path, "hpc_dynamic_pyc_build")
    install_import_hook()
    with monkey_zoo("hpc_dynamic_pyc") as monkey:
        monkey.patch_function("greet", upper_wrapper)

    spec = importlib.util.spec_from_file_location("hpc_dynamic_pyc", compiled)
    assert spec is not None and isinstance(spec.loader, PostExecLoader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.greet("ada") == "HELLO ADA"


def test_post_exec_eligibility_excludes_builtin_frozen_and_namespace(tmp_path):
    (tmp_path / "hpc_namespace_pkg").mkdir()
    sys.path.insert(0, str(tmp_path))
    importlib.invalidate_caches()

    builtin_spec = importlib.util.find_spec("itertools")
    frozen_spec = importlib.util.find_spec("zipimport")
    namespace_spec = importlib.util.find_spec("hpc_namespace_pkg")

    assert builtin_spec is not None and not _is_post_exec_spec(builtin_spec)
    assert frozen_spec is not None and not _is_post_exec_spec(frozen_spec)
    assert namespace_spec is not None and not _is_post_exec_spec(namespace_spec)
    assert not _is_post_exec_spec(importlib.machinery.ModuleSpec("hpc_no_loader", None))


def test_builtin_module_plan_is_not_wrapped():
    finder = install_import_hook()
    with monkey_zoo("hpc_fake_builtin") as monkey:
        monkey.patch_module(lambda module: None)

    spec = importlib.machinery.ModuleSpec("hpc_fake_builtin", importlib.machinery.BuiltinImporter, origin="built-in")  # ty: ignore[invalid-argument-type]
    assert finder._wrap_and_cache("hpc_fake_builtin", spec, monkey) is None
    assert spec.loader is importlib.machinery.BuiltinImporter


def test_reload_after_invalidation_rewraps_without_nesting(tmp_path):
    sys.path.insert(0, str(tmp_path))
    write_module(tmp_path, "hpc_reload", TARGET_SOURCE)
    write_sourceless_module(tmp_path, "hpc_reload_pyc")
    install_import_hook()
    with monkey_zoo("hpc_reload") as monkey:
        monkey.patch_function("greet", upper_wrapper)
    with monkey_zoo("hpc_reload_pyc") as pyc_monkey:
        pyc_handle = pyc_monkey.patch_function("greet", upper_wrapper)

    for name in ("hpc_reload", "hpc_reload_pyc"):
        module = importlib.import_module(name)
        live_spec = module.__spec__
        assert live_spec is not None
        live_loader = live_spec.loader
        monkey_zoo.invalidate(name)
        reloaded = importlib.reload(module)

        assert reloaded.greet("ada") == "HELLO ADA"
        loader = loader_of(reloaded)
        assert type(getattr(loader, "loader")).__name__ in {"SourceFileLoader", "SourcelessFileLoader"}
        # 已导入模块的 spec 被复制后再替换 loader, 原 spec 对象保持不变。
        assert reloaded.__spec__ is not live_spec
        assert live_spec.loader is live_loader

    assert pyc_handle.outcome_counts["applied"] == 2
    assert pyc_monkey.remove(pyc_handle) is PatchStatus.REVERTED


def test_importing_package_and_installing_hook_does_not_load_control():
    script = textwrap.dedent(
        """
        import json
        import sys

        sys.path.insert(0, sys.argv[1])
        import sd_webui_all_in_one_hotpatcher
        after_import = sorted(name for name in sys.modules if name.startswith("sd_webui_all_in_one_hotpatcher.control"))
        sd_webui_all_in_one_hotpatcher.install_import_hook()
        import colorsys  # noqa: F401
        import importlib.util
        importlib.util.spec_from_file_location("hpc_lazy_probe", sys.argv[1] + "/sitecustomize.py")
        after_hook = sorted(name for name in sys.modules if name.startswith("sd_webui_all_in_one_hotpatcher.control"))
        with sd_webui_all_in_one_hotpatcher.monkey_zoo("hpc_lazy_target") as monkey:
            monkey.patch_module(lambda module: None)
        after_register = "sd_webui_all_in_one_hotpatcher.control" in sys.modules
        print(json.dumps([after_import, after_hook, after_register]))
        """
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script, str(PATCHER_ROOT)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    after_import, after_hook, after_register = json.loads(completed.stdout.strip().splitlines()[-1])
    assert after_import == []
    assert after_hook == []
    assert after_register is True
