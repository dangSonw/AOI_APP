import json
import os
import re
import shutil
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError

from app.schemas.workflow import WorkflowSchema
from core.pipeline import ValidationIssue, Workflow, create_default_workflow, validate_workflow


RECIPE_SLUG_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


class InvalidRecipeSlug(ValueError):
    pass


class WorkflowStorageError(RuntimeError):
    def __init__(
        self,
        message: str,
        validation_issues: tuple[ValidationIssue, ...] = (),
    ) -> None:
        super().__init__(message)
        self.validation_issues = validation_issues


class WorkflowValidationError(WorkflowStorageError):
    pass


class StaleWorkflowRevision(RuntimeError):
    pass


class WorkflowRepository:
    _write_lock = RLock()

    def __init__(self, root: Path) -> None:
        self.root = root

    @staticmethod
    def validate_slug(slug: str) -> str:
        if RECIPE_SLUG_PATTERN.fullmatch(slug) is None:
            raise InvalidRecipeSlug('The recipe slug is invalid.')
        return slug

    def _workflow_path(self, slug: str) -> Path:
        return self.root / self.validate_slug(slug) / 'workflow.json'

    @staticmethod
    def serialize(workflow: Workflow) -> dict[str, object]:
        return WorkflowSchema.from_core(workflow).model_dump(mode='json', by_alias=True)

    @staticmethod
    def _control_port(node_id: str, key: str, direction: str) -> dict[str, object]:
        return {
            'id': str(uuid5(NAMESPACE_URL, f'aoi-workflow-v2:{node_id}:{key}')),
            'templateKey': key,
            'direction': direction,
            'dataType': 'generic',
            'displayLabel': key.capitalize(),
            'required': False,
            'variadic': False,
            'variadicInstanceIndex': None,
            'channel': 'control',
            'origin': 'system',
            'runtimeBinding': 'none',
            'runtimeKey': None,
            'passthroughInputPortId': None,
        }

    @classmethod
    def _migrate_v1_payload(cls, payload: dict[str, object]) -> dict[str, object]:
        nodes = [dict(node) for node in payload.get('nodes', []) if isinstance(node, dict)]
        removed_ids = {str(node.get('id')) for node in nodes if node.get('algorithmId') == 'bounded-loop'}
        nodes = [node for node in nodes if str(node.get('id')) not in removed_ids]
        node_ids = {str(node.get('id')) for node in nodes}
        execution_order = [
            str(node_id) for node_id in payload.get('executionOrder', [])
            if str(node_id) in node_ids
        ]
        execution_order.extend(node_id for node_id in node_ids if node_id not in execution_order)

        for node in nodes:
            data_ports: list[dict[str, object]] = []
            for raw_port in node.get('ports', []):
                if not isinstance(raw_port, dict) or raw_port.get('channel', 'data') == 'control':
                    continue
                port = dict(raw_port)
                port.update({
                    'channel': 'data',
                    'origin': port.get('origin', 'default'),
                    'runtimeBinding': port.get('runtimeBinding', 'slot'),
                    'runtimeKey': port.get('runtimeKey') or port.get('templateKey'),
                    'passthroughInputPortId': port.get('passthroughInputPortId'),
                })
                data_ports.append(port)
            node_id = str(node['id'])
            node['ports'] = [
                *data_ports,
                cls._control_port(node_id, 'trigger', 'input'),
                cls._control_port(node_id, 'success', 'output'),
                cls._control_port(node_id, 'failure', 'output'),
            ]

        ports_by_node = {
            str(node['id']): {str(port['templateKey']): str(port['id']) for port in node['ports']}
            for node in nodes
        }
        data_connections = [
            dict(connection) for connection in payload.get('connections', [])
            if isinstance(connection, dict)
            and connection.get('kind', 'data') == 'data'
            and str(connection.get('sourceNodeId')) in node_ids
            and str(connection.get('targetNodeId')) in node_ids
        ]
        control_connections = [
            {
                'id': str(uuid5(NAMESPACE_URL, f'aoi-workflow-v2:control:{source_id}:{target_id}')),
                'sourceNodeId': source_id,
                'sourcePortId': ports_by_node[source_id]['success'],
                'targetNodeId': target_id,
                'targetPortId': ports_by_node[target_id]['trigger'],
                'kind': 'control',
                'maxTraversals': None,
            }
            for source_id, target_id in zip(execution_order, execution_order[1:])
        ]
        notices = [str(notice) for notice in payload.get('migrationNotices', [])]
        notices.append('Workflow migrated to control-flow schema v2.')
        if removed_ids:
            notices.append(f'Removed {len(removed_ids)} bounded-loop node(s) and attached connections.')
        return {
            **payload,
            'version': 2,
            'nodes': nodes,
            'connections': [*data_connections, *control_connections],
            'executionOrder': execution_order,
            'migrationNotices': notices,
        }

    @classmethod
    def _persist_payload(cls, path: Path, payload: dict[str, object]) -> None:
        temporary_path = path.with_name(f'{path.name}.tmp')
        try:
            with temporary_path.open('w', encoding='utf-8') as workflow_file:
                json.dump(payload, workflow_file, ensure_ascii=False, indent=2)
                workflow_file.write('\n')
                workflow_file.flush()
                os.fsync(workflow_file.fileno())
            os.replace(temporary_path, path)
        except OSError:
            temporary_path.unlink(missing_ok=True)
            raise

    def _read_file(self, path: Path) -> Workflow:
        try:
            with path.open('r', encoding='utf-8') as workflow_file:
                payload = json.load(workflow_file)
            if not isinstance(payload, dict):
                raise TypeError('Workflow payload must be an object.')
            if int(payload.get('version', 1)) < 2:
                with self._write_lock:
                    backup_path = path.with_name('workflow.pre-control-flow-v2.json')
                    if not backup_path.exists():
                        shutil.copy2(path, backup_path)
                    payload = self._migrate_v1_payload(payload)
                    self._persist_payload(path, payload)
            workflow = WorkflowSchema.model_validate(payload).to_core()
        except (OSError, json.JSONDecodeError, ValidationError, TypeError, ValueError) as error:
            raise WorkflowStorageError('The recipe contains an invalid persisted workflow.') from error

        if validate_workflow(workflow):
            raise WorkflowStorageError('The recipe contains an invalid persisted workflow.')
        return workflow

    def read(self, slug: str) -> Workflow:
        path = self._workflow_path(slug)
        if not path.exists():
            recipe_name = ' '.join(part.capitalize() for part in slug.split('-'))
            if slug == 'rev-c-mainboard':
                recipe_name = 'Rev C · Mainboard'
            return create_default_workflow(slug, recipe_name)
        return self._read_file(path)

    def save(self, slug: str, submitted: Workflow) -> Workflow:
        path = self._workflow_path(slug)
        issues = validate_workflow(submitted)
        if issues:
            raise WorkflowValidationError('The submitted workflow is invalid.', issues)
        if submitted.recipe_slug != slug:
            mismatch = ValidationIssue('invalid-parameter', 'The workflow recipe slug does not match the request path.')
            raise WorkflowValidationError('The submitted workflow is invalid.', (mismatch,))

        with self._write_lock:
            stored_revision = self._read_file(path).revision if path.exists() else 0
            if submitted.revision != stored_revision:
                raise StaleWorkflowRevision('The workflow has been updated by another request.')

            updated = replace(
                submitted,
                revision=stored_revision + 1,
                updated_at=datetime.now(timezone.utc),
            )
            temporary_path = path.with_name('workflow.json.tmp')
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with temporary_path.open('w', encoding='utf-8') as workflow_file:
                    json.dump(self.serialize(updated), workflow_file, ensure_ascii=False, indent=2)
                    workflow_file.write('\n')
                    workflow_file.flush()
                    os.fsync(workflow_file.fileno())
                os.replace(temporary_path, path)
                try:
                    directory_descriptor = os.open(path.parent, os.O_RDONLY)
                    try:
                        os.fsync(directory_descriptor)
                    finally:
                        os.close(directory_descriptor)
                except OSError:
                    pass
            except OSError as error:
                temporary_path.unlink(missing_ok=True)
                raise WorkflowStorageError('The workflow could not be persisted.') from error
            return updated