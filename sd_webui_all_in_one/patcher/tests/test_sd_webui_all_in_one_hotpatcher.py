import importlib
import sys
import textwrap

import pytest

from sd_webui_all_in_one_hotpatcher import install_import_hook, monkey_zoo, uninstall_import_hook


@pytest.fixture(autouse=True)
def clean_import_state():
    uninstall_import_hook()
    monkey_zoo.clear()
    before_path = list(sys.path)
    yield
    uninstall_import_hook()
    monkey_zoo.clear()
    sys.path[:] = before_path
    for name in list(sys.modules):
        if name.startswith("hp_target_") or name in {"hp_missing_alias", "hp_real_alias"}:
            sys.modules.pop(name, None)


@pytest.fixture
def module_dir(tmp_path):
    sys.path.insert(0, str(tmp_path))
    return tmp_path


def write_module(module_dir, name, source):
    path = module_dir / f"{name}.py"
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    importlib.invalidate_caches()
    return path


def test_patch_function_wraps_target_function(module_dir):
    write_module(
        module_dir,
        "hp_target_function",
        """
        def greet(name):
            return f"hello {name}"
        """,
    )

    install_import_hook()
    with monkey_zoo("hp_target_function") as monkey:

        def patch_greet(func, module):
            def wrapper(name):
                return func(name).upper()

            return wrapper

        monkey.patch_function("greet", patch_greet)

    module = importlib.import_module("hp_target_function")

    assert module.greet("ada") == "HELLO ADA"


def test_patch_module_runs_after_module_execution(module_dir):
    write_module(module_dir, "hp_target_module", "VALUE = 1\n")

    install_import_hook()
    with monkey_zoo("hp_target_module") as monkey:

        def patch_module(module):
            module.EXTRA = module.VALUE + 1

        monkey.patch_module(patch_module)

    module = importlib.import_module("hp_target_module")

    assert module.EXTRA == 2


def test_patch_sources_rewrites_source_before_execution(module_dir):
    write_module(module_dir, "hp_target_source", 'VALUE = "before"\n')

    install_import_hook()
    with monkey_zoo("hp_target_source") as monkey:

        def patch_source(source, filename):
            return source.replace('"before"', '"after"')

        monkey.patch_sources(patch_source)

    module = importlib.import_module("hp_target_source")

    assert module.VALUE == "after"


def test_patch_bytecode_rewrites_module_constant(module_dir):
    write_module(module_dir, "hp_target_bytecode", 'VALUE = "old"\n')

    install_import_hook()
    with monkey_zoo("hp_target_bytecode") as monkey:

        def patch_bytecode(code):
            code.co_consts.replace_primitive("old", "new")

        monkey.patch_bytecode(patch_bytecode)

    module = importlib.import_module("hp_target_bytecode")

    assert module.VALUE == "new"


def test_inject_import_adds_name_before_module_execution(module_dir):
    write_module(module_dir, "hp_target_injection", "RESULT = sqrt(9)\n")

    install_import_hook()
    with monkey_zoo("hp_target_injection") as monkey:
        monkey.inject_import("math", "sqrt")

    module = importlib.import_module("hp_target_injection")

    assert module.RESULT == 3


def test_alias_if_not_exists_falls_back_to_alias_module(module_dir):
    write_module(module_dir, "hp_real_alias", "VALUE = 42\n")

    install_import_hook()
    monkey_zoo.alias_if_not_exists("hp_missing_alias", "hp_real_alias")

    module = importlib.import_module("hp_missing_alias")

    assert module.VALUE == 42
    assert module is sys.modules["hp_real_alias"]


def test_spec_from_file_location_applies_registered_patch(tmp_path):
    module_path = tmp_path / "dynamic_target.py"
    module_path.write_text('VALUE = "before"\n', encoding="utf-8")

    install_import_hook()
    with monkey_zoo("hp_target_dynamic") as monkey:

        def patch_source(source, filename):
            return source.replace('"before"', '"after"')

        monkey.patch_sources(patch_source)

    spec = importlib.util.spec_from_file_location("hp_target_dynamic", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert module.VALUE == "after"


def test_install_and_uninstall_are_idempotent():
    original_spec_from_file_location = importlib.util.spec_from_file_location

    finder = install_import_hook()
    assert install_import_hook() is finder
    assert sys.meta_path.count(finder) == 1
    assert importlib.util.spec_from_file_location is not original_spec_from_file_location

    uninstall_import_hook()
    assert finder not in sys.meta_path
    assert importlib.util.spec_from_file_location is original_spec_from_file_location
