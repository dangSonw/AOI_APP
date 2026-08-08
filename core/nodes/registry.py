import json
from dataclasses import replace
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Any

from core.algorithms.models import (
    AlgorithmDefinition, DataType, ParameterDefinition, ParameterKind,
    PortDefinition, PortDirection, is_json_parameter_value,
)

from .models import NodeManifest, NodeRuntime, NodeUse


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


def _port(payload: dict[str, Any]) -> PortDefinition:
    return PortDefinition(
        key=payload['key'], label=payload['label'], direction=PortDirection(payload['direction']),
        data_type=DataType(payload['data_type']), required=payload.get('required', True),
        variadic=payload.get('variadic', False),
    )


def _parameter(payload: dict[str, Any]) -> ParameterDefinition:
    default_value = payload['default_value']
    options = tuple(payload.get('options', ()))
    if not is_json_parameter_value(default_value) or not is_json_parameter_value(list(options)):
        raise InvalidNodeRuntime('Node manifest contains an invalid JSON parameter value.')
    return ParameterDefinition(
        key=payload['key'], label=payload['label'], kind=ParameterKind(payload['kind']),
        default_value=default_value, required=payload.get('required', True),
        minimum=payload.get('minimum'), maximum=payload.get('maximum'), options=options,
        description=payload.get('description', ''),
    )


def _load_manifest(path: Path) -> NodeManifest:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        definition_payload = payload['definition']
        inspector = payload['inspector']
        definition = AlgorithmDefinition(
            id=definition_payload['id'], name=definition_payload['name'],
            description=definition_payload['description'], category=definition_payload['category'],
            documentation_group=definition_payload['documentation_group'],
            inputs=tuple(_port(item) for item in definition_payload['inputs']),
            outputs=tuple(_port(item) for item in definition_payload['outputs']),
            parameters=tuple(_parameter(item) for item in definition_payload.get('parameters', ())),
            availability=definition_payload.get('availability', 'configuration-only'),
            documentation_reference=definition_payload.get('documentation_reference'),
            manifest_version=payload['manifestVersion'], package_version=payload['packageVersion'],
            execution_target=payload['executionTarget'], inspector_kind=inspector['kind'],
            custom_inspector_key=inspector.get('customKey'),
        )
        manifest = NodeManifest(
            manifest_version=payload['manifestVersion'], catalog_order=payload['catalogOrder'], package_version=payload['packageVersion'],
            id=payload['id'], use=NodeUse(payload['use']), execution_target=payload['executionTarget'],
            capabilities=tuple(payload.get('capabilities', ())),
            resource_hints=dict(payload.get('resourceHints', {})),
            artifact_contracts={key: tuple(value) for key, value in payload.get('artifactContracts', {}).items()},
            parameter_migration_hooks=tuple(payload.get('parameterMigrationHooks', ())),
            inspector_kind=inspector['kind'], custom_inspector_key=inspector.get('customKey'),
            definition=definition,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise InvalidNodeRuntime(f'Node manifest {path.parent.name} has an invalid contract.') from error
    if manifest.manifest_version != 1 or manifest.id != path.parent.name or manifest.definition.id != manifest.id:
        raise InvalidNodeRuntime(f'Node manifest {path.parent.name} identity is invalid.')
    if manifest.execution_target not in {'local-cpu', 'local-gpu', 'adapter'}:
        raise InvalidNodeRuntime(f'Node manifest {manifest.id} execution target is unsupported.')
    if manifest.inspector_kind not in {'none', 'generic', 'custom'}:
        raise InvalidNodeRuntime(f'Node manifest {manifest.id} inspector contract is unsupported.')
    if manifest.inspector_kind == 'custom' and not manifest.custom_inspector_key:
        raise InvalidNodeRuntime(f'Node manifest {manifest.id} custom inspector key is required.')
    return manifest


def _load_manifest_registry() -> dict[str, NodeManifest]:
    registry: dict[str, NodeManifest] = {}
    for path in sorted(NODES_ROOT.glob('*/*/manifest.json')):
        manifest = _load_manifest(path)
        if manifest.id in registry:
            raise InvalidNodeRuntime(f'Node manifest {manifest.id} is duplicated.')
        registry[manifest.id] = manifest
    return registry


def _load_registry(manifests: dict[str, NodeManifest]) -> dict[str, NodeRuntime]:
    registry: dict[str, NodeRuntime] = {}
    for path in sorted(NODES_ROOT.glob('*/*/node.py')):
        module = _load_module(path)
        try:
            runtime = NodeRuntime(
                id=module.NODE_ID, use=NodeUse(module.USE), input_keys=tuple(module.INPUT_KEYS),
                output_keys=tuple(module.OUTPUT_KEYS), execute=module.execute,
            )
        except (AttributeError, TypeError, ValueError) as error:
            raise InvalidNodeRuntime(f'Node module {path.parent.name} has an invalid contract.') from error
        if runtime.id in registry:
            raise InvalidNodeRuntime(f'Node runtime {runtime.id} is duplicated.')
        registry[runtime.id] = runtime
    if set(registry) != set(manifests):
        raise InvalidNodeRuntime('Node runtime packages do not match node manifests.')
    for node_id, runtime in registry.items():
        manifest = manifests[node_id]
        if runtime.use != manifest.use:
            raise InvalidNodeRuntime(f'Node runtime {node_id} release contract does not match its manifest.')
        if runtime.input_keys != tuple(port.key for port in manifest.definition.inputs):
            raise InvalidNodeRuntime(f'Node runtime {node_id} input contract does not match its manifest.')
        if runtime.output_keys != tuple(port.key for port in manifest.definition.outputs):
            raise InvalidNodeRuntime(f'Node runtime {node_id} output contract does not match its manifest.')
    return registry


_MANIFEST_REGISTRY: dict[str, NodeManifest] | None = None
_REGISTRY: dict[str, NodeRuntime] | None = None


def get_node_manifest_registry() -> dict[str, NodeManifest]:
    global _MANIFEST_REGISTRY
    if _MANIFEST_REGISTRY is None:
        _MANIFEST_REGISTRY = _load_manifest_registry()
    return dict(_MANIFEST_REGISTRY)


def get_node_registry() -> dict[str, NodeRuntime]:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _load_registry(get_node_manifest_registry())
    return dict(_REGISTRY)


def get_node_runtime(node_id: str) -> NodeRuntime | None:
    return get_node_registry().get(node_id)


def validate_node_runtime_support(node_id: str, *, deployment_mode: str) -> tuple[str, ...]:
    manifest = get_node_manifest_registry().get(node_id)
    if manifest is None:
        return (f'Node {node_id} is not registered.',)
    if deployment_mode == 'production' and manifest.use is not NodeUse.RELEASE:
        return (f'Node {node_id} uses a {manifest.use.value} runtime and cannot run in production.',)
    if manifest.execution_target not in {'local-cpu', 'local-gpu', 'adapter'}:
        return (f'Node {node_id} uses an unsupported execution target.',)
    return ()
