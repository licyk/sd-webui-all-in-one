import importlib.metadata

import pytest

from sd_webui_all_in_one.package_analyzer import dependency_categorizer
from sd_webui_all_in_one.package_analyzer import installation_checker
from sd_webui_all_in_one.package_analyzer.requirement_normalizer import parse_requirement_list


def test_parse_requirement_list_handles_sources_constraints_and_skips():
    requirements = [
        "Torch==2.3.0",
        "diffusers[torch]==0.10.2",
        "protobuf<5,>=4.25.3",
        "git+https://github.com/user/Repo-Name.git",
        "-e git+https://github.com/user/pkg.git@main#egg=Pkg-Extra",
        "git+ssh://git@github.com:user/sshrepo.git@main",
        "https://example.test/packages/demo_pkg-1.2.3-py3-none-any.whl",
        "http://example.test/packages/BadName-0.1.0-cp311-cp311-manylinux.whl",
        "invalid !!!",
        "foo==not_canonical",
        "bar===custom build",
        "--index-url https://pypi.example/simple",
        "--extra-index-url https://extra.example/simple",
        "--find-links https://wheels.example",
        "-r requirements.txt",
        "-e .",
        "# comment",
        "",
    ]

    assert parse_requirement_list(requirements) == [
        "torch==2.3.0",
        "diffusers==0.10.2",
        "protobuf<5",
        "protobuf>=4.25.3",
        "repo-name",
        "pkg",
        "sshrepo",
        "demo_pkg==1.2.3",
        "badname==0.1.0",
    ]


def test_parse_requirement_list_extracts_repo_name_fallbacks():
    assert parse_requirement_list(
        [
            "git+https://gitlab.example/group/subgroup/fancy-package.git@main",
            "-e git+ssh://git@git.example:owner/ssh-package.git",
        ]
    ) == ["fancy-package", "ssh-package"]


def test_dependency_categorizer_formats_and_groups_markers(monkeypatch, capsys):
    monkeypatch.setattr(
        dependency_categorizer,
        "requires",
        lambda _name: [
            "core>=1.0",
            "gpu-extra>=2.0 ; extra == 'gpu'",
            "skip-me>=1.0 ; python_version < '0'",
            "bad requirement !!!",
        ],
    )
    monkeypatch.setattr(dependency_categorizer, "get_parse_bindings", lambda: "bindings")

    def fake_parse_requirement(req, _bindings):
        if req.startswith("core"):
            return "core", [], [(">=", "1.0")], None
        if req.startswith("gpu-extra"):
            return "gpu-extra", [], [(">=", "2.0")], ["extra", "==", "gpu"]
        if req.startswith("skip-me"):
            return "skip-me", [], [(">=", "1.0")], ["python_version", "<", "0"]
        raise ValueError("bad")

    monkeypatch.setattr(dependency_categorizer, "parse_requirement", fake_parse_requirement)
    monkeypatch.setattr(dependency_categorizer, "evaluate_marker", lambda marker: marker is None)

    deps = dependency_categorizer.get_categorized_dependencies("demo")

    assert deps == {"mandatory": ["core>=1.0"], "optional": {"gpu": ["gpu-extra>=2.0"]}}
    assert "解析依赖" in capsys.readouterr().out


def test_installation_checker_package_versions_specs_and_validation(monkeypatch, tmp_path):
    versions = {
        "Demo_Pkg": None,
        "demo_pkg": None,
        "Demo-Pkg": "1.2.3",
        "demo-pkg": "1.2.3",
        "missing": None,
    }

    def fake_version(name):
        value = versions.get(name)
        if value is None:
            raise importlib.metadata.PackageNotFoundError(name)
        return value

    monkeypatch.setattr(installation_checker.importlib.metadata, "version", fake_version)
    assert installation_checker.get_package_version_from_library("Demo_Pkg") == "1.2.3"
    assert installation_checker.get_package_version_from_library("missing") is None

    assert installation_checker.parse_package_spec("demo>=1.0,<2.0") == ("demo", [(">=", "1.0"), ("<", "2.0")], False)
    assert installation_checker.parse_package_spec("demo @ https://example.test/demo.whl") == (
        "demo",
        [("@", "https://example.test/demo.whl")],
        True,
    )
    assert installation_checker._split_package_spec("demo~=1.4") == ("demo", "~=", "1.4")

    installed = {
        "ok": "1.4.2",
        "bad": "1.0.0",
        "wild": "2.1.5+local",
    }
    monkeypatch.setattr(installation_checker, "get_package_version_from_library", lambda name: installed.get(name))
    assert installation_checker.is_package_installed("ok~=1.4") is True
    assert installation_checker.is_package_installed("bad>=2.0") is False
    assert installation_checker.is_package_installed("wild==2.1.*") is True
    assert installation_checker.is_package_installed("missing") is False

    req = tmp_path / "requirements.txt"
    req.write_text("ok~=1.4\nbad>=2.0\n", encoding="utf-8")
    assert installation_checker.validate_requirements(req) is False

    req.write_text("ok~=1.4\nwild==2.1.*\n", encoding="utf-8")
    assert installation_checker.validate_requirements(req) is True
