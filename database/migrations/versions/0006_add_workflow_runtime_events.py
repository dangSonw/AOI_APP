"""Add workflow node identities and structured log events.

Revision ID: 0006_add_workflow_runtime_events
Revises: 0005_create_pilot_foundation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0006_add_workflow_runtime_events'
down_revision = '0005_create_pilot_foundation'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('inspection_node_runs', sa.Column('algorithm_id', sa.String(128), nullable=True))
    op.add_column('inspection_node_runs', sa.Column('visit_index', sa.Integer(), server_default='1', nullable=False))
    op.add_column('inspection_node_runs', sa.Column('log_event', postgresql.JSONB(), nullable=True))
    op.execute('UPDATE inspection_node_runs SET algorithm_id = node_id WHERE algorithm_id IS NULL')
    op.alter_column('inspection_node_runs', 'algorithm_id', nullable=False)


def downgrade() -> None:
    op.drop_column('inspection_node_runs', 'log_event')
    op.drop_column('inspection_node_runs', 'visit_index')
    op.drop_column('inspection_node_runs', 'algorithm_id')