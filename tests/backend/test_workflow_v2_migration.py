import json
from pathlib import Path

from app.services.workflow_repository import WorkflowRepository
from core.pipeline import create_default_workflow


def test_read_migrates_v1_removes_bounded_loop_and_writes_backup(tmp_path: Path) -> None:
    repository = WorkflowRepository(tmp_path)
    payload = repository.serialize(create_default_workflow())
    payload['version'] = 1
    payload['migrationNotices'] = []
    payload['nodes'].append({
        'id': '00000000-0000-4000-8000-000000009999',
        'algorithmId': 'bounded-loop',
        'displayName': 'Bounded loop',
        'position': {'x': 0, 'y': 0},
        'parameters': {'targetNodeId': payload['nodes'][0]['id'], 'iterations': 2},
        'ports': [],
    })
    payload['executionOrder'].append('00000000-0000-4000-8000-000000009999')
    for node in payload['nodes'][:-1]:
        node['ports'] = [port for port in node['ports'] if port.get('channel', 'data') == 'data']
    workflow_path = tmp_path / 'rev-c-mainboard' / 'workflow.json'
    workflow_path.parent.mkdir(parents=True)
    workflow_path.write_text(json.dumps(payload), encoding='utf-8')

    migrated = repository.read('rev-c-mainboard')

    assert migrated.version == 2
    assert all(node.algorithm_id != 'bounded-loop' for node in migrated.nodes)
    assert migrated.migration_notices
    assert (workflow_path.parent / 'workflow.pre-control-flow-v2.json').is_file()
    assert json.loads(workflow_path.read_text(encoding='utf-8'))['version'] == 2
