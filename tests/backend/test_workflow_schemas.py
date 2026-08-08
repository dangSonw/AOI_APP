from app.schemas.workflow import AlgorithmDefinitionSchema, WorkflowSchema
from core.algorithms import get_algorithm_catalog
from core.pipeline import create_default_workflow


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
