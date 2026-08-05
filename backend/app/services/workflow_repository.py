import json
import os
import re
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

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

    def _read_file(self, path: Path) -> Workflow:
        try:
            with path.open('r', encoding='utf-8') as workflow_file:
                workflow = WorkflowSchema.model_validate(json.load(workflow_file)).to_core()
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