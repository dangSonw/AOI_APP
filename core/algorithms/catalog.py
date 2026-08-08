from .models import AlgorithmDefinition


def get_algorithm_catalog() -> tuple[AlgorithmDefinition, ...]:
    from core.nodes.registry import get_node_manifest_registry

    manifests = get_node_manifest_registry()
    return tuple(manifest.definition for manifest in sorted(manifests.values(), key=lambda item: item.catalog_order))


def get_algorithm_definition(algorithm_id: str) -> AlgorithmDefinition | None:
    from core.nodes.registry import get_node_manifest_registry

    manifest = get_node_manifest_registry().get(algorithm_id)
    return manifest.definition if manifest else None
