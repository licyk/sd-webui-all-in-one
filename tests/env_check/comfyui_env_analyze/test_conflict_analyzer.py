"""ComfyUI 冲突分析器安装与禁用流程测试"""

import os
import sys
from pathlib import Path

import pytest

from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.env_check import comfyui_env_analyze as analyzer
from sd_webui_all_in_one.env_check.comfyui_env_analyze import actions as analyzer_actions
from sd_webui_all_in_one.env_check.comfyui_env_analyze import checks as analyzer_checks
from sd_webui_all_in_one.env_check.comfyui_env_analyze import environment as analyzer_environment
from tests.env_check.comfyui_env_analyze.helpers import make_comfyui


def _rename_disable(comfyui: Path, calls: list[str]):
    def disable(name: str) -> None:
        calls.append(name)
        path = comfyui / "custom_nodes" / name
        path.rename(path.with_name(f"{name}.disabled"))

    return disable


# ============================================================================
# check_comfyui_component_dependencies
# ============================================================================
def test_check_dependencies_includes_resolution_and_prefers_installed(monkeypatch, tmp_path):
    comfyui = make_comfyui(tmp_path, "torch\n", {"a": "numpy<2\n", "b": "numpy>=2\n"})
    monkeypatch.setattr(analyzer_environment, "is_package_installed", lambda package: package != "numpy<2")
    monkeypatch.setattr(analyzer_checks, "is_package_installed", lambda package: package != "numpy<2")

    result = analyzer.check_comfyui_component_dependencies(comfyui)

    assert result["conflict_resolution"]["disable_components"] == ["a"]
    assert result["conflict_resolution"]["keep_components"] == ["b"]


def test_disabling_resolution_clears_conflicts_on_reanalysis(monkeypatch, tmp_path):
    comfyui = make_comfyui(
        tmp_path,
        "numpy>=1.25\n",
        {"old": "numpy<1.24\n", "ok": "numpy>=1.20\n", "x": "protobuf<4\n", "z": "protobuf>=4\n", "w": "protobuf>=4\n"},
    )
    monkeypatch.setattr(analyzer_environment, "is_package_installed", lambda _package: True)
    monkeypatch.setattr(analyzer_checks, "is_package_installed", lambda _package: True)

    resolution = analyzer.check_comfyui_component_dependencies(comfyui)["conflict_resolution"]
    for name in resolution["disable_components"]:
        _rename_disable(comfyui, [])(name)

    assert resolution["disable_components"] == ["old", "x"]
    assert analyzer.check_comfyui_component_dependencies(comfyui)["has_conflict_requires"] is False


# ============================================================================
# comfyui_conflict_analyzer
# ============================================================================
@pytest.fixture
def install_calls(monkeypatch):
    calls: list = []
    monkeypatch.setattr(analyzer_environment, "is_package_installed", lambda _package: False)
    monkeypatch.setattr(analyzer_checks, "is_package_installed", lambda _package: False)
    monkeypatch.setattr(analyzer_actions, "install_requirements", lambda path, use_uv, cwd, custom_env: calls.append(path))
    return calls


def test_analyzer_disables_conflicts_then_batch_installs(install_calls, tmp_path):
    comfyui = make_comfyui(tmp_path, "torch\n", {"a": "numpy>=2\n", "b": "numpy>=2.1\n", "outlier": "numpy<2\n"})
    disabled: list[str] = []

    analyzer.comfyui_conflict_analyzer(comfyui, disable_conflict_component=True, use_uv=False, disable_component_callback=_rename_disable(comfyui, disabled))

    assert disabled == ["outlier"]
    assert (comfyui / "custom_nodes" / "outlier.disabled").is_dir()
    assert len(install_calls) == 1
    assert isinstance(install_calls[0], list)
    assert sorted(path.parent.name for path in install_calls[0]) == ["ComfyUI", "a", "b"]


def test_analyzer_disable_takes_precedence_over_install(install_calls, tmp_path):
    comfyui = make_comfyui(tmp_path, "torch\n", {"a": "numpy>=2\n", "outlier": "numpy<2\n", "b": "numpy>=2\n"})
    disabled: list[str] = []

    analyzer.comfyui_conflict_analyzer(
        comfyui,
        install_conflict_component_requirement=True,
        disable_conflict_component=True,
        use_uv=False,
        disable_component_callback=_rename_disable(comfyui, disabled),
    )

    assert disabled == ["outlier"]
    assert isinstance(install_calls[0], list)


def test_analyzer_falls_back_to_sequential_install_when_conflicts_remain(install_calls, tmp_path):
    comfyui = make_comfyui(tmp_path, "numpy<1.20\nnumpy>=1.26\n", {"a": "numpy>=1.26\n", "b": "numpy<1.20\n"})
    disabled: list[str] = []

    analyzer.comfyui_conflict_analyzer(
        comfyui,
        install_conflict_component_requirement=True,
        disable_conflict_component=True,
        use_uv=False,
        disable_component_callback=_rename_disable(comfyui, disabled),
    )

    assert disabled == ["a", "b"]
    assert install_calls == [(comfyui / "requirements.txt").resolve()]


def test_analyzer_skips_when_conflicts_remain_without_install_flag(install_calls, tmp_path):
    comfyui = make_comfyui(tmp_path, "numpy<1.20\nnumpy>=1.26\n", {"a": "numpy>=1.26\n"})

    analyzer.comfyui_conflict_analyzer(comfyui, disable_conflict_component=True, use_uv=False, disable_component_callback=_rename_disable(comfyui, []))

    assert install_calls == []


def test_analyzer_disable_flag_without_candidates_uses_install_flag(install_calls, tmp_path):
    comfyui = make_comfyui(tmp_path, "numpy<1.20\nnumpy>=1.26\n", {})
    disabled: list[str] = []

    analyzer.comfyui_conflict_analyzer(
        comfyui,
        install_conflict_component_requirement=True,
        disable_conflict_component=True,
        use_uv=False,
        disable_component_callback=_rename_disable(comfyui, disabled),
    )

    assert disabled == []
    assert install_calls == [(comfyui / "requirements.txt").resolve()]


def test_analyzer_aggregates_disable_errors(install_calls, tmp_path):
    comfyui = make_comfyui(tmp_path, "torch\n", {"a": "numpy>=2\n", "b": "numpy>=2\n", "outlier": "numpy<2\n"})

    def failing_disable(_name: str) -> None:
        raise PermissionError("locked")

    with pytest.raises(AggregateError) as exc:
        analyzer.comfyui_conflict_analyzer(comfyui, disable_conflict_component=True, use_uv=False, disable_component_callback=failing_disable)

    assert [type(e) for e in exc.value.exceptions] == [PermissionError]
    assert install_calls == []


@pytest.mark.parametrize(
    ("answer", "expected_disabled", "expected_install"),
    [
        ("2", ["outlier"], "batch"),
        ("d", ["outlier"], "batch"),
        ("1", [], "sequential"),
        ("y", [], "sequential"),
        ("", [], "none"),
        ("n", [], "none"),
    ],
)
def test_analyzer_interactive_menu(monkeypatch, install_calls, tmp_path, answer, expected_disabled, expected_install):
    comfyui = make_comfyui(tmp_path, "torch\n", {"a": "numpy>=2\n", "b": "numpy>=2\n", "outlier": "numpy<2\n"})
    disabled: list[str] = []
    prompts: list[str] = []

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return answer

    monkeypatch.setattr("builtins.input", fake_input)

    # 交互模式下由用户选择, 不受命令行参数影响
    analyzer.comfyui_conflict_analyzer(
        comfyui,
        install_conflict_component_requirement=True,
        disable_conflict_component=True,
        interactive_mode=True,
        use_uv=False,
        disable_component_callback=_rename_disable(comfyui, disabled),
    )

    assert prompts == ["请输入选项 (1/2/N): "]
    assert disabled == expected_disabled
    if expected_install == "batch":
        assert len(install_calls) == 1 and isinstance(install_calls[0], list)
    elif expected_install == "sequential":
        assert len(install_calls) == 4 and not any(isinstance(call, list) for call in install_calls)
    else:
        assert install_calls == []


def test_analyzer_interactive_menu_hides_disable_option_without_candidates(monkeypatch, install_calls, tmp_path):
    comfyui = make_comfyui(tmp_path, "numpy<1.20\nnumpy>=1.26\n", {})
    prompts: list[str] = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "2")

    analyzer.comfyui_conflict_analyzer(comfyui, interactive_mode=True, use_uv=False, disable_component_callback=_rename_disable(comfyui, []))

    assert prompts == ["请输入选项 (1/N): "]
    assert install_calls == []


def test_analyzer_interactive_asks_again_when_conflicts_remain(monkeypatch, install_calls, tmp_path):
    comfyui = make_comfyui(tmp_path, "numpy<1.20\nnumpy>=1.26\n", {"a": "numpy>=1.26\n"})
    answers = iter(["2", "y"])
    prompts: list[str] = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or next(answers))
    disabled: list[str] = []

    analyzer.comfyui_conflict_analyzer(comfyui, interactive_mode=True, use_uv=False, disable_component_callback=_rename_disable(comfyui, disabled))

    assert disabled == ["a"]
    assert prompts == ["请输入选项 (1/2/N): ", "是否按顺序安装冲突组件依赖 (y/N): "]
    assert install_calls == [(comfyui / "requirements.txt").resolve()]


def test_analyzer_default_callback_disables_custom_node(install_calls, tmp_path):
    comfyui = make_comfyui(tmp_path, "torch\n", {"a": "numpy>=2\n", "b": "numpy>=2\n", "outlier": "numpy<2\n"})

    analyzer.comfyui_conflict_analyzer(comfyui, disable_conflict_component=True, use_uv=False)

    assert not (comfyui / "custom_nodes" / "outlier").exists()
    assert (comfyui / "custom_nodes" / "outlier.disabled").is_dir()


def test_comfyui_conflict_analyzer_installs_needed_requirements_and_aggregates(monkeypatch, tmp_path):
    node_a = tmp_path / "custom_nodes" / "node-a"
    node_b = tmp_path / "custom_nodes" / "node-b"
    for node in [node_a, node_b]:
        node.mkdir(parents=True)
        (node / "requirements.txt").write_text("demo\n", encoding="utf-8")

    reqs = [node_a / "requirements.txt", node_b / "requirements.txt"]
    calls = []
    monkeypatch.setattr(
        analyzer_checks,
        "process_comfyui_env_analysis",
        lambda _path: (
            {},
            reqs,
            [
                {
                    "package": "demo",
                    "components": [
                        {"component": "node-a", "requirement": "demo<1"},
                        {"component": "node-b", "requirement": "demo>=2"},
                    ],
                }
            ],
        ),
    )

    def fake_install_requirements(path, use_uv, cwd, custom_env):
        calls.append((path, use_uv, cwd, custom_env))
        if path == node_b / "requirements.txt":
            raise RuntimeError("install bad")

    monkeypatch.setattr(analyzer_actions, "install_requirements", fake_install_requirements)

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
    assert not any(isinstance(call[0], list) for call in calls)

    calls.clear()
    monkeypatch.setattr(
        analyzer_checks,
        "process_comfyui_env_analysis",
        lambda _path: (
            {},
            [],
            [],
        ),
    )
    analyzer.comfyui_conflict_analyzer(tmp_path, install_conflict_component_requirement=False)
    assert calls == []


def test_comfyui_conflict_analyzer_batches_non_conflicting_requirements(monkeypatch, tmp_path):
    node_a = tmp_path / "custom_nodes" / "node-a"
    node_b = tmp_path / "custom_nodes" / "node-b"
    for node in [node_a, node_b]:
        node.mkdir(parents=True)
        (node / "requirements.txt").write_text("demo\n", encoding="utf-8")

    req_paths = [(node_a / "requirements.txt").resolve(), (node_b / "requirements.txt").resolve()]
    calls = []
    info_messages = []
    monkeypatch.setattr(
        analyzer_checks,
        "process_comfyui_env_analysis",
        lambda _path: ({}, req_paths, []),
    )
    monkeypatch.setattr(analyzer.logger, "info", lambda message, *args: info_messages.append(message % args if args else message))

    def fake_install_requirements(path, use_uv, cwd, custom_env):
        calls.append((path, use_uv, cwd, custom_env))

    monkeypatch.setattr(analyzer_actions, "install_requirements", fake_install_requirements)

    analyzer.comfyui_conflict_analyzer(tmp_path, use_uv=False, custom_env={"PYTHONPATH": "old"})

    assert len(calls) == 1
    assert calls[0][0] == req_paths
    assert calls[0][1] is False
    assert calls[0][2] == tmp_path.resolve()
    assert calls[0][3]["PYTHONPATH"].split(os.pathsep)[0] == tmp_path.resolve().as_posix()
    assert "批量安装以下 ComfyUI 组件的依赖中: node-a, node-b" in info_messages
    assert "批量安装以下 ComfyUI 组件的依赖完成: node-a, node-b" in info_messages


def test_comfyui_conflict_analyzer_falls_back_to_sequential_when_batch_fails(monkeypatch, tmp_path):
    node_a = tmp_path / "custom_nodes" / "node-a"
    node_b = tmp_path / "custom_nodes" / "node-b"
    for node in [node_a, node_b]:
        node.mkdir(parents=True)
        (node / "requirements.txt").write_text("demo\n", encoding="utf-8")

    req_paths = [(node_a / "requirements.txt").resolve(), (node_b / "requirements.txt").resolve()]
    calls = []
    monkeypatch.setattr(
        analyzer_checks,
        "process_comfyui_env_analysis",
        lambda _path: ({}, req_paths, []),
    )

    def fake_install_requirements(path, use_uv, cwd, custom_env):
        calls.append((path, use_uv, cwd, custom_env))
        if isinstance(path, list):
            raise RuntimeError("batch bad")

    monkeypatch.setattr(analyzer_actions, "install_requirements", fake_install_requirements)

    analyzer.comfyui_conflict_analyzer(tmp_path, use_uv=False, custom_env={"PYTHONPATH": "old"})

    assert calls[0][0] == req_paths
    assert calls[0][2] == tmp_path.resolve()
    assert calls[1][0] == req_paths[0]
    assert calls[1][2] == node_a
    assert calls[2][0] == req_paths[1]
    assert calls[2][2] == node_b


def test_comfyui_conflict_analyzer_runs_install_scripts_sequentially(monkeypatch, tmp_path):
    node_a = tmp_path / "custom_nodes" / "node-a"
    node_b = tmp_path / "custom_nodes" / "node-b"
    node_c = tmp_path / "custom_nodes" / "node-c"
    for node in [node_a, node_b, node_c]:
        node.mkdir(parents=True)
        (node / "requirements.txt").write_text("demo\n", encoding="utf-8")
    for node in [node_b, node_c]:
        (node / "install.py").write_text("print('install')\n", encoding="utf-8")

    req_paths = [(node_a / "requirements.txt").resolve(), (node_b / "requirements.txt").resolve(), (node_c / "requirements.txt").resolve()]
    events = []
    info_messages = []
    monkeypatch.setattr(analyzer_checks, "process_comfyui_env_analysis", lambda _path: ({}, req_paths, ""))
    monkeypatch.setattr(analyzer.logger, "info", lambda message, *args: info_messages.append(message % args if args else message))

    def fake_install_requirements(path, use_uv, cwd, custom_env):
        events.append(("requirements", path, cwd))

    def fake_run_cmd(command, cwd, custom_env):
        events.append(("install.py", command, cwd))

    monkeypatch.setattr(analyzer_actions, "install_requirements", fake_install_requirements)
    monkeypatch.setattr(analyzer_actions, "run_cmd", fake_run_cmd)

    analyzer.comfyui_conflict_analyzer(tmp_path, use_uv=False)

    assert events == [
        ("requirements", req_paths, tmp_path.resolve()),
        ("install.py", [Path(sys.executable).as_posix(), (node_b / "install.py").as_posix()], node_b),
        ("install.py", [Path(sys.executable).as_posix(), (node_c / "install.py").as_posix()], node_c),
    ]
    assert "执行以下 ComfyUI 组件的安装脚本中: node-b, node-c" in info_messages
    assert "[1/2] 执行 node-b 的安装脚本中" in info_messages
    assert "[2/2] 执行 node-c 的安装脚本中" in info_messages
