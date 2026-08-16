from collections import defaultdict

from .models import ConnectionKind, Workflow


class CycleError(ValueError):
    pass


def stable_topological_order(
    workflow: Workflow,
    preferred_order: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    node_ids = tuple(node.id for node in workflow.nodes)
    node_set = set(node_ids)
    preference = preferred_order or workflow.execution_order or node_ids
    rank = {node_id: index for index, node_id in enumerate(preference)}
    fallback = {node_id: index for index, node_id in enumerate(node_ids)}
    indegree = {node_id: 0 for node_id in node_ids}
    dependents: dict[str, set[str]] = defaultdict(set)

    for connection in workflow.connections:
        if connection.kind is ConnectionKind.CONTROL:
            continue
        source = connection.source_node_id
        target = connection.target_node_id
        if source not in node_set or target not in node_set or target in dependents[source]:
            continue
        dependents[source].add(target)
        indegree[target] += 1

    def order_key(node_id: str) -> tuple[int, int]:
        return rank.get(node_id, len(rank) + fallback[node_id]), fallback[node_id]

    ready = sorted((node_id for node_id, degree in indegree.items() if degree == 0), key=order_key)
    result: list[str] = []
    while ready:
        current = ready.pop(0)
        result.append(current)
        for target in sorted(dependents[current], key=order_key):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort(key=order_key)

    if len(result) != len(node_ids):
        raise CycleError('The workflow contains a cycle.')
    return tuple(result)