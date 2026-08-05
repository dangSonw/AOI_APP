import pytest

from core.pipeline import CycleError, stable_topological_order

from workflow_fixtures import NODE_IDS, branched_workflow, connection


def test_stable_order_preserves_preference_between_ready_nodes() -> None:
    workflow = branched_workflow()

    assert stable_topological_order(workflow, workflow.execution_order) == workflow.execution_order


def test_stable_order_uses_workflow_order_as_default_preference() -> None:
    workflow = branched_workflow()

    assert stable_topological_order(workflow) == (
        NODE_IDS['source'],
        NODE_IDS['right'],
        NODE_IDS['left'],
        NODE_IDS['merge'],
    )


def test_stable_order_rejects_cycles() -> None:
    workflow = branched_workflow()
    source, left, right, merge = workflow.nodes
    cyclic = workflow.with_connections(
        (*workflow.connections, connection(5, merge, 'decision', left, 'score'))
    )

    with pytest.raises(CycleError):
        stable_topological_order(cyclic)