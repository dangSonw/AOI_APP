"""Validation gate for promoting a workflow to RELEASE."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.nodes import get_node_manifest_registry, validate_node_runtime_support
from core.pipeline.models import Workflow


@dataclass(frozen=True, slots=True)
class ReleaseValidationIssue:
    code: str
    message: str
    node_id: str | None = None


def validate_release_workflow(
    workflow: Workflow,
    *,
    evidence: dict[str, Any] | None = None,
) -> tuple[ReleaseValidationIssue, ...]:
    """Return blocking issues; never promote DEBUG/TEST nodes implicitly."""
    issues: list[ReleaseValidationIssue] = []
    evidence = evidence or {}
    required_evidence = {
        'deterministicTest', 'edgeCaseTest', 'benchmark', 'lineage',
        'auditEvidence', 'deploymentCheck',
    }
    missing_evidence = sorted(required_evidence - set(evidence))
    if missing_evidence:
        issues.append(ReleaseValidationIssue(
            'missing-evidence',
            f'Release evidence is incomplete: {", ".join(missing_evidence)}.',
        ))

    manifests = get_node_manifest_registry()
    for node in workflow.nodes:
        manifest = manifests.get(node.algorithm_id)
        if manifest is None:
            issues.append(ReleaseValidationIssue('unknown-node', f'Node {node.algorithm_id} is not registered.', node.id))
            continue
        for message in validate_node_runtime_support(node.algorithm_id, deployment_mode='production'):
            issues.append(ReleaseValidationIssue('node-not-release', message, node.id))
        if not manifest.resource_hints:
            issues.append(ReleaseValidationIssue('missing-resource-limit', f'Node {node.algorithm_id} has no resource limits.', node.id))
        if not manifest.definition.documentation_reference and not evidence.get('documentation'):
            issues.append(ReleaseValidationIssue('missing-documentation', f'Node {node.algorithm_id} has no documentation reference.', node.id))

    if not workflow.recipe_slug.strip():
        issues.append(ReleaseValidationIssue('missing-lineage', 'Release workflow recipe lineage is required.'))
    return tuple(issues)


__all__ = ['ReleaseValidationIssue', 'validate_release_workflow']
