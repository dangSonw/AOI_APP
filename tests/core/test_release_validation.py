from dataclasses import replace

from core.pipeline import create_default_workflow
from core.pipeline.release_validation import validate_release_workflow


def test_release_validation_blocks_debug_nodes_and_missing_evidence() -> None:
    issues = validate_release_workflow(create_default_workflow())

    codes = {issue.code for issue in issues}
    assert 'missing-evidence' in codes
    assert 'node-not-release' in codes
    assert any('DEBUG' in issue.message or 'debug' in issue.message.lower() for issue in issues)


def test_release_validation_accepts_only_release_nodes_with_complete_evidence() -> None:
    workflow = create_default_workflow()
    evidence = {
        'deterministicTest': 'sha256:' + 'a' * 64,
        'edgeCaseTest': 'sha256:' + 'b' * 64,
        'benchmark': {'fixture': 'deterministic', 'resourceLimitMiB': 256},
        'lineage': {'recipe': workflow.recipe_slug, 'revision': workflow.revision},
        'auditEvidence': 'audit-event-01',
        'deploymentCheck': 'passed',
        'documentation': 'docs/release-slice.md',
    }

    issues = validate_release_workflow(workflow, evidence=evidence)

    assert any(issue.code == 'node-not-release' for issue in issues)
    assert not any(issue.code == 'missing-evidence' for issue in issues)


def test_release_validation_reports_unknown_node_without_crashing() -> None:
    workflow = create_default_workflow()
    broken = replace(workflow, nodes=(replace(workflow.nodes[0], algorithm_id='missing-node'), *workflow.nodes[1:]))

    issues = validate_release_workflow(broken)

    assert any(issue.code == 'unknown-node' and issue.node_id == broken.nodes[0].id for issue in issues)
