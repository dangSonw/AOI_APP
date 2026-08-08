"""Create persistent inspection runtime evidence.

Revision ID: 0004_create_inspection_runtime
Revises: 0003_create_research_registry
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0004_create_inspection_runtime'
down_revision = '0003_create_research_registry'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'inspection_runs',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('board_serial', sa.String(128), nullable=False),
        sa.Column('lot', sa.String(128), server_default='', nullable=False),
        sa.Column('recipe_id', sa.BigInteger(), sa.ForeignKey('recipes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('operator_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('result_id', sa.BigInteger(), sa.ForeignKey('inspection_results.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('status', sa.String(24), nullable=False),
        sa.Column('current_step', sa.String(64), nullable=False),
        sa.Column('progress_percent', sa.Integer(), server_default='0', nullable=False),
        sa.Column('cancel_requested', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('workflow_snapshot', postgresql.JSONB(), nullable=False),
        sa.Column('workflow_sha256', sa.String(64), nullable=False),
        sa.Column('effective_versions', postgresql.JSONB(), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=False),
        sa.Column('input_artifact', postgresql.JSONB(), nullable=True),
        sa.Column('decision', sa.String(16), nullable=True),
        sa.Column('evidence_sha256', sa.String(64), nullable=True),
        sa.Column('error_code', sa.String(64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('result_id', name='uq_inspection_runs_result_id'),
        sa.CheckConstraint(
            "status IN ('queued','precheck','capturing','executing','completed','faulted','cancelled')",
            name='ck_inspection_runs_status',
        ),
        sa.CheckConstraint('progress_percent >= 0 AND progress_percent <= 100', name='ck_inspection_runs_progress'),
    )
    for column in ('board_serial', 'recipe_id', 'operator_id', 'status'):
        op.create_index(f'ix_inspection_runs_{column}', 'inspection_runs', [column])
    op.create_index('ix_inspection_runs_created_at', 'inspection_runs', [sa.text('created_at DESC')])

    op.create_table(
        'inspection_node_runs',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('run_id', sa.String(64), sa.ForeignKey('inspection_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.String(128), nullable=False),
        sa.Column('node_version', sa.String(64), nullable=False),
        sa.Column('execution_target', sa.String(32), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=False),
        sa.Column('inputs', postgresql.JSONB(), nullable=False),
        sa.Column('outputs', postgresql.JSONB(), nullable=False),
        sa.Column('resources', postgresql.JSONB(), nullable=False),
        sa.Column('evidence_sha256', sa.String(64), nullable=True),
        sa.Column('error_code', sa.String(64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.UniqueConstraint('run_id', 'sequence', name='uq_inspection_node_runs_sequence'),
        sa.CheckConstraint("status IN ('running','completed','faulted','cancelled')", name='ck_inspection_node_runs_status'),
    )
    op.create_index('ix_inspection_node_runs_run_id', 'inspection_node_runs', ['run_id'])

    op.create_table(
        'inspection_review_events',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('result_id', sa.BigInteger(), sa.ForeignKey('inspection_results.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('actor_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('decision', sa.String(10), nullable=False),
        sa.Column('reason', sa.Text(), server_default='', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("decision IN ('PASS','FAIL')", name='ck_inspection_review_events_decision'),
    )
    op.create_index('ix_inspection_review_events_result_id', 'inspection_review_events', ['result_id'])
    op.create_index('ix_inspection_review_events_actor_id', 'inspection_review_events', ['actor_id'])


def downgrade() -> None:
    op.drop_table('inspection_review_events')
    op.drop_table('inspection_node_runs')
    op.drop_table('inspection_runs')