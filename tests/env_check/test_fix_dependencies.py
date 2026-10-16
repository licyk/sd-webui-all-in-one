"""Python 依赖检查与修复测试"""

import importlib

import pytest

fix_dependencies = importlib.import_module("sd_webui_all_in_one.env_check.fix_dependencies")


fix_dependencies_requirements = importlib.import_module("sd_webui_all_in_one.env_check.fix_dependencies.requirements")


fix_dependencies_metadata = importlib.import_module("sd_webui_all_in_one.env_check.fix_dependencies.metadata")


def test_py_dependency_checker_installs_missing_and_wraps(monkeypatch, tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("demo\n", encoding="utf-8")
    calls = []

    monkeypatch.setattr(fix_dependencies_requirements, "validate_requirements", lambda path: calls.append(("validate", path)) or False)
    monkeypatch.setattr(fix_dependencies_requirements, "install_requirements", lambda **kwargs: calls.append(("install", kwargs)))

    fix_dependencies.py_dependency_checker(req, use_uv=False, custom_env={"A": "B"})

    assert calls == [
        ("validate", req),
        ("install", {"path": req, "use_uv": False, "cwd": tmp_path, "custom_env": {"A": "B"}}),
    ]

    monkeypatch.setattr(fix_dependencies_requirements, "install_requirements", lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("pip bad")))
    with pytest.raises(RuntimeError, match="pip bad"):
        fix_dependencies.py_dependency_checker(req)

    with pytest.raises(FileNotFoundError):
        fix_dependencies.py_dependency_checker(tmp_path / "missing.txt")


def test_py_package_metadata_dependency_checker_installs_only_missing(monkeypatch):
    calls = []
    monkeypatch.setattr(fix_dependencies_metadata, "get_missing_package_metadata_dependencies", lambda package_name: calls.append(("missing", package_name)) or [])
    monkeypatch.setattr(fix_dependencies_metadata, "pip_install", lambda *args, **kwargs: calls.append(("pip", args, kwargs)))

    fix_dependencies.py_package_metadata_dependency_checker("demo[gpu]", name="Demo")

    assert calls == [("missing", "demo[gpu]")]

    calls.clear()
    monkeypatch.setattr(
        fix_dependencies_metadata,
        "get_missing_package_metadata_dependencies",
        lambda package_name: calls.append(("missing", package_name)) or ["dep>=1.0", "pkg[extra]>=2.0"],
    )

    fix_dependencies.py_package_metadata_dependency_checker("demo[gpu]", name="Demo", use_uv=False, custom_env={"A": "B"})

    assert calls == [
        ("missing", "demo[gpu]"),
        ("pip", ("dep>=1.0", "pkg[extra]>=2.0"), {"use_uv": False, "custom_env": {"A": "B"}}),
    ]


def test_py_package_metadata_dependency_checker_wraps_install_error(monkeypatch):
    monkeypatch.setattr(fix_dependencies_metadata, "get_missing_package_metadata_dependencies", lambda _package_name: ["dep>=1.0"])
    monkeypatch.setattr(fix_dependencies_metadata, "pip_install", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("pip bad")))

    with pytest.raises(RuntimeError, match="pip bad"):
        fix_dependencies.py_package_metadata_dependency_checker("demo")
