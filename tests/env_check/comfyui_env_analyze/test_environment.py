"""ComfyUI 环境依赖分析测试"""

import pytest

from sd_webui_all_in_one.env_check import comfyui_env_analyze as analyzer
from sd_webui_all_in_one.env_check.comfyui_env_analyze import checks as analyzer_checks
from sd_webui_all_in_one.env_check.comfyui_env_analyze import environment as analyzer_environment


def test_comfyui_environment_dict_updates_missing_and_conflict_lists(monkeypatch, tmp_path):
    comfyui = tmp_path / "ComfyUI"
    custom_nodes = comfyui / "custom_nodes"
    enabled = custom_nodes / "enabled"
    disabled = custom_nodes / "disabled.disabled"
    file_node = custom_nodes / "file.py"
    for path in [enabled, disabled]:
        path.mkdir(parents=True)
        (path / "requirements.txt").write_text("shared==1.0\nmissing-pkg>=2\n", encoding="utf-8")
    (comfyui / "requirements.txt").write_text("base-pkg==1.0\nshared<1\n", encoding="utf-8")
    file_node.write_text("pass", encoding="utf-8")

    env_data = analyzer.create_comfyui_environment_dict(comfyui)
    analyzer.update_comfyui_component_requires_list(env_data)
    monkeypatch.setattr(analyzer_environment, "is_package_installed", lambda package: "missing-pkg" not in package)
    monkeypatch.setattr(analyzer_checks, "is_package_installed", lambda package: "missing-pkg" not in package)
    analyzer.update_comfyui_component_missing_requires_list(env_data)
    analyzer.update_comfyui_component_conflict_requires_list(env_data, ["shared"])

    assert sorted(env_data) == ["ComfyUI", "disabled.disabled", "enabled"]
    assert env_data["disabled.disabled"]["is_disabled"] is True
    assert env_data["disabled.disabled"]["requires"] == []
    assert env_data["enabled"]["missing_requires"] == ["missing-pkg>=2"]
    assert env_data["ComfyUI"]["conflict_requires"] == ["shared<1"]
    assert sorted(analyzer.get_comfyui_component_requires_list(env_data)) == sorted(["base-pkg==1.0", "shared<1", "shared==1.0", "missing-pkg>=2"])
    assert sorted(analyzer.statistical_need_install_require_component(env_data)) == sorted(
        [
            comfyui / "requirements.txt",
            enabled / "requirements.txt",
        ]
    )
    assert analyzer.collect_conflict_components(env_data, ["shared", "Shared"]) == [
        {
            "package": "shared",
            "components": [
                {"component": "ComfyUI", "component_type": "core", "requirement": "shared<1"},
                {"component": "enabled", "component_type": "extension", "requirement": "shared==1.0"},
            ],
        }
    ]


def test_process_comfyui_env_analysis_detects_conflicts_and_missing_paths(monkeypatch, tmp_path):
    comfyui = tmp_path / "ComfyUI"
    node = comfyui / "custom_nodes" / "node"
    node.mkdir(parents=True)
    (comfyui / "requirements.txt").write_text("numpy<2\n", encoding="utf-8")
    (node / "requirements.txt").write_text("numpy>=2\n", encoding="utf-8")
    monkeypatch.setattr(analyzer_environment, "is_package_installed", lambda _package: True)
    monkeypatch.setattr(analyzer_checks, "is_package_installed", lambda _package: True)

    env_data, req_list, conflicts = analyzer.process_comfyui_env_analysis(comfyui)

    assert env_data["ComfyUI"]["has_conflict_requires"] is True
    assert env_data["node"]["has_conflict_requires"] is True
    assert req_list == [comfyui / "requirements.txt", node / "requirements.txt"]
    conflict_info = analyzer.format_conflict_info(conflicts)
    assert "ComfyUI (core): numpy<2" in conflict_info
    assert "node (extension): numpy>=2" in conflict_info

    with pytest.raises(FileNotFoundError):
        analyzer.process_comfyui_env_analysis(tmp_path / "missing")


def test_check_comfyui_component_dependencies_returns_structured_result(monkeypatch, tmp_path):
    comfyui = tmp_path / "ComfyUI"
    node = comfyui / "custom_nodes" / "node"
    node.mkdir(parents=True)
    (comfyui / "requirements.txt").write_text("numpy<2\n", encoding="utf-8")
    (node / "requirements.txt").write_text("numpy>=2\nmissing-demo\n", encoding="utf-8")
    monkeypatch.setattr(analyzer_environment, "is_package_installed", lambda package: package != "missing-demo")
    monkeypatch.setattr(analyzer_checks, "is_package_installed", lambda package: package != "missing-demo")

    result = analyzer.check_comfyui_component_dependencies(comfyui)

    assert result["has_missing_requires"] is True
    assert result["has_conflict_requires"] is True
    assert result["requirement_paths"] == [comfyui / "requirements.txt", node / "requirements.txt"]
    assert result["components"]["node"]["missing_requires"] == ["missing-demo"]
    assert " - node (extension): numpy>=2" in result["conflict_info"]
    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0]["package"] == "numpy"


def test_check_comfyui_manager_dependence_installs_only_when_needed(monkeypatch, tmp_path):
    calls = []

    analyzer.check_comfyui_manager_dependence(tmp_path)
    assert calls == []

    req = tmp_path / "manager_requirements.txt"
    req.write_text("demo\n", encoding="utf-8")
    monkeypatch.setattr(analyzer_checks, "validate_requirements", lambda path: calls.append(("validate", path)) or True)
    monkeypatch.setattr(analyzer_checks, "install_requirements", lambda **kwargs: calls.append(("install", kwargs)))

    analyzer.check_comfyui_manager_dependence(tmp_path, use_uv=False, custom_env={"A": "B"})
    assert calls == [("validate", req)]

    calls.clear()
    monkeypatch.setattr(analyzer_checks, "validate_requirements", lambda path: calls.append(("validate", path)) or False)
    analyzer.check_comfyui_manager_dependence(tmp_path, use_uv=False, custom_env={"A": "B"})
    assert calls == [
        ("validate", req),
        ("install", {"path": req, "use_uv": False, "custom_env": {"A": "B"}, "cwd": tmp_path}),
    ]

    monkeypatch.setattr(analyzer_checks, "install_requirements", lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("pip bad")))
    with pytest.raises(RuntimeError, match="pip bad"):
        analyzer.check_comfyui_manager_dependence(tmp_path)


def test_comfyui_requires_list_skips_unreadable_requirement_file(tmp_path):
    comfyui = tmp_path / "ComfyUI"
    broken = comfyui / "custom_nodes" / "broken"
    broken.mkdir(parents=True)
    (comfyui / "requirements.txt").write_text("base-pkg==1.0\n", encoding="utf-8")
    (broken / "requirements.txt").write_bytes(b"\xff\xfe\x00invalid")

    env_data = analyzer.create_comfyui_environment_dict(comfyui)
    analyzer.update_comfyui_component_requires_list(env_data)

    assert env_data["ComfyUI"]["requires"] == ["base-pkg==1.0"]
    assert env_data["broken"]["requires"] == []
