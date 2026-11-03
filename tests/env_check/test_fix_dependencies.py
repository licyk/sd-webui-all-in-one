"""Python 依赖检查与修复测试"""

import importlib

import pytest

fix_dependencies = importlib.import_module("sd_webui_all_in_one.env_check.fix_dependencies")


fix_dependencies_requirements = importlib.import_module("sd_webui_all_in_one.env_check.fix_dependencies.requirements")


fix_dependencies_metadata = importlib.import_module("sd_webui_all_in_one.env_check.fix_dependencies.metadata")


fix_dependencies_broken = importlib.import_module("sd_webui_all_in_one.env_check.fix_dependencies.broken")


installed_module = importlib.import_module("sd_webui_all_in_one.package_analyzer.installed")


def test_py_dependency_checker_installs_missing_and_wraps(monkeypatch, tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("demo\n", encoding="utf-8")
    calls = []

    monkeypatch.setattr(fix_dependencies_requirements, "repair_broken_distributions", lambda **kwargs: calls.append(("repair", kwargs)))
    monkeypatch.setattr(fix_dependencies_requirements, "validate_requirements", lambda path: calls.append(("validate", path)) or False)
    monkeypatch.setattr(fix_dependencies_requirements, "install_requirements", lambda **kwargs: calls.append(("install", kwargs)))

    fix_dependencies.py_dependency_checker(req, use_uv=False, custom_env={"A": "B"})

    assert calls == [
        ("repair", {"use_uv": False, "custom_env": {"A": "B"}}),
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


@pytest.fixture
def broken_site(tmp_path, monkeypatch):
    """把扫描与查找都限定在临时 site-packages 目录, 返回创建分发的函数"""
    site_dir = tmp_path / "site-packages"
    site_dir.mkdir()
    monkeypatch.syspath_prepend(str(site_dir))
    monkeypatch.setattr(installed_module, "_site_packages_paths", lambda: [str(site_dir)])

    def make(name, version, metadata=None):
        dist_info = site_dir / f"{name}-{version}.dist-info"
        dist_info.mkdir()
        if metadata is not None:
            (dist_info / "METADATA").write_text(metadata, encoding="utf-8")
        return dist_info

    return make


def test_repair_broken_distributions_removes_metadata_and_reinstalls_same_version(monkeypatch, broken_site):
    calls = []
    monkeypatch.setattr(fix_dependencies_broken, "pip_install", lambda *args, **kwargs: calls.append((args, kwargs)))
    missing = broken_site("sdaio_numpy", "2.2.6")
    empty = broken_site("sdaio_other", "1.0", metadata="")

    fix_dependencies.repair_broken_distributions(use_uv=False, custom_env={"A": "B"})

    assert not missing.exists() and not empty.exists()
    assert calls == [(("sdaio_numpy==2.2.6", "sdaio_other==1.0", "--no-deps"), {"use_uv": False, "custom_env": {"A": "B"}})]


def test_repair_broken_distributions_only_removes_stale_metadata_when_valid_copy_exists(monkeypatch, broken_site):
    calls = []
    monkeypatch.setattr(fix_dependencies_broken, "pip_install", lambda *args, **kwargs: calls.append((args, kwargs)))
    stale = broken_site("sdaio_numpy", "2.2.6", metadata="Metadata-Version: 2.1\nName: sdaio-numpy\n")
    valid = broken_site("sdaio_numpy", "2.4.6", metadata="Metadata-Version: 2.1\nName: sdaio-numpy\nVersion: 2.4.6\n")

    fix_dependencies.repair_broken_distributions()

    assert not stale.exists() and valid.exists()
    assert calls == []


def test_repair_broken_distributions_does_nothing_for_healthy_environment(monkeypatch, broken_site):
    monkeypatch.setattr(fix_dependencies_broken, "pip_install", lambda *_args, **_kwargs: pytest.fail("should not install"))
    healthy = broken_site("sdaio_fine", "1.0", metadata="Metadata-Version: 2.1\nName: sdaio-fine\nVersion: 1.0\n")

    fix_dependencies.repair_broken_distributions()

    assert healthy.exists()


def test_repair_broken_distributions_wraps_install_error(monkeypatch, broken_site):
    monkeypatch.setattr(fix_dependencies_broken, "pip_install", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("pip bad")))
    broken_site("sdaio_numpy", "2.2.6")

    with pytest.raises(RuntimeError, match="sdaio_numpy==2.2.6.*pip bad"):
        fix_dependencies.repair_broken_distributions()
