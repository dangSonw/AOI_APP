from dataclasses import replace

from app.schemas.workflow import AlgorithmDefinitionSchema, WorkflowSchema
from core.algorithms import get_algorithm_catalog
from core.pipeline import ConnectionKind, create_default_workflow


def test_workflow_schema_round_trip_uses_camel_case_contract() -> None:
    workflow = create_default_workflow()

    schema = WorkflowSchema.from_core(workflow)
    payload = schema.model_dump(mode='json', by_alias=True)

    assert payload['recipeSlug'] == 'rev-c-mainboard'
    assert payload['updatedAt'].endswith('Z')
    assert 'executionOrder' in payload
    assert payload['nodes'][0]['algorithmId'] == 'image-input'
    assert payload['nodes'][0]['ports'][0]['templateKey'] == 'image'
    assert schema.to_core() == workflow


def test_workflow_schema_round_trips_control_connection_fields() -> None:
    workflow = create_default_workflow()
    control = replace(
        workflow.connections[0], source_port_id='completed', target_port_id='control-in',
        kind=ConnectionKind.CONTROL, max_traversals=3,
    )
    workflow = replace(workflow, connections=(control, *workflow.connections[1:]))

    payload = WorkflowSchema.from_core(workflow).model_dump(mode='json', by_alias=True)

    assert payload['connections'][0]['kind'] == 'control'
    assert payload['connections'][0]['maxTraversals'] == 3
    assert WorkflowSchema.model_validate(payload).to_core() == workflow


def test_algorithm_schema_exposes_typed_configuration_metadata() -> None:
    definition = get_algorithm_catalog()[0]

    payload = AlgorithmDefinitionSchema.from_core(definition).model_dump(mode='json', by_alias=True)

    assert payload['id'] == 'image-input'
    assert payload['availability'] == 'configuration-only'
    assert payload['outputs'][0]['dataType'] == 'image'
    assert payload['parameters'][0]['defaultValue'] == 'recipe-image'

def test_algorithm_schema_projects_manifest_and_inspector_contract() -> None:
    from app.schemas.workflow import AlgorithmDefinitionSchema
    from core.algorithms import get_algorithm_definition

    schema = AlgorithmDefinitionSchema.from_core(get_algorithm_definition('camera-capture'))
    payload = schema.model_dump(mode='json', by_alias=True)

    assert payload['manifestVersion'] == 1
    assert payload['packageVersion'] == '1.0.0'
    assert payload['executionTarget'] == 'adapter'
    assert payload['inspectorKind'] == 'custom'
    assert payload['customInspectorKey'] == 'camera-acquisition'


def test_custom_inspector_manifest_keys_are_valid_and_projected() -> None:
    payloads = [
        AlgorithmDefinitionSchema.from_core(definition).model_dump(mode='json', by_alias=True)
        for definition in get_algorithm_catalog()
        if definition.inspector_kind == 'custom'
    ]

    assert {payload['customInspectorKey'] for payload in payloads} == {
        'camera-acquisition', 'knn-image-segmentation', 'svm-image-classifier',
    }
    assert all(payload['customInspectorKey'] and payload['customInspectorKey'].replace('-', '').isalnum() for payload in payloads)


def test_algorithm_schema_projects_default_custom_control_ports() -> None:
    from core.algorithms import get_algorithm_definition

    payload = AlgorithmDefinitionSchema.from_core(
        get_algorithm_definition('logic-and'),
    ).model_dump(mode='json', by_alias=True)

    assert [port['key'] for port in payload['controlPorts']] == ['true', 'false']
    assert all(port['dataType'] == 'boolean' for port in payload['inputs'])


def test_algorithm_schema_projects_optional_v2_action_and_artifact_contracts() -> None:
    from core.algorithms.models import AlgorithmActionDefinition, ArtifactContractDefinition

    definition = replace(
        get_algorithm_catalog()[0],
        manifest_version=2,
        capabilities=('configure', 'train'),
        actions={
            'train': AlgorithmActionDefinition(
                dataset_inputs=('training-dataset',), execution_targets=('local-cpu',), cancellable=True,
            ),
        },
        artifact_contracts={
            'outputs': (ArtifactContractDefinition(key='model', schema='aoi.model.v1'),),
        },
    )

    payload = AlgorithmDefinitionSchema.from_core(definition).model_dump(mode='json', by_alias=True)

    assert payload['actions']['train'] == {
        'datasetInputs': ['training-dataset'], 'executionTargets': ['local-cpu'], 'cancellable': True,
    }
    assert payload['artifactContracts']['outputs'] == [{'key': 'model', 'schema': 'aoi.model.v1'}]
