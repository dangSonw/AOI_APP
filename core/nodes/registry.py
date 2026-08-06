from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

from core.algorithms import get_algorithm_catalog

from .models import NodeRuntime, NodeUse


NODES_ROOT = Path(__file__).parent


class InvalidNodeRuntime(RuntimeError):
    pass


def _load_module(path: Path) -> ModuleType:
    module_name = f"core.nodes.runtime_{path.parent.parent.name.replace('-', '_')}_{path.parent.name.replace('-', '_')}"
    spec = spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise InvalidNodeRuntime(f'Node module {path.parent.name} cannot be loaded.')
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_registry() -> dict[str, NodeRuntime]:
    registry: dict[str, NodeRuntime] = {}
    for path in sorted(NODES_ROOT.glob('*/*/node.py')):
        module = _load_module(path)
        try:
            runtime = NodeRuntime(
                id=module.NODE_ID,
                use=NodeUse(module.USE),
                input_keys=tuple(module.INPUT_KEYS),
                output_keys=tuple(module.OUTPUT_KEYS),
                execute=module.execute,
            )
        except (AttributeError, TypeError, ValueError) as error:
            raise InvalidNodeRuntime(f'Node module {path.parent.name} has an invalid contract.') from error
        if runtime.id in registry:
            raise InvalidNodeRuntime(f'Node runtime {runtime.id} is duplicated.')
        registry[runtime.id] = runtime

    definitions = {definition.id: definition for definition in get_algorithm_catalog()}
    if set(registry) != set(definitions):
        raise InvalidNodeRuntime('Node runtime packages do not match the algorithm catalog.')
    for node_id, runtime in registry.items():
        definition = definitions[node_id]
        if runtime.input_keys != tuple(port.key for port in definition.inputs):
            raise InvalidNodeRuntime(f'Node runtime {node_id} input contract does not match the catalog.')
        if runtime.output_keys != tuple(port.key for port in definition.outputs):
            raise InvalidNodeRuntime(f'Node runtime {node_id} output contract does not match the catalog.')
    return registry


_REGISTRY: dict[str, NodeRuntime] | None = None


def get_node_registry() -> dict[str, NodeRuntime]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _load_registry()
    return dict(_REGISTRY)


def get_node_runtime(node_id: str) -> NodeRuntime | None:
    return get_node_registry().get(node_id)