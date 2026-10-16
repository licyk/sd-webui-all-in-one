"""ComfyUI 冲突组件禁用方案求解测试"""

import random

from sd_webui_all_in_one.env_check import comfyui_env_analyze as analyzer
from sd_webui_all_in_one.env_check.comfyui_env_analyze import resolution as analyzer_resolution


def _group(package: str, *items: tuple[str, str], core: tuple[str, ...] = ("ComfyUI",)) -> dict:
    return {
        "package": package,
        "components": [{"component": name, "component_type": "core" if name in core else "extension", "requirement": req} for name, req in items],
    }


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
        if all(not (neighbors[v] & mask) for v in analyzer_resolution._iter_mask_bits(mask)):
            best = max(best, sum(weights[v] for v in analyzer_resolution._iter_mask_bits(mask)))
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

            chosen, optimal = analyzer_resolution._max_weight_independent_set(neighbors, weights, 10**6)

            assert optimal is True
            assert all(not (neighbors[v] & chosen) for v in analyzer_resolution._iter_mask_bits(chosen))
            assert sum(weights[v] for v in analyzer_resolution._iter_mask_bits(chosen)) == _brute_force_mwis(neighbors, weights)


def test_max_weight_independent_set_budget_returns_valid_set():
    rng = random.Random(7)
    node_count = 120
    neighbors = [0] * node_count
    for i in range(node_count):
        for j in range(i + 1, node_count):
            if rng.random() < 0.5:
                neighbors[i] |= 1 << j
                neighbors[j] |= 1 << i

    chosen, optimal = analyzer_resolution._max_weight_independent_set(neighbors, [1] * node_count, 5)

    assert optimal is False
    assert chosen != 0
    assert all(not (neighbors[v] & chosen) for v in analyzer_resolution._iter_mask_bits(chosen))
