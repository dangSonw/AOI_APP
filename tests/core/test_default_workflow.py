from core.pipeline import create_default_workflow, validate_workflow


def test_default_workflow_is_valid_branched_configuration() -> None:
    workflow = create_default_workflow()

    assert workflow.recipe_slug == 'rev-c-mainboard'
    assert workflow.recipe_name == 'Rev C · Mainboard'
    assert workflow.revision == 0
    assert [node.algorithm_id for node in workflow.nodes] == [
        'image-input',
        'ecc-registration',
        'median-mad-robust-difference',
        'patchcore',
        'golden-component-matching',
        'decision-fusion',
        'decision-output',
    ]
    assert len(workflow.connections) == 9
    assert validate_workflow(workflow) == ()