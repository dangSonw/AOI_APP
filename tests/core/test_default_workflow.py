from core.pipeline import create_default_workflow, validate_workflow


def test_default_workflow_is_valid_branched_configuration() -> None:
    workflow = create_default_workflow()

    assert workflow.recipe_slug == 'rev-c-mainboard'
    assert workflow.recipe_name == 'Rev C · Mainboard'
    assert workflow.revision == 0
    assert [node.algorithm_id for node in workflow.nodes] == [
        'image-input',
        'color-conversion',
        'gaussian-blur',
        'otsu-threshold',
        'morphology-operation',
        'connected-components',
        'draw-detections',
        'mask-coverage-score',
        'decision-fusion',
        'decision-output',
        'image-output',
    ]
    assert len(workflow.connections) == 11
    assert validate_workflow(workflow) == ()