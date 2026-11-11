"""补丁目标路径解析测试。"""

import importlib
import sys
import textwrap

import pytest

from sd_webui_all_in_one_hotpatcher.control.targets import (
    TargetAttributeError,
    TargetError,
    TargetImportError,
    TargetSyntaxError,
    describe_target,
    parse_target,
    resolve_target,
    split_target,
)

PACKAGE = "hp_control_targets_pkg"


@pytest.fixture(autouse=True)
def target_package(tmp_path):
    package_dir = tmp_path / PACKAGE
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("TOP = 'top'\n", encoding="utf-8")
    (package_dir / "sub.py").write_text(
        textwrap.dedent(
            """
            class Outer:
                class Inner:
                    value = "inner"

                def method(self):
                    return "method"


            FLAG = False
            """
        ),
        encoding="utf-8",
    )
    (package_dir / "broken.py").write_text("import hp_control_targets_missing_dependency\n", encoding="utf-8")
    before_path = list(sys.path)
    sys.path.insert(0, str(tmp_path))
    importlib.invalidate_caches()
    yield
    sys.path[:] = before_path
    for name in list(sys.modules):
        if name == PACKAGE or name.startswith(f"{PACKAGE}."):
            sys.modules.pop(name, None)


def test_parse_target_both_syntaxes():
    assert parse_target("pkg.mod:Obj.attr") == ("pkg.mod", ("Obj", "attr"), True)
    assert parse_target("pkg.mod.Obj.attr") == ("pkg", ("mod", "Obj", "attr"), False)
    assert parse_target("pkg") == ("pkg", (), False)


@pytest.mark.parametrize("path", ["", "  ", "pkg:", ":attr", "a:b:c", "pkg..mod", "pkg.mod:1bad", "pkg-name.mod"])
def test_parse_target_rejects_invalid_paths(path):
    with pytest.raises(TargetSyntaxError) as exc_info:
        parse_target(path)

    assert isinstance(exc_info.value, ValueError)
    assert isinstance(exc_info.value, TargetError)


def test_resolve_colon_and_dotted_syntax_imports_submodule_lazily():
    assert f"{PACKAGE}.sub" not in sys.modules

    explicit = resolve_target(f"{PACKAGE}.sub:Outer.Inner.value")
    assert f"{PACKAGE}.sub" in sys.modules
    dotted = resolve_target(f"{PACKAGE}.sub.Outer.Inner.value")

    assert explicit == dotted == "inner"
    assert resolve_target(f"{PACKAGE}.sub:Outer.Inner") is sys.modules[f"{PACKAGE}.sub"].Outer.Inner


def test_dotted_syntax_falls_back_to_import_for_unloaded_submodule():
    module = resolve_target(f"{PACKAGE}.sub")

    assert module is sys.modules[f"{PACKAGE}.sub"]
    assert resolve_target(PACKAGE).TOP == "top"


def test_colon_syntax_falls_back_to_import_for_submodule_attribute():
    assert resolve_target(f"{PACKAGE}:sub.FLAG") is False


def test_split_target_returns_owner_and_name():
    owner, name = split_target(f"{PACKAGE}.sub:Outer.Inner.value")
    assert owner is resolve_target(f"{PACKAGE}.sub:Outer.Inner")
    assert name == "value"

    owner, name = split_target(f"{PACKAGE}.sub.FLAG")
    assert owner is sys.modules[f"{PACKAGE}.sub"]
    assert name == "FLAG"

    owner, name = split_target(f"{PACKAGE}.sub:NEW_NAME")
    assert name == "NEW_NAME"


def test_split_target_requires_attribute_segment():
    with pytest.raises(TargetSyntaxError):
        split_target(PACKAGE)


def test_split_target_raising_checks_attribute():
    with pytest.raises(TargetAttributeError, match="NEW_NAME"):
        split_target(f"{PACKAGE}.sub:NEW_NAME", raising=True)


@pytest.mark.parametrize("path", ["hp_control_targets_no_such_module:attr", "hp_control_targets_no_such_module.attr"])
def test_missing_module_raises_import_error_with_context(path):
    with pytest.raises(TargetImportError) as exc_info:
        resolve_target(path)

    error = exc_info.value
    assert isinstance(error, ImportError)
    assert "hp_control_targets_no_such_module" in str(error)
    assert path in str(error)
    assert error.target == path


@pytest.mark.parametrize(
    "path",
    [
        f"{PACKAGE}.sub:Outer.missing",
        f"{PACKAGE}.sub.Outer.missing",
        f"{PACKAGE}:missing",
        f"{PACKAGE}.missing",
        f"{PACKAGE}.missing.deeper",
    ],
)
def test_missing_attribute_raises_attribute_error_with_context(path):
    with pytest.raises(TargetAttributeError) as exc_info:
        resolve_target(path)

    error = exc_info.value
    assert isinstance(error, AttributeError)
    assert "missing" in str(error)
    assert path in str(error)
    assert error.target == path


def test_missing_module_inside_colon_module_part():
    with pytest.raises(TargetImportError, match="not found"):
        resolve_target(f"{PACKAGE}.missing:attr")


def test_import_error_inside_existing_module_is_not_reported_as_missing_attribute():
    with pytest.raises(TargetImportError, match="import error"):
        resolve_target(f"{PACKAGE}.broken")
    with pytest.raises(TargetImportError, match="import error"):
        resolve_target(f"{PACKAGE}.broken:anything")


def test_describe_target():
    module = resolve_target(f"{PACKAGE}.sub")

    assert describe_target(module) == f"{PACKAGE}.sub"
    assert describe_target(module.Outer, "method") == f"{PACKAGE}.sub.Outer.method"
    assert describe_target(module.Outer()) == "<Outer object>"
