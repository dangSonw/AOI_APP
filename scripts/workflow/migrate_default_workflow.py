import argparse
import shutil
from dataclasses import replace
from pathlib import Path

from app.services.workflow_repository import WorkflowRepository
from core.pipeline import create_default_workflow, validate_workflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Replace a saved recipe workflow with the executable default DAG.')
    parser.add_argument('--recipe-slug', default='rev-c-mainboard')
    parser.add_argument('--projects-root', type=Path, default=Path('data/projects'))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repository = WorkflowRepository(args.projects_root)
    current = repository.read(args.recipe_slug)
    workflow_path = args.projects_root / args.recipe_slug / 'workflow.json'
    backup_path = workflow_path.with_name('workflow.pre-opencv-backup.json')
    if workflow_path.is_file() and not backup_path.exists():
        shutil.copy2(workflow_path, backup_path)

    submitted = replace(
        create_default_workflow(args.recipe_slug, current.recipe_name),
        revision=current.revision,
    )
    saved = repository.save(args.recipe_slug, submitted)
    if validate_workflow(saved):
        raise RuntimeError('Migrated workflow failed validation.')
    print(
        f'Migrated {args.recipe_slug} from revision {current.revision} to {saved.revision} '
        f'with {len(saved.nodes)} executable nodes.',
    )
    if backup_path.exists():
        print(f'Backup: {backup_path.as_posix()}')


if __name__ == '__main__':
    main()