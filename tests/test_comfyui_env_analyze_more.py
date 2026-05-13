import os
from pathlib import Path

import pytest

from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.env_check import comfyui_env_analyze as analyzer


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
    monkeypatch.setattr(analyzer, "is_package_installed", lambda package: "missing-pkg" not in package)
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
        (comfyui / "requirements.txt").as_posix(),
        (enabled / "requirements.txt").as_posix(),
        ]
    )
    assert analyzer.statistical_has_conflict_component(env_data, ["shared", "Shared"]) == "shared:\n - ComfyUI: shared<1\n - enabled: shared==1.0"


def test_process_comfyui_env_analysis_detects_conflicts_and_missing_paths(monkeypatch, tmp_path):
    comfyui = tmp_path / "ComfyUI"
    node = comfyui / "custom_nodes" / "node"
    node.mkdir(parents=True)
    (comfyui / "requirements.txt").write_text("numpy<2\n", encoding="utf-8")
    (node / "requirements.txt").write_text("numpy>=2\n", encoding="utf-8")
    monkeypatch.setattr(analyzer, "is_package_installed", lambda _package: True)

    env_data, req_list, conflict_info = analyzer.process_comfyui_env_analysis(comfyui)

    assert env_data["ComfyUI"]["has_conflict_requires"] is True
    assert env_data["node"]["has_conflict_requires"] is True
    assert req_list == [(comfyui / "requirements.txt").as_posix(), (node / "requirements.txt").as_posix()]
    assert "ComfyUI: numpy<2" in conflict_info
    assert "node: numpy>=2" in conflict_info

    with pytest.raises(FileNotFoundError):
        analyzer.process_comfyui_env_analysis(tmp_path / "missing")


def test_comfyui_conflict_analyzer_installs_needed_requirements_and_aggregates(monkeypatch, tmp_path):
    node_a = tmp_path / "custom_nodes" / "node-a"
    node_b = tmp_path / "custom_nodes" / "node-b"
    for node in [node_a, node_b]:
        node.mkdir(parents=True)
        (node / "requirements.txt").write_text("demo\n", encoding="utf-8")

    reqs = [(node_a / "requirements.txt").as_posix(), (node_b / "requirements.txt").as_posix()]
    calls = []
    monkeypatch.setattr(analyzer, "process_comfyui_env_analysis", lambda _path: ({}, reqs, "demo\n - node-a: demo<1\n - node-b: demo>=2"))

    def fake_install_requirements(path, use_uv, cwd, custom_env):
        calls.append((path, use_uv, cwd, custom_env))
        if path == node_b / "requirements.txt":
            raise RuntimeError("install bad")

    monkeypatch.setattr(analyzer, "install_requirements", fake_install_requirements)

    with pytest.raises(AggregateError) as exc:
        analyzer.comfyui_conflict_analyzer(
            tmp_path,
            install_conflict_component_requirement=True,
            use_uv=False,
            custom_env={"PYTHONPATH": "old"},
        )

    assert len(exc.value.exceptions) == 1
    assert calls[0][0] == node_a / "requirements.txt"
    assert calls[0][1] is False
    assert calls[0][2] == node_a
    assert calls[0][3]["PYTHONPATH"].split(os.pathsep)[0] == tmp_path.as_posix()
    assert calls[1][0] == node_b / "requirements.txt"

    calls.clear()
    monkeypatch.setattr(analyzer, "process_comfyui_env_analysis", lambda _path: ({}, [], "conflict"))
    analyzer.comfyui_conflict_analyzer(tmp_path, install_conflict_component_requirement=False)
    assert calls == []


def test_check_comfyui_manager_dependence_installs_only_when_needed(monkeypatch, tmp_path):
    calls = []

    analyzer.check_comfyui_manager_dependence(tmp_path)
    assert calls == []

    req = tmp_path / "manager_requirements.txt"
    req.write_text("demo\n", encoding="utf-8")
    monkeypatch.setattr(analyzer, "validate_requirements", lambda path: calls.append(("validate", path)) or True)
    monkeypatch.setattr(analyzer, "install_requirements", lambda **kwargs: calls.append(("install", kwargs)))

    analyzer.check_comfyui_manager_dependence(tmp_path, use_uv=False, custom_env={"A": "B"})
    assert calls == [("validate", req)]

    calls.clear()
    monkeypatch.setattr(analyzer, "validate_requirements", lambda path: calls.append(("validate", path)) or False)
    analyzer.check_comfyui_manager_dependence(tmp_path, use_uv=False, custom_env={"A": "B"})
    assert calls == [
        ("validate", req),
        ("install", {"path": req, "use_uv": False, "custom_env": {"A": "B"}, "cwd": tmp_path}),
    ]

    monkeypatch.setattr(analyzer, "install_requirements", lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("pip bad")))
    with pytest.raises(RuntimeError, match="pip bad"):
        analyzer.check_comfyui_manager_dependence(tmp_path)
