"""Create research run and model registry lineage.

Revision ID: 0003_create_research_registry
Revises: 0002_create_settings_platform
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003_create_research_registry'
down_revision = '0002_create_settings_platform'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'research_experiments',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), server_default='', nullable=False),
        sa.Column('created_by', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        'research_runs',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('experiment_id', sa.String(64), sa.ForeignKey('research_experiments.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('execution_target', sa.String(32), nullable=False),
        sa.Column('code_revision', sa.String(64), nullable=False),
        sa.Column('node_versions', postgresql.JSONB(), nullable=False),
        sa.Column('environment', postgresql.JSONB(), nullable=False),
        sa.Column('random_seeds', postgresql.JSONB(), nullable=False),
        sa.Column('resources', postgresql.JSONB(), nullable=False),
        sa.Column('dataset_versions', postgresql.JSONB(), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=False),
        sa.Column('metrics', postgresql.JSONB(), nullable=False),
        sa.Column('output_artifacts', postgresql.JSONB(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_by', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('queued','running','completed','failed','cancelled')", name='ck_research_runs_status'),
    )
    op.create_index('ix_research_runs_search', 'research_runs', ['experiment_id', 'created_at'])
    op.create_table(
        'research_artifacts',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('run_id', sa.String(64), sa.ForeignKey('research_runs.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('media_type', sa.String(200), nullable=False),
        sa.Column('byte_length', sa.BigInteger(), nullable=False),
        sa.Column('storage_uri', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('run_id', 'name', name='uq_research_artifacts_run_name'),
    )
    op.create_table(
        'model_registry_entries',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('name', sa.String(200), unique=True, nullable=False),
        sa.Column('description', sa.Text(), server_default='', nullable=False),
        sa.Column('created_by', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        'model_versions',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('model_id', sa.BigInteger(), sa.ForeignKey('model_registry_entries.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.String(64), sa.ForeignKey('research_runs.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('artifact_id', sa.BigInteger(), sa.ForeignKey('research_artifacts.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('validation_evidence', postgresql.JSONB(), nullable=False),
        sa.Column('created_by', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('model_id', 'version', name='uq_model_versions_model_version'),
    )
    op.create_table(
        'model_aliases',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('model_id', sa.BigInteger(), sa.ForeignKey('model_registry_entries.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('alias', sa.String(32), nullable=False),
        sa.Column('model_version_id', sa.BigInteger(), sa.ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('model_id', 'alias', name='uq_model_aliases_model_alias'),
    )
    op.create_table(
        'model_promotion_events',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('model_id', sa.BigInteger(), sa.ForeignKey('model_registry_entries.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('alias', sa.String(32), nullable=False),
        sa.Column('action', sa.String(16), nullable=False),
        sa.Column('previous_version_id', sa.BigInteger(), sa.ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('next_version_id', sa.BigInteger(), sa.ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('actor_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("action IN ('promote','rollback')", name='ck_model_promotion_events_action'),
    )


def downgrade() -> None:
    op.drop_table('model_promotion_events')
    op.drop_table('model_aliases')
    op.drop_table('model_versions')
    op.drop_table('model_registry_entries')
    op.drop_table('research_artifacts')
    op.drop_table('research_runs')
    op.drop_table('research_experiments')
