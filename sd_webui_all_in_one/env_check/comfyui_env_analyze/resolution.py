"""ComfyUI 组件冲突解决方案计算"""

from collections import deque

from sd_webui_all_in_one.env_check.comfyui_env_analyze.models import (
    ComponentType,
    ComfyUIConflictGroup,
    ComfyUIDisableReason,
    ComfyUIConflictEdge,
    ComfyUIDisableCandidate,
    ComfyUIConflictResolution,
)
from sd_webui_all_in_one.env_check.comfyui_env_analyze.conflict_detection import (
    detect_conflict_package,
)


def build_component_conflict_graph(
    conflicts: list[ComfyUIConflictGroup],
) -> tuple[dict[str, ComponentType | None], dict[str, set[str]], list[ComfyUIConflictEdge], dict[str, list[ComfyUIConflictEdge]]]:
    """根据冲突组构建组件级冲突图

    冲突组只记录了声明同一冲突软件包的组件, 组内组件之间不一定互相冲突,
    因此需要对组内每对版本声明重新检测, 仅在真正无法同时满足的组件之间连边.

    Args:
        conflicts (list[ComfyUIConflictGroup]):
            结构化的冲突组列表

    Returns:
        (tuple[dict[str, ComponentType | None], dict[str, set[str]], list[ComfyUIConflictEdge], dict[str, list[ComfyUIConflictEdge]]]):
            组件类型表, 邻接表, 组件之间的冲突关系列表, 组件自身的冲突关系表
    """
    component_types: dict[str, ComponentType | None] = {}
    adjacency: dict[str, set[str]] = {}
    edges: list[ComfyUIConflictEdge] = []
    self_conflicts: dict[str, list[ComfyUIConflictEdge]] = {}

    for group in conflicts:
        items = group["components"]
        for item in items:
            component_types.setdefault(item["component"], item.get("component_type"))
            adjacency.setdefault(item["component"], set())

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                if not detect_conflict_package(a["requirement"], b["requirement"]):
                    continue
                edge: ComfyUIConflictEdge = {
                    "package": group["package"],
                    "component": a["component"],
                    "requirement": a["requirement"],
                    "other_component": b["component"],
                    "other_requirement": b["requirement"],
                }
                if a["component"] == b["component"]:
                    self_conflicts.setdefault(a["component"], []).append(edge)
                    continue
                edges.append(edge)
                adjacency[a["component"]].add(b["component"])
                adjacency[b["component"]].add(a["component"])

    return component_types, adjacency, edges, self_conflicts


def _split_connected_components(
    nodes: list[str],
    adjacency: dict[str, set[str]],
) -> list[list[str]]:
    """将冲突图拆分为连通分量, 各分量内节点按名称排序"""
    visited: set[str] = set()
    result: list[list[str]] = []
    for start in nodes:
        if start in visited:
            continue
        visited.add(start)
        queue = deque([start])
        component: list[str] = []
        while queue:
            node = queue.popleft()
            component.append(node)
            for neighbor in sorted(adjacency[node]):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        result.append(sorted(component))
    return result


def _iter_mask_bits(
    mask: int,
) -> list[int]:
    """返回位掩码中所有置位的下标"""
    bits: list[int] = []
    while mask:
        low = mask & -mask
        bits.append(low.bit_length() - 1)
        mask ^= low
    return bits


def _max_weight_independent_set(
    neighbors: list[int],
    weights: list[int],
    search_budget: int,
) -> tuple[int, bool]:
    """使用位集分支定界求解最大权独立集

    先以贪心解作为初始下界, 搜索中使用度为 0 / 1 的节点约简, 并以贪心团划分作为上界剪枝.
    搜索步数超过预算时返回当前最优解 (仍然是合法的独立集).

    Args:
        neighbors (list[int]):
            每个节点的邻居位掩码
        weights (list[int]):
            每个节点的权重
        search_budget (int):
            最大搜索步数

    Returns:
        (tuple[int, bool]):
            选中节点的位掩码, 以及该结果是否已被证明为最优解
    """
    node_count = len(neighbors)
    degrees = [mask.bit_count() for mask in neighbors]

    greedy_set, blocked = 0, 0
    for v in sorted(range(node_count), key=lambda x: (-weights[x] / (degrees[x] + 1), x)):
        if not (blocked >> v) & 1:
            greedy_set |= 1 << v
            blocked |= neighbors[v] | (1 << v)
    best_weight = sum(weights[v] for v in _iter_mask_bits(greedy_set))
    best_set = greedy_set
    steps = 0

    def clique_cover_bound(candidates: int) -> int:
        # 将候选节点贪心划分为若干团, 每个团至多选一个节点, 上界为各团最大权重之和
        bound, rest = 0, candidates
        while rest:
            v = (rest & -rest).bit_length() - 1
            rest &= ~(1 << v)
            members, top = 1 << v, weights[v]
            for u in _iter_mask_bits(rest & neighbors[v]):
                if (neighbors[u] & members) == members:
                    members |= 1 << u
                    top = max(top, weights[u])
                    rest &= ~(1 << u)
            bound += top
        return bound

    def search(candidates: int, current_weight: int, current_set: int) -> bool:
        nonlocal best_weight, best_set, steps
        steps += 1
        if steps > search_budget:
            return False

        # 约简: 候选中无邻居的节点必选; 仅有一个邻居且权重不小于该邻居的节点必选
        changed = True
        while changed and candidates:
            changed = False
            for v in _iter_mask_bits(candidates):
                if not (candidates >> v) & 1:
                    continue
                local_neighbors = neighbors[v] & candidates
                if local_neighbors == 0 or (local_neighbors & (local_neighbors - 1) == 0 and weights[v] >= weights[local_neighbors.bit_length() - 1]):
                    current_weight += weights[v]
                    current_set |= 1 << v
                    candidates &= ~(local_neighbors | (1 << v))
                    changed = True

        if candidates == 0:
            if current_weight > best_weight:
                best_weight, best_set = current_weight, current_set
            return True

        if current_weight + clique_cover_bound(candidates) <= best_weight:
            return True

        # 在候选中度最大的节点上分支 (同度时取下标最小者, 保证结果确定)
        pivot = max(_iter_mask_bits(candidates), key=lambda x: ((neighbors[x] & candidates).bit_count(), -x))
        if not search(candidates & ~(neighbors[pivot] | (1 << pivot)), current_weight + weights[pivot], current_set | (1 << pivot)):
            return False
        return search(candidates & ~(1 << pivot), current_weight, current_set)

    is_optimal = search((1 << node_count) - 1, 0, 0)
    return best_set, is_optimal


def resolve_conflict_components(
    conflicts: list[ComfyUIConflictGroup],
    protected_components: list[str] | None = None,
    preferred_components: list[str] | None = None,
    search_budget: int = 200_000,
) -> ComfyUIConflictResolution:
    """计算保留组件最多的无冲突组合, 并给出需要禁用的组件列表

    算法流程:
    1. 对冲突组内的版本声明逐对检测, 构建组件级冲突图.
    2. ComfyUI 内核与 ``protected_components`` 中的组件始终保留; 与其冲突的扩展, 以及自身依赖冲突的扩展必须禁用.
    3. 对剩余冲突图的每个连通分量求最大权独立集: 首先保证保留的组件数量最多,
       其次优先保留 ``preferred_components`` 中的组件, 最后按组件名称确定性地选择.

    Args:
        conflicts (list[ComfyUIConflictGroup]):
            结构化的冲突组列表
        protected_components (list[str] | None):
            始终保留的组件
        preferred_components (list[str] | None):
            保留数量相同时优先保留的组件
        search_budget (int):
            每个连通分量的最大搜索步数, 超出后使用当前最优解

    Returns:
        ComfyUIConflictResolution: 冲突组件禁用方案
    """
    component_types, adjacency, edges, self_conflicts = build_component_conflict_graph(conflicts)
    protected = {name for name, component_type in component_types.items() if component_type == "core"}
    protected |= set(protected_components or []) & set(component_types)
    preferred = set(preferred_components or [])

    disable: dict[str, ComfyUIDisableCandidate] = {}
    unresolvable: list[ComfyUIConflictEdge] = []

    def add_disable(name: str, reason: ComfyUIDisableReason) -> None:
        if name not in disable:
            disable[name] = {"component": name, "reason": reason, "conflicts_with": [], "packages": []}

    for name, self_edges in self_conflicts.items():
        if name in protected:
            unresolvable.extend(self_edges)
        else:
            add_disable(name, "self_conflict")

    for edge in edges:
        if edge["component"] in protected and edge["other_component"] in protected:
            unresolvable.append(edge)

    for name in sorted(component_types):
        if name not in protected and adjacency[name] & protected:
            add_disable(name, "conflicts_with_protected")

    free_nodes = sorted(name for name in component_types if name not in protected and name not in disable and adjacency[name])
    free_set = set(free_nodes)
    is_optimal = True
    for component in _split_connected_components(free_nodes, {name: adjacency[name] & free_set for name in free_nodes}):
        index = {name: i for i, name in enumerate(component)}
        neighbors = [sum(1 << index[other] for other in adjacency[name] if other in index) for name in component]
        # 基础权重大于所有偏好加成之和, 保证 "保留数量" 严格优先于 "偏好"
        scale = len(component) + 1
        weights = [scale + (1 if name in preferred else 0) for name in component]
        chosen, optimal = _max_weight_independent_set(neighbors, weights, search_budget)
        is_optimal = is_optimal and optimal
        for i, name in enumerate(component):
            if not (chosen >> i) & 1:
                add_disable(name, "optimal_selection")

    for edge in edges:
        for name, other in ((edge["component"], edge["other_component"]), (edge["other_component"], edge["component"])):
            if name in disable and other not in disable:
                if other not in disable[name]["conflicts_with"]:
                    disable[name]["conflicts_with"].append(other)
                if edge["package"] not in disable[name]["packages"]:
                    disable[name]["packages"].append(edge["package"])
    for name, self_edges in self_conflicts.items():
        if name in disable:
            for edge in self_edges:
                if edge["package"] not in disable[name]["packages"]:
                    disable[name]["packages"].append(edge["package"])

    details = [disable[name] for name in sorted(disable)]
    for detail in details:
        detail["conflicts_with"].sort()
        detail["packages"].sort()

    keep = sorted(name for name in component_types if name not in disable)
    keep_set = set(keep)
    is_conflict_free = not any(name in keep_set for name in self_conflicts) and not any(edge["component"] in keep_set and edge["other_component"] in keep_set for edge in edges)
    return {
        "keep_components": keep,
        "disable_components": sorted(disable),
        "disable_details": details,
        "unresolvable_conflicts": unresolvable,
        "is_optimal": is_optimal,
        "is_conflict_free": is_conflict_free,
    }
