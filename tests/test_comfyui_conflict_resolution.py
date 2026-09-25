"""ComfyUI 冲突组件禁用方案测试"""

import argparse
import random
from pathlib import Path

import pytest

from sd_webui_all_in_one.base_manager.comfyui_base import lifecycle
from sd_webui_all_in_one.cli_manager import comfyui_cli
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.env_check import comfyui_env_analyze as analyzer
from sd_webui_all_in_one.notebook_manager import comfyui_manager


def _group(package: str, *items: tuple[str, str], core: tuple[str, ...] = ("ComfyUI",)) -> dict:
    return {
        "package": package,
        "components": [{"component": name, "component_type": "core" if name in core else "extension", "requirement": req} for name, req in items],
    }


def _make_comfyui(root: Path, core_requirements: str, nodes: dict[str, str]) -> Path:
    comfyui = root / "ComfyUI"
    (comfyui / "custom_nodes").mkdir(parents=True)
    (comfyui / "requirements.txt").write_text(core_requirements, encoding="utf-8")
    for name, requirements in nodes.items():
        node = comfyui / "custom_nodes" / name
        node.mkdir()
        (node / "requirements.txt").write_text(requirements, encoding="utf-8")
    return comfyui


def _rename_disable(comfyui: Path, calls: list[str]):
    def disable(name: str) -> None:
        calls.append(name)
        path = comfyui / "custom_nodes" / name
        path.rename(path.with_name(f"{name}.disabled"))

    return disable


# ============================================================================
# resolve_conflict_components
# ============================================================================


def test_resolve_disables_only_truly_conflicting_component():
    conflicts = [_group("transformers", ("a", "transformers>=4.40"), ("b", "transformers>=4.38"), ("c", "transformers<5"), ("outlier", "transformers==4.26.0"))]

    result = analyzer.resolve_conflict_components(conflicts)

    assert result["disable_components"] == ["outlier"]
    assert result["keep_components"] == ["a", "b", "c"]
    assert result["disable_details"] == [{"component": "outlier", "reason": "optimal_selection", "conflicts_with": ["a", "b"], "packages": ["transformers"]}]
    assert result["is_optimal"] is True
    assert result["is_conflict_free"] is True
    assert result["unresolvable_conflicts"] == []


def test_resolve_star_graph_disables_hub():
    conflicts = [_group("numpy", ("hub", "numpy<2"), ("l1", "numpy>=2"), ("l2", "numpy>=2.1"), ("l3", "numpy==2.2.0"))]

    assert analyzer.resolve_conflict_components(conflicts)["disable_components"] == ["hub"]


def test_resolve_triangle_keeps_one_deterministically():
    conflicts = [_group("opencv-python", ("p1", "opencv-python==4.8.0.76"), ("p2", "opencv-python==4.9.0.80"), ("p3", "opencv-python==4.10.0.84"))]

    first = analyzer.resolve_conflict_components(conflicts)
    second = analyzer.resolve_conflict_components(list(reversed(conflicts)))

    assert len(first["disable_components"]) == 2
    assert first == second


def test_resolve_considers_all_packages_jointly():
    conflicts = [
        _group("numpy", ("x", "numpy<2"), ("y", "numpy>=2"), ("w", "numpy>=2")),
        _group("protobuf", ("x", "protobuf<4"), ("z", "protobuf>=4"), ("w", "protobuf>=4")),
    ]

    result = analyzer.resolve_conflict_components(conflicts)

    assert result["disable_components"] == ["x"]
    assert result["disable_details"][0]["packages"] == ["numpy", "protobuf"]


def test_resolve_never_disables_core_and_disables_its_conflicts():
    conflicts = [_group("numpy", ("ComfyUI", "numpy>=1.25"), ("old", "numpy<1.24"), ("ok", "numpy>=1.20"))]

    result = analyzer.resolve_conflict_components(conflicts)

    assert result["disable_components"] == ["old"]
    assert result["disable_details"][0]["reason"] == "conflicts_with_protected"
    assert "ComfyUI" in result["keep_components"]


def test_resolve_protected_component_prevails_over_count():
    conflicts = [_group("numpy", ("manager", "numpy<2"), ("a", "numpy>=2"), ("b", "numpy>=2"))]

    result = analyzer.resolve_conflict_components(conflicts, protected_components=["manager"])

    assert result["disable_components"] == ["a", "b"]


def test_resolve_self_conflicting_extension():
    conflicts = [_group("numpy", ("broken", "numpy<1.20"), ("broken", "numpy>=1.26"), ("fine", "numpy>=1.26"))]

    result = analyzer.resolve_conflict_components(conflicts)

    assert result["disable_details"] == [{"component": "broken", "reason": "self_conflict", "conflicts_with": ["fine"], "packages": ["numpy"]}]
    assert result["is_conflict_free"] is True


def test_resolve_reports_unresolvable_core_conflict():
    conflicts = [_group("numpy", ("ComfyUI", "numpy<1.20"), ("ComfyUI", "numpy>=1.26"))]

    result = analyzer.resolve_conflict_components(conflicts)

    assert result["disable_components"] == []
    assert result["is_conflict_free"] is False
    assert result["unresolvable_conflicts"][0]["component"] == "ComfyUI"
    assert "无法通过禁用扩展解决" in analyzer.format_conflict_resolution_info(result)


def test_resolve_prefers_components_when_counts_tie():
    conflicts = [_group("numpy", ("a", "numpy<2"), ("b", "numpy>=2"))]

    assert analyzer.resolve_conflict_components(conflicts, preferred_components=["a"])["disable_components"] == ["b"]
    assert analyzer.resolve_conflict_components(conflicts, preferred_components=["b"])["disable_components"] == ["a"]


def test_resolve_preference_never_reduces_kept_count():
    conflicts = [_group("numpy", ("hub", "numpy<2"), ("l1", "numpy>=2"), ("l2", "numpy>=2"))]

    assert analyzer.resolve_conflict_components(conflicts, preferred_components=["hub"])["disable_components"] == ["hub"]


def test_resolve_accepts_items_without_component_type():
    conflicts = [{"package": "demo", "components": [{"component": "node-a", "requirement": "demo<1"}, {"component": "node-b", "requirement": "demo>=2"}]}]

    result = analyzer.resolve_conflict_components(conflicts)

    assert len(result["disable_components"]) == 1


def test_resolve_empty_conflicts():
    assert analyzer.resolve_conflict_components([]) == {
        "keep_components": [],
        "disable_components": [],
        "disable_details": [],
        "unresolvable_conflicts": [],
        "is_optimal": True,
        "is_conflict_free": True,
    }


def _brute_force_mwis(neighbors: list[int], weights: list[int]) -> int:
    best = 0
    for mask in range(1 << len(neighbors)):
        if all(not (neighbors[v] & mask) for v in analyzer._iter_mask_bits(mask)):
            best = max(best, sum(weights[v] for v in analyzer._iter_mask_bits(mask)))
    return best


def test_max_weight_independent_set_matches_brute_force():
    rng = random.Random(20260925)
    for node_count in range(1, 12):
        for density in (0.2, 0.5, 0.8):
            neighbors = [0] * node_count
            for i in range(node_count):
                for j in range(i + 1, node_count):
                    if rng.random() < density:
                        neighbors[i] |= 1 << j
                        neighbors[j] |= 1 << i
            weights = [node_count + 1 + rng.randint(0, 1) for _ in range(node_count)]

            chosen, optimal = analyzer._max_weight_independent_set(neighbors, weights, 10**6)

            assert optimal is True
            assert all(not (neighbors[v] & chosen) for v in analyzer._iter_mask_bits(chosen))
            assert sum(weights[v] for v in analyzer._iter_mask_bits(chosen)) == _brute_force_mwis(neighbors, weights)


def test_max_weight_independent_set_budget_returns_valid_set():
    rng = random.Random(7)
    node_count = 120
    neighbors = [0] * node_count
    for i in range(node_count):
        for j in range(i + 1, node_count):
            if rng.random() < 0.5:
                neighbors[i] |= 1 << j
                neighbors[j] |= 1 << i

    chosen, optimal = analyzer._max_weight_independent_set(neighbors, [1] * node_count, 5)

    assert optimal is False
    assert chosen != 0
    assert all(not (neighbors[v] & chosen) for v in analyzer._iter_mask_bits(chosen))


# ============================================================================
# check_comfyui_component_dependencies
# ============================================================================


def test_check_dependencies_includes_resolution_and_prefers_installed(monkeypatch, tmp_path):
    comfyui = _make_comfyui(tmp_path, "torch\n", {"a": "numpy<2\n", "b": "numpy>=2\n"})
    monkeypatch.setattr(analyzer, "is_package_installed", lambda package: package != "numpy<2")

    result = analyzer.check_comfyui_component_dependencies(comfyui)

    assert result["conflict_resolution"]["disable_components"] == ["a"]
    assert result["conflict_resolution"]["keep_components"] == ["b"]


def test_disabling_resolution_clears_conflicts_on_reanalysis(monkeypatch, tmp_path):
    comfyui = _make_comfyui(
        tmp_path,
        "numpy>=1.25\n",
        {"old": "numpy<1.24\n", "ok": "numpy>=1.20\n", "x": "protobuf<4\n", "z": "protobuf>=4\n", "w": "protobuf>=4\n"},
    )
    monkeypatch.setattr(analyzer, "is_package_installed", lambda _package: True)

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
    monkeypatch.setattr(analyzer, "is_package_installed", lambda _package: False)
    monkeypatch.setattr(analyzer, "install_requirements", lambda path, use_uv, cwd, custom_env: calls.append(path))
    return calls


def test_analyzer_disables_conflicts_then_batch_installs(install_calls, tmp_path):
    comfyui = _make_comfyui(tmp_path, "torch\n", {"a": "numpy>=2\n", "b": "numpy>=2.1\n", "outlier": "numpy<2\n"})
    disabled: list[str] = []

    analyzer.comfyui_conflict_analyzer(comfyui, disable_conflict_component=True, use_uv=False, disable_component_callback=_rename_disable(comfyui, disabled))

    assert disabled == ["outlier"]
    assert (comfyui / "custom_nodes" / "outlier.disabled").is_dir()
    assert len(install_calls) == 1
    assert isinstance(install_calls[0], list)
    assert sorted(path.parent.name for path in install_calls[0]) == ["ComfyUI", "a", "b"]


def test_analyzer_disable_takes_precedence_over_install(install_calls, tmp_path):
    comfyui = _make_comfyui(tmp_path, "torch\n", {"a": "numpy>=2\n", "outlier": "numpy<2\n", "b": "numpy>=2\n"})
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
    comfyui = _make_comfyui(tmp_path, "numpy<1.20\nnumpy>=1.26\n", {"a": "numpy>=1.26\n", "b": "numpy<1.20\n"})
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
    comfyui = _make_comfyui(tmp_path, "numpy<1.20\nnumpy>=1.26\n", {"a": "numpy>=1.26\n"})

    analyzer.comfyui_conflict_analyzer(comfyui, disable_conflict_component=True, use_uv=False, disable_component_callback=_rename_disable(comfyui, []))

    assert install_calls == []


def test_analyzer_disable_flag_without_candidates_uses_install_flag(install_calls, tmp_path):
    comfyui = _make_comfyui(tmp_path, "numpy<1.20\nnumpy>=1.26\n", {})
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
    comfyui = _make_comfyui(tmp_path, "torch\n", {"a": "numpy>=2\n", "b": "numpy>=2\n", "outlier": "numpy<2\n"})

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
    comfyui = _make_comfyui(tmp_path, "torch\n", {"a": "numpy>=2\n", "b": "numpy>=2\n", "outlier": "numpy<2\n"})
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
    comfyui = _make_comfyui(tmp_path, "numpy<1.20\nnumpy>=1.26\n", {})
    prompts: list[str] = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "2")

    analyzer.comfyui_conflict_analyzer(comfyui, interactive_mode=True, use_uv=False, disable_component_callback=_rename_disable(comfyui, []))

    assert prompts == ["请输入选项 (1/N): "]
    assert install_calls == []


def test_analyzer_interactive_asks_again_when_conflicts_remain(monkeypatch, install_calls, tmp_path):
    comfyui = _make_comfyui(tmp_path, "numpy<1.20\nnumpy>=1.26\n", {"a": "numpy>=1.26\n"})
    answers = iter(["2", "y"])
    prompts: list[str] = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or next(answers))
    disabled: list[str] = []

    analyzer.comfyui_conflict_analyzer(comfyui, interactive_mode=True, use_uv=False, disable_component_callback=_rename_disable(comfyui, disabled))

    assert disabled == ["a"]
    assert prompts == ["请输入选项 (1/2/N): ", "是否按顺序安装冲突组件依赖 (y/N): "]
    assert install_calls == [(comfyui / "requirements.txt").resolve()]


def test_analyzer_default_callback_disables_custom_node(install_calls, tmp_path):
    comfyui = _make_comfyui(tmp_path, "torch\n", {"a": "numpy>=2\n", "b": "numpy>=2\n", "outlier": "numpy<2\n"})

    analyzer.comfyui_conflict_analyzer(comfyui, disable_conflict_component=True, use_uv=False)

    assert not (comfyui / "custom_nodes" / "outlier").exists()
    assert (comfyui / "custom_nodes" / "outlier.disabled").is_dir()


# ============================================================================
# 参数传递
# ============================================================================


def test_check_comfyui_env_passes_disable_option(monkeypatch, tmp_path):
    comfyui = _make_comfyui(tmp_path, "torch\n", {"outlier": "numpy<2\n"})
    captured = {}

    def fake_run_env_check_tasks(tasks, **_kwargs):
        captured.update({task.name: task.kwargs for task in tasks})

    monkeypatch.setattr(lifecycle, "run_env_check_tasks", fake_run_env_check_tasks)
    monkeypatch.setattr(lifecycle, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(lifecycle, "apply_git_config_global_to_process", lambda _env: None)

    lifecycle.check_comfyui_env(comfyui, disable_conflict_component=True)

    kwargs = captured[lifecycle.ComfyUIEnvCheckName.COMFYUI_CONFLICTS]
    assert kwargs["disable_conflict_component"] is True
    kwargs["disable_component_callback"]("outlier")
    assert (comfyui / "custom_nodes" / "outlier.disabled").is_dir()


@pytest.mark.parametrize("command", ["check-env", "launch"])
def test_cli_disable_conflict_flag(monkeypatch, tmp_path, command):
    parser = argparse.ArgumentParser(prog="sd-webui-all-in-one")
    comfyui_cli.register_comfyui(parser.add_subparsers(dest="command", required=True))
    calls: list[dict] = []
    target = "check_env" if command == "check-env" else "launch"
    monkeypatch.setattr(comfyui_cli, target, lambda **kwargs: calls.append(kwargs))

    for extra, expected in (([], False), (["--disable-conflict"], True)):
        args = parser.parse_args(["comfyui", command, "--comfyui-path", str(tmp_path), "--no-auto-mirror", *extra])
        args.func(args)
        assert calls[-1]["disable_conflict_component"] is expected


def test_notebook_check_env_passes_disable_option(monkeypatch, tmp_path):
    calls: list[dict] = []
    monkeypatch.setattr(comfyui_manager, "check_comfyui_env", lambda **kwargs: calls.append(kwargs))

    comfyui_manager.ComfyUIManager(tmp_path, "app").check_env(disable_conflict_component=True)

    assert calls[0]["disable_conflict_component"] is True
    assert calls[0]["install_conflict_component_requirement"] is True
