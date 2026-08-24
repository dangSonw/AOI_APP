"""Add research training-job identity, progress, and retry lineage.

Revision ID: 0007_add_research_training_jobs
Revises: 0006_add_workflow_runtime_events
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0007_add_research_training_jobs'
down_revision = '0006_add_workflow_runtime_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('ck_research_runs_status', 'research_runs', type_='check')
    op.add_column('research_runs', sa.Column('parent_run_id', sa.String(64), nullable=True))
    op.add_column('research_runs', sa.Column('action_name', sa.String(64), server_default='legacy-run', nullable=False))
    op.add_column('research_runs', sa.Column('node_id', sa.String(128), server_default='legacy', nullable=False))
    op.add_column('research_runs', sa.Column('node_instance_id', sa.String(128), server_default='legacy', nullable=False))
    op.add_column('research_runs', sa.Column('node_package_version', sa.String(64), server_default='legacy', nullable=False))
    op.add_column('research_runs', sa.Column('workflow_revision', sa.Integer(), server_default='1', nullable=False))
    op.add_column('research_runs', sa.Column('progress', postgresql.JSONB(), nullable=True))
    op.create_foreign_key(
        'fk_research_runs_parent_run_id', 'research_runs', 'research_runs',
        ['parent_run_id'], ['id'], ondelete='RESTRICT',
    )
    op.create_check_constraint(
        'ck_research_runs_status', 'research_runs',
        "status IN ('queued','running','preparing-dataset','validating','training','evaluating',"
        "'persisting-artifacts','cancelling','completed','failed','cancelled')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_research_runs_status', 'research_runs', type_='check')
    op.execute(
        "UPDATE research_runs SET status = 'failed', "
        "error = COALESCE(error, 'Training job stopped by database downgrade.') "
        "WHERE status NOT IN ('queued','running','completed','failed','cancelled')"
    )
    op.create_check_constraint(
        'ck_research_runs_status', 'research_runs',
        "status IN ('queued','running','completed','failed','cancelled')",
    )
    op.drop_constraint('fk_research_runs_parent_run_id', 'research_runs', type_='foreignkey')
    op.drop_column('research_runs', 'progress')
    op.drop_column('research_runs', 'workflow_revision')
    op.drop_column('research_runs', 'node_package_version')
    op.drop_column('research_runs', 'node_instance_id')
    op.drop_column('research_runs', 'node_id')
    op.drop_column('research_runs', 'action_name')
    op.drop_column('research_runs', 'parent_run_id')